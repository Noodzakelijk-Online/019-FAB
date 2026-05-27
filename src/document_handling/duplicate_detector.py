import hashlib
import re
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, Optional


class DuplicateDetector:
    """Detect duplicate financial documents with strict and fuzzy matching."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.similarity_threshold = float(self.config.get("duplicate_similarity_threshold", 0.9))
        self.amount_tolerance = float(self.config.get("duplicate_amount_tolerance", 0.02))

    def build_fingerprint(self, document: Dict[str, Any]) -> str:
        extracted = document.get("extracted_data", document)
        vendor = self._normalize(extracted.get("vendor_name") or document.get("vendor_name"))
        date = self._normalize(str(extracted.get("transaction_date") or extracted.get("date") or ""))
        amount = self._normalize_amount(extracted.get("total_amount") or extracted.get("amount"))
        tax = self._normalize_amount(extracted.get("vat_amount") or extracted.get("taxes"))
        invoice_number = self._normalize(
            extracted.get("invoice_number")
            or extracted.get("receipt_number")
            or extracted.get("order_number")
            or ""
        )
        filename = self._normalize(document.get("original_filename") or document.get("filename") or "")

        fingerprint_source = "|".join([vendor, date, amount, tax, invoice_number, filename])
        return hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()

    def is_duplicate(
        self,
        document: Dict[str, Any],
        existing_documents: Iterable[Dict[str, Any]],
    ) -> Dict[str, Any]:
        new_fingerprint = self.build_fingerprint(document)
        for existing in existing_documents:
            if new_fingerprint == existing.get("duplicate_fingerprint") or new_fingerprint == self.build_fingerprint(existing):
                return {
                    "is_duplicate": True,
                    "confidence_score": 1.0,
                    "reason": "exact_fingerprint_match",
                    "matched_document_id": existing.get("document_id") or existing.get("id"),
                }

            fuzzy_score = self.similarity_score(document, existing)
            if fuzzy_score >= self.similarity_threshold:
                return {
                    "is_duplicate": True,
                    "confidence_score": round(fuzzy_score, 4),
                    "reason": "fuzzy_document_match",
                    "matched_document_id": existing.get("document_id") or existing.get("id"),
                }

        return {
            "is_duplicate": False,
            "confidence_score": 0.0,
            "reason": "no_duplicate_found",
            "matched_document_id": None,
            "duplicate_fingerprint": new_fingerprint,
        }

    def annotate(self, document: Dict[str, Any]) -> Dict[str, Any]:
        document = dict(document)
        document["duplicate_fingerprint"] = self.build_fingerprint(document)
        return document

    def similarity_score(self, left: Dict[str, Any], right: Dict[str, Any]) -> float:
        left_data = left.get("extracted_data", left)
        right_data = right.get("extracted_data", right)

        vendor_score = self._string_similarity(
            left_data.get("vendor_name") or left.get("vendor_name"),
            right_data.get("vendor_name") or right.get("vendor_name"),
        )
        date_score = 1.0 if self._normalize(str(left_data.get("transaction_date", ""))) == self._normalize(str(right_data.get("transaction_date", ""))) else 0.0
        amount_score = self._amount_similarity(
            left_data.get("total_amount") or left_data.get("amount"),
            right_data.get("total_amount") or right_data.get("amount"),
        )
        text_score = self._string_similarity(left.get("ocr_text", ""), right.get("ocr_text", ""))

        weighted_score = (
            vendor_score * 0.30
            + date_score * 0.25
            + amount_score * 0.30
            + text_score * 0.15
        )
        return max(0.0, min(1.0, weighted_score))

    @staticmethod
    def _normalize(value: Optional[Any]) -> str:
        if value is None:
            return ""
        value = str(value).lower().strip()
        value = re.sub(r"[^a-z0-9]+", " ", value)
        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _normalize_amount(value: Optional[Any]) -> str:
        if value is None:
            return ""
        try:
            return f"{float(str(value).replace(',', '.')):.2f}"
        except (TypeError, ValueError):
            cleaned = re.sub(r"[^0-9,.]", "", str(value))
            return cleaned.replace(",", ".")

    def _amount_similarity(self, left: Optional[Any], right: Optional[Any]) -> float:
        try:
            left_amount = float(str(left).replace(",", "."))
            right_amount = float(str(right).replace(",", "."))
        except (TypeError, ValueError):
            return self._string_similarity(left, right)

        return 1.0 if abs(left_amount - right_amount) <= self.amount_tolerance else 0.0

    def _string_similarity(self, left: Optional[Any], right: Optional[Any]) -> float:
        left_norm = self._normalize(left)
        right_norm = self._normalize(right)
        if not left_norm and not right_norm:
            return 0.0
        return SequenceMatcher(None, left_norm, right_norm).ratio()
