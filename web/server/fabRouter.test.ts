import express from "express";
import { createServer } from "http";
import { createExpressMiddleware } from "@trpc/server/adapters/express";
import { describe, expect, it } from "vitest";
import { fabStandaloneRouter } from "./fabRouter";

describe("FAB standalone router", () => {
  it("serves the existing operator contract without the public application router", async () => {
    const app = express();
    app.use("/api/trpc", createExpressMiddleware({
      router: fabStandaloneRouter,
      createContext: ({ req, res }) => ({
        req,
        res,
        user: {
          id: 7,
          role: "admin",
          name: "FAB operator",
          email: "operator@example.test",
        },
      }) as never,
    }));
    const server = createServer(app);
    await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
    try {
      const address = server.address();
      if (!address || typeof address === "string") throw new Error("Expected TCP address");
      const access = await fetch(
        `http://127.0.0.1:${address.port}/api/trpc/fab.access?input=${encodeURIComponent(JSON.stringify({ json: null }))}`,
      );
      const identity = await fetch(
        `http://127.0.0.1:${address.port}/api/trpc/auth.me?input=${encodeURIComponent(JSON.stringify({ json: null }))}`,
      );
      const missingPublicRoute = await fetch(
        `http://127.0.0.1:${address.port}/api/trpc/stripe.products?input=${encodeURIComponent(JSON.stringify({ json: null }))}`,
      );
      expect(access.status).toBe(200);
      expect(await access.text()).toContain("FAB operator");
      expect(identity.status).toBe(200);
      expect(await identity.text()).toContain("operator@example.test");
      expect(missingPublicRoute.status).toBe(404);
    } finally {
      await new Promise<void>((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
    }
  });
});
