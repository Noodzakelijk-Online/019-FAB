import { useCallback, useEffect, useState } from "react";
import { AlertCircle, LockKeyhole } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/_core/hooks/useAuth";
import { FabCommandDrawer } from "@/components/fab/FabCommandDrawer";
import { FabConnections } from "@/components/fab/FabConnections";
import { FabControlOverview } from "@/components/fab/FabControlOverview";
import { FabOperationsPanels } from "@/components/fab/FabOperationsPanels";
import { FabOperatorShell } from "@/components/fab/FabOperatorShell";
import type { FabCommandId, FabRecord } from "@/components/fab/fabView";
import { humanize, text } from "@/components/fab/fabView";
import { trpc } from "@/lib/trpc";
import "@/components/fab/fab-operator.css";

type CommandPayload = {
  limit?: number;
  sources?: Array<"gmail" | "google_drive" | "freshdesk" | "google_photos">;
  dryRun?: boolean;
  fromDate?: string;
  toDate?: string;
  targetSystem?: string;
};

export default function AdminOperations() {
  const { user, loading: authLoading } = useAuth();
  const [search, setSearch] = useState("");
  const [commandDrawerOpen, setCommandDrawerOpen] = useState(false);
  const [pendingCommand, setPendingCommand] = useState<FabCommandId | null>(null);
  const isAdmin = user?.role === "admin";
  const operatorAccess = trpc.fab.access.useQuery(undefined, {
    retry: false,
    refetchOnWindowFocus: false,
  });
  const hasOperatorAccess = isAdmin || operatorAccess.data?.allowed === true;

  const controlCenter = trpc.fab.controlCenter.useQuery(undefined, {
    enabled: hasOperatorAccess,
    refetchInterval: 60_000,
    refetchOnWindowFocus: false,
  });
  const runCommand = trpc.fab.runCommand.useMutation({
    onSuccess: async (result) => {
      const status = text(result.status, text(result.result && typeof result.result === "object" ? (result.result as FabRecord).status : "", "completed"));
      toast.success(`${pendingCommand ? humanize(pendingCommand) : "Command"}: ${humanize(status)}`);
      setPendingCommand(null);
      await controlCenter.refetch();
    },
    onError: (error) => {
      toast.error(error.message || "FAB command failed");
      setPendingCommand(null);
    },
  });

  const executeCommand = useCallback((commandId: FabCommandId, payload: FabRecord = {}) => {
    if (!controlCenter.data?.connection.connected || pendingCommand) return;
    setPendingCommand(commandId);
    runCommand.mutate({ commandId, payload: payload as CommandPayload });
  }, [controlCenter.data?.connection.connected, pendingCommand, runCommand]);

  const operatorLabel = user?.name || user?.email || operatorAccess.data?.operatorLabel || "Operator";
  const data = controlCenter.data;
  const connected = Boolean(data?.connection.connected);

  useEffect(() => {
    document.documentElement.classList.add("fab-operator-active");
    return () => document.documentElement.classList.remove("fab-operator-active");
  }, []);

  return (
    <FabOperatorShell
      connected={connected}
      connectionStatus={authLoading ? "Checking access" : text(data?.connection.status, "Local API offline")}
      organization="FAB Local Ledger"
      operatorLabel={operatorLabel}
      search={search}
      onSearchChange={setSearch}
      onRefresh={() => { void controlCenter.refetch(); }}
      refreshing={controlCenter.isFetching}
      onOpenCommands={() => setCommandDrawerOpen(true)}
    >
      {!authLoading && !operatorAccess.isLoading && !hasOperatorAccess ? (
        <div className="fab-access-state">
          <LockKeyhole aria-hidden="true" />
          <h1>Operator access required</h1>
          <p>Sign in with an administrator account to operate the authoritative FAB ledger.</p>
        </div>
      ) : controlCenter.isLoading || authLoading || operatorAccess.isLoading ? (
        <FabLoadingState />
      ) : (
        <>
          {!connected && (
            <div className="fab-system-banner tone-bad">
              <AlertCircle aria-hidden="true" />
              <div><strong>FAB local API is disconnected</strong><span>{text(data?.connection.error, "Start the local FAB API and verify the server-side URL and token.")}</span></div>
              <button className="fab-secondary-button compact" onClick={() => { void controlCenter.refetch(); }}>Retry</button>
            </div>
          )}
          {Boolean(data?.partialErrors.length) && connected && (
            <div className="fab-system-banner tone-warn">
              <AlertCircle aria-hidden="true" />
              <div><strong>Some control-center resources are unavailable</strong><span>{data?.partialErrors.map((item) => item.resource).join(", ")}</span></div>
            </div>
          )}
          <FabControlOverview
            connected={connected}
            metrics={data?.metrics || { documents: 0, pendingReview: 0, unreconciled: 0, exceptions: 0, failedDocuments: 0 }}
            health={data?.health || {}}
            autonomy={data?.autonomy || {}}
            closeReadiness={data?.closeReadiness || {}}
            commandPending={Boolean(pendingCommand)}
            onCommand={executeCommand}
            onOpenCommands={() => setCommandDrawerOpen(true)}
          />
          <FabOperationsPanels
            exceptions={data?.exceptions || []}
            exceptionSummary={data?.exceptionSummary || {}}
            recovery={data?.recovery || {}}
            activity={data?.activity || []}
            workflows={data?.workflows || []}
            search={search}
            localApiEndpoint={data?.connection.endpoint || "http://127.0.0.1:5001"}
          />
          <FabConnections
            connections={data?.connections || []}
            search={search}
            commandPending={Boolean(pendingCommand)}
            onCommand={executeCommand}
          />
        </>
      )}
      <FabCommandDrawer
        open={commandDrawerOpen && connected}
        pendingCommand={pendingCommand}
        onClose={() => setCommandDrawerOpen(false)}
        onCommand={executeCommand}
      />
    </FabOperatorShell>
  );
}

function FabLoadingState() {
  return (
    <div className="fab-loading-state" aria-label="Loading FAB control center">
      <div className="fab-loading-heading"><span /><span /></div>
      <div className="fab-loading-metrics">{Array.from({ length: 4 }, (_, index) => <span key={index} />)}</div>
      <div className="fab-loading-panel" />
      <div className="fab-loading-panel short" />
    </div>
  );
}
