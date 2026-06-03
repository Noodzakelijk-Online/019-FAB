/**
 * Structured logging utility for production-grade observability.
 * Outputs JSON in production for log aggregation tools,
 * and human-readable format in development.
 */

type LogLevel = "debug" | "info" | "warn" | "error";

interface LogEntry {
  level: LogLevel;
  message: string;
  timestamp: string;
  context?: string;
  data?: Record<string, unknown>;
  error?: {
    message: string;
    stack?: string;
    code?: string;
  };
}

const isProduction = process.env.NODE_ENV === "production";

function formatEntry(entry: LogEntry): string {
  if (isProduction) {
    return JSON.stringify(entry);
  }

  // Human-readable format for development
  const prefix = `[${entry.timestamp}] [${entry.level.toUpperCase()}]`;
  const ctx = entry.context ? ` [${entry.context}]` : "";
  let msg = `${prefix}${ctx} ${entry.message}`;

  if (entry.data && Object.keys(entry.data).length > 0) {
    msg += ` ${JSON.stringify(entry.data)}`;
  }

  if (entry.error) {
    msg += `\n  Error: ${entry.error.message}`;
    if (entry.error.stack && !isProduction) {
      msg += `\n  ${entry.error.stack}`;
    }
  }

  return msg;
}

function createEntry(
  level: LogLevel,
  message: string,
  context?: string,
  data?: Record<string, unknown>,
  error?: Error
): LogEntry {
  const entry: LogEntry = {
    level,
    message,
    timestamp: new Date().toISOString(),
  };

  if (context) entry.context = context;
  if (data) entry.data = data;
  if (error) {
    entry.error = {
      message: error.message,
      stack: error.stack,
      code: (error as any).code,
    };
  }

  return entry;
}

/**
 * Create a scoped logger with a fixed context prefix.
 *
 * Usage:
 *   const log = createLogger("Stripe");
 *   log.info("Checkout session created", { sessionId: "cs_xxx" });
 *   log.error("Webhook failed", { eventId: "evt_xxx" }, err);
 */
export function createLogger(context: string) {
  return {
    debug(message: string, data?: Record<string, unknown>) {
      if (isProduction) return; // Skip debug in production
      const entry = createEntry("debug", message, context, data);
      console.debug(formatEntry(entry));
    },

    info(message: string, data?: Record<string, unknown>) {
      const entry = createEntry("info", message, context, data);
      console.log(formatEntry(entry));
    },

    warn(message: string, data?: Record<string, unknown>, error?: Error) {
      const entry = createEntry("warn", message, context, data, error);
      console.warn(formatEntry(entry));
    },

    error(message: string, data?: Record<string, unknown>, error?: Error) {
      const entry = createEntry("error", message, context, data, error);
      console.error(formatEntry(entry));
    },
  };
}

/**
 * Default application logger (no context prefix)
 */
export const log = createLogger("App");
