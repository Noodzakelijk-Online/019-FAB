import { useEffect } from "react";
import {
  BellRing,
  Bot,
  FileScan,
  FolderSearch2,
  Landmark,
  RefreshCw,
  RotateCcw,
  ScanSearch,
  ShieldCheck,
  X,
} from "lucide-react";
import type { FabCommandId, FabRecord } from "./fabView";

const commands: Array<{ id: FabCommandId; label: string; description: string; icon: typeof Bot }> = [
  { id: "run_safe_cycle", label: "Run safe cycle", description: "Collect, process, classify, reconcile, and prepare local evidence.", icon: Bot },
  { id: "rescan_intake", label: "Rescan intake", description: "Register files from configured local and scanner folders.", icon: FolderSearch2 },
  { id: "process_imported", label: "Process imported", description: "Run OCR, validation, duplicate checks, and classification.", icon: FileScan },
  { id: "sync_sources", label: "Sync sources", description: "Collect from configured Gmail, Drive, Photos, and Freshdesk sources.", icon: RefreshCw },
  { id: "run_reconciliation", label: "Run reconciliation", description: "Match bank transactions against document-backed records.", icon: ScanSearch },
  { id: "run_due_recovery", label: "Run due recovery", description: "Retry only failed steps FAB has classified as safe and due.", icon: RotateCcw },
  { id: "refresh_notifications", label: "Refresh notifications", description: "Rebuild the local exception and notification signals.", icon: BellRing },
  { id: "run_due_reports", label: "Run due reports", description: "Generate scheduled checksum-bound local report artifacts.", icon: Landmark },
  { id: "assess_compliance", label: "Assess compliance", description: "Prepare a provisional Dutch VAT and retention assessment.", icon: ShieldCheck },
];

type FabCommandDrawerProps = {
  open: boolean;
  pendingCommand: FabCommandId | null;
  onClose: () => void;
  onCommand: (commandId: FabCommandId, payload?: FabRecord) => void;
};

export function FabCommandDrawer({ open, pendingCommand, onClose, onCommand }: FabCommandDrawerProps) {
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fab-command-overlay" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <aside className="fab-command-drawer" role="dialog" aria-modal="true" aria-labelledby="fab-command-title">
        <div className="fab-command-header">
          <div><span>Operator controls</span><h2 id="fab-command-title">Safe commands</h2></div>
          <button className="fab-icon-button" onClick={onClose} aria-label="Close commands" title="Close commands"><X aria-hidden="true" /></button>
        </div>
        <div className="fab-command-policy"><ShieldCheck aria-hidden="true" /><span>These commands mutate only FAB's local operating state. Approvals, exports, and external submissions are excluded.</span></div>
        <div className="fab-command-list">
          {commands.map(({ id, label, description, icon: Icon }) => (
            <button key={id} className="fab-command-row" onClick={() => onCommand(id)} disabled={Boolean(pendingCommand)}>
              <span className="fab-command-icon"><Icon className={pendingCommand === id ? "is-spinning" : ""} aria-hidden="true" /></span>
              <span><strong>{label}</strong><small>{description}</small></span>
              <span className="fab-command-risk">Local safe</span>
            </button>
          ))}
        </div>
        <div className="fab-hai-note"><Bot aria-hidden="true" /><span><strong>HAI-ready contract</strong>The same command catalog is exposed through the disabled-by-default, allowlisted HAI connector.</span></div>
      </aside>
    </div>
  );
}
