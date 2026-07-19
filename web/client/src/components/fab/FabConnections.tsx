import {
  ArrowUpRight,
  Bot,
  Building2,
  CheckCircle2,
  CircleDollarSign,
  Cloud,
  Database,
  HardDrive,
  Inbox,
  Landmark,
  Mail,
  RefreshCw,
  ScanText,
  Settings2,
  Unplug,
  UsersRound,
} from "lucide-react";
import { compactHumanize, matchesSearch, statusTone, text, timeAgo, type FabCommandId, type FabRecord } from "./fabView";

const connectorIcons: Record<string, typeof Cloud> = {
  local_folder: HardDrive,
  gmail: Mail,
  google_drive: Cloud,
  google_photos: Cloud,
  freshdesk: Inbox,
  tesseract_ocr: ScanText,
  waveapps_business: Building2,
  waveapps_personal: UsersRound,
  mijngeldzaken: Landmark,
  banking_api: CircleDollarSign,
  hai: Bot,
};

type FabConnectionsProps = {
  connections: FabRecord[];
  search: string;
  commandPending: boolean;
  localApiEndpoint: string;
  onCommand: (commandId: FabCommandId, payload?: FabRecord) => void;
};

export function FabConnections({ connections, search, commandPending, localApiEndpoint, onCommand }: FabConnectionsProps) {
  const visibleConnections = connections.filter((item) => matchesSearch(item, search));
  const syncableConnections = connections.filter((item) => item.canSync === true);
  const readyCount = connections.filter((item) => text(item.status) === "ready").length;

  return (
    <section id="connections" className="fab-section fab-connections-section">
      <div className="fab-section-heading">
        <div><span>Source and downstream controls</span><h2>Connections</h2></div>
        <div className="fab-connection-heading-actions">
          <span className="fab-status-chip tone-good">{readyCount}/{connections.length} ready</span>
          {syncableConnections.length ? (
            <button className="fab-secondary-button compact" onClick={() => onCommand("sync_sources")} disabled={commandPending}>
              <RefreshCw aria-hidden="true" /> Sync sources
            </button>
          ) : (
            <a className="fab-secondary-button compact" href={`${localApiEndpoint}/#settings`} target="_blank" rel="noreferrer">
              <Settings2 aria-hidden="true" /> Review setup
            </a>
          )}
        </div>
      </div>
      <div className="fab-connection-list">
        {visibleConnections.map((connection) => {
          const id = text(connection.id, "unknown");
          const Icon = connectorIcons[id] || Database;
          const status = text(connection.status, connection.ready ? "ready" : connection.configured ? "attention" : "not_configured");
          const canSync = connection.canSync === true && ["gmail", "google_drive", "google_photos", "freshdesk"].includes(id);
          const ready = status === "ready";
          const setupTarget = connectionSetupTarget(id, localApiEndpoint);
          return (
            <div className="fab-connection-row" key={id}>
              <div className={`fab-connection-icon tone-${statusTone(status)}`}><Icon aria-hidden="true" /></div>
              <div className="fab-connection-name"><strong>{text(connection.label, compactHumanize(id))}</strong><span>{text(ready ? connection.details : connection.nextAction || connection.details, "No connector details recorded.")}</span></div>
              <div className="fab-connection-last"><span>Last ledger signal</span><strong>{timeAgo(connection.lastSyncAt)}</strong></div>
              <span className={`fab-status-chip tone-${statusTone(status)}`}>{compactHumanize(status)}</span>
              {canSync ? (
                <button className="fab-icon-button" onClick={() => onCommand("sync_sources", { sources: [id] })} disabled={commandPending} aria-label={`Sync ${text(connection.label, id)}`} title={`Sync ${text(connection.label, id)}`}><RefreshCw aria-hidden="true" /></button>
              ) : ready && ["local_folder", "tesseract_ocr"].includes(id) ? (
                <span className="fab-connection-static tone-good" title="This local capability is ready"><CheckCircle2 aria-hidden="true" /></span>
              ) : (
                <a className="fab-icon-button" href={setupTarget} target="_blank" rel="noreferrer" aria-label={`Review ${text(connection.label, id)} setup`} title={`Review ${text(connection.label, id)} setup`}>
                  {ready ? <ArrowUpRight aria-hidden="true" /> : <Settings2 aria-hidden="true" />}
                </a>
              )}
            </div>
          );
        })}
        {!visibleConnections.length && <div className="fab-empty-state"><Unplug aria-hidden="true" /><strong>No matching connections</strong><span>Configure sources in FAB or adjust the search.</span></div>}
      </div>
    </section>
  );
}

function connectionSetupTarget(id: string, endpoint: string): string {
  const anchor = ["gmail", "google_drive", "google_photos", "freshdesk"].includes(id)
    ? "sources"
    : id === "mijngeldzaken"
      ? "mijngeldzaken"
      : id.startsWith("waveapps_")
        ? "wave"
        : id === "banking_api"
          ? "reconciliation"
          : id === "hai"
            ? "api/hai/manifest"
            : "settings";
  return anchor.startsWith("api/") ? `${endpoint}/${anchor}` : `${endpoint}/#${anchor}`;
}
