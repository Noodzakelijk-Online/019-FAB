import { describe, expect, it } from "vitest";
import {
  MAX_BANK_STATEMENT_BYTES,
  inferBankStatementFormat,
  validateBankStatementFile,
} from "../client/src/components/fab/fabBankStatement";

describe("FAB bank statement file policy", () => {
  it("infers only supported text statement formats", () => {
    expect(inferBankStatementFormat("transactions.CSV")).toBe("csv");
    expect(inferBankStatementFormat("transactions.json")).toBe("json");
    expect(inferBankStatementFormat("camt.053.xml")).toBe("camt");
    expect(inferBankStatementFormat("statement.camt")).toBe("camt");
    expect(inferBankStatementFormat("statement.sta")).toBe("mt940");
    expect(inferBankStatementFormat("statement.mt940")).toBe("mt940");
    expect(inferBankStatementFormat("statement.xlsx")).toBeNull();
  });

  it("rejects empty, oversized, and unsupported files before upload", () => {
    expect(validateBankStatementFile({ name: "empty.csv", size: 0 })).toEqual({
      format: "csv",
      error: "empty",
    });
    expect(validateBankStatementFile({
      name: "large.csv",
      size: MAX_BANK_STATEMENT_BYTES + 1,
    })).toEqual({ format: "csv", error: "too_large" });
    expect(validateBankStatementFile({ name: "sheet.xlsx", size: 128 })).toEqual({
      format: null,
      error: "unsupported",
    });
  });
});
