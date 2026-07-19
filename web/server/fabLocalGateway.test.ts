import { afterEach, describe, expect, it, vi } from "vitest";
import {
  fabLocalRequest,
  getFabControlCenter,
  getFabLocalApiBaseUrl,
  runFabOperatorCommand,
  uploadFabIntakeFile,
} from "./fabLocalGateway";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("FAB local API gateway", () => {
  it("rejects insecure non-loopback endpoints", () => {
    expect(() => getFabLocalApiBaseUrl("http://accounting.example.test"))
      .toThrow("must use https");
    expect(getFabLocalApiBaseUrl("http://127.0.0.1:5001").hostname).toBe("127.0.0.1");
  });

  it("keeps the local API token server-side", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      expect(new Headers(init?.headers).get("authorization")).toBe("Bearer private-token");
      return new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await fabLocalRequest("/api/health", {}, {
      baseUrl: "http://127.0.0.1:5001",
      token: "private-token",
    });

    expect(result).toEqual({ status: "ok" });
    expect(JSON.stringify(result)).not.toContain("private-token");
  });

  it("aggregates authoritative ledger state into the control center", async () => {
    const fixtures: Record<string, unknown> = {
      "/api/health": { status: "attention", operations: { status: "attention" } },
      "/api/dashboard": {
        documents: 18,
        pending_review: 4,
        unreconciled_bank_transactions: 3,
        unreconciled_documents: 2,
        failed_documents: 1,
      },
      "/api/autonomy/plan": { status: "ready", actions: [] },
      "/api/exceptions": {
        summary: { total: 2, bySeverity: { high: 1, medium: 1, low: 0 } },
        exceptions: [{ id: "exception-1", severity: "high" }],
      },
      "/api/settings": {
        sources: [{ id: "google_drive", label: "Google Drive", status: "ready", configured: true }],
      },
      "/api/sources/readiness": {
        sources: [{ source: "google_drive", enabled: true, canSync: true }],
      },
      "/api/sources": { sources: [{ source_type: "google_drive", status: "connected", updated_at: "2026-07-15T08:00:00Z" }] },
      "/api/workflows": { workflowRuns: [{ id: 10, status: "completed" }] },
      "/api/workflows/recovery": { status: "due", dueCount: 1, candidates: [{ workflowRunId: 9 }] },
      "/api/notifications": { notifications: [{ id: 4, severity: "medium" }] },
      "/api/reconciliation": { reconciliationMatches: [{ id: 3, status: "needs_review" }] },
      "/api/audit": { auditEvents: [{ id: 2, action: "local_api.source.upsert" }] },
      "/api/close-readiness": { status: "blocked", canClose: false, blockingCount: 2 },
      "/api/hai/status": { status: "prepared_disabled", enabled: false, allowedCommandIds: [] },
      "/api/hai/manifest": { version: "fab-hai-connector-v1", commands: [] },
    };
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input));
      const fixture = fixtures[url.pathname];
      return new Response(JSON.stringify(fixture ?? {}), {
        status: fixture ? 200 : 404,
        headers: { "content-type": "application/json" },
      });
    }));

    const result = await getFabControlCenter();

    expect(result.connection.connected).toBe(true);
    expect(result.metrics).toMatchObject({ documents: 18, pendingReview: 4, unreconciled: 5, exceptions: 2 });
    expect(result.connections).toEqual(expect.arrayContaining([
      expect.objectContaining({ id: "google_drive", canSync: true }),
      expect.objectContaining({ id: "hai", status: "prepared_disabled" }),
    ]));
    expect(result.recovery).toMatchObject({ dueCount: 1 });
    expect(JSON.stringify(result)).not.toContain("private-token");
  });

  it("maps dashboard commands only to fixed local API paths", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => new Response(
      JSON.stringify({ status: "completed", path: new URL(String(input)).pathname, body: JSON.parse(String(init?.body)) }),
      { status: 200, headers: { "content-type": "application/json" } },
    ));
    vi.stubGlobal("fetch", fetchMock);

    const result = await runFabOperatorCommand("run_due_recovery", "operator-12", { limit: 2 });

    expect(result).toMatchObject({
      status: "completed",
      path: "/api/workflows/recovery/run-due",
      body: { limit: 2, actor: "operator-12" },
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("uploads intake files only through the fixed local API path", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => new Response(
      JSON.stringify({
        status: "registered",
        path: new URL(String(input)).pathname,
        body: JSON.parse(String(init?.body)),
      }),
      { status: 201, headers: { "content-type": "application/json" } },
    ));
    vi.stubGlobal("fetch", fetchMock);

    const result = await uploadFabIntakeFile({
      filename: "receipt.pdf",
      mimeType: "application/pdf",
      contentBase64: "cmVjZWlwdA==",
    });

    expect(result).toMatchObject({
      status: "registered",
      path: "/api/intake/upload",
      body: { filename: "receipt.pdf", mimeType: "application/pdf" },
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
