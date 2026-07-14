import {
  AlertTriangle,
  ArrowUpRight,
  CheckCircle2,
  Clock3,
  FileWarning,
  History,
  RotateCcw,
} from "lucide-react";
import { asRecord, compactHumanize, count, humanize, matchesSearch, records, statusTone, text, timeAgo, type FabRecord } from "./fabView";

type FabOperationsPanelsProps = {
  exceptions: FabRecord[];
  exceptionSummary: FabRecord;
  recovery: FabRecord;
  activity: FabRecord[];
  workflows: FabRecord[];
  search: string;
  localApiEndpoint: string;
};

export function FabOperationsPanels({
  exceptions,
  exceptionSummary,
  recovery,
  activity,
  workflows,
  search,
  localApiEndpoint,
}: FabOperationsPanelsProps) {
  const visibleExceptions = exceptions.filter((item) => matchesSearch(item, search));
  const visibleActivity = activity.filter((item) => matchesSearch(item, search));
  const candidates = records(recovery.candidates).filter((item) => matchesSearch(item, search));
  const bySeverity = asRecord(exceptionSummary.bySeverity);

  return (
    <>
      <section id="exceptions" className="fab-section fab-exceptions">
        <div className="fab-section-heading">
          <div><span>Manual attention</span><h2>Operating exceptions</h2></div>
          <div className="fab-severity-summary" aria-label="Exception severity summary">
            <span className="tone-bad">{count(bySeverity.high)} high</span>
            <span className="tone-warn">{count(bySeverity.medium)} medium</span>
            <span>{count(bySeverity.low)} low</span>
          </div>
        </div>
        <div className="fab-table-wrap">
          <table className="fab-table">
            <thead><tr><th>Severity</th><th>Exception</th><th>Entity</th><th>Age</th><th>Required next action</th><th><span className="sr-only">Open</span></th></tr></thead>
            <tbody>
              {visibleExceptions.map((exception) => {
                const entity = asRecord(exception.entity);
                const actions = records(exception.actions);
                const openAction = actions.find((action) => text(action.method, "GET") === "GET") || actions[0];
                const path = text(openAction?.dashboardPath || openAction?.path, "");
                return (
                  <tr key={text(exception.id)}>
                    <td data-label="Severity"><span className={`fab-status-chip tone-${statusTone(exception.severity)}`}><AlertTriangle aria-hidden="true" />{humanize(exception.severity)}</span></td>
                    <td data-label="Exception"><strong>{compactHumanize(exception.type)}</strong><span>{text(exception.message)}</span></td>
                    <td data-label="Entity"><strong>{compactHumanize(exception.entityType)}</strong><span>#{text(exception.entityId, text(entity.id, "-") )}</span></td>
                    <td data-label="Age">{exception.ageHours === null || exception.ageHours === undefined ? "-" : `${Math.round(count(exception.ageHours))}h`}</td>
                    <td data-label="Next action">{text(exception.nextAction)}</td>
                    <td data-label="Evidence">
                      {path ? <a className="fab-icon-button fab-table-action" href={`${localApiEndpoint}${path}`} target="_blank" rel="noreferrer" aria-label="Open exception evidence" title="Open exception evidence"><ArrowUpRight aria-hidden="true" /></a> : <span className="fab-muted">-</span>}
                    </td>
                  </tr>
                );
              })}
              {!visibleExceptions.length && (
                <tr><td colSpan={6}><div className="fab-empty-state"><CheckCircle2 aria-hidden="true" /><strong>No matching exceptions</strong><span>{search ? "Adjust the control-center search." : "FAB has no operating exceptions to show."}</span></div></td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <div className="fab-split-band" id="ledger">
        <section className="fab-section" id="audit">
          <div className="fab-section-heading">
            <div><span>Immutable evidence</span><h2>Recent activity</h2></div>
            <History aria-hidden="true" />
          </div>
          <div className="fab-activity-list">
            {visibleActivity.slice(0, 8).map((event) => (
              <div className="fab-activity-row" key={text(event.id)}>
                <span className={`fab-timeline-dot tone-${statusTone(event.action)}`} />
                <div><strong>{compactHumanize(event.action)}</strong><span>{compactHumanize(event.entity_type || event.entityType)} #{text(event.entity_id || event.entityId, "-")}</span></div>
                <time>{timeAgo(event.created_at || event.createdAt)}</time>
              </div>
            ))}
            {!visibleActivity.length && <div className="fab-empty-state compact"><History aria-hidden="true" /><strong>No matching audit events</strong><span>Actions performed in FAB appear here.</span></div>}
          </div>
        </section>

        <section className="fab-section" id="reconciliation">
          <div className="fab-section-heading">
            <div><span>Governed retries</span><h2>Recovery queue</h2></div>
            <span className={`fab-status-chip tone-${statusTone(recovery.status)}`}>{count(recovery.dueCount)} due</span>
          </div>
          <div className="fab-recovery-list">
            {candidates.slice(0, 6).map((candidate) => (
              <div className="fab-recovery-row" key={text(candidate.workflowRunId)}>
                <div className={`fab-recovery-icon tone-${statusTone(candidate.status)}`}><RotateCcw aria-hidden="true" /></div>
                <div><strong>Workflow #{text(candidate.workflowRunId)}</strong><span>{compactHumanize(candidate.triggerSource)} - retry {count(candidate.retryDepth)}/{count(candidate.maxRetries)}</span></div>
                <div><span className={`fab-status-chip tone-${statusTone(candidate.status)}`}>{humanize(candidate.status)}</span><small>{timeAgo(candidate.eligibleAt)}</small></div>
              </div>
            ))}
            {!candidates.length && (
              <div className="fab-empty-state compact"><CheckCircle2 aria-hidden="true" /><strong>No recovery work due</strong><span>{count(recovery.candidateCount)} candidate workflows are being monitored.</span></div>
            )}
          </div>
          <div className="fab-workflow-footnote">
            <Clock3 aria-hidden="true" /> {workflows.length ? `Latest workflow: ${compactHumanize(workflows[0].status)} ${timeAgo(workflows[0].finished_at || workflows[0].updated_at)}` : "No workflow runs recorded yet."}
          </div>
        </section>
      </div>

      <section id="reports" className="fab-proof-band">
        <FileWarning aria-hidden="true" />
        <div><strong>Close and report evidence stays local until approved.</strong><span>FAB records every prepared artifact, checksum, review gate, and downstream execution result in the authoritative ledger.</span></div>
      </section>
    </>
  );
}
