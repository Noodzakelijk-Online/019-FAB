import unittest

from src.data_entry.waveapps_transaction import build_expense_transaction_input


class TestWaveappsTransactionInput(unittest.TestCase):
    def _document(self, **overrides):
        document = {
            "document_id": "doc-wave-1",
            "category": "Business",
            "extracted_data": {
                "description": "Office supplies with a quote: \"paper\"",
                "total_amount": "42.505",
                "transaction_date": "2026-07-10",
            },
        }
        document.update(overrides)
        return document

    def test_builds_balanced_withdrawal_using_verified_account_ids(self):
        result = build_expense_transaction_input(
            self._document(),
            business_id="business-1",
            anchor_account_id="anchor-1",
            category_mapping={"Business": "Office Supplies"},
            category_account_ids={"Office Supplies": "expense-1"},
        )

        self.assertTrue(result["success"])
        payload = result["input"]
        self.assertEqual(payload["externalId"], "fab:doc-wave-1")
        self.assertEqual(payload["anchor"], {
            "accountId": "anchor-1",
            "amount": 42.51,
            "direction": "WITHDRAWAL",
        })
        self.assertEqual(payload["lineItems"], [{
            "accountId": "expense-1",
            "amount": 42.51,
            "balance": "INCREASE",
        }])
        self.assertIn('"paper"', payload["description"])

    def test_missing_or_invalid_financial_fields_are_not_dispatchable(self):
        result = build_expense_transaction_input(
            self._document(extracted_data={"total_amount": "0", "transaction_date": "not-a-date"}),
            business_id="business-1",
            anchor_account_id="anchor-1",
            category_mapping={"Business": "Office Supplies"},
            category_account_ids={},
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["missingFields"], ["categoryAccountId", "transactionDate", "totalAmount"])


if __name__ == "__main__":
    unittest.main()
