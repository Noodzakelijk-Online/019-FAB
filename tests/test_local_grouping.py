import os
import tempfile
import unittest

from src.operations.local_grouping import LocalDocumentGroupingService
from src.operations.local_ledger import LocalOperationsLedger


class TestLocalDocumentGroupingService(unittest.TestCase):
    def test_detect_scanner_groups_creates_reviewable_candidate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            first_id = ledger.register_document({
                "source": "local_folder",
                "sourceAccountId": 1,
                "sourceDocumentId": "batch-a-001",
                "originalFilename": "insurance_invoice_page_001.pdf",
                "storagePath": os.path.join(temp_dir, "insurance_invoice_page_001.pdf"),
            })
            second_id = ledger.register_document({
                "source": "local_folder",
                "sourceAccountId": 1,
                "sourceDocumentId": "batch-a-002",
                "originalFilename": "insurance_invoice_page_002.pdf",
                "storagePath": os.path.join(temp_dir, "insurance_invoice_page_002.pdf"),
            })
            ledger.register_document({
                "source": "local_folder",
                "sourceAccountId": 1,
                "sourceDocumentId": "other",
                "originalFilename": "unrelated_receipt.pdf",
            })

            summary = LocalDocumentGroupingService(ledger).detect_scanner_groups()

            self.assertTrue(summary["success"])
            self.assertEqual(summary["groupsCreated"], 1)
            group = ledger.list_document_groups()[0]
            self.assertEqual(group["group_type"], "scanner_batch")
            self.assertEqual(group["status"], "candidate")
            self.assertEqual(group["primary_document_id"], first_id)
            self.assertEqual([member["document_id"] for member in group["members"][:2]], [first_id, second_id])
            self.assertEqual({item["reason"] for item in ledger.list_review_items(status="pending")}, {"document_group_candidate"})
            self.assertEqual(ledger.dashboard_metrics()["open_document_groups"], 1)

            repeat_summary = LocalDocumentGroupingService(ledger).detect_scanner_groups()

            self.assertEqual(repeat_summary["groupsCreated"], 0)
            self.assertEqual(len(ledger.list_document_groups()), 1)
            self.assertEqual(len(ledger.list_review_items(status="pending")), 2)

    def test_manual_merge_and_split_are_audited_and_review_gated(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            first_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "manual-1",
                "originalFilename": "manual_page_1.pdf",
            })
            second_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "manual-2",
                "originalFilename": "manual_page_2.pdf",
            })
            service = LocalDocumentGroupingService(ledger)

            merge = service.merge_documents(
                [first_id, second_id],
                title="Manual two-page document",
                reason="Same scanned invoice.",
                actor="test",
            )

            self.assertTrue(merge["success"])
            self.assertEqual(merge["status"], "needs_review")
            self.assertEqual(merge["documentGroup"]["member_count"], 2)
            group_id = merge["groupId"]

            split = service.split_document_from_group(group_id, second_id, reason="Second page belongs elsewhere.", actor="test")

            self.assertTrue(split["success"])
            self.assertEqual(split["status"], "split")
            self.assertEqual(split["documentGroup"]["member_count"], 1)
            audit_actions = [event["action"] for event in ledger.list_audit_events()]
            self.assertIn("local_grouping.documents_merged_for_review", audit_actions)
            self.assertIn("local_grouping.document_split_from_group", audit_actions)


if __name__ == "__main__":
    unittest.main()
