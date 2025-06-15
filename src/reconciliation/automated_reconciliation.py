from typing import Dict, Any, List

class AutomatedReconciliation:
    """Automates the reconciliation process between bank statements and processed documents."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.match_threshold = self.config.get("reconciliation_match_threshold", 0.9) # Similarity threshold

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
            matched = False
            for doc in processed_documents:
                # Simple matching logic: check date and amount
                # In a real system, this would involve more sophisticated fuzzy matching
                # on description, vendor name, and handling of multiple line items.
                bank_date = bt.get("date")
                bank_amount = bt.get("amount")
                doc_date = doc.get("extracted_data", {}).get("transaction_date")
                doc_amount = doc.get("extracted_data", {}).get("total_amount")

                if bank_date and doc_date and bank_amount and doc_amount:
                    # Convert dates to comparable format (e.g., datetime objects)
                    # For simplicity, assume string comparison for now
                    if str(bank_date) == str(doc_date) and abs(float(bank_amount) - float(doc_amount)) < 0.01:
                        reconciliation_results.append({
                            "type": "match",
                            "bank_transaction": bt,
                            "document": doc,
                            "matched": True
                        })
                        matched_doc_ids.add(doc["document_id"])
                        matched = True
                        break
            
            if not matched:
                reconciliation_results.append({
                    "type": "unmatched_bank_transaction",
                    "bank_transaction": bt,
                    "matched": False
                })
        
        # Identify unmatched documents
        for doc in processed_documents:
            if doc["document_id"] not in matched_doc_ids:
                reconciliation_results.append({
                    "type": "unmatched_document",
                    "document": doc,
                    "matched": False
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
                # Add logic here to filter out transactions that don't need receipts
                # e.g., internal transfers, known recurring payments without receipts
                missing_receipt_alerts.append({
                    "transaction": result["bank_transaction"],
                    "alert_message": "Possible missing receipt for this transaction."
                })
        return missing_receipt_alerts


