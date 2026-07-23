import { describe, expect, it } from "vitest";
import { reviewApprovalBlockers } from "../client/src/components/fab/fabReviewApproval";

const today = new Date("2026-07-23T00:00:00Z");
const validInput = {
  vendorName: "Action",
  transactionDate: "2023-06-12",
  totalAmount: "13.98",
  vatAmount: "",
  category: "Office Supplies",
  resolution: "Verified against source evidence.",
};

describe("FAB review approval readiness", () => {
  it("allows a complete posting decision", () => {
    expect(
      reviewApprovalBlockers(validInput, { nonPosting: false, today })
    ).toEqual([]);
  });

  it("blocks missing required bookkeeping fields before submission", () => {
    expect(
      reviewApprovalBlockers(
        {
          ...validInput,
          transactionDate: "",
          category: "",
        },
        { nonPosting: false, today }
      )
    ).toEqual(["transactionDate", "category"]);
  });

  it("blocks impossible dates and non-positive totals", () => {
    expect(
      reviewApprovalBlockers(
        {
          ...validInput,
          transactionDate: "3038-06-10",
          totalAmount: "0",
        },
        { nonPosting: false, today }
      )
    ).toEqual(["transactionDate", "totalAmount"]);
  });

  it("blocks malformed optional VAT when a value is entered", () => {
    expect(
      reviewApprovalBlockers(
        {
          ...validInput,
          vatAmount: "not-a-number",
        },
        { nonPosting: false, today }
      )
    ).toEqual(["vatAmount"]);
  });

  it("requires only a decision note for non-posting evidence", () => {
    expect(
      reviewApprovalBlockers(
        {
          ...validInput,
          vendorName: "",
          transactionDate: "",
          totalAmount: "",
          category: "",
          resolution: "",
        },
        { nonPosting: true, today }
      )
    ).toEqual(["resolution"]);
  });
});
