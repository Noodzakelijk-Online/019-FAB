import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { AlertTriangle, ArrowUpRight, Filter, Search, X } from "lucide-react";
import { FabDataStatus, FabPanelStateMessage } from "./FabDataState";
import { useFabLocale } from "./fabLocale";
import {
  asRecord,
  compactHumanize,
  count,
  exactDateTime,
  matchesSearch,
  panelState,
  records,
  statusTone,
  text,
  type FabRecord,
  type FabResourceState,
} from "./fabView";

type FabExceptionsPanelProps = {
  exceptions: FabRecord[];
  exceptionSummary: FabRecord;
  resource?: FabResourceState;
  closeReadiness: FabRecord;
  closeResource?: FabResourceState;
  search: string;
  localApiEndpoint: string;
};

type SeverityFilter = "all" | "high" | "medium" | "low";
type SortMode = "risk" | "oldest" | "newest";

const severityRank: Record<string, number> = { high: 3, medium: 2, low: 1 };

export function FabExceptionsPanel({ exceptions, exceptionSummary, resource, closeReadiness, closeResource, search, localApiEndpoint }: FabExceptionsPanelProps) {
  const { copy, status, dateLocale } = useFabLocale();
  const [severity, setSeverity] = useState<SeverityFilter>("all");
  const [sort, setSort] = useState<SortMode>("risk");
  const [selected, setSelected] = useState<FabRecord | null>(null);
  const bySeverity = asRecord(exceptionSummary.bySeverity);
  const visibleExceptions = useMemo(() => exceptions
    .filter((item) => matchesSearch(item, search))
    .filter((item) => severity === "all" || text(item.severity, "low") === severity)
    .sort((left, right) => compareExceptions(left, right, sort)), [exceptions, search, severity, sort]);
  const state = panelState(resource, exceptions.length);
  const displayState = resource?.state === "live" && visibleExceptions.length === 0 ? "empty" : state;
  const total = exceptionSummary.total === null || exceptionSummary.total === undefined
    ? exceptions.length
    : count(exceptionSummary.total);

  return (
    <section id="exceptions" className="fab-section fab-exceptions">
      <div className="fab-section-heading fab-section-heading-stacked">
        <div>
          <span>{copy("Manual attention", "Handmatige aandacht")}</span>
          <h2>{copy("Operating exceptions", "Operationele uitzonderingen")}</h2>
        </div>
        <div className="fab-section-statuses">
          <FabDataStatus resource={resource} state={displayState} emptyLabel="Clear" />
          <div className="fab-severity-summary" aria-label={copy("Exception severity summary", "Samenvatting ernst uitzonderingen")}>
            <span className="tone-bad">{resource?.state === "live" || resource?.state === "stale" ? count(bySeverity.high) : "-"} {copy("high", "hoog")}</span>
            <span className="tone-warn">{resource?.state === "live" || resource?.state === "stale" ? count(bySeverity.medium) : "-"} {copy("medium", "middel")}</span>
            <span>{resource?.state === "live" || resource?.state === "stale" ? count(bySeverity.low) : "-"} {copy("low", "laag")}</span>
          </div>
        </div>
      </div>

      {(resource?.state === "live" || resource?.state === "stale") && exceptions.length > 0 && (
        <div className="fab-filter-bar" aria-label={copy("Exception filters", "Uitzonderingsfilters")}>
          <label>
            <Filter aria-hidden="true" />
            <span>{copy("Severity", "Ernst")}</span>
            <select value={severity} onChange={(event) => setSeverity(event.target.value as SeverityFilter)}>
              <option value="all">{copy("All severities", "Alle niveaus")}</option>
              <option value="high">{copy("High", "Hoog")}</option>
              <option value="medium">{copy("Medium", "Middel")}</option>
              <option value="low">{copy("Low", "Laag")}</option>
            </select>
          </label>
          <label>
            <span>{copy("Sort", "Sorteren")}</span>
            <select value={sort} onChange={(event) => setSort(event.target.value as SortMode)}>
              <option value="risk">{copy("Highest risk", "Hoogste risico")}</option>
              <option value="oldest">{copy("Oldest first", "Oudste eerst")}</option>
              <option value="newest">{copy("Newest first", "Nieuwste eerst")}</option>
            </select>
          </label>
          <span className="fab-result-count">{copy("Showing", "Getoond")} {visibleExceptions.length} {copy("of", "van")} {total}. {copy("Local API limit", "Lokale API-limiet")}: 25.</span>
        </div>
      )}

      {resource?.state === "stale" && <FabPanelStateMessage resource={resource} title="Exceptions" />}
      {resource?.state !== "live" && resource?.state !== "stale" ? (
        <FabPanelStateMessage resource={resource} title="Exceptions" />
      ) : visibleExceptions.length === 0 ? (
        <FabPanelStateMessage
          resource={{ ...resource, state: "empty" }}
          title={copy("Exceptions", "Uitzonderingen")}
          emptyTitle={exceptions.length ? copy("No matching exceptions", "Geen overeenkomende uitzonderingen") : copy("No operating exceptions", "Geen operationele uitzonderingen")}
          emptyMessage={exceptions.length ? copy("Adjust the active search or severity filter.", "Pas de zoekopdracht of het ernstfilter aan.") : copy("The live exception service positively returned zero operating exceptions.", "De actuele uitzonderingsservice heeft bevestigd dat er geen operationele uitzonderingen zijn.")}
          searchActive={Boolean(search || severity !== "all") && exceptions.length > 0}
        />
      ) : (
        <div className="fab-table-wrap">
          <table className="fab-table">
            <thead><tr><th>{copy("Severity", "Ernst")}</th><th>{copy("Exception", "Uitzondering")}</th><th>{copy("Entity", "Entiteit")}</th><th>{copy("Age", "Leeftijd")}</th><th>{copy("Owner / due", "Eigenaar / deadline")}</th><th>{copy("Required next action", "Vereiste volgende actie")}</th><th><span className="sr-only">{copy("Actions", "Acties")}</span></th></tr></thead>
            <tbody>
              {visibleExceptions.map((exception) => {
                const entity = asRecord(exception.entity);
                const age = exception.ageHours === null || exception.ageHours === undefined ? null : Math.round(count(exception.ageHours));
                return (
                  <tr key={text(exception.id)}>
                    <td data-label="Severity"><span className={`fab-status-chip tone-${statusTone(exception.severity)}`}><AlertTriangle aria-hidden="true" />{status(exception.severity)}</span></td>
                    <td data-label="Exception"><strong>{compactHumanize(exception.type)}</strong><span>{text(exception.message)}</span></td>
                    <td data-label="Entity"><strong>{compactHumanize(exception.entityType)}</strong><span>#{text(exception.entityId, text(entity.id, "-") )}</span></td>
                    <td data-label="Age">{age === null ? copy("Not recorded", "Niet vastgelegd") : `${age}u`}</td>
                    <td data-label="Owner / due"><strong>{text(exception.owner || exception.assignedTo, copy("Unassigned", "Niet toegewezen"))}</strong><span>{exception.dueAt ? exactDateTime(exception.dueAt, dateLocale) : copy("No SLA recorded", "Geen SLA vastgelegd")}</span></td>
                    <td data-label="Next action">{text(exception.nextAction, copy("Inspect the exception evidence.", "Bekijk het bewijs van de uitzondering."))}</td>
                    <td data-label="Actions"><button className="fab-secondary-button compact" onClick={() => setSelected(exception)}><Search aria-hidden="true" /> {copy("Inspect", "Bekijken")}</button></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <FabNextDecisions closeReadiness={closeReadiness} resource={closeResource} localApiEndpoint={localApiEndpoint} />
      <FabExceptionDrawer exception={selected} localApiEndpoint={localApiEndpoint} onClose={() => setSelected(null)} />
    </section>
  );
}

function FabNextDecisions({ closeReadiness, resource, localApiEndpoint }: { closeReadiness: FabRecord; resource?: FabResourceState; localApiEndpoint: string }) {
  const { copy, status } = useFabLocale();
  const gates = records(closeReadiness.gates).filter((gate) => ["blocked", "attention"].includes(text(gate.status, "")));
  const nextActions = Array.isArray(closeReadiness.nextActions) ? closeReadiness.nextActions.filter((item): item is string => typeof item === "string") : [];
  return (
    <div className="fab-next-decisions">
      <div className="fab-subsection-heading"><div><span>{copy("Period close", "Periodeafsluiting")}</span><h3>{copy("Next decisions", "Volgende beslissingen")}</h3></div><FabDataStatus resource={resource} /></div>
      {resource?.state !== "live" && resource?.state !== "stale" ? <FabPanelStateMessage resource={resource} title={copy("Close readiness", "Afsluitgereedheid")} /> : (
        <>
          {gates.map((gate) => <div className="fab-decision-row" key={text(gate.id)}><AlertTriangle aria-hidden="true" /><div><strong>{text(gate.label, compactHumanize(gate.id))}</strong><span>{compactHumanize(gate.message)}</span></div><span className={`fab-status-chip tone-${statusTone(gate.status)}`}>{status(gate.status)}</span></div>)}
          {nextActions.slice(0, 3).map((action, index) => <div className="fab-decision-row" key={`${action}-${index}`}><span className="fab-decision-index">{index + 1}</span><div><strong>{copy("Required next action", "Vereiste volgende actie")}</strong><span>{action}</span></div></div>)}
          {!gates.length && !nextActions.length && <FabPanelStateMessage resource={{ ...resource, state: "empty" }} title={copy("Close readiness", "Afsluitgereedheid")} emptyTitle={copy("No close decisions due", "Geen afsluitbeslissingen nodig")} emptyMessage={copy("The live close-readiness service returned no blocked gates or next actions.", "De actuele afsluitservice gaf geen geblokkeerde poorten of volgende acties terug.")} />}
        </>
      )}
      <div className="fab-panel-footer"><a href={`${localApiEndpoint}/#close-readiness`} target="_blank" rel="noreferrer">{copy("Open close evidence", "Afsluitbewijs openen")} <ArrowUpRight aria-hidden="true" /></a><span>{copy("External submission remains approval-gated.", "Externe indiening blijft goedkeuringsplichtig.")}</span></div>
    </div>
  );
}

function FabExceptionDrawer({ exception, localApiEndpoint, onClose }: { exception: FabRecord | null; localApiEndpoint: string; onClose: () => void }) {
  const { copy, status } = useFabLocale();
  const closeRef = useRef<HTMLButtonElement>(null);
  const restoreFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!exception) return;
    restoreFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    document.body.classList.add("fab-dialog-open");
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      if (event.key !== "Tab") return;
      const dialog = closeRef.current?.closest<HTMLElement>("[role=dialog]");
      const focusable = dialog ? Array.from(dialog.querySelectorAll<HTMLElement>("button:not(:disabled), a[href], select, input")) : [];
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      document.body.classList.remove("fab-dialog-open");
      restoreFocusRef.current?.focus();
    };
  }, [exception, onClose]);

  if (!exception) return null;
  const actions = records(exception.actions);
  return createPortal(
    <div className="fab-command-overlay" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <aside className="fab-detail-drawer" role="dialog" aria-modal="true" aria-labelledby="fab-exception-title" aria-describedby="fab-exception-description">
        <div className="fab-command-header">
          <div><span>{copy("Exception evidence", "Uitzonderingsbewijs")}</span><h2 id="fab-exception-title">{compactHumanize(exception.type)}</h2></div>
          <button ref={closeRef} className="fab-icon-button" onClick={onClose} aria-label={copy("Close exception details", "Uitzonderingsdetails sluiten")} title={copy("Close exception details", "Uitzonderingsdetails sluiten")}><X aria-hidden="true" /></button>
        </div>
        <div className="fab-detail-body">
          <p id="fab-exception-description">{text(exception.message, "No explanatory message was recorded.")}</p>
          <dl>
            <div><dt>{copy("Severity", "Ernst")}</dt><dd>{status(exception.severity)}</dd></div>
            <div><dt>{copy("Entity", "Entiteit")}</dt><dd>{compactHumanize(exception.entityType)} #{text(exception.entityId, "-")}</dd></div>
            <div><dt>{copy("Owner", "Eigenaar")}</dt><dd>{text(exception.owner || exception.assignedTo, copy("Unassigned", "Niet toegewezen"))}</dd></div>
            <div><dt>{copy("Required next action", "Vereiste volgende actie")}</dt><dd>{text(exception.nextAction, copy("Inspect the authoritative evidence.", "Bekijk het gezaghebbende bewijs."))}</dd></div>
          </dl>
          <div className="fab-detail-actions">
            {actions.map((action, index) => {
              const path = text(action.dashboardPath || action.path, "");
              if (!path || text(action.method, "GET") !== "GET") return null;
              return <a key={`${path}-${index}`} className="fab-primary-button" href={`${localApiEndpoint}${path}`} target="_blank" rel="noreferrer"><ArrowUpRight aria-hidden="true" /> {text(action.label, copy("Open evidence", "Bewijs openen"))}</a>;
            })}
            {!actions.length && <a className="fab-primary-button" href={`${localApiEndpoint}/#exceptions`} target="_blank" rel="noreferrer"><ArrowUpRight aria-hidden="true" /> {copy("Open advanced evidence", "Geavanceerd bewijs openen")}</a>}
          </div>
        </div>
      </aside>
    </div>,
    document.body,
  );
}

function compareExceptions(left: FabRecord, right: FabRecord, mode: SortMode): number {
  const leftAge = count(left.ageHours);
  const rightAge = count(right.ageHours);
  if (mode === "oldest") return rightAge - leftAge;
  if (mode === "newest") return leftAge - rightAge;
  const risk = (severityRank[text(right.severity, "low")] || 0) - (severityRank[text(left.severity, "low")] || 0);
  return risk || rightAge - leftAge;
}
