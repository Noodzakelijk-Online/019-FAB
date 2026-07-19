import { ENV } from "./_core/env";

type JsonRecord = Record<string, unknown>;

export const FAB_OPERATOR_COMMAND_IDS = [
  "run_safe_cycle",
  "rescan_intake",
  "process_imported",
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
    documents: number;
    pendingReview: number;
    unreconciled: number;
    exceptions: number;
    failedDocuments: number;
  };
  health: JsonRecord;
  autonomy: JsonRecord;
  closeReadiness: JsonRecord;
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
  partialErrors: Array<{ resource: string; error: string }>;
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
} as const;

const COMMAND_PATHS: Record<FabOperatorCommandId, { path: string; body: JsonRecord }> = {
  run_safe_cycle: { path: "/api/autonomy/run", body: { limit: 25, includeWavePlan: true, includeWaveSync: true } },
  rescan_intake: { path: "/api/intake/rescan", body: {} },
  process_imported: { path: "/api/documents/process-imported", body: { limit: 25 } },
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

  const entries = Object.entries(READ_PATHS) as Array<[keyof typeof READ_PATHS, string]>;
  const settled = await Promise.allSettled(entries.map(([, path]) => fabLocalRequest(path)));
  const resources: Record<string, JsonRecord> = {};
  const partialErrors: Array<{ resource: string; error: string }> = [];
  settled.forEach((result, index) => {
    const resource = entries[index][0];
    if (result.status === "fulfilled") {
      resources[resource] = result.value;
      return;
    }
    partialErrors.push({
      resource,
      error: result.reason instanceof Error ? result.reason.message : "Request failed",
    });
  });

  const connected = Boolean(resources.health);
  if (!connected) {
    return {
      ...disconnectedControlCenter(endpoint, checkedAt, partialErrors[0]?.error || "FAB local API is unavailable"),
      partialErrors,
    };
  }

  const metrics = resources.metrics || {};
  const exceptionsPayload = resources.exceptions || {};
  const settings = resources.settings || {};
  const sourceReadiness = resources.sourceReadiness || {};
  const registeredSources = arrayValue(resources.sources?.sources);
  const haiAllowedCommandIds = stringArray(resources.haiStatus?.allowedCommandIds);
  const sourceConnections = arrayValue(settings.sources).map((source) => {
    const sourceId = stringValue(source.id);
    const syncPlan = arrayValue(sourceReadiness.sources).find((item) => stringValue(item.source) === sourceId);
    const account = registeredSources.find((item) => {
      const sourceType = stringValue(item.source_type || item.sourceType);
      return sourceType === sourceId || sourceType === sourceId.replace("waveapps_", "waveapps");
    });
    return {
      ...source,
      canSync: Boolean(syncPlan?.canSync),
      enabled: syncPlan ? Boolean(syncPlan.enabled) : Boolean(source.configured),
      nextAction: syncPlan?.nextAction || null,
      lastSyncAt: account?.last_sync_at || account?.updated_at || null,
      accountStatus: account?.status || null,
    };
  });

  return {
    connection: {
      connected: true,
      status: stringValue(resources.health.status, "connected"),
      endpoint,
      authConfigured: Boolean(ENV.fabLocalApiToken),
      checkedAt,
      latencyMs: Date.now() - startedAt,
      error: null,
    },
    metrics: {
      documents: numberValue(metrics.documents),
      pendingReview: numberValue(metrics.pending_review),
      unreconciled: numberValue(metrics.unreconciled_bank_transactions) + numberValue(metrics.unreconciled_documents),
      exceptions: numberValue(asRecord(exceptionsPayload.summary)?.total),
      failedDocuments: numberValue(metrics.failed_documents),
    },
    health: resources.health,
    autonomy: resources.autonomy || {},
    closeReadiness: resources.closeReadiness || {},
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
          ? `Governed machine control is enabled for ${haiAllowedCommandIds.length} local-safe commands.`
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
    partialErrors,
  };
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

function disconnectedControlCenter(endpoint: string, checkedAt: string, error: string): FabControlCenter {
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
    metrics: { documents: 0, pendingReview: 0, unreconciled: 0, exceptions: 0, failedDocuments: 0 },
    health: {},
    autonomy: {},
    closeReadiness: {},
    exceptions: [],
    exceptionSummary: {},
    connections: [],
    workflows: [],
    recovery: {},
    notifications: [],
    reconciliation: [],
    activity: [],
    hai: { status: {}, manifest: {} },
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

function numberValue(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}
