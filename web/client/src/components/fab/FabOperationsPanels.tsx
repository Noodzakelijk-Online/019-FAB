import {
  ArrowUpRight,
  Clock3,
  FileWarning,
  History,
  RotateCcw,
} from "lucide-react";
import { FabDataStatus, FabPanelStateMessage } from "./FabDataState";
import { useFabLocale } from "./fabLocale";
import { compactHumanize, count, exactDateTime, matchesSearch, panelState, records, statusTone, text, timeAgo, type FabRecord, type FabResourceState } from "./fabView";

type FabOperationsPanelsProps = {
  recovery: FabRecord;
  activity: FabRecord[];
  workflows: FabRecord[];
  recoveryResource?: FabResourceState;
  activityResource?: FabResourceState;
  workflowResource?: FabResourceState;
  search: string;
  localApiEndpoint: string;
};

export function FabOperationsPanels({
  recovery,
  activity,
  workflows,
  recoveryResource,
  activityResource,
  workflowResource,
  search,
  localApiEndpoint,
}: FabOperationsPanelsProps) {
  const { copy, status, dateLocale } = useFabLocale();
  const visibleActivity = activity.filter((item) => matchesSearch(item, search));
  const candidates = records(recovery.candidates).filter((item) => matchesSearch(item, search));
  const activityState = activityResource?.state === "live" && visibleActivity.length === 0 ? "empty" : panelState(activityResource, activity.length);
  const recoveryState = recoveryResource?.state === "live" && candidates.length === 0 ? "empty" : panelState(recoveryResource, candidates.length);

  return (
    <>
      <div className="fab-split-band">
        <section className="fab-section" id="audit">
          <div className="fab-section-heading">
            <div><span>{copy("Immutable evidence", "Onveranderlijk bewijs")}</span><h2>{copy("Recent activity", "Recente activiteit")}</h2></div>
            <div className="fab-section-statuses"><FabDataStatus resource={activityResource} state={activityState} /><History aria-hidden="true" /></div>
          </div>
          <div className="fab-activity-list">
            {activityResource?.state === "stale" && <FabPanelStateMessage resource={activityResource} title={copy("Audit activity", "Auditactiviteit")} />}
            {(activityResource?.state === "live" || activityResource?.state === "stale") && visibleActivity.slice(0, 8).map((event) => (
              <div className="fab-activity-row" key={text(event.id)}>
                <span className={`fab-timeline-dot tone-${statusTone(event.action)}`} />
                <div><strong>{compactHumanize(event.action)}</strong><span>{compactHumanize(event.entity_type || event.entityType)} #{text(event.entity_id || event.entityId, "-")}</span></div>
                <time>{exactDateTime(event.created_at || event.createdAt, dateLocale)}</time>
              </div>
            ))}
            {activityResource?.state !== "live" && activityResource?.state !== "stale" && <FabPanelStateMessage resource={activityResource} title={copy("Audit activity", "Auditactiviteit")} />}
            {activityResource?.state === "live" && !visibleActivity.length && <FabPanelStateMessage resource={{ ...activityResource, state: "empty" }} title={copy("Audit activity", "Auditactiviteit")} emptyTitle={search ? copy("No matching audit events", "Geen overeenkomende auditgebeurtenissen") : copy("No audit events", "Geen auditgebeurtenissen")} emptyMessage={search ? copy("Adjust the active search.", "Pas de zoekopdracht aan.") : copy("The audit service positively returned no events.", "De auditservice heeft bevestigd dat er geen gebeurtenissen zijn.")} />}
          </div>
          <div className="fab-panel-footer"><a href={`${localApiEndpoint}/#audit`} target="_blank" rel="noreferrer">{copy("View full audit log", "Volledig auditlog bekijken")} <ArrowUpRight aria-hidden="true" /></a><span>{copy("Showing up to 8 of the latest 12 fetched events.", "Maximaal 8 van de 12 laatst opgehaalde gebeurtenissen worden getoond.")}</span></div>
        </section>

        <section className="fab-section" id="recovery">
          <div className="fab-section-heading">
            <div><span>{copy("Governed retries", "Beheerde herpogingen")}</span><h2>{copy("Recovery queue", "Herstelwachtrij")}</h2></div>
            <div className="fab-section-statuses"><FabDataStatus resource={recoveryResource} state={recoveryState} /><span className={`fab-status-chip tone-${statusTone(recovery.status)}`}>{recoveryResource?.state === "live" || recoveryResource?.state === "stale" ? `${count(recovery.dueCount)} due` : "- due"}</span></div>
          </div>
          <div className="fab-recovery-list">
            {recoveryResource?.state === "stale" && <FabPanelStateMessage resource={recoveryResource} title={copy("Recovery queue", "Herstelwachtrij")} />}
            {(recoveryResource?.state === "live" || recoveryResource?.state === "stale") && candidates.slice(0, 6).map((candidate) => (
              <div className="fab-recovery-row" key={text(candidate.workflowRunId)}>
                <div className={`fab-recovery-icon tone-${statusTone(candidate.status)}`}><RotateCcw aria-hidden="true" /></div>
                <div><strong>Workflow #{text(candidate.workflowRunId)}</strong><span>{compactHumanize(candidate.triggerSource)} - retry {count(candidate.retryDepth)}/{count(candidate.maxRetries)}</span></div>
                <div><span className={`fab-status-chip tone-${statusTone(candidate.status)}`}>{status(candidate.status)}</span><small>{exactDateTime(candidate.eligibleAt, dateLocale)}</small></div>
              </div>
            ))}
            {recoveryResource?.state !== "live" && recoveryResource?.state !== "stale" && <FabPanelStateMessage resource={recoveryResource} title={copy("Recovery queue", "Herstelwachtrij")} />}
            {recoveryResource?.state === "live" && !candidates.length && <FabPanelStateMessage resource={{ ...recoveryResource, state: "empty" }} title={copy("Recovery queue", "Herstelwachtrij")} emptyTitle={copy("No recovery work due", "Geen herstelwerk gepland")} emptyMessage={`${count(recovery.candidateCount)} ${copy("candidate workflows are being monitored.", "kandidaatworkflows worden bewaakt.")}`} />}
          </div>
          <div className="fab-workflow-footnote">
            <Clock3 aria-hidden="true" /> {workflowResource?.state === "live" || workflowResource?.state === "stale" ? (workflows.length ? `${copy("Latest workflow", "Laatste workflow")}: ${status(workflows[0].status)} ${timeAgo(workflows[0].finished_at || workflows[0].updated_at, dateLocale)}` : copy("The workflow service positively returned no runs.", "De workflowservice heeft bevestigd dat er geen runs zijn.")) : copy("Workflow history unavailable.", "Workflowgeschiedenis niet beschikbaar.")}
          </div>
          <div className="fab-panel-footer"><a href={`${localApiEndpoint}/#workflows`} target="_blank" rel="noreferrer">{copy("View recovery centre", "Herstelcentrum bekijken")} <ArrowUpRight aria-hidden="true" /></a><span>{copy("Automatic retries remain policy-bound.", "Automatische herpogingen blijven beleidsgebonden.")}</span></div>
        </section>
      </div>

      <section className="fab-proof-band">
        <FileWarning aria-hidden="true" />
        <div><strong>{copy("Close and report evidence stays local until approved.", "Afsluit- en rapportbewijs blijft lokaal tot goedkeuring.")}</strong><span>{copy("FAB records every prepared artifact, checksum, review gate, and downstream execution result in the authoritative ledger.", "FAB legt ieder voorbereid artefact, controlegetal, controlemoment en uitvoeringsresultaat vast in het gezaghebbende grootboek.")}</span></div>
      </section>
    </>
  );
}
