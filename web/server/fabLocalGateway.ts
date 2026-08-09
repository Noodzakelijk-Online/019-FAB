import { ENV } from "./_core/env";

type JsonRecord = Record<string, unknown>;

export type FabDataState = "live" | "stale" | "unavailable" | "error";

export type FabResourceState = {
  state: FabDataState;
  checkedAt: string;
  updatedAt: string | null;
  error: string | null;
};

export const FAB_OPERATOR_COMMAND_IDS = [
  "run_safe_cycle",
  "engage_emergency_stop",
  "clear_emergency_stop",
  "rescan_intake",
  "process_imported",
  "reprocess_incomplete",
  "reprocess_review_queue",
  "sync_sources",
  "run_due_recovery",
  "run_reconciliation",
  "refresh_notifications",
  "run_due_reports",
  "assess_compliance",
] as const;

export type FabOperatorCommandId = typeof FAB_OPERATOR_COMMAND_IDS[number];

export type FabControlCenter = {
  connection: {
    connected: boolean;
    status: string;
    endpoint: string;
    authConfigured: boolean;
    checkedAt: string;
    latencyMs: number | null;
    error: string | null;
  };
  metrics: {
    documents: number | null;
    pendingReview: number | null;
    pendingReviewDocuments: number | null;
    postingBlockedReviewDocuments: number | null;
    unreconciled: number | null;
    unreconciledDocuments: number | null;
    unreconciledBankTransactions: number | null;
    exceptions: number | null;
    failedDocuments: number | null;
  };
  decisionContext: {
    lastSafeCycleAt: string | null;
    latestWorkflowStatus: string | null;
    dataThroughDate: string | null;
    sourceCount: number | null;
    readySourceCount: number | null;
    latestSourceSyncAt: string | null;
    unreconciledAmountByCurrency: Record<string, number> | null;
    oldestReviewAgeHours: number | null;
    highPriorityExceptions: number | null;
    ledgerReadyForApproval: number | null;
  };
  health: JsonRecord;
  autonomy: JsonRecord;
  closeReadiness: JsonRecord;
  delivery: {
    status: JsonRecord;
    summary: JsonRecord;
    workOrders: JsonRecord[];
    count: number | null;
  };
  reviews: {
    workItems: JsonRecord[];
    categoryOptions: string[];
    summary: JsonRecord;
  };
  gmailAuthorization: JsonRecord;
  driveAuthorization: JsonRecord;
  waveSetup: JsonRecord;
  waveReceiptExecutor: JsonRecord;
  cloudAccess: JsonRecord;
  exceptions: JsonRecord[];
  exceptionSummary: JsonRecord;
  connections: JsonRecord[];
  workflows: JsonRecord[];
  recovery: JsonRecord;
  backups: {
    backups: JsonRecord[];
    schedule: JsonRecord;
    verificationMode: string | null;
  };
  notifications: JsonRecord[];
  reconciliation: JsonRecord[];
  activity: JsonRecord[];
  hai: {
    status: JsonRecord;
    manifest: JsonRecord;
  };
  resourceStates: Record<FabResourceKey, FabResourceState>;
  partialErrors: Array<{ resource: FabResourceKey; error: string; state: FabDataState; updatedAt: string | null }>;
};

const DEFAULT_FAB_LOCAL_API_URL = "http://127.0.0.1:5001";
const LOOPBACK_HOSTS = new Set(["127.0.0.1", "localhost", "::1", "[::1]"]);
const MAX_CONCURRENT_READS = 4;
// Start the costliest independent reads first so the bounded worker pool does
// not leave a long-running request at the end of the dashboard refresh.
const READ_PATHS = {
  backups: "/api/backups?limit=5&verify=false",
  autonomy: "/api/autonomy/plan?limit=25",
  reviewQueue: "/api/review?status=open&limit=200&view=summary",
  exceptions: "/api/exceptions?limit=25&includeEntities=true",
  driveWaveWorkOrders: "/api/drive-wave/work-orders?limit=200&view=summary",
  health: "/api/health",
  closeReadiness: "/api/close-readiness",
  recovery: "/api/workflows/recovery?limit=10",
  liveness: "/api/live",
  waveSetup: "/api/wave/setup",
  driveWaveStatus: "/api/drive-wave/status",
  workflows: "/api/workflows?limit=10",
  masterLedger: "/api/master-ledger?limit=250&summaryOnly=true",
  metrics: "/api/dashboard",
  notifications: "/api/notifications?limit=10",
  settings: "/api/settings",
  bankTransactions: "/api/bank-transactions?status=unreconciled&limit=250",
  reconciliation: "/api/reconciliation?limit=10",
  activity: "/api/audit?limit=12",
  sources: "/api/sources?limit=50",
  waveReceiptExecutor: "/api/wave/receipt-executor/status",
  sourceReadiness: "/api/sources/readiness",
  driveAuthorization: "/api/connectors/google-drive/authorization",
  haiStatus: "/api/hai/status",
  haiManifest: "/api/hai/manifest",
  cloudStatus: "/api/cloud/status",
  gmailAuthorization: "/api/connectors/gmail/authorization",
} as const;

export type FabResourceKey = keyof typeof READ_PATHS;

const READ_TIMEOUT_MS: Partial<Record<FabResourceKey, number>> = {
  health: 12_000,
  autonomy: 15_000,
  backups: 12_000,
  driveWaveWorkOrders: 12_000,
  cloudStatus: 3_000,
};

const resourceCache = new Map<FabResourceKey, { value: JsonRecord; updatedAt: string }>();
const CONTROL_CENTER_CACHE_TTL_MS = 2_000;
let controlCenterSnapshot: { value: FabControlCenter; expiresAt: number } | null = null;
let controlCenterInFlight: Promise<FabControlCenter> | null = null;
let controlCenterCacheGeneration = 0;

const COMMAND_PATHS: Record<FabOperatorCommandId, { path: string; body: JsonRecord; method?: "POST" | "DELETE" }> = {
  run_safe_cycle: { path: "/api/autonomy/run", body: { limit: 25, includeWavePlan: true, includeWaveSync: true, includeConnectorSync: true } },
  engage_emergency_stop: { path: "/api/autonomy/emergency-stop", body: { reason: "Operator stopped autonomous processing from the FAB dashboard." } },
  clear_emergency_stop: { path: "/api/autonomy/emergency-stop", method: "DELETE", body: {} },
  rescan_intake: { path: "/api/intake/rescan", body: {} },
  process_imported: { path: "/api/documents/process-imported", body: { limit: 25 } },
  reprocess_incomplete: { path: "/api/documents/reprocess-incomplete", body: { limit: 25 } },
  reprocess_review_queue: { path: "/api/documents/reprocess-review-queue", body: { limit: 25 } },
  sync_sources: { path: "/api/sources/sync", body: {} },
  run_due_recovery: { path: "/api/workflows/recovery/run-due", body: { limit: 5 } },
  run_reconciliation: { path: "/api/reconciliation/run", body: { limit: 100 } },
  refresh_notifications: { path: "/api/notifications/refresh", body: {} },
  run_due_reports: { path: "/api/report-runs/run-due", body: {} },
  assess_compliance: { path: "/api/compliance/assessments", body: {} },
};

export function getFabLocalApiBaseUrl(
  rawUrl = ENV.fabLocalApiUrl,
  insecureHosts: readonly string[] = ENV.fabLocalApiInsecureHosts,
): URL {
  const parsed = new URL((rawUrl || DEFAULT_FAB_LOCAL_API_URL).trim().replace(/\/+$/, ""));
  if (!new Set(["http:", "https:"]).has(parsed.protocol)) {
    throw new Error("FAB_LOCAL_API_URL must use http or https");
  }
  if (parsed.username || parsed.password) {
    throw new Error("FAB_LOCAL_API_URL must not contain credentials");
  }
  const hostname = parsed.hostname.toLowerCase();
  if (
    parsed.protocol !== "https:"
    && !LOOPBACK_HOSTS.has(hostname)
    && !insecureHosts.includes(hostname)
  ) {
    throw new Error("Non-loopback FAB_LOCAL_API_URL values must use https");
  }
  return parsed;
}

export async function fabLocalRequest(
  path: string,
  init: RequestInit = {},
  options: { baseUrl?: string; token?: string; timeoutMs?: number } = {},
): Promise<JsonRecord> {
  const baseUrl = getFabLocalApiBaseUrl(options.baseUrl);
  const target = new URL(path, `${baseUrl.toString().replace(/\/$/, "")}/`);
  if (target.origin !== baseUrl.origin) {
    throw new Error("FAB local API path escaped the configured origin");
  }
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), options.timeoutMs ?? 8_000);
  const token = options.token ?? ENV.fabLocalApiToken;
  const headers = new Headers(init.headers);
  headers.set("accept", "application/json");
  if (init.body) headers.set("content-type", "application/json");
  if (token) headers.set("authorization", `Bearer ${token}`);

  try {
    const response = await fetch(target, { ...init, headers, signal: controller.signal });
    const body = await response.json().catch(() => ({})) as JsonRecord;
    if (!response.ok) {
      throw new Error(stringValue(body.error) || `FAB local API returned ${response.status}`);
    }
    const method = String(init.method || "GET").toUpperCase();
    if (method !== "GET" && method !== "HEAD") {
      invalidateFabControlCenterSnapshot();
    }
    return body;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("FAB local API request timed out");
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

async function settleFabReads(
  entries: Array<[FabResourceKey, string]>,
): Promise<Array<PromiseSettledResult<JsonRecord>>> {
  const results = new Array<PromiseSettledResult<JsonRecord>>(entries.length);
  let nextIndex = 0;
  const workerCount = Math.min(MAX_CONCURRENT_READS, entries.length);
  await Promise.all(Array.from({ length: workerCount }, async () => {
    while (nextIndex < entries.length) {
      const index = nextIndex;
      nextIndex += 1;
      try {
        const [resource, path] = entries[index];
        results[index] = {
          status: "fulfilled",
          value: await fabLocalRequest(path, {}, { timeoutMs: READ_TIMEOUT_MS[resource] }),
        };
      } catch (reason) {
        results[index] = { status: "rejected", reason };
      }
    }
  }));
  return results;
}

export async function getFabControlCenter(): Promise<FabControlCenter> {
  const now = Date.now();
  if (controlCenterSnapshot && controlCenterSnapshot.expiresAt > now) {
    return controlCenterSnapshot.value;
  }
  if (controlCenterInFlight) return controlCenterInFlight;

  const generation = controlCenterCacheGeneration;
  const request = buildFabControlCenter();
  controlCenterInFlight = request;
  try {
    const value = await request;
    if (value.connection.connected && generation === controlCenterCacheGeneration) {
      controlCenterSnapshot = {
        value,
        expiresAt: Date.now() + CONTROL_CENTER_CACHE_TTL_MS,
      };
    }
    return value;
  } finally {
    if (controlCenterInFlight === request) controlCenterInFlight = null;
  }
}

async function buildFabControlCenter(): Promise<FabControlCenter> {
  const checkedAt = new Date().toISOString();
  const startedAt = Date.now();
  let endpoint = DEFAULT_FAB_LOCAL_API_URL;
  try {
    endpoint = getFabLocalApiBaseUrl().toString().replace(/\/$/, "");
  } catch (error) {
    return disconnectedControlCenter(
      endpoint,
      checkedAt,
      error instanceof Error ? error.message : "Invalid FAB local API configuration",
    );
  }

  const entries = Object.entries(READ_PATHS) as Array<[FabResourceKey, string]>;
  const settled = await settleFabReads(entries);
  const resources: Partial<Record<FabResourceKey, JsonRecord>> = {};
  const resourceStates = {} as Record<FabResourceKey, FabResourceState>;
  const partialErrors: FabControlCenter["partialErrors"] = [];
  settled.forEach((result, index) => {
    const resource = entries[index][0];
    if (result.status === "fulfilled") {
      resources[resource] = result.value;
      resourceCache.set(resource, { value: result.value, updatedAt: checkedAt });
      resourceStates[resource] = { state: "live", checkedAt, updatedAt: checkedAt, error: null };
      return;
    }
    const error = result.reason instanceof Error ? result.reason.message : "Request failed";
    const cached = resourceCache.get(resource);
    if (cached) {
      resources[resource] = cached.value;
      resourceStates[resource] = { state: "stale", checkedAt, updatedAt: cached.updatedAt, error };
    } else {
      resourceStates[resource] = { state: "error", checkedAt, updatedAt: null, error };
    }
    partialErrors.push({
      resource,
      error,
      state: resourceStates[resource].state,
      updatedAt: resourceStates[resource].updatedAt,
    });
  });

  const connected = resourceStates.liveness.state === "live";

  const metrics = resources.metrics || {};
  const reviewSummary = asRecord(resources.reviewQueue?.summary) || {};
  const exceptionsPayload = resources.exceptions || {};
  const settings = resources.settings || {};
  const sourceReadiness = resources.sourceReadiness || {};
  const waveSetup = resources.waveSetup || {};
  const waveReceiptExecutor = resources.waveReceiptExecutor || {};
  const cloudAccess = resources.cloudStatus || {};
  const registeredSources = arrayValue(resources.sources?.sources);
  const workflowRuns = arrayValue(resources.workflows?.workflowRuns);
  const reviewWorkItems = arrayValue(resources.reviewQueue?.workItems);
  const bankTransactions = arrayValue(resources.bankTransactions?.bankTransactions);
  const haiAllowedCommandIds = stringArray(resources.haiStatus?.allowedCommandIds);
  const sourceConnections = arrayValue(settings.sources).map((source) => {
    const sourceId = stringValue(source.id);
    const syncPlan = arrayValue(sourceReadiness.sources).find((item) => stringValue(item.source) === sourceId);
    const account = registeredSources.find((item) => {
      const sourceType = stringValue(item.source_type || item.sourceType);
      return sourceType === sourceId || sourceType === sourceId.replace("waveapps_", "waveapps");
    });
    const baseConnection = {
      ...source,
      canSync: Boolean(syncPlan?.canSync),
      enabled: syncPlan ? Boolean(syncPlan.enabled) : Boolean(source.configured),
      mode: syncPlan?.mode || source.mode || null,
      scannerProfile: syncPlan?.scannerProfile || null,
      connectorProfile: syncPlan?.connectorProfile || null,
      nextAction: syncPlan?.nextAction || null,
      lastSyncAt: account?.last_sync_at || account?.updated_at || null,
      accountStatus: account?.status || null,
    };
    if (sourceId !== "waveapps_business") return baseConnection;
    const setupStatus = stringValue(waveSetup.status, stringValue(source.status, "not_configured"));
    return {
      ...baseConnection,
      status: setupStatus,
      ready: waveSetup.ready === true,
      configured: waveSetup.accessTokenConfigured === true && Boolean(waveSetup.businessId),
      details: waveSetup.ready === true
        ? "Wave business and account mappings were verified from the live chart of accounts."
        : "Connect Wave, validate the business, and map the posting accounts.",
      nextAction: stringValue(asRecord(waveSetup.activation)?.nextAction, waveSetupNextAction(setupStatus)),
    };
  });
  const latestSafeCycle = workflowRuns.find((workflow) => (
    stringValue(workflow.status).toLowerCase() === "completed"
      && ["local_autonomous_cycle", "autonomy_run"].includes(
        stringValue(workflow.trigger_source, stringValue(workflow.triggerSource)).toLowerCase(),
      )
  ));

  return {
    connection: {
      connected,
      status: connected ? stringValue(resources.health?.status, "connected") : "disconnected",
      endpoint,
      authConfigured: Boolean(ENV.fabLocalApiToken),
      checkedAt,
      latencyMs: connected ? Date.now() - startedAt : null,
      error: connected ? null : resourceStates.liveness.error || "FAB local API is unavailable",
    },
    metrics: {
      documents: nullableNumber(metrics.documents),
      pendingReview: nullableNumber(metrics.pending_review),
      pendingReviewDocuments: nullableNumber(reviewSummary.documents),
      postingBlockedReviewDocuments: nullableNumber(reviewSummary.postingBlockedDocuments),
      unreconciled: sumNullable(metrics.unreconciled_bank_transactions, metrics.unreconciled_documents),
      unreconciledDocuments: nullableNumber(metrics.unreconciled_documents),
      unreconciledBankTransactions: nullableNumber(metrics.unreconciled_bank_transactions),
      exceptions: nullableNumber(asRecord(exceptionsPayload.summary)?.total),
      failedDocuments: nullableNumber(metrics.failed_documents),
    },
    decisionContext: {
      lastSafeCycleAt: latestSafeCycle
        ? nullableString(latestSafeCycle.finished_at || latestSafeCycle.finishedAt || latestSafeCycle.updated_at || latestSafeCycle.updatedAt)
        : null,
      latestWorkflowStatus: workflowRuns.length ? nullableString(workflowRuns[0].status) : null,
      dataThroughDate: resourceStates.masterLedger.state === "live" || resourceStates.masterLedger.state === "stale"
        ? nullableString(resources.masterLedger?.dataThroughDate)
        : null,
      sourceCount: resourceStates.sources.state === "live" || resourceStates.sources.state === "stale"
        ? registeredSources.length
        : null,
      readySourceCount: resourceStates.sources.state === "live" || resourceStates.sources.state === "stale"
        ? registeredSources.filter((source) => ["connected", "ready", "ok"].includes(
          stringValue(source.status).toLowerCase(),
        )).length
        : null,
      latestSourceSyncAt: resourceStates.sources.state === "live" || resourceStates.sources.state === "stale"
        ? latestDate(registeredSources.map((source) => source.last_sync_at || source.lastSyncAt || source.updated_at || source.updatedAt))
        : null,
      unreconciledAmountByCurrency: resourceStates.bankTransactions.state === "live" || resourceStates.bankTransactions.state === "stale"
        ? amountByCurrency(bankTransactions)
        : null,
      oldestReviewAgeHours: resourceStates.reviewQueue.state === "live" || resourceStates.reviewQueue.state === "stale"
        ? oldestReviewAgeHours(reviewWorkItems, checkedAt)
        : null,
      highPriorityExceptions: resourceStates.exceptions.state === "live" || resourceStates.exceptions.state === "stale"
        ? nullableNumber(asRecord(asRecord(exceptionsPayload.summary)?.bySeverity)?.high)
        : null,
      ledgerReadyForApproval: resourceStates.masterLedger.state === "live" || resourceStates.masterLedger.state === "stale"
        ? nullableNumber(asRecord(resources.masterLedger?.summary)?.readyForApproval)
        : null,
    },
    health: resources.health || {},
    autonomy: resources.autonomy || {},
    closeReadiness: resources.closeReadiness || {},
    delivery: {
      status: resources.driveWaveStatus || {},
      summary: asRecord(resources.driveWaveWorkOrders?.summary) || {},
      workOrders: arrayValue(resources.driveWaveWorkOrders?.workOrders).map(projectDeliveryWorkOrder),
      count: nullableNumber(resources.driveWaveWorkOrders?.count),
    },
    reviews: {
      workItems: arrayValue(resources.reviewQueue?.workItems).map(projectReviewWorkItem),
      categoryOptions: stringArray(resources.reviewQueue?.categoryOptions),
      summary: asRecord(resources.reviewQueue?.summary) || {},
    },
    gmailAuthorization: resources.gmailAuthorization || {},
    driveAuthorization: resources.driveAuthorization || {},
    waveSetup,
    waveReceiptExecutor,
    cloudAccess,
    exceptions: arrayValue(exceptionsPayload.exceptions),
    exceptionSummary: asRecord(exceptionsPayload.summary) || {},
    connections: [
      ...sourceConnections,
      {
        id: "wave_receipt_executor",
        label: "Wave receipt session",
        status: stringValue(waveReceiptExecutor.status, "not_connected"),
        configured: waveReceiptExecutor.enabled === true,
        ready: waveReceiptExecutor.ready === true,
        details: waveReceiptExecutor.ready === true
          ? "A fresh user-owned browser executor can upload and read receipts back into FAB verification."
          : "Non-secret HAI/browser bridge for Wave receipt upload and exact attachment readback.",
        nextAction: stringValue(
          waveReceiptExecutor.nextAction,
          "Connect a supervised HAI or browser executor using the local FAB manifest.",
        ),
        lastSyncAt: waveReceiptExecutor.lastSeenAt || null,
        missingCapabilities: stringArray(waveReceiptExecutor.missingCapabilities),
      },
      {
        id: "hai",
        label: "HAI connector",
        status: stringValue(resources.haiStatus?.status, "unavailable"),
        configured: Boolean(resources.haiStatus?.enabled),
        ready: resources.haiStatus?.status === "ready",
        details: resources.haiStatus?.status === "ready"
          ? `Governed machine control is enabled for ${haiAllowedCommandIds.length} allowlisted commands.`
          : "Governed machine-control contract for safe local FAB commands.",
        allowedCommandIds: haiAllowedCommandIds,
      },
      {
        id: "ngrok_cloud",
        label: "FAB cloud access",
        status: stringValue(cloudAccess.status, "not_running"),
        configured: cloudAccess.configured === true,
        ready: cloudAccess.active === true,
        details: cloudAccess.active === true
          ? "Authenticated HTTPS access is verified for the FAB API and HAI manifest."
          : "Project-owned ngrok access for the authenticated FAB API and HAI connector.",
        nextAction: stringValue(
          cloudAccess.nextAction,
          "Run Start-FAB-Ngrok.cmd after configuring a dedicated FAB endpoint.",
        ),
        lastSyncAt: cloudAccess.verifiedAt || null,
        publicUrl: cloudAccess.publicUrl || null,
        authMode: cloudAccess.authMode || null,
      },
    ],
    workflows: workflowRuns,
    recovery: resources.recovery || {},
    backups: projectBackups(resources.backups),
    notifications: arrayValue(resources.notifications?.notifications),
    reconciliation: arrayValue(resources.reconciliation?.reconciliationMatches),
    activity: arrayValue(resources.activity?.auditEvents),
    hai: {
      status: resources.haiStatus || {},
      manifest: resources.haiManifest || {},
    },
    resourceStates,
    partialErrors,
  };
}

export function resetFabControlCenterCacheForTests() {
  resourceCache.clear();
  invalidateFabControlCenterSnapshot();
}

function invalidateFabControlCenterSnapshot() {
  controlCenterSnapshot = null;
  controlCenterInFlight = null;
  controlCenterCacheGeneration += 1;
}

export async function runFabOperatorCommand(
  commandId: FabOperatorCommandId,
  actor: string,
  payload: JsonRecord = {},
): Promise<JsonRecord> {
  const command = COMMAND_PATHS[commandId];
  const safeActor = actor.trim().slice(0, 200) || "fab_dashboard";
  return fabLocalRequest(command.path, {
    method: command.method || "POST",
    body: JSON.stringify({ ...command.body, ...payload, actor: safeActor }),
  });
}

export async function createFabBackup(actor: string): Promise<JsonRecord> {
  const response = await fabLocalRequest("/api/backups", {
    method: "POST",
    body: JSON.stringify({
      actor: actor.trim().slice(0, 200) || "fab_dashboard:local_operator",
      note: "Created from the FAB operator dashboard.",
      requireCompleteSourceEvidence: true,
    }),
  }, { timeoutMs: 120_000 });
  const manifest = selectFields(response.manifest, [
    "createdAt",
    "format",
    "ledgerBytes",
    "ledgerSha256",
  ]);
  manifest.sourceEvidence = selectFields(asRecord(response.manifest)?.sourceEvidence, [
    "coverageStatus",
    "gapCount",
    "includedBytes",
    "includedDocuments",
    "includedFiles",
    "totalDocuments",
  ]);
  return {
    ...selectFields(response, ["backupFilename", "status", "success"]),
    manifest,
  };
}

export async function createFabSupportBundle(actor: string): Promise<JsonRecord> {
  const response = await fabLocalRequest("/api/support-bundles", {
    method: "POST",
    body: JSON.stringify({
      actor: actor.trim().slice(0, 200) || "fab_dashboard:local_operator",
      note: "Created from the FAB operator dashboard.",
    }),
  }, { timeoutMs: 120_000 });
  return selectFields(response, [
    "bundleFilename",
    "externalSubmission",
    "privacy",
    "sha256",
    "sizeBytes",
    "status",
    "success",
  ]);
}

export async function uploadFabIntakeFile(input: {
  filename: string;
  mimeType?: string;
  contentBase64: string;
}): Promise<JsonRecord> {
  return fabLocalRequest("/api/intake/upload", {
    method: "POST",
    body: JSON.stringify(input),
  }, { timeoutMs: 20_000 });
}

export async function uploadFabGoogleDriveCredentials(input: {
  filename: string;
  contentBase64: string;
  replace?: boolean;
  actor: string;
}): Promise<JsonRecord> {
  return fabLocalRequest("/api/connectors/google-drive/credentials", {
    method: "POST",
    body: JSON.stringify({
      filename: input.filename,
      contentBase64: input.contentBase64,
      replace: input.replace ?? false,
      actor: input.actor.trim().slice(0, 200) || "fab_dashboard:local_operator",
    }),
  }, { timeoutMs: 20_000 });
}

export async function uploadFabGmailCredentials(input: {
  filename: string;
  contentBase64: string;
  replace?: boolean;
  actor: string;
}): Promise<JsonRecord> {
  return fabLocalRequest("/api/connectors/gmail/credentials", {
    method: "POST",
    body: JSON.stringify({
      filename: input.filename,
      contentBase64: input.contentBase64,
      replace: input.replace ?? false,
      actor: input.actor.trim().slice(0, 200) || "fab_dashboard:local_operator",
    }),
  }, { timeoutMs: 20_000 });
}

export async function startFabGmailAuthorization(actor: string): Promise<JsonRecord> {
  return fabLocalRequest("/api/connectors/gmail/authorization/start", {
    method: "POST",
    body: JSON.stringify({
      actor: actor.trim().slice(0, 200) || "fab_dashboard:local_operator",
    }),
  });
}

export async function startFabGoogleDriveAuthorization(actor: string): Promise<JsonRecord> {
  return fabLocalRequest("/api/connectors/google-drive/authorization/start", {
    method: "POST",
    body: JSON.stringify({
      actor: actor.trim().slice(0, 200) || "fab_dashboard:local_operator",
    }),
  });
}

export async function saveFabWaveSetup(input: {
  targetSystem?: "waveapps_business" | "waveapps_personal";
  accessToken?: string;
  businessId?: string;
  anchorAccountId?: string;
  defaultCategoryAccountId?: string;
  categoryAccountIds?: Record<string, string>;
  clearAccessToken?: boolean;
  actor: string;
}): Promise<JsonRecord> {
  return fabLocalRequest("/api/wave/setup", {
    method: "PUT",
    body: JSON.stringify({
      ...input,
      actor: input.actor.trim().slice(0, 200) || "fab_dashboard:local_operator",
    }),
  });
}

export async function validateFabWaveSetup(
  targetSystem: "waveapps_business" | "waveapps_personal" = "waveapps_business",
): Promise<JsonRecord> {
  return fabLocalRequest("/api/wave/setup/validate", {
    method: "POST",
    body: JSON.stringify({ targetSystem }),
  }, { timeoutMs: 20_000 });
}

export async function resolveFabReviewItem(input: {
  reviewItemId: number;
  status: "approved" | "rejected" | "resolved" | "ignored";
  resolution: string;
  corrections?: {
    vendorName?: string;
    category?: string;
    transactionDate?: string;
    totalAmount?: number;
    vatAmount?: number;
    targetSystem?: string;
    duplicateOfDocumentId?: number;
    duplicateCandidateId?: number;
    documentType?: "receipt" | "vendor_invoice" | "credit_note" | "order_confirmation" | "estimate" | "bank_statement" | "insurance_policy" | "government_correspondence";
  };
  learnRule?: boolean;
  applyToMatchingVendor?: boolean;
}): Promise<JsonRecord> {
  return fabLocalRequest(`/api/review/${input.reviewItemId}/resolve`, {
    method: "POST",
    body: JSON.stringify({
      status: input.status,
      resolution: input.resolution,
      corrections: input.corrections || {},
      learnRule: input.learnRule ?? true,
      applyToMatchingVendor: input.applyToMatchingVendor ?? false,
    }),
  });
}

function disconnectedControlCenter(endpoint: string, checkedAt: string, error: string): FabControlCenter {
  const resourceStates = Object.fromEntries(
    (Object.keys(READ_PATHS) as FabResourceKey[]).map((resource) => [
      resource,
      { state: "unavailable", checkedAt, updatedAt: null, error },
    ]),
  ) as Record<FabResourceKey, FabResourceState>;
  return {
    connection: {
      connected: false,
      status: "disconnected",
      endpoint,
      authConfigured: Boolean(ENV.fabLocalApiToken),
      checkedAt,
      latencyMs: null,
      error,
    },
    metrics: {
      documents: null,
      pendingReview: null,
      pendingReviewDocuments: null,
      postingBlockedReviewDocuments: null,
      unreconciled: null,
      unreconciledDocuments: null,
      unreconciledBankTransactions: null,
      exceptions: null,
      failedDocuments: null,
    },
    decisionContext: {
      lastSafeCycleAt: null,
      latestWorkflowStatus: null,
      dataThroughDate: null,
      sourceCount: null,
      readySourceCount: null,
      latestSourceSyncAt: null,
      unreconciledAmountByCurrency: null,
      oldestReviewAgeHours: null,
      highPriorityExceptions: null,
      ledgerReadyForApproval: null,
    },
    health: {},
    autonomy: {},
    closeReadiness: {},
    delivery: { status: {}, summary: {}, workOrders: [], count: null },
    reviews: { workItems: [], categoryOptions: [], summary: {} },
    gmailAuthorization: {},
    driveAuthorization: {},
    waveSetup: {},
    waveReceiptExecutor: {},
    cloudAccess: {},
    exceptions: [],
    exceptionSummary: {},
    connections: [],
    workflows: [],
    recovery: {},
    backups: { backups: [], schedule: {}, verificationMode: null },
    notifications: [],
    reconciliation: [],
    activity: [],
    hai: { status: {}, manifest: {} },
    resourceStates,
    partialErrors: [],
  };
}

function asRecord(value: unknown): JsonRecord | null {
  return value && typeof value === "object" && !Array.isArray(value) ? value as JsonRecord : null;
}

function arrayValue(value: unknown): JsonRecord[] {
  return Array.isArray(value) ? value.flatMap((item) => asRecord(item) ? [asRecord(item)!] : []) : [];
}

function projectDeliveryWorkOrder(value: JsonRecord): JsonRecord {
  const source = selectFields(value.source, ["filename", "mimeType", "provider", "sha256"]);
  const wave = selectFields(value.wave, ["externalTransactionId", "targetSystem"]);
  const archivePlan = selectFields(value.archivePlan, [
    "canArchive",
    "evidenceVerified",
    "externalSubmission",
    "reasons",
    "retentionStatus",
    "status",
  ]);
  const reviews = selectFields(value.reviews, ["blocking", "open", "reasons"]);
  return {
    ...selectFields(value, [
      "actionRequired",
      "documentId",
      "externalSubmission",
      "stage",
      "status",
      "success",
      "workOrderId",
      "workOrderVersion",
    ]),
    source,
    wave,
    archivePlan,
    reviews,
  };
}

function projectBackups(value: unknown): FabControlCenter["backups"] {
  const payload = asRecord(value) || {};
  return {
    verificationMode: stringValue(payload.verificationMode) || null,
    backups: arrayValue(payload.backups).map((backup) => selectFields(backup, [
      "backupFilename",
      "createdAt",
      "format",
      "ledgerBytes",
      "ledgerSha256",
      "sizeBytes",
      "sourceEvidenceBytes",
      "sourceEvidenceDocuments",
      "sourceEvidenceFiles",
      "sourceEvidenceGaps",
      "sourceEvidenceStatus",
      "status",
    ])),
    schedule: selectFields(payload.schedule, [
      "due",
      "intervalHours",
      "invalidBackupCount",
      "integrityVerification",
      "lastSuccessfulAt",
      "latestBackupFilename",
      "latestLedgerSha256",
      "nextDueAt",
      "reason",
      "requireCompleteSourceEvidence",
      "sourceEvidenceBytes",
      "sourceEvidenceDocuments",
      "sourceEvidenceFiles",
      "sourceEvidenceGaps",
      "sourceEvidenceStatus",
      "status",
    ]),
  };
}

function projectReviewWorkItem(value: JsonRecord): JsonRecord {
  const document = selectFields(value.document, [
    "category",
    "classifiedDocumentType",
    "currency",
    "documentType",
    "duplicateOfDocumentId",
    "filename",
    "financialFieldIssues",
    "normalizedRecordDate",
    "normalizedVatAmount",
    "ocrExcerpt",
    "orderNumber",
    "postingEligible",
    "processingStatus",
    "source",
    "sourceUrl",
    "targetSystem",
    "totalAmount",
    "transactionDate",
    "transactionReference",
    "vatAmount",
    "vendorName",
    "invoiceNumber",
    "receiptNumber",
  ]);
  const categorySuggestion = selectFields(
    asRecord(value.document)?.categorySuggestion,
    ["category", "confidenceScore", "matchPolicy", "rationale", "source"],
  );
  if (Object.keys(categorySuggestion).length) {
    document.categorySuggestion = categorySuggestion;
  }
  const duplicateCandidates = arrayValue(value.duplicateCandidates).map((candidate) => ({
    ...selectFields(candidate, [
      "candidateDocumentId",
      "confidenceScore",
      "conflictingIdentityFields",
      "comparableFields",
      "id",
      "matchType",
      "matchedIdentityFields",
      "reason",
      "similarityScore",
    ]),
    currentIdentity: selectFields(candidate.currentIdentity, [
      "amount",
      "date",
      "invoiceNumber",
      "orderNumber",
      "postingPolarity",
      "receiptNumber",
      "tax",
      "transactionReference",
      "vendor",
    ]),
    candidateIdentity: selectFields(candidate.candidateIdentity, [
      "amount",
      "date",
      "invoiceNumber",
      "orderNumber",
      "postingPolarity",
      "receiptNumber",
      "tax",
      "transactionReference",
      "vendor",
    ]),
    document: selectFields(candidate.document, [
      "currency",
      "documentType",
      "filename",
      "invoiceNumber",
      "orderNumber",
      "receiptNumber",
      "source",
      "totalAmount",
      "transactionDate",
      "transactionReference",
      "vendorName",
    ]),
  }));
  const reviewItems = arrayValue(value.reviewItems).map((item) => selectFields(
    item,
    ["createdAt", "details", "id", "reason", "status", "updatedAt"],
  ));
  return {
    ...selectFields(value, [
      "documentId",
      "id",
      "reasons",
      "reviewPath",
      "status",
    ]),
    document,
    duplicateCandidates,
    reviewItems,
  };
}

function selectFields(value: unknown, fields: string[]): JsonRecord {
  const source = asRecord(value);
  if (!source) return {};
  return Object.fromEntries(
    fields
      .filter((field) => Object.prototype.hasOwnProperty.call(source, field))
      .map((field) => [field, source[field]]),
  );
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function stringValue(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function nullableString(value: unknown): string | null {
  const result = stringValue(value).trim();
  return result || null;
}

function latestDate(values: unknown[]): string | null {
  const valid = values
    .flatMap((value) => {
      const raw = nullableString(value);
      const timestamp = raw ? Date.parse(raw) : Number.NaN;
      return raw && !Number.isNaN(timestamp) ? [{ raw, timestamp }] : [];
    })
    .sort((left, right) => right.timestamp - left.timestamp);
  return valid[0]?.raw || null;
}

function amountByCurrency(transactions: JsonRecord[]): Record<string, number> {
  return transactions.reduce<Record<string, number>>((totals, transaction) => {
    const amount = nullableNumber(transaction.amount);
    if (amount === null) return totals;
    const currency = stringValue(transaction.currency, "UNKNOWN").toUpperCase();
    totals[currency] = Number(((totals[currency] || 0) + Math.abs(amount)).toFixed(2));
    return totals;
  }, {});
}

function oldestReviewAgeHours(workItems: JsonRecord[], checkedAt: string): number | null {
  const timestamps = workItems.flatMap((item) => arrayValue(item.reviewItems))
    .flatMap((review) => {
      const raw = nullableString(review.createdAt || review.created_at);
      const timestamp = raw ? Date.parse(raw) : Number.NaN;
      return Number.isNaN(timestamp) ? [] : [timestamp];
    });
  if (!timestamps.length) return null;
  return Math.max(0, Math.round((Date.parse(checkedAt) - Math.min(...timestamps)) / 3_600_000));
}

function waveSetupNextAction(status: string): string {
  if (status === "needs_token") return "Add the user-owned Wave access token.";
  if (status === "needs_business_id") return "Select the Wave business to operate.";
  if (status === "needs_validation") return "Validate the Wave business and load its chart of accounts.";
  if (status === "needs_mapping") return "Map the verified funding account and every FAB category currently in use.";
  if (status === "ready") return "Wave is ready for governed bookkeeping operations.";
  return "Review the Wave connection setup.";
}

function nullableNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  if (typeof value === "number" && Number.isFinite(value)) return value;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function sumNullable(left: unknown, right: unknown): number | null {
  const leftNumber = nullableNumber(left);
  const rightNumber = nullableNumber(right);
  return leftNumber === null || rightNumber === null ? null : leftNumber + rightNumber;
}
