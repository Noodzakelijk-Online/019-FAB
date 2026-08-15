import { afterEach, describe, expect, it, vi } from "vitest";
import { createLogger } from "./logger";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("structured logger secret handling", () => {
  it("redacts secrets from data and Error fields before writing", () => {
    const output = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const error = Object.assign(
      new Error("Wave failed: access_token=message-secret Authorization: Bearer bearer-secret"),
      {
        code: "ERR_WAVE",
        response: { data: { refresh_token: "body-secret" } },
      },
    );

    createLogger("Wave").error("Provider request failed", {
      requestId: "req-123",
      authorization: "Bearer data-secret",
      endpoint: "https://api.wave.test/graphql?api_key=query-secret",
    }, error);

    const serialized = output.mock.calls.flat().join(" ");
    expect(serialized).toContain("req-123");
    expect(serialized).toContain("[REDACTED]");
    for (const secret of ["message-secret", "bearer-secret", "body-secret", "data-secret", "query-secret"]) {
      expect(serialized).not.toContain(secret);
    }
  });
});
