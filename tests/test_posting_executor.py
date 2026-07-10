import os
import tempfile
import unittest

from src.data_entry.posting_approval import PostingApprovalService
from src.data_entry.posting_executor import PostingExecutor
from src.data_entry.safe_posting import SafePostingService
from src.storage.database import Database


class DummySuccessHandler:
    def enter_data(self, categorized_data):
        return {"status": "success", "external_id": "ext-123", "message": "posted"}


class DummyFailureHandler:
    def enter_data(self, categorized_data):
        return {"status": "failure", "message": "failed", "requires_manual_review": True}


class DeferredRateLimitHandler:
    def enter_data(self, categorized_data):
        return {
            "status": "rate_limited",
            "message": "WaveApps dispatch deferred because its configured quota is currently unavailable.",
            "retryable": True,
            "retry_after_seconds": 90,
            "requires_manual_review": False,
            "rate_limit": {"name": "WaveApps", "quotaExhausted": False},
        }


class TestPostingExecutor(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.config = {
            "database_path": os.path.join(self.tempdir.name, "fab.sqlite3"),
            "execute_approved_postings": True,
        }
        self.database = Database(self.config)
        self.database.upsert_document({"id": "doc-1", "source": "test", "original_filename": "receipt.pdf"})

    def tearDown(self):
        self.tempdir.cleanup()

    def _create_approved_attempt(self, target_system="mijngeldzaken"):
        dry_run = SafePostingService(self.config).create_dry_run(
            {
                "document_id": "doc-1",
                "category": "A",
                "target_system": target_system,
                "confidence_score": 0.99,
                "extracted_data": {
                    "vendor_name": "Vendor",
                    "transaction_date": "2026-06-05",
                    "total_amount": 10.0,
                    "currency": "EUR",
                },
            },
            target_system,
        )
        PostingApprovalService(self.config).approve_attempt(dry_run["posting_attempt_id"], reason="Approved for test")
        return dry_run["posting_attempt_id"]

    def test_executes_approved_attempt_successfully(self):
        attempt_id = self._create_approved_attempt()
        executor = PostingExecutor(self.config, handlers={"mijngeldzaken": DummySuccessHandler()})

        result = executor.execute_attempt(attempt_id)

        self.assertEqual(result["status"], "posted")
        attempt = self.database.fetch_one("SELECT * FROM posting_attempts WHERE id = ?", (attempt_id,))
        self.assertEqual(attempt["status"], "posted")
        self.assertEqual(attempt["external_id"], "ext-123")

    def test_failed_execution_creates_manual_review(self):
        attempt_id = self._create_approved_attempt()
        executor = PostingExecutor(self.config, handlers={"mijngeldzaken": DummyFailureHandler()})

        result = executor.execute_attempt(attempt_id)

        self.assertEqual(result["status"], "posting_failed")
        review = self.database.fetch_one("SELECT * FROM manual_review_items WHERE document_id = ?", ("doc-1",))
        self.assertEqual(review["reason"], "posting_execution_failed")

    def test_execution_respects_disabled_flag(self):
        disabled_config = dict(self.config)
        disabled_config["execute_approved_postings"] = False
        attempt_id = self._create_approved_attempt()
        executor = PostingExecutor(disabled_config, handlers={"mijngeldzaken": DummySuccessHandler()})

        result = executor.execute_attempt(attempt_id)

        self.assertEqual(result["status"], "skipped")

    def test_rate_limited_execution_is_deferred_without_failure_or_manual_review(self):
        attempt_id = self._create_approved_attempt(target_system="waveapps_business")
        executor = PostingExecutor(self.config, handlers={"waveapps_business": DeferredRateLimitHandler()})

        result = executor.execute_attempt(attempt_id)

        self.assertEqual(result["status"], "posting_deferred")
        self.assertEqual(result["defer_reason"], "rate_limited")
        attempt = self.database.fetch_one("SELECT * FROM posting_attempts WHERE id = ?", (attempt_id,))
        self.assertEqual(attempt["status"], "posting_deferred")
        retry = self.database.fetch_one(
            "SELECT * FROM retry_queue WHERE entity_type = ? AND entity_id = ? AND operation = ?",
            ("posting_attempt", str(attempt_id), "execute_posting"),
        )
        self.assertEqual(retry["status"], "pending")
        self.assertEqual(retry["attempt_count"], 0)
        self.assertEqual(self.database.fetch_all("SELECT * FROM manual_review_items"), [])
        audit_actions = [entry["action"] for entry in self.database.fetch_all("SELECT * FROM audit_log")]
        self.assertIn("retry_deferred", audit_actions)
        self.assertIn("execution_deferred_rate_limit", audit_actions)


if __name__ == "__main__":
    unittest.main()
