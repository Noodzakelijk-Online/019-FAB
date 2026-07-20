import {
  AlertCircle,
  ArrowRight,
  BookCheck,
  CheckCircle2,
  CircleDollarSign,
  Clock3,
  FileInput,
  ListChecks,
  Play,
  ScanText,
} from "lucide-react";
import { FabDataStatus, FabPanelStateMessage } from "./FabDataState";
import { useFabLocale } from "./fabLocale";
import {
  asRecord,
  bool,
  compactHumanize,
  count,
  durationBetween,
  exactDateTime,
  records,
  statusTone,
  text,
  type FabCommandId,
  type FabRecord,
  type FabResourceState,
} from "./fabView";

const pipelineStages = [
  { id: "collect", label: "Collect", labelNl: "Verzamelen", icon: FileInput, stages: ["collect"] },
  { id: "extract", label: "Extract & validate", labelNl: "Uitlezen en valideren", icon: ScanText, stages: ["extract_validate"] },
  { id: "classify", label: "Classify & draft", labelNl: "Classificeren en opstellen", icon: ListChecks, stages: ["classify_post"] },
  { id: "reconcile", label: "Reconcile", labelNl: "Afstemmen", icon: CircleDollarSign, stages: ["match_reconcile"] },
  { id: "close", label: "Close & report", labelNl: "Afsluiten en rapporteren", icon: BookCheck, stages: ["close_report"] },
];

type FabAutomationPanelProps = {
  autonomy: FabRecord;
  workflows: FabRecord[];
  autonomyResource?: FabResourceState;
  workflowResource?: FabResourceState;
  pendingCommand: FabCommandId | null;
  connected: boolean;
  onCommand: (commandId: FabCommandId) => void;
};

export function FabAutomationPanel({
  autonomy,
  workflows,
  autonomyResource,
  workflowResource,
  pendingCommand,
  connected,
  onCommand,
}: FabAutomationPanelProps) {
  const { lang, copy, status, dateLocale } = useFabLocale();
  const latest = workflows[0];
  const runStatus = latest ? text(latest.status, "unknown") : "idle";
  const metadata = asRecord(latest?.metadata);
  const steps = asRecord(metadata.steps);
  const executed = recordsOrStrings(steps.executed);
  const skipped = recordsOrStrings(steps.skipped);
  const failed = recordsOrStrings(steps.failed);
  const actions = records(autonomy.actions);
  const capabilityStatus = text(autonomy.status, "unavailable");

  return (
    <section id="automation" className="fab-section fab-automation-section">
      <div className="fab-section-heading">
        <div><span>{copy("Governed autonomy", "Beheerste autonomie")}</span><h2>{copy("Automation control", "Automatiseringsbesturing")}</h2></div>
        <div className="fab-section-statuses">
          <FabDataStatus resource={workflowResource} />
          <span className={`fab-status-chip tone-${statusTone(runStatus)}`}>{copy("Latest run", "Laatste run")}: {status(runStatus)}</span>
        </div>
      </div>

      {workflowResource?.state !== "live" && workflowResource?.state !== "stale" ? (
        <FabPanelStateMessage resource={workflowResource} title={copy("Workflow history", "Workflowgeschiedenis")} />
      ) : (
        <div className="fab-run-summary">
          <div className={`fab-run-state tone-${statusTone(runStatus)}`}>
            {runStatus === "completed" ? <CheckCircle2 aria-hidden="true" /> : runStatus === "running" ? <Clock3 aria-hidden="true" /> : <AlertCircle aria-hidden="true" />}
            <div><span>{copy("Current run state", "Huidige runstatus")}</span><strong>{latest ? status(runStatus) : copy("Idle", "Inactief")}</strong><small>{latest ? `Workflow #${text(latest.id)} - ${compactHumanize(latest.trigger_source || latest.triggerSource)}` : copy("No workflow runs were returned.", "Er zijn geen workflowruns teruggegeven.")}</small></div>
          </div>
          <dl className="fab-run-facts">
            <div><dt>{copy("Started", "Gestart")}</dt><dd>{latest ? exactDateTime(latest.started_at, dateLocale) : copy("Not recorded", "Niet vastgelegd")}</dd></div>
            <div><dt>{copy("Duration", "Duur")}</dt><dd>{durationBetween(latest?.started_at, latest?.finished_at || latest?.updated_at)}</dd></div>
            <div><dt>{copy("Documents", "Documenten")}</dt><dd>{latest ? `${count(latest.documents_processed)} ${copy("processed", "verwerkt")}, ${count(latest.documents_needing_review)} ${copy("review", "controle")}` : "-"}</dd></div>
            <div><dt>{copy("Steps", "Stappen")}</dt><dd>{latest ? `${executed.length} ${copy("executed", "uitgevoerd")}, ${skipped.length} ${copy("skipped", "overgeslagen")}, ${failed.length} ${copy("failed", "mislukt")}` : "-"}</dd></div>
          </dl>
          {latest?.error_message ? <div className="fab-inline-error"><AlertCircle aria-hidden="true" />{text(latest.error_message)}</div> : null}
        </div>
      )}

      <div className="fab-capability-heading">
        <div><span>{copy("Capability readiness", "Capabiliteitsgereedheid")}</span><strong>{copy("What FAB can safely execute now", "Wat FAB nu veilig kan uitvoeren")}</strong></div>
        <div className="fab-section-statuses"><FabDataStatus resource={autonomyResource} /><span className={`fab-status-chip tone-${statusTone(capabilityStatus)}`}>{status(capabilityStatus)}</span></div>
      </div>
      {autonomyResource?.state !== "live" && autonomyResource?.state !== "stale" ? (
        <FabPanelStateMessage resource={autonomyResource} title={copy("Autonomy plan", "Autonomieplan")} />
      ) : (
        <>
          <div className="fab-pipeline" aria-label="Safe automation capability stages">
            {pipelineStages.map((stage, index) => {
              const stageActions = actions.filter((action) => stage.stages.includes(text(action.stage, "")));
              const runnable = stageActions.filter((action) => bool(action.canRun));
              const blocked = stageActions.filter((action) => text(action.blockedReason, "") !== "");
              const reason = blocked.length
                ? `${runnable.length ? `${runnable.length} ${copy("eligible", "uitvoerbaar")}; ${blocked.length} ${copy("additional actions gated", "extra acties geblokkeerd")}: ` : ""}${text(blocked[0]?.blockedReason)}`
                : runnable.length ? copy("Ready for safe local execution.", "Gereed voor veilige lokale uitvoering.") : copy("No work is due for this stage.", "Voor deze fase is geen werk gepland.");
              const tone = runnable.length ? "good" : blocked.length ? "warn" : "neutral";
              const Icon = stage.icon;
              return (
                <div className="fab-pipeline-step" key={stage.id}>
                  <div className={`fab-pipeline-node tone-${tone}`}><Icon aria-hidden="true" /></div>
                  <div><strong>{lang === "nl" ? stage.labelNl : stage.label}</strong><small>{runnable.length && blocked.length ? `${runnable.length} ${copy("ready", "gereed")} / ${blocked.length} ${copy("gated", "geblokkeerd")}` : runnable.length ? `${runnable.length} ${copy("ready", "gereed")}` : blocked.length ? `${blocked.length} ${copy("gated", "geblokkeerd")}` : copy("No work due", "Geen werk gepland")}</small><span title={reason}>{reason}</span></div>
                  {index < pipelineStages.length - 1 && <ArrowRight className="fab-pipeline-arrow" aria-hidden="true" />}
                </div>
              );
            })}
          </div>
          <div className="fab-pipeline-note">
            <AlertCircle aria-hidden="true" />
            <span><strong>{copy("Readiness is not run progress.", "Gereedheid is geen runvoortgang.")}</strong> {copy("These gates describe what may run now; the latest-run evidence above describes what actually happened.", "Deze poorten tonen wat nu mag draaien; het bewijs van de laatste run hierboven toont wat werkelijk is gebeurd.")}</span>
            <button className="fab-secondary-button compact" onClick={() => onCommand("run_safe_cycle")} disabled={!connected || Boolean(pendingCommand) || !bool(autonomy.canRunAutonomously)}><Play aria-hidden="true" />{pendingCommand === "run_safe_cycle" ? copy("Running...", "Bezig...") : copy("Run eligible work", "Uitvoerbaar werk starten")}</button>
          </div>
        </>
      )}
    </section>
  );
}

function recordsOrStrings(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}
