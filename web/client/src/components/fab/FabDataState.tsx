import { AlertCircle, CheckCircle2, Clock3, DatabaseZap, Loader2 } from "lucide-react";
import { exactDateTime, type FabPanelState, type FabResourceState } from "./fabView";
import { useFabLocale } from "./fabLocale";

type FabDataStatusProps = {
  resource?: FabResourceState;
  state?: FabPanelState;
  emptyLabel?: string;
};

export function FabDataStatus({ resource, state, emptyLabel = "Empty" }: FabDataStatusProps) {
  const { copy, dateLocale } = useFabLocale();
  const effective = state || resource?.state || "unavailable";
  const config = dataStateConfig(effective, copy(emptyLabel, emptyLabel === "Clear" ? "Geen" : "Leeg"), copy);
  const Icon = config.icon;
  const title = resource?.updatedAt
    ? `${config.label}. ${copy("Last valid data", "Laatste geldige gegevens")}: ${exactDateTime(resource.updatedAt, dateLocale)}.`
    : config.label;

  return (
    <span className={`fab-data-status tone-${config.tone}`} title={title}>
      <Icon className={effective === "loading" ? "is-spinning" : ""} aria-hidden="true" />
      {config.label}
    </span>
  );
}

type FabPanelStateMessageProps = {
  resource?: FabResourceState;
  title: string;
  emptyTitle?: string;
  emptyMessage?: string;
  searchActive?: boolean;
};

export function FabPanelStateMessage({
  resource,
  title,
  emptyTitle = "No records returned",
  emptyMessage = "The live source positively returned an empty result.",
  searchActive = false,
}: FabPanelStateMessageProps) {
  const { copy, dateLocale } = useFabLocale();
  const state = resource?.state || "unavailable";
  if (state === "live") return null;
  if (state === "stale") {
    return (
      <div className="fab-panel-state tone-warn" role="status">
        <Clock3 aria-hidden="true" />
        <div>
          <strong>{title} {copy("is showing retained data", "toont bewaarde gegevens")}</strong>
          <span>{copy("Last valid response", "Laatste geldige reactie")}: {exactDateTime(resource?.updatedAt, dateLocale)}. {resource?.error || copy("The current refresh did not succeed.", "De huidige vernieuwing is niet geslaagd.")}</span>
        </div>
      </div>
    );
  }
  if (state === "loading") {
    return (
      <div className="fab-panel-state tone-info" role="status">
        <Loader2 className="is-spinning" aria-hidden="true" />
        <div><strong>{copy("Loading", "Laden")}: {title.toLowerCase()}</strong><span>{copy("Waiting for the authoritative local ledger.", "Wachten op het gezaghebbende lokale grootboek.")}</span></div>
      </div>
    );
  }
  if (state === "empty") {
    return (
      <div className="fab-panel-state tone-neutral" role="status">
        <CheckCircle2 aria-hidden="true" />
        <div><strong>{searchActive ? copy("No matching records", "Geen overeenkomende records") : emptyTitle}</strong><span>{searchActive ? copy("Adjust the active search or filters.", "Pas de actieve zoekopdracht of filters aan.") : emptyMessage}</span></div>
      </div>
    );
  }
  return (
    <div className="fab-panel-state tone-bad" role="alert">
      {state === "error" ? <AlertCircle aria-hidden="true" /> : <DatabaseZap aria-hidden="true" />}
      <div>
        <strong>{title}: {copy("data unavailable", "gegevens niet beschikbaar")}</strong>
        <span>{resource?.error || copy("FAB did not receive an authoritative response for this panel.", "FAB ontving geen gezaghebbende reactie voor dit paneel.")}</span>
      </div>
    </div>
  );
}

function dataStateConfig(state: FabPanelState, emptyLabel: string, copy: (english: string, dutch: string) => string) {
  switch (state) {
    case "live": return { label: copy("Live", "Actueel"), tone: "good", icon: CheckCircle2 } as const;
    case "empty": return { label: emptyLabel, tone: "neutral", icon: CheckCircle2 } as const;
    case "stale": return { label: copy("Stale", "Verouderd"), tone: "warn", icon: Clock3 } as const;
    case "loading": return { label: copy("Loading", "Laden"), tone: "info", icon: Loader2 } as const;
    case "error": return { label: copy("Error", "Fout"), tone: "bad", icon: AlertCircle } as const;
    default: return { label: copy("Unavailable", "Niet beschikbaar"), tone: "bad", icon: DatabaseZap } as const;
  }
}
