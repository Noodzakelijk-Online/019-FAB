import { asRecord, records, text, type FabRecord } from "./fabView";

export const reviewTriageFilters = [
  "all",
  "vendor_batches",
  "suggestions",
  "validation",
  "duplicates",
  "supporting",
] as const;

export type FabReviewTriageFilter = typeof reviewTriageFilters[number];
export type FabReviewTriageCounts = Record<FabReviewTriageFilter, number>;
export type FabVendorReviewBatch = {
  key: string;
  vendorName: string;
  targetSystem: string;
  representative: FabRecord;
  items: FabRecord[];
};

const VENDOR_CATEGORY_REASONS = new Set([
  "low_confidence_categorization",
  "manual_review_category",
]);

export function matchesReviewTriage(item: FabRecord, filter: FabReviewTriageFilter): boolean {
  if (filter === "all") return true;
  if (filter === "vendor_batches") return vendorReviewBatchKey(item) !== null;

  const document = asRecord(item.document);
  const reasons = Array.isArray(item.reasons)
    ? item.reasons.filter((reason): reason is string => typeof reason === "string")
    : [];

  if (filter === "suggestions") {
    return Boolean(text(asRecord(document.categorySuggestion).category, ""));
  }

  if (filter === "validation") {
    return reasons.includes("validation_failed") || records(document.financialFieldIssues).length > 0;
  }

  if (filter === "duplicates") {
    return reasons.includes("duplicate") || records(item.duplicateCandidates).length > 0;
  }

  return document.postingEligible === false
    || text(document.category, "").toLowerCase() === "supporting evidence"
    || reasons.includes("non_posting");
}

export function reviewTriageCounts(workItems: FabRecord[]): FabReviewTriageCounts {
  return reviewTriageFilters.reduce<FabReviewTriageCounts>((counts, filter) => {
    counts[filter] = filter === "vendor_batches"
      ? vendorReviewBatches(workItems).length
      : workItems.filter((item) => matchesReviewTriage(item, filter)).length;
    return counts;
  }, {
    all: 0,
    vendor_batches: 0,
    suggestions: 0,
    validation: 0,
    duplicates: 0,
    supporting: 0,
  });
}

export function vendorReviewBatches(workItems: FabRecord[]): FabVendorReviewBatch[] {
  const grouped = new Map<string, FabRecord[]>();
  for (const item of workItems) {
    const key = vendorReviewBatchKey(item);
    if (!key) continue;
    grouped.set(key, [...(grouped.get(key) || []), item]);
  }

  return Array.from(grouped.entries())
    .flatMap(([key, items]) => {
      if (items.length < 2) return [];
      const ranked = [...items].sort(compareBatchRepresentatives);
      if (!batchRepresentativeReady(ranked[0])) return [];
      const document = asRecord(ranked[0].document);
      return [{
        key,
        vendorName: text(document.vendorName),
        targetSystem: text(document.targetSystem, "waveapps_business"),
        representative: ranked[0],
        items: ranked,
      }];
    })
    .sort((left, right) => (
      right.items.length - left.items.length
      || left.vendorName.localeCompare(right.vendorName)
      || left.key.localeCompare(right.key)
    ));
}

function batchRepresentativeReady(item: FabRecord): boolean {
  const document = asRecord(item.document);
  const reasons = Array.isArray(item.reasons)
    ? item.reasons.filter((reason): reason is string => typeof reason === "string")
    : [];
  return Boolean(
    text(document.vendorName, "")
    && text(document.transactionDate, "")
    && document.totalAmount !== null
    && document.totalAmount !== undefined
    && Number.isFinite(Number(document.totalAmount))
    && !reasons.includes("validation_failed")
    && records(document.financialFieldIssues).length === 0
  );
}

function vendorReviewBatchKey(item: FabRecord): string | null {
  const document = asRecord(item.document);
  const reasons = Array.isArray(item.reasons)
    ? item.reasons.filter((reason): reason is string => typeof reason === "string")
    : [];
  const vendorName = normalizeVendorName(text(document.vendorName, ""));
  if (
    !vendorName
    || document.postingEligible === false
    || text(document.processingStatus, "") === "duplicate"
    || Number(document.duplicateOfDocumentId || 0) > 0
    || !reasons.some((reason) => VENDOR_CATEGORY_REASONS.has(reason))
  ) {
    return null;
  }
  return `${text(document.targetSystem, "waveapps_business")}:${vendorName}`;
}

function compareBatchRepresentatives(left: FabRecord, right: FabRecord): number {
  return batchRepresentativeScore(right) - batchRepresentativeScore(left)
    || reviewDocumentId(left) - reviewDocumentId(right)
    || text(left.id).localeCompare(text(right.id));
}

function batchRepresentativeScore(item: FabRecord): number {
  const document = asRecord(item.document);
  const reasons = Array.isArray(item.reasons)
    ? item.reasons.filter((reason): reason is string => typeof reason === "string")
    : [];
  let score = 0;
  if (text(document.vendorName, "")) score += 2;
  if (text(document.transactionDate, "")) score += 4;
  if (document.totalAmount !== null && document.totalAmount !== undefined && Number.isFinite(Number(document.totalAmount))) score += 4;
  if (!reasons.includes("validation_failed") && records(document.financialFieldIssues).length === 0) score += 12;
  if (records(item.duplicateCandidates).length === 0) score += 3;
  if (text(asRecord(document.categorySuggestion).category, "")) score += 1;
  return score;
}

function reviewDocumentId(item: FabRecord): number {
  const document = asRecord(item.document);
  const value = Number(item.documentId || document.id || item.id || Number.MAX_SAFE_INTEGER);
  return Number.isFinite(value) ? value : Number.MAX_SAFE_INTEGER;
}

function normalizeVendorName(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, " ");
}
