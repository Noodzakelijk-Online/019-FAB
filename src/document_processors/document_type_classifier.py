import re
from typing import Any, Dict, Iterable, List, Tuple


class DocumentTypeClassifier:
    """Conservatively infer the bookkeeping role of an OCR document."""

    CLASSIFIER_VERSION = "deterministic_financial_document_type_v2"

    _PATTERNS: Tuple[Tuple[str, float, Tuple[str, ...]], ...] = (
        (
            "government_correspondence",
            0.99,
            (
                r"\bparticipatiewet\b",
                r"\bbijstandsnorm\b",
                r"\buitkeringsspecificatie\b",
                r"\btoeslagbeschikking\b",
            ),
        ),
        (
            "insurance_policy",
            0.98,
            (
                r"\bpolisblad\b",
                r"\bverzekeringspolis\b",
                r"\binsurance\s+policy\b",
                r"\bpolicy\s+schedule\b",
            ),
        ),
        (
            "credit_note",
            0.97,
            (
                r"\bcredit\s+note\b",
                r"\bcreditnota\b",
                r"\bcreditfactuur\b",
                r"\bcredit\s+memo\b",
            ),
        ),
        (
            "order_confirmation",
            0.95,
            (
                r"\border\s+confirmation\b",
                r"\borderbevestiging\b",
                r"\bbestelbevestiging\b",
                r"\bbevestiging\s+(?:van\s+)?(?:uw\s+)?bestelling\b",
            ),
        ),
        (
            "bank_statement",
            0.95,
            (
                r"\bbank\s+statement\b",
                r"\brekeningafschrift\b",
                r"\bbankafschrift\b",
                r"\baccount\s+statement\b",
            ),
        ),
        (
            "estimate",
            0.93,
            (
                r"\bestimate\b",
                r"\bquotation\b",
                r"\bofferte\b",
                r"\bprijsopgave\b",
            ),
        ),
        (
            "receipt",
            0.93,
            (
                r"\breceipt\b",
                r"\bkassabon\b",
                r"\bpinbon\b",
                r"\bbetaalbewijs\b",
                r"\bpayment\s+receipt\b",
                r"\bontvangstbewijs\b",
            ),
        ),
        (
            "vendor_invoice",
            0.92,
            (
                r"\binvoice\b",
                r"\bfactuur\b",
                r"\bfacturering\b",
                r"\bfactuurnummer\b",
                r"\binvoice\s+(?:no|number)\b",
            ),
        ),
    )

    _REFERENCE_SIGNALS = (
        ("credit_note", "credit_note_number", 0.97),
        ("receipt", "receipt_number", 0.94),
        ("vendor_invoice", "invoice_number", 0.95),
    )

    _POSTING_ELIGIBLE = {"receipt", "vendor_invoice"}
    _REVIEW_REQUIRED = {
        "bank_statement",
        "credit_note",
        "estimate",
        "government_correspondence",
        "insurance_policy",
        "order_confirmation",
    }
    _EVIDENCE_PRIORITY = {
        "receipt": 100,
        "vendor_invoice": 100,
        "credit_note": 95,
        "government_correspondence": 90,
        "insurance_policy": 90,
        "bank_statement": 60,
        "order_confirmation": 30,
        "estimate": 20,
        "unknown": 0,
    }

    def classify(self, text: str, extracted_data: Dict[str, Any] | None = None) -> Dict[str, Any]:
        extracted = extracted_data if isinstance(extracted_data, dict) else {}
        normalized_text = _normalize_text(text)
        candidates: List[Dict[str, Any]] = []

        for document_type, field_name, confidence in self._REFERENCE_SIGNALS:
            if str(extracted.get(field_name) or "").strip():
                candidates.append({
                    "documentType": document_type,
                    "confidenceScore": confidence,
                    "evidence": [f"field:{field_name}"],
                })

        for document_type, confidence, patterns in self._PATTERNS:
            evidence = [pattern for pattern in patterns if re.search(pattern, normalized_text, re.IGNORECASE)]
            if evidence:
                candidates.append({
                    "documentType": document_type,
                    "confidenceScore": confidence,
                    "evidence": [f"text:{_evidence_label(pattern)}" for pattern in evidence],
                })

        selected = _select_candidate(candidates)
        document_type = selected.get("documentType", "unknown")
        return {
            "documentType": document_type,
            "confidenceScore": float(selected.get("confidenceScore") or 0.0),
            "evidence": list(selected.get("evidence") or []),
            "postingEligible": document_type in self._POSTING_ELIGIBLE,
            "reviewRequired": document_type in self._REVIEW_REQUIRED,
            "evidencePriority": self._EVIDENCE_PRIORITY.get(document_type, 0),
            "classifier": self.CLASSIFIER_VERSION,
        }


NON_POSTING_DOCUMENT_TYPES = frozenset({
    "bank_statement",
    "credit_note",
    "estimate",
    "government_correspondence",
    "insurance_policy",
    "order_confirmation",
})


def is_non_posting_document_type(value: Any) -> bool:
    return str(value or "").strip().lower() in NON_POSTING_DOCUMENT_TYPES


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def _evidence_label(pattern: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", pattern.lower()).strip("_")[:80]


def _select_candidate(candidates: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    priority = {
        "credit_note": 6,
        "government_correspondence": 7,
        "insurance_policy": 7,
        "order_confirmation": 5,
        "bank_statement": 4,
        "estimate": 3,
        "receipt": 2,
        "vendor_invoice": 1,
    }
    candidates = list(candidates)
    if not candidates:
        return {}
    return max(
        candidates,
        key=lambda item: (
            float(item.get("confidenceScore") or 0.0),
            priority.get(str(item.get("documentType") or ""), 0),
        ),
    )
