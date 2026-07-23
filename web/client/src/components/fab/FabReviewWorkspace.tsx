import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  AlertTriangle,
  ArrowUpRight,
  CheckCircle2,
  ClipboardCheck,
  CopyCheck,
  FileSearch,
  Scale,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { FabDataStatus, FabPanelStateMessage } from "./FabDataState";
import { useFabLocale } from "./fabLocale";
import {
  matchesReviewTriage,
  reviewTriageCounts,
  reviewTriageFilters,
  vendorReviewBatches,
  type FabReviewTriageFilter,
} from "./fabReviewTriage";
import {
  reviewApprovalBlockers,
  type FabReviewApprovalBlocker,
} from "./fabReviewApproval";
import {
  asRecord,
  count,
  humanize,
  matchesSearch,
  panelState,
  records,
  statusTone,
  text,
  type FabRecord,
  type FabResourceState,
} from "./fabView";

export type FabReviewResolution = {
  reviewItemId: number;
  status: "approved" | "rejected" | "resolved" | "ignored";
  resolution: string;
  corrections?: {
    vendorName?: string;
    category?: string;
    transactionDate?: string;
    totalAmount?: number;
    vatAmount?: number;
    targetSystem?: "waveapps_business" | "waveapps_personal" | "mijngeldzaken";
    duplicateOfDocumentId?: number;
    duplicateCandidateId?: number;
    documentType?: ReviewDocumentType;
  };
  learnRule?: boolean;
  applyToMatchingVendor?: boolean;
};

type FabReviewWorkspaceProps = {
  workItems: FabRecord[];
  categoryOptions: string[];
  summary: FabRecord;
  resource?: FabResourceState;
  search: string;
  localApiEndpoint: string;
  resolvingReviewId: number | null;
  onResolve: (input: FabReviewResolution) => Promise<void>;
};

export function FabReviewWorkspace({
  workItems,
  categoryOptions,
  summary,
  resource,
  search,
  localApiEndpoint,
  resolvingReviewId,
  onResolve,
}: FabReviewWorkspaceProps) {
  const { copy } = useFabLocale();
  const [selectedId, setSelectedId] = useState("");
  const [reviewFilter, setReviewFilter] = useState<FabReviewTriageFilter>("all");
  const triageCounts = useMemo(() => reviewTriageCounts(workItems), [workItems]);
  const vendorBatches = useMemo(() => vendorReviewBatches(workItems), [workItems]);
  const visibleItems = useMemo(
    () => reviewFilter === "vendor_batches"
      ? vendorBatches
        .filter((batch) => batch.items.some((item) => matchesSearch(item, search)))
        .map((batch) => batch.representative)
      : workItems.filter((item) => matchesReviewTriage(item, reviewFilter) && matchesSearch(item, search)),
    [reviewFilter, vendorBatches, workItems, search],
  );
  const vendorBatchByRepresentativeId = useMemo(
    () => new Map(vendorBatches.map((batch) => [text(batch.representative.id), batch])),
    [vendorBatches],
  );
  const selected = workItems.find((item) => text(item.id, "") === selectedId) || null;
  const state = panelState(resource, workItems.length);

  useEffect(() => {
    if (selectedId && !workItems.some((item) => text(item.id, "") === selectedId)) {
      setSelectedId("");
    }
  }, [selectedId, workItems]);

  return (
    <section id="review-workspace" className="fab-section fab-review-workspace">
      <div className="fab-section-heading">
        <div>
          <span>{copy("Human decisions", "Menselijke beslissingen")}</span>
          <h2>{copy("Document review workspace", "Werkruimte documentcontrole")}</h2>
        </div>
        <div className="fab-section-statuses">
          <span className="fab-review-count"><strong>{count(summary.documents)}</strong> {copy("documents", "documenten")}</span>
          <FabDataStatus resource={resource} state={state} emptyLabel={copy("Clear", "Leeg")} />
        </div>
      </div>

      {(resource?.state === "live" || resource?.state === "stale") && workItems.length > 0 ? (
        <div className="fab-filter-bar fab-review-filter-bar">
          <div className="fab-segmented-control" role="group" aria-label={copy("Review queue mode", "Modus controlewachtrij")}>
            {reviewTriageFilters.map((filter) => (
              <button
                key={filter}
                type="button"
                className={reviewFilter === filter ? "is-active" : ""}
                aria-pressed={reviewFilter === filter}
                onClick={() => setReviewFilter(filter)}
              >
                <span>{reviewFilterLabel(filter, copy)}</span>
                <strong>{triageCounts[filter]}</strong>
              </button>
            ))}
          </div>
          <span className="fab-result-count">
            {reviewFilter === "vendor_batches"
              ? copy(`${visibleItems.length} vendor batches shown`, `${visibleItems.length} leveranciersbatches weergegeven`)
              : copy(`${visibleItems.length} shown`, `${visibleItems.length} weergegeven`)}
          </span>
        </div>
      ) : null}

      {(resource?.state === "live" || resource?.state === "stale") && visibleItems.length > 0 ? (
        <div className="fab-table-wrap">
          <table className="fab-table fab-review-table">
            <thead>
              <tr>
                <th>{copy("Source", "Bron")}</th>
                <th>{copy("Evidence / transaction", "Bewijs / transactie")}</th>
                <th>{copy("Open decisions", "Open beslissingen")}</th>
                <th>{copy("Duplicate evidence", "Duplicaatbewijs")}</th>
                <th><span className="sr-only">{copy("Actions", "Acties")}</span></th>
              </tr>
            </thead>
            <tbody>
              {visibleItems.map((item) => {
                const document = asRecord(item.document);
                const reasons = Array.isArray(item.reasons) ? item.reasons.filter((reason): reason is string => typeof reason === "string") : [];
                const duplicates = records(item.duplicateCandidates);
                const financialIssues = records(document.financialFieldIssues);
                const categorySuggestion = asRecord(document.categorySuggestion);
                const postingEligible = document.postingEligible !== false;
                const vendorBatch = vendorBatchByRepresentativeId.get(text(item.id));
                return (
                  <tr key={text(item.id)}>
                    <td data-label={copy("Source", "Bron")}>
                      <strong>{text(document.filename, copy("Unlinked review", "Niet-gekoppelde controle"))}</strong>
                      <span>{text(document.source, "-")} | #{text(item.documentId, "-")}</span>
                    </td>
                    <td data-label={copy("Transaction", "Transactie")}>
                      <strong>{text(document.vendorName, copy("Vendor missing", "Leverancier ontbreekt"))}</strong>
                      <span>{text(document.transactionDate, copy("Date missing", "Datum ontbreekt"))} | {postingEligible ? formatMoney(document.totalAmount, document.currency, copy("Amount missing", "Bedrag ontbreekt")) : reasons.includes("document_type_conflict") ? copy("Type decision required", "Typebeslissing vereist") : copy("Non-posting evidence", "Niet-boekingsbewijs")}</span>
                      <span>{text(categorySuggestion.category, "")
                        ? copy(`Suggested: ${text(categorySuggestion.category)}`, `Voorgesteld: ${text(categorySuggestion.category)}`)
                        : text(document.category, copy("Category missing", "Categorie ontbreekt"))}</span>
                      {vendorBatch && <span>{copy(
                        `${vendorBatch.items.length} exact-vendor documents in this batch`,
                        `${vendorBatch.items.length} documenten met exact dezelfde leverancier in deze batch`,
                      )}</span>}
                    </td>
                    <td data-label={copy("Open decisions", "Open beslissingen")}>
                      <div className="fab-review-reasons">
                        {reasons.map((reason) => <span key={reason} className={`fab-status-chip tone-${statusTone(reason)}`}>{humanize(reason)}</span>)}
                        {financialIssues.map((issue, index) => <span key={`${text(issue.field)}-${index}`} className="fab-status-chip tone-warn">{financialIssueLabel(issue, copy)}</span>)}
                      </div>
                    </td>
                    <td data-label={copy("Duplicates", "Duplicaten")}>
                      <strong>{duplicates.length || copy("None", "Geen")}</strong>
                      <span>{duplicates.length ? copy("Comparison required", "Vergelijking vereist") : copy("No duplicate decision open", "Geen duplicaatbeslissing open")}</span>
                    </td>
                    <td data-label={copy("Actions", "Acties")}>
                      <button className="fab-primary-button compact" onClick={() => setSelectedId(text(item.id))}>
                        <ClipboardCheck aria-hidden="true" /> {vendorBatch
                          ? copy(`Review ${vendorBatch.items.length}`, `${vendorBatch.items.length} controleren`)
                          : copy("Review", "Controleren")}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : resource?.state === "live" && workItems.length === 0 ? (
        <div className="fab-empty-state compact"><CheckCircle2 aria-hidden="true" /><strong>{copy("No document decisions waiting", "Geen documentbeslissingen in afwachting")}</strong><span>{copy("FAB has no open document review gates.", "FAB heeft geen open documentcontroles.")}</span></div>
      ) : (resource?.state === "live" || resource?.state === "stale") && workItems.length > 0 && visibleItems.length === 0 ? (
        <div className="fab-empty-state compact"><FileSearch aria-hidden="true" /><strong>{copy("No matching reviews", "Geen overeenkomende controles")}</strong><span>{copy("Adjust the review mode or active search.", "Pas de controlemodus of zoekopdracht aan.")}</span></div>
      ) : (
        <FabPanelStateMessage resource={resource} title={copy("Review queue", "Controlewachtrij")} />
      )}

      <FabReviewDrawer
        item={selected}
        workItems={workItems}
        categoryOptions={categoryOptions}
        localApiEndpoint={localApiEndpoint}
        resolvingReviewId={resolvingReviewId}
        onResolve={onResolve}
        onClose={() => setSelectedId("")}
        defaultApplyToMatchingVendor={reviewFilter === "vendor_batches"}
      />
    </section>
  );
}

function reviewFilterLabel(
  filter: FabReviewTriageFilter,
  copy: (english: string, dutch: string) => string,
): string {
  if (filter === "vendor_batches") return copy("Vendor batches", "Leveranciersbatches");
  if (filter === "suggestions") return copy("Suggestions", "Voorstellen");
  if (filter === "validation") return copy("Validation", "Validatie");
  if (filter === "duplicates") return copy("Duplicates", "Duplicaten");
  if (filter === "supporting") return copy("Supporting", "Onderbouwing");
  return copy("All", "Alles");
}

function FabReviewDrawer({ item, workItems, categoryOptions, localApiEndpoint, resolvingReviewId, onResolve, onClose, defaultApplyToMatchingVendor }: {
  item: FabRecord | null;
  workItems: FabRecord[];
  categoryOptions: string[];
  localApiEndpoint: string;
  resolvingReviewId: number | null;
  onResolve: (input: FabReviewResolution) => Promise<void>;
  onClose: () => void;
  defaultApplyToMatchingVendor: boolean;
}) {
  const { copy } = useFabLocale();
  const closeRef = useRef<HTMLButtonElement>(null);
  const [form, setForm] = useState(() => emptyForm());
  const [error, setError] = useState("");
  const [selectedDuplicateCandidateId, setSelectedDuplicateCandidateId] = useState(0);
  const [previewDocumentId, setPreviewDocumentId] = useState(0);

  useEffect(() => {
    if (!item) return;
    const document = asRecord(item.document);
    const categorySuggestion = asRecord(document.categorySuggestion);
    const financialIssues = records(document.financialFieldIssues);
    const invalidDate = financialIssues.some((issue) => text(issue.field, "") === "recordDate");
    const invalidVat = financialIssues.some((issue) => text(issue.field, "") === "vatAmount");
    const documentType = normalizedDocumentType(document.documentType);
    setForm({
      vendorName: text(document.vendorName, ""),
      transactionDate: invalidDate ? "" : text(document.normalizedRecordDate, text(document.transactionDate, "")),
      totalAmount: numericText(document.totalAmount),
      vatAmount: invalidVat
        ? ""
        : numericText(documentType === "credit_note" ? document.vatAmount : document.normalizedVatAmount ?? document.vatAmount),
      category: text(document.category, "") === "Manual Review"
        ? text(categorySuggestion.category, "")
        : text(document.category, ""),
      documentType,
      targetSystem: text(document.targetSystem, "waveapps_business") as ReviewForm["targetSystem"],
      resolution: text(categorySuggestion.category, "")
        ? copy(
          `Verified FAB's exact-vendor suggestion: ${text(categorySuggestion.category)}.`,
          `FAB's exacte leveranciersvoorstel geverifieerd: ${text(categorySuggestion.category)}.`,
        )
        : copy("Verified against the source document in FAB.", "Geverifieerd aan de hand van het brondocument in FAB."),
      learnRule: true,
      applyToMatchingVendor: defaultApplyToMatchingVendor,
    });
    const duplicateCandidates = records(item.duplicateCandidates);
    setSelectedDuplicateCandidateId((current) => (
      duplicateCandidates.some((candidate) => count(candidate.id) === current)
        ? current
        : count(duplicateCandidates[0]?.id)
    ));
    setPreviewDocumentId(count(item.documentId));
    setError("");
  }, [copy, defaultApplyToMatchingVendor, item]);

  useEffect(() => {
    if (!item) return;
    globalThis.document.body.classList.add("fab-dialog-open");
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      globalThis.document.body.classList.remove("fab-dialog-open");
    };
  }, [item, onClose]);

  if (!item) return null;
  const document = asRecord(item.document);
  const categorySuggestion = asRecord(document.categorySuggestion);
  const reviewItems = records(item.reviewItems);
  const detailReview = reviewItems.find((review) => TYPE_REVIEW_REASONS.has(text(review.reason, "")))
    || reviewItems.find((review) => text(review.reason, "") !== "duplicate_candidate")
    || null;
  const duplicateReview = reviewItems.find((review) => text(review.reason, "") === "duplicate_candidate") || null;
  const duplicateCandidates = records(item.duplicateCandidates);
  const financialIssues = records(document.financialFieldIssues);
  const duplicateCandidate = duplicateCandidates.find(
    (candidate) => count(candidate.id) === selectedDuplicateCandidateId,
  ) || duplicateCandidates[0] || null;
  const candidateDocument = asRecord(duplicateCandidate?.document);
  const currentIdentity = asRecord(duplicateCandidate?.currentIdentity);
  const candidateIdentity = asRecord(duplicateCandidate?.candidateIdentity);
  const matchedIdentityFields = stringList(duplicateCandidate?.matchedIdentityFields);
  const conflictingIdentityFields = stringList(duplicateCandidate?.conflictingIdentityFields);
  const duplicateCandidateIndex = Math.max(
    0,
    duplicateCandidates.findIndex((candidate) => count(candidate.id) === count(duplicateCandidate?.id)),
  );
  const sourceDocumentId = count(item.documentId);
  const comparisonDocumentId = count(duplicateCandidate?.candidateDocumentId);
  const selectedPreviewDocumentId = previewDocumentId || sourceDocumentId;
  const previewFilename = selectedPreviewDocumentId === comparisonDocumentId
    ? text(candidateDocument.filename, copy("Comparison source", "Vergelijkingsbron"))
    : text(document.filename, copy("Source document", "Brondocument"));
  const isBusy = resolvingReviewId !== null;
  const typeDecisionRequired = reviewItems.some((review) => TYPE_REVIEW_REASONS.has(text(review.reason, "")));
  const selectedNonPosting = NON_POSTING_DOCUMENT_TYPES.has(form.documentType);
  const selectedCreditNote = form.documentType === "credit_note";
  const approvalBlockers = reviewApprovalBlockers(form, { nonPosting: selectedNonPosting });
  const approvalReady = approvalBlockers.length === 0;
  const detailReviewSupportsBatch = VENDOR_CATEGORY_REASONS.has(text(detailReview?.reason, ""));
  const matchingVendorDocuments = detailReviewSupportsBatch ? workItems.filter((candidate) => {
    if (text(candidate.id, "") === text(item.id, "")) return false;
    const candidateDocument = asRecord(candidate.document);
    const candidateReasons = Array.isArray(candidate.reasons) ? candidate.reasons : [];
    return normalizedVendor(text(candidateDocument.vendorName, "")) === normalizedVendor(form.vendorName)
      && text(candidateDocument.targetSystem, "waveapps_business") === form.targetSystem
      && text(candidateDocument.processingStatus, "") !== "duplicate"
      && count(candidateDocument.duplicateOfDocumentId) === 0
      && candidateReasons.some((reason) => VENDOR_CATEGORY_REASONS.has(text(reason, "")));
  }).length : 0;

  async function approveDetails() {
    if (!detailReview) return;
    if (selectedNonPosting) {
      if (form.resolution.trim().length < 3) {
        setError(copy("Add a short decision note.", "Voeg een korte beslisnotitie toe."));
        return;
      }
      setError("");
      try {
        await onResolve({
          reviewItemId: count(detailReview.id),
          status: "approved",
          resolution: form.resolution.trim(),
          corrections: { documentType: form.documentType },
          learnRule: false,
          applyToMatchingVendor: false,
        });
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : copy("Review update failed.", "Bijwerken van controle mislukt."));
      }
      return;
    }
    const totalAmount = parseNumber(form.totalAmount);
    const vatAmount = form.vatAmount.trim() ? parseNumber(form.vatAmount) : undefined;
    if (!form.vendorName.trim() || !form.transactionDate || totalAmount === undefined || !form.category.trim()) {
      setError(copy("Vendor, date, amount, and category are required.", "Leverancier, datum, bedrag en categorie zijn verplicht."));
      return;
    }
    if (form.resolution.trim().length < 3) {
      setError(copy("Add a short decision note.", "Voeg een korte beslisnotitie toe."));
      return;
    }
    setError("");
    try {
      await onResolve({
        reviewItemId: count(detailReview.id),
        status: "approved",
        resolution: form.resolution.trim(),
        corrections: {
          vendorName: form.vendorName.trim(),
          transactionDate: form.transactionDate,
          totalAmount,
          vatAmount,
          category: form.category.trim(),
          targetSystem: form.targetSystem,
          documentType: typeDecisionRequired ? form.documentType : undefined,
        },
        learnRule: form.learnRule,
        applyToMatchingVendor: form.applyToMatchingVendor,
      });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : copy("Review update failed.", "Bijwerken van controle mislukt."));
    }
  }

  async function decideDuplicate(isDuplicate: boolean) {
    if (!duplicateReview) return;
    const duplicateCandidateId = count(duplicateCandidate?.id);
    const candidateId = count(duplicateCandidate?.candidateDocumentId);
    if (!duplicateCandidateId || !candidateId) {
      setError(copy("The duplicate candidate is missing its canonical document.", "Bij het duplicaat ontbreekt het canonieke document."));
      return;
    }
    setError("");
    try {
      await onResolve({
        reviewItemId: count(duplicateReview.id),
        status: isDuplicate ? "approved" : "rejected",
        resolution: isDuplicate
          ? copy(`Confirmed as the same transaction as document #${candidateId}.`, `Bevestigd als dezelfde transactie als document #${candidateId}.`)
          : copy(`Confirmed as a different transaction from document #${candidateId}.`, `Bevestigd als een andere transactie dan document #${candidateId}.`),
        corrections: {
          duplicateCandidateId,
          duplicateOfDocumentId: isDuplicate ? candidateId : undefined,
        },
        learnRule: false,
      });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : copy("Duplicate decision failed.", "Duplicaatbeslissing mislukt."));
    }
  }

  return createPortal(
    <div className="fab-command-overlay" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <aside className="fab-detail-drawer fab-review-drawer" role="dialog" aria-modal="true" aria-labelledby="fab-review-title">
        <div className="fab-command-header">
          <div><span>{copy("Source-backed decision", "Brongestuurde beslissing")}</span><h2 id="fab-review-title">{text(document.filename, copy("Review item", "Controle-item"))}</h2></div>
          <button ref={closeRef} className="fab-icon-button" onClick={onClose} aria-label={copy("Close review", "Controle sluiten")} title={copy("Close review", "Controle sluiten")}><X aria-hidden="true" /></button>
        </div>
        <div className="fab-detail-body">
          {sourceDocumentId > 0 && (
            <section className={`fab-source-preview${comparisonDocumentId > 0 && comparisonDocumentId !== sourceDocumentId ? " has-comparison" : ""}`} aria-labelledby="fab-source-preview-title">
              <div className="fab-source-preview-heading">
                <div>
                  <span>{copy("Retained evidence", "Bewaard bewijs")}</span>
                  <h3 id="fab-source-preview-title">{copy("Source document", "Brondocument")}</h3>
                </div>
                <strong><ShieldCheck aria-hidden="true" /> {copy("Integrity checked", "Integriteit gecontroleerd")}</strong>
              </div>
              {comparisonDocumentId > 0 && comparisonDocumentId !== sourceDocumentId && (
                <div className="fab-source-preview-switcher" role="group" aria-label={copy("Source document selection", "Selectie brondocument")}>
                  <button type="button" className={selectedPreviewDocumentId === sourceDocumentId ? "is-active" : ""} aria-pressed={selectedPreviewDocumentId === sourceDocumentId} onClick={() => setPreviewDocumentId(sourceDocumentId)}>
                    {copy("Current", "Huidig")} #{sourceDocumentId}
                  </button>
                  <button type="button" className={selectedPreviewDocumentId === comparisonDocumentId ? "is-active" : ""} aria-pressed={selectedPreviewDocumentId === comparisonDocumentId} onClick={() => setPreviewDocumentId(comparisonDocumentId)}>
                    {copy("Candidate", "Kandidaat")} #{comparisonDocumentId}
                  </button>
                </div>
              )}
              <iframe
                key={selectedPreviewDocumentId}
                src={`/api/fab/source/${selectedPreviewDocumentId}`}
                title={copy(`Source preview: ${previewFilename}`, `Bronvoorbeeld: ${previewFilename}`)}
                referrerPolicy="no-referrer"
              />
              <div className="fab-source-preview-footer">
                <span>{previewFilename}</span>
                <a href={`/api/fab/source/${selectedPreviewDocumentId}`} target="_blank" rel="noreferrer">
                  {copy("Open separately", "Apart openen")} <ArrowUpRight aria-hidden="true" />
                </a>
              </div>
            </section>
          )}

          <div className="fab-review-evidence-links">
            <a className="fab-secondary-button" href={`${localApiEndpoint}${text(item.reviewPath, "/#review")}`} target="_blank" rel="noreferrer"><FileSearch aria-hidden="true" /> {copy("Open FAB evidence", "Open FAB-bewijs")}</a>
            {text(document.sourceUrl, "") && <a className="fab-secondary-button" href={text(document.sourceUrl)} target="_blank" rel="noreferrer"><ArrowUpRight aria-hidden="true" /> {copy("Open Drive source", "Open Drive-bron")}</a>}
          </div>

          <div className="fab-review-gates" aria-label={copy("Open review gates", "Open controlepoorten")}>
            {reviewItems.map((review) => <div key={text(review.id)}><span className={`fab-status-chip tone-${statusTone(review.reason)}`}>{humanize(review.reason)}</span><p>{text(review.details, copy("Manual verification required.", "Handmatige verificatie vereist."))}</p></div>)}
          </div>

          {financialIssues.length > 0 && (
            <div className="fab-financial-warning" role="alert">
              <AlertTriangle aria-hidden="true" />
              <div>
                <strong>{copy("Financial values held out of posting", "Financiele waarden niet meegenomen in boeking")}</strong>
                {financialIssues.map((issue, index) => (
                  <span key={`${text(issue.field)}-${index}`}>
                    {financialIssueLabel(issue, copy)}: {copy("source evidence", "bronbewijs")} {formatEvidenceValue(issue.evidenceValue)}. {copy("Enter a verified replacement before approval.", "Voer voor goedkeuring een geverifieerde vervanging in.")}
                  </span>
                ))}
              </div>
            </div>
          )}

          {text(categorySuggestion.category, "") && !selectedNonPosting && (
            <div className="fab-category-suggestion">
              <Sparkles aria-hidden="true" />
              <div>
                <strong>{copy(`Suggested category: ${text(categorySuggestion.category)}`, `Voorgestelde categorie: ${text(categorySuggestion.category)}`)}</strong>
                <span>{copy(text(categorySuggestion.rationale), text(categorySuggestion.rationale))} {copy("This is prefilled but is not applied until you approve it.", "Dit is vooraf ingevuld, maar wordt pas toegepast na uw goedkeuring.")}</span>
              </div>
              <span>{formatPercent(categorySuggestion.confidenceScore)}</span>
            </div>
          )}

          {detailReview && (
            <form className="fab-review-form" onSubmit={(event) => { event.preventDefault(); void approveDetails(); }}>
              <div className="fab-subsection-heading"><div><span>{selectedNonPosting ? copy("Evidence classification", "Bewijsclassificatie") : copy("Bookkeeping fields", "Boekhoudvelden")}</span><h3>{selectedNonPosting ? copy("Confirm document role", "Bevestig documentrol") : copy("Confirm extracted details", "Bevestig uitgelezen gegevens")}</h3></div></div>
              {typeDecisionRequired && <label><span>{copy("Document type", "Documenttype")}</span><select value={form.documentType} onChange={(event) => setForm({ ...form, documentType: event.target.value as ReviewDocumentType })}>{DOCUMENT_TYPE_OPTIONS.map((option) => <option key={option} value={option}>{humanize(option)}</option>)}</select><small>{copy(`Classifier suggestion: ${humanize(text(document.classifiedDocumentType, "unknown"))}`, `Classificatievoorstel: ${humanize(text(document.classifiedDocumentType, "unknown"))}`)}</small></label>}
              {!selectedNonPosting && <>
                {selectedCreditNote && <div className="fab-financial-warning" role="status"><AlertTriangle aria-hidden="true" /><div><strong>{copy("Expense reversal", "Kostenboeking terugdraaien")}</strong><span>{copy("FAB will post this credit note as a Wave deposit that decreases the selected expense account. Verify the positive source amount below; FAB stores the ledger reversal with a negative sign.", "FAB boekt deze creditnota als een Wave-storting die de gekozen kostenrekening verlaagt. Controleer hieronder het positieve bronbedrag; FAB bewaart de terugboeking negatief in het grootboek.")}</span></div></div>}
                <label><span>{copy("Vendor", "Leverancier")}</span><input value={form.vendorName} onChange={(event) => setForm({ ...form, vendorName: event.target.value })} required /></label>
                <div className="fab-review-field-row">
                  <label><span>{copy("Transaction date", "Transactiedatum")}</span><input type="date" value={form.transactionDate} onChange={(event) => setForm({ ...form, transactionDate: event.target.value })} required /></label>
                  <label><span>{selectedCreditNote ? copy("Credit amount", "Creditbedrag") : copy("Amount", "Bedrag")}</span><input type="number" min="0" step="0.01" value={form.totalAmount} onChange={(event) => setForm({ ...form, totalAmount: event.target.value })} required /></label>
                  <label><span>{copy("VAT", "Btw")}</span><input type="number" min="0" step="0.01" value={form.vatAmount} onChange={(event) => setForm({ ...form, vatAmount: event.target.value })} /></label>
                </div>
                <label>
                  <span>{copy("FAB category intent", "FAB-categorie-intentie")}</span>
                  <input list="fab-review-categories" value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })} placeholder={copy("Choose or enter a bookkeeping category", "Kies of voer een boekhoudcategorie in")} required />
                  <datalist id="fab-review-categories">{categoryOptions.map((category) => <option key={category} value={category} />)}</datalist>
                  <small>{copy("FAB learns this decision now. The exact Wave ledger account is mapped separately and must be verified before posting.", "FAB leert deze beslissing nu. De exacte Wave-grootboekrekening wordt apart toegewezen en moet voor het boeken zijn geverifieerd.")}</small>
                </label>
                <label><span>{copy("Destination", "Bestemming")}</span><select value={form.targetSystem} onChange={(event) => setForm({ ...form, targetSystem: event.target.value as ReviewForm["targetSystem"] })}><option value="waveapps_business">Wave - Noodzakelijk Online</option><option value="waveapps_personal">Wave - Personal</option><option value="mijngeldzaken">MijnGeldzaken</option></select></label>
              </>}
              <label><span>{copy("Decision note", "Beslisnotitie")}</span><textarea value={form.resolution} onChange={(event) => setForm({ ...form, resolution: event.target.value })} rows={3} required /></label>
              {!selectedNonPosting && <label className="fab-review-checkbox"><input type="checkbox" checked={form.learnRule} onChange={(event) => setForm({ ...form, learnRule: event.target.checked })} /><span><strong>{copy("Teach FAB this exact vendor/category rule", "Leer FAB deze exacte leverancier/categorieregel")}</strong><small>{copy("Your approved source-backed decision becomes reusable for future exact-vendor matches.", "Uw goedgekeurde, brongestuurde beslissing wordt herbruikbaar voor toekomstige exacte leveranciersmatches.")}</small></span></label>}
              {!selectedNonPosting && matchingVendorDocuments > 0 && <label className="fab-review-checkbox fab-review-batch"><input type="checkbox" checked={form.applyToMatchingVendor} onChange={(event) => setForm({ ...form, applyToMatchingVendor: event.target.checked })} /><span><strong>{copy(`Apply this category to ${matchingVendorDocuments} other exact vendor match${matchingVendorDocuments === 1 ? "" : "es"}`, `Pas deze categorie toe op ${matchingVendorDocuments} andere exacte leveranciersmatch${matchingVendorDocuments === 1 ? "" : "es"}`)}</strong><small>{copy("Dates and amounts stay unchanged. Duplicate and missing-field reviews remain open.", "Datums en bedragen blijven ongewijzigd. Controles voor duplicaten en ontbrekende velden blijven open.")}</small></span></label>}
              {!approvalReady && (
                <div className="fab-review-readiness" role="status">
                  <AlertTriangle aria-hidden="true" />
                  <span>
                    <strong>{copy("Required before approval", "Vereist voor goedkeuring")}</strong>
                    <small>{approvalBlockers.map((blocker) => reviewApprovalBlockerLabel(blocker, copy)).join(", ")}</small>
                  </span>
                </div>
              )}
              <button className="fab-primary-button" type="submit" disabled={isBusy || !approvalReady}><CheckCircle2 aria-hidden="true" /> {selectedNonPosting ? copy("Keep as supporting evidence", "Bewaren als ondersteunend bewijs") : selectedCreditNote ? copy("Approve credit reversal", "Creditboeking goedkeuren") : copy("Approve verified details", "Goedgekeurde gegevens bevestigen")}</button>
            </form>
          )}

          {duplicateReview && (
            <section className="fab-duplicate-decision">
              <div className="fab-subsection-heading">
                <div>
                  <span>{copy("Duplicate control", "Duplicaatcontrole")}</span>
                  <h3>{copy("Compare both source documents", "Vergelijk beide brondocumenten")}</h3>
                </div>
                {duplicateCandidate && (
                  <strong className="fab-duplicate-position">
                    {copy(
                      `${duplicateCandidateIndex + 1} of ${duplicateCandidates.length}`,
                      `${duplicateCandidateIndex + 1} van ${duplicateCandidates.length}`,
                    )}
                  </strong>
                )}
              </div>

              {duplicateCandidates.length > 1 && (
                <div className="fab-duplicate-candidate-picker" role="group" aria-label={copy("Duplicate candidates", "Duplicaatkandidaten")}>
                  {duplicateCandidates.map((candidate, index) => (
                    <button
                      key={text(candidate.id)}
                      type="button"
                      className={count(candidate.id) === count(duplicateCandidate?.id) ? "is-active" : ""}
                      aria-pressed={count(candidate.id) === count(duplicateCandidate?.id)}
                      onClick={() => setSelectedDuplicateCandidateId(count(candidate.id))}
                    >
                      <span>{copy(`Match ${index + 1}`, `Match ${index + 1}`)}</span>
                      <strong>#{text(candidate.candidateDocumentId)}</strong>
                    </button>
                  ))}
                </div>
              )}

              {duplicateCandidate ? (
                <>
                  <div className="fab-duplicate-evidence-summary">
                    <div>
                      <span className="fab-status-chip tone-info">{humanize(duplicateCandidate.matchType)}</span>
                      <strong>{copy(
                        `${formatPercent(duplicateCandidate.confidenceScore) || "Unscored"} detector confidence`,
                        `${formatPercent(duplicateCandidate.confidenceScore) || "Geen score"} detectorbetrouwbaarheid`,
                      )}</strong>
                      <small>{copy(
                        `${count(duplicateCandidate.comparableFields)} comparable identity fields`,
                        `${count(duplicateCandidate.comparableFields)} vergelijkbare identiteitsvelden`,
                      )}</small>
                    </div>
                    <div className="fab-duplicate-match-tags" aria-label={copy("Matched identity fields", "Overeenkomende identiteitsvelden")}>
                      {matchedIdentityFields.length > 0
                        ? matchedIdentityFields.map((field) => <span key={field}><CheckCircle2 aria-hidden="true" /> {humanize(field)}</span>)
                        : <span className="is-neutral">{copy("No exact identity field match", "Geen exacte overeenkomst van identiteitsvelden")}</span>}
                    </div>
                  </div>

                  {conflictingIdentityFields.length > 0 && (
                    <div className="fab-financial-warning" role="alert">
                      <AlertTriangle aria-hidden="true" />
                      <div>
                        <strong>{copy("Conflicting transaction identifiers", "Tegenstrijdige transactie-identificaties")}</strong>
                        <span>{conflictingIdentityFields.map(humanize).join(", ")}. {copy("Do not approve this pair without checking both source files.", "Keur dit paar niet goed zonder beide bronbestanden te controleren.")}</span>
                      </div>
                    </div>
                  )}

                  <div className="fab-duplicate-comparison">
                    <div>
                      <small>{copy("Current", "Huidig")}</small>
                      <strong>#{text(item.documentId)} {text(document.filename)}</strong>
                      <span>{text(document.vendorName, copy("Vendor missing", "Leverancier ontbreekt"))}</span>
                      <span>{text(document.transactionDate, copy("Date missing", "Datum ontbreekt"))} | {formatMoney(document.totalAmount, document.currency, copy("Amount missing", "Bedrag ontbreekt"))}</span>
                      <DuplicateIdentityEvidence identity={currentIdentity} copy={copy} />
                    </div>
                    <Scale aria-hidden="true" />
                    <div>
                      <small>{copy("Candidate", "Kandidaat")}</small>
                      <strong>#{text(duplicateCandidate.candidateDocumentId)} {text(candidateDocument.filename)}</strong>
                      <span>{text(candidateDocument.vendorName, copy("Vendor missing", "Leverancier ontbreekt"))}</span>
                      <span>{text(candidateDocument.transactionDate, copy("Date missing", "Datum ontbreekt"))} | {formatMoney(candidateDocument.totalAmount, candidateDocument.currency, copy("Amount missing", "Bedrag ontbreekt"))}</span>
                      <DuplicateIdentityEvidence identity={candidateIdentity} copy={copy} />
                      <a href={`${localApiEndpoint}/documents/${text(duplicateCandidate.candidateDocumentId)}`} target="_blank" rel="noreferrer">{copy("Open comparison evidence", "Open vergelijkingsbewijs")} <ArrowUpRight aria-hidden="true" /></a>
                    </div>
                  </div>

                  <div className="fab-duplicate-retention-note">
                    <ShieldCheck aria-hidden="true" />
                    <span>
                      <strong>{copy("Both source files are retained", "Beide bronbestanden blijven behouden")}</strong>
                      <small>{copy("This decision controls bookkeeping identity only. FAB does not delete or archive either source file here.", "Deze beslissing bepaalt alleen de boekhoudkundige identiteit. FAB verwijdert of archiveert hier geen van beide bronbestanden.")}</small>
                    </span>
                  </div>
                </>
              ) : (
                <p>{copy("Duplicate candidate evidence is incomplete. Keep this gate open.", "Het duplicaatbewijs is onvolledig. Laat deze controle open.")}</p>
              )}
              <div className="fab-detail-actions">
                <button className="fab-primary-button" type="button" disabled={isBusy || !duplicateCandidate} onClick={() => { void decideDuplicate(true); }}><CopyCheck aria-hidden="true" /> {copy("Same transaction", "Dezelfde transactie")}</button>
                <button className="fab-secondary-button" type="button" disabled={isBusy || !duplicateCandidate} onClick={() => { void decideDuplicate(false); }}><X aria-hidden="true" /> {copy("Different transaction", "Andere transactie")}</button>
              </div>
            </section>
          )}

          {text(document.ocrExcerpt, "") && <details className="fab-review-ocr"><summary>{copy("Extracted source text", "Uitgelezen brontekst")}</summary><pre>{text(document.ocrExcerpt)}</pre></details>}
          {error && <div className="fab-inline-error" role="alert">{error}</div>}
        </div>
      </aside>
    </div>,
    globalThis.document.body,
  );
}

function DuplicateIdentityEvidence({ identity, copy }: {
  identity: FabRecord;
  copy: (english: string, dutch: string) => string;
}) {
  const fields = [
    [copy("Invoice", "Factuur"), text(identity.invoiceNumber, "")],
    [copy("Receipt", "Bon"), text(identity.receiptNumber, "")],
    [copy("Order", "Bestelling"), text(identity.orderNumber, "")],
    [copy("Transaction", "Transactie"), text(identity.transactionReference, "")],
    [copy("VAT", "Btw"), text(identity.tax, "")],
  ].filter((field): field is [string, string] => Boolean(field[1]));
  if (!fields.length) {
    return <p className="fab-duplicate-no-reference">{copy("No labeled reference recovered", "Geen gelabelde referentie gevonden")}</p>;
  }
  return (
    <dl className="fab-duplicate-identifiers">
      {fields.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

type ReviewForm = {
  vendorName: string;
  transactionDate: string;
  totalAmount: string;
  vatAmount: string;
  category: string;
  documentType: ReviewDocumentType;
  targetSystem: "waveapps_business" | "waveapps_personal" | "mijngeldzaken";
  resolution: string;
  learnRule: boolean;
  applyToMatchingVendor: boolean;
};

function emptyForm(): ReviewForm {
  return { vendorName: "", transactionDate: "", totalAmount: "", vatAmount: "", category: "", documentType: "receipt", targetSystem: "waveapps_business", resolution: "", learnRule: true, applyToMatchingVendor: false };
}

const VENDOR_CATEGORY_REASONS = new Set(["manual_review_category", "low_confidence_categorization"]);
const TYPE_REVIEW_REASONS = new Set(["credit_note_posting_review", "document_type_conflict", "non_posting_document_type"]);
const DOCUMENT_TYPE_OPTIONS = ["receipt", "vendor_invoice", "credit_note", "order_confirmation", "estimate", "bank_statement", "insurance_policy", "government_correspondence"] as const;
type ReviewDocumentType = typeof DOCUMENT_TYPE_OPTIONS[number];
const NON_POSTING_DOCUMENT_TYPES = new Set<ReviewDocumentType>(["order_confirmation", "estimate", "bank_statement", "insurance_policy", "government_correspondence"]);

function normalizedDocumentType(value: unknown): ReviewDocumentType {
  const normalized = text(value, "receipt") as ReviewDocumentType;
  return DOCUMENT_TYPE_OPTIONS.includes(normalized) ? normalized : "receipt";
}

function normalizedVendor(value: string): string {
  return value.trim().replace(/\s+/g, " ").toLocaleLowerCase();
}

function numericText(value: unknown): string {
  return typeof value === "number" && Number.isFinite(value) ? String(value) : "";
}

function stringList(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
    : [];
}

function parseNumber(value: string): number | undefined {
  const parsed = Number(value.replace(",", "."));
  return Number.isFinite(parsed) ? parsed : undefined;
}

function reviewApprovalBlockerLabel(
  blocker: FabReviewApprovalBlocker,
  copy: (english: string, dutch: string) => string,
): string {
  if (blocker === "vendorName") return copy("vendor", "leverancier");
  if (blocker === "transactionDate") return copy("valid transaction date", "geldige transactiedatum");
  if (blocker === "totalAmount") return copy("positive amount", "positief bedrag");
  if (blocker === "vatAmount") return copy("valid VAT", "geldige btw");
  if (blocker === "category") return copy("FAB category intent", "FAB-categorie-intentie");
  return copy("decision note", "beslisnotitie");
}

function formatMoney(value: unknown, currency: unknown, missingLabel: string): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return missingLabel;
  try {
    return new Intl.NumberFormat("en-NL", { style: "currency", currency: text(currency, "EUR") }).format(value);
  } catch {
    return `${text(currency, "EUR")} ${value.toFixed(2)}`;
  }
}

function formatPercent(value: unknown): string {
  const numeric = typeof value === "number" ? value : Number(value);
  return Number.isFinite(numeric) ? `${Math.round(numeric * 100)}%` : "";
}

function financialIssueLabel(issue: FabRecord, copy: (english: string, dutch: string) => string): string {
  const field = text(issue.field, "");
  if (field === "recordDate") return copy("Invalid transaction date", "Ongeldige transactiedatum");
  if (field === "vatAmount") return copy("Invalid VAT amount", "Ongeldig btw-bedrag");
  if (field.startsWith("lineItems[")) return copy("Invalid line-item tax", "Ongeldige btw op regel");
  return copy("Invalid financial field", "Ongeldig financieel veld");
}

function formatEvidenceValue(value: unknown): string {
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  return text(value, "-");
}
