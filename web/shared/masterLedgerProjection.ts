import { buildMijngeldzakenMasterLedgerDraft } from "./mijngeldzakenSurface";

export type MasterLedgerOperationInput = Record<string, unknown>;

export type MasterLedgerProjectionRow = {
  workflowRunId?: number;
  workflowId: string;
  operationId: string;
  stepId: string;
  targetSystem: string;
  surfaceId: string;
  actionId: string;
  mode: string;
  safety: string;
  status: string;
  downstreamStatus: string;
  externalSubmission: string;
  masterLedgerDraftType: string;
  masterLedgerChecksum: string;
  sourceProof: Record<string, unknown>;
  downstreamProof: Record<string, unknown>;
  blockers: string[];
  readyForDraft: boolean;
  readyForApproval: boolean;
  readyForExternalExecution: boolean;
  rowChecksum: string;
};

export type MasterLedgerProjection = {
  success: true;
  projectionVersion: "fab-web-master-ledger-v1";
  generatedAt: string;
  externalSubmission: "not_executed";
  targetSystem?: string;
  workflowRunId?: number;
  workflowId?: string;
  summary: {
    totalRows: number;
    byTargetSystem: Record<string, { rows: number; statuses: Record<string, number> }>;
    downstreamStatuses: Record<string, number>;
    blockedRows: number;
    readyForDraft: number;
    readyForApproval: number;
    readyForExternalExecution: number;
    blockers: Record<string, number>;
    ledgerChecksum: string;
  };
  rows: MasterLedgerProjectionRow[];
  ledgerChecksum: string;
};

export function buildAutomationWorkflowMasterLedgerProjection(input: {
  workflowRunId?: number;
  workflowId?: string;
  targetSystem?: string;
  operations: MasterLedgerOperationInput[];
  generatedAt?: string;
}): MasterLedgerProjection {
  const targetFilter = input.targetSystem?.trim();
  const rows = input.operations
    .flatMap((operation) => {
      const targetSystem = stringValue(operation.targetSystem, "waveapps");
      if (targetFilter && targetSystem !== targetFilter) return [];
      const row = projectOperation(operation, input.workflowRunId, input.workflowId);
      return [row];
    })
    .sort((left, right) =>
      `${left.workflowId}:${left.stepId}:${left.operationId}`.localeCompare(`${right.workflowId}:${right.stepId}:${right.operationId}`)
    );
  const ledgerChecksum = stableChecksum({
    projectionVersion: "fab-web-master-ledger-v1",
    workflowRunId: input.workflowRunId,
    workflowId: input.workflowId,
    targetSystem: targetFilter,
    rowChecksums: rows.map((row) => row.rowChecksum),
  });
  const summary = summarizeRows(rows, ledgerChecksum);

  return {
    success: true,
    projectionVersion: "fab-web-master-ledger-v1",
    generatedAt: input.generatedAt || new Date().toISOString(),
    externalSubmission: "not_executed",
    targetSystem: targetFilter,
    workflowRunId: input.workflowRunId,
    workflowId: input.workflowId,
    summary,
    rows,
    ledgerChecksum,
  };
}

export function buildAutomationWorkflowMasterLedgerCsv(projection: MasterLedgerProjection) {
  const columns = [
    "workflowRunId",
    "workflowId",
    "operationId",
    "stepId",
    "targetSystem",
    "surfaceId",
    "actionId",
    "safety",
    "status",
    "downstreamStatus",
    "externalSubmission",
    "masterLedgerDraftType",
    "masterLedgerChecksum",
    "rowChecksum",
  ];
  return [
    columns.join(","),
    ...projection.rows.map((row) => columns.map((column) => csvCell(row[column as keyof MasterLedgerProjectionRow])).join(",")),
  ].join("\n");
}

function projectOperation(
  operation: MasterLedgerOperationInput,
  workflowRunId?: number,
  workflowIdFallback?: string,
): MasterLedgerProjectionRow {
  const workflowId = stringValue(operation.workflowId, workflowIdFallback || "");
  const targetSystem = stringValue(operation.targetSystem, "waveapps");
  const surfaceId = stringValue(operation.surfaceId);
  const actionId = stringValue(operation.actionId);
  const safety = stringValue(operation.safety);
  const status = stringValue(operation.status, "pending");
  const operationId = stringValue(operation.operationId);
  const stepId = stringValue(operation.stepId);
  const resolvedWorkflowRunId = typeof operation.workflowRunId === "number" ? operation.workflowRunId : workflowRunId;
  const draft =
    targetSystem === "mijngeldzaken" && safety === "safe_draft"
      ? asRecord(operation.masterLedgerDraft) || buildMijngeldzakenMasterLedgerDraft({
          actionId,
          surfaceId,
          payload: asRecord(operation.payload) || {},
          sourceProof: {
            workflowRunId: resolvedWorkflowRunId,
            workflowId,
            stepId,
            operationId,
          },
        })
      : undefined;
  const evidence = asRecord(operation.evidence) || {};
  const downstreamStatus = downstreamStatusForOperation(operation, safety, status);
  const externalSubmission = stringValue(evidence.externalSubmission, "not_executed");
  const masterLedgerChecksum = stringValue(operation.masterLedgerChecksum) || stringValue(asRecord(draft)?.checksum);
  const masterLedgerDraftType = stringValue(asRecord(draft)?.draftType);
  const blockers = blockersForOperation(operation, status, safety, downstreamStatus);
  const rowBase = {
    workflowRunId: resolvedWorkflowRunId,
    workflowId,
    operationId,
    stepId,
    targetSystem,
    surfaceId,
    actionId,
    mode: stringValue(operation.mode),
    safety,
    status,
    downstreamStatus,
    externalSubmission,
    masterLedgerDraftType,
    masterLedgerChecksum,
    sourceProof: compactRecord({
      workflowRunId: resolvedWorkflowRunId,
      workflowId,
      stepId,
      operationId,
    }),
    downstreamProof: compactRecord({
      targetSystem,
      surfaceId,
      actionId,
      operationId,
      externalSubmission,
      masterLedgerChecksum,
    }),
    blockers,
    readyForDraft: status === "pending" && safety === "safe_draft" && blockers.length === 0,
    readyForApproval: ["requires_confirmation", "requires_credentials"].includes(safety) && status === "pending",
    readyForExternalExecution: status === "pending" && safety === "safe_draft" && blockers.length === 0,
  };
  return {
    ...rowBase,
    rowChecksum: stableChecksum(rowBase),
  };
}

function downstreamStatusForOperation(operation: MasterLedgerOperationInput, safety: string, status: string) {
  const evidence = asRecord(operation.evidence) || {};
  const externalSubmission = stringValue(evidence.externalSubmission);
  if (externalSubmission && externalSubmission !== "not_executed") return externalSubmission;
  if (status === "succeeded") {
    return safety === "safe_draft" ? "draft_prepared" : "read_completed";
  }
  if (status === "running") return "running";
  if (status === "blocked") return "blocked";
  if (status === "failed") return "failed";
  if (status === "skipped") return "skipped";
  if (safety === "read_only") return "ready_for_read";
  if (safety === "safe_draft") return "ready_for_draft";
  if (safety === "requires_confirmation") return "awaiting_confirmation";
  if (safety === "requires_credentials") return "awaiting_credentials";
  return status || "pending";
}

function blockersForOperation(
  operation: MasterLedgerOperationInput,
  status: string,
  safety: string,
  downstreamStatus: string,
) {
  const blockers = new Set<string>();
  if (status === "blocked") blockers.add("operation_blocked");
  if (status === "failed") blockers.add("operation_failed");
  if (safety === "unsupported") blockers.add("unsupported_action");
  if (safety === "requires_credentials") blockers.add("requires_credentials");
  if (downstreamStatus === "failed") blockers.add("downstream_failed");
  const missingFields = Array.isArray(operation.missingFields)
    ? operation.missingFields.filter((field): field is string => typeof field === "string")
    : [];
  for (const field of missingFields) blockers.add(`missing_${field}`);
  return Array.from(blockers).sort();
}

function summarizeRows(rows: MasterLedgerProjectionRow[], ledgerChecksum: string) {
  const byTargetSystem: Record<string, { rows: number; statuses: Record<string, number> }> = {};
  const downstreamStatuses: Record<string, number> = {};
  const blockers: Record<string, number> = {};
  for (const row of rows) {
    byTargetSystem[row.targetSystem] ||= { rows: 0, statuses: {} };
    byTargetSystem[row.targetSystem].rows += 1;
    byTargetSystem[row.targetSystem].statuses[row.downstreamStatus] =
      (byTargetSystem[row.targetSystem].statuses[row.downstreamStatus] || 0) + 1;
    downstreamStatuses[row.downstreamStatus] = (downstreamStatuses[row.downstreamStatus] || 0) + 1;
    for (const blocker of row.blockers) blockers[blocker] = (blockers[blocker] || 0) + 1;
  }
  return {
    totalRows: rows.length,
    byTargetSystem,
    downstreamStatuses,
    blockedRows: rows.filter((row) => row.blockers.length > 0).length,
    readyForDraft: rows.filter((row) => row.readyForDraft).length,
    readyForApproval: rows.filter((row) => row.readyForApproval).length,
    readyForExternalExecution: rows.filter((row) => row.readyForExternalExecution).length,
    blockers,
    ledgerChecksum,
  };
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;
}

function stringValue(value: unknown, fallback = "") {
  return typeof value === "string" ? value : fallback;
}

function compactRecord(value: Record<string, unknown>) {
  return Object.fromEntries(Object.entries(value).filter(([, item]) => item !== undefined && item !== null && item !== ""));
}

function stableChecksum(value: unknown) {
  const body = stableStringify(value);
  return [0x811c9dc5, 0x9e3779b1, 0x85ebca77, 0xc2b2ae3d, 0x27d4eb2f, 0x165667b1, 0xd3a2646c, 0xfd7046c5]
    .map((seed) => fnv1aHex(body, seed))
    .join("");
}

function stableStringify(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map((item) => stableStringify(item)).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.entries(value as Record<string, unknown>)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, item]) => `${JSON.stringify(key)}:${stableStringify(item)}`)
      .join(",")}}`;
  }
  return JSON.stringify(value) ?? "null";
}

function fnv1aHex(value: string, seed: number) {
  let hash = seed >>> 0;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash.toString(16).padStart(8, "0");
}

function csvCell(value: unknown) {
  const text = value === undefined || value === null ? "" : String(value);
  if (!/[",\n]/.test(text)) return text;
  return `"${text.replaceAll("\"", "\"\"")}"`;
}
