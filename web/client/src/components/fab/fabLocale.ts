import { useLanguage } from "@/contexts/LanguageContext";
import { humanize } from "./fabView";

const dutchStatuses: Record<string, string> = {
  ok: "In orde",
  ready: "Gereed",
  completed: "Voltooid",
  running: "Bezig",
  blocked: "Geblokkeerd",
  failed: "Mislukt",
  error: "Fout",
  disconnected: "Niet verbonden",
  connected: "Verbonden",
  unavailable: "Niet beschikbaar",
  not_executed: "Niet uitgevoerd",
  not_configured: "Niet ingesteld",
  needs_token: "Token vereist",
  needs_business_id: "Bedrijfs-ID vereist",
  needs_validation: "Validatie vereist",
  needs_mapping: "Toewijzing vereist",
  credentials_required: "Referenties vereist",
  needs_attention: "Aandacht nodig",
  supervision_required: "Toezicht vereist",
  idle: "Inactief",
  high: "Hoog",
  medium: "Middel",
  low: "Laag",
};

export function useFabLocale() {
  const { lang, setLang } = useLanguage();
  const copy = (english: string, dutch: string) => lang === "nl" ? dutch : english;
  const status = (value: unknown) => {
    const key = typeof value === "string" ? value.toLowerCase() : "";
    return lang === "nl" && dutchStatuses[key] ? dutchStatuses[key] : humanize(value);
  };
  return {
    lang,
    setLang,
    copy,
    status,
    dateLocale: lang === "nl" ? "nl-NL" : "en-NL",
  };
}
