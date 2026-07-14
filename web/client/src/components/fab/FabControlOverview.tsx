import {
  ArrowRight,
  BadgeCheck,
  BookCheck,
  Bot,
  CircleDollarSign,
  FileInput,
  FileSearch,
  ListChecks,
  MoreHorizontal,
  Play,
  ScanText,
  ShieldAlert,
} from "lucide-react";
import { asRecord, bool, count, humanize, records, statusTone, text, type FabCommandId, type FabRecord } from "./fabView";

type FabControlOverviewProps = {
  connected: boolean;
  metrics: {
    documents: number;
    pendingReview: number;
    unreconciled: number;
    exceptions: number;
    failedDocuments: number;
  };
  health: FabRecord;
  autonomy: FabRecord;
  closeReadiness: FabRecord;
  commandPending: boolean;
  onCommand: (commandId: FabCommandId) => void;
  onOpenCommands: () => void;
};

const pipelineStages = [
  { id: "collect", label: "Collect", detail: "Sources and intake", icon: FileInput, stages: ["collect"] },
  { id: "extract", label: "Extract", detail: "OCR and validation", icon: ScanText, stages: ["extract_validate"] },
  { id: "classify", label: "Classify", detail: "Rules and drafts", icon: ListChecks, stages: ["classify_post"] },
  { id: "reconcile", label: "Reconcile", detail: "Bank matching", icon: CircleDollarSign, stages: ["match_reconcile"] },
  { id: "close", label: "Close", detail: "Evidence and reports", icon: BookCheck, stages: ["close_report"] },
];

export function FabControlOverview({
  connected,
  metrics,
  health,
  autonomy,
  closeReadiness,
  commandPending,
  onCommand,
  onOpenCommands,
}: FabControlOverviewProps) {
  const operations = asRecord(health.operations);
  const healthStatus = text(operations.status || health.status, connected ? "unknown" : "disconnected");
  const autonomyStatus = text(autonomy.status, "unavailable");
  const closeStatus = text(closeReadiness.status, "unavailable");
  const actionRows = records(autonomy.actions);

  const metricRows = [
    {
      label: "Health",
      value: humanize(healthStatus),
      detail: `${count(operations.issueCount || records(operations.issues).length)} active signals`,
      icon: healthStatus === "ok" || healthStatus === "ready" ? BadgeCheck : ShieldAlert,
      tone: statusTone(healthStatus),
    },
    {
      label: "Review backlog",
      value: String(metrics.pendingReview),
      detail: `${metrics.exceptions} operating exceptions`,
      icon: FileSearch,
      tone: metrics.pendingReview > 0 ? "warn" as const : "good" as const,
    },
    {
      label: "Unreconciled",
      value: String(metrics.unreconciled),
      detail: "Documents and bank lines",
      icon: CircleDollarSign,
      tone: metrics.unreconciled > 0 ? "warn" as const : "good" as const,
    },
    {
      label: "Close readiness",
      value: humanize(closeStatus),
      detail: `${count(closeReadiness.blockingCount)} blocking gates`,
      icon: BookCheck,
      tone: statusTone(closeStatus),
    },
  ];

  return (
    <section id="control-room" className="fab-control-overview">
      <div className="fab-page-heading">
        <div>
          <div className="fab-eyebrow"><Bot aria-hidden="true" /> Autonomous bookkeeping control</div>
          <h1>Control room</h1>
          <p>Operate the local FAB ledger, review exceptions, and supervise downstream bookkeeping readiness.</p>
        </div>
        <div className="fab-heading-actions">
          <button className="fab-primary-button" onClick={() => onCommand("run_safe_cycle")} disabled={!connected || commandPending || !bool(autonomy.canRunAutonomously)}>
            <Play aria-hidden="true" /> Run safe cycle
          </button>
          <button className="fab-secondary-button" onClick={onOpenCommands} disabled={!connected}>
            <MoreHorizontal aria-hidden="true" /> More actions
          </button>
        </div>
      </div>

      <div className="fab-metric-strip" id="documents">
        {metricRows.map(({ label, value, detail, icon: Icon, tone }) => (
          <div className="fab-metric" key={label}>
            <div className={`fab-metric-icon tone-${tone}`}><Icon aria-hidden="true" /></div>
            <div><span>{label}</span><strong>{value}</strong><small>{detail}</small></div>
          </div>
        ))}
      </div>

      <div className="fab-section fab-pipeline-section">
        <div className="fab-section-heading">
          <div><span>Autonomous run</span><h2>Safe-cycle pipeline</h2></div>
          <span className={`fab-status-chip tone-${statusTone(autonomyStatus)}`}>{humanize(autonomyStatus)}</span>
        </div>
        <div className="fab-pipeline" aria-label="Autonomous bookkeeping stages">
          {pipelineStages.map((stage, index) => {
            const stageActions = actionRows.filter((action) => stage.stages.includes(text(action.stage, "")));
            const runnable = stageActions.filter((action) => bool(action.canRun)).length;
            const blocked = stageActions.filter((action) => text(action.blockedReason, "") !== "").length;
            const tone = autonomyStatus === "blocked" ? "bad" : runnable > 0 ? "good" : blocked > 0 ? "warn" : "neutral";
            const StageIcon = stage.icon;
            return (
              <div className="fab-pipeline-step" key={stage.id}>
                <div className={`fab-pipeline-node tone-${tone}`}><StageIcon aria-hidden="true" /></div>
                <div><strong>{stage.label}</strong><span>{stage.detail}</span><small>{runnable > 0 ? `${runnable} ready` : blocked > 0 ? `${blocked} gated` : "No work due"}</small></div>
                {index < pipelineStages.length - 1 && <ArrowRight className="fab-pipeline-arrow" aria-hidden="true" />}
              </div>
            );
          })}
        </div>
        <div className="fab-pipeline-note">
          <ShieldAlert aria-hidden="true" />
          <span><strong>External submission remains approval-gated.</strong> {text(autonomy.nextAction, "FAB will prepare local evidence and drafts only.")}</span>
        </div>
      </div>
    </section>
  );
}
