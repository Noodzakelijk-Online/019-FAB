const REDACTED = "[REDACTED]";
const DEFAULT_MESSAGE_LIMIT = 500;
const DEFAULT_STACK_LIMIT = 2_000;
const MAX_COLLECTION_ITEMS = 50;
const MAX_DEPTH = 4;

const SENSITIVE_KEY = /^(?:authorization|proxy[-_]?authorization|cookie|set[-_]?cookie|access[-_]?token|refresh[-_]?token|id[-_]?token|client[-_]?secret|api[-_]?key|apikey|secret|password|passwd|token|database[-_]?url|connection[-_]?string|dsn)$/i;
const CREDENTIAL_ASSIGNMENT = /(\b(?:access[_-]?token|refresh[_-]?token|id[_-]?token|client[_-]?secret|api[_-]?key|apikey|secret|password|passwd|token|database[_-]?url|connection[_-]?string|dsn)\b\s*[=:]\s*)(?:"[^"]*"|'[^']*'|[^&\s,;]+)/gi;
const JSON_CREDENTIAL = /(["'](?:access[_-]?token|refresh[_-]?token|id[_-]?token|client[_-]?secret|api[_-]?key|apikey|secret|password|passwd|token|database[_-]?url|connection[_-]?string|dsn)["']\s*:\s*)(?:"[^"]*"|'[^']*'|[^,}\s]+)/gi;
const AUTH_SCHEME = /\b(Bearer|Basic)\s+[^\s,;"']+/gi;
const AUTH_HEADER = /\b(authorization|proxy-authorization)\s*[:=]\s*(?:Bearer|Basic)?\s*[^\s,;"']+/gi;
const COOKIE_HEADER = /\b(set-cookie|cookie)\s*:\s*[^\r\n,]+/gi;
const URL_USERINFO = /([a-z][a-z0-9+.-]*:\/\/)[^/@\s]+@/gi;
const REQUEST_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;

export type SanitizedExternalError = {
  name: string;
  message: string;
  code?: string;
  status?: number;
  requestId?: string;
  stack?: string;
};

function bounded(value: string, maxLength: number): string {
  if (value.length <= maxLength) return value;
  return value.slice(0, Math.max(0, maxLength - 3)) + "...";
}

export function sanitizeExternalMessage(
  value: unknown,
  maxLength = DEFAULT_MESSAGE_LIMIT,
  fallback = "External request failed",
): string {
  let message: string;
  try {
    message = typeof value === "string" ? value : String(value ?? "");
  } catch {
    message = fallback;
  }
  const sanitized = message
    .replace(URL_USERINFO, `$1${REDACTED}@`)
    .replace(JSON_CREDENTIAL, `$1"${REDACTED}"`)
    .replace(CREDENTIAL_ASSIGNMENT, `$1${REDACTED}`)
    .replace(AUTH_HEADER, `$1: ${REDACTED}`)
    .replace(AUTH_SCHEME, `$1 ${REDACTED}`)
    .replace(COOKIE_HEADER, `$1: ${REDACTED}`)
    .trim();
  return bounded(sanitized || fallback, Math.max(1, maxLength));
}

function ownPrimitive(value: object, key: PropertyKey): string | number | undefined {
  try {
    const descriptor = Object.getOwnPropertyDescriptor(value, key);
    const candidate = descriptor && "value" in descriptor ? descriptor.value : undefined;
    return typeof candidate === "string" || typeof candidate === "number" ? candidate : undefined;
  } catch {
    return undefined;
  }
}

function nestedStatus(value: object): number | undefined {
  const direct = ownPrimitive(value, "status");
  if (typeof direct === "number" && Number.isFinite(direct)) return direct;
  try {
    const descriptor = Object.getOwnPropertyDescriptor(value, "response");
    const response = descriptor && "value" in descriptor ? descriptor.value : undefined;
    if (!response || typeof response !== "object") return undefined;
    const status = ownPrimitive(response, "status");
    return typeof status === "number" && Number.isFinite(status) ? status : undefined;
  } catch {
    return undefined;
  }
}

export function sanitizeExternalError(
  error: unknown,
  options: { includeStack?: boolean; fallback?: string } = {},
): SanitizedExternalError {
  const objectError = error && typeof error === "object" ? error : null;
  const rawName = objectError ? ownPrimitive(objectError, "name") : undefined;
  const rawMessage = objectError ? ownPrimitive(objectError, "message") : error;
  const rawCode = objectError ? ownPrimitive(objectError, "code") : undefined;
  const rawRequestId = objectError
    ? ownPrimitive(objectError, "requestId") ?? ownPrimitive(objectError, "request_id")
    : undefined;
  const result: SanitizedExternalError = {
    name: bounded(sanitizeExternalMessage(rawName || "Error", 80, "Error"), 80),
    message: sanitizeExternalMessage(rawMessage, DEFAULT_MESSAGE_LIMIT, options.fallback),
  };
  if (typeof rawCode === "string" || typeof rawCode === "number") {
    result.code = sanitizeExternalMessage(rawCode, 80, "unknown");
  }
  const status = objectError ? nestedStatus(objectError) : undefined;
  if (status !== undefined) result.status = status;
  if (typeof rawRequestId === "string" && REQUEST_ID_PATTERN.test(rawRequestId)) {
    result.requestId = rawRequestId;
  }
  if (options.includeStack && objectError) {
    const stack = ownPrimitive(objectError, "stack");
    if (typeof stack === "string") {
      result.stack = sanitizeExternalMessage(stack, DEFAULT_STACK_LIMIT, result.message);
    }
  }
  return result;
}

const OMIT = Symbol("omit");

function sanitizeValue(
  value: unknown,
  depth: number,
  seen: WeakSet<object>,
): unknown | typeof OMIT {
  if (value === null || typeof value === "boolean") return value;
  if (typeof value === "number") return Number.isFinite(value) ? value : String(value);
  if (typeof value === "bigint") return value.toString();
  if (typeof value === "string") return sanitizeExternalMessage(value);
  if (typeof value === "undefined" || typeof value === "function" || typeof value === "symbol") return OMIT;
  if (value instanceof Error) return sanitizeExternalError(value);
  if (typeof value !== "object" || depth >= MAX_DEPTH || seen.has(value)) return OMIT;

  seen.add(value);
  if (Array.isArray(value)) {
    const output: unknown[] = [];
    for (const item of value.slice(0, MAX_COLLECTION_ITEMS)) {
      const sanitized = sanitizeValue(item, depth + 1, seen);
      if (sanitized !== OMIT) output.push(sanitized);
    }
    return output;
  }

  const output: Record<string, unknown> = {};
  for (const key of Object.keys(value).slice(0, MAX_COLLECTION_ITEMS)) {
    if (SENSITIVE_KEY.test(key)) {
      output[key] = REDACTED;
      continue;
    }
    let descriptor: PropertyDescriptor | undefined;
    try {
      descriptor = Object.getOwnPropertyDescriptor(value, key);
    } catch {
      continue;
    }
    if (!descriptor || !("value" in descriptor)) continue;
    const sanitized = sanitizeValue(descriptor.value, depth + 1, seen);
    if (sanitized !== OMIT) output[key] = sanitized;
  }
  return output;
}

export function sanitizeDiagnosticValue(value: unknown): unknown {
  try {
    const sanitized = sanitizeValue(value, 0, new WeakSet<object>());
    return sanitized === OMIT ? undefined : sanitized;
  } catch {
    return undefined;
  }
}
