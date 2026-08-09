const REVIEW_DRAFT_VERSION = 1;
const REVIEW_DRAFT_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000;
const REVIEW_DRAFT_PREFIX = "fab.review-draft.v1";
const TARGET_SYSTEMS = new Set(["waveapps_business", "waveapps_personal", "mijngeldzaken"]);
const DOCUMENT_TYPES = new Set([
  "receipt",
  "vendor_invoice",
  "credit_note",
  "order_confirmation",
  "estimate",
  "bank_statement",
  "insurance_policy",
  "government_correspondence",
]);

export type FabReviewDraftForm = {
  vendorName: string;
  transactionDate: string;
  totalAmount: string;
  vatAmount: string;
  category: string;
  documentType: "receipt" | "vendor_invoice" | "credit_note" | "order_confirmation" | "estimate" | "bank_statement" | "insurance_policy" | "government_correspondence";
  targetSystem: "waveapps_business" | "waveapps_personal" | "mijngeldzaken";
  resolution: string;
  learnRule: boolean;
  applyToMatchingVendor: boolean;
};

export type FabReviewDraftStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">;

type StoredReviewDraft = {
  version: number;
  identity: string;
  savedAt: string;
  form: FabReviewDraftForm;
};

export function reviewDraftKey(reviewItemId: number): string {
  return `${REVIEW_DRAFT_PREFIX}.${reviewItemId}`;
}

export function saveReviewDraft(
  storage: FabReviewDraftStorage,
  reviewItemId: number,
  identity: string,
  form: FabReviewDraftForm,
  now = new Date(),
): boolean {
  if (!validReviewItemId(reviewItemId) || !validIdentity(identity) || !validForm(form)) return false;
  const payload: StoredReviewDraft = {
    version: REVIEW_DRAFT_VERSION,
    identity,
    savedAt: now.toISOString(),
    form,
  };
  try {
    storage.setItem(reviewDraftKey(reviewItemId), JSON.stringify(payload));
    return true;
  } catch {
    return false;
  }
}

export function loadReviewDraft(
  storage: FabReviewDraftStorage,
  reviewItemId: number,
  identity: string,
  now = new Date(),
): FabReviewDraftForm | null {
  if (!validReviewItemId(reviewItemId) || !validIdentity(identity)) return null;
  let raw: string | null = null;
  try {
    raw = storage.getItem(reviewDraftKey(reviewItemId));
  } catch {
    return null;
  }
  if (!raw || raw.length > 16_384) return null;
  try {
    const payload = JSON.parse(raw) as Partial<StoredReviewDraft>;
    const savedAt = Date.parse(String(payload.savedAt || ""));
    const stale = !Number.isFinite(savedAt)
      || savedAt > now.getTime() + 60_000
      || now.getTime() - savedAt > REVIEW_DRAFT_MAX_AGE_MS;
    if (
      payload.version !== REVIEW_DRAFT_VERSION
      || payload.identity !== identity
      || stale
      || !validForm(payload.form)
    ) {
      clearReviewDraft(storage, reviewItemId);
      return null;
    }
    return { ...payload.form };
  } catch {
    clearReviewDraft(storage, reviewItemId);
    return null;
  }
}

export function clearReviewDraft(storage: FabReviewDraftStorage, reviewItemId: number): void {
  if (!validReviewItemId(reviewItemId)) return;
  try {
    storage.removeItem(reviewDraftKey(reviewItemId));
  } catch {
    // Storage denial must never block a bookkeeping decision.
  }
}

export function reviewDraftChanged(form: FabReviewDraftForm, baseline: FabReviewDraftForm): boolean {
  return JSON.stringify(form) !== JSON.stringify(baseline);
}

function validReviewItemId(value: number): boolean {
  return Number.isSafeInteger(value) && value > 0;
}

function validIdentity(value: string): boolean {
  return value.length > 0 && value.length <= 2_048;
}

function validForm(value: unknown): value is FabReviewDraftForm {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const form = value as Record<string, unknown>;
  return boundedString(form.vendorName, 500)
    && boundedString(form.transactionDate, 32)
    && boundedString(form.totalAmount, 64)
    && boundedString(form.vatAmount, 64)
    && boundedString(form.category, 500)
    && typeof form.documentType === "string"
    && DOCUMENT_TYPES.has(form.documentType)
    && typeof form.targetSystem === "string"
    && TARGET_SYSTEMS.has(form.targetSystem)
    && boundedString(form.resolution, 4_000)
    && typeof form.learnRule === "boolean"
    && typeof form.applyToMatchingVendor === "boolean";
}

function boundedString(value: unknown, maxLength: number): value is string {
  return typeof value === "string" && value.length <= maxLength;
}
