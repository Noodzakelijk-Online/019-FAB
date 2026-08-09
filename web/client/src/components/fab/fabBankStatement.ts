export const MAX_BANK_STATEMENT_BYTES = 4 * 1024 * 1024;

export type FabBankStatementFormat = "csv" | "json" | "camt" | "mt940";
export type FabBankStatementValidation = {
  format: FabBankStatementFormat | null;
  error: "empty" | "too_large" | "unsupported" | null;
};

const FORMAT_BY_EXTENSION: Record<string, FabBankStatementFormat> = {
  camt: "camt",
  csv: "csv",
  json: "json",
  mt940: "mt940",
  sta: "mt940",
  xml: "camt",
};

export function inferBankStatementFormat(filename: string): FabBankStatementFormat | null {
  const extension = filename.trim().toLowerCase().split(".").pop() || "";
  return FORMAT_BY_EXTENSION[extension] || null;
}

export function validateBankStatementFile(file: { name: string; size: number }): FabBankStatementValidation {
  const format = inferBankStatementFormat(file.name);
  if (!format) return { format: null, error: "unsupported" };
  if (file.size <= 0) return { format, error: "empty" };
  if (file.size > MAX_BANK_STATEMENT_BYTES) return { format, error: "too_large" };
  return { format, error: null };
}
