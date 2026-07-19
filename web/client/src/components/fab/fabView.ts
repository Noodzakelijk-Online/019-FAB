export type FabRecord = Record<string, unknown>;
export type FabCommandId =
  | "run_safe_cycle"
  | "rescan_intake"
  | "process_imported"
  | "sync_sources"
  | "run_due_recovery"
  | "run_reconciliation"
  | "refresh_notifications"
  | "run_due_reports"
  | "assess_compliance";

export function asRecord(value: unknown): FabRecord {
  return value && typeof value === "object" && !Array.isArray(value) ? value as FabRecord : {};
}

export function records(value: unknown): FabRecord[] {
  return Array.isArray(value)
    ? value.flatMap((item) => Object.keys(asRecord(item)).length ? [asRecord(item)] : [])
    : [];
}

export function text(value: unknown, fallback = "-"): string {
  if (typeof value === "string" && value.trim()) return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return fallback;
}

export function count(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function bool(value: unknown): boolean {
  return value === true || value === 1 || value === "true" || value === "ready" || value === "ok";
}

export function humanize(value: unknown): string {
  const raw = text(value, "Unknown");
  return raw.replace(/[._-]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function compactHumanize(value: unknown): string {
  const raw = text(value, "Unknown");
  return raw.replace(/[._-]+/g, " ").replace(/^\w/, (letter) => letter.toUpperCase());
}

export function timeAgo(value: unknown): string {
  const raw = text(value, "");
  const timestamp = Date.parse(raw);
  if (!raw || Number.isNaN(timestamp)) return "Not recorded";
  const seconds = Math.round((timestamp - Date.now()) / 1_000);
  const formatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  const ranges: Array<[Intl.RelativeTimeFormatUnit, number]> = [
    ["year", 31_536_000],
    ["month", 2_592_000],
    ["day", 86_400],
    ["hour", 3_600],
    ["minute", 60],
  ];
  for (const [unit, divisor] of ranges) {
    if (Math.abs(seconds) >= divisor) return formatter.format(Math.round(seconds / divisor), unit);
  }
  return formatter.format(seconds, "second");
}

export function statusTone(value: unknown): "good" | "warn" | "bad" | "neutral" | "info" {
  const status = text(value, "").toLowerCase();
  if (["ready", "ok", "healthy", "completed", "connected", "reconciled", "idle"].includes(status)) return "good";
  if (["blocked", "failed", "error", "disconnected", "high", "unavailable"].includes(status)) return "bad";
  if (["attention", "needs_attention", "needs_auth", "needs_review", "medium", "due", "deferred", "prepared_disabled", "not_configured", "supervision_required"].includes(status)) return "warn";
  if (["running", "syncing", "candidate", "pending"].includes(status)) return "info";
  return "neutral";
}

export function matchesSearch(item: FabRecord, search: string): boolean {
  const normalized = search.trim().toLowerCase();
  if (!normalized) return true;
  return JSON.stringify(item).toLowerCase().includes(normalized);
}
