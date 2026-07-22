import type { Application } from "express";
import { ENV } from "./_core/env";

export function registerFabRuntimeRoute(
  app: Application,
  localApiEndpoint = ENV.fabLocalApiUrl,
) {
  app.get("/api/fab/runtime", (_req, res) => {
    res.setHeader("cache-control", "no-store");
    res.json({
      service: "fab-operator-dashboard",
      apiVersion: "1",
      localApiEndpoint,
    });
  });
}
