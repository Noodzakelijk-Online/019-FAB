import "dotenv/config";
import express from "express";
import { createServer } from "http";
import net from "net";
import helmet from "helmet";
import { createExpressMiddleware } from "@trpc/server/adapters/express";
import { registerOAuthRoutes } from "./oauth";
import { appRouter } from "../routers";
import { createContext } from "./context";
import { serveStatic, setupVite } from "./vite";
import { webhookLimiter, relaxedLimiter } from "../lib/rateLimiter";
import { createLogger } from "../lib/logger";
import { registerFabOperationsRoutes } from "../fabOperations";

const log = createLogger("Server");

function isPortAvailable(port: number): Promise<boolean> {
  return new Promise(resolve => {
    const server = net.createServer();
    server.listen(port, () => {
      server.close(() => resolve(true));
    });
    server.on("error", () => resolve(false));
  });
}

async function findAvailablePort(startPort: number = 3000): Promise<number> {
  for (let port = startPort; port < startPort + 20; port++) {
    if (await isPortAvailable(port)) {
      return port;
    }
  }
  throw new Error(`No available port found starting from ${startPort}`);
}

async function startServer() {
  const app = express();
  const server = createServer(app);

  // Trust first proxy (required for rate limiting and IP detection behind reverse proxy)
  app.set("trust proxy", 1);

  // ── Security headers via Helmet ───────────────────────────────
  // Helmet sets Content-Security-Policy, X-Content-Type-Options,
  // Strict-Transport-Security, X-Frame-Options, etc.
  app.use(
    helmet({
      contentSecurityPolicy: false, // Managed by Vite in dev, configured separately in prod
      crossOriginEmbedderPolicy: false, // Allow embedding external resources (CDN images, Stripe)
    })
  );

  // ── Stripe webhook — BEFORE express.json() for raw body ───────
  app.post(
    "/api/stripe/webhook",
    webhookLimiter,
    express.raw({ type: "application/json" }),
    async (req, res) => {
      try {
        const { handleStripeWebhook } = await import("../stripe/webhook");
        await handleStripeWebhook(req, res);
      } catch (err) {
        log.error("Webhook handler failed", {}, err instanceof Error ? err : new Error(String(err)));
        res.status(500).json({ error: "Webhook handler failed" });
      }
    }
  );

  // ── Body parsers ──────────────────────────────────────────────
  // 10mb limit is generous for form data; file uploads go to S3
  app.use(express.json({ limit: "10mb" }));
  app.use(express.urlencoded({ limit: "10mb", extended: true }));

  // ── OAuth callback ────────────────────────────────────────────
  registerOAuthRoutes(app);
  registerFabOperationsRoutes(app, relaxedLimiter);

  // ── tRPC API with relaxed rate limiting ───────────────────────
  app.use(
    "/api/trpc",
    relaxedLimiter,
    createExpressMiddleware({
      router: appRouter,
      createContext,
    })
  );

  // ── Static / Vite ─────────────────────────────────────────────
  if (process.env.NODE_ENV === "development") {
    await setupVite(app, server);
  } else {
    serveStatic(app);
  }

  // ── Graceful shutdown ─────────────────────────────────────────
  const shutdown = (signal: string) => {
    log.info(`${signal} received, shutting down gracefully...`);
    server.close(() => {
      log.info("Server closed");
      process.exit(0);
    });
    // Force exit after 10s if connections don't close
    setTimeout(() => {
      log.warn("Forcing shutdown after timeout");
      process.exit(1);
    }, 10_000);
  };

  process.on("SIGTERM", () => shutdown("SIGTERM"));
  process.on("SIGINT", () => shutdown("SIGINT"));

  // ── Unhandled rejection / exception safety net ────────────────
  process.on("unhandledRejection", (reason) => {
    log.error("Unhandled promise rejection", {
      reason: reason instanceof Error ? reason.message : String(reason),
    });
  });

  process.on("uncaughtException", (err) => {
    log.error("Uncaught exception — shutting down", {}, err);
    process.exit(1);
  });

  // ── Start listening ───────────────────────────────────────────
  const preferredPort = parseInt(process.env.PORT || "3000");
  const port = await findAvailablePort(preferredPort);

  if (port !== preferredPort) {
    log.info(`Port ${preferredPort} is busy, using port ${port} instead`);
  }

  server.listen(port, () => {
    log.info(`Server running on http://localhost:${port}/`);
  });
}

startServer().catch((err) => {
  const log = createLogger("Server");
  log.error("Failed to start server", {}, err);
  process.exit(1);
});
