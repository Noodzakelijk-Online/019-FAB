import {
  Archive,
  ArrowUpRight,
  CloudUpload,
  FileCheck2,
  FileClock,
  ShieldCheck,
} from "lucide-react";
import { FabDataStatus, FabPanelStateMessage } from "./FabDataState";
import { useFabLocale } from "./fabLocale";
import {
  asRecord,
  count,
  humanize,
  matchesSearch,
  panelState,
  statusTone,
  text,
  type FabRecord,
  type FabResourceState,
} from "./fabView";

type FabDeliveryQueueProps = {
  delivery: {
    status: FabRecord;
    summary: FabRecord;
    workOrders: FabRecord[];
    count: number | null;
  };
  resource?: FabResourceState;
  search: string;
  localApiEndpoint: string;
};

export function FabDeliveryQueue({ delivery, resource, search, localApiEndpoint }: FabDeliveryQueueProps) {
  const { copy, status: localizedStatus } = useFabLocale();
  const visibleOrders = delivery.workOrders.filter((item) => matchesSearch(item, search));
  const connectorStatus = text(delivery.status.status, "unavailable");
  const relayReady = delivery.status.relayIntakeReady === true;
  const resourceAvailable = resource?.state === "live" || resource?.state === "stale";
  const readyToArchive = resourceAvailable ? count(delivery.summary.readyToArchive) : null;
  const completed = resourceAvailable ? count(delivery.summary.completed) : null;
  const verifiedOrReady = readyToArchive === null || completed === null ? null : readyToArchive + completed;
  const needsVerification = resourceAvailable ? count(delivery.summary.needsAttachmentVerification) + count(delivery.summary.needsFreshReadback) : null;
  const blocked = resourceAvailable ? count(delivery.summary.sourceUnavailable) + count(delivery.summary.sourceIncompatible) + count(delivery.summary.needsProcessing) + count(delivery.summary.blockedByReview) + count(delivery.summary.needsWaveTransaction) : null;
  const state = panelState(resource, delivery.workOrders.length);

  return (
    <section id="delivery" className="fab-section fab-delivery-section">
      <div className="fab-section-heading">
        <div>
          <span>{copy("Verified document handoff", "Geverifieerde documentoverdracht")}</span>
          <h2>{copy("Source to Wave delivery", "Bron naar Wave levering")}</h2>
        </div>
        <div className="fab-section-statuses">
          <FabDataStatus resource={resource} state={state} />
          <span className={`fab-status-chip tone-${statusTone(connectorStatus)}`}>{localizedStatus(connectorStatus)}</span>
          <a className="fab-icon-button" href={`${localApiEndpoint}/api/drive-wave/work-orders`} target="_blank" rel="noreferrer" aria-label={copy("Open delivery work orders", "Open leveringsopdrachten")} title={copy("Open delivery work orders", "Open leveringsopdrachten")}>
            <ArrowUpRight aria-hidden="true" />
          </a>
        </div>
      </div>

      <div className="fab-delivery-summary" aria-label={copy("Delivery queue summary", "Samenvatting leveringswachtrij")}>
        <DeliveryMetric icon={CloudUpload} label={copy("Work orders", "Opdrachten")} value={delivery.count} tone="info" />
        <DeliveryMetric icon={FileClock} label={copy("Needs proof", "Bewijs nodig")} value={needsVerification} tone={needsVerification ? "warn" : "neutral"} />
        <DeliveryMetric icon={ShieldCheck} label={copy("Policy blocked", "Beleid blokkeert")} value={blocked} tone={blocked ? "bad" : "neutral"} />
        <DeliveryMetric icon={Archive} label={copy("Verified or archive-ready", "Geverifieerd of archiefklaar")} value={verifiedOrReady} tone={verifiedOrReady ? "good" : "neutral"} />
      </div>

      {connectorStatus === "needs_authorization" && (
        <div className="fab-delivery-gate tone-warn">
          <ShieldCheck aria-hidden="true" />
          <div>
            <strong>{relayReady ? copy("Relay intake ready; archive authorization required", "Relayinname gereed; archiefautorisatie vereist") : copy("Drive authorization required", "Drive-autorisatie vereist")}</strong>
            <span>{relayReady ? copy("HAI can hand exact Drive bytes into FAB now. Install the Google OAuth desktop credentials and run Authorize-FAB-GoogleDrive.cmd before FAB can move a fully verified source into the archive folder.", "HAI kan nu exacte Drive-bytes aan FAB leveren. Installeer de Google OAuth-desktopgegevens en voer Authorize-FAB-GoogleDrive.cmd uit voordat FAB een volledig geverifieerde bron naar de archiefmap kan verplaatsen.") : copy("Install the Google OAuth desktop credentials, then run Authorize-FAB-GoogleDrive.cmd. Source files remain in the intake folder until Wave attachment proof passes.", "Installeer de Google OAuth-desktopgegevens en voer daarna Authorize-FAB-GoogleDrive.cmd uit. Bronbestanden blijven in de inname-map totdat het Wave-bijlagebewijs slaagt.")}</span>
          </div>
        </div>
      )}

      {(resource?.state === "live" || resource?.state === "stale") && visibleOrders.length > 0 && (
        <div className="fab-table-wrap">
          <table className="fab-table fab-delivery-table">
            <thead>
              <tr>
                <th>{copy("Source file", "Bronbestand")}</th>
                <th>{copy("Required action", "Vereiste actie")}</th>
                <th>{copy("Wave target", "Wave-doel")}</th>
                <th>{copy("Retention gate", "Bewaarcontrole")}</th>
                <th><span className="sr-only">{copy("Inspect", "Bekijken")}</span></th>
              </tr>
            </thead>
            <tbody>
              {visibleOrders.map((order) => {
                const source = asRecord(order.source);
                const wave = asRecord(order.wave);
                const archivePlan = asRecord(order.archivePlan);
                const blockerCount = Array.isArray(archivePlan.reasons)
                  ? archivePlan.reasons.length
                  : count(asRecord(order.reviews).blocking);
                const stage = text(order.stage, "needs_processing");
                const documentId = text(order.documentId, "");
                const sourceProvider = text(source.provider, "google_drive");
                const isGmailScanner = sourceProvider === "gmail";
                const gmailVerified = isGmailScanner && archivePlan.evidenceVerified === true;
                return (
                  <tr key={text(order.workOrderId, documentId)}>
                    <td data-label={copy("Source file", "Bronbestand")}>
                      <strong>{text(source.filename, copy("Unnamed document", "Naamloos document"))}</strong>
                      <span>{humanize(sourceProvider)} | {text(source.mimeType, "-")} | {text(source.sha256, "-").slice(0, 12)}</span>
                    </td>
                    <td data-label={copy("Required action", "Vereiste actie")}>
                      <span className={`fab-status-chip tone-${statusTone(stage)}`}>{humanize(stage)}</span>
                      <span>{text(order.actionRequired, "-")}</span>
                    </td>
                    <td data-label={copy("Wave target", "Wave-doel")}>
                      <strong>{text(wave.externalTransactionId, copy("Transaction not bound", "Transactie niet gekoppeld"))}</strong>
                      <span>{text(wave.targetSystem, "waveapps_business")}</span>
                    </td>
                    <td data-label={copy("Retention gate", "Bewaarcontrole")}>
                      <strong>
                        {gmailVerified
                          ? copy("Verified; email unchanged", "Geverifieerd; e-mail ongewijzigd")
                          : isGmailScanner
                            ? copy("Email and evidence retained", "E-mail en bewijs behouden")
                            : archivePlan.canArchive === true
                              ? copy("All checks passed", "Alle controles geslaagd")
                              : copy("Source retained", "Bron behouden")}
                      </strong>
                      <span>
                        {gmailVerified
                          ? copy("No source mutation or deletion", "Geen bronwijziging of verwijdering")
                          : isGmailScanner
                            ? `${blockerCount} ${copy("verification checks open", "verificatiecontroles open")}`
                            : archivePlan.canArchive === true
                              ? copy("Move-only worker may proceed", "Verplaatsingsworker mag doorgaan")
                              : `${blockerCount} ${copy("blocking checks", "blokkerende controles")}`}
                      </span>
                    </td>
                    <td>
                      <a className="fab-icon-button" href={`${localApiEndpoint}/api/drive-wave/documents/${documentId}/work-order`} target="_blank" rel="noreferrer" aria-label={`${copy("Inspect work order", "Bekijk opdracht")} ${documentId}`} title={copy("Inspect work order", "Bekijk opdracht")}>
                        <ArrowUpRight aria-hidden="true" />
                      </a>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {resource?.state === "stale" && <FabPanelStateMessage resource={resource} title={copy("Delivery queue", "Leveringswachtrij")} />}
      {resource?.state !== "live" && resource?.state !== "stale" && <FabPanelStateMessage resource={resource} title={copy("Delivery queue", "Leveringswachtrij")} />}
      {resource?.state === "live" && !visibleOrders.length && (
        <div className="fab-empty-state compact">
          <FileCheck2 aria-hidden="true" />
          <strong>{delivery.workOrders.length ? copy("No matching delivery work orders", "Geen overeenkomende leveringsopdrachten") : copy("No source documents queued", "Geen brondocumenten in de wachtrij")}</strong>
          <span>{delivery.workOrders.length ? copy("Adjust the active search.", "Pas de zoekopdracht aan.") : copy("Trusted Gmail scanner and authorized Drive intake create one evidence-bound work order per accepted source file.", "Vertrouwde Gmail-scanner- en geautoriseerde Drive-inname maken per geaccepteerd bronbestand een bewijsgebonden opdracht.")}</span>
        </div>
      )}
    </section>
  );
}

function DeliveryMetric({ icon: Icon, label, value, tone }: { icon: typeof Archive; label: string; value: number | null; tone: string }) {
  return (
    <div className="fab-delivery-metric">
      <span className={`tone-${tone}`}><Icon aria-hidden="true" /></span>
      <div><strong>{value === null ? "-" : value}</strong><small>{label}</small></div>
    </div>
  );
}
