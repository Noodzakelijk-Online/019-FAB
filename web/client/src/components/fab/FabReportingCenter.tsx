import {
  ArrowUpRight,
  CalendarClock,
  Download,
  FileBarChart,
  Landmark,
  Loader2,
  ShieldCheck,
} from "lucide-react";
import { FabDataStatus, FabPanelStateMessage } from "./FabDataState";
import { useFabLocale } from "./fabLocale";
import {
  count,
  exactDateTime,
  humanize,
  panelState,
  records,
  statusTone,
  text,
  type FabCommandId,
  type FabRecord,
  type FabResourceState,
} from "./fabView";

type FabReportingCenterProps = {
  reporting: {
    scheduleStatus: FabRecord;
    reportRuns: FabRecord[];
    externalSubmission: string | null;
  };
  compliance: {
    summary: FabRecord;
    assessments: FabRecord[];
    statutoryStatus: string | null;
    filingStatus: string | null;
    externalFiling: string | null;
  };
  reportingResource?: FabResourceState;
  complianceResource?: FabResourceState;
  connected: boolean;
  pendingCommand: FabCommandId | null;
  localApiEndpoint: string;
  onCommand: (commandId: FabCommandId) => void;
};

export function FabReportingCenter({
  reporting,
  compliance,
  reportingResource,
  complianceResource,
  connected,
  pendingCommand,
  localApiEndpoint,
  onCommand,
}: FabReportingCenterProps) {
  const { copy, dateLocale, status } = useFabLocale();
  const reportRuns = records(reporting.reportRuns);
  const assessments = records(compliance.assessments);
  const schedule = reporting.scheduleStatus || {};
  const summary = compliance.summary || {};
  const latestReport = reportRuns[0] || {};
  const latestAssessment = assessments[0] || {};
  const reportingState = panelState(reportingResource, reportRuns.length);
  const complianceState = panelState(complianceResource, assessments.length);
  const reportingAvailable = reportingResource?.state === "live" || reportingResource?.state === "stale";
  const complianceAvailable = complianceResource?.state === "live" || complianceResource?.state === "stale";
  const commandBusy = Boolean(pendingCommand);

  return (
    <section className="fab-section fab-reporting-center" id="reporting">
      <div className="fab-section-heading fab-reporting-heading">
        <div>
          <span>{copy("Close evidence", "Afsluitbewijs")}</span>
          <h2>{copy("Reporting & compliance", "Rapportage en compliance")}</h2>
        </div>
        <div className="fab-section-statuses">
          <FabDataStatus resource={reportingResource} state={reportingState} />
          <FabDataStatus resource={complianceResource} state={complianceState} />
          <button
            className="fab-secondary-button"
            type="button"
            disabled={!connected || commandBusy}
            onClick={() => onCommand("run_due_reports")}
          >
            {pendingCommand === "run_due_reports" ? <Loader2 className="is-spinning" aria-hidden="true" /> : <FileBarChart aria-hidden="true" />}
            {pendingCommand === "run_due_reports"
              ? copy("Preparing report", "Rapport voorbereiden")
              : copy("Run due report", "Maak gepland rapport")}
          </button>
          <button
            className="fab-primary-button"
            type="button"
            disabled={!connected || commandBusy}
            onClick={() => onCommand("assess_compliance")}
          >
            {pendingCommand === "assess_compliance" ? <Loader2 className="is-spinning" aria-hidden="true" /> : <ShieldCheck aria-hidden="true" />}
            {pendingCommand === "assess_compliance"
              ? copy("Assessing", "Beoordelen")
              : copy("Assess compliance", "Beoordeel compliance")}
          </button>
        </div>
      </div>

      {reportingResource?.state === "stale" && (
        <FabPanelStateMessage resource={reportingResource} title={copy("Scheduled reports", "Geplande rapporten")} />
      )}
      {complianceResource?.state === "stale" && (
        <FabPanelStateMessage resource={complianceResource} title={copy("Compliance evidence", "Compliancebewijs")} />
      )}

      {(reportingAvailable || complianceAvailable) && (
        <div className="fab-reporting-summary">
          <div>
            <CalendarClock aria-hidden="true" />
            <span>{copy("Report schedule", "Rapportschema")}</span>
            <strong className={`tone-${statusTone(schedule.status)}`}>{reportingAvailable ? humanize(schedule.status) : "-"}</strong>
            <small>{schedule.enabled === false
              ? copy("Enable the local report schedule to create recurring artifacts.", "Schakel het lokale rapportschema in voor terugkerende artefacten.")
              : `${copy("Next slot", "Volgend moment")}: ${exactDateTime((schedule.slot as FabRecord | undefined)?.nextDueAt, dateLocale)}`}</small>
          </div>
          <div>
            <FileBarChart aria-hidden="true" />
            <span>{copy("Latest report", "Laatste rapport")}</span>
            <strong className={`tone-${statusTone(latestReport.status)}`}>{reportRuns.length ? humanize(latestReport.status) : copy("None", "Geen")}</strong>
            <small>{reportRuns.length
              ? `${count(latestReport.rowCount)} ${copy("rows", "regels")} / ${count(latestReport.blockerCount)} ${copy("blockers", "blokkades")}`
              : copy("No checksum-bound scheduled report has been prepared.", "Er is nog geen gepland rapport met checksum voorbereid.")}</small>
          </div>
          <div>
            <ShieldCheck aria-hidden="true" />
            <span>{copy("Open findings", "Open bevindingen")}</span>
            <strong className={`tone-${count(summary.blockingFindings) > 0 ? "bad" : count(summary.openFindings) > 0 ? "warn" : "good"}`}>{complianceAvailable ? count(summary.openFindings) : "-"}</strong>
            <small>{complianceAvailable
              ? `${count(summary.blockingFindings)} ${copy("blocking", "blokkerend")} / ${count(summary.attentionFindings)} ${copy("attention", "aandacht")}`
              : copy("Compliance state unavailable.", "Compliancestatus niet beschikbaar.")}</small>
          </div>
          <div>
            <Landmark aria-hidden="true" />
            <span>{copy("Retention evidence", "Bewaarbewijs")}</span>
            <strong>{complianceAvailable ? count(summary.retentionRecords) : "-"}</strong>
            <small>{`${copy("Filing", "Aangifte")}: ${status(compliance.filingStatus || summary.filingStatus || "not_filed")}`}</small>
          </div>
        </div>
      )}

      <div className="fab-reporting-grid">
        <div className="fab-reporting-pane">
          <div className="fab-subsection-heading">
            <div><span>{copy("Generated locally", "Lokaal gegenereerd")}</span><h3>{copy("Scheduled report runs", "Geplande rapportruns")}</h3></div>
            {reportingAvailable && <span className={`fab-status-chip tone-${statusTone(schedule.status)}`}>{status(schedule.status)}</span>}
          </div>
          {!reportingAvailable && <FabPanelStateMessage resource={reportingResource} title={copy("Scheduled reports", "Geplande rapporten")} />}
          {reportingAvailable && reportRuns.length === 0 && (
            <FabPanelStateMessage
              resource={{ ...reportingResource, state: "empty" }}
              title={copy("Scheduled reports", "Geplande rapporten")}
              emptyTitle={copy("No report runs yet", "Nog geen rapportruns")}
              emptyMessage={copy("Run the due schedule to prepare checksum-bound JSON and CSV evidence.", "Voer het geplande schema uit om JSON- en CSV-bewijs met checksum voor te bereiden.")}
            />
          )}
          {reportingAvailable && reportRuns.length > 0 && (
            <div className="fab-table-wrap">
              <table className="fab-table fab-reporting-table">
                <thead><tr><th>{copy("Report", "Rapport")}</th><th>{copy("Period", "Periode")}</th><th>{copy("Status", "Status")}</th><th>{copy("Evidence", "Bewijs")}</th></tr></thead>
                <tbody>
                  {reportRuns.map((report) => {
                    const reportId = count(report.id);
                    return (
                      <tr key={text(report.id)}>
                        <td data-label={copy("Report", "Rapport")}><strong>{humanize(report.reportType)}</strong><span>{text(report.scheduleId)} / {humanize(report.basis)}</span></td>
                        <td data-label={copy("Period", "Periode")}><strong>{period(report.periodFrom, report.periodTo)}</strong><span>{exactDateTime(report.finishedAt || report.updatedAt, dateLocale)}</span></td>
                        <td data-label={copy("Status", "Status")}><span className={`fab-status-chip tone-${statusTone(report.status)}`}>{status(report.status)}</span><span>{count(report.rowCount)} {copy("rows", "regels")}, {count(report.blockerCount)} {copy("blockers", "blokkades")}</span></td>
                        <td data-label={copy("Evidence", "Bewijs")}>
                          <div className="fab-artifact-actions">
                            {report.hasJsonArtifact === true && reportId > 0 && <a href={`${localApiEndpoint}/api/report-runs/${reportId}/artifact?format=json`} target="_blank" rel="noreferrer"><Download aria-hidden="true" /> JSON</a>}
                            {report.hasCsvArtifact === true && reportId > 0 && <a href={`${localApiEndpoint}/api/report-runs/${reportId}/artifact?format=csv`} target="_blank" rel="noreferrer"><Download aria-hidden="true" /> CSV</a>}
                            {report.hasJsonArtifact !== true && report.hasCsvArtifact !== true && <span>{copy("No artifact", "Geen artefact")}</span>}
                          </div>
                          <code title={text(report.jsonSha256 || report.csvSha256, "")}>{shortHash(report.jsonSha256 || report.csvSha256)}</code>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="fab-reporting-pane">
          <div className="fab-subsection-heading">
            <div><span>{copy("Provisional Dutch checks", "Voorlopige Nederlandse controles")}</span><h3>{copy("Compliance assessments", "Compliancebeoordelingen")}</h3></div>
            {complianceAvailable && <span className={`fab-status-chip tone-${statusTone(latestAssessment.status)}`}>{assessments.length ? status(latestAssessment.status) : status("not_assessed")}</span>}
          </div>
          {!complianceAvailable && <FabPanelStateMessage resource={complianceResource} title={copy("Compliance evidence", "Compliancebewijs")} />}
          {complianceAvailable && assessments.length === 0 && (
            <FabPanelStateMessage
              resource={{ ...complianceResource, state: "empty" }}
              title={copy("Compliance evidence", "Compliancebewijs")}
              emptyTitle={copy("No assessment yet", "Nog geen beoordeling")}
              emptyMessage={copy("Assess the current period to create VAT and retention evidence for review.", "Beoordeel de huidige periode om btw- en bewaartermijnbewijs te maken.")}
            />
          )}
          {complianceAvailable && assessments.length > 0 && (
            <div className="fab-table-wrap">
              <table className="fab-table fab-reporting-table">
                <thead><tr><th>{copy("Period", "Periode")}</th><th>{copy("Status", "Status")}</th><th>{copy("Coverage", "Dekking")}</th><th>{copy("Checksum", "Checksum")}</th></tr></thead>
                <tbody>
                  {assessments.map((assessment) => (
                    <tr key={text(assessment.id)}>
                      <td data-label={copy("Period", "Periode")}><strong>{period(assessment.periodFrom, assessment.periodTo)}</strong><span>{humanize(assessment.basis)} / {text(assessment.targetSystem, copy("All ledgers", "Alle grootboeken"))}</span></td>
                      <td data-label={copy("Status", "Status")}><span className={`fab-status-chip tone-${statusTone(assessment.status)}`}>{status(assessment.status)}</span><span>{status(assessment.statutoryStatus || compliance.statutoryStatus || "provisional")}</span></td>
                      <td data-label={copy("Coverage", "Dekking")}><strong>{count(assessment.recordCount)} {copy("records", "boekingen")}</strong><span>{count(assessment.findingCount)} {copy("findings", "bevindingen")}, {count(assessment.blockingCount)} {copy("blocking", "blokkerend")}</span></td>
                      <td data-label={copy("Checksum", "Checksum")}><code title={text(assessment.sourceChecksum, "")}>{shortHash(assessment.sourceChecksum)}</code></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      <div className="fab-panel-footer">
        <div className="fab-reporting-links">
          <a href={`${localApiEndpoint}/#reports`} target="_blank" rel="noreferrer">{copy("Open full reports", "Open volledige rapporten")} <ArrowUpRight aria-hidden="true" /></a>
          <a href={`${localApiEndpoint}/#compliance`} target="_blank" rel="noreferrer">{copy("Open compliance evidence", "Open compliancebewijs")} <ArrowUpRight aria-hidden="true" /></a>
        </div>
        <span>{copy("Reports are provisional local evidence. FAB does not file taxes or submit artifacts externally from this workspace.", "Rapporten zijn voorlopig lokaal bewijs. FAB dient vanuit deze werkruimte geen aangiften of artefacten extern in.")}</span>
      </div>
    </section>
  );
}

function period(fromValue: unknown, toValue: unknown): string {
  const from = text(fromValue, "-");
  const to = text(toValue, "-");
  return from === to ? from : `${from} - ${to}`;
}

function shortHash(value: unknown): string {
  const hash = text(value, "");
  return hash.length >= 16 ? `${hash.slice(0, 8)}...${hash.slice(-8)}` : "-";
}
