import { describe, expect, it } from "vitest";
import {
  matchesReviewTriage,
  reviewTriageCounts,
} from "../client/src/components/fab/fabReviewTriage";

describe("FAB review triage", () => {
  const workItems = [
    {
      id: 1,
      reasons: ["low_confidence", "manual_category"],
      document: {
        postingEligible: true,
        categorySuggestion: { category: "Construction Materials & Tools" },
      },
    },
    {
      id: 2,
      reasons: ["validation_failed"],
      document: {
        postingEligible: true,
        financialFieldIssues: [{ field: "recordDate" }],
      },
    },
    {
      id: 3,
      reasons: ["duplicate", "validation_failed"],
      duplicateCandidates: [{ documentId: 30 }],
      document: {
        postingEligible: true,
      },
    },
    {
      id: 4,
      reasons: ["non_posting"],
      document: {
        postingEligible: false,
        category: "Supporting Evidence",
      },
    },
  ];

  it("counts overlapping accounting work modes without hiding documents", () => {
    expect(reviewTriageCounts(workItems)).toEqual({
      all: 4,
      suggestions: 1,
      validation: 2,
      duplicates: 1,
      supporting: 1,
    });
  });

  it("recognizes retained financial field issues as validation work", () => {
    expect(matchesReviewTriage({
      document: { financialFieldIssues: [{ field: "vatAmount" }] },
    }, "validation")).toBe(true);
  });

  it("recognizes candidate evidence as duplicate work", () => {
    expect(matchesReviewTriage({
      duplicateCandidates: [{ documentId: 99 }],
      document: {},
    }, "duplicates")).toBe(true);
  });

  it("does not treat an empty category suggestion as actionable", () => {
    expect(matchesReviewTriage({
      document: { categorySuggestion: { category: "" } },
    }, "suggestions")).toBe(false);
  });

  it("keeps non-posting evidence in the supporting mode", () => {
    expect(matchesReviewTriage({
      document: { postingEligible: false },
    }, "supporting")).toBe(true);
  });
});
