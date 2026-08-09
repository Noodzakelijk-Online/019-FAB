import { describe, expect, it } from "vitest";
import { fabActivationState } from "../client/src/components/fab/fabActivation";

describe("FAB activation flow", () => {
  const readyInput = {
    waveSetup: { ready: true },
    gmailAuthorization: {
      scannerPolicyReady: true,
      credentialsPresent: true,
      tokenPresent: true,
    },
    driveAuthorization: {
      credentialsPresent: true,
      tokenPresent: true,
      folderConfigured: true,
    },
    waveReceiptExecutor: { ready: true },
    reviewSummary: { postingBlockedDocuments: 0, evidenceOnlyDocuments: 3 },
  };

  it("advances through the dependency-ordered next incomplete step", () => {
    const driveFirst = fabActivationState({
      ...readyInput,
      driveAuthorization: { credentialsPresent: true, tokenPresent: false, folderConfigured: true },
      gmailAuthorization: { credentialsPresent: false, tokenPresent: false, scannerPolicyReady: false },
      waveSetup: { ready: false },
    });
    expect(driveFirst.currentStepId).toBe("google_drive");

    const gmailNext = fabActivationState({
      ...readyInput,
      gmailAuthorization: { credentialsPresent: true, tokenPresent: false, scannerPolicyReady: true },
      waveSetup: { ready: false },
    });
    expect(gmailNext.currentStepId).toBe("gmail");
  });

  it("treats reauthorization as incomplete even when old tokens remain", () => {
    const state = fabActivationState({
      ...readyInput,
      driveAuthorization: { ...readyInput.driveAuthorization, reauthorizationRequired: true },
    });
    expect(state.steps.find((step) => step.id === "google_drive")?.complete).toBe(false);
    expect(state.currentStepId).toBe("google_drive");
  });

  it("does not declare the review gate ready when its count is unavailable", () => {
    const state = fabActivationState({ ...readyInput, reviewSummary: {} });
    expect(state.reviewCountKnown).toBe(false);
    expect(state.currentStepId).toBe("reviews");
    expect(state.complete).toBe(false);
  });

  it("keeps evidence-only reviews outside the posting blocker count", () => {
    const state = fabActivationState(readyInput);
    expect(state.complete).toBe(true);
    expect(state.evidenceOnlyDocuments).toBe(3);
    expect(state.completedSteps).toBe(state.totalSteps);
  });
});
