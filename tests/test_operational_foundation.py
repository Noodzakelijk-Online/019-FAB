import os
import tempfile
import unittest

from src.data_entry.safe_posting import SafePostingService
from src.storage.database import Database
from src.workflow.safety_engine import SafetyEngine
from src.workflow.state_machine import DocumentStateMachine, InvalidStateTransition


class TestOperationalFoundation(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.config = {
            "database_path": os.path.join(self.tempdir.name, "fab.sqlite3"),
            "dashboard_access_token": "test-token",
        }

    def tearDown(self):
        self.tempdir.cleanup()

    def test_database_initializes_and_stores_document(self):
        database = Database(self.config)
        database.upsert_document({"id": "doc-1", "source": "test", "original_filename": "receipt.pdf"})
        row = database.fetch_one("SELECT * FROM documents WHERE id = ?", ("doc-1",))
        self.assertEqual(row["current_state"], "received")

    def test_state_machine_blocks_invalid_transition(self):
        self.assertTrue(DocumentStateMachine.can_transition("received", "stored"))
        with self.assertRaises(InvalidStateTransition):
            DocumentStateMachine.validate_transition("received", "posted")

    def test_safety_engine_blocks_missing_fields(self):
        safety = SafetyEngine(self.config)
        result = safety.evaluate_posting_readiness({"extracted_data": {}, "target_system": "mijngeldzaken"})
        self.assertEqual(result["decision"], "manual_review")
        self.assertFalse(result["may_post"])

    def test_safe_posting_creates_idempotent_dry_run(self):
        service = SafePostingService(self.config)
        document = {
            "document_id": "doc-2",
            "category": "A",
            "target_system": "mijngeldzaken",
            "confidence_score": 0.99,
            "extracted_data": {
                "vendor_name": "Vendor",
                "transaction_date": "2026-01-01",
                "total_amount": 12.34,
                "currency": "EUR",
            },
        }
        first = service.create_dry_run(document, "mijngeldzaken")
        second = service.create_dry_run(document, "mijngeldzaken")
        self.assertEqual(first["status"], "dry_run_created")
        self.assertEqual(second["status"], "existing_attempt")
        self.assertEqual(first["idempotency_key"], second["idempotency_key"])


if __name__ == "__main__":
    unittest.main()
