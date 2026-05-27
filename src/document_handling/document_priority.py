import re
from typing import Any, Dict, Iterable, List


class DocumentPriorityResolver:
    """Classify and prioritize financial documents from the same order.

    Invoices and receipts are prioritized because they are normally the
    strongest bookkeeping documents. Order confirmations are kept only when
    no invoice or receipt is available for the same order group.
    """

    DEFAULT_PRIORITIES = {
        "invoice": 100,
        "receipt": 100,
        "credit_note": 90,
        "bank_statement": 70,
        "order_confirmation": 40,
        "quote": 20,
        "unknown": 10,
    }

    DOCUMENT_PATTERNS = {
        "invoice": [r"\binvoice\b", r"\bfactuur\b", r"\binvoice\s*no\b", r"\bfactuurnummer\b"],
        "receipt": [r"\breceipt\b", r"\bbon\b", r"\bkassabon\b", r"\bbetaalbewijs\b"],
        "credit_note": [r"\bcredit\s*note\b", r"\bcreditnota\b"],
        "bank_statement": [r"\bbank\s*statement\b", r"\bafschrift\b"],
        "order_confirmation": [r"\border\s*confirmation\b", r"\bbestelbevestiging\b"],
        "quote": [r"\bquote\b", r"\bofferte\b"],
    }

    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.priorities = dict(self.DEFAULT_PRIORITIES)
        self.priorities.update(self.config.get("document_type_priorities", {}))

    def classify_document(self, document: Dict[str, Any]) -> str:
        filename = document.get("original_filename") or document.get("filename") or ""
        ocr_text = document.get("ocr_text") or document.get("text") or ""
        haystack = f"{filename}\n{ocr_text}".lower()

        for document_type, patterns in self.DOCUMENT_PATTERNS.items():
            if any(re.search(pattern, haystack, flags=re.IGNORECASE) for pattern in patterns):
                return document_type

        return document.get("document_type") or "unknown"

    def priority_score(self, document: Dict[str, Any]) -> int:
        document_type = self.classify_document(document)
        return int(self.priorities.get(document_type, self.priorities["unknown"]))

    def group_key(self, document: Dict[str, Any]) -> str:
        extracted = document.get("extracted_data", document)
        order_id = (
            extracted.get("invoice_number")
            or extracted.get("receipt_number")
            or extracted.get("order_number")
            or self._extract_order_reference(document)
        )
        vendor = extracted.get("vendor_name") or document.get("vendor_name") or ""
        date = extracted.get("transaction_date") or extracted.get("date") or ""
        amount = extracted.get("total_amount") or extracted.get("amount") or ""
        return "|".join(str(part).strip().lower() for part in [vendor, order_id, date, amount] if part)

    def select_preferred_documents(self, documents: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        ungrouped: List[Dict[str, Any]] = []

        for document in documents:
            key = self.group_key(document)
            enriched = dict(document)
            enriched["document_type"] = self.classify_document(document)
            enriched["document_priority_score"] = self.priority_score(enriched)
            if key:
                grouped.setdefault(key, []).append(enriched)
            else:
                ungrouped.append(enriched)

        selected = list(ungrouped)
        for group_documents in grouped.values():
            group_documents.sort(key=lambda doc: doc["document_priority_score"], reverse=True)
            top_score = group_documents[0]["document_priority_score"]
            selected.extend([doc for doc in group_documents if doc["document_priority_score"] == top_score])

        return selected

    @staticmethod
    def _extract_order_reference(document: Dict[str, Any]) -> str:
        text = f"{document.get('original_filename', '')}\n{document.get('ocr_text', '')}"
        patterns = [
            r"(?:order|bestel|invoice|factuur)\s*(?:no|nr|number|nummer)?[:#\s-]*([a-z0-9-]{4,})",
            r"\b([A-Z]{2,}-?\d{4,})\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1)
        return ""
