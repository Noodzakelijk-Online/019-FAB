import { asRecord, records, text, type FabRecord } from "./fabView";

export const reviewTriageFilters = [
  "all",
  "suggestions",
  "validation",
  "duplicates",
  "supporting",
] as const;

export type FabReviewTriageFilter = typeof reviewTriageFilters[number];
export type FabReviewTriageCounts = Record<FabReviewTriageFilter, number>;

export function matchesReviewTriage(item: FabRecord, filter: FabReviewTriageFilter): boolean {
  if (filter === "all") return true;

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
    counts[filter] = workItems.filter((item) => matchesReviewTriage(item, filter)).length;
    return counts;
  }, {
    all: 0,
    suggestions: 0,
    validation: 0,
    duplicates: 0,
    supporting: 0,
  });
}
