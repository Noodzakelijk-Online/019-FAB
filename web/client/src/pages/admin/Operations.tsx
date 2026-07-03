import { useAuth } from "@/_core/hooks/useAuth";
import AdminLayout from "@/components/AdminLayout";
import { Button } from "@/components/ui/button";
import { trpc } from "@/lib/trpc";
import {
  AlertCircle,
  ArrowRightLeft,
  Activity,
  Bot,
  CalendarRange,
  CheckCircle2,
  ClipboardList,
  Clock,
  CreditCard,
  DatabaseZap,
  FileSearch,
  Files,
  Gauge,
  Landmark,
  Layers3,
  ListFilter,
  MessageSquareWarning,
  PlayCircle,
  RefreshCw,
  Route,
  ShieldCheck,
  SlidersHorizontal,
  XCircle,
} from "lucide-react";
import { useMemo, useState } from "react";

type ReviewStatus = "pending" | "in_review" | "approved" | "rejected" | "resolved";
type StatusFilter = ReviewStatus | "all";
type AutomationWorkflowId = "daily_reconciliation_run" | "period_close_pack" | "mijngeldzaken_master_ledger_sync";

type WorkflowPlannerDraft = {
  workflowId: AutomationWorkflowId;
  fromDate: string;
  toDate: string;
  accountOption: string;
  accountName: string;
  contactOption: string;
  contactName: string;
  cashMode: string;
  includeExports: boolean;
  availableSignals: string[];
  confidence: number;
  approvals: string[];
};

type DraftArtifactRequest = {
  workflowRunId: number;
  operationId: string;
  format: "json" | "csv";
};

const workflowLabels: Record<AutomationWorkflowId, string> = {
  daily_reconciliation_run: "Daily reconciliation",
  period_close_pack: "Period close pack",
  mijngeldzaken_master_ledger_sync: "MijnGeldzaken master ledger",
};

const automationSignalOptions = [
  { id: "ledger_period", label: "Ledger period" },
  { id: "account_scope", label: "Account scope" },
  { id: "reconciliation_status", label: "Reconciliation status" },
  { id: "source_document", label: "Source document" },
  { id: "bank_transaction", label: "Bank transaction" },
  { id: "duplicate_fingerprint", label: "Duplicate fingerprint" },
  { id: "ledger_snapshot", label: "Ledger snapshot" },
  { id: "bank_feed", label: "Bank feed" },
  { id: "vendor_identity", label: "Vendor identity" },
  { id: "category_candidates", label: "Category candidates" },
  { id: "ocr_text", label: "OCR text" },
  { id: "approved_operation", label: "Approved operation" },
  { id: "idempotency_key", label: "Idempotency key" },
  { id: "target_surface", label: "Target surface" },
] as const;

const automationGateOptions = [
  "empty ledger scope",
  "unmatched bank activity",
  "material discrepancy",
  "partial amount match",
  "duplicate candidate",
  "multi-document order",
  "period lock",
  "tax filing",
  "material unresolved exception",
  "advisory recommendation",
  "tax-sensitive decision",
] as const;

function formatLocalDate(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function buildInitialPlannerDraft(): WorkflowPlannerDraft {
  const today = formatLocalDate(new Date());

  return {
    workflowId: "daily_reconciliation_run",
    fromDate: today,
    toDate: today,
    accountOption: "-1",
    accountName: "All accounts",
    contactOption: "0",
    contactName: "All contacts",
    cashMode: "1",
    includeExports: true,
    availableSignals: automationSignalOptions.map((signal) => signal.id),
    confidence: 0.92,
    approvals: [],
  };
}

function toWorkflowPlanInput(draft: WorkflowPlannerDraft) {
  return {
    workflowId: draft.workflowId,
    fromDate: draft.fromDate,
    toDate: draft.toDate,
    accountOption: draft.accountOption.trim() || undefined,
    accountName: draft.accountName.trim() || undefined,
    contactOption: draft.contactOption.trim() || undefined,
    contactName: draft.contactName.trim() || undefined,
    cashMode: draft.cashMode.trim() || undefined,
    includeExports: draft.includeExports,
    availableSignals: draft.availableSignals,
    confidence: draft.confidence,
    approvals: draft.approvals,
  };
}

function toggleListValue(values: string[], value: string) {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

function workflowStatusClass(status: string) {
  if (["ready", "planned", "queued", "completed", "succeeded"].includes(status)) return "bg-sage-light text-sage";
  if (["running", "safe_draft"].includes(status)) return "bg-teal/10 text-teal";
  if (["needs_signals", "needs_review", "pending", "skipped", "completed_with_review"].includes(status)) {
    return "bg-amber-50 text-amber-700";
  }
  return "bg-red-50 text-red-600";
}

const reviewStatusLabels: Record<ReviewStatus, string> = {
  pending: "Pending",
  in_review: "In review",
  approved: "Approved",
  rejected: "Rejected",
  resolved: "Resolved",
};

const reconciliationStatusLabels: Record<string, string> = {
  matched: "Matched",
  unmatched: "Unmatched",
  partial: "Partial",
  review: "Review",
};

function reconciliationStatusClass(status: string) {
  if (status === "matched") return "bg-sage-light text-sage";
  if (status === "unmatched") return "bg-red-50 text-red-600";
  if (status === "partial") return "bg-amber-50 text-amber-700";
  return "bg-sand/60 text-charcoal";
}

function benchmarkStatusClass(status: string) {
  if (status === "covered") return "bg-sage-light text-sage";
  if (status === "partial") return "bg-amber-50 text-amber-700";
  return "bg-sand/60 text-charcoal";
}

function benchmarkPriorityClass(priority: string) {
  if (priority === "high") return "bg-red-50 text-red-600";
  if (priority === "medium") return "bg-teal/10 text-teal";
  return "bg-sand/60 text-charcoal";
}

function serviceStatusClass(status: string) {
  if (status === "modeled") return "bg-sage-light text-sage";
  if (status === "partial") return "bg-amber-50 text-amber-700";
  return "bg-sand/60 text-charcoal";
}

function waveSafetyClass(safety: string) {
  if (safety === "read_only") return "bg-sage-light text-sage";
  if (safety === "safe_draft") return "bg-teal/10 text-teal";
  if (safety === "unsupported") return "bg-red-50 text-red-600";
  return "bg-amber-50 text-amber-700";
}

function waveAutomationModeClass(mode: string) {
  if (mode === "observe") return "bg-sage-light text-sage";
  if (mode === "safe_draft") return "bg-teal/10 text-teal";
  if (mode === "blocked") return "bg-red-50 text-red-600";
  return "bg-amber-50 text-amber-700";
}

export default function AdminOperations() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("pending");
  const [workflowDraft, setWorkflowDraft] = useState<WorkflowPlannerDraft>(() => buildInitialPlannerDraft());
  const [workflowPlanInput, setWorkflowPlanInput] = useState(() => toWorkflowPlanInput(buildInitialPlannerDraft()));
  const [draftArtifactRequest, setDraftArtifactRequest] = useState<DraftArtifactRequest | null>(null);
  const { user } = useAuth();
  const adminQueriesEnabled = user?.role === "admin";
  const utils = trpc.useUtils();

  const overview = trpc.bookkeeping.overview.useQuery(undefined, { enabled: adminQueriesEnabled });
  const workflowRuns = trpc.bookkeeping.workflowRuns.useQuery(undefined, { enabled: adminQueriesEnabled });
  const autonomousWorkflowRuns = trpc.bookkeeping.autonomousWorkflowRuns.useQuery(undefined, {
    enabled: adminQueriesEnabled,
  });
  const automationMasterLedger = trpc.bookkeeping.automationWorkflowMasterLedger.useQuery(
    { audit: false },
    { enabled: adminQueriesEnabled }
  );
  const reconciliationMatches = trpc.bookkeeping.reconciliationMatches.useQuery(undefined, { enabled: adminQueriesEnabled });
  const auditEvents = trpc.bookkeeping.auditEvents.useQuery({ limit: 12 }, { enabled: adminQueriesEnabled });
  const waveSurface = trpc.bookkeeping.waveSurface.useQuery(undefined, { enabled: adminQueriesEnabled });
  const waveParity = trpc.bookkeeping.waveParity.useQuery(undefined, { enabled: adminQueriesEnabled });
  const mijngeldzakenSurface = trpc.bookkeeping.mijngeldzakenSurface.useQuery(undefined, { enabled: adminQueriesEnabled });
  const mijngeldzakenParity = trpc.bookkeeping.mijngeldzakenParity.useQuery(undefined, { enabled: adminQueriesEnabled });
  const automationPlaybook = trpc.bookkeeping.automationPlaybook.useQuery(undefined, { enabled: adminQueriesEnabled });
  const automationParity = trpc.bookkeeping.automationParity.useQuery(undefined, { enabled: adminQueriesEnabled });
  const automationWorkflowPlan = trpc.bookkeeping.planAutomationWorkflow.useQuery(workflowPlanInput, {
    enabled: adminQueriesEnabled,
  });
  const draftArtifact = trpc.bookkeeping.automationWorkflowDraftArtifact.useQuery(
    draftArtifactRequest ?? { workflowRunId: 1, operationId: "__none__", format: "json" },
    { enabled: adminQueriesEnabled && Boolean(draftArtifactRequest) }
  );
  const reviewQueue = trpc.bookkeeping.reviewQueue.useQuery(
    statusFilter === "all" ? undefined : { status: statusFilter },
    { enabled: adminQueriesEnabled }
  );

  const updateReviewStatus = trpc.bookkeeping.updateReviewStatus.useMutation({
    onSuccess: async () => {
      await Promise.all([
        utils.bookkeeping.reviewQueue.invalidate(),
        utils.bookkeeping.overview.invalidate(),
      ]);
    },
  });
  const queueAutomationWorkflow = trpc.bookkeeping.queueAutomationWorkflow.useMutation({
    onSuccess: async () => {
      await Promise.all([
        utils.bookkeeping.auditEvents.invalidate(),
        utils.bookkeeping.automationWorkflowMasterLedger.invalidate(),
        utils.bookkeeping.autonomousWorkflowRuns.invalidate(),
        utils.bookkeeping.workflowRuns.invalidate(),
        utils.bookkeeping.overview.invalidate(),
      ]);
    },
  });
  const claimAutomationWorkflowOperation = trpc.bookkeeping.claimAutomationWorkflowOperation.useMutation({
    onSuccess: async () => {
      await Promise.all([
        utils.bookkeeping.auditEvents.invalidate(),
        utils.bookkeeping.automationWorkflowMasterLedger.invalidate(),
        utils.bookkeeping.autonomousWorkflowRuns.invalidate(),
        utils.bookkeeping.workflowRuns.invalidate(),
        utils.bookkeeping.overview.invalidate(),
      ]);
    },
  });
  const runAutomationWorkflowExecutorCycle = trpc.bookkeeping.runAutomationWorkflowExecutorCycle.useMutation({
    onSuccess: async () => {
      await Promise.all([
        utils.bookkeeping.auditEvents.invalidate(),
        utils.bookkeeping.automationWorkflowMasterLedger.invalidate(),
        utils.bookkeeping.autonomousWorkflowRuns.invalidate(),
        utils.bookkeeping.workflowRuns.invalidate(),
        utils.bookkeeping.overview.invalidate(),
      ]);
    },
  });
  const runAutomationWorkflowExecutorLoop = trpc.bookkeeping.runAutomationWorkflowExecutorLoop.useMutation({
    onSuccess: async () => {
      await Promise.all([
        utils.bookkeeping.auditEvents.invalidate(),
        utils.bookkeeping.automationWorkflowMasterLedger.invalidate(),
        utils.bookkeeping.autonomousWorkflowRuns.invalidate(),
        utils.bookkeeping.workflowRuns.invalidate(),
        utils.bookkeeping.overview.invalidate(),
      ]);
    },
  });

  const stats = useMemo(
    () => [
      {
        label: "Documents",
        value: overview.data?.documents ?? 0,
        icon: Files,
        color: "bg-teal/10 text-teal",
      },
      {
        label: "Pending Review",
        value: overview.data?.pendingReviews ?? 0,
        icon: FileSearch,
        color: "bg-amber-50 text-amber-700",
      },
      {
        label: "Routed",
        value: overview.data?.routed ?? 0,
        icon: Route,
        color: "bg-sage-light text-sage",
      },
      {
        label: "Failed",
        value: overview.data?.failed ?? 0,
        icon: AlertCircle,
        color: "bg-red-50 text-red-600",
      },
      {
        label: "Active Runs",
        value: overview.data?.activeWorkflowRuns ?? 0,
        icon: PlayCircle,
        color: "bg-sand text-charcoal",
      },
    ],
    [overview.data]
  );

  const automationSourceLabels = useMemo(
    () => new Map((automationPlaybook.data?.sources ?? []).map((source) => [source.id, source.label])),
    [automationPlaybook.data?.sources]
  );

  function updateStatus(id: number, status: ReviewStatus, resolution?: string) {
    updateReviewStatus.mutate({ id, status, resolution });
  }

  function updateWorkflowDraft<Value extends keyof WorkflowPlannerDraft>(
    field: Value,
    value: WorkflowPlannerDraft[Value]
  ) {
    setWorkflowDraft((current) => ({ ...current, [field]: value }));
  }

  function toggleWorkflowSignal(signal: string) {
    setWorkflowDraft((current) => ({
      ...current,
      availableSignals: toggleListValue(current.availableSignals, signal),
    }));
  }

  function toggleWorkflowApproval(gate: string) {
    setWorkflowDraft((current) => ({
      ...current,
      approvals: toggleListValue(current.approvals, gate),
    }));
  }

  function planWorkflowRun() {
    setWorkflowPlanInput(toWorkflowPlanInput(workflowDraft));
  }

  function dryRunWorkflowBatch() {
    queueAutomationWorkflow.mutate({
      ...workflowPlanInput,
      mode: "dry_run",
      actor: "fab_admin",
    });
  }

  function queueWorkflowBatch() {
    queueAutomationWorkflow.mutate({
      ...workflowPlanInput,
      mode: "queue",
      actor: "fab_admin",
      confirmed: workflowPlanInput.approvals.length > 0,
    });
  }

  function claimNextOperation(workflowRunId: number) {
    claimAutomationWorkflowOperation.mutate({
      workflowRunId,
      actor: "fab_executor",
      leaseSeconds: 300,
    });
  }

  function runExecutorCycle(workflowRunId: number) {
    runAutomationWorkflowExecutorCycle.mutate({
      workflowRunId,
      actor: "fab_executor",
      leaseSeconds: 300,
    });
  }

  function runExecutorLoop(workflowRunId: number) {
    runAutomationWorkflowExecutorLoop.mutate({
      workflowRunId,
      actor: "fab_executor",
      leaseSeconds: 300,
      maxSteps: 25,
    });
  }

  function requestDraftArtifact(workflowRunId: number, operationId: string, format: "json" | "csv") {
    setDraftArtifactRequest({ workflowRunId, operationId, format });
  }

  function draftArtifactText() {
    const data = draftArtifact.data;
    if (!data) return "";
    if (data.status !== "prepared" || !("artifact" in data)) {
      return data.message || data.status;
    }
    const content = data.artifact.content;
    return data.artifact.format === "json" ? JSON.stringify(content, null, 2) : String(content);
  }

  return (
    <AdminLayout>
      <div className="space-y-8">
        <div>
          <h1 className="text-2xl font-semibold text-charcoal">FAB Operations</h1>
          <p className="text-charcoal-light mt-1">
            Monitor document processing, workflow runs, and manual review.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 xl:grid-cols-5 gap-5">
          {stats.map((stat) => (
            <div key={stat.label} className="bg-white rounded-2xl p-5 border border-sand-dark/15 shadow-sm">
              <div className={`w-10 h-10 rounded-xl ${stat.color} flex items-center justify-center mb-4`}>
                <stat.icon className="w-5 h-5" />
              </div>
              <div className="text-2xl font-semibold text-charcoal">{stat.value}</div>
              <div className="text-sm text-charcoal-light mt-1">{stat.label}</div>
            </div>
          ))}
        </div>

        <section className="bg-white rounded-2xl border border-sand-dark/15 shadow-sm overflow-hidden">
          <div className="p-6 border-b border-sand-dark/10 flex flex-col xl:flex-row xl:items-start xl:justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <Bot className="w-5 h-5 text-teal" />
                <h2 className="text-lg font-semibold text-charcoal">Autonomous Bookkeeper Playbook</h2>
              </div>
              <p className="text-sm text-charcoal-light mt-1">
                Competitor-informed control model for continuous collection, reconciliation, exception chase, and close.
              </p>
            </div>
            {automationParity.data && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 min-w-fit">
                <span className="text-xs px-2 py-1 rounded-lg bg-teal/10 text-teal text-center">
                  {automationParity.data.sources} sources
                </span>
                <span className="text-xs px-2 py-1 rounded-lg bg-sage-light text-sage text-center">
                  {automationParity.data.stages} stages
                </span>
                <span className="text-xs px-2 py-1 rounded-lg bg-sand/60 text-charcoal text-center">
                  {automationParity.data.capabilities} capabilities
                </span>
                <span className="text-xs px-2 py-1 rounded-lg bg-teal/10 text-teal text-center">
                  {automationParity.data.serviceOfferings} services
                </span>
                <span className="text-xs px-2 py-1 rounded-lg bg-amber-50 text-amber-700 text-center">
                  {automationParity.data.waveLinkedCapabilities} Wave-linked
                </span>
              </div>
            )}
          </div>

          {automationPlaybook.isLoading ? (
            <div className="p-8 text-center text-charcoal-light">Loading automation playbook...</div>
          ) : automationPlaybook.data ? (
            <div className="p-6 space-y-6">
              <div className="grid lg:grid-cols-[0.9fr_1.1fr] gap-6">
                <div>
                  <h3 className="text-sm font-semibold text-charcoal mb-3">Reference Patterns</h3>
                  <div className="space-y-3">
                    {automationPlaybook.data.sources.map((source) => (
                      <div key={source.id} className="rounded-xl border border-sand-dark/15 p-4 bg-sand/10">
                        <div className="flex items-center justify-between gap-3">
                          <div className="text-sm font-semibold text-charcoal">{source.label}</div>
                          <a
                            href={source.url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-xs text-teal hover:text-teal-light"
                          >
                            Source
                          </a>
                        </div>
                        <ul className="mt-3 space-y-2">
                          {source.patterns.slice(0, 3).map((pattern) => (
                            <li key={pattern} className="text-xs text-charcoal-light flex gap-2">
                              <ShieldCheck className="w-3.5 h-3.5 text-sage shrink-0 mt-0.5" />
                              <span>{pattern}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-charcoal mb-3">Operating Loop</h3>
                  <div className="grid sm:grid-cols-2 gap-3">
                    {automationPlaybook.data.stages.map((stage) => {
                      const count = automationParity.data?.capabilitiesByStage[stage.id] ?? 0;
                      return (
                        <div key={stage.id} className="rounded-xl border border-sand-dark/15 p-4">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <div className="text-sm font-semibold text-charcoal">{stage.label}</div>
                              <div className="text-xs text-charcoal-light mt-1">{stage.purpose}</div>
                            </div>
                            <span className="text-[11px] px-2 py-1 rounded-lg bg-sand/60 text-charcoal shrink-0">
                              {count}
                            </span>
                          </div>
                          <div className="text-xs text-teal mt-3">{stage.targetOutcome}</div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between gap-3 mb-3">
                  <div className="flex items-center gap-2">
                    <ClipboardList className="w-4 h-4 text-teal" />
                    <h3 className="text-sm font-semibold text-charcoal">Service Coverage Inventory</h3>
                  </div>
                  {automationParity.data && (
                    <div className="flex flex-wrap justify-end gap-2">
                      <span className="text-[11px] px-2 py-1 rounded-lg bg-sage-light text-sage">
                        {automationParity.data.servicesByStatus.modeled} modeled
                      </span>
                      <span className="text-[11px] px-2 py-1 rounded-lg bg-amber-50 text-amber-700">
                        {automationParity.data.servicesByStatus.partial} partial
                      </span>
                      <span className="text-[11px] px-2 py-1 rounded-lg bg-sand/60 text-charcoal">
                        {automationParity.data.servicesByStatus.planned} planned
                      </span>
                    </div>
                  )}
                </div>
                <div className="overflow-x-auto rounded-xl border border-sand-dark/15">
                  <table className="w-full">
                    <thead>
                      <tr className="bg-sand/30 border-b border-sand-dark/10">
                        <th className="text-left text-xs font-medium text-charcoal-light uppercase tracking-wider px-4 py-3">
                          Service
                        </th>
                        <th className="text-left text-xs font-medium text-charcoal-light uppercase tracking-wider px-4 py-3">
                          FAB Build Target
                        </th>
                        <th className="text-left text-xs font-medium text-charcoal-light uppercase tracking-wider px-4 py-3">
                          Netherlands Layer
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-sand-dark/10 bg-white">
                      {automationPlaybook.data.serviceOfferings.map((service) => (
                        <tr key={service.id} className="align-top">
                          <td className="px-4 py-3 min-w-56">
                            <div className="text-sm font-medium text-charcoal">{service.label}</div>
                            <div className="mt-2 flex flex-wrap gap-2">
                              <span className="text-[11px] px-2 py-1 rounded-md bg-teal/10 text-teal">
                                {automationSourceLabels.get(service.sourceId) ?? service.sourceId}
                              </span>
                              <span className={`text-[11px] px-2 py-1 rounded-md ${serviceStatusClass(service.status)}`}>
                                {service.status}
                              </span>
                              <span className="text-[11px] px-2 py-1 rounded-md bg-sand/60 text-charcoal">
                                {service.category.replaceAll("_", " ")}
                              </span>
                            </div>
                          </td>
                          <td className="px-4 py-3 min-w-80">
                            <div className="text-xs text-charcoal-light">{service.serviceSurface}</div>
                            <div className="text-xs text-charcoal mt-2">{service.fabImplementation}</div>
                            <div className="mt-2 flex flex-wrap gap-2">
                              {service.requiredCapabilities.slice(0, 3).map((capabilityId) => (
                                <span
                                  key={capabilityId}
                                  className="text-[11px] px-2 py-1 rounded-md bg-sand/60 text-charcoal"
                                >
                                  {capabilityId.replaceAll("_", " ")}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td className="px-4 py-3 min-w-72 text-xs text-charcoal-light">
                            {service.netherlandsAdaptation}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between gap-3 mb-3">
                  <div className="flex items-center gap-2">
                    <Gauge className="w-4 h-4 text-teal" />
                    <h3 className="text-sm font-semibold text-charcoal">Benchmark Against AI Bookkeepers</h3>
                  </div>
                  {automationParity.data && (
                    <div className="flex flex-wrap justify-end gap-2">
                      <span className="text-[11px] px-2 py-1 rounded-lg bg-sage-light text-sage">
                        {automationParity.data.benchmarkByStatus.covered} covered
                      </span>
                      <span className="text-[11px] px-2 py-1 rounded-lg bg-amber-50 text-amber-700">
                        {automationParity.data.benchmarkByStatus.partial} partial
                      </span>
                      <span className="text-[11px] px-2 py-1 rounded-lg bg-sand/60 text-charcoal">
                        {automationParity.data.benchmarkByStatus.planned} planned
                      </span>
                    </div>
                  )}
                </div>
                <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">
                  {automationPlaybook.data.benchmarkAreas.map((area) => (
                    <div key={area.id} className="rounded-xl border border-sand-dark/15 p-4 bg-white">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="text-sm font-medium text-charcoal">{area.label}</div>
                          <div className="text-xs text-charcoal-light mt-1">
                            {area.sourceIds.map((sourceId) => automationSourceLabels.get(sourceId) ?? sourceId).join(", ")}
                          </div>
                        </div>
                        <div className="flex flex-col items-end gap-1 shrink-0">
                          <span className={`text-[11px] px-2 py-1 rounded-lg ${benchmarkStatusClass(area.fabStatus)}`}>
                            {area.fabStatus}
                          </span>
                          <span className={`text-[11px] px-2 py-1 rounded-lg ${benchmarkPriorityClass(area.priority)}`}>
                            {area.priority}
                          </span>
                        </div>
                      </div>
                      <p className="text-xs text-charcoal-light mt-3">{area.competitorPattern}</p>
                      <div className="mt-3 text-xs text-charcoal">
                        <span className="font-medium">Next:</span> {area.nextMilestone}
                      </div>
                      <div className="mt-2 text-xs text-charcoal-light flex gap-2">
                        <ShieldCheck className="w-3.5 h-3.5 text-sage shrink-0 mt-0.5" />
                        <span>{area.riskControl}</span>
                      </div>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {area.capabilityIds.slice(0, 3).map((capabilityId) => (
                          <span key={capabilityId} className="text-[11px] px-2 py-1 rounded-md bg-sand/60 text-charcoal">
                            {capabilityId.replaceAll("_", " ")}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <div className="flex items-center gap-2 mb-3">
                  <Layers3 className="w-4 h-4 text-teal" />
                  <h3 className="text-sm font-semibold text-charcoal">Capabilities FAB Can Orchestrate</h3>
                </div>
                <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">
                  {automationPlaybook.data.capabilities.map((capability) => (
                    <div key={capability.id} className="rounded-xl border border-sand-dark/15 p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="text-sm font-medium text-charcoal">{capability.label}</div>
                          <div className="text-xs text-charcoal-light mt-1">
                            {capability.stageId.replaceAll("_", " ")}
                          </div>
                        </div>
                        <span
                          className={`text-[11px] px-2 py-1 rounded-lg shrink-0 ${
                            capability.autonomyLevel === "safe_draft"
                              ? "bg-teal/10 text-teal"
                              : capability.autonomyLevel === "review_required" ||
                                  capability.autonomyLevel === "confirmed_execute"
                                ? "bg-amber-50 text-amber-700"
                                : "bg-sage-light text-sage"
                          }`}
                        >
                          {capability.autonomyLevel.replaceAll("_", " ")}
                        </span>
                      </div>
                      <p className="text-xs text-charcoal-light mt-3">{capability.description}</p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {capability.waveActions.slice(0, 3).map((action) => (
                          <span key={action} className="text-[11px] px-2 py-1 rounded-md bg-sand/60 text-charcoal">
                            {action.replaceAll("_", " ")}
                          </span>
                        ))}
                        {!capability.waveActions.length && (
                          <span className="text-[11px] px-2 py-1 rounded-md bg-sand/60 text-charcoal">
                            internal workflow
                          </span>
                        )}
                      </div>
                      <div className="mt-3 text-xs text-charcoal-light flex gap-2">
                        <MessageSquareWarning className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
                        <span>{capability.reviewGates[0]}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-charcoal-light">Automation playbook unavailable.</div>
          )}
        </section>

        <section className="bg-white rounded-2xl border border-sand-dark/15 shadow-sm overflow-hidden">
          <div className="p-6 border-b border-sand-dark/10 flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <DatabaseZap className="w-5 h-5 text-teal" />
                <h2 className="text-lg font-semibold text-charcoal">Autonomous Wave Workflow Planner</h2>
              </div>
              <p className="text-sm text-charcoal-light mt-1">
                Convert FAB policy, date scope, and readiness signals into executable Wave action plans.
              </p>
            </div>
            {automationWorkflowPlan.data && (
              <div className="flex flex-wrap justify-start lg:justify-end gap-2">
                <span className={`text-xs px-2 py-1 rounded-lg ${workflowStatusClass(automationWorkflowPlan.data.status)}`}>
                  {automationWorkflowPlan.data.status.replaceAll("_", " ")}
                </span>
                <span className="text-xs px-2 py-1 rounded-lg bg-sand/60 text-charcoal">
                  {automationWorkflowPlan.data.steps.length} steps
                </span>
                <span
                  className={`text-xs px-2 py-1 rounded-lg ${
                    automationWorkflowPlan.data.canRunAutonomously
                      ? "bg-sage-light text-sage"
                      : "bg-amber-50 text-amber-700"
                  }`}
                >
                  {automationWorkflowPlan.data.canRunAutonomously ? "autonomous-ready" : "policy-gated"}
                </span>
              </div>
            )}
          </div>

          <div className="p-6 grid xl:grid-cols-[420px_1fr] gap-6">
            <div className="space-y-5">
              <div className="rounded-xl border border-sand-dark/15 p-4 bg-sand/10">
                <div className="flex items-center gap-2 mb-4">
                  <SlidersHorizontal className="w-4 h-4 text-teal" />
                  <h3 className="text-sm font-semibold text-charcoal">Run Scope</h3>
                </div>
                <div className="space-y-4">
                  <label className="block">
                    <span className="text-xs font-medium text-charcoal-light">Workflow</span>
                    <select
                      value={workflowDraft.workflowId}
                      onChange={(event) => updateWorkflowDraft("workflowId", event.target.value as AutomationWorkflowId)}
                      className="mt-1 w-full px-3 py-2 rounded-xl border border-sand-dark/30 bg-white text-charcoal text-sm focus:outline-none focus:ring-2 focus:ring-teal/30 focus:border-teal"
                    >
                      {Object.entries(workflowLabels).map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </label>

                  <div className="grid grid-cols-2 gap-3">
                    <label className="block">
                      <span className="text-xs font-medium text-charcoal-light">From</span>
                      <input
                        type="date"
                        value={workflowDraft.fromDate}
                        onChange={(event) => updateWorkflowDraft("fromDate", event.target.value)}
                        className="mt-1 w-full px-3 py-2 rounded-xl border border-sand-dark/30 bg-white text-charcoal text-sm focus:outline-none focus:ring-2 focus:ring-teal/30 focus:border-teal"
                      />
                    </label>
                    <label className="block">
                      <span className="text-xs font-medium text-charcoal-light">To</span>
                      <input
                        type="date"
                        value={workflowDraft.toDate}
                        onChange={(event) => updateWorkflowDraft("toDate", event.target.value)}
                        className="mt-1 w-full px-3 py-2 rounded-xl border border-sand-dark/30 bg-white text-charcoal text-sm focus:outline-none focus:ring-2 focus:ring-teal/30 focus:border-teal"
                      />
                    </label>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <label className="block">
                      <span className="text-xs font-medium text-charcoal-light">Account option</span>
                      <input
                        value={workflowDraft.accountOption}
                        onChange={(event) => updateWorkflowDraft("accountOption", event.target.value)}
                        className="mt-1 w-full px-3 py-2 rounded-xl border border-sand-dark/30 bg-white text-charcoal text-sm focus:outline-none focus:ring-2 focus:ring-teal/30 focus:border-teal"
                      />
                    </label>
                    <label className="block">
                      <span className="text-xs font-medium text-charcoal-light">Contact option</span>
                      <input
                        value={workflowDraft.contactOption}
                        onChange={(event) => updateWorkflowDraft("contactOption", event.target.value)}
                        className="mt-1 w-full px-3 py-2 rounded-xl border border-sand-dark/30 bg-white text-charcoal text-sm focus:outline-none focus:ring-2 focus:ring-teal/30 focus:border-teal"
                      />
                    </label>
                  </div>

                  <label className="block">
                    <span className="text-xs font-medium text-charcoal-light">Account name</span>
                    <input
                      value={workflowDraft.accountName}
                      onChange={(event) => updateWorkflowDraft("accountName", event.target.value)}
                      className="mt-1 w-full px-3 py-2 rounded-xl border border-sand-dark/30 bg-white text-charcoal text-sm focus:outline-none focus:ring-2 focus:ring-teal/30 focus:border-teal"
                    />
                  </label>

                  <label className="block">
                    <span className="text-xs font-medium text-charcoal-light">Contact name</span>
                    <input
                      value={workflowDraft.contactName}
                      onChange={(event) => updateWorkflowDraft("contactName", event.target.value)}
                      className="mt-1 w-full px-3 py-2 rounded-xl border border-sand-dark/30 bg-white text-charcoal text-sm focus:outline-none focus:ring-2 focus:ring-teal/30 focus:border-teal"
                    />
                  </label>

                  <div className="grid grid-cols-[1fr_auto] gap-3 items-end">
                    <label className="block">
                      <span className="text-xs font-medium text-charcoal-light">Confidence</span>
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.01"
                        value={workflowDraft.confidence}
                        onChange={(event) => updateWorkflowDraft("confidence", Number(event.target.value))}
                        className="mt-2 w-full accent-teal"
                      />
                    </label>
                    <span className="text-sm font-semibold text-charcoal pb-0.5">
                      {Math.round(workflowDraft.confidence * 100)}%
                    </span>
                  </div>

                  <label className="flex items-center justify-between gap-3 rounded-xl border border-sand-dark/15 bg-white px-3 py-2">
                    <span className="text-sm text-charcoal">Export evidence files</span>
                    <input
                      type="checkbox"
                      checked={workflowDraft.includeExports}
                      onChange={(event) => updateWorkflowDraft("includeExports", event.target.checked)}
                      className="h-4 w-4 accent-teal"
                    />
                  </label>

                  <Button
                    type="button"
                    onClick={planWorkflowRun}
                    className="w-full rounded-xl bg-teal hover:bg-teal-light text-white"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Plan run
                  </Button>
                </div>
              </div>

              <div className="rounded-xl border border-sand-dark/15 p-4">
                <div className="flex items-center gap-2 mb-3">
                  <CalendarRange className="w-4 h-4 text-teal" />
                  <h3 className="text-sm font-semibold text-charcoal">Readiness Signals</h3>
                </div>
                <div className="grid sm:grid-cols-2 xl:grid-cols-1 gap-2">
                  {automationSignalOptions.map((signal) => (
                    <label
                      key={signal.id}
                      className="flex items-center justify-between gap-3 rounded-lg bg-sand/20 px-3 py-2"
                    >
                      <span className="text-xs text-charcoal">{signal.label}</span>
                      <input
                        type="checkbox"
                        checked={workflowDraft.availableSignals.includes(signal.id)}
                        onChange={() => toggleWorkflowSignal(signal.id)}
                        className="h-4 w-4 accent-teal"
                      />
                    </label>
                  ))}
                </div>
              </div>

              <div className="rounded-xl border border-sand-dark/15 p-4">
                <div className="flex items-center gap-2 mb-3">
                  <ShieldCheck className="w-4 h-4 text-teal" />
                  <h3 className="text-sm font-semibold text-charcoal">Cleared Gates</h3>
                </div>
                <div className="space-y-2">
                  {automationGateOptions.map((gate) => (
                    <label key={gate} className="flex items-center justify-between gap-3 rounded-lg bg-sand/20 px-3 py-2">
                      <span className="text-xs text-charcoal">{gate}</span>
                      <input
                        type="checkbox"
                        checked={workflowDraft.approvals.includes(gate)}
                        onChange={() => toggleWorkflowApproval(gate)}
                        className="h-4 w-4 accent-teal"
                      />
                    </label>
                  ))}
                </div>
              </div>
            </div>

            <div className="space-y-5">
              {automationWorkflowPlan.isLoading ? (
                <div className="rounded-xl border border-sand-dark/15 p-8 text-center text-charcoal-light">
                  Planning autonomous workflow...
                </div>
              ) : automationWorkflowPlan.data ? (
                <>
                  <div className="rounded-xl border border-sand-dark/15 p-5">
                    <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
                      <div>
                        <div className="text-sm font-semibold text-charcoal">
                          {workflowLabels[automationWorkflowPlan.data.workflowId]}
                        </div>
                        <p className="text-sm text-charcoal-light mt-1">{automationWorkflowPlan.data.nextAction}</p>
                      </div>
                      <div className="flex flex-wrap md:justify-end gap-2">
                        <span className={`text-xs px-2 py-1 rounded-lg ${workflowStatusClass(automationWorkflowPlan.data.status)}`}>
                          {automationWorkflowPlan.data.status.replaceAll("_", " ")}
                        </span>
                        <span
                          className={`text-xs px-2 py-1 rounded-lg ${
                            automationWorkflowPlan.data.canRunAutonomously
                              ? "bg-sage-light text-sage"
                              : "bg-amber-50 text-amber-700"
                          }`}
                        >
                          {automationWorkflowPlan.data.canRunAutonomously ? "can queue" : "needs gate"}
                        </span>
                      </div>
                    </div>

                    <div className="grid md:grid-cols-3 gap-3 mt-5">
                      <div className="rounded-xl bg-sand/30 p-3">
                        <div className="text-sm font-semibold text-charcoal">
                          {automationWorkflowPlan.data.requiredSignals.length}
                        </div>
                        <div className="text-[11px] text-charcoal-light">Required signals</div>
                      </div>
                      <div className="rounded-xl bg-sand/30 p-3">
                        <div className="text-sm font-semibold text-charcoal">
                          {automationWorkflowPlan.data.missingSignals.length}
                        </div>
                        <div className="text-[11px] text-charcoal-light">Missing signals</div>
                      </div>
                      <div className="rounded-xl bg-sand/30 p-3">
                        <div className="text-sm font-semibold text-charcoal">
                          {automationWorkflowPlan.data.reviewGates.length}
                        </div>
                        <div className="text-[11px] text-charcoal-light">Open gates</div>
                      </div>
                    </div>

                    <div className="mt-5 rounded-xl border border-sand-dark/15 bg-sand/10 p-4">
                      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                        <div>
                          <div className="text-sm font-semibold text-charcoal">Batch executor</div>
                          <div className="text-xs text-charcoal-light mt-1">
                            Queue the displayed plan as one audited set of downstream operations.
                          </div>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <Button
                            type="button"
                            variant="outline"
                            onClick={dryRunWorkflowBatch}
                            disabled={queueAutomationWorkflow.isPending}
                            className="rounded-xl border-teal/20 text-teal hover:bg-teal/5"
                          >
                            <FileSearch className="w-4 h-4" />
                            Dry-run batch
                          </Button>
                          <Button
                            type="button"
                            onClick={queueWorkflowBatch}
                            disabled={queueAutomationWorkflow.isPending || !automationWorkflowPlan.data.canRunAutonomously}
                            className="rounded-xl bg-teal hover:bg-teal-light text-white"
                          >
                            <PlayCircle className="w-4 h-4" />
                            Queue batch
                          </Button>
                        </div>
                      </div>

                      {queueAutomationWorkflow.data && (
                        <div className="mt-4 flex flex-col md:flex-row md:items-start md:justify-between gap-3 rounded-xl bg-white border border-sand-dark/15 p-3">
                          <div>
                            <div className="text-sm font-medium text-charcoal">{queueAutomationWorkflow.data.message}</div>
                          <div className="text-xs text-charcoal-light mt-1">
                              Run #{queueAutomationWorkflow.data.workflowRunId} /{" "}
                              {queueAutomationWorkflow.data.operations.length} downstream operations prepared
                              {queueAutomationWorkflow.data.blockingActions.length
                                ? ` / ${queueAutomationWorkflow.data.blockingActions.length} blocked`
                                : ""}
                            </div>
                          </div>
                          <span className={`text-xs px-2 py-1 rounded-lg ${workflowStatusClass(queueAutomationWorkflow.data.status)}`}>
                            {queueAutomationWorkflow.data.status.replaceAll("_", " ")}
                          </span>
                        </div>
                      )}
                    </div>

                    <div className="grid lg:grid-cols-2 gap-4 mt-5">
                      <div>
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-charcoal-light mb-2">
                          Missing
                        </h4>
                        <div className="flex flex-wrap gap-2">
                          {automationWorkflowPlan.data.missingSignals.length ? (
                            automationWorkflowPlan.data.missingSignals.map((signal) => (
                              <span key={signal} className="text-[11px] px-2 py-1 rounded-md bg-amber-50 text-amber-700">
                                {signal.replaceAll("_", " ")}
                              </span>
                            ))
                          ) : (
                            <span className="text-[11px] px-2 py-1 rounded-md bg-sage-light text-sage">
                              all required signals present
                            </span>
                          )}
                        </div>
                      </div>
                      <div>
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-charcoal-light mb-2">
                          Open review gates
                        </h4>
                        <div className="flex flex-wrap gap-2">
                          {automationWorkflowPlan.data.reviewGates.length ? (
                            automationWorkflowPlan.data.reviewGates.map((gate) => (
                              <span key={gate} className="text-[11px] px-2 py-1 rounded-md bg-amber-50 text-amber-700">
                                {gate}
                              </span>
                            ))
                          ) : (
                            <span className="text-[11px] px-2 py-1 rounded-md bg-sage-light text-sage">
                              no open gates
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-xl border border-sand-dark/15 overflow-hidden">
                    <div className="px-5 py-4 border-b border-sand-dark/10 flex items-center justify-between gap-3">
                      <h3 className="text-sm font-semibold text-charcoal">Wave Execution Steps</h3>
                      <span className="text-xs text-charcoal-light">
                        {automationWorkflowPlan.data.steps.length} actions
                      </span>
                    </div>
                    <div className="divide-y divide-sand-dark/10">
                      {automationWorkflowPlan.data.steps.map((step, index) => (
                        <div key={step.id} className="p-4 grid md:grid-cols-[48px_1fr_auto] gap-3 align-top">
                          <div className="w-9 h-9 rounded-xl bg-teal/10 text-teal flex items-center justify-center text-sm font-semibold">
                            {index + 1}
                          </div>
                          <div className="min-w-0">
                            <div className="text-sm font-medium text-charcoal">{step.label}</div>
                            <div className="text-xs text-charcoal-light mt-1">{step.purpose}</div>
                            <div className="mt-2 flex flex-wrap gap-2">
                              <span className="text-[11px] px-2 py-1 rounded-md bg-sand/60 text-charcoal">
                                {step.actionId.replaceAll("_", " ")}
                              </span>
                              <span className="text-[11px] px-2 py-1 rounded-md bg-sand/60 text-charcoal">
                                {step.surfaceId}
                              </span>
                              <span className="text-[11px] px-2 py-1 rounded-md bg-sand/60 text-charcoal">
                                {step.capabilityId.replaceAll("_", " ")}
                              </span>
                            </div>
                          </div>
                          <span className={`text-[11px] px-2 py-1 rounded-lg h-fit ${waveSafetyClass(step.safety)}`}>
                            {step.safety.replaceAll("_", " ")}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="rounded-xl border border-sand-dark/15 p-5">
                    <h3 className="text-sm font-semibold text-charcoal mb-3">Capability Decisions</h3>
                    <div className="grid lg:grid-cols-2 gap-3">
                      {automationWorkflowPlan.data.capabilityPlans.map((plan) => (
                        <div key={plan.capability?.id ?? plan.nextAction} className="rounded-xl bg-sand/20 p-4">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <div className="text-sm font-medium text-charcoal">
                                {plan.capability?.label ?? "Unknown capability"}
                              </div>
                              <div className="text-xs text-charcoal-light mt-1">{plan.nextAction}</div>
                            </div>
                            <span className={`text-[11px] px-2 py-1 rounded-lg shrink-0 ${workflowStatusClass(plan.status)}`}>
                              {plan.status.replaceAll("_", " ")}
                            </span>
                          </div>
                          <div className="mt-3 flex flex-wrap gap-2">
                            <span className="text-[11px] px-2 py-1 rounded-md bg-white border border-sand-dark/15 text-charcoal">
                              {plan.recommendedMode.replaceAll("_", " ")}
                            </span>
                            <span
                              className={`text-[11px] px-2 py-1 rounded-md ${
                                plan.canRunAutonomously ? "bg-sage-light text-sage" : "bg-amber-50 text-amber-700"
                              }`}
                            >
                              {plan.canRunAutonomously ? "autonomous" : "guarded"}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              ) : (
                <div className="rounded-xl border border-sand-dark/15 p-8 text-center text-charcoal-light">
                  Workflow plan unavailable.
                </div>
              )}
            </div>
          </div>
        </section>

        <section className="bg-white rounded-2xl border border-sand-dark/15 shadow-sm overflow-hidden">
          <div className="p-6 border-b border-sand-dark/10 flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <CreditCard className="w-5 h-5 text-teal" />
                <h2 className="text-lg font-semibold text-charcoal">Wave Surface Model</h2>
              </div>
              <p className="text-sm text-charcoal-light mt-1">
                Read-only map of the Wave modules, destinations, and account families FAB routes against.
              </p>
            </div>
            <div className="space-y-3 lg:text-right">
              <div className="text-xs text-charcoal-light max-w-xl">
                {waveSurface.data?.capturedFrom || "Loading Wave model..."}
              </div>
              {waveParity.data && (
                <div className="flex flex-wrap justify-start lg:justify-end gap-2">
                  <span className="text-xs px-2 py-1 rounded-lg bg-teal/10 text-teal">
                    {waveParity.data.surfaces} surfaces
                  </span>
                  <span className="text-xs px-2 py-1 rounded-lg bg-sand/60 text-charcoal">
                    {waveParity.data.menuItems} menu items
                  </span>
                  <span className="text-xs px-2 py-1 rounded-lg bg-teal/10 text-teal">
                    {waveParity.data.syncContracts} sync contracts
                  </span>
                  <span className="text-xs px-2 py-1 rounded-lg bg-sand/60 text-charcoal">
                    {waveParity.data.featurePages} pages
                  </span>
                  <span className="text-xs px-2 py-1 rounded-lg bg-sand/60 text-charcoal">
                    {waveParity.data.observedControls} controls
                  </span>
                  <span className="text-xs px-2 py-1 rounded-lg bg-sage-light text-sage">
                    {waveParity.data.actions} actions
                  </span>
                  <span className="text-xs px-2 py-1 rounded-lg bg-amber-50 text-amber-700">
                    {waveParity.data.actionsBySafety.requires_confirmation} confirmed
                  </span>
                </div>
              )}
            </div>
          </div>

          {waveSurface.isLoading ? (
            <div className="p-8 text-center text-charcoal-light">Loading Wave model...</div>
          ) : waveSurface.data ? (
            <div className="p-6 space-y-6">
              <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-4">
                {waveSurface.data.modules.map((module) => (
                  <div key={module.id} className="border border-sand-dark/15 rounded-xl p-4 bg-sand/10">
                    <div className="text-sm font-semibold text-charcoal">{module.label}</div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {module.surfaces.map((surface) => (
                        <span
                          key={surface.id}
                          className="text-xs px-2 py-1 rounded-lg bg-white border border-sand-dark/15 text-charcoal"
                          title={surface.routeTemplate}
                        >
                          {surface.label}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>

              <div className="grid xl:grid-cols-[0.9fr_1.1fr] gap-6">
                <div>
                  <h3 className="text-sm font-semibold text-charcoal mb-3">Wave Menu Map</h3>
                  <div className="space-y-3">
                    {waveSurface.data.menuInventory.map((group) => (
                      <div key={group.id} className="rounded-xl border border-sand-dark/15 p-4 bg-sand/10">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="text-sm font-semibold text-charcoal">{group.label}</div>
                            <div className="text-xs text-charcoal-light mt-1">{group.entrypoint}</div>
                          </div>
                          <span className="text-[11px] px-2 py-1 rounded-lg bg-white border border-sand-dark/15 text-charcoal">
                            {group.items.length}
                          </span>
                        </div>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {group.items.map((item) => (
                            <span
                              key={`${group.id}-${item.label}`}
                              className={`text-[11px] px-2 py-1 rounded-md ${waveSafetyClass(item.safety)}`}
                              title={`${item.routeTemplate} - ${item.notes}`}
                            >
                              {item.label}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-charcoal mb-3">FAB Source of Truth Contracts</h3>
                  <div className="space-y-3">
                    {waveSurface.data.syncContracts.map((contract) => (
                      <div key={contract.id} className="rounded-xl border border-sand-dark/15 p-4 bg-white">
                        <div className="text-sm font-semibold text-charcoal">{contract.domain}</div>
                        <div className="grid md:grid-cols-2 gap-3 mt-3">
                          <div>
                            <div className="text-[11px] uppercase text-charcoal-light">FAB owns</div>
                            <div className="mt-1 flex flex-wrap gap-1.5">
                              {contract.fabOwns.slice(0, 4).map((item) => (
                                <span key={item} className="text-[11px] px-2 py-1 rounded-md bg-teal/10 text-teal">
                                  {item}
                                </span>
                              ))}
                            </div>
                          </div>
                          <div>
                            <div className="text-[11px] uppercase text-charcoal-light">Wave owns</div>
                            <div className="mt-1 flex flex-wrap gap-1.5">
                              {contract.waveOwns.slice(0, 4).map((item) => (
                                <span key={item} className="text-[11px] px-2 py-1 rounded-md bg-sage-light text-sage">
                                  {item}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>
                        <div className="text-xs text-charcoal-light mt-3">{contract.conflictResolution}</div>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {contract.confirmationRequiredFor.slice(0, 5).map((item) => (
                            <span key={item} className="text-[11px] px-2 py-1 rounded-md bg-amber-50 text-amber-700">
                              {item}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between gap-3 mb-3">
                  <h3 className="text-sm font-semibold text-charcoal">Observed Wave Pages & Controls</h3>
                  {waveParity.data && (
                    <div className="flex flex-wrap justify-end gap-2">
                      <span className="text-[11px] px-2 py-1 rounded-lg bg-sage-light text-sage">
                        {waveParity.data.pagesByAutomationMode.observe} observe
                      </span>
                      <span className="text-[11px] px-2 py-1 rounded-lg bg-teal/10 text-teal">
                        {waveParity.data.pagesByAutomationMode.safe_draft} draft
                      </span>
                      <span className="text-[11px] px-2 py-1 rounded-lg bg-amber-50 text-amber-700">
                        {waveParity.data.pagesByAutomationMode.confirmed_execute +
                          waveParity.data.pagesByAutomationMode.credential_owner} gated
                      </span>
                    </div>
                  )}
                </div>
                <div className="grid lg:grid-cols-2 gap-4">
                  {waveSurface.data.featureInventory.map((page) => (
                    <div key={page.id} className="rounded-xl border border-sand-dark/15 p-4 bg-white">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="text-sm font-semibold text-charcoal">{page.label}</div>
                          <div className="text-xs text-charcoal-light mt-1 truncate" title={page.observedRoute}>
                            {page.observedRoute}
                          </div>
                        </div>
                        <span className={`text-[11px] px-2 py-1 rounded-lg shrink-0 ${waveAutomationModeClass(page.automationMode)}`}>
                          {page.automationMode.replaceAll("_", " ")}
                        </span>
                      </div>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {page.controls.slice(0, 6).map((control) => (
                          <span
                            key={`${page.id}-${control.label}-${control.kind}`}
                            className={`text-[11px] px-2 py-1 rounded-md ${waveSafetyClass(control.safety)}`}
                            title={control.notes}
                          >
                            {control.label}
                          </span>
                        ))}
                        {page.controls.length > 6 && (
                          <span className="text-[11px] px-2 py-1 rounded-md bg-sand/60 text-charcoal">
                            +{page.controls.length - 6} more
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-charcoal-light mt-3">{page.reviewGate}</div>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {page.fabCoverage.slice(0, 3).map((coverage) => (
                          <span key={coverage} className="text-[11px] px-2 py-1 rounded-md bg-sand/60 text-charcoal">
                            {coverage}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="grid lg:grid-cols-[1.2fr_0.8fr] gap-6">
                <div>
                  <h3 className="text-sm font-semibold text-charcoal mb-3">Autonomous Routing Rules</h3>
                  <div className="overflow-x-auto rounded-xl border border-sand-dark/15">
                    <table className="w-full">
                      <thead>
                        <tr className="bg-sand/30 border-b border-sand-dark/10">
                          <th className="text-left text-xs font-medium text-charcoal-light uppercase tracking-wider px-4 py-3">
                            Documents
                          </th>
                          <th className="text-left text-xs font-medium text-charcoal-light uppercase tracking-wider px-4 py-3">
                            Target
                          </th>
                          <th className="text-left text-xs font-medium text-charcoal-light uppercase tracking-wider px-4 py-3">
                            Fallback
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-sand-dark/10 bg-white">
                        {waveSurface.data.documentRoutingRules.map((rule) => (
                          <tr key={rule.targetSurfaceId + rule.documentTypes.join("-")}>
                            <td className="px-4 py-3 text-sm text-charcoal">
                              {rule.documentTypes.map((type) => type.replaceAll("_", " ")).join(", ")}
                              <div className="text-xs text-charcoal-light mt-1">{rule.reason}</div>
                            </td>
                            <td className="px-4 py-3 text-sm font-medium text-teal">
                              {rule.targetSurfaceId.replaceAll("_", " ")}
                            </td>
                            <td className="px-4 py-3 text-sm text-charcoal">
                              {rule.fallbackSurfaceId.replaceAll("_", " ")}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <h3 className="text-sm font-semibold text-charcoal mb-3">Account Families</h3>
                    <div className="space-y-2">
                      {waveSurface.data.accountFamilies.map((family) => (
                        <div key={family.type} className="rounded-xl border border-sand-dark/15 p-3">
                          <div className="flex items-center justify-between gap-3">
                            <span className="text-sm font-medium text-charcoal">{family.label}</span>
                            <span className="text-[11px] uppercase text-charcoal-light">{family.type}</span>
                          </div>
                          <div className="text-xs text-charcoal-light mt-1">{family.fabMapping}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h3 className="text-sm font-semibold text-charcoal mb-3">Integration Channels</h3>
                    <div className="flex flex-wrap gap-2">
                      {waveSurface.data.integrationChannels.map((channel) => (
                        <span key={channel} className="text-xs px-2 py-1 rounded-lg bg-teal/10 text-teal">
                          {channel}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-sm font-semibold text-charcoal mb-3">Wave Action Coverage</h3>
                <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">
                  {waveSurface.data.actions.map((action) => (
                    <div key={action.id} className="rounded-xl border border-sand-dark/15 p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="text-sm font-medium text-charcoal">{action.label}</div>
                          <div className="text-xs text-charcoal-light mt-1">
                            {action.surfaceId.replaceAll("_", " ")} / {action.mode}
                          </div>
                        </div>
                        <span
                          className={`text-[11px] px-2 py-1 rounded-lg shrink-0 ${waveSafetyClass(action.safety)}`}
                        >
                          {action.safety.replaceAll("_", " ")}
                        </span>
                      </div>
                      <div className="text-xs text-charcoal-light mt-3">
                        Required: {action.requiredFields.length ? action.requiredFields.join(", ") : "none"}
                      </div>
                      <div className="text-xs text-charcoal-light mt-1">{action.workflowNotes}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-charcoal-light">Wave model unavailable.</div>
          )}
        </section>

        <section className="bg-white rounded-2xl border border-sand-dark/15 shadow-sm overflow-hidden">
          <div className="p-6 border-b border-sand-dark/10 flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <DatabaseZap className="w-5 h-5 text-teal" />
                <h2 className="text-lg font-semibold text-charcoal">MijnGeldzaken Master Ledger</h2>
              </div>
              <p className="text-sm text-charcoal-light mt-1">
                Downstream household-ledger, budget, document-vault, and learning model for Category A entries.
              </p>
            </div>
            <div className="space-y-3 lg:text-right">
              <div className="text-xs text-charcoal-light max-w-xl">
                {mijngeldzakenSurface.data?.capturedFrom || "Loading MijnGeldzaken model..."}
              </div>
              {mijngeldzakenParity.data && (
                <div className="flex flex-wrap justify-start lg:justify-end gap-2">
                  <span className="text-xs px-2 py-1 rounded-lg bg-teal/10 text-teal">
                    {mijngeldzakenParity.data.surfaces} surfaces
                  </span>
                  <span className="text-xs px-2 py-1 rounded-lg bg-sand/60 text-charcoal">
                    {mijngeldzakenParity.data.syncContracts} sync contracts
                  </span>
                  <span className="text-xs px-2 py-1 rounded-lg bg-sand/60 text-charcoal">
                    {mijngeldzakenParity.data.featurePages} pages
                  </span>
                  <span className="text-xs px-2 py-1 rounded-lg bg-sand/60 text-charcoal">
                    {mijngeldzakenParity.data.observedControls} controls
                  </span>
                  <span className="text-xs px-2 py-1 rounded-lg bg-sage-light text-sage">
                    {mijngeldzakenParity.data.actions} actions
                  </span>
                  <span className="text-xs px-2 py-1 rounded-lg bg-amber-50 text-amber-700">
                    {mijngeldzakenParity.data.actionsBySafety.requires_confirmation} confirmed
                  </span>
                </div>
              )}
            </div>
          </div>

          {mijngeldzakenSurface.isLoading ? (
            <div className="p-8 text-center text-charcoal-light">Loading MijnGeldzaken model...</div>
          ) : mijngeldzakenSurface.data ? (
            <div className="p-6 space-y-6">
              <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-4">
                {mijngeldzakenSurface.data.modules.map((module) => (
                  <div key={module.id} className="border border-sand-dark/15 rounded-xl p-4 bg-sand/10">
                    <div className="text-sm font-semibold text-charcoal">{module.label}</div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {module.surfaces.map((surface) => (
                        <span
                          key={`${module.id}-${surface}`}
                          className="text-xs px-2 py-1 rounded-lg bg-white border border-sand-dark/15 text-charcoal"
                        >
                          {surface.replaceAll("_", " ")}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>

              <div className="grid xl:grid-cols-[0.9fr_1.1fr] gap-6">
                <div>
                  <h3 className="text-sm font-semibold text-charcoal mb-3">FAB Source of Truth Contracts</h3>
                  <div className="space-y-3">
                    {mijngeldzakenSurface.data.syncContracts.map((contract) => (
                      <div key={contract.id} className="rounded-xl border border-sand-dark/15 p-4 bg-white">
                        <div className="text-sm font-semibold text-charcoal">{contract.domain}</div>
                        <div className="grid md:grid-cols-2 gap-3 mt-3">
                          <div>
                            <div className="text-[11px] uppercase text-charcoal-light">FAB owns</div>
                            <div className="mt-1 flex flex-wrap gap-1.5">
                              {contract.fabOwns.slice(0, 4).map((item) => (
                                <span key={item} className="text-[11px] px-2 py-1 rounded-md bg-teal/10 text-teal">
                                  {item}
                                </span>
                              ))}
                            </div>
                          </div>
                          <div>
                            <div className="text-[11px] uppercase text-charcoal-light">MijnGeldzaken owns</div>
                            <div className="mt-1 flex flex-wrap gap-1.5">
                              {contract.mijngeldzakenOwns.slice(0, 4).map((item) => (
                                <span key={item} className="text-[11px] px-2 py-1 rounded-md bg-sage-light text-sage">
                                  {item}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>
                        <div className="text-xs text-charcoal-light mt-3">{contract.conflictResolution}</div>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {contract.confirmationRequiredFor.map((item) => (
                            <span key={item} className="text-[11px] px-2 py-1 rounded-md bg-amber-50 text-amber-700">
                              {item}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between gap-3 mb-3">
                    <h3 className="text-sm font-semibold text-charcoal">Observed Pages & Controls</h3>
                    {mijngeldzakenParity.data && (
                      <div className="flex flex-wrap justify-end gap-2">
                        <span className="text-[11px] px-2 py-1 rounded-lg bg-sage-light text-sage">
                          {mijngeldzakenParity.data.pagesByAutomationMode.observe +
                            mijngeldzakenParity.data.pagesByAutomationMode.read_only} observe
                        </span>
                        <span className="text-[11px] px-2 py-1 rounded-lg bg-teal/10 text-teal">
                          {mijngeldzakenParity.data.pagesByAutomationMode.safe_draft} draft
                        </span>
                        <span className="text-[11px] px-2 py-1 rounded-lg bg-amber-50 text-amber-700">
                          {mijngeldzakenParity.data.pagesByAutomationMode.requires_user_auth} auth
                        </span>
                      </div>
                    )}
                  </div>
                  <div className="grid lg:grid-cols-2 gap-4">
                    {mijngeldzakenSurface.data.featureInventory.map((page) => (
                      <div key={page.id} className="rounded-xl border border-sand-dark/15 p-4 bg-white">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="text-sm font-semibold text-charcoal">{page.label}</div>
                            <div className="text-xs text-charcoal-light mt-1 truncate">
                              {page.observedFrom || page.surfaceId.replaceAll("_", " ")}
                            </div>
                          </div>
                          <span className={`text-[11px] px-2 py-1 rounded-lg shrink-0 ${waveAutomationModeClass(page.automationMode)}`}>
                            {page.automationMode.replaceAll("_", " ")}
                          </span>
                        </div>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {page.controls.slice(0, 6).map((control) => (
                            <span
                              key={`${page.id}-${control.label}-${control.kind}`}
                              className={`text-[11px] px-2 py-1 rounded-md ${waveSafetyClass(control.safety)}`}
                            >
                              {control.label}
                            </span>
                          ))}
                          {page.controls.length > 6 && (
                            <span className="text-[11px] px-2 py-1 rounded-md bg-sand/60 text-charcoal">
                              +{page.controls.length - 6} more
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-charcoal-light mt-3">{page.reviewGate}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-sm font-semibold text-charcoal mb-3">MijnGeldzaken Action Coverage</h3>
                <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">
                  {mijngeldzakenSurface.data.actions.map((action) => (
                    <div key={action.id} className="rounded-xl border border-sand-dark/15 p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="text-sm font-medium text-charcoal">{action.label}</div>
                          <div className="text-xs text-charcoal-light mt-1">
                            {action.surfaceId.replaceAll("_", " ")} / {action.mode}
                          </div>
                        </div>
                        <span className={`text-[11px] px-2 py-1 rounded-lg shrink-0 ${waveSafetyClass(action.safety)}`}>
                          {action.safety.replaceAll("_", " ")}
                        </span>
                      </div>
                      <div className="text-xs text-charcoal-light mt-3">
                        Required: {action.requiredFields.length ? action.requiredFields.join(", ") : "none"}
                      </div>
                      <div className="text-xs text-charcoal-light mt-1">{action.workflowNotes}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-charcoal-light">MijnGeldzaken model unavailable.</div>
          )}
        </section>

        <div className="grid xl:grid-cols-[1fr_360px] gap-6">
          <section className="bg-white rounded-2xl border border-sand-dark/15 shadow-sm overflow-hidden">
            <div className="p-6 border-b border-sand-dark/10 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-charcoal">Manual Review Backlog</h2>
                <p className="text-sm text-charcoal-light mt-1">
                  Resolve extraction, categorization, duplicate, and routing exceptions.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <ListFilter className="w-4 h-4 text-charcoal-light" />
                <select
                  value={statusFilter}
                  onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
                  className="px-3 py-2 rounded-xl border border-sand-dark/30 bg-white text-charcoal text-sm focus:outline-none focus:ring-2 focus:ring-teal/30 focus:border-teal"
                >
                  <option value="all">All statuses</option>
                  {Object.entries(reviewStatusLabels).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {reviewQueue.isLoading ? (
              <div className="p-12 text-center text-charcoal-light">Loading review queue...</div>
            ) : !reviewQueue.data?.length ? (
              <div className="p-12 text-center">
                <CheckCircle2 className="w-12 h-12 text-sage mx-auto mb-4" />
                <p className="text-charcoal font-medium">No review items match this filter</p>
                <p className="text-sm text-charcoal-light mt-1">Documents that need human decisions will appear here.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-sand-dark/10">
                      <th className="text-left text-xs font-medium text-charcoal-light uppercase tracking-wider px-6 py-3">
                        Document
                      </th>
                      <th className="text-left text-xs font-medium text-charcoal-light uppercase tracking-wider px-6 py-3">
                        Reason
                      </th>
                      <th className="text-left text-xs font-medium text-charcoal-light uppercase tracking-wider px-6 py-3">
                        Status
                      </th>
                      <th className="text-right text-xs font-medium text-charcoal-light uppercase tracking-wider px-6 py-3">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-sand-dark/10">
                    {reviewQueue.data.map((item) => (
                      <tr key={item.id} className="hover:bg-sand/20 transition-colors align-top">
                        <td className="px-6 py-4">
                          <div className="text-sm font-medium text-charcoal">
                            {item.document?.originalFilename || `Document #${item.documentId || "unknown"}`}
                          </div>
                          <div className="text-xs text-charcoal-light mt-1">
                            {item.document?.source || "unknown source"}
                            {item.document?.vendorName ? ` / ${item.document.vendorName}` : ""}
                            {item.document?.category ? ` / ${item.document.category}` : ""}
                          </div>
                        </td>
                        <td className="px-6 py-4 max-w-sm">
                          <div className="text-sm text-charcoal">{item.reason}</div>
                          {item.details && (
                            <p className="text-xs text-charcoal-light mt-1 line-clamp-2">{item.details}</p>
                          )}
                        </td>
                        <td className="px-6 py-4">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-sand/60 text-charcoal">
                            {reviewStatusLabels[item.status as ReviewStatus] || item.status}
                          </span>
                          <div className="text-xs text-charcoal-light mt-2">
                            {new Date(item.createdAt).toLocaleDateString()}
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex justify-end gap-2">
                            {item.status === "pending" && (
                              <Button
                                size="sm"
                                variant="outline"
                                className="rounded-xl border-teal/20 text-teal hover:bg-teal/5"
                                disabled={updateReviewStatus.isPending}
                                onClick={() => updateStatus(item.id, "in_review")}
                              >
                                <Clock className="w-4 h-4 mr-1" />
                                Start
                              </Button>
                            )}
                            {(item.status === "pending" || item.status === "in_review") && (
                              <>
                                <Button
                                  size="sm"
                                  className="rounded-xl bg-teal hover:bg-teal-light text-white"
                                  disabled={updateReviewStatus.isPending}
                                  onClick={() => updateStatus(item.id, "approved", "Approved from operations dashboard")}
                                >
                                  <CheckCircle2 className="w-4 h-4 mr-1" />
                                  Approve
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  className="rounded-xl border-red-200 text-red-600 hover:bg-red-50"
                                  disabled={updateReviewStatus.isPending}
                                  onClick={() => updateStatus(item.id, "rejected", "Rejected from operations dashboard")}
                                >
                                  <XCircle className="w-4 h-4 mr-1" />
                                  Reject
                                </Button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <div className="space-y-6">
            <section className="bg-white rounded-2xl border border-sand-dark/15 shadow-sm overflow-hidden">
              <div className="p-6 border-b border-sand-dark/10">
                <div className="flex items-center gap-2">
                  <DatabaseZap className="w-5 h-5 text-teal" />
                  <h2 className="text-lg font-semibold text-charcoal">Automation Master Ledger</h2>
                </div>
                <p className="text-sm text-charcoal-light mt-1">
                  Checksum-bound downstream state across Wave and MijnGeldzaken workflow operations.
                </p>
              </div>
              {automationMasterLedger.isLoading ? (
                <div className="p-6 text-center text-charcoal-light">Loading...</div>
              ) : !automationMasterLedger.data?.summary.totalRows ? (
                <div className="p-6 text-center text-sm text-charcoal-light">
                  No autonomous workflow operations have been projected yet.
                </div>
              ) : (
                <div className="p-5 space-y-4">
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div className="rounded-xl bg-sand/30 p-3">
                      <div className="text-sm font-semibold text-charcoal">{automationMasterLedger.data.summary.totalRows}</div>
                      <div className="text-[11px] text-charcoal-light">Rows</div>
                    </div>
                    <div className="rounded-xl bg-sand/30 p-3">
                      <div className="text-sm font-semibold text-charcoal">{automationMasterLedger.data.summary.blockedRows}</div>
                      <div className="text-[11px] text-charcoal-light">Blocked</div>
                    </div>
                    <div className="rounded-xl bg-sand/30 p-3">
                      <div className="text-sm font-semibold text-charcoal">
                        {automationMasterLedger.data.summary.readyForExternalExecution}
                      </div>
                      <div className="text-[11px] text-charcoal-light">Executable</div>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(automationMasterLedger.data.summary.byTargetSystem).map(([target, targetSummary]) => (
                      <span
                        key={target}
                        className="text-[11px] px-2 py-1 rounded-md bg-white border border-sand-dark/15 text-charcoal"
                      >
                        {target === "mijngeldzaken" ? "MijnGeldzaken" : "Wave"} {targetSummary.rows}
                      </span>
                    ))}
                    {Object.entries(automationMasterLedger.data.summary.downstreamStatuses).slice(0, 4).map(([status, count]) => (
                      <span key={status} className={`text-[11px] px-2 py-1 rounded-md ${workflowStatusClass(status)}`}>
                        {status.replaceAll("_", " ")} {count}
                      </span>
                    ))}
                  </div>
                  <div className="rounded-lg bg-sand/20 px-3 py-2">
                    <div className="text-[11px] text-charcoal-light">Ledger checksum</div>
                    <div className="font-mono text-xs text-charcoal truncate">
                      {automationMasterLedger.data.ledgerChecksum}
                    </div>
                  </div>
                </div>
              )}
            </section>

            <section className="bg-white rounded-2xl border border-sand-dark/15 shadow-sm overflow-hidden">
              <div className="p-6 border-b border-sand-dark/10">
                <div className="flex items-center gap-2">
                  <Bot className="w-5 h-5 text-teal" />
                  <h2 className="text-lg font-semibold text-charcoal">Autonomous Downstream Runs</h2>
                </div>
                <p className="text-sm text-charcoal-light mt-1">Persisted workflow batches and downstream operation traces.</p>
              </div>
              <div className="divide-y divide-sand-dark/10">
                {autonomousWorkflowRuns.isLoading ? (
                  <div className="p-6 text-center text-charcoal-light">Loading...</div>
                ) : !autonomousWorkflowRuns.data?.length ? (
                  <div className="p-6 text-center text-sm text-charcoal-light">
                    No autonomous downstream runs have been recorded yet.
                  </div>
                ) : (
                  autonomousWorkflowRuns.data.map((run) => (
                    <div key={run.id} className="p-5">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="text-sm font-medium text-charcoal">Run #{run.id}</div>
                          <div className="text-xs text-charcoal-light mt-1 truncate">
                            {workflowLabels[run.workflowId as AutomationWorkflowId] ?? run.workflowId} / {run.mode}
                          </div>
                        </div>
                        <div className="flex flex-col items-end gap-2 shrink-0">
                          <span className={`text-xs px-2 py-1 rounded-full ${workflowStatusClass(run.status)}`}>
                            {run.status.replaceAll("_", " ")}
                          </span>
                          {["queued", "running"].includes(run.status) && (
                            <div className="flex flex-col gap-1">
                              <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                disabled={
                                  claimAutomationWorkflowOperation.isPending ||
                                  runAutomationWorkflowExecutorCycle.isPending ||
                                  runAutomationWorkflowExecutorLoop.isPending
                                }
                                onClick={() => claimNextOperation(run.id)}
                                className="h-7 rounded-lg border-teal/20 text-teal hover:bg-teal/5 text-xs"
                              >
                                <PlayCircle className="w-3.5 h-3.5" />
                                Claim next
                              </Button>
                              <Button
                                type="button"
                                size="sm"
                                disabled={
                                  claimAutomationWorkflowOperation.isPending ||
                                  runAutomationWorkflowExecutorCycle.isPending ||
                                  runAutomationWorkflowExecutorLoop.isPending
                                }
                                onClick={() => runExecutorCycle(run.id)}
                                className="h-7 rounded-lg bg-teal hover:bg-teal-light text-white text-xs"
                              >
                                <RefreshCw className="w-3.5 h-3.5" />
                                Run cycle
                              </Button>
                              <Button
                                type="button"
                                size="sm"
                                disabled={
                                  claimAutomationWorkflowOperation.isPending ||
                                  runAutomationWorkflowExecutorCycle.isPending ||
                                  runAutomationWorkflowExecutorLoop.isPending
                                }
                                onClick={() => runExecutorLoop(run.id)}
                                className="h-7 rounded-lg bg-sage hover:bg-sage/90 text-white text-xs"
                              >
                                <RefreshCw className="w-3.5 h-3.5" />
                                Run safe loop
                              </Button>
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="grid grid-cols-3 gap-2 mt-4 text-center">
                        <div className="rounded-xl bg-sand/30 p-3">
                          <div className="text-sm font-semibold text-charcoal">{run.operationCount}</div>
                          <div className="text-[11px] text-charcoal-light">Ops</div>
                        </div>
                        <div className="rounded-xl bg-sand/30 p-3">
                          <div className="text-sm font-semibold text-charcoal">{run.documentsNeedingReview}</div>
                          <div className="text-[11px] text-charcoal-light">Review</div>
                        </div>
                        <div className="rounded-xl bg-sand/30 p-3">
                          <div className="text-sm font-semibold text-charcoal">{run.blockingActions.length}</div>
                          <div className="text-[11px] text-charcoal-light">Blocked</div>
                        </div>
                      </div>

                      {run.masterLedger && (
                        <div className="mt-3 rounded-lg bg-sand/20 px-3 py-2">
                          <div className="flex items-center justify-between gap-3">
                            <div>
                              <div className="text-[11px] text-charcoal-light">Master ledger</div>
                              <div className="text-xs text-charcoal">
                                {run.masterLedger.totalRows} rows / {run.masterLedger.blockedRows} blocked /{" "}
                                {run.masterLedger.readyForExternalExecution} executable
                              </div>
                            </div>
                            <span className="font-mono text-[11px] text-charcoal shrink-0">
                              {run.masterLedger.ledgerChecksum.slice(0, 12)}
                            </span>
                          </div>
                        </div>
                      )}

                      <div className="mt-4 flex flex-wrap gap-2">
                        <span className={`text-[11px] px-2 py-1 rounded-md ${workflowStatusClass(run.planStatus)}`}>
                          {run.planStatus.replaceAll("_", " ")}
                        </span>
                        {(run.targetSystems ?? []).map((target) => (
                          <span
                            key={`${run.id}-${target}`}
                            className="text-[11px] px-2 py-1 rounded-md bg-white border border-sand-dark/15 text-charcoal"
                          >
                            {target === "mijngeldzaken" ? "MijnGeldzaken" : "Wave"}{" "}
                            {run.targetBreakdown?.[target] ?? 0}
                          </span>
                        ))}
                        <span
                          className={`text-[11px] px-2 py-1 rounded-md ${
                            run.canRunAutonomously ? "bg-sage-light text-sage" : "bg-amber-50 text-amber-700"
                          }`}
                        >
                          {run.canRunAutonomously ? "autonomous-ready" : "policy-gated"}
                        </span>
                      </div>

                      {run.operations.length > 0 && (
                        <div className="mt-4 space-y-2">
                          {run.operations.slice(0, 3).map((operation) => (
                            <div
                              key={`${run.id}-${operation.operationId}`}
                              className="rounded-lg bg-sand/20 px-3 py-2"
                            >
                              <div className="flex items-center justify-between gap-2">
                                <span className="text-xs font-medium text-charcoal truncate">
                                  {operation.actionId.replaceAll("_", " ")}
                                </span>
                                <div className="flex items-center gap-1">
                                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-white border border-sand-dark/15 text-charcoal">
                                    {operation.targetSystem === "mijngeldzaken" ? "MGZ" : "Wave"}
                                  </span>
                                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${workflowStatusClass(operation.status)}`}>
                                    {operation.status.replaceAll("_", " ")}
                                  </span>
                                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${waveSafetyClass(operation.safety)}`}>
                                    {operation.safety.replaceAll("_", " ")}
                                  </span>
                                </div>
                              </div>
                              <div className="text-[11px] text-charcoal-light mt-1 truncate">{operation.stepId}</div>
                              {operation.masterLedgerChecksum && (
                                <div className="mt-2 flex flex-wrap items-center gap-2">
                                  <span className="text-[11px] text-charcoal-light truncate">
                                    Master ledger {operation.masterLedgerDraftType || "draft"} /{" "}
                                    <span className="font-mono">{operation.masterLedgerChecksum.slice(0, 12)}</span>
                                  </span>
                                  <Button
                                    type="button"
                                    variant="outline"
                                    size="sm"
                                    className="h-6 px-2 text-[10px]"
                                    onClick={() => requestDraftArtifact(run.id, operation.operationId, "json")}
                                  >
                                    JSON
                                  </Button>
                                  {operation.masterLedgerDraftType === "transaction_import" && (
                                    <Button
                                      type="button"
                                      variant="outline"
                                      size="sm"
                                      className="h-6 px-2 text-[10px]"
                                      onClick={() => requestDraftArtifact(run.id, operation.operationId, "csv")}
                                    >
                                      CSV
                                    </Button>
                                  )}
                                </div>
                              )}
                              {(operation.actor || operation.leaseExpiresAt) && (
                                <div className="text-[11px] text-charcoal-light mt-1 truncate">
                                  {operation.actor ? `Actor: ${operation.actor}` : ""}
                                  {operation.actor && operation.leaseExpiresAt ? " / " : ""}
                                  {operation.leaseExpiresAt
                                    ? `Lease: ${new Date(operation.leaseExpiresAt).toLocaleTimeString()}`
                                    : ""}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}

                      {draftArtifactRequest?.workflowRunId === run.id && (
                        <div className="mt-4 rounded-lg border border-sand-dark/15 bg-white p-3">
                          <div className="flex items-center justify-between gap-3">
                            <div>
                              <div className="text-xs font-semibold text-charcoal">Master ledger artifact</div>
                              <div className="text-[11px] text-charcoal-light font-mono truncate">
                                {draftArtifactRequest.operationId} / {draftArtifactRequest.format}
                              </div>
                            </div>
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              className="h-7 px-2 text-[11px]"
                              onClick={() => setDraftArtifactRequest(null)}
                            >
                              Close
                            </Button>
                          </div>
                          {draftArtifact.isLoading ? (
                            <div className="mt-3 text-xs text-charcoal-light">Loading artifact...</div>
                          ) : draftArtifact.data && draftArtifact.data.status === "prepared" && "artifact" in draftArtifact.data ? (
                            <div className="mt-3">
                              <div className="mb-2 flex flex-wrap gap-2 text-[11px] text-charcoal-light">
                                <span>{draftArtifact.data.artifact.filename}</span>
                                <span className="font-mono">{draftArtifact.data.artifact.checksum.slice(0, 12)}</span>
                                <span>{draftArtifact.data.artifact.externalSubmission}</span>
                              </div>
                              <pre className="max-h-48 overflow-auto rounded-md bg-sand/30 p-3 text-[11px] text-charcoal whitespace-pre-wrap">
                                {draftArtifactText()}
                              </pre>
                            </div>
                          ) : (
                            <div className="mt-3 text-xs text-amber-700">
                              {draftArtifact.data ? draftArtifactText() : "Artifact unavailable."}
                            </div>
                          )}
                        </div>
                      )}

                      {(run.missingSignals.length > 0 || run.blockingActions.length > 0) && (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {run.missingSignals.slice(0, 3).map((signal) => (
                            <span key={signal} className="text-[11px] px-2 py-1 rounded-md bg-amber-50 text-amber-700">
                              {signal.replaceAll("_", " ")}
                            </span>
                          ))}
                          {run.blockingActions.slice(0, 2).map((operation) => (
                            <span
                              key={`${run.id}-blocked-${operation.operationId}`}
                              className="text-[11px] px-2 py-1 rounded-md bg-red-50 text-red-600"
                            >
                              {operation.actionId.replaceAll("_", " ")}
                            </span>
                          ))}
                        </div>
                      )}

                      <div className="text-xs text-charcoal-light mt-3">
                        {new Date(run.createdAt).toLocaleString()}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </section>

            <section className="bg-white rounded-2xl border border-sand-dark/15 shadow-sm overflow-hidden">
              <div className="p-6 border-b border-sand-dark/10">
                <h2 className="text-lg font-semibold text-charcoal">Recent Workflow Runs</h2>
                <p className="text-sm text-charcoal-light mt-1">Latest import and processing activity.</p>
              </div>
              <div className="divide-y divide-sand-dark/10">
                {workflowRuns.isLoading ? (
                  <div className="p-6 text-center text-charcoal-light">Loading...</div>
                ) : !workflowRuns.data?.length ? (
                  <div className="p-6 text-center text-sm text-charcoal-light">
                    No workflow runs have been recorded yet.
                  </div>
                ) : (
                  workflowRuns.data.map((run) => (
                    <div key={run.id} className="p-5">
                      <div className="flex items-center justify-between gap-3">
                        <div className="text-sm font-medium text-charcoal">Run #{run.id}</div>
                        <span className="text-xs px-2 py-1 rounded-full bg-sand/60 text-charcoal">
                          {run.status.replaceAll("_", " ")}
                        </span>
                      </div>
                      <div className="grid grid-cols-3 gap-2 mt-4 text-center">
                        <div className="rounded-xl bg-sand/30 p-3">
                          <div className="text-sm font-semibold text-charcoal">{run.documentsImported}</div>
                          <div className="text-[11px] text-charcoal-light">Imported</div>
                        </div>
                        <div className="rounded-xl bg-sand/30 p-3">
                          <div className="text-sm font-semibold text-charcoal">{run.documentsProcessed}</div>
                          <div className="text-[11px] text-charcoal-light">Processed</div>
                        </div>
                        <div className="rounded-xl bg-sand/30 p-3">
                          <div className="text-sm font-semibold text-charcoal">{run.documentsNeedingReview}</div>
                          <div className="text-[11px] text-charcoal-light">Review</div>
                        </div>
                      </div>
                      <div className="text-xs text-charcoal-light mt-3">
                        {new Date(run.createdAt).toLocaleString()}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </section>

            <section className="bg-white rounded-2xl border border-sand-dark/15 shadow-sm overflow-hidden">
              <div className="p-6 border-b border-sand-dark/10">
                <div className="flex items-center gap-2">
                  <Activity className="w-5 h-5 text-teal" />
                  <h2 className="text-lg font-semibold text-charcoal">Audit Timeline</h2>
                </div>
                <p className="text-sm text-charcoal-light mt-1">Autonomous decisions and service actions.</p>
              </div>
              <div className="divide-y divide-sand-dark/10">
                {auditEvents.isLoading ? (
                  <div className="p-6 text-center text-charcoal-light">Loading...</div>
                ) : !auditEvents.data?.length ? (
                  <div className="p-6 text-center text-sm text-charcoal-light">
                    No audit events have been recorded yet.
                  </div>
                ) : (
                  auditEvents.data.map((event) => (
                    <div key={event.id} className="p-5">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="text-sm font-medium text-charcoal truncate">
                            {event.action.replaceAll("_", " ")}
                          </div>
                          <div className="text-xs text-charcoal-light mt-1 truncate">
                            {event.entityType}
                            {event.entityId ? ` #${event.entityId}` : ""}
                          </div>
                        </div>
                        <span className="text-[11px] px-2 py-1 rounded-full bg-sand/60 text-charcoal shrink-0">
                          audit
                        </span>
                      </div>
                      <div className="text-xs text-charcoal-light mt-3">
                        {new Date(event.createdAt).toLocaleString()}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </section>

            <section className="bg-white rounded-2xl border border-sand-dark/15 shadow-sm overflow-hidden">
              <div className="p-6 border-b border-sand-dark/10">
                <div className="flex items-center gap-2">
                  <ArrowRightLeft className="w-5 h-5 text-teal" />
                  <h2 className="text-lg font-semibold text-charcoal">Recent Reconciliation</h2>
                </div>
                <p className="text-sm text-charcoal-light mt-1">Latest bank transaction matching outcomes.</p>
              </div>
              <div className="divide-y divide-sand-dark/10">
                {reconciliationMatches.isLoading ? (
                  <div className="p-6 text-center text-charcoal-light">Loading...</div>
                ) : !reconciliationMatches.data?.length ? (
                  <div className="p-6 text-center text-sm text-charcoal-light">
                    No reconciliation activity has been recorded yet.
                  </div>
                ) : (
                  reconciliationMatches.data.map((match) => (
                    <div key={match.id} className="p-5">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2 text-sm font-medium text-charcoal">
                            <Landmark className="w-4 h-4 text-charcoal-light shrink-0" />
                            <span className="truncate">{match.bankTransactionId}</span>
                          </div>
                          <div className="text-xs text-charcoal-light mt-1 truncate">
                            {match.document?.originalFilename || "No matched document"}
                          </div>
                        </div>
                        <span
                          className={`shrink-0 text-xs px-2 py-1 rounded-full ${reconciliationStatusClass(match.status)}`}
                        >
                          {reconciliationStatusLabels[match.status] || match.status}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-2 mt-4 text-center">
                        <div className="rounded-xl bg-sand/30 p-3">
                          <div className="text-sm font-semibold text-charcoal">
                            {match.confidenceScore ? `${Math.round(Number(match.confidenceScore) * 100)}%` : "-"}
                          </div>
                          <div className="text-[11px] text-charcoal-light">Confidence</div>
                        </div>
                        <div className="rounded-xl bg-sand/30 p-3">
                          <div className="text-sm font-semibold text-charcoal">
                            {match.amountDifference ?? "-"}
                          </div>
                          <div className="text-[11px] text-charcoal-light">Difference</div>
                        </div>
                      </div>

                      <div className="text-xs text-charcoal-light mt-3">
                        {new Date(match.createdAt).toLocaleString()}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </section>
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}
