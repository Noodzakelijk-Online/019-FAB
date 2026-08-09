import { bool, count, type FabRecord } from "./fabView";

export type FabActivationStepId = "google_drive" | "gmail" | "wave" | "wave_receipt_executor" | "reviews";

export type FabActivationStepState = {
  id: FabActivationStepId;
  complete: boolean;
  reauthorizationRequired?: boolean;
};

export type FabActivationState = {
  complete: boolean;
  completedSteps: number;
  totalSteps: number;
  currentStepId: FabActivationStepId | null;
  steps: FabActivationStepState[];
  postingBlockedDocuments: number;
  evidenceOnlyDocuments: number;
  reviewCountKnown: boolean;
};

export function fabActivationState(input: {
  waveSetup: FabRecord;
  gmailAuthorization: FabRecord;
  driveAuthorization: FabRecord;
  waveReceiptExecutor: FabRecord;
  reviewSummary: FabRecord;
}): FabActivationState {
  const gmailReauthorizationRequired = bool(input.gmailAuthorization.reauthorizationRequired);
  const driveReauthorizationRequired = bool(input.driveAuthorization.reauthorizationRequired);
  const reviewCountSource = input.reviewSummary.postingBlockedDocuments ?? input.reviewSummary.documents;
  const reviewCountKnown = reviewCountSource !== null && reviewCountSource !== undefined;
  const postingBlockedDocuments = count(reviewCountSource);
  const evidenceOnlyDocuments = count(input.reviewSummary.evidenceOnlyDocuments);

  const steps: FabActivationStepState[] = [
    {
      id: "google_drive",
      complete: bool(input.driveAuthorization.credentialsPresent)
        && bool(input.driveAuthorization.tokenPresent)
        && bool(input.driveAuthorization.folderConfigured)
        && !driveReauthorizationRequired,
      reauthorizationRequired: driveReauthorizationRequired,
    },
    {
      id: "gmail",
      complete: bool(input.gmailAuthorization.scannerPolicyReady)
        && bool(input.gmailAuthorization.credentialsPresent)
        && bool(input.gmailAuthorization.tokenPresent)
        && !gmailReauthorizationRequired,
      reauthorizationRequired: gmailReauthorizationRequired,
    },
    { id: "wave", complete: bool(input.waveSetup.ready) },
    { id: "wave_receipt_executor", complete: bool(input.waveReceiptExecutor.ready) },
    { id: "reviews", complete: reviewCountKnown && postingBlockedDocuments === 0 },
  ];
  const completedSteps = steps.filter((step) => step.complete).length;

  return {
    complete: completedSteps === steps.length,
    completedSteps,
    totalSteps: steps.length,
    currentStepId: steps.find((step) => !step.complete)?.id ?? null,
    steps,
    postingBlockedDocuments,
    evidenceOnlyDocuments,
    reviewCountKnown,
  };
}
