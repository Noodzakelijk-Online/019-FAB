import os
import tempfile
import unittest

from src.data_entry.posting_approval import PostingApprovalService
from src.data_entry.safe_posting import SafePostingService
from src.reports.reporting_service import ReportingService
from src.storage.database import Database


class TestReportingAndPostingApproval(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.config = {
            "database_path": os.path.join(self.tempdir.name, "fab.sqlite3"),
            "report_export_dir": os.path.join(self.tempdir.name, "reports"),
        }
        self.database = Database(self.config)
        self.database.upsert_document({"id": "doc-1", "source": "test", "original_filename": "receipt.pdf"})

    def tearDown(self):
        self.tempdir.cleanup()

    def test_reporting_summary_and_export(self):
        reporting = ReportingService(self.config)
        summary = reporting.summary()
        self.assertIn("document_states", summary)
        export = reporting.export_table_csv("documents")
        self.assertEqual(export["status"], "success")
        self.assertTrue(os.path.exists(export["path"]))

    def test_posting_approval_flow(self):
        safe_posting = SafePostingService(self.config)
        dry_run = safe_posting.create_dry_run(
            {
                "document_id": "doc-1",
                "category": "A",
                "target_system": "mijngeldzaken",
                "confidence_score": 0.99,
                "extracted_data": {
                    "vendor_name": "Vendor",
                    "transaction_date": "2026-06-05",
                    "total_amount": 10.0,
                    "currency": "EUR",
                },
            },
            "mijngeldzaken",
        )
        approval = PostingApprovalService(self.config)
        approved = approval.approve_attempt(dry_run["posting_attempt_id"], reason="Looks correct")
        self.assertEqual(approved["status"], "approved")
        rejected = approval.reject_attempt(dry_run["posting_attempt_id"], reason="Changed mind")
        self.assertEqual(rejected["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
