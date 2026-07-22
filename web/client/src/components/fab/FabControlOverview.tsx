import {
  AlertTriangle,
  BookCheck,
  Bot,
  CircleDollarSign,
  ExternalLink,
  FileSearch,
  FileStack,
  FileUp,
  MoreHorizontal,
  Play,
  ShieldAlert,
} from "lucide-react";
import { FabDataStatus } from "./FabDataState";
import { useFabLocale } from "./fabLocale";
import { bool, count, exactDateTime, statusTone, text, type FabCommandId, type FabRecord, type FabResourceState } from "./fabView";

type NullableMetrics = {
  documents: number | null;
  pendingReview: number | null;
  pendingReviewDocuments: number | null;
  unreconciled: number | null;
  unreconciledDocuments: number | null;
  unreconciledBankTransactions: number | null;
  exceptions: number | null;
  failedDocuments: number | null;
};

type FabControlOverviewProps = {
  connected: boolean;
  metrics: NullableMetrics;
  health: FabRecord;
  autonomy: FabRecord;
  closeReadiness: FabRecord;
  metricResource?: FabResourceState;
  healthResource?: FabResourceState;
  exceptionResource?: FabResourceState;
  closeResource?: FabResourceState;
  checkedAt?: string | null;
  latencyMs?: number | null;
  commandPending: boolean;
  pendingCommand: FabCommandId | null;
  uploading: boolean;
  localApiEndpoint: string;
  onCommand: (commandId: FabCommandId) => void;
  onOpenIntake: () => void;
  onOpenCommands: () => void;
};

export function FabControlOverview({
  connected,
  metrics,
  health,
  autonomy,
  closeReadiness,
  metricResource,
  healthResource,
  exceptionResource,
  closeResource,
  checkedAt,
  latencyMs,
  commandPending,
  pendingCommand,
  uploading,
  localApiEndpoint,
  onCommand,
  onOpenIntake,
  onOpenCommands,
}: FabControlOverviewProps) {
  const { lang, copy, status, dateLocale } = useFabLocale();
  const operations = record(health.operations);
  const healthStatus = text(operations.status || health.status, connected ? "unknown" : "disconnected");
  const closeStatus = text(closeReadiness.status, "unavailable");
  const canRun = bool(autonomy.canRunAutonomously);
  const pendingReview = metrics.pendingReview;
  const pendingReviewDocuments = metrics.pendingReviewDocuments;
  const primary = pendingReviewDocuments !== null && pendingReviewDocuments > 0
    ? { label: lang === "nl" ? `Controleer ${pendingReviewDocuments} document${pendingReviewDocuments === 1 ? "" : "en"}` : `Review ${pendingReviewDocuments} document${pendingReviewDocuments === 1 ? "" : "s"}`, action: () => document.getElementById("review-workspace")?.scrollIntoView({ behavior: "smooth" }) }
    : canRun
      ? { label: pendingCommand === "run_safe_cycle" ? copy("Cycle running...", "Cyclus wordt uitgevoerd...") : copy("Run safe cycle", "Veilige cyclus uitvoeren"), action: () => onCommand("run_safe_cycle") }
      : { label: copy("Inspect automation gates", "Automatiseringspoorten bekijken"), action: () => document.getElementById("automation")?.scrollIntoView({ behavior: "smooth" }) };

  const metricRows = [
    {
      label: copy("Operational health", "Operationele gezondheid"),
      value: healthResource?.state === "live" || healthResource?.state === "stale" ? status(healthStatus) : null,
      detail: healthResource?.state === "live" || healthResource?.state === "stale" ? `${count(operations.issueCount || array(operations.issues).length)} ${copy("active signals", "actieve signalen")}` : copy("Health source unavailable", "Gezondheidsbron niet beschikbaar"),
      icon: ShieldAlert,
      tone: statusTone(healthStatus),
      resource: healthResource,
    },
    {
      label: copy("Documents in ledger", "Documenten in grootboek"),
      value: metric(metrics.documents, lang),
      detail: copy("Authoritative local records", "Gezaghebbende lokale records"),
      icon: FileStack,
      tone: "info" as const,
      resource: metricResource,
    },
    {
      label: copy("Review backlog", "Controleachterstand"),
      value: metric(pendingReviewDocuments, lang),
      detail: pendingReview === null
        ? copy("Decision count unavailable", "Aantal beslissingen niet beschikbaar")
        : `${pendingReview} ${copy(pendingReview === 1 ? "open decision" : "open decisions", pendingReview === 1 ? "open beslissing" : "open beslissingen")}`,
      icon: FileSearch,
      tone: pendingReviewDocuments !== null && pendingReviewDocuments > 0 ? "warn" as const : "good" as const,
      resource: metricResource,
    },
    {
      label: copy("Bank lines unmatched", "Ongekoppelde bankregels"),
      value: metric(metrics.unreconciledBankTransactions, lang),
      detail: metrics.unreconciledDocuments === null ? copy("Document matching unavailable", "Documentkoppeling niet beschikbaar") : `${metrics.unreconciledDocuments} ${copy("documents unmatched", "documenten ongekoppeld")}`,
      icon: CircleDollarSign,
      tone: metrics.unreconciled !== null && metrics.unreconciled > 0 ? "warn" as const : "good" as const,
      resource: metricResource,
    },
    {
      label: copy("Failed documents", "Mislukte documenten"),
      value: metric(metrics.failedDocuments, lang),
      detail: copy("Requires recovery or review", "Vereist herstel of controle"),
      icon: AlertTriangle,
      tone: metrics.failedDocuments !== null && metrics.failedDocuments > 0 ? "bad" as const : "good" as const,
      resource: metricResource,
    },
    {
      label: copy("Close readiness", "Afsluitgereedheid"),
      value: closeResource?.state === "live" || closeResource?.state === "stale" ? status(closeStatus) : null,
      detail: closeResource?.state === "live" || closeResource?.state === "stale" ? `${count(closeReadiness.blockingCount)} ${copy("blocking gates", "blokkerende poorten")}` : copy("Close evidence unavailable", "Afsluitbewijs niet beschikbaar"),
      icon: BookCheck,
      tone: statusTone(closeStatus),
      resource: closeResource,
    },
  ];

  return (
    <section id="control-room" className="fab-control-overview">
      <div className="fab-page-heading">
        <div>
          <div className="fab-eyebrow"><Bot aria-hidden="true" /> {copy("Autonomous bookkeeping control", "Autonome boekhoudbesturing")}</div>
          <h1>{copy("Control room", "Controlecentrum")}</h1>
          <p>{copy("Decide what needs attention, supervise safe automation, and keep every downstream action evidence-bound.", "Bepaal wat aandacht nodig heeft, bewaak veilige automatisering en houd iedere vervolgactie bewijsgebonden.")}</p>
        </div>
        <div className="fab-heading-actions">
          <button className="fab-secondary-button" onClick={onOpenIntake} disabled={commandPending || uploading}>
            <FileUp aria-hidden="true" /> {uploading ? copy("Adding receipts...", "Bonnen toevoegen...") : copy("Add receipts", "Bonnen toevoegen")}
          </button>
          <button className="fab-primary-button" onClick={primary.action} disabled={!connected || commandPending}>
            <Play aria-hidden="true" /> {primary.label}
          </button>
          <a className="fab-secondary-button" href={localApiEndpoint} target="_blank" rel="noreferrer">
            <ExternalLink aria-hidden="true" /> {copy("Open advanced local ledger", "Geavanceerd lokaal grootboek openen")}
          </a>
          <button className="fab-secondary-button" onClick={onOpenCommands}>
            <MoreHorizontal aria-hidden="true" /> {copy("Command centre", "Opdrachtencentrum")}
          </button>
        </div>
      </div>

      <div className="fab-context-strip" aria-label="Control-center data context">
        <span><strong>{copy("Last refresh", "Laatst vernieuwd")}</strong>{exactDateTime(checkedAt, dateLocale)}</span>
        <span><strong>API-latentie</strong>{latencyMs === null || latencyMs === undefined ? copy("Unavailable", "Niet beschikbaar") : `${latencyMs} ms`}</span>
        <span><strong>{copy("Fiscal period", "Boekingsperiode")}</strong>{period(closeReadiness.fromDate, closeReadiness.toDate, dateLocale)}</span>
        <span><strong>{copy("Submission mode", "Indieningsmodus")}</strong>{status(closeReadiness.externalSubmission || "not_executed")}</span>
      </div>

      <div className="fab-metric-strip" aria-label="Decision metrics">
        {metricRows.map(({ label, value, detail, icon: Icon, tone, resource }) => (
          <div className={`fab-metric fab-metric-${value === null ? "bad" : tone}`} key={label}>
            <div className={`fab-metric-icon tone-${value === null ? "bad" : tone}`}><Icon aria-hidden="true" /></div>
            <div>
              <span>{label}</span>
              <strong>{value === null ? copy("Unavailable", "Niet beschikbaar") : value}</strong>
              <small>{detail}</small>
            </div>
            <FabDataStatus resource={resource} />
          </div>
        ))}
      </div>
    </section>
  );
}

function metric(value: number | null, lang: "en" | "nl"): string | null {
  return value === null ? null : new Intl.NumberFormat(lang === "nl" ? "nl-NL" : "en-NL").format(value);
}

function record(value: unknown): FabRecord {
  return value && typeof value === "object" && !Array.isArray(value) ? value as FabRecord : {};
}

function array(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function period(fromValue: unknown, toValue: unknown, locale: string): string {
  const from = text(fromValue, "");
  const to = text(toValue, "");
  if (!from || !to) return "Unavailable";
  return from === to ? exactDateTime(`${from}T00:00:00Z`, locale).split(",")[0] : `${from} - ${to}`;
}
