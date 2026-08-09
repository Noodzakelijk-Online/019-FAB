import {
  ArrowRight,
  Building2,
  CheckCircle2,
  Cloud,
  FileCheck2,
  Mail,
  MonitorUp,
  ShieldCheck,
} from "lucide-react";
import { fabActivationState, type FabActivationStepId } from "./fabActivation";
import { useFabLocale } from "./fabLocale";
import { text, type FabRecord } from "./fabView";

type FabActivationChecklistProps = {
  waveSetup: FabRecord;
  gmailAuthorization: FabRecord;
  driveAuthorization: FabRecord;
  waveReceiptExecutor: FabRecord;
  reviewSummary: FabRecord;
  onOpenWave: () => void;
  onOpenGmail: () => void;
  onOpenDrive: () => void;
  onOpenReceiptExecutor: () => void;
  onOpenReviews: () => void;
};

export function FabActivationChecklist({
  waveSetup,
  gmailAuthorization,
  driveAuthorization,
  waveReceiptExecutor,
  reviewSummary,
  onOpenWave,
  onOpenGmail,
  onOpenDrive,
  onOpenReceiptExecutor,
  onOpenReviews,
}: FabActivationChecklistProps) {
  const { copy, status: localizedStatus } = useFabLocale();
  const activation = fabActivationState({
    waveSetup,
    gmailAuthorization,
    driveAuthorization,
    waveReceiptExecutor,
    reviewSummary,
  });
  const stepState = new Map(activation.steps.map((step) => [step.id, step]));
  const stepSpecs: Array<{
    id: FabActivationStepId;
    icon: typeof Building2;
    title: string;
    status: string;
    actionLabel: string;
    onAction: () => void;
  }> = [
    {
      id: "google_drive",
      icon: Cloud,
      title: "Google Drive",
      status: localizedStatus(text(driveAuthorization.status, "credentials_required")),
      actionLabel: stepState.get("google_drive")?.reauthorizationRequired
        ? copy("Reauthorize Drive", "Drive opnieuw autoriseren")
        : copy("Authorize Drive", "Drive autoriseren"),
      onAction: onOpenDrive,
    },
    {
      id: "gmail",
      icon: Mail,
      title: "Gmail scanner",
      status: localizedStatus(text(gmailAuthorization.status, "credentials_required")),
      actionLabel: stepState.get("gmail")?.reauthorizationRequired
        ? copy("Reauthorize Gmail", "Gmail opnieuw autoriseren")
        : copy("Authorize Gmail", "Gmail autoriseren"),
      onAction: onOpenGmail,
    },
    {
      id: "wave",
      icon: Building2,
      title: "Wave - Noodzakelijk Online",
      status: localizedStatus(text(waveSetup.status, "needs_token")),
      actionLabel: copy("Connect Wave", "Wave koppelen"),
      onAction: onOpenWave,
    },
    {
      id: "wave_receipt_executor",
      icon: MonitorUp,
      title: copy("Wave receipt session", "Wave-bewijssessie"),
      status: localizedStatus(text(waveReceiptExecutor.status, "not_connected")),
      actionLabel: copy("Review executor", "Executor bekijken"),
      onAction: onOpenReceiptExecutor,
    },
    {
      id: "reviews",
      icon: FileCheck2,
      title: copy("Document decisions", "Documentbeslissingen"),
      status: activation.reviewCountKnown
        ? activation.postingBlockedDocuments === 0
          ? activation.evidenceOnlyDocuments > 0
            ? `${copy("Posting queue clear", "Boekingswachtrij leeg")}; ${activation.evidenceOnlyDocuments} ${copy(activation.evidenceOnlyDocuments === 1 ? "evidence review retained" : "evidence reviews retained", activation.evidenceOnlyDocuments === 1 ? "bewijscontrole behouden" : "bewijscontroles behouden")}`
            : copy("Posting review queue clear", "Boekingscontrolewachtrij leeg")
          : `${activation.postingBlockedDocuments} ${copy(activation.postingBlockedDocuments === 1 ? "posting document blocked" : "posting documents blocked", activation.postingBlockedDocuments === 1 ? "boekingsdocument geblokkeerd" : "boekingsdocumenten geblokkeerd")}`
        : copy("Review status unavailable", "Controlestatus niet beschikbaar"),
      actionLabel: copy("Open review queue", "Controlewachtrij openen"),
      onAction: onOpenReviews,
    },
  ];
  const currentStep = stepSpecs.find((step) => step.id === activation.currentStepId) || null;
  const progress = `${Math.round((activation.completedSteps / activation.totalSteps) * 100)}%`;

  if (activation.complete) return null;

  return (
    <section className="fab-activation-checklist" aria-labelledby="fab-activation-title">
      <div className="fab-activation-heading">
        <div className="fab-activation-heading-main">
          <div><span>{copy("Required before autonomous delivery", "Vereist voor autonome verwerking")}</span><h2 id="fab-activation-title">{copy("Finish activation", "Activering voltooien")}</h2></div>
          <div className="fab-activation-progress" aria-label={copy(`${activation.completedSteps} of ${activation.totalSteps} activation steps ready`, `${activation.completedSteps} van ${activation.totalSteps} activeringsstappen gereed`)}>
            <span><i style={{ width: progress }} /></span>
            <small>{activation.completedSteps}/{activation.totalSteps} {copy("ready", "gereed")}</small>
          </div>
        </div>
        <div className="fab-activation-heading-actions">
          <span className="fab-status-chip tone-warn">{copy("External delivery paused", "Externe verwerking gepauzeerd")}</span>
          {currentStep && <button className="fab-primary-button compact" type="button" onClick={currentStep.onAction}>{currentStep.actionLabel} <ArrowRight aria-hidden="true" /></button>}
        </div>
      </div>
      <div className="fab-activation-steps">
        {stepSpecs.map((step, index) => <ActivationStep
          key={step.id}
          icon={step.icon}
          complete={stepState.get(step.id)?.complete === true}
          current={activation.currentStepId === step.id}
          stepNumber={index + 1}
          title={step.title}
          status={step.status}
          actionLabel={step.actionLabel}
          onAction={step.onAction}
        />)}
      </div>
      <div className="fab-activation-safety"><ShieldCheck aria-hidden="true" /><span>{copy("Source files remain retained until Wave transaction and exact attachment readback evidence pass every archive gate.", "Bronbestanden blijven behouden totdat de Wave-transactie en de exacte teruggelezen bijlage alle archiefcontroles doorstaan.")}</span></div>
    </section>
  );
}

type ActivationStepProps = {
  icon: typeof Building2;
  complete: boolean;
  current: boolean;
  stepNumber: number;
  title: string;
  status: string;
  actionLabel: string;
  onAction: () => void;
};

function ActivationStep({ icon: Icon, complete, current, stepNumber, title, status, actionLabel, onAction }: ActivationStepProps) {
  const { copy } = useFabLocale();
  return (
    <div className={`fab-activation-step ${complete ? "is-complete" : ""} ${current ? "is-current" : ""}`} aria-current={current ? "step" : undefined}>
      <span className={`fab-activation-icon tone-${complete ? "good" : current ? "warn" : "neutral"}`}>{complete ? <CheckCircle2 aria-hidden="true" /> : current ? <Icon aria-hidden="true" /> : stepNumber}</span>
      <div><strong>{title}</strong><span>{status}</span></div>
      {complete
        ? <span className="fab-status-chip tone-good">{copy("Ready", "Gereed")}</span>
        : <button className={`fab-secondary-button compact${current ? " is-current" : ""}`} type="button" onClick={onAction}>{current ? copy("Continue", "Doorgaan") : actionLabel}</button>}
    </div>
  );
}
