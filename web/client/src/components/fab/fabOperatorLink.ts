export function fabOperatorLink(target: string): string {
  const safeTarget = target.startsWith("/") && !target.startsWith("//")
    ? target
    : "/";
  return `/api/fab/operator-session?next=${encodeURIComponent(safeTarget)}`;
}
