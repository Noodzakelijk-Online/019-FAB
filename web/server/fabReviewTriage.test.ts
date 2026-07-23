import { describe, expect, it } from "vitest";
import {
  matchesReviewTriage,
  reviewTriageCounts,
  vendorReviewBatches,
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
      vendor_batches: 0,
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

  it("collapses exact-vendor category work into ranked batches", () => {
    const batches = vendorReviewBatches([
      {
        id: "review-12",
        documentId: 12,
        reasons: ["manual_review_category", "validation_failed"],
        duplicateCandidates: [{ id: 8 }],
        document: {
          vendorName: " Praxis B.V. ",
          targetSystem: "waveapps_business",
          postingEligible: true,
          totalAmount: 12.5,
        },
      },
      {
        id: "review-7",
        documentId: 7,
        reasons: ["low_confidence_categorization"],
        document: {
          vendorName: "praxis b.v.",
          targetSystem: "waveapps_business",
          postingEligible: true,
          transactionDate: "2026-07-23",
          totalAmount: 42.5,
        },
      },
      {
        id: "review-15",
        documentId: 15,
        reasons: ["manual_review_category"],
        document: {
          vendorName: "Other Vendor",
          targetSystem: "waveapps_business",
          postingEligible: true,
        },
      },
      {
        id: "review-18",
        documentId: 18,
        reasons: ["manual_review_category"],
        document: {
          vendorName: "Praxis B.V.",
          targetSystem: "waveapps_business",
          postingEligible: true,
          processingStatus: "duplicate",
        },
      },
      {
        id: "review-20",
        documentId: 20,
        reasons: ["manual_review_category", "validation_failed"],
        document: {
          vendorName: "Unreadable Vendor",
          targetSystem: "waveapps_business",
          postingEligible: true,
        },
      },
      {
        id: "review-21",
        documentId: 21,
        reasons: ["low_confidence_categorization", "validation_failed"],
        document: {
          vendorName: " unreadable vendor ",
          targetSystem: "waveapps_business",
          postingEligible: true,
          financialFieldIssues: [{ field: "transactionDate" }],
        },
      },
    ]);

    expect(batches).toHaveLength(1);
    expect(batches[0].vendorName).toBe("praxis b.v.");
    expect(batches[0].items).toHaveLength(2);
    expect(batches[0].representative.id).toBe("review-7");
    expect(reviewTriageCounts(batches[0].items).vendor_batches).toBe(1);
  });
});
