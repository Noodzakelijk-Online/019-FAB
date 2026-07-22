import {
  Building2,
  CheckCircle2,
  Cloud,
  FileCheck2,
  Mail,
  ShieldCheck,
} from "lucide-react";
import { useFabLocale } from "./fabLocale";
import { bool, count, text, type FabRecord } from "./fabView";

type FabActivationChecklistProps = {
  waveSetup: FabRecord;
  gmailAuthorization: FabRecord;
  driveAuthorization: FabRecord;
  reviewSummary: FabRecord;
  onOpenWave: () => void;
  onOpenGmail: () => void;
  onOpenDrive: () => void;
  onOpenReviews: () => void;
};

export function FabActivationChecklist({
  waveSetup,
  gmailAuthorization,
  driveAuthorization,
  reviewSummary,
  onOpenWave,
  onOpenGmail,
  onOpenDrive,
  onOpenReviews,
}: FabActivationChecklistProps) {
  const { copy, status: localizedStatus } = useFabLocale();
  const waveReady = bool(waveSetup.ready);
  const gmailReady = bool(gmailAuthorization.scannerPolicyReady)
    && bool(gmailAuthorization.credentialsPresent)
    && bool(gmailAuthorization.tokenPresent)
    && !bool(gmailAuthorization.reauthorizationRequired);
  const driveReady = bool(driveAuthorization.credentialsPresent)
    && bool(driveAuthorization.tokenPresent)
    && bool(driveAuthorization.folderConfigured)
    && !bool(driveAuthorization.reauthorizationRequired);
  const reviewCountKnown = reviewSummary.documents !== null && reviewSummary.documents !== undefined;
  const reviewDocuments = count(reviewSummary.documents);
  const reviewsReady = reviewCountKnown && reviewDocuments === 0;

  if (waveReady && gmailReady && driveReady && reviewsReady) return null;

  return (
    <section className="fab-activation-checklist" aria-labelledby="fab-activation-title">
      <div className="fab-activation-heading">
        <div><span>{copy("Required before autonomous delivery", "Vereist voor autonome verwerking")}</span><h2 id="fab-activation-title">{copy("Finish activation", "Activering voltooien")}</h2></div>
        <span className="fab-status-chip tone-warn">{copy("External delivery paused", "Externe verwerking gepauzeerd")}</span>
      </div>
      <div className="fab-activation-steps">
        <ActivationStep
          icon={Building2}
          complete={waveReady}
          title="Wave - Noodzakelijk Online"
          status={localizedStatus(text(waveSetup.status, "needs_token"))}
          actionLabel={copy("Connect Wave", "Wave koppelen")}
          onAction={onOpenWave}
        />
        <ActivationStep
          icon={Mail}
          complete={gmailReady}
          title="Gmail scanner"
          status={localizedStatus(text(gmailAuthorization.status, "credentials_required"))}
          actionLabel={copy("Authorize Gmail", "Gmail autoriseren")}
          onAction={onOpenGmail}
        />
        <ActivationStep
          icon={Cloud}
          complete={driveReady}
          title="Google Drive"
          status={localizedStatus(text(driveAuthorization.status, "credentials_required"))}
          actionLabel={copy("Authorize Drive", "Drive autoriseren")}
          onAction={onOpenDrive}
        />
        <ActivationStep
          icon={FileCheck2}
          complete={reviewsReady}
          title={copy("Document decisions", "Documentbeslissingen")}
          status={reviewCountKnown
            ? reviewDocuments === 0
              ? copy("Review queue clear", "Controlewachtrij leeg")
              : `${reviewDocuments} ${copy(reviewDocuments === 1 ? "document blocked" : "documents blocked", reviewDocuments === 1 ? "document geblokkeerd" : "documenten geblokkeerd")}`
            : copy("Review status unavailable", "Controlestatus niet beschikbaar")}
          actionLabel={copy("Open review queue", "Controlewachtrij openen")}
          onAction={onOpenReviews}
        />
      </div>
      <div className="fab-activation-safety"><ShieldCheck aria-hidden="true" /><span>{copy("Source files remain retained until Wave transaction and exact attachment readback evidence pass every archive gate.", "Bronbestanden blijven behouden totdat de Wave-transactie en de exacte teruggelezen bijlage alle archiefcontroles doorstaan.")}</span></div>
    </section>
  );
}

type ActivationStepProps = {
  icon: typeof Building2;
  complete: boolean;
  title: string;
  status: string;
  actionLabel: string;
  onAction: () => void;
};

function ActivationStep({ icon: Icon, complete, title, status, actionLabel, onAction }: ActivationStepProps) {
  const { copy } = useFabLocale();
  return (
    <div className={`fab-activation-step ${complete ? "is-complete" : ""}`}>
      <span className={`fab-activation-icon tone-${complete ? "good" : "warn"}`}>{complete ? <CheckCircle2 aria-hidden="true" /> : <Icon aria-hidden="true" />}</span>
      <div><strong>{title}</strong><span>{status}</span></div>
      {complete
        ? <span className="fab-status-chip tone-good">{copy("Ready", "Gereed")}</span>
        : <button className="fab-secondary-button compact" type="button" onClick={onAction}>{actionLabel}</button>}
    </div>
  );
}
