import express from "express";
import { describe, expect, it } from "vitest";
import { registerFabRuntimeRoute } from "./fabRuntime";

describe("FAB runtime identity", () => {
  it("exposes an exact, non-cacheable service marker and API endpoint", async () => {
    const app = express();
    registerFabRuntimeRoute(app, "http://127.0.0.1:5007");
    const server = app.listen(0);
    try {
      const address = server.address();
      if (!address || typeof address === "string") {
        throw new Error("Expected TCP test server address");
      }

      const response = await fetch(`http://127.0.0.1:${address.port}/api/fab/runtime`);

      expect(response.status).toBe(200);
      expect(response.headers.get("cache-control")).toBe("no-store");
      await expect(response.json()).resolves.toEqual({
        service: "fab-operator-dashboard",
        apiVersion: "1",
        localApiEndpoint: "http://127.0.0.1:5007",
        instanceId: expect.stringMatching(/^[a-f0-9]{64}$/),
      });
    } finally {
      await new Promise<void>((resolve, reject) => {
        server.close((error) => {
          if (error) reject(error);
          else resolve();
        });
      });
    }
  });
});
