import unittest

from src.reconciliation.automated_reconciliation import AutomatedReconciliation
from src.validation.receipt_validator import ReceiptValidator


class TestValidationAndReconciliation(unittest.TestCase):
    def test_receipt_validator_accepts_confident_complete_receipt(self):
        validator = ReceiptValidator({})
        result = validator.validate_receipt(
            {
                "extracted_data": {
                    "vendor_name": "Albert Heijn",
                    "transaction_date": "2026-06-05",
                    "total_amount": 4.28,
                    "currency": "EUR",
                    "vat_amount": 0.27,
                },
                "field_confidences": {
                    "vendor_name": 0.90,
                    "transaction_date": 0.90,
                    "total_amount": 0.95,
                    "currency": 0.90,
                    "vat_amount": 0.75,
                },
            }
        )
        self.assertTrue(result["is_valid"])
        self.assertEqual(result["reason"], "")

    def test_receipt_validator_blocks_low_confidence_required_field(self):
        validator = ReceiptValidator({})
        result = validator.validate_receipt(
            {
                "extracted_data": {
                    "vendor_name": "Albert Heijn",
                    "transaction_date": "2026-06-05",
                    "total_amount": 4.28,
                    "currency": "EUR",
                },
                "field_confidences": {
                    "vendor_name": 0.50,
                    "transaction_date": 0.90,
                    "total_amount": 0.95,
                    "currency": 0.90,
                },
            }
        )
        self.assertFalse(result["is_valid"])
        self.assertIn("Low confidence", result["reason"])

    def test_reconciliation_matches_by_amount_date_and_vendor(self):
        reconciler = AutomatedReconciliation({})
        transactions = [
            {"id": "tx-1", "date": "2026-06-05", "description": "Albert Heijn", "amount": -4.28, "currency": "EUR"}
        ]
        documents = [
            {
                "document_id": "doc-1",
                "extracted_data": {
                    "vendor_name": "Albert Heijn",
                    "transaction_date": "2026-06-05",
                    "total_amount": 4.28,
                    "currency": "EUR",
                },
            }
        ]
        results = reconciler.reconcile(transactions, documents)
        self.assertEqual(results[0]["type"], "match")
        self.assertTrue(results[0]["matched"])
        self.assertGreaterEqual(results[0]["match_score"], 0.85)

    def test_missing_receipt_detects_unmatched_negative_transaction(self):
        reconciler = AutomatedReconciliation({})
        alerts = reconciler.detect_missing_receipts(
            [{"id": "tx-2", "date": "2026-06-05", "description": "Unknown Vendor", "amount": -19.99}],
            [],
        )
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["suggested_action"], "Request receipt from vendor or mark as exception with explanation.")


if __name__ == "__main__":
    unittest.main()
