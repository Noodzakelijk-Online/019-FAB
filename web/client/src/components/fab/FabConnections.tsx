import {
  Bot,
  Building2,
  CircleDollarSign,
  Cloud,
  Database,
  HardDrive,
  Inbox,
  Landmark,
  Mail,
  RefreshCw,
  ScanText,
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
  onCommand: (commandId: FabCommandId, payload?: FabRecord) => void;
};

export function FabConnections({ connections, search, commandPending, onCommand }: FabConnectionsProps) {
  const visibleConnections = connections.filter((item) => matchesSearch(item, search));

  return (
    <section id="connections" className="fab-section fab-connections-section">
      <div className="fab-section-heading">
        <div><span>Source and downstream controls</span><h2>Connections</h2></div>
        <button className="fab-secondary-button compact" onClick={() => onCommand("sync_sources")} disabled={commandPending}>
          <RefreshCw aria-hidden="true" /> Sync sources
        </button>
      </div>
      <div className="fab-connection-list">
        {visibleConnections.map((connection) => {
          const id = text(connection.id, "unknown");
          const Icon = connectorIcons[id] || Database;
          const status = text(connection.status, connection.ready ? "ready" : connection.configured ? "attention" : "not_configured");
          const canSync = connection.canSync === true && ["gmail", "google_drive", "google_photos", "freshdesk"].includes(id);
          return (
            <div className="fab-connection-row" key={id}>
              <div className={`fab-connection-icon tone-${statusTone(status)}`}><Icon aria-hidden="true" /></div>
              <div className="fab-connection-name"><strong>{text(connection.label, compactHumanize(id))}</strong><span>{text(connection.details, "No connector details recorded.")}</span></div>
              <div className="fab-connection-last"><span>Last ledger signal</span><strong>{timeAgo(connection.lastSyncAt)}</strong></div>
              <span className={`fab-status-chip tone-${statusTone(status)}`}>{compactHumanize(status)}</span>
              {canSync ? (
                <button className="fab-icon-button" onClick={() => onCommand("sync_sources", { sources: [id] })} disabled={commandPending} aria-label={`Sync ${text(connection.label, id)}`} title={`Sync ${text(connection.label, id)}`}><RefreshCw aria-hidden="true" /></button>
              ) : (
                <span className="fab-connection-static" title="This connection does not expose a source sync command"><Unplug aria-hidden="true" /></span>
              )}
            </div>
          );
        })}
        {!visibleConnections.length && <div className="fab-empty-state"><Unplug aria-hidden="true" /><strong>No matching connections</strong><span>Configure sources in FAB or adjust the search.</span></div>}
      </div>
    </section>
  );
}
