import type { Application } from "express";
import { createHash } from "crypto";
import path from "path";
import { ENV } from "./_core/env";

export function registerFabRuntimeRoute(
  app: Application,
  localApiEndpoint = ENV.fabLocalApiUrl,
  instanceRoot = path.resolve(import.meta.dirname, "../.."),
) {
  app.get("/api/fab/runtime", (_req, res) => {
    res.setHeader("cache-control", "no-store");
    res.json({
      service: "fab-operator-dashboard",
      apiVersion: "1",
      localApiEndpoint,
      instanceId: localInstanceId(instanceRoot),
    });
  });
}

function localInstanceId(instanceRoot: string) {
  let normalized = path.resolve(instanceRoot).replaceAll("\\", "/").replace(/\/+$/, "");
  if (process.platform === "win32") normalized = normalized.toLowerCase();
  return createHash("sha256").update(normalized, "utf8").digest("hex");
}
