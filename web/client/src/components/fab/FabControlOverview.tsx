import {
  AlertTriangle,
  BookCheck,
  Bot,
  CircleDollarSign,
  ExternalLink,
  FileSearch,
  FileUp,
  MoreHorizontal,
  Play,
  RefreshCw,
  ShieldAlert,
} from "lucide-react";
import { FabDataStatus } from "./FabDataState";
import { useFabLocale } from "./fabLocale";
import {
  bool,
  count,
  exactDateTime,
  statusTone,
  text,
  type FabCommandId,
  type FabRecord,
  type FabResourceState,
} from "./fabView";

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

type DecisionContext = {
  lastSafeCycleAt: string | null;
  latestWorkflowStatus: string | null;
  dataThroughDate: string | null;
  sourceCount: number | null;
  readySourceCount: number | null;
  latestSourceSyncAt: string | null;
  unreconciledAmountByCurrency: Record<string, number> | null;
  oldestReviewAgeHours: number | null;
  highPriorityExceptions: number | null;
  ledgerReadyForApproval: number | null;
};

type FabControlOverviewProps = {
  connected: boolean;
  metrics: NullableMetrics;
  health: FabRecord;
  autonomy: FabRecord;
  closeReadiness: FabRecord;
  decisionContext: DecisionContext;
  metricResource?: FabResourceState;
  healthResource?: FabResourceState;
  exceptionResource?: FabResourceState;
  closeResource?: FabResourceState;
  workflowResource?: FabResourceState;
  sourceResource?: FabResourceState;
  ledgerResource?: FabResourceState;
  bankResource?: FabResourceState;
  reviewResource?: FabResourceState;
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
  decisionContext,
  metricResource,
  healthResource,
  exceptionResource,
  closeResource,
  workflowResource,
  sourceResource,
  ledgerResource,
  bankResource,
  reviewResource,
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
  const healthStatus = text(health.status || operations.status, connected ? "unknown" : "disconnected");
  const closeStatus = text(closeReadiness.status, "unavailable");
  const canRun = bool(autonomy.canRunAutonomously);
  const pendingReview = metrics.pendingReview;
  const pendingReviewDocuments = metrics.pendingReviewDocuments;
  const highPriority = decisionContext.highPriorityExceptions;
  const oldestReview = decisionContext.oldestReviewAgeHours;
  const decision = highPriority !== null && highPriority > 0
    ? {
        tone: "bad",
        title: copy(`${highPriority} high-risk exception${highPriority === 1 ? "" : "s"} need a decision`, `${highPriority} uitzondering${highPriority === 1 ? "" : "en"} met hoog risico vereist${highPriority === 1 ? "" : "en"} een beslissing`),
        detail: copy("Inspect the evidence before the next safe automation cycle.", "Controleer het bewijs voor de volgende veilige automatiseringscyclus."),
      }
    : pendingReviewDocuments !== null && pendingReviewDocuments > 0
      ? {
          tone: "warn",
          title: copy(`${pendingReviewDocuments} document${pendingReviewDocuments === 1 ? "" : "s"} are waiting for review`, `${pendingReviewDocuments} document${pendingReviewDocuments === 1 ? "" : "en"} wacht${pendingReviewDocuments === 1 ? "" : "en"} op controle`),
          detail: oldestReview === null
            ? copy("Resolve source-backed decisions to unblock posting.", "Los brononderbouwde beslissingen op om boekingen vrij te geven.")
            : copy(`The oldest open review is ${oldestReview} hours old.`, `De oudste open controle is ${oldestReview} uur oud.`),
        }
      : canRun
        ? {
            tone: "good",
            title: copy("No manual decision is blocking the next safe cycle", "Geen handmatige beslissing blokkeert de volgende veilige cyclus"),
            detail: copy("FAB can execute the currently eligible local work.", "FAB kan het momenteel uitvoerbare lokale werk uitvoeren."),
          }
        : {
            tone: "warn",
            title: copy("Automation gates require inspection", "Automatiseringspoorten vereisen controle"),
            detail: copy("Review capability readiness before starting another cycle.", "Controleer de capabiliteitsgereedheid voor een nieuwe cyclus."),
          };
  const primary = pendingReviewDocuments !== null && pendingReviewDocuments > 0
    ? {
        label: copy(
          `Review ${pendingReviewDocuments} document${pendingReviewDocuments === 1 ? "" : "s"}`,
          `${pendingReviewDocuments} document${pendingReviewDocuments === 1 ? "" : "en"} controleren`,
        ),
        action: () => navigateTo("review-workspace"),
      }
    : canRun
      ? {
          label: pendingCommand === "run_safe_cycle" ? copy("Cycle running...", "Cyclus wordt uitgevoerd...") : copy("Run safe cycle", "Veilige cyclus uitvoeren"),
          action: () => onCommand("run_safe_cycle"),
        }
      : {
          label: copy("Inspect automation gates", "Automatiseringspoorten bekijken"),
          action: () => navigateTo("automation"),
        };
  const amountExposure = formatCurrencyTotals(decisionContext.unreconciledAmountByCurrency, lang);
  const readySources = decisionContext.readySourceCount;
  const sourceCount = decisionContext.sourceCount;
  const latestSourceSyncAt = decisionContext.latestSourceSyncAt;

  const metricRows = [
    {
      label: copy("Operational health", "Operationele gezondheid"),
      value: hasData(healthResource) ? status(healthStatus) : null,
      detail: hasData(healthResource)
        ? `${count(operations.issueCount || array(operations.issues).length)} ${copy("active signals", "actieve signalen")}`
        : copy("Health source unavailable", "Gezondheidsbron niet beschikbaar"),
      icon: ShieldAlert,
      tone: statusTone(healthStatus),
      resource: healthResource,
      action: () => navigateTo("audit"),
    },
    {
      label: copy("Review queue", "Controlewachtrij"),
      value: metric(pendingReviewDocuments, lang),
      detail: pendingReview === null
        ? copy("Decision count unavailable", "Aantal beslissingen niet beschikbaar")
        : `${pendingReview} ${copy(pendingReview === 1 ? "open decision" : "open decisions", pendingReview === 1 ? "open beslissing" : "open beslissingen")}${oldestReview === null ? "" : ` · ${copy("oldest", "oudste")} ${oldestReview}u`}`,
      icon: FileSearch,
      tone: pendingReviewDocuments !== null && pendingReviewDocuments > 0 ? "warn" as const : "good" as const,
      resource: reviewResource || metricResource,
      action: () => navigateTo("review-workspace"),
    },
    {
      label: copy("Reconciliation", "Afstemming"),
      value: metric(metrics.unreconciledBankTransactions, lang),
      detail: amountExposure === null
        ? copy("Unmatched value unavailable", "Ongekoppelde waarde niet beschikbaar")
        : `${amountExposure || copy("No unmatched bank value", "Geen ongekoppelde bankwaarde")}${metrics.unreconciledDocuments === null ? "" : ` · ${metrics.unreconciledDocuments} ${copy("document records unmatched", "documentrecords ongekoppeld")}`}`,
      icon: CircleDollarSign,
      tone: metrics.unreconciled !== null && metrics.unreconciled > 0 ? "warn" as const : "good" as const,
      resource: bankResource || metricResource,
      action: () => navigateTo("recovery"),
    },
    {
      label: copy("Close readiness", "Afsluitgereedheid"),
      value: hasData(closeResource) ? status(closeStatus) : null,
      detail: hasData(closeResource)
        ? `${count(closeReadiness.blockingCount)} ${copy("blocking gates", "blokkerende poorten")}`
        : copy("Close evidence unavailable", "Afsluitbewijs niet beschikbaar"),
      icon: BookCheck,
      tone: statusTone(closeStatus),
      resource: closeResource,
      action: () => navigateTo("exceptions"),
    },
    {
      label: copy("Intake freshness", "Actualiteit inname"),
      value: sourceCount === null || readySources === null ? null : `${readySources}/${sourceCount}`,
      detail: latestSourceSyncAt
        ? `${copy("Last source update", "Laatste bronupdate")} ${exactDateTime(latestSourceSyncAt, dateLocale)}`
        : copy("Source update unavailable", "Bronupdate niet beschikbaar"),
      icon: RefreshCw,
      tone: sourceCount !== null && readySources === sourceCount && isRecent(latestSourceSyncAt, 48) ? "good" as const : "warn" as const,
      resource: sourceResource || ledgerResource,
      action: () => navigateTo("connections"),
    },
    {
      label: copy("Failed processing", "Mislukte verwerking"),
      value: metric(metrics.failedDocuments, lang),
      detail: decisionContext.ledgerReadyForApproval === null
        ? copy("Approval-ready count unavailable", "Aantal gereed voor goedkeuring niet beschikbaar")
        : `${decisionContext.ledgerReadyForApproval} ${copy("ledger rows ready for approval", "grootboekregels gereed voor goedkeuring")}`,
      icon: AlertTriangle,
      tone: metrics.failedDocuments !== null && metrics.failedDocuments > 0 ? "bad" as const : "good" as const,
      resource: metricResource,
      action: () => navigateTo("recovery"),
    },
  ];

  return (
    <section id="control-room" className="fab-control-overview">
      <div className="fab-page-heading">
        <div>
          <div className="fab-eyebrow"><Bot aria-hidden="true" /> {copy("Autonomous bookkeeping control", "Autonome boekhoudbesturing")}</div>
          <h1>{copy("Control room", "Controlecentrum")}</h1>
          <p>{copy("Supervise source-backed decisions and safe local automation.", "Bewaak brononderbouwde beslissingen en veilige lokale automatisering.")}</p>
        </div>
        <div className="fab-heading-actions">
          <button className="fab-secondary-button" onClick={onOpenIntake} disabled={commandPending || uploading}>
            <FileUp aria-hidden="true" /> {uploading ? copy("Adding...", "Toevoegen...") : copy("Add documents", "Documenten toevoegen")}
          </button>
          <button className="fab-primary-button" onClick={primary.action} disabled={!connected || commandPending}>
            <Play aria-hidden="true" /> {primary.label}
          </button>
          <button className="fab-icon-button" onClick={onOpenCommands} aria-label={copy("Open command centre", "Opdrachtencentrum openen")} title={copy("Command centre", "Opdrachtencentrum")}>
            <MoreHorizontal aria-hidden="true" />
          </button>
          <a className="fab-icon-button" href={localApiEndpoint} target="_blank" rel="noreferrer" aria-label={copy("Open advanced local ledger", "Geavanceerd lokaal grootboek openen")} title={copy("Advanced local ledger", "Geavanceerd lokaal grootboek")}>
            <ExternalLink aria-hidden="true" />
          </a>
        </div>
      </div>

      <div className={`fab-decision-rail tone-${decision.tone}`}>
        <div>
          <span>{copy("Operator decision", "Operatorbeslissing")}</span>
          <strong>{decision.title}</strong>
          <small>{decision.detail}</small>
        </div>
        <FabDataStatus resource={exceptionResource || reviewResource} />
      </div>

      <div className="fab-context-strip" aria-label={copy("Control-center data context", "Datacontext controlecentrum")}>
        <span><strong>{copy("Last refresh", "Laatst vernieuwd")}</strong>{exactDateTime(checkedAt, dateLocale)}</span>
        <span><strong>{copy("Last safe cycle", "Laatste veilige cyclus")}</strong>{exactDateTime(decisionContext.lastSafeCycleAt, dateLocale)}<small>{decisionContext.latestWorkflowStatus ? status(decisionContext.latestWorkflowStatus) : copy("No run evidence", "Geen runbewijs")}</small></span>
        <span><strong>{copy("Data through", "Gegevens t/m")}</strong>{shortDate(decisionContext.dataThroughDate, dateLocale)}</span>
        <span><strong>{copy("Fiscal period", "Boekingsperiode")}</strong>{period(closeReadiness.fromDate, closeReadiness.toDate, dateLocale, copy("Unavailable", "Niet beschikbaar"))}</span>
        <span><strong>{copy("Submission mode", "Indieningsmodus")}</strong>{status(closeReadiness.externalSubmission || "not_executed")}</span>
      </div>
      <details className="fab-technical-context">
        <summary>{copy("Technical refresh details", "Technische vernieuwingsdetails")}</summary>
        <span>{copy("Local API latency", "Lokale API-latentie")}: {latencyMs === null || latencyMs === undefined ? copy("Unavailable", "Niet beschikbaar") : `${latencyMs} ms`}</span>
        <FabDataStatus resource={workflowResource} />
      </details>

      <div className="fab-metric-strip" aria-label={copy("Decision metrics", "Beslissingsmetrics")}>
        {metricRows.map(({ label, value, detail, icon: Icon, tone, resource, action }) => (
          <button className={`fab-metric fab-metric-${value === null ? "bad" : tone}`} key={label} onClick={action}>
            <div className={`fab-metric-icon tone-${value === null ? "bad" : tone}`}><Icon aria-hidden="true" /></div>
            <div>
              <span>{label}</span>
              <strong>{value === null ? copy("Unavailable", "Niet beschikbaar") : value}</strong>
              <small>{detail}</small>
            </div>
            <FabDataStatus resource={resource} />
          </button>
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

function period(fromValue: unknown, toValue: unknown, locale: string, unavailable: string): string {
  const from = text(fromValue, "");
  const to = text(toValue, "");
  if (!from || !to) return unavailable;
  return from === to ? shortDate(from, locale) : `${shortDate(from, locale)} - ${shortDate(to, locale)}`;
}

function shortDate(value: unknown, locale: string): string {
  const raw = text(value, "");
  const timestamp = Date.parse(raw);
  if (!raw || Number.isNaN(timestamp)) return locale === "nl-NL" ? "Niet beschikbaar" : "Unavailable";
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(new Date(timestamp));
}

function formatCurrencyTotals(value: Record<string, number> | null, lang: "en" | "nl"): string | null {
  if (value === null) return null;
  const entries = Object.entries(value);
  if (!entries.length) return "";
  return entries.slice(0, 2).map(([currency, amount]) => {
    if (currency === "UNKNOWN") return new Intl.NumberFormat(lang === "nl" ? "nl-NL" : "en-NL", { maximumFractionDigits: 2 }).format(amount);
    return new Intl.NumberFormat(lang === "nl" ? "nl-NL" : "en-NL", { style: "currency", currency }).format(amount);
  }).join(" + ");
}

function hasData(resource?: FabResourceState): boolean {
  return resource?.state === "live" || resource?.state === "stale";
}

function navigateTo(sectionId: string) {
  document.getElementById(sectionId)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function isRecent(value: unknown, hours: number): boolean {
  const timestamp = Date.parse(text(value, ""));
  return !Number.isNaN(timestamp) && Date.now() - timestamp <= hours * 3_600_000;
}
