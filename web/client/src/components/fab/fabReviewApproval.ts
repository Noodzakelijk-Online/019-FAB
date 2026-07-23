export type FabReviewApprovalBlocker =
  | "vendorName"
  | "transactionDate"
  | "totalAmount"
  | "vatAmount"
  | "category"
  | "resolution";

export type FabReviewApprovalInput = {
  vendorName: string;
  transactionDate: string;
  totalAmount: string;
  vatAmount: string;
  category: string;
  resolution: string;
};

export function reviewApprovalBlockers(
  input: FabReviewApprovalInput,
  options: { nonPosting: boolean; today?: Date }
): FabReviewApprovalBlocker[] {
  const blockers: FabReviewApprovalBlocker[] = [];
  if (input.resolution.trim().length < 3) blockers.push("resolution");
  if (options.nonPosting) return blockers;

  if (!input.vendorName.trim()) blockers.push("vendorName");
  if (!plausibleTransactionDate(input.transactionDate, options.today)) {
    blockers.push("transactionDate");
  }

  const totalAmount = parseDecimal(input.totalAmount);
  if (totalAmount === undefined || totalAmount <= 0)
    blockers.push("totalAmount");

  if (input.vatAmount.trim()) {
    const vatAmount = parseDecimal(input.vatAmount);
    if (vatAmount === undefined || vatAmount < 0) blockers.push("vatAmount");
  }

  if (!input.category.trim()) blockers.push("category");
  return blockers;
}

export function normalizedReviewEvidenceAmount(
  value: unknown,
  documentType: string
): string {
  if (value === null || value === undefined || value === "") return "";
  const raw = String(value).trim();
  const parsed = parseDecimal(raw);
  if (documentType === "credit_note" && parsed !== undefined) {
    return String(Math.abs(parsed));
  }
  return raw;
}

function plausibleTransactionDate(value: string, today = new Date()): boolean {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value.trim());
  if (!match) return false;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const parsed = new Date(Date.UTC(year, month - 1, day));
  return (
    parsed.getUTCFullYear() === year &&
    parsed.getUTCMonth() === month - 1 &&
    parsed.getUTCDate() === day &&
    year >= 1900 &&
    year <= today.getUTCFullYear() + 1
  );
}

function parseDecimal(value: string): number | undefined {
  const parsed = Number(value.trim().replace(",", "."));
  return Number.isFinite(parsed) ? parsed : undefined;
}
