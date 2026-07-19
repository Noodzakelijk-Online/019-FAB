import { describe, expect, it } from "vitest";
import { isLoopbackFabOperatorRequest } from "./_core/trpc";
import type { TrpcContext } from "./_core/context";

function context(hostname: string, remoteAddress: string): TrpcContext {
  return {
    req: {
      hostname,
      socket: { remoteAddress },
    } as TrpcContext["req"],
    res: {} as TrpcContext["res"],
    user: null,
  };
}

describe("FAB loopback operator access", () => {
  it("accepts direct IPv4 and IPv6 loopback requests", () => {
    expect(isLoopbackFabOperatorRequest(context("127.0.0.1", "::ffff:127.0.0.1"))).toBe(true);
    expect(isLoopbackFabOperatorRequest(context("localhost", "::1"))).toBe(true);
  });

  it("rejects remote addresses and non-loopback host headers", () => {
    expect(isLoopbackFabOperatorRequest(context("127.0.0.1", "10.10.0.8"))).toBe(false);
    expect(isLoopbackFabOperatorRequest(context("fab.example.com", "::1"))).toBe(false);
  });
});
