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
  exceptions: JsonRecord[];
  exceptionSummary: JsonRecord;
  connections: JsonRecord[];
  workflows: JsonRecord[];
  recovery: JsonRecord;
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
const READ_PATHS = {
  health: "/api/health",
  metrics: "/api/dashboard",
  autonomy: "/api/autonomy/plan?limit=25",
  exceptions: "/api/exceptions?limit=25&includeEntities=true",
  settings: "/api/settings",
  sourceReadiness: "/api/sources/readiness",
  sources: "/api/sources?limit=50",
  workflows: "/api/workflows?limit=10",
  recovery: "/api/workflows/recovery?limit=10",
  notifications: "/api/notifications?limit=10",
  reconciliation: "/api/reconciliation?limit=10",
  activity: "/api/audit?limit=12",
  closeReadiness: "/api/close-readiness",
  haiStatus: "/api/hai/status",
  haiManifest: "/api/hai/manifest",
  driveWaveStatus: "/api/drive-wave/status",
  driveWaveWorkOrders: "/api/drive-wave/work-orders?limit=50",
  gmailAuthorization: "/api/connectors/gmail/authorization",
  driveAuthorization: "/api/connectors/google-drive/authorization",
  waveSetup: "/api/wave/setup",
  reviewQueue: "/api/review?status=open&limit=500",
} as const;

export type FabResourceKey = keyof typeof READ_PATHS;

const resourceCache = new Map<FabResourceKey, { value: JsonRecord; updatedAt: string }>();

const COMMAND_PATHS: Record<FabOperatorCommandId, { path: string; body: JsonRecord }> = {
  run_safe_cycle: { path: "/api/autonomy/run", body: { limit: 25, includeWavePlan: true, includeWaveSync: true, includeConnectorSync: true } },
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

export function getFabLocalApiBaseUrl(rawUrl = ENV.fabLocalApiUrl): URL {
  const parsed = new URL((rawUrl || DEFAULT_FAB_LOCAL_API_URL).trim().replace(/\/+$/, ""));
  if (!new Set(["http:", "https:"]).has(parsed.protocol)) {
    throw new Error("FAB_LOCAL_API_URL must use http or https");
  }
  if (parsed.username || parsed.password) {
    throw new Error("FAB_LOCAL_API_URL must not contain credentials");
  }
  if (parsed.protocol !== "https:" && !LOOPBACK_HOSTS.has(parsed.hostname.toLowerCase())) {
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

export async function getFabControlCenter(): Promise<FabControlCenter> {
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
  const settled = await Promise.allSettled(entries.map(([, path]) => fabLocalRequest(path)));
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

  const connected = resourceStates.health.state === "live";

  const metrics = resources.metrics || {};
  const reviewSummary = asRecord(resources.reviewQueue?.summary) || {};
  const exceptionsPayload = resources.exceptions || {};
  const settings = resources.settings || {};
  const sourceReadiness = resources.sourceReadiness || {};
  const waveSetup = resources.waveSetup || {};
  const registeredSources = arrayValue(resources.sources?.sources);
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
      nextAction: waveSetupNextAction(setupStatus),
    };
  });

  return {
    connection: {
      connected,
      status: connected ? stringValue(resources.health?.status, "connected") : "disconnected",
      endpoint,
      authConfigured: Boolean(ENV.fabLocalApiToken),
      checkedAt,
      latencyMs: connected ? Date.now() - startedAt : null,
      error: connected ? null : resourceStates.health.error || "FAB local API is unavailable",
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
    health: resources.health || {},
    autonomy: resources.autonomy || {},
    closeReadiness: resources.closeReadiness || {},
    delivery: {
      status: resources.driveWaveStatus || {},
      summary: asRecord(resources.driveWaveWorkOrders?.summary) || {},
      workOrders: arrayValue(resources.driveWaveWorkOrders?.workOrders),
      count: nullableNumber(resources.driveWaveWorkOrders?.count),
    },
    reviews: {
      workItems: arrayValue(resources.reviewQueue?.workItems),
      categoryOptions: stringArray(resources.reviewQueue?.categoryOptions),
      summary: asRecord(resources.reviewQueue?.summary) || {},
    },
    gmailAuthorization: resources.gmailAuthorization || {},
    driveAuthorization: resources.driveAuthorization || {},
    waveSetup,
    exceptions: arrayValue(exceptionsPayload.exceptions),
    exceptionSummary: asRecord(exceptionsPayload.summary) || {},
    connections: [
      ...sourceConnections,
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
    ],
    workflows: arrayValue(resources.workflows?.workflowRuns),
    recovery: resources.recovery || {},
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
}

export async function runFabOperatorCommand(
  commandId: FabOperatorCommandId,
  actor: string,
  payload: JsonRecord = {},
): Promise<JsonRecord> {
  const command = COMMAND_PATHS[commandId];
  const safeActor = actor.trim().slice(0, 200) || "fab_dashboard";
  return fabLocalRequest(command.path, {
    method: "POST",
    body: JSON.stringify({ ...command.body, ...payload, actor: safeActor }),
  });
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
    health: {},
    autonomy: {},
    closeReadiness: {},
    delivery: { status: {}, summary: {}, workOrders: [], count: null },
    reviews: { workItems: [], categoryOptions: [], summary: {} },
    gmailAuthorization: {},
    driveAuthorization: {},
    waveSetup: {},
    exceptions: [],
    exceptionSummary: {},
    connections: [],
    workflows: [],
    recovery: {},
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

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function stringValue(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function waveSetupNextAction(status: string): string {
  if (status === "needs_token") return "Add the user-owned Wave access token.";
  if (status === "needs_business_id") return "Select the Wave business to operate.";
  if (status === "needs_validation") return "Validate the Wave business and load its chart of accounts.";
  if (status === "needs_mapping") return "Map the verified bank and default expense accounts.";
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
