from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
import re
from typing import Dict, Any, List, Optional, Tuple
import unicodedata

class AutomatedReconciliation:
    """Automates the reconciliation process between bank statements and processed documents."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.match_threshold = float(self.config.get("reconciliation_match_threshold", 0.9))
        self.amount_tolerance = Decimal(
            str(
                self.config.get(
                    "reconciliation_threshold",
                    self.config.get("reconciliation_amount_tolerance", 0.01),
                )
            )
        )
        self.date_tolerance_days = int(self.config.get("reconciliation_date_tolerance_days", 0))
        self.use_absolute_amounts = self._as_bool(
            self.config.get("reconciliation_use_absolute_amounts", True)
        )
        self.ignore_positive_transactions = self._as_bool(
            self.config.get("ignore_positive_transactions_for_missing_receipts", True)
        )

    def _document_id(self, document: Dict[str, Any]) -> str:
        return document.get("document_id") or document.get("id") or document.get("local_path") or str(id(document))

    def _document_payload(self, document: Dict[str, Any]) -> Dict[str, Any]:
        return document.get("extracted_data") or document

    @staticmethod
    def _as_bool(value: Any) -> bool:
        if isinstance(value, str):
            return value.strip().lower() not in {"0", "false", "no", "off", ""}
        return bool(value)

    @staticmethod
    def _amount(value: Any) -> Optional[Decimal]:
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
            text = "".join(parts[:-1]) + "." + parts[-1] if len(parts) > 1 else text
        elif text.count(".") > 1:
            parts = text.split(".")
            text = "".join(parts[:-1]) + "." + parts[-1]

        try:
            return Decimal(text)
        except InvalidOperation:
            return None

    @staticmethod
    def _date(value: Any) -> Optional[date]:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if value is None:
            return None

        text = str(value).strip()
        if not text:
            return None

        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        except ValueError:
            pass

        for date_format in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(text[:10], date_format).date()
            except ValueError:
                continue
        return None

    @staticmethod
    def _normalized_text(value: Any) -> str:
        normalized = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
        return " ".join(re.sub(r"[^a-z0-9]+", " ", normalized.lower()).split())

    @classmethod
    def _vendor_text(cls, data: Dict[str, Any]) -> str:
        for key in ("vendor_name", "merchant", "counterparty", "description", "name"):
            value = cls._normalized_text(data.get(key))
            if value:
                return value
        return ""

    def _match_score(
        self,
        bank_transaction: Dict[str, Any],
        document: Dict[str, Any],
    ) -> Optional[Tuple[float, float]]:
        doc_data = self._document_payload(document)
        bank_amount = self._amount(bank_transaction.get("amount"))
        doc_amount = self._amount(doc_data.get("total_amount") or doc_data.get("amount"))
        if bank_amount is None or doc_amount is None:
            return None

        comparable_bank_amount = abs(bank_amount) if self.use_absolute_amounts else bank_amount
        comparable_doc_amount = abs(doc_amount) if self.use_absolute_amounts else doc_amount
        amount_difference = abs(comparable_bank_amount - comparable_doc_amount)
        if amount_difference > self.amount_tolerance:
            return None

        score = 0.6
        bank_date = self._date(bank_transaction.get("date") or bank_transaction.get("transaction_date"))
        doc_date = self._date(doc_data.get("transaction_date") or doc_data.get("date"))
        if bank_date and doc_date:
            if abs((bank_date - doc_date).days) > self.date_tolerance_days:
                return None
            score += 0.3

        bank_vendor = self._vendor_text(bank_transaction)
        doc_vendor = self._vendor_text(doc_data)
        if bank_vendor and doc_vendor:
            score += 0.1 * SequenceMatcher(None, bank_vendor, doc_vendor).ratio()

        return round(score, 4), float(amount_difference)

    def reconcile(self, bank_transactions: List[Dict[str, Any]], processed_documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Attempts to match bank transactions with processed documents.

        Args:
            bank_transactions: A list of dictionaries, each representing a bank transaction.
            processed_documents: A list of dictionaries, each representing a processed document.

        Returns:
            A list of reconciliation results, indicating matches or unmatched items.
        """
        reconciliation_results = []
        matched_doc_ids = set()

        for bt in bank_transactions:
            best_match = None
            for doc in processed_documents:
                document_id = self._document_id(doc)
                if document_id in matched_doc_ids:
                    continue

                match_result = self._match_score(bt, doc)
                if match_result is None:
                    continue
                confidence_score, amount_difference = match_result
                if confidence_score < self.match_threshold:
                    continue
                if best_match is None or confidence_score > best_match["confidence_score"]:
                    best_match = {
                        "document": doc,
                        "document_id": document_id,
                        "confidence_score": confidence_score,
                        "amount_difference": amount_difference,
                    }

            if best_match:
                reconciliation_results.append({
                    "type": "match",
                    "bank_transaction": bt,
                    "document": best_match["document"],
                    "bank_transaction_id": bt.get("id"),
                    "document_id": best_match["document_id"],
                    "receipt_id": best_match["document_id"],
                    "confidence_score": best_match["confidence_score"],
                    "match_score": best_match["confidence_score"],
                    "match_reason": ["amount/date/vendor matched within configured tolerance"],
                    "amount_difference": best_match["amount_difference"],
                    "matched": True
                })
                matched_doc_ids.add(best_match["document_id"])
            
            else:
                reconciliation_results.append({
                    "type": "unmatched_bank_transaction",
                    "bank_transaction": bt,
                    "matched": False,
                    "match_score": 0.0,
                    "match_reason": ["No document matched this bank transaction above threshold."],
                })
        
        # Identify unmatched documents
        for doc in processed_documents:
            document_id = self._document_id(doc)
            if document_id not in matched_doc_ids:
                reconciliation_results.append({
                    "type": "unmatched_document",
                    "document": doc,
                    "document_id": document_id,
                    "matched": False,
                    "match_score": 0.0,
                    "match_reason": ["No bank transaction matched this document above threshold."],
                })

        return reconciliation_results

    def detect_missing_receipts(self, bank_transactions: List[Dict[str, Any]], processed_documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identifies bank transactions that likely require a missing receipt."""
        # This is a high-level function that would typically be called after reconciliation.
        # It would look for unmatched bank transactions that are not easily explainable
        # (e.g., not internal transfers, not payroll, etc.)
        missing_receipt_alerts = []
        reconciliation_results = self.reconcile(bank_transactions, processed_documents)

        for result in reconciliation_results:
            if result["type"] == "unmatched_bank_transaction":
                amount = self._amount(result.get("bank_transaction", {}).get("amount"))
                if self.ignore_positive_transactions and amount is not None and amount >= 0:
                    continue
                missing_receipt_alerts.append({
                    "transaction": result["bank_transaction"],
                    "alert_message": "Possible missing receipt for this transaction.",
                    "match_score": result.get("match_score", 0.0),
                    "match_reason": result.get("match_reason", []),
                    "suggested_action": "Request receipt from vendor or mark as exception with explanation.",
                })
        return missing_receipt_alerts


