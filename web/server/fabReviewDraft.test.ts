import { describe, expect, it } from "vitest";
import {
  clearReviewDraft,
  loadReviewDraft,
  reviewDraftChanged,
  reviewDraftKey,
  saveReviewDraft,
  type FabReviewDraftForm,
  type FabReviewDraftStorage,
} from "../client/src/components/fab/fabReviewDraft";

class MemoryStorage implements FabReviewDraftStorage {
  private readonly values = new Map<string, string>();
  getItem(key: string) { return this.values.get(key) ?? null; }
  setItem(key: string, value: string) { this.values.set(key, value); }
  removeItem(key: string) { this.values.delete(key); }
}

const form: FabReviewDraftForm = {
  vendorName: "Verified Vendor",
  transactionDate: "2026-08-09",
  totalAmount: "118.60",
  vatAmount: "20.58",
  category: "Office Supplies",
  documentType: "vendor_invoice",
  targetSystem: "waveapps_business",
  resolution: "Checked against retained source evidence.",
  learnRule: true,
  applyToMatchingVendor: false,
};

describe("FAB review draft recovery", () => {
  it("round-trips an exact current review draft", () => {
    const storage = new MemoryStorage();
    const now = new Date("2026-08-09T12:00:00Z");
    expect(saveReviewDraft(storage, 12, "review-12:source-v3", form, now)).toBe(true);
    expect(loadReviewDraft(storage, 12, "review-12:source-v3", now)).toEqual(form);
  });

  it("rejects and clears a draft when the source identity changed", () => {
    const storage = new MemoryStorage();
    saveReviewDraft(storage, 12, "review-12:source-v2", form, new Date("2026-08-09T12:00:00Z"));
    expect(loadReviewDraft(storage, 12, "review-12:source-v3", new Date("2026-08-09T12:01:00Z"))).toBeNull();
    expect(storage.getItem(reviewDraftKey(12))).toBeNull();
  });

  it("expires drafts after seven days and rejects future timestamps", () => {
    const storage = new MemoryStorage();
    saveReviewDraft(storage, 12, "identity", form, new Date("2026-08-01T00:00:00Z"));
    expect(loadReviewDraft(storage, 12, "identity", new Date("2026-08-09T00:00:01Z"))).toBeNull();

    saveReviewDraft(storage, 12, "identity", form, new Date("2026-08-09T01:02:00Z"));
    expect(loadReviewDraft(storage, 12, "identity", new Date("2026-08-09T01:00:00Z"))).toBeNull();
  });

  it("fails closed on malformed or oversized values without throwing", () => {
    const storage = new MemoryStorage();
    storage.setItem(reviewDraftKey(12), "not-json");
    expect(loadReviewDraft(storage, 12, "identity")).toBeNull();
    expect(saveReviewDraft(storage, 12, "identity", { ...form, resolution: "x".repeat(4_001) })).toBe(false);
  });

  it("detects edits and supports explicit discard", () => {
    const storage = new MemoryStorage();
    expect(reviewDraftChanged(form, form)).toBe(false);
    expect(reviewDraftChanged({ ...form, category: "Travel" }, form)).toBe(true);
    saveReviewDraft(storage, 12, "identity", form);
    clearReviewDraft(storage, 12);
    expect(storage.getItem(reviewDraftKey(12))).toBeNull();
  });
});
