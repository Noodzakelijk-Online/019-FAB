import { afterEach, describe, expect, it, vi } from "vitest";
import {
  createFabBackup,
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
          { id: "freshdesk", label: "Freshdesk", status: "ready", configured: true },
          { id: "waveapps_business", label: "Wave - Noodzakelijk Online", status: "attention", configured: false },
        ],
      },
      "/api/sources/readiness": {
        sources: [
          { source: "google_drive", enabled: true, canSync: true, nextAction: "Sync the approved folder." },
          {
            source: "freshdesk",
            enabled: true,
            canSync: true,
            mode: "financial_ticket_read_only",
            connectorProfile: {
              enabled: true,
              profileId: "scan_to_folder_v1",
              ticketMutation: "not_executed",
            },
          },
        ],
      },
      "/api/sources": { sources: [{ source_type: "google_drive", status: "connected", updated_at: "2026-07-15T08:00:00Z" }] },
      "/api/workflows": {
        workflowRuns: [{
          id: 10,
          status: "completed",
          trigger_source: "local_autonomous_cycle",
          finished_at: "2026-07-25T09:15:00Z",
        }],
      },
      "/api/workflows/recovery": { status: "due", dueCount: 1, candidates: [{ workflowRunId: 9 }] },
      "/api/backups": {
        backupDir: "C:\\private\\backups",
        restoreConfirmationPhrase: "RESTORE FAB LOCAL LEDGER",
        schedule: {
          status: "current",
          due: false,
          intervalHours: 24,
          lastSuccessfulAt: "2026-07-25T08:00:00Z",
          nextDueAt: "2026-07-26T08:00:00Z",
          latestBackupFilename: "fab-recovery-package_20260725.zip",
          latestLedgerSha256: "a".repeat(64),
          sourceEvidenceStatus: "complete",
          sourceEvidenceDocuments: 18,
          sourceEvidenceFiles: 18,
          sourceEvidenceBytes: 4096,
          sourceEvidenceGaps: 0,
        },
        backups: [{
          backupFilename: "fab-recovery-package_20260725.zip",
          backupPath: "C:\\private\\backups\\fab-recovery-package_20260725.zip",
          status: "valid",
          createdAt: "2026-07-25T08:00:00Z",
          ledgerBytes: 2048,
          ledgerSha256: "a".repeat(64),
          sizeBytes: 6144,
          format: "fab-recovery-package-v2",
          sourceEvidenceStatus: "complete",
          sourceEvidenceDocuments: 18,
          sourceEvidenceFiles: 18,
          sourceEvidenceBytes: 4096,
          sourceEvidenceGaps: 0,
        }],
      },
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
        workOrders: [{
          workOrderId: "drive-wave-7-abcd",
          documentId: 7,
          stage: "upload_and_verify_attachment",
          actionRequired: "Verify the attachment.",
          source: {
            filename: "receipt.pdf",
            mimeType: "application/pdf",
            provider: "google_drive",
            sha256: "abc123",
            attachmentId: "private-provider-attachment",
            localPath: "C:\\private\\receipt.pdf",
          },
          wave: {
            externalTransactionId: null,
            targetSystem: "waveapps_business",
            expectedFields: { vendor: "Example" },
          },
          archivePlan: {
            canArchive: false,
            reasons: ["wave_attachment_evidence_missing"],
            evidenceDigest: "private-evidence-digest",
          },
          reviews: { blocking: 1, open: 1, reasons: ["manual_review_category"] },
          browserExecution: { transactionListUrl: "https://example.test/private" },
          evidence: { template: { businessId: "private-business-id" } },
        }],
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
      "/api/wave/receipt-executor/status": {
        status: "not_connected",
        enabled: true,
        ready: false,
        nextAction: "Connect a supervised HAI or browser executor using the local FAB manifest.",
        missingCapabilities: ["receipt_upload", "receipt_download"],
      },
      "/api/review": {
        summary: {
          reviewItems: 3,
          documents: 2,
          postingBlockedDocuments: 1,
          postingBlockedReviewItems: 2,
          evidenceOnlyDocuments: 1,
          evidenceOnlyReviewItems: 1,
          duplicateCandidates: 0,
        },
        categoryOptions: ["Operations | Office Supplies"],
        workItems: [{
          id: "document-7",
          documentId: 7,
          reasons: ["manual_review_category"],
          reviewPath: "/documents/7",
          document: {
            filename: "receipt.pdf",
            vendorName: "Example",
            category: "Manual Review",
            categorySuggestion: {
              category: "Office Supplies",
              confidenceScore: 0.97,
              rationale: "Exact vendor match.",
              privateModelTrace: "omit-this",
            },
            ocrExcerpt: "Source evidence",
            privateInternalMetadata: { raw: true },
          },
          duplicateCandidates: [{
            id: 11,
            candidateDocumentId: 6,
            matchType: "fuzzy_document_match",
            confidenceScore: 0.96,
            matchedIdentityFields: ["vendor", "date", "amount", "transaction_reference"],
            conflictingIdentityFields: [],
            comparableFields: 4,
            similarityScore: 1,
            currentIdentity: {
              vendor: "example",
              date: "2026 07 01",
              amount: "42.00",
              transactionReference: "tx1234",
              privateReference: "omit-this",
            },
            candidateIdentity: {
              vendor: "example",
              date: "2026 07 01",
              amount: "42.00",
              transactionReference: "tx1234",
            },
            document: {
              filename: "possible-duplicate.pdf",
              vendorName: "Example",
              transactionDate: "2026-07-01",
              totalAmount: 42,
              ocrExcerpt: "omit duplicate OCR",
            },
            evidence: { duplicateFingerprint: "omit-this" },
          }],
          reviewItems: [{
            id: 9,
            reason: "manual_review_category",
            details: "Verify category.",
            createdAt: "2026-07-24T09:00:00Z",
            correctedData: { private: true },
          }],
        }],
      },
      "/api/master-ledger": {
        summary: { readyForApproval: 2 },
        rows: [
          { recordDate: "2026-06-30", amount: 42, vendorName: "Private ledger vendor" },
          { recordDate: "2026-07-19", amount: 12, vendorName: "Private latest vendor" },
        ],
      },
      "/api/bank-transactions": {
        bankTransactions: [
          { id: 90, amount: -125.5, currency: "EUR", description: "Private bank line" },
          { id: 91, amount: 20, currency: "EUR", description: "Private bank line" },
          { id: 92, amount: 8.25, currency: "GBP", description: "Private bank line" },
        ],
      },
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input));
      const fixture = fixtures[url.pathname];
      return new Response(JSON.stringify(fixture ?? {}), {
        status: fixture ? 200 : 404,
        headers: { "content-type": "application/json" },
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await getFabControlCenter();

    expect(result.connection.connected).toBe(true);
    expect(result.metrics).toMatchObject({
      documents: 18,
      pendingReview: 4,
      pendingReviewDocuments: 2,
      postingBlockedReviewDocuments: 1,
      unreconciled: 5,
      exceptions: 2,
    });
    expect(result.resourceStates.metrics.state).toBe("live");
    expect(result.decisionContext).toMatchObject({
      lastSafeCycleAt: "2026-07-25T09:15:00Z",
      latestWorkflowStatus: "completed",
      dataThroughDate: "2026-07-19",
      sourceCount: 1,
      readySourceCount: 1,
      latestSourceSyncAt: "2026-07-15T08:00:00Z",
      unreconciledAmountByCurrency: { EUR: 145.5, GBP: 8.25 },
      highPriorityExceptions: 1,
      ledgerReadyForApproval: 2,
    });
    expect(result.decisionContext.oldestReviewAgeHours).toBeGreaterThan(0);
    expect(result.connections).toEqual(expect.arrayContaining([
      expect.objectContaining({ id: "google_drive", canSync: true, nextAction: "Sync the approved folder." }),
      expect.objectContaining({
        id: "freshdesk",
        mode: "financial_ticket_read_only",
        connectorProfile: expect.objectContaining({
          profileId: "scan_to_folder_v1",
          ticketMutation: "not_executed",
        }),
      }),
      expect.objectContaining({
        id: "waveapps_business",
        status: "needs_mapping",
        configured: true,
        ready: false,
        nextAction: "Map the verified funding account and every FAB category currently in use.",
      }),
      expect.objectContaining({
        id: "wave_receipt_executor",
        status: "not_connected",
        configured: true,
        ready: false,
        missingCapabilities: ["receipt_upload", "receipt_download"],
      }),
      expect.objectContaining({
        id: "hai",
        status: "ready",
        allowedCommandIds: ["run_safe_cycle", "refresh_notifications"],
        details: "Governed machine control is enabled for 2 allowlisted commands.",
      }),
    ]));
    expect(result.recovery).toMatchObject({ dueCount: 1 });
    expect(result.backups).toMatchObject({
      schedule: {
        status: "current",
        sourceEvidenceStatus: "complete",
        sourceEvidenceDocuments: 18,
      },
      backups: [expect.objectContaining({
        backupFilename: "fab-recovery-package_20260725.zip",
        status: "valid",
        sourceEvidenceFiles: 18,
      })],
    });
    expect(result.delivery).toMatchObject({
      count: 1,
      summary: { needsAttachmentVerification: 1 },
      workOrders: [expect.objectContaining({
        documentId: 7,
        source: {
          filename: "receipt.pdf",
          mimeType: "application/pdf",
          provider: "google_drive",
          sha256: "abc123",
        },
        archivePlan: {
          canArchive: false,
          reasons: ["wave_attachment_evidence_missing"],
        },
      })],
    });
    expect(result.reviews).toMatchObject({
      summary: {
        reviewItems: 3,
        documents: 2,
        postingBlockedDocuments: 1,
        evidenceOnlyDocuments: 1,
      },
      categoryOptions: ["Operations | Office Supplies"],
      workItems: [expect.objectContaining({
        documentId: 7,
        document: expect.objectContaining({
          filename: "receipt.pdf",
          vendorName: "Example",
          ocrExcerpt: "Source evidence",
          categorySuggestion: {
            category: "Office Supplies",
            confidenceScore: 0.97,
            rationale: "Exact vendor match.",
          },
        }),
        duplicateCandidates: [
          expect.objectContaining({
            id: 11,
            candidateDocumentId: 6,
            matchType: "fuzzy_document_match",
            matchedIdentityFields: ["vendor", "date", "amount", "transaction_reference"],
            currentIdentity: {
              vendor: "example",
              date: "2026 07 01",
              amount: "42.00",
              transactionReference: "tx1234",
            },
            document: {
              filename: "possible-duplicate.pdf",
              vendorName: "Example",
              transactionDate: "2026-07-01",
              totalAmount: 42,
            },
          }),
        ],
        reviewItems: [
          expect.objectContaining({
            id: 9,
            reason: "manual_review_category",
            details: "Verify category.",
          }),
        ],
      })],
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
    expect(result.waveReceiptExecutor).toMatchObject({
      status: "not_connected",
      enabled: true,
      ready: false,
    });
    expect(fetchMock.mock.calls.some(([input]) => {
      const url = new URL(String(input));
      return url.pathname === "/api/review" && url.searchParams.get("limit") === "500";
    })).toBe(true);
    const serialized = JSON.stringify(result);
    expect(serialized).not.toContain("private-token");
    expect(serialized).not.toContain("private-provider-attachment");
    expect(serialized).not.toContain("C:\\private\\receipt.pdf");
    expect(serialized).not.toContain("private-evidence-digest");
    expect(serialized).not.toContain("private-business-id");
    expect(serialized).not.toContain("privateModelTrace");
    expect(serialized).not.toContain("privateReference");
    expect(serialized).not.toContain("privateInternalMetadata");
    expect(serialized).not.toContain("omit duplicate OCR");
    expect(serialized).not.toContain("duplicateFingerprint");
    expect(serialized).not.toContain("correctedData");
    expect(serialized).not.toContain("Private ledger vendor");
    expect(serialized).not.toContain("Private latest vendor");
    expect(serialized).not.toContain("Private bank line");
    expect(serialized).not.toContain("C:\\private\\backups");
    expect(serialized).not.toContain("RESTORE FAB LOCAL LEDGER");
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
      postingBlockedReviewDocuments: null,
      unreconciled: null,
      exceptions: null,
    });
    expect(result.decisionContext).toMatchObject({
      lastSafeCycleAt: null,
      dataThroughDate: null,
      sourceCount: null,
      readySourceCount: null,
      latestSourceSyncAt: null,
      unreconciledAmountByCurrency: null,
      ledgerReadyForApproval: null,
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

  it("creates only a source-complete backup through the fixed local endpoint", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => new Response(
      JSON.stringify({
        success: true,
        status: "created",
        backupFilename: "fab-recovery-package.zip",
        backupPath: "C:\\private\\backups\\fab-recovery-package.zip",
        manifest: {
          format: "fab-recovery-package-v2",
          createdAt: "2026-07-25T10:00:00Z",
          ledgerBytes: 2048,
          ledgerSha256: "b".repeat(64),
          configSummary: { backupDir: "C:\\private\\backups" },
          sourceEvidence: {
            coverageStatus: "complete",
            totalDocuments: 18,
            includedDocuments: 18,
            includedFiles: 18,
            includedBytes: 4096,
            gapCount: 0,
            entries: [{ originalFilename: "private.pdf" }],
          },
        },
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ));
    vi.stubGlobal("fetch", fetchMock);

    const result = await createFabBackup("operator-15");

    expect(result).toMatchObject({
      success: true,
      status: "created",
      backupFilename: "fab-recovery-package.zip",
      manifest: {
        format: "fab-recovery-package-v2",
        sourceEvidence: {
          coverageStatus: "complete",
          includedDocuments: 18,
          gapCount: 0,
        },
      },
    });
    const [input, init] = fetchMock.mock.calls[0];
    expect(new URL(String(input)).pathname).toBe("/api/backups");
    expect(JSON.parse(String(init?.body))).toEqual({
      actor: "operator-15",
      note: "Created from the FAB operator dashboard.",
      requireCompleteSourceEvidence: true,
    });
    expect(JSON.stringify(result)).not.toContain("C:\\private\\backups");
    expect(JSON.stringify(result)).not.toContain("private.pdf");
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

  it("maps review reassessment to its backed-up local endpoint", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => new Response(
      JSON.stringify({ status: "completed", path: new URL(String(input)).pathname, body: JSON.parse(String(init?.body)) }),
      { status: 200, headers: { "content-type": "application/json" } },
    ));
    vi.stubGlobal("fetch", fetchMock);

    const result = await runFabOperatorCommand("reprocess_review_queue", "operator-14", { limit: 20 });

    expect(result).toMatchObject({
      status: "completed",
      path: "/api/documents/reprocess-review-queue",
      body: { limit: 20, actor: "operator-14" },
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
        duplicateCandidateId: 7,
      },
    });

    expect(result).toMatchObject({
      success: true,
      path: "/api/review/42/resolve",
      body: {
        status: "approved",
        resolution: "Verified against the source receipt.",
        corrections: {
          category: "Operations | Office Supplies",
          totalAmount: 42.5,
          duplicateCandidateId: 7,
        },
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
