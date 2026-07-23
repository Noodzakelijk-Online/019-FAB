import { afterEach, describe, expect, it, vi } from "vitest";
import {
  fabLocalRequest,
  getFabControlCenter,
  getFabLocalApiBaseUrl,
  resetFabControlCenterCacheForTests,
  resolveFabReviewItem,
  runFabOperatorCommand,
  saveFabWaveSetup,
  startFabGmailAuthorization,
  startFabGoogleDriveAuthorization,
  uploadFabGmailCredentials,
  uploadFabGoogleDriveCredentials,
  uploadFabIntakeFile,
  validateFabWaveSetup,
} from "./fabLocalGateway";

afterEach(() => {
  resetFabControlCenterCacheForTests();
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
        sources: [
          { id: "google_drive", label: "Google Drive", status: "ready", configured: true },
          { id: "waveapps_business", label: "Wave - Noodzakelijk Online", status: "attention", configured: false },
        ],
      },
      "/api/sources/readiness": {
        sources: [{ source: "google_drive", enabled: true, canSync: true, nextAction: "Sync the approved folder." }],
      },
      "/api/sources": { sources: [{ source_type: "google_drive", status: "connected", updated_at: "2026-07-15T08:00:00Z" }] },
      "/api/workflows": { workflowRuns: [{ id: 10, status: "completed" }] },
      "/api/workflows/recovery": { status: "due", dueCount: 1, candidates: [{ workflowRunId: 9 }] },
      "/api/notifications": { notifications: [{ id: 4, severity: "medium" }] },
      "/api/reconciliation": { reconciliationMatches: [{ id: 3, status: "needs_review" }] },
      "/api/audit": { auditEvents: [{ id: 2, action: "local_api.source.upsert" }] },
      "/api/close-readiness": { status: "blocked", canClose: false, blockingCount: 2 },
      "/api/hai/status": { status: "ready", enabled: true, allowedCommandIds: ["run_safe_cycle", "refresh_notifications"] },
      "/api/hai/manifest": { version: "fab-hai-connector-v1", commands: [] },
      "/api/drive-wave/status": { status: "ready", archiveEnabled: true, driveTokenPresent: true },
      "/api/drive-wave/work-orders": {
        count: 1,
        summary: { needsAttachmentVerification: 1, readyToArchive: 0 },
        workOrders: [{ workOrderId: "drive-wave-7-abcd", documentId: 7, stage: "upload_and_verify_attachment" }],
      },
      "/api/connectors/google-drive/authorization": {
        status: "ready_to_authorize",
        credentialsPresent: true,
        tokenPresent: false,
        folderConfigured: true,
      },
      "/api/connectors/gmail/authorization": {
        status: "ready_to_authorize",
        credentialsPresent: true,
        tokenPresent: false,
        scannerMode: true,
        trustedSenders: ["eprintcenter@hp8.us"],
      },
      "/api/wave/setup": {
        status: "needs_mapping",
        ready: false,
        targetSystem: "waveapps_business",
        businessId: "business-1",
        accessTokenConfigured: true,
        accounts: [{ id: "account-1", name: "Current Account" }],
        mapping: { verified: false },
      },
      "/api/review": {
        summary: { reviewItems: 2, documents: 1, duplicateCandidates: 0 },
        categoryOptions: ["Operations | Office Supplies"],
        workItems: [{ id: "document-7", documentId: 7, reasons: ["manual_review_category"] }],
      },
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
    expect(result.metrics).toMatchObject({ documents: 18, pendingReview: 4, pendingReviewDocuments: 1, unreconciled: 5, exceptions: 2 });
    expect(result.resourceStates.metrics.state).toBe("live");
    expect(result.connections).toEqual(expect.arrayContaining([
      expect.objectContaining({ id: "google_drive", canSync: true, nextAction: "Sync the approved folder." }),
      expect.objectContaining({
        id: "waveapps_business",
        status: "needs_mapping",
        configured: true,
        ready: false,
        nextAction: "Map the verified bank and default expense accounts.",
      }),
      expect.objectContaining({
        id: "hai",
        status: "ready",
        allowedCommandIds: ["run_safe_cycle", "refresh_notifications"],
        details: "Governed machine control is enabled for 2 allowlisted commands.",
      }),
    ]));
    expect(result.recovery).toMatchObject({ dueCount: 1 });
    expect(result.delivery).toMatchObject({
      count: 1,
      summary: { needsAttachmentVerification: 1 },
      workOrders: [expect.objectContaining({ documentId: 7 })],
    });
    expect(result.reviews).toMatchObject({
      summary: { reviewItems: 2, documents: 1 },
      categoryOptions: ["Operations | Office Supplies"],
      workItems: [expect.objectContaining({ documentId: 7 })],
    });
    expect(result.driveAuthorization).toMatchObject({
      status: "ready_to_authorize",
      credentialsPresent: true,
      tokenPresent: false,
    });
    expect(result.gmailAuthorization).toMatchObject({
      status: "ready_to_authorize",
      scannerMode: true,
      trustedSenders: ["eprintcenter@hp8.us"],
    });
    expect(result.waveSetup).toMatchObject({
      status: "needs_mapping",
      accessTokenConfigured: true,
      businessId: "business-1",
    });
    expect(JSON.stringify(result)).not.toContain("private-token");
  });

  it("does not turn unavailable resources into reassuring zeroes", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new Error("local API offline");
    }));

    const result = await getFabControlCenter();

    expect(result.connection.connected).toBe(false);
    expect(result.metrics).toMatchObject({
      documents: null,
      pendingReview: null,
      pendingReviewDocuments: null,
      unreconciled: null,
      exceptions: null,
    });
    expect(result.resourceStates.metrics).toMatchObject({ state: "error", updatedAt: null });
    expect(result.resourceStates.exceptions.state).toBe("error");
  });

  it("retains last valid resource data as visibly stale after a partial failure", async () => {
    let failMetrics = false;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const path = new URL(String(input)).pathname;
      if (failMetrics && ["/api/dashboard", "/api/exceptions"].includes(path)) {
        return new Response(JSON.stringify({ error: "resource unavailable" }), {
          status: 503,
          headers: { "content-type": "application/json" },
        });
      }
      const value = path === "/api/dashboard"
        ? { documents: 7, pending_review: 3, unreconciled_bank_transactions: 2, unreconciled_documents: 1, failed_documents: 0 }
        : path === "/api/exceptions"
          ? { summary: { total: 3 }, exceptions: [{ id: "held-exception" }] }
          : path === "/api/health"
            ? { status: "ok" }
            : {};
      return new Response(JSON.stringify(value), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }));

    const live = await getFabControlCenter();
    failMetrics = true;
    const stale = await getFabControlCenter();

    expect(live.metrics.pendingReview).toBe(3);
    expect(stale.connection.connected).toBe(true);
    expect(stale.metrics).toMatchObject({ documents: 7, pendingReview: 3, unreconciled: 3, exceptions: 3 });
    expect(stale.exceptions).toEqual([{ id: "held-exception" }]);
    expect(stale.resourceStates.metrics).toMatchObject({ state: "stale", error: "resource unavailable" });
    expect(stale.resourceStates.exceptions.state).toBe("stale");
    expect(stale.partialErrors).toEqual(expect.arrayContaining([
      expect.objectContaining({ resource: "metrics", state: "stale" }),
      expect.objectContaining({ resource: "exceptions", state: "stale" }),
    ]));
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

  it("maps unread-scan recovery to its bounded local endpoint", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => new Response(
      JSON.stringify({ status: "completed", path: new URL(String(input)).pathname, body: JSON.parse(String(init?.body)) }),
      { status: 200, headers: { "content-type": "application/json" } },
    ));
    vi.stubGlobal("fetch", fetchMock);

    const result = await runFabOperatorCommand("reprocess_incomplete", "operator-13", { limit: 10 });

    expect(result).toMatchObject({
      status: "completed",
      path: "/api/documents/reprocess-incomplete",
      body: { limit: 10, actor: "operator-13" },
    });
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

  it("resolves a review only through its fixed local API record path", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => new Response(
      JSON.stringify({
        success: true,
        path: new URL(String(input)).pathname,
        body: JSON.parse(String(init?.body)),
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ));
    vi.stubGlobal("fetch", fetchMock);

    const result = await resolveFabReviewItem({
      reviewItemId: 42,
      status: "approved",
      resolution: "Verified against the source receipt.",
      corrections: {
        category: "Operations | Office Supplies",
        totalAmount: 42.5,
      },
    });

    expect(result).toMatchObject({
      success: true,
      path: "/api/review/42/resolve",
      body: {
        status: "approved",
        resolution: "Verified against the source receipt.",
        corrections: { category: "Operations | Office Supplies", totalAmount: 42.5 },
        learnRule: true,
        applyToMatchingVendor: false,
      },
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("installs Drive credentials and starts only the fixed authorization workflow", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => new Response(
      JSON.stringify({
        success: true,
        path: new URL(String(input)).pathname,
        body: JSON.parse(String(init?.body)),
      }),
      { status: 202, headers: { "content-type": "application/json" } },
    ));
    vi.stubGlobal("fetch", fetchMock);

    const installed = await uploadFabGoogleDriveCredentials({
      filename: "drive-client.json",
      contentBase64: "e30=",
      replace: false,
      actor: "fab_dashboard:7",
    });
    const started = await startFabGoogleDriveAuthorization("fab_dashboard:7");

    expect(installed).toMatchObject({
      path: "/api/connectors/google-drive/credentials",
      body: {
        filename: "drive-client.json",
        replace: false,
        actor: "fab_dashboard:7",
      },
    });
    expect(started).toMatchObject({
      path: "/api/connectors/google-drive/authorization/start",
      body: { actor: "fab_dashboard:7" },
    });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("installs Gmail credentials and starts only the read-only authorization workflow", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => new Response(
      JSON.stringify({
        success: true,
        path: new URL(String(input)).pathname,
        body: JSON.parse(String(init?.body)),
      }),
      { status: 202, headers: { "content-type": "application/json" } },
    ));
    vi.stubGlobal("fetch", fetchMock);

    const installed = await uploadFabGmailCredentials({
      filename: "gmail-client.json",
      contentBase64: "e30=",
      replace: false,
      actor: "fab_dashboard:7",
    });
    const started = await startFabGmailAuthorization("fab_dashboard:7");

    expect(installed).toMatchObject({
      path: "/api/connectors/gmail/credentials",
      body: {
        filename: "gmail-client.json",
        replace: false,
        actor: "fab_dashboard:7",
      },
    });
    expect(started).toMatchObject({
      path: "/api/connectors/gmail/authorization/start",
      body: { actor: "fab_dashboard:7" },
    });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("stores and validates Wave setup only through fixed local API paths", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const requestBody = JSON.parse(String(init?.body));
      const publicBody = { ...requestBody };
      delete publicBody.accessToken;
      return new Response(JSON.stringify({
        success: true,
        path: new URL(String(input)).pathname,
        body: publicBody,
        accessTokenConfigured: true,
      }), { status: 200, headers: { "content-type": "application/json" } });
    });
    vi.stubGlobal("fetch", fetchMock);

    const saved = await saveFabWaveSetup({
      targetSystem: "waveapps_business",
      accessToken: "user-owned-wave-token",
      businessId: "business-1",
      actor: "fab_dashboard:7",
    });
    const validated = await validateFabWaveSetup("waveapps_business");

    expect(saved).toMatchObject({
      path: "/api/wave/setup",
      body: {
        targetSystem: "waveapps_business",
        businessId: "business-1",
        actor: "fab_dashboard:7",
      },
      accessTokenConfigured: true,
    });
    expect(validated).toMatchObject({
      path: "/api/wave/setup/validate",
      body: { targetSystem: "waveapps_business" },
    });
    expect(JSON.stringify(saved)).not.toContain("user-owned-wave-token");
    expect(String(fetchMock.mock.calls[0]?.[1]?.body)).toContain("user-owned-wave-token");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
