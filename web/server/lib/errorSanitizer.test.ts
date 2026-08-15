import { describe, expect, it } from "vitest";
import {
  sanitizeDiagnosticValue,
  sanitizeExternalError,
  sanitizeExternalMessage,
} from "./errorSanitizer";

describe("external error sanitization", () => {
  it("redacts credentials from provider messages and bounds their size", () => {
    const message = [
      "POST https://api.example.test/callback?access_token=oauth-secret&safe=visible",
      "Authorization: Bearer bearer-secret",
      "Cookie: session=session-secret; theme=dark",
      "DATABASE_URL=postgres://operator:database-secret@localhost/fab",
      "client_secret=client-secret",
      "x".repeat(1_000),
    ].join(" ");

    const sanitized = sanitizeExternalMessage(message);

    expect(sanitized).toContain("safe=visible");
    expect(sanitized).toContain("[REDACTED]");
    expect(sanitized.length).toBeLessThanOrEqual(500);
    for (const secret of ["oauth-secret", "bearer-secret", "session-secret", "database-secret", "client-secret"]) {
      expect(sanitized).not.toContain(secret);
    }
  });

  it("reduces Axios-like failures to a bounded non-secret record", () => {
    const error = Object.assign(new Error(
      "Request failed at https://api.example.test/resource?api_key=query-secret",
    ), {
      name: "AxiosError",
      code: "ERR_BAD_RESPONSE",
      config: {
        url: "https://api.example.test/resource?refresh_token=refresh-secret",
        headers: {
          Authorization: "Bearer header-secret",
          Cookie: "session=cookie-secret",
        },
      },
      response: {
        status: 502,
        data: { access_token: "response-secret", detail: "provider detail" },
      },
      request: { rawHeaders: ["Authorization", "Bearer raw-secret"] },
    });

    const sanitized = sanitizeExternalError(error);
    const serialized = JSON.stringify(sanitized);

    expect(sanitized).toMatchObject({
      name: "AxiosError",
      code: "ERR_BAD_RESPONSE",
      status: 502,
    });
    expect(sanitized.message).toContain("[REDACTED]");
    expect(serialized).not.toContain("config");
    expect(serialized).not.toContain("request");
    expect(serialized).not.toContain("response-secret");
    expect(serialized).not.toContain("refresh-secret");
    expect(serialized).not.toContain("header-secret");
    expect(serialized).not.toContain("cookie-secret");
    expect(serialized).not.toContain("raw-secret");
  });

  it("redacts sensitive nested keys without retaining deep or cyclic objects", () => {
    const value: Record<string, unknown> = {
      requestId: "req-123",
      headers: { authorization: "Bearer nested-secret", accept: "application/json" },
      payload: { clientSecret: "client-secret", status: "failed" },
      list: [{ apiKey: "key-secret", id: 7 }],
    };
    value.self = value;

    const sanitized = sanitizeDiagnosticValue(value);
    const serialized = JSON.stringify(sanitized);

    expect(serialized).toContain("req-123");
    expect(serialized).toContain("failed");
    expect(serialized).toContain("[REDACTED]");
    expect(serialized).not.toContain("nested-secret");
    expect(serialized).not.toContain("client-secret");
    expect(serialized).not.toContain("key-secret");
    expect(serialized).not.toContain("self");
  });

  it("never lets hostile provider objects break diagnostics", () => {
    const hostile = new Proxy({}, {
      ownKeys() {
        throw new Error("provider proxy rejected inspection");
      },
    });

    expect(() => sanitizeDiagnosticValue(hostile)).not.toThrow();
  });
});
