import { createHmac } from "crypto";
import express from "express";
import { describe, expect, it } from "vitest";
import {
  FAB_OPERATOR_SESSION_AUDIENCE,
  FAB_OPERATOR_SESSION_TTL_SECONDS,
  normalizeFabOperatorTarget,
  registerFabOperatorSessionRoutes,
} from "./fabOperatorSession";

async function startTestServer(
  options: Parameters<typeof registerFabOperatorSessionRoutes>[2],
): Promise<{ baseUrl: string; close: () => Promise<void> }> {
  const app = express();
  registerFabOperatorSessionRoutes(app, undefined, options);
  const server = app.listen(0);
  const address = server.address();
  if (!address || typeof address === "string") throw new Error("Expected a TCP test server");
  return {
    baseUrl: `http://127.0.0.1:${address.port}`,
    close: () => new Promise<void>((resolve, reject) => {
      server.close(error => error ? reject(error) : resolve());
    }),
  };
}

describe("FAB operator session handoff", () => {
  it("creates a short-lived signed ticket without exposing the API token", async () => {
    const token = "private-local-api-token";
    const now = 1_775_000_000_000;
    const server = await startTestServer({
      localOperatorMode: true,
      nonce: () => "fixed_operator_nonce_1234",
      now: () => now,
      publicBaseUrl: "http://127.0.0.1:5001",
      token,
    });
    try {
      const response = await fetch(
        `${server.baseUrl}/api/fab/operator-session?next=${encodeURIComponent("/api/audit?limit=25")}`,
        { redirect: "manual" },
      );

      expect(response.status).toBe(302);
      expect(response.headers.get("cache-control")).toBe("no-store");
      expect(response.headers.get("referrer-policy")).toBe("no-referrer");
      const location = response.headers.get("location") || "";
      expect(location).toMatch(/^http:\/\/127\.0\.0\.1:5001\/operator\/session\/bootstrap\?ticket=/);
      expect(location).not.toContain(token);

      const ticket = new URL(location).searchParams.get("ticket") || "";
      const [encodedPayload, signature] = ticket.split(".");
      expect(signature).toBe(createHmac("sha256", token).update(encodedPayload).digest("base64url"));
      expect(JSON.parse(Buffer.from(encodedPayload, "base64url").toString("utf8"))).toEqual({
        actor: "fab_dashboard:local_operator",
        aud: FAB_OPERATOR_SESSION_AUDIENCE,
        exp: now / 1_000 + FAB_OPERATOR_SESSION_TTL_SECONDS,
        iat: now / 1_000,
        nonce: "fixed_operator_nonce_1234",
        next: "/api/audit?limit=25",
        v: 1,
      });
    } finally {
      await server.close();
    }
  });

  it("requires a loopback operator or authenticated administrator", async () => {
    const denied = await startTestServer({
      authenticateRequest: async () => { throw new Error("No session"); },
      localOperatorMode: false,
      token: "token",
    });
    const admin = await startTestServer({
      authenticateRequest: async () => ({ openId: "owner", role: "admin" } as never),
      localOperatorMode: false,
      publicBaseUrl: "https://fab-api.example",
      token: "token",
    });
    try {
      expect((await fetch(`${denied.baseUrl}/api/fab/operator-session?next=%2F`, { redirect: "manual" })).status).toBe(403);
      const response = await fetch(`${admin.baseUrl}/api/fab/operator-session?next=%2F%23audit`, { redirect: "manual" });
      expect(response.status).toBe(302);
      expect(response.headers.get("location")).toMatch(/^https:\/\/fab-api\.example\/operator\/session\/bootstrap\?ticket=/);
    } finally {
      await denied.close();
      await admin.close();
    }
  });

  it("rejects unsafe destinations and missing or invalid service configuration", async () => {
    expect(normalizeFabOperatorTarget("/documents/42?view=evidence#source")).toBe("/documents/42?view=evidence#source");
    for (const target of [
      "https://evil.example",
      "//evil.example",
      "/\\evil.example",
      "/%5cevil.example",
      "/operator/session/bootstrap",
      "/operator%2fsession%2fbootstrap",
      `/documents/${"x".repeat(2_100)}`,
    ]) {
      expect(normalizeFabOperatorTarget(target)).toBeNull();
    }

    const missingToken = await startTestServer({ localOperatorMode: true, token: "" });
    const invalidOrigin = await startTestServer({
      localOperatorMode: true,
      publicBaseUrl: "http://fab-api.example",
      token: "token",
    });
    try {
      expect((await fetch(`${missingToken.baseUrl}/api/fab/operator-session?next=%2F`, { redirect: "manual" })).status).toBe(503);
      expect((await fetch(`${invalidOrigin.baseUrl}/api/fab/operator-session?next=%2F`, { redirect: "manual" })).status).toBe(500);
    } finally {
      await missingToken.close();
      await invalidOrigin.close();
    }
  });
});
