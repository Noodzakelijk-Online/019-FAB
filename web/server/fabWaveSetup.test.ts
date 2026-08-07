import { beforeEach, describe, expect, it, vi } from "vitest";
import type { TrpcContext } from "./_core/context";

const gatewayMocks = vi.hoisted(() => ({
  saveFabWaveSetup: vi.fn(),
}));

vi.mock("./fabLocalGateway", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./fabLocalGateway")>();
  return {
    ...actual,
    saveFabWaveSetup: gatewayMocks.saveFabWaveSetup,
  };
});

import { appRouter } from "./routers";

function createOperatorContext(): TrpcContext {
  return {
    user: {
      id: 1,
      openId: "fab-operator",
      email: "operator@example.com",
      name: "FAB Operator",
      loginMethod: "local",
      role: "admin",
      createdAt: new Date(),
      updatedAt: new Date(),
      lastSignedIn: new Date(),
      stripeCustomerId: null,
    },
    req: { protocol: "https", headers: {} } as TrpcContext["req"],
    res: { clearCookie: vi.fn() } as unknown as TrpcContext["res"],
  };
}

describe("FAB Wave setup", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    gatewayMocks.saveFabWaveSetup.mockResolvedValue({ success: true, status: "ready" });
  });

  it("accepts an intentionally empty optional fallback account", async () => {
    const caller = appRouter.createCaller(createOperatorContext());

    await caller.fab.saveWaveSetup({
      targetSystem: "waveapps_business",
      anchorAccountId: "anchor-account",
      defaultCategoryAccountId: "",
      categoryAccountIds: {
        Telecommunications: "phone-expense-account",
      },
    });

    expect(gatewayMocks.saveFabWaveSetup).toHaveBeenCalledWith({
      targetSystem: "waveapps_business",
      anchorAccountId: "anchor-account",
      defaultCategoryAccountId: "",
      categoryAccountIds: {
        Telecommunications: "phone-expense-account",
      },
      actor: "fab_dashboard:1",
    });
  });
});
