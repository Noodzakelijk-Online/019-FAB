import os
import tempfile
import unittest

from src.data_entry.posting_approval import PostingApprovalService
from src.data_entry.posting_executor import PostingExecutor
from src.data_entry.safe_posting import SafePostingService
from src.queue.retry_manager import RetryManager
from src.storage.database import Database


class AlwaysFailHandler:
    def enter_data(self, categorized_data):
        return {"status": "failure", "message": "temporary external failure", "requires_manual_review": True}


class AlwaysSuccessHandler:
    def enter_data(self, categorized_data):
        return {"status": "success", "external_id": "posted-123"}


class TestRetryAndHardenedPostingExecutor(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.config = {
            "database_path": os.path.join(self.tempdir.name, "fab.sqlite3"),
            "execute_approved_postings": True,
            "retry_max_attempts": 2,
            "retry_base_delay_seconds": 1,
        }
        self.database = Database(self.config)
        self.database.upsert_document({"id": "doc-1", "source": "test", "original_filename": "receipt.pdf"})

    def tearDown(self):
        self.tempdir.cleanup()

    def _approved_attempt(self):
        dry_run = SafePostingService(self.config).create_dry_run(
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
        PostingApprovalService(self.config).approve_attempt(dry_run["posting_attempt_id"], reason="Approved for execution")
        return dry_run["posting_attempt_id"]

    def test_retry_manager_schedules_then_dead_letters(self):
        retry = RetryManager(self.config)
        first = retry.schedule_retry("posting_attempt", "1", "execute_posting", "first failure")
        second = retry.schedule_retry("posting_attempt", "1", "execute_posting", "second failure")

        self.assertEqual(first["status"], "retry_scheduled")
        self.assertEqual(second["status"], "dead_lettered")
        dead = self.database.fetch_one("SELECT * FROM dead_letter_queue WHERE entity_id = ?", ("1",))
        self.assertIsNotNone(dead)

    def test_failed_executor_schedules_retry(self):
        attempt_id = self._approved_attempt()
        executor = PostingExecutor(self.config, handlers={"mijngeldzaken": AlwaysFailHandler()})
        result = executor.execute_attempt(attempt_id)

        self.assertEqual(result["status"], "posting_failed")
        retry = self.database.fetch_one("SELECT * FROM retry_queue WHERE entity_id = ?", (str(attempt_id),))
        self.assertIsNotNone(retry)
        self.assertEqual(retry["operation"], "execute_posting")

    def test_successful_executor_completes_retry(self):
        attempt_id = self._approved_attempt()
        retry = RetryManager(self.config)
        retry.schedule_retry("posting_attempt", str(attempt_id), "execute_posting", "temporary issue")

        executor = PostingExecutor(self.config, handlers={"mijngeldzaken": AlwaysSuccessHandler()})
        result = executor.execute_attempt(attempt_id, force=True)

        self.assertEqual(result["status"], "posted")
        queue_row = self.database.fetch_one("SELECT * FROM retry_queue WHERE entity_id = ?", (str(attempt_id),))
        self.assertEqual(queue_row["status"], "completed")


if __name__ == "__main__":
    unittest.main()
