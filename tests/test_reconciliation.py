import unittest

from src.reconciliation.automated_reconciliation import AutomatedReconciliation


class TestAutomatedReconciliation(unittest.TestCase):
    def test_matches_localized_negative_bank_amount(self):
        reconciliation = AutomatedReconciliation(
            {
                "reconciliation_match_threshold": 0.9,
                "reconciliation_amount_tolerance": 0.01,
            }
        )

        results = reconciliation.reconcile(
            [
                {
                    "id": "tx-1",
                    "amount": "-EUR 1.234,56",
                    "date": "2026-06-05T14:30:00+02:00",
                    "description": "Cafe Belgie",
                }
            ],
            [
                {
                    "document_id": "doc-1",
                    "extracted_data": {
                        "total_amount": "1234.56",
                        "transaction_date": "05-06-2026",
                        "vendor_name": "Cafe Belgie",
                    },
                }
            ],
        )

        match = next(result for result in results if result["type"] == "match")
        self.assertEqual(match["document_id"], "doc-1")
        self.assertEqual(match["amount_difference"], 0.0)
        self.assertEqual(match["confidence_score"], 1.0)

    def test_selects_best_vendor_match_for_same_date_and_amount(self):
        reconciliation = AutomatedReconciliation({"reconciliation_match_threshold": 0.9})
        documents = [
            {
                "document_id": "doc-other",
                "extracted_data": {
                    "total_amount": 42.5,
                    "transaction_date": "2026-06-05",
                    "vendor_name": "Unrelated Supplier",
                },
            },
            {
                "document_id": "doc-best",
                "extracted_data": {
                    "total_amount": 42.5,
                    "transaction_date": "2026-06-05",
                    "vendor_name": "Office Depot",
                },
            },
        ]

        results = reconciliation.reconcile(
            [
                {
                    "id": "tx-2",
                    "amount": -42.5,
                    "date": "2026-06-05",
                    "counterparty": "Office Depot",
                }
            ],
            documents,
        )

        match = next(result for result in results if result["type"] == "match")
        self.assertEqual(match["document_id"], "doc-best")
        self.assertEqual(match["confidence_score"], 1.0)

    def test_applies_configured_date_tolerance(self):
        reconciliation = AutomatedReconciliation(
            {
                "reconciliation_match_threshold": 0.9,
                "reconciliation_date_tolerance_days": 2,
            }
        )

        results = reconciliation.reconcile(
            [{"id": "tx-3", "amount": 25, "date": "2026-06-07"}],
            [{"document_id": "doc-3", "total_amount": 25, "transaction_date": "2026-06-05"}],
        )

        self.assertEqual(next(result for result in results if result["type"] == "match")["document_id"], "doc-3")

    def test_malformed_amounts_remain_unmatched_without_crashing(self):
        reconciliation = AutomatedReconciliation({})

        results = reconciliation.reconcile(
            [{"id": "tx-invalid", "amount": "not-an-amount", "date": "2026-06-05"}],
            [{"document_id": "doc-invalid", "total_amount": "unknown", "transaction_date": "2026-06-05"}],
        )

        self.assertEqual(
            [result["type"] for result in results],
            ["unmatched_bank_transaction", "unmatched_document"],
        )


if __name__ == "__main__":
    unittest.main()
