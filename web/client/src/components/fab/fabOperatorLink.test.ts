import { describe, expect, it } from "vitest";
import { fabOperatorLink } from "./fabOperatorLink";

describe("fabOperatorLink", () => {
  it("keeps operator navigation same-origin and encodes the protected target", () => {
    expect(fabOperatorLink("/api/report-runs/12/artifact?format=csv")).toBe(
      "/api/fab/operator-session?next=%2Fapi%2Freport-runs%2F12%2Fartifact%3Fformat%3Dcsv",
    );
  });

  it("falls back to the ledger home for external-looking targets", () => {
    expect(fabOperatorLink("https://evil.example")).toBe("/api/fab/operator-session?next=%2F");
    expect(fabOperatorLink("//evil.example")).toBe("/api/fab/operator-session?next=%2F");
  });
});
