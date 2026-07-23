import os
import tempfile
import unittest

from src.operations.local_categories import fab_category_intents, fab_category_options
from src.operations.local_ledger import LocalOperationsLedger


class TestLocalCategories(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ledger = LocalOperationsLedger(
            os.path.join(self.temp_dir.name, "fab.sqlite3")
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_options_merge_defaults_configuration_and_local_evidence(self):
        self.ledger.register_document({
            "source": "scanner",
            "sourceDocumentId": "receipt-1",
            "originalFilename": "receipt.pdf",
            "documentType": "receipt",
            "category": "Special Local Category",
        })
        self.ledger.register_document({
            "source": "scanner",
            "sourceDocumentId": "evidence-1",
            "originalFilename": "statement.pdf",
            "documentType": "bank_statement",
            "category": "Supporting Evidence",
        })
        self.ledger.upsert_vendor_category_rule({
            "vendorName": "Supplier",
            "category": "Learned Category",
            "targetSystem": "waveapps_business",
            "status": "approved",
        })

        options = fab_category_options(
            self.ledger,
            {
                "operations_fab_category_catalog": "Custom One, Custom Two",
                "waveapps_business_category_account_ids": {
                    "Mapped Category": "account-1",
                },
            },
        )

        self.assertIn("Office Supplies", options)
        self.assertIn("Special Local Category", options)
        self.assertIn("Learned Category", options)
        self.assertIn("Custom One", options)
        self.assertIn("Mapped Category", options)
        self.assertNotIn("Supporting Evidence", options)

    def test_intents_count_only_posting_evidence_for_the_target(self):
        for source_id, target in (
            ("business-1", "waveapps_business"),
            ("personal-1", "waveapps_personal"),
        ):
            self.ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": source_id,
                "originalFilename": f"{source_id}.pdf",
                "documentType": "receipt",
                "category": "Office Supplies",
                "metadata": {"targetSystem": target},
            })

        intents = fab_category_intents(
            self.ledger,
            {},
            target_system="waveapps_business",
        )
        office = next(
            intent for intent in intents
            if intent["category"] == "Office Supplies"
        )

        self.assertTrue(office["inUse"])
        self.assertEqual(office["documentCount"], 1)


if __name__ == "__main__":
    unittest.main()
