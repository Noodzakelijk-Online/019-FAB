import { useCallback, useEffect, useState } from "react";
import { AlertCircle, ChevronDown, LockKeyhole } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/_core/hooks/useAuth";
import { FabCommandDrawer } from "@/components/fab/FabCommandDrawer";
import { FabConnections } from "@/components/fab/FabConnections";
import { FabControlOverview } from "@/components/fab/FabControlOverview";
import { FabDeliveryQueue } from "@/components/fab/FabDeliveryQueue";
import { FabAutomationPanel } from "@/components/fab/FabAutomationPanel";
import { FabExceptionsPanel } from "@/components/fab/FabExceptionsPanel";
import { FabIntakeDrawer } from "@/components/fab/FabIntakeDrawer";
import { FabOperationsPanels } from "@/components/fab/FabOperationsPanels";
import { FabOperatorShell } from "@/components/fab/FabOperatorShell";
import { FabReviewWorkspace, type FabReviewResolution } from "@/components/fab/FabReviewWorkspace";
import type { FabCommandId, FabRecord } from "@/components/fab/fabView";
import { humanize, text } from "@/components/fab/fabView";
import { useFabLocale } from "@/components/fab/fabLocale";
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
  const { copy } = useFabLocale();
  const { user, loading: authLoading } = useAuth();
  const [search, setSearch] = useState("");
  const [commandDrawerOpen, setCommandDrawerOpen] = useState(false);
  const [intakeDrawerOpen, setIntakeDrawerOpen] = useState(false);
  const [pendingCommand, setPendingCommand] = useState<FabCommandId | null>(null);
  const [commandStartedAt, setCommandStartedAt] = useState<string | null>(null);
  const [lastCommand, setLastCommand] = useState<{ id: FabCommandId; status: string; startedAt: string | null; finishedAt: string } | null>(null);
  const [uploading, setUploading] = useState(false);
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
      if (pendingCommand) setLastCommand({ id: pendingCommand, status, startedAt: commandStartedAt, finishedAt: new Date().toISOString() });
      toast.success(`${pendingCommand ? humanize(pendingCommand) : "Command"}: ${humanize(status)}`);
      setPendingCommand(null);
      setCommandStartedAt(null);
      await controlCenter.refetch();
    },
    onError: (error) => {
      toast.error(error.message || copy("FAB command failed", "FAB-opdracht mislukt"));
      if (pendingCommand) setLastCommand({ id: pendingCommand, status: "failed", startedAt: commandStartedAt, finishedAt: new Date().toISOString() });
      setPendingCommand(null);
      setCommandStartedAt(null);
    },
  });
  const uploadIntake = trpc.fab.uploadIntake.useMutation();
  const resolveReview = trpc.fab.resolveReview.useMutation();

  const executeCommand = useCallback((commandId: FabCommandId, payload: FabRecord = {}) => {
    if (!controlCenter.data?.connection.connected || pendingCommand) return;
    setPendingCommand(commandId);
    setCommandStartedAt(new Date().toISOString());
    runCommand.mutate({ commandId, payload: payload as CommandPayload });
  }, [controlCenter.data?.connection.connected, pendingCommand, runCommand]);

  const uploadDocument = useCallback(async (file: File) => {
    if (!controlCenter.data?.connection.connected) throw new Error(copy("FAB local API is disconnected.", "De lokale FAB-API is niet verbonden."));
    await uploadIntake.mutateAsync({
      filename: file.name,
      mimeType: file.type || "application/octet-stream",
      contentBase64: await readFileBase64(file),
    });
  }, [controlCenter.data?.connection.connected, uploadIntake]);

  const finishIntake = useCallback(async (uploadedCount: number) => {
    toast.success(`${uploadedCount} ${copy(uploadedCount === 1 ? "document added to FAB intake." : "documents added to FAB intake.", uploadedCount === 1 ? "document toegevoegd aan FAB-inname." : "documenten toegevoegd aan FAB-inname.")}`);
    await controlCenter.refetch();
    executeCommand("process_imported");
  }, [controlCenter, executeCommand]);

  const resolveReviewItem = useCallback(async (input: FabReviewResolution) => {
    try {
      const result = await resolveReview.mutateAsync(input);
      toast.success(`${copy("Review updated", "Controle bijgewerkt")}: ${humanize(text(result.processingStatus, text(result.status)))}`);
      await controlCenter.refetch();
    } catch (error) {
      const message = error instanceof Error ? error.message : copy("Review update failed", "Bijwerken van controle mislukt");
      toast.error(message);
      throw error;
    }
  }, [controlCenter, copy, resolveReview]);

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
      connectionStatus={authLoading ? copy("Checking access", "Toegang controleren") : text(data?.connection.status, copy("Local API offline", "Lokale API offline"))}
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
          <h1>{copy("Operator access required", "Operatortoegang vereist")}</h1>
          <p>{copy("Sign in with an administrator account to operate the authoritative FAB ledger.", "Log in met een beheerdersaccount om het gezaghebbende FAB-grootboek te bedienen.")}</p>
        </div>
      ) : controlCenter.isLoading || authLoading || operatorAccess.isLoading ? (
        <FabLoadingState />
      ) : (
        <>
          {!connected && (
            <div className="fab-system-banner tone-bad">
              <AlertCircle aria-hidden="true" />
              <div><strong>{copy("FAB local API is disconnected", "De lokale FAB-API is niet verbonden")}</strong><span>{text(data?.connection.error, copy("Start the local FAB API and verify the server-side URL and token.", "Start de lokale FAB-API en controleer de server-URL en het token."))}</span></div>
              <button className="fab-secondary-button compact" onClick={() => { void controlCenter.refetch(); }}>{copy("Retry", "Opnieuw proberen")}</button>
            </div>
          )}
          {Boolean(data?.partialErrors.length) && connected && (
            <details className="fab-system-details tone-warn">
              <summary><AlertCircle aria-hidden="true" /><span><strong>{copy("Some control-center resources are retained or unavailable", "Sommige bronnen zijn bewaard of niet beschikbaar")}</strong><small>{copy("Inspect", "Bekijk")} {data?.partialErrors.length} {copy(data?.partialErrors.length === 1 ? "technical detail" : "technical details", data?.partialErrors.length === 1 ? "technisch detail" : "technische details")}</small></span><ChevronDown aria-hidden="true" /></summary>
              <div>{data?.partialErrors.map((item) => <p key={item.resource}><strong>{humanize(item.resource)} - {humanize(item.state)}</strong><span>{item.error}{item.updatedAt ? ` Last valid response: ${item.updatedAt}.` : ""}</span></p>)}</div>
            </details>
          )}
          <FabControlOverview
            connected={connected}
            metrics={data?.metrics || { documents: null, pendingReview: null, pendingReviewDocuments: null, unreconciled: null, unreconciledDocuments: null, unreconciledBankTransactions: null, exceptions: null, failedDocuments: null }}
            health={data?.health || {}}
            autonomy={data?.autonomy || {}}
            closeReadiness={data?.closeReadiness || {}}
            metricResource={data?.resourceStates.metrics}
            healthResource={data?.resourceStates.health}
            exceptionResource={data?.resourceStates.exceptions}
            closeResource={data?.resourceStates.closeReadiness}
            checkedAt={data?.connection.checkedAt}
            latencyMs={data?.connection.latencyMs}
            commandPending={Boolean(pendingCommand) || uploading}
            pendingCommand={pendingCommand}
            uploading={uploading}
            localApiEndpoint={data?.connection.endpoint || "http://127.0.0.1:5001"}
            onCommand={executeCommand}
            onOpenIntake={() => setIntakeDrawerOpen(true)}
            onOpenCommands={() => setCommandDrawerOpen(true)}
          />
          <FabReviewWorkspace
            workItems={data?.reviews.workItems || []}
            categoryOptions={data?.reviews.categoryOptions || []}
            summary={data?.reviews.summary || {}}
            resource={data?.resourceStates.reviewQueue}
            search={search}
            localApiEndpoint={data?.connection.endpoint || "http://127.0.0.1:5001"}
            resolvingReviewId={resolveReview.isPending ? resolveReview.variables?.reviewItemId || null : null}
            onResolve={resolveReviewItem}
          />
          <div className="fab-priority-grid">
            <FabExceptionsPanel
              exceptions={data?.exceptions || []}
              exceptionSummary={data?.exceptionSummary || {}}
              resource={data?.resourceStates.exceptions}
              closeReadiness={data?.closeReadiness || {}}
              closeResource={data?.resourceStates.closeReadiness}
              search={search}
              localApiEndpoint={data?.connection.endpoint || "http://127.0.0.1:5001"}
            />
            <FabAutomationPanel
              autonomy={data?.autonomy || {}}
              workflows={data?.workflows || []}
              autonomyResource={data?.resourceStates.autonomy}
              workflowResource={data?.resourceStates.workflows}
              pendingCommand={pendingCommand}
              connected={connected}
              onCommand={executeCommand}
            />
          </div>
          <FabOperationsPanels
            recovery={data?.recovery || {}}
            activity={data?.activity || []}
            workflows={data?.workflows || []}
            recoveryResource={data?.resourceStates.recovery}
            activityResource={data?.resourceStates.activity}
            workflowResource={data?.resourceStates.workflows}
            search={search}
            localApiEndpoint={data?.connection.endpoint || "http://127.0.0.1:5001"}
          />
          <FabDeliveryQueue
            delivery={data?.delivery || { status: {}, summary: {}, workOrders: [], count: null }}
            resource={data?.resourceStates.driveWaveWorkOrders}
            search={search}
            localApiEndpoint={data?.connection.endpoint || "http://127.0.0.1:5001"}
          />
          <FabConnections
            connections={data?.connections || []}
            search={search}
            commandPending={Boolean(pendingCommand)}
            resource={data?.resourceStates.settings}
            localApiEndpoint={data?.connection.endpoint || "http://127.0.0.1:5001"}
            onCommand={executeCommand}
          />
        </>
      )}
      <FabCommandDrawer
        open={commandDrawerOpen}
        connected={connected}
        pendingCommand={pendingCommand}
        commandStartedAt={commandStartedAt}
        lastCommand={lastCommand}
        onClose={() => setCommandDrawerOpen(false)}
        onCommand={executeCommand}
      />
      <FabIntakeDrawer
        open={intakeDrawerOpen}
        connected={connected}
        onClose={() => setIntakeDrawerOpen(false)}
        onUploadFile={uploadDocument}
        onFinished={finishIntake}
        onBusyChange={setUploading}
      />
    </FabOperatorShell>
  );
}

function readFileBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error(`Could not read ${file.name}`));
    reader.onload = () => {
      const result = typeof reader.result === "string" ? reader.result : "";
      const separator = result.indexOf(",");
      if (separator < 0) {
        reject(new Error(`Could not encode ${file.name}`));
        return;
      }
      resolve(result.slice(separator + 1));
    };
    reader.readAsDataURL(file);
  });
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
