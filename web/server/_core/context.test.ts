import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./sdk", () => ({
  sdk: {
    authenticateRequest: vi.fn(),
  },
}));

import { ENV } from "./env";
import { createContext } from "./context";
import { sdk } from "./sdk";

const authenticateRequest = vi.mocked(sdk.authenticateRequest);
const originalLocalMode = ENV.fabOperatorLocalMode;

function options(remoteAddress: string, hostname: string) {
  return {
    req: { socket: { remoteAddress }, hostname },
    res: {},
    info: {} as never,
  } as never;
}

describe("createContext local operator authentication", () => {
  beforeEach(() => {
    authenticateRequest.mockReset();
    ENV.fabOperatorLocalMode = true;
  });

  afterEach(() => {
    ENV.fabOperatorLocalMode = originalLocalMode;
  });

  it("does not verify irrelevant session cookies for a loopback operator", async () => {
    const context = await createContext(options("127.0.0.1", "127.0.0.1"));

    expect(authenticateRequest).not.toHaveBeenCalled();
    expect(context.user).toBeNull();
  });

  it("still authenticates a non-loopback request", async () => {
    authenticateRequest.mockResolvedValue({ id: 7, role: "admin" } as never);

    const context = await createContext(options("203.0.113.10", "example.test"));

    expect(authenticateRequest).toHaveBeenCalledOnce();
    expect(context.user).toMatchObject({ id: 7, role: "admin" });
  });
});
