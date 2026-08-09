import { beforeEach, describe, expect, it, vi } from "vitest";
import type { TrpcContext } from "./_core/context";

const gatewayMocks = vi.hoisted(() => ({
  importFabBankStatement: vi.fn(),
}));

vi.mock("./fabLocalGateway", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./fabLocalGateway")>();
  return {
    ...actual,
    importFabBankStatement: gatewayMocks.importFabBankStatement,
  };
});

import { appRouter } from "./routers";

function createOperatorContext(): TrpcContext {
  return {
    user: {
      id: 9,
      openId: "fab-bank-operator",
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

describe("FAB bank statement import", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    gatewayMocks.importFabBankStatement.mockResolvedValue({
      success: true,
      status: "completed",
      rowsImported: 2,
      externalSubmission: "not_executed",
    });
  });

  it("binds the authenticated operator to a validated statement import", async () => {
    const caller = appRouter.createCaller(createOperatorContext());

    const result = await caller.fab.importBankStatement({
      filename: "transactions.csv",
      format: "csv",
      accountIdentifier: "NL00FAB0123456789",
      contentBase64: "YSxiLGM=",
    });

    expect(result).toMatchObject({ success: true, rowsImported: 2 });
    expect(gatewayMocks.importFabBankStatement).toHaveBeenCalledWith({
      filename: "transactions.csv",
      format: "csv",
      accountIdentifier: "NL00FAB0123456789",
      contentBase64: "YSxiLGM=",
      actor: "fab_dashboard:9",
    });
  });

  it("rejects a mismatched extension before calling the ledger API", async () => {
    const caller = appRouter.createCaller(createOperatorContext());

    await expect(caller.fab.importBankStatement({
      filename: "transactions.json",
      format: "csv",
      accountIdentifier: "checking",
      contentBase64: "YSxiLGM=",
    })).rejects.toThrow("File extension does not match csv format");

    expect(gatewayMocks.importFabBankStatement).not.toHaveBeenCalled();
  });
});
