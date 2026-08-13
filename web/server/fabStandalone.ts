import "dotenv/config";
import compression from "compression";
import express from "express";
import { createServer } from "http";
import net from "net";
import { createExpressMiddleware } from "@trpc/server/adapters/express";
import { createFabContext } from "./fabContext";
import { registerFabOperatorSessionRoutes } from "./fabOperatorSession";
import { fabStandaloneRouter } from "./fabRouter";
import { registerFabRuntimeRoute } from "./fabRuntime";
import { registerFabSourcePreviewRoutes } from "./fabSourcePreview";
import { ENV } from "./_core/env";
import { createFabSecurityMiddleware } from "./_core/security";
import { serveStatic } from "./_core/static";
import { relaxedLimiter } from "./lib/rateLimiter";

function isPortAvailable(port: number): Promise<boolean> {
  return new Promise((resolve) => {
    const probe = net.createServer();
    probe.listen(port, ENV.fabWebHost, () => probe.close(() => resolve(true)));
    probe.on("error", () => resolve(false));
  });
}

async function findAvailablePort(startPort: number): Promise<number> {
  for (let port = startPort; port < startPort + 20; port += 1) {
    if (await isPortAvailable(port)) return port;
  }
  throw new Error(`No available port found starting at ${startPort}`);
}

export async function startFabStandaloneServer() {
  const app = express();
  const server = createServer(app);
  app.set("trust proxy", 1);
  app.use(...createFabSecurityMiddleware(ENV.isProduction));
  app.use(compression({ threshold: 1_024 }));
  app.use(express.json({ limit: "10mb" }));
  app.use(express.urlencoded({ limit: "10mb", extended: true }));

  registerFabRuntimeRoute(app);
  registerFabSourcePreviewRoutes(app);
  registerFabOperatorSessionRoutes(app, relaxedLimiter);
  app.use(
    "/api/trpc",
    relaxedLimiter,
    createExpressMiddleware({
      router: fabStandaloneRouter,
      createContext: createFabContext,
    }),
  );
  serveStatic(app);

  const preferredPort = Number.parseInt(process.env.PORT || "3000", 10);
  const port = await findAvailablePort(preferredPort);
  await new Promise<void>((resolve) => {
    server.listen(port, ENV.fabWebHost, resolve);
  });

  const shutdown = () => {
    server.close(() => process.exit(0));
    setTimeout(() => process.exit(1), 10_000).unref();
  };
  process.on("SIGTERM", shutdown);
  process.on("SIGINT", shutdown);
  return { app, port, server };
}

if (process.env.NODE_ENV !== "test") {
  startFabStandaloneServer().catch((error) => {
    console.error(error instanceof Error ? error.message : "FAB dashboard startup failed");
    process.exit(1);
  });
}
