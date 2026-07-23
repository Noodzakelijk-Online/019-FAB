import { createHash } from "crypto";
import express from "express";
import { describe, expect, it, vi } from "vitest";
import { registerFabSourcePreviewRoutes } from "./fabSourcePreview";

async function startTestServer(
  options: Parameters<typeof registerFabSourcePreviewRoutes>[1],
): Promise<{ baseUrl: string; close: () => Promise<void> }> {
  const app = express();
  registerFabSourcePreviewRoutes(app, options);
  const server = app.listen(0);
  const address = server.address();
  if (!address || typeof address === "string") {
    throw new Error("Expected TCP test server address");
  }
  return {
    baseUrl: `http://127.0.0.1:${address.port}`,
    close: () => new Promise<void>((resolve, reject) => {
      server.close((error) => error ? reject(error) : resolve());
    }),
  };
}

describe("FAB source preview proxy", () => {
  it("keeps the API token server-side and re-verifies source bytes", async () => {
    const source = new TextEncoder().encode("verified receipt");
    const sha256 = createHash("sha256").update(source).digest("hex");
    const fetchImpl = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      expect(new Headers(init?.headers).get("authorization")).toBe("Bearer private-token");
      return new Response(source, {
        headers: {
          "content-length": String(source.byteLength),
          "content-type": "text/plain",
          "x-fab-source-integrity": "verified",
          "x-fab-source-sha256": sha256,
          "x-frame-options": "DENY",
        },
      });
    });
    const server = await startTestServer({
      baseUrl: "http://127.0.0.1:5001",
      fetchImpl,
      localOperatorMode: true,
      token: "private-token",
    });
    try {
      const response = await fetch(`${server.baseUrl}/api/fab/source/42`);

      expect(response.status).toBe(200);
      await expect(response.text()).resolves.toBe("verified receipt");
      expect(response.headers.get("cache-control")).toBe("no-store");
      expect(response.headers.get("x-fab-source-integrity")).toBe("verified");
      expect(response.headers.get("x-fab-source-sha256")).toBe(sha256);
      expect(response.headers.get("x-frame-options")).toBe("SAMEORIGIN");
      expect(response.headers.get("content-security-policy")).toContain("sandbox");
    } finally {
      await server.close();
    }
  });

  it("allows the browser PDF viewer while retaining same-origin framing", async () => {
    const source = new TextEncoder().encode("%PDF verified receipt");
    const sha256 = createHash("sha256").update(source).digest("hex");
    const server = await startTestServer({
      baseUrl: "http://127.0.0.1:5001",
      fetchImpl: async () => new Response(source, {
        headers: {
          "content-type": "application/pdf",
          "x-fab-source-integrity": "verified",
          "x-fab-source-sha256": sha256,
        },
      }),
      localOperatorMode: true,
    });
    try {
      const response = await fetch(`${server.baseUrl}/api/fab/source/42`);

      expect(response.status).toBe(200);
      expect(response.headers.get("content-security-policy")).toBe("frame-ancestors 'self'");
      expect(response.headers.get("x-frame-options")).toBe("SAMEORIGIN");
      expect(response.headers.get("x-content-type-options")).toBe("nosniff");
    } finally {
      await server.close();
    }
  });

  it("rejects requests without an admin or enabled loopback operator", async () => {
    const fetchImpl = vi.fn();
    const server = await startTestServer({
      authenticateRequest: async () => {
        throw new Error("No session");
      },
      fetchImpl,
      localOperatorMode: false,
    });
    try {
      const response = await fetch(`${server.baseUrl}/api/fab/source/42`);

      expect(response.status).toBe(403);
      expect(fetchImpl).not.toHaveBeenCalled();
    } finally {
      await server.close();
    }
  });

  it("rejects a mismatched upstream integrity proof", async () => {
    const source = new TextEncoder().encode("changed receipt");
    const fetchImpl = vi.fn(async () => new Response(source, {
      headers: {
        "content-type": "text/plain",
        "x-fab-source-integrity": "verified",
        "x-fab-source-sha256": "0".repeat(64),
      },
    }));
    const server = await startTestServer({
      baseUrl: "http://127.0.0.1:5001",
      fetchImpl,
      localOperatorMode: true,
    });
    try {
      const response = await fetch(`${server.baseUrl}/api/fab/source/42`);

      expect(response.status).toBe(502);
      await expect(response.json()).resolves.toEqual({
        error: "The FAB source preview failed its gateway integrity check",
      });
    } finally {
      await server.close();
    }
  });

  it("rejects unsafe MIME types and bounded-length violations", async () => {
    const source = new TextEncoder().encode("1234");
    const sha256 = createHash("sha256").update(source).digest("hex");
    const unsafeServer = await startTestServer({
      baseUrl: "http://127.0.0.1:5001",
      fetchImpl: async () => new Response(source, {
        headers: {
          "content-type": "text/html",
          "x-fab-source-integrity": "verified",
          "x-fab-source-sha256": sha256,
        },
      }),
      localOperatorMode: true,
    });
    const oversizedServer = await startTestServer({
      baseUrl: "http://127.0.0.1:5001",
      fetchImpl: async () => new Response(source, {
        headers: {
          "content-length": String(source.byteLength),
          "content-type": "text/plain",
          "x-fab-source-integrity": "verified",
          "x-fab-source-sha256": sha256,
        },
      }),
      localOperatorMode: true,
      maxBytes: 3,
    });
    try {
      expect((await fetch(`${unsafeServer.baseUrl}/api/fab/source/42`)).status).toBe(415);
      expect((await fetch(`${oversizedServer.baseUrl}/api/fab/source/42`)).status).toBe(413);
    } finally {
      await unsafeServer.close();
      await oversizedServer.close();
    }
  });
});
