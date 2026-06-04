from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple


class AutomatedReconciliation:
    """Reconciles bank transactions with processed FAB documents using scored matching."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.match_threshold = float(self.config.get("reconciliation_match_threshold", 0.85))
        self.possible_match_threshold = float(self.config.get("reconciliation_possible_match_threshold", 0.65))
        self.amount_tolerance = float(self.config.get("reconciliation_amount_tolerance", 0.02))
        self.date_tolerance_days = int(self.config.get("reconciliation_date_tolerance_days", 3))
        self.ignore_positive_transactions = bool(self.config.get("ignore_positive_transactions_for_missing_receipts", True))

    def reconcile(self, bank_transactions: List[Dict[str, Any]], processed_documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        reconciliation_results: List[Dict[str, Any]] = []
        matched_doc_ids = set()

        for transaction in bank_transactions or []:
            best_doc, best_score, best_reasons = self._best_document_match(transaction, processed_documents, matched_doc_ids)
            if best_doc and best_score >= self.match_threshold:
                matched_doc_ids.add(best_doc.get("document_id"))
                reconciliation_results.append(
                    {
                        "type": "match",
                        "bank_transaction": transaction,
                        "document": best_doc,
                        "matched": True,
                        "match_score": round(best_score, 4),
                        "match_reason": best_reasons,
                    }
                )
            elif best_doc and best_score >= self.possible_match_threshold:
                reconciliation_results.append(
                    {
                        "type": "possible_match_requires_review",
                        "bank_transaction": transaction,
                        "document": best_doc,
                        "matched": False,
                        "match_score": round(best_score, 4),
                        "match_reason": best_reasons,
                    }
                )
            else:
                reconciliation_results.append(
                    {
                        "type": "unmatched_bank_transaction",
                        "bank_transaction": transaction,
                        "matched": False,
                        "match_score": round(best_score, 4),
                        "match_reason": best_reasons,
                    }
                )

        for document in processed_documents or []:
            document_id = document.get("document_id")
            if document_id and document_id not in matched_doc_ids:
                reconciliation_results.append(
                    {
                        "type": "unmatched_document",
                        "document": document,
                        "matched": False,
                        "match_score": 0.0,
                        "match_reason": ["No bank transaction matched this document above threshold."],
                    }
                )

        return reconciliation_results

    def detect_missing_receipts(self, bank_transactions: List[Dict[str, Any]], processed_documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        alerts = []
        for result in self.reconcile(bank_transactions, processed_documents):
            if result.get("type") != "unmatched_bank_transaction":
                continue
            transaction = result.get("bank_transaction", {})
            amount = self._to_float(transaction.get("amount"))
            if self.ignore_positive_transactions and amount is not None and amount >= 0:
                continue
            alerts.append(
                {
                    "transaction": transaction,
                    "alert_message": "Possible missing receipt for this transaction.",
                    "match_score": result.get("match_score", 0.0),
                    "match_reason": result.get("match_reason", []),
                    "suggested_action": "Request receipt from vendor or mark as exception with explanation.",
                }
            )
        return alerts

    def detect_conflicts(self, reconciliation_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        conflicts = []
        seen_transactions = {}
        seen_documents = {}
        for result in reconciliation_results:
            if not result.get("matched"):
                continue
            transaction_id = result.get("bank_transaction", {}).get("id")
            document_id = result.get("document", {}).get("document_id")
            if transaction_id in seen_transactions:
                conflicts.append({"type": "transaction_matched_multiple_documents", "transaction_id": transaction_id, "results": [seen_transactions[transaction_id], result]})
            if document_id in seen_documents:
                conflicts.append({"type": "document_matched_multiple_transactions", "document_id": document_id, "results": [seen_documents[document_id], result]})
            seen_transactions[transaction_id] = result
            seen_documents[document_id] = result
        return conflicts

    def _best_document_match(
        self,
        transaction: Dict[str, Any],
        documents: List[Dict[str, Any]],
        already_matched_doc_ids: set,
    ) -> Tuple[Optional[Dict[str, Any]], float, List[str]]:
        best_doc = None
        best_score = 0.0
        best_reasons: List[str] = ["No candidate documents available."]
        for document in documents or []:
            if document.get("document_id") in already_matched_doc_ids:
                continue
            score, reasons = self.match_score(transaction, document)
            if score > best_score:
                best_doc = document
                best_score = score
                best_reasons = reasons
        return best_doc, best_score, best_reasons

    def match_score(self, transaction: Dict[str, Any], document: Dict[str, Any]) -> Tuple[float, List[str]]:
        extracted = document.get("extracted_data", {}) or {}
        reasons: List[str] = []

        amount_score = self._amount_score(transaction.get("amount"), extracted.get("total_amount"))
        reasons.append(f"amount_score={amount_score:.2f}")

        date_score = self._date_score(transaction.get("date"), extracted.get("transaction_date"))
        reasons.append(f"date_score={date_score:.2f}")

        description = transaction.get("description") or transaction.get("counterparty") or ""
        vendor = extracted.get("vendor_name") or document.get("vendor_name") or ""
        description_score = self._string_similarity(description, vendor)
        reasons.append(f"vendor_description_score={description_score:.2f}")

        reference_score = self._reference_score(transaction, extracted)
        reasons.append(f"reference_score={reference_score:.2f}")

        score = amount_score * 0.40 + date_score * 0.25 + description_score * 0.25 + reference_score * 0.10
        return max(0.0, min(1.0, score)), reasons

    def _amount_score(self, transaction_amount: Any, document_amount: Any) -> float:
        tx_amount = self._to_float(transaction_amount)
        doc_amount = self._to_float(document_amount)
        if tx_amount is None or doc_amount is None:
            return 0.0
        if abs(abs(tx_amount) - abs(doc_amount)) <= self.amount_tolerance:
            return 1.0
        difference = abs(abs(tx_amount) - abs(doc_amount))
        denominator = max(abs(tx_amount), abs(doc_amount), 1.0)
        return max(0.0, 1.0 - difference / denominator)

    def _date_score(self, transaction_date: Any, document_date: Any) -> float:
        tx_date = self._parse_date(transaction_date)
        doc_date = self._parse_date(document_date)
        if not tx_date or not doc_date:
            return 0.0
        delta_days = abs((tx_date - doc_date).days)
        if delta_days == 0:
            return 1.0
        if delta_days <= self.date_tolerance_days:
            return max(0.0, 1.0 - (delta_days / (self.date_tolerance_days + 1)))
        return 0.0

    @staticmethod
    def _reference_score(transaction: Dict[str, Any], extracted: Dict[str, Any]) -> float:
        haystack = " ".join(str(transaction.get(key, "")) for key in ["description", "counterparty", "reference", "id"])
        references = [extracted.get("invoice_number"), extracted.get("receipt_number"), extracted.get("order_number")]
        for reference in references:
            if reference and str(reference).lower() in haystack.lower():
                return 1.0
        return 0.0

    @staticmethod
    def _string_similarity(left: Any, right: Any) -> float:
        left_text = str(left or "").lower().strip()
        right_text = str(right or "").lower().strip()
        if not left_text or not right_text:
            return 0.0
        return SequenceMatcher(None, left_text, right_text).ratio()

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            return float(str(value).replace(",", "."))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_date(value: Any):
        if not value:
            return None
        for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"]:
            try:
                return datetime.strptime(str(value), fmt).date()
            except ValueError:
                continue
        return None
