import hashlib
import re
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, Optional, Tuple


class DuplicateDetector:
    """Detect duplicate financial documents with strict and fuzzy matching."""

    REFERENCE_FIELDS = (
        "invoice_number",
        "receipt_number",
        "order_number",
        "transaction_reference",
    )
    OCR_REFERENCE_PATTERNS = {
        "invoice_number": (
            r"\binvoice\s+(?:no|number)\b\s*[:#-]?\s*"
            r"(?P<ref>[A-Z0-9][A-Z0-9\-/]{3,})",
            r"\bfactuurnummer\b\s*[:#-]?\s*"
            r"(?P<ref>[A-Z0-9][A-Z0-9\-/]{3,})",
        ),
        "receipt_number": (
            r"\breceipt(?:\s+(?:no|number))?\b\s*[:#-]?\s*"
            r"(?P<ref>[A-Z0-9][A-Z0-9\-/]{3,})",
            r"\b(?:bon|kassabon)(?:\s*(?:nr|nummer))?\b\s*[:#-]?\s*"
            r"(?P<ref>[A-Z0-9][A-Z0-9\-/]{3,})",
        ),
        "order_number": (
            r"\border(?:\s+(?:no|number))\b\s*[:#-]?\s*"
            r"(?P<ref>[A-Z0-9][A-Z0-9\-/]{3,})",
            r"\b(?:order|bestel)(?:nummer|\s*(?:nr|nummer))\b\s*[:#-]?\s*"
            r"(?P<ref>[A-Z0-9][A-Z0-9\-/]{3,})",
        ),
        "transaction_reference": (
            r"\b(?:transactie|transaction)"
            r"(?:\s*(?:nr|no|number|nummer|id))?\.?\s*[:#-]?\s*"
            r"(?P<ref>[A-Z0-9][A-Z0-9\-/]{3,})",
            r"\bmerchant\s+ref\.?\s*[:#-]?\s*"
            r"(?P<ref>[A-Z0-9][A-Z0-9\-/]{3,})",
        ),
    }

    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.similarity_threshold = self._bounded_float(
            self.config.get("duplicate_similarity_threshold", 0.9),
            0.9,
            0.0,
            1.0,
        )
        self.amount_tolerance = Decimal(
            str(
                self._bounded_float(
                    self.config.get("duplicate_amount_tolerance", 0.02),
                    0.02,
                    0.0,
                )
            )
        )

    def build_fingerprint(self, document: Dict[str, Any]) -> str:
        evidence = self._identity_evidence(document)
        posting_polarity = self._posting_polarity(document)
        filename = self._normalize(document.get("original_filename") or document.get("filename") or "")

        fingerprint_source = "|".join([
            posting_polarity,
            evidence["vendor"],
            evidence["date"],
            evidence["amount"],
            evidence["tax"],
            evidence["invoice_number"],
            evidence["receipt_number"],
            evidence["order_number"],
            evidence["transaction_reference"],
            filename,
        ])
        return hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()

    def is_duplicate(
        self,
        document: Dict[str, Any],
        existing_documents: Iterable[Dict[str, Any]],
    ) -> Dict[str, Any]:
        new_fingerprint = self.build_fingerprint(document)
        new_evidence = self._identity_evidence(document)
        identity_conflicts = []
        for existing in existing_documents:
            if self._posting_polarity(document) != self._posting_polarity(existing):
                continue
            existing_evidence = self._identity_evidence(existing)
            conflicts = self._identity_conflicts(new_evidence, existing_evidence)
            if conflicts:
                identity_conflicts.append({
                    "document_id": existing.get("document_id") or existing.get("id"),
                    "fields": conflicts,
                })
                continue
            has_exact_evidence = self._supports_exact_match(new_evidence, existing_evidence)
            fingerprint_matches = (
                new_fingerprint == existing.get("duplicate_fingerprint")
                or new_fingerprint == self.build_fingerprint(existing)
            )
            if self._exact_evidence_match(new_evidence, existing_evidence) or (
                has_exact_evidence and fingerprint_matches
            ):
                return {
                    "is_duplicate": True,
                    "confidence_score": 1.0,
                    "reason": "exact_fingerprint_match",
                    "matched_document_id": existing.get("document_id") or existing.get("id"),
                    "matched_identity_fields": self._matching_identity_fields(
                        new_evidence,
                        existing_evidence,
                    ),
                }

            fuzzy_score, comparable_fields = self._similarity_details(document, existing)
            if comparable_fields >= 3 and fuzzy_score >= self.similarity_threshold:
                return {
                    "is_duplicate": True,
                    "confidence_score": round(fuzzy_score, 4),
                    "reason": "fuzzy_document_match",
                    "matched_document_id": existing.get("document_id") or existing.get("id"),
                    "matched_identity_fields": self._matching_identity_fields(
                        new_evidence,
                        existing_evidence,
                    ),
                }

        result = {
            "is_duplicate": False,
            "confidence_score": 0.0,
            "reason": "no_duplicate_found",
            "matched_document_id": None,
            "duplicate_fingerprint": new_fingerprint,
        }
        if identity_conflicts:
            result["identity_conflicts"] = identity_conflicts[:10]
        return result

    def annotate(self, document: Dict[str, Any]) -> Dict[str, Any]:
        document = dict(document)
        document["duplicate_fingerprint"] = self.build_fingerprint(document)
        return document

    def similarity_score(self, left: Dict[str, Any], right: Dict[str, Any]) -> float:
        score, _ = self._similarity_details(left, right)
        return score

    def identity_evidence(self, document: Dict[str, Any]) -> Dict[str, str]:
        """Return the bounded, normalized transaction identity used by the detector."""
        return dict(self._identity_evidence(document))

    def compare_identity_evidence(
        self,
        left: Dict[str, Any],
        right: Dict[str, Any],
    ) -> Dict[str, Any]:
        left_evidence = self._identity_evidence(left)
        right_evidence = self._identity_evidence(right)
        similarity_score, comparable_fields = self._similarity_details(left, right)
        return {
            "left": dict(left_evidence),
            "right": dict(right_evidence),
            "matched_identity_fields": self._matching_identity_fields(
                left_evidence,
                right_evidence,
            ),
            "conflicting_identity_fields": self._identity_conflicts(
                left_evidence,
                right_evidence,
            ),
            "similarity_score": round(similarity_score, 4),
            "comparable_fields": comparable_fields,
        }

    def _similarity_details(
        self,
        left: Dict[str, Any],
        right: Dict[str, Any],
    ) -> Tuple[float, int]:
        left_data = left.get("extracted_data") if isinstance(left.get("extracted_data"), dict) else left
        right_data = right.get("extracted_data") if isinstance(right.get("extracted_data"), dict) else right

        comparisons = []
        self._append_text_comparison(
            comparisons,
            left_data.get("vendor_name") or left.get("vendor_name"),
            right_data.get("vendor_name") or right.get("vendor_name"),
            0.30,
        )
        self._append_exact_comparison(
            comparisons,
            left_data.get("transaction_date") or left_data.get("date"),
            right_data.get("transaction_date") or right_data.get("date"),
            0.25,
        )
        self._append_amount_comparison(
            comparisons,
            left_data.get("total_amount") or left_data.get("amount"),
            right_data.get("total_amount") or right_data.get("amount"),
            0.30,
        )
        self._append_reference_comparison(
            comparisons,
            self._primary_reference(left),
            self._primary_reference(right),
            0.35,
        )
        self._append_reference_comparison(
            comparisons,
            self._transaction_reference(left),
            self._transaction_reference(right),
            0.40,
        )
        self._append_text_comparison(
            comparisons,
            left.get("ocr_text"),
            right.get("ocr_text"),
            0.15,
        )

        total_weight = sum(weight for _, weight in comparisons)
        if not total_weight:
            return 0.0, 0
        weighted_score = sum(score * weight for score, weight in comparisons) / total_weight
        return max(0.0, min(1.0, weighted_score)), len(comparisons)

    @staticmethod
    def _normalize(value: Optional[Any]) -> str:
        if value is None:
            return ""
        value = str(value).lower().strip()
        value = re.sub(r"[^a-z0-9]+", " ", value)
        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _normalize_amount(value: Optional[Any]) -> str:
        amount = DuplicateDetector._parse_amount(value)
        return f"{amount:.2f}" if amount is not None else ""

    def _amount_similarity(self, left: Optional[Any], right: Optional[Any]) -> float:
        left_amount = self._parse_amount(left)
        right_amount = self._parse_amount(right)
        if left_amount is None or right_amount is None:
            return 0.0

        return 1.0 if abs(left_amount - right_amount) <= self.amount_tolerance else 0.0

    def _string_similarity(self, left: Optional[Any], right: Optional[Any]) -> float:
        left_norm = self._normalize(left)
        right_norm = self._normalize(right)
        if not left_norm and not right_norm:
            return 0.0
        return SequenceMatcher(None, left_norm, right_norm).ratio()

    @classmethod
    def _identity_evidence(cls, document: Dict[str, Any]) -> Dict[str, str]:
        extracted = (
            document.get("extracted_data")
            if isinstance(document.get("extracted_data"), dict)
            else document
        )
        return {
            "posting_polarity": cls._posting_polarity(document),
            "vendor": cls._normalize(extracted.get("vendor_name") or document.get("vendor_name")),
            "date": cls._normalize(extracted.get("transaction_date") or extracted.get("date")),
            "amount": cls._normalize_amount(extracted.get("total_amount") or extracted.get("amount")),
            "tax": cls._normalize_amount(extracted.get("vat_amount") or extracted.get("taxes")),
            "invoice_number": cls._document_reference(document, "invoice_number"),
            "receipt_number": cls._document_reference(document, "receipt_number"),
            "order_number": cls._document_reference(document, "order_number"),
            "transaction_reference": cls._transaction_reference(document),
        }

    @classmethod
    def _document_reference(cls, document: Dict[str, Any], field: str) -> str:
        extracted = (
            document.get("extracted_data")
            if isinstance(document.get("extracted_data"), dict)
            else document
        )
        reference = cls._normalize_reference(extracted.get(field))
        if reference:
            return reference
        return cls._ocr_reference(document.get("ocr_text"), field)

    @classmethod
    def _primary_reference(cls, document: Dict[str, Any]) -> str:
        for field in ("invoice_number", "receipt_number", "order_number"):
            reference = cls._document_reference(document, field)
            if reference:
                return reference
        return ""

    @classmethod
    def _transaction_reference(cls, document: Dict[str, Any]) -> str:
        extracted = (
            document.get("extracted_data")
            if isinstance(document.get("extracted_data"), dict)
            else document
        )
        reference = cls._normalize_reference(
            extracted.get("transaction_reference")
            or document.get("transaction_reference")
        )
        if reference:
            return reference
        return cls._ocr_reference(document.get("ocr_text"), "transaction_reference")

    @classmethod
    def _ocr_reference(cls, text: Optional[Any], field: str) -> str:
        for pattern in cls.OCR_REFERENCE_PATTERNS.get(field, ()):
            for match in re.finditer(pattern, str(text or ""), flags=re.IGNORECASE):
                reference = cls._normalize_reference(match.group("ref"))
                if reference:
                    return reference
        return ""

    @classmethod
    def _normalize_reference(cls, value: Optional[Any]) -> str:
        normalized = re.sub(r"[^a-z0-9]", "", cls._normalize(value))
        if len(normalized) < 4 or not any(character.isdigit() for character in normalized):
            return ""
        return normalized

    @staticmethod
    def _supports_exact_match(left: Dict[str, str], right: Dict[str, str]) -> bool:
        if left["posting_polarity"] != right["posting_polarity"]:
            return False
        shared = {key for key in left if left[key] and right[key]}
        return bool(
            set(DuplicateDetector.REFERENCE_FIELDS).intersection(shared)
            or {"vendor", "date", "amount"}.issubset(shared)
        )

    @classmethod
    def _exact_evidence_match(cls, left: Dict[str, str], right: Dict[str, str]) -> bool:
        if left["posting_polarity"] != right["posting_polarity"]:
            return False
        if cls._identity_conflicts(left, right):
            return False
        matching_references = [
            field
            for field in cls.REFERENCE_FIELDS
            if left[field] and left[field] == right[field]
        ]
        corroborating_matches = sum(
            1
            for key in ("vendor", "date", "amount")
            if left[key] and left[key] == right[key]
        )
        if matching_references and corroborating_matches >= 2:
            return True
        if all(
            left[key] and left[key] == right[key]
            for key in ("vendor", "date", "amount")
        ):
            return True

        return False

    @classmethod
    def _identity_conflicts(cls, left: Dict[str, str], right: Dict[str, str]) -> list:
        return [
            field
            for field in cls.REFERENCE_FIELDS
            if left.get(field)
            and right.get(field)
            and cls._references_conflict(left[field], right[field])
        ]

    @staticmethod
    def _references_conflict(left: str, right: str) -> bool:
        if left == right:
            return False
        # A shorter OCR value is commonly a clipped prefix of the same receipt
        # identifier. Only complete, same-length references are strong enough
        # to disprove a duplicate match autonomously.
        return len(left) == len(right)

    @classmethod
    def _matching_identity_fields(cls, left: Dict[str, str], right: Dict[str, str]) -> list:
        return [
            field
            for field in (
                "vendor",
                "date",
                "amount",
                "tax",
                *cls.REFERENCE_FIELDS,
            )
            if left.get(field)
            and left[field] == right.get(field)
        ]

    @classmethod
    def _posting_polarity(cls, document: Dict[str, Any]) -> str:
        extracted = document.get("extracted_data") if isinstance(document.get("extracted_data"), dict) else {}
        document_type = cls._normalize(
            document.get("document_type")
            or document.get("type")
            or extracted.get("document_type")
            or extracted.get("type")
        ).replace(" ", "_")
        return "credit" if document_type == "credit_note" else "standard"

    @staticmethod
    def _parse_amount(value: Optional[Any]) -> Optional[Decimal]:
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))

        text = re.sub(r"[^\d,.\-]", "", str(value).strip())
        if not text or text in {"-", ".", ","}:
            return None
        if "," in text and "." in text:
            if text.rfind(",") > text.rfind("."):
                text = text.replace(".", "").replace(",", ".")
            else:
                text = text.replace(",", "")
        elif "," in text:
            parts = text.split(",")
            text = "".join(parts[:-1]) + "." + parts[-1]
        elif text.count(".") > 1:
            parts = text.split(".")
            text = "".join(parts[:-1]) + "." + parts[-1]
        try:
            return Decimal(text)
        except InvalidOperation:
            return None

    def _append_text_comparison(
        self,
        comparisons: list,
        left: Optional[Any],
        right: Optional[Any],
        weight: float,
    ):
        if self._normalize(left) and self._normalize(right):
            comparisons.append((self._string_similarity(left, right), weight))

    def _append_exact_comparison(
        self,
        comparisons: list,
        left: Optional[Any],
        right: Optional[Any],
        weight: float,
    ):
        left_normalized = self._normalize(left)
        right_normalized = self._normalize(right)
        if left_normalized and right_normalized:
            comparisons.append((1.0 if left_normalized == right_normalized else 0.0, weight))

    def _append_amount_comparison(
        self,
        comparisons: list,
        left: Optional[Any],
        right: Optional[Any],
        weight: float,
    ):
        if self._parse_amount(left) is not None and self._parse_amount(right) is not None:
            comparisons.append((self._amount_similarity(left, right), weight))

    def _append_reference_comparison(
        self,
        comparisons: list,
        left: Optional[Any],
        right: Optional[Any],
        weight: float,
    ):
        left_normalized = self._normalize_reference(left)
        right_normalized = self._normalize_reference(right)
        if not left_normalized or not right_normalized:
            return
        if left_normalized == right_normalized:
            comparisons.append((1.0, weight))
        elif self._references_conflict(left_normalized, right_normalized):
            comparisons.append((0.0, weight))

    @staticmethod
    def _bounded_float(
        value: Any,
        default: float,
        minimum: float,
        maximum: Optional[float] = None,
    ) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return default
        if parsed < minimum or (maximum is not None and parsed > maximum):
            return default
        return parsed
