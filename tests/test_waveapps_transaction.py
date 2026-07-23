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

    def test_credit_note_builds_deposit_that_decreases_expense(self):
        result = build_expense_transaction_input(
            self._document(
                document_type="credit_note",
                extracted_data={
                    "document_type": "credit_note",
                    "description": "Supplier refund",
                    "total_amount": -42.50,
                    "transaction_date": "2026-07-10",
                    "line_items": [{
                        "description": "Returned paper",
                        "amount": -42.50,
                        "category": "Business",
                    }],
                },
            ),
            business_id="business-1",
            anchor_account_id="anchor-1",
            category_mapping={"Business": "Office Supplies"},
            category_account_ids={"Office Supplies": "expense-1"},
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["input"]["anchor"], {
            "accountId": "anchor-1",
            "amount": 42.5,
            "direction": "DEPOSIT",
        })
        self.assertEqual(result["input"]["lineItems"], [{
            "accountId": "expense-1",
            "amount": 42.5,
            "balance": "DECREASE",
        }])

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

    def test_default_account_cannot_hide_an_unmapped_category(self):
        result = build_expense_transaction_input(
            self._document(),
            business_id="business-1",
            anchor_account_id="anchor-1",
            category_mapping={},
            category_account_ids={"Office Supplies": "expense-1"},
            default_category_account_id="fallback-expense",
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["missingFields"], ["categoryAccountId"])

    def test_preserves_balanced_multi_category_line_items(self):
        document = self._document(extracted_data={
            "description": "Office order",
            "total_amount": "42.50",
            "transaction_date": "2026-07-10",
            "line_items": [
                {"description": "Paper", "amount": "30.00", "category": "Office Supplies"},
                {"description": "Cloud storage", "amount": "12.50", "category": "Software"},
            ],
        })

        result = build_expense_transaction_input(
            document,
            business_id="business-1",
            anchor_account_id="anchor-1",
            category_mapping={
                "Business": "Office Supplies",
                "Office Supplies": "Office Supplies",
                "Software": "Software",
            },
            category_account_ids={
                "Office Supplies": "expense-office",
                "Software": "expense-software",
            },
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["input"]["lineItems"], [
            {"accountId": "expense-office", "amount": 30.0, "balance": "INCREASE"},
            {"accountId": "expense-software", "amount": 12.5, "balance": "INCREASE"},
        ])

    def test_unbalanced_line_items_require_review(self):
        document = self._document(extracted_data={
            "description": "Office order",
            "total_amount": "42.50",
            "transaction_date": "2026-07-10",
            "line_items": [
                {"description": "Paper", "amount": "30.00", "category": "Business"},
            ],
        })

        result = build_expense_transaction_input(
            document,
            business_id="business-1",
            anchor_account_id="anchor-1",
            category_mapping={"Business": "Office Supplies"},
            category_account_ids={"Office Supplies": "expense-office"},
        )

        self.assertFalse(result["success"])
        self.assertIn("lineItemTotal", result["missingFields"])


if __name__ == "__main__":
    unittest.main()
