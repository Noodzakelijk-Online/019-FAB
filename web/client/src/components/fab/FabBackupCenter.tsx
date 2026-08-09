import {
  ArrowUpRight,
  Clock3,
  DatabaseBackup,
  FileCheck2,
  LifeBuoy,
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
  type FabRecord,
  type FabResourceState,
} from "./fabView";

type FabBackupCenterProps = {
  backups: {
    backups: FabRecord[];
    schedule: FabRecord;
    verificationMode: string | null;
  };
  resource?: FabResourceState;
  connected: boolean;
  pending: boolean;
  supportPending: boolean;
  localApiEndpoint: string;
  onCreate: () => void;
  onCreateSupportBundle: () => void;
};

export function FabBackupCenter({
  backups,
  resource,
  connected,
  pending,
  supportPending,
  localApiEndpoint,
  onCreate,
  onCreateSupportBundle,
}: FabBackupCenterProps) {
  const { copy, dateLocale } = useFabLocale();
  const items = records(backups.backups);
  const schedule = backups.schedule || {};
  const state = panelState(resource, items.length);
  const scheduleStatus = text(schedule.status, "unavailable");
  const evidenceStatus = text(schedule.sourceEvidenceStatus, "unavailable");
  const due = schedule.due === true;
  const showData = resource?.state === "live" || resource?.state === "stale";
  const evidenceDocuments = count(schedule.sourceEvidenceDocuments);
  const evidenceFiles = count(schedule.sourceEvidenceFiles);
  const evidenceGaps = count(schedule.sourceEvidenceGaps);
  const verificationMode = text(backups.verificationMode, "unavailable");

  return (
    <section className="fab-section fab-backup-center" id="backups">
      <div className="fab-section-heading fab-backup-heading">
        <div>
          <span>{copy("Recovery evidence", "Herstelbewijs")}</span>
          <h2>{copy("Recovery packages", "Herstelpakketten")}</h2>
        </div>
        <div className="fab-section-statuses">
          <FabDataStatus resource={resource} state={state} />
          {showData && (
            <span className={`fab-status-chip tone-${statusTone(scheduleStatus)}`}>
              <Clock3 aria-hidden="true" />
              {humanize(scheduleStatus)}
            </span>
          )}
          <button
            className="fab-secondary-button"
            type="button"
            disabled={!connected || supportPending}
            onClick={onCreateSupportBundle}
            title={copy("Create a sanitized diagnostic ZIP", "Maak een opgeschoonde diagnostische ZIP")}
          >
            {supportPending ? <Loader2 className="is-spinning" aria-hidden="true" /> : <LifeBuoy aria-hidden="true" />}
            {supportPending
              ? copy("Creating support bundle", "Supportpakket maken")
              : copy("Create support bundle", "Supportpakket maken")}
          </button>
          <button
            className="fab-primary-button"
            type="button"
            disabled={!connected || pending}
            onClick={onCreate}
          >
            {pending ? <Loader2 className="is-spinning" aria-hidden="true" /> : <DatabaseBackup aria-hidden="true" />}
            {pending
              ? copy("Creating verified backup", "Geverifieerde back-up maken")
              : copy("Create verified backup", "Geverifieerde back-up maken")}
          </button>
        </div>
      </div>

      {resource?.state === "stale" && (
        <FabPanelStateMessage resource={resource} title={copy("Recovery packages", "Herstelpakketten")} />
      )}
      {resource?.state !== "live" && resource?.state !== "stale" && (
        <FabPanelStateMessage resource={resource} title={copy("Recovery packages", "Herstelpakketten")} />
      )}

      {showData && items.length > 0 && (
        <>
          <div className="fab-backup-summary">
            <div>
              <ShieldCheck aria-hidden="true" />
              <span>{copy("Evidence coverage", "Bewijsdekking")}</span>
              <strong className={`tone-${statusTone(evidenceStatus)}`}>{humanize(evidenceStatus)}</strong>
              <small>{evidenceDocuments} {copy("documents", "documenten")} / {evidenceFiles} {copy("files", "bestanden")}</small>
            </div>
            <div>
              <FileCheck2 aria-hidden="true" />
              <span>{copy("Evidence gaps", "Ontbrekend bewijs")}</span>
              <strong>{evidenceGaps}</strong>
              <small>{copy("A complete package requires zero gaps.", "Een volledig pakket vereist nul hiaten.")}</small>
            </div>
            <div>
              <DatabaseBackup aria-hidden="true" />
              <span>{copy("Protected source bytes", "Beveiligde bronbytes")}</span>
              <strong>{formatBytes(count(schedule.sourceEvidenceBytes))}</strong>
              <small>{copy("Ledger and source checksums are recorded in each package.", "Grootboek- en bronchecksums zijn in elk pakket vastgelegd.")}</small>
            </div>
            <div>
              <Clock3 aria-hidden="true" />
              <span>{copy("Next scheduled check", "Volgende geplande controle")}</span>
              <strong>{exactDateTime(schedule.nextDueAt, dateLocale)}</strong>
              <small>{count(schedule.intervalHours)} {copy("hour interval", "uur interval")}</small>
            </div>
          </div>

          {verificationMode === "manifest_only" && (
            <div className="fab-backup-alert tone-info" role="status">
              <ShieldCheck aria-hidden="true" />
              <div>
                <strong>{copy("Dashboard manifest check complete", "Dashboardmanifest gecontroleerd")}</strong>
                <span>{copy(
                  "This fast view validates archive structure and recorded metadata. FAB performs full byte-level checksum and database integrity verification when a package is created, explicitly inspected, restored, or evaluated by the recovery schedule.",
                  "Deze snelle weergave controleert de archiefstructuur en vastgelegde metadata. FAB voert volledige checksum- en database-integriteitscontrole uit bij het maken, expliciet inspecteren, herstellen of plannen van een pakket.",
                )}</span>
              </div>
            </div>
          )}

          {(due || evidenceStatus !== "complete") && (
            <div className="fab-backup-alert tone-warn" role="status">
              <Clock3 aria-hidden="true" />
              <div>
                <strong>{due
                  ? copy("A new verified recovery package is due.", "Een nieuw geverifieerd herstelpakket is nodig.")
                  : copy("The latest package is not source complete.", "Het nieuwste pakket bevat niet alle bronbestanden.")}</strong>
                <span>{copy(
                  "FAB will not report a complete backup while a ledger document is missing safe, checksum-matching source evidence.",
                  "FAB meldt geen volledige back-up zolang een grootboekdocument geen veilig bronbestand met overeenkomende checksum heeft.",
                )}</span>
              </div>
            </div>
          )}

          <div className="fab-table-wrap">
            <table className="fab-table fab-backup-table">
              <thead>
                <tr>
                  <th>{copy("Package", "Pakket")}</th>
                  <th>{copy("Created", "Gemaakt")}</th>
                  <th>{copy("Verification", "Verificatie")}</th>
                  <th>{copy("Coverage", "Dekking")}</th>
                  <th>{copy("Size", "Grootte")}</th>
                  <th>{copy("Ledger checksum", "Grootboekchecksum")}</th>
                </tr>
              </thead>
              <tbody>
                {items.slice(0, 5).map((backup) => (
                  <tr key={text(backup.backupFilename)}>
                    <td data-label={copy("Package", "Pakket")}>
                      <strong>{text(backup.backupFilename)}</strong>
                      <span>{text(backup.format)}</span>
                    </td>
                    <td data-label={copy("Created", "Gemaakt")}>{exactDateTime(backup.createdAt, dateLocale)}</td>
                    <td data-label={copy("Verification", "Verificatie")}>
                      <span className={`fab-status-chip tone-${statusTone(backup.status)}`}>{humanize(backup.status)}</span>
                    </td>
                    <td data-label={copy("Coverage", "Dekking")}>
                      <span className={`fab-status-chip tone-${statusTone(backup.sourceEvidenceStatus)}`}>{humanize(backup.sourceEvidenceStatus)}</span>
                      <span>{count(backup.sourceEvidenceDocuments)} {copy("documents", "documenten")}, {count(backup.sourceEvidenceFiles)} {copy("files", "bestanden")}</span>
                    </td>
                    <td data-label={copy("Size", "Grootte")}>{formatBytes(count(backup.sizeBytes))}</td>
                    <td data-label={copy("Ledger checksum", "Grootboekchecksum")}>
                      <code title={text(backup.ledgerSha256)}>{shortHash(backup.ledgerSha256)}</code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

        </>
      )}
      {showData && !items.length && (
        <FabPanelStateMessage
          resource={{ ...resource, state: "empty" }}
          title={copy("Recovery packages", "Herstelpakketten")}
          emptyTitle={copy("No verified package exists yet", "Er bestaat nog geen geverifieerd pakket")}
          emptyMessage={copy(
            "Create one now; the worker will then keep the schedule current.",
            "Maak er nu een; de worker houdt daarna het schema actueel.",
          )}
        />
      )}

      <div className="fab-panel-footer">
        <a href={`${localApiEndpoint}/#backups`} target="_blank" rel="noreferrer">
          {copy("Open advanced recovery", "Geavanceerd herstel openen")} <ArrowUpRight aria-hidden="true" />
        </a>
        <span>{copy(
          "Recovery creation reads source files only. Support bundles exclude documents, OCR, amounts, paths, and credentials. Restore remains confirmation-gated.",
          "Herstelpakketten lezen bronbestanden alleen. Supportpakketten sluiten documenten, OCR, bedragen, paden en inloggegevens uit. Herstel blijft beveiligd met bevestiging.",
        )}</span>
      </div>
    </section>
  );
}

function formatBytes(value: number): string {
  if (!Number.isFinite(value) || value <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  const scaled = value / (1024 ** index);
  return `${scaled.toFixed(index === 0 || scaled >= 10 ? 0 : 1)} ${units[index]}`;
}

function shortHash(value: unknown): string {
  const hash = text(value, "");
  return hash.length >= 16 ? `${hash.slice(0, 8)}...${hash.slice(-8)}` : "-";
}
