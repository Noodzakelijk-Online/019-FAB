import os
import tempfile
import unittest

from src.exceptions.exception_memory import ExceptionMemory
from src.missing_receipts.follow_up_manager import MissingReceiptFollowUpManager
from src.storage.database import Database


class TestExceptionMemoryAndFollowUps(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.config = {"database_path": os.path.join(self.tempdir.name, "fab.sqlite3")}
        Database(self.config)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_exception_memory_approves_and_finds_exception(self):
        memory = ExceptionMemory(self.config)
        context = {"transaction_id": "tx-1", "amount": -10.00, "description": "Known exception"}

        approved = memory.approve_exception("missing_receipt", context, "Valid exception explained by user")

        self.assertTrue(approved["active"])
        self.assertTrue(memory.is_approved("missing_receipt", context))
        stored = memory.get_exception("missing_receipt", context)
        self.assertEqual(stored["explanation"], "Valid exception explained by user")

    def test_missing_receipt_follow_up_creation_and_completion(self):
        manager = MissingReceiptFollowUpManager(self.config)
        alert = {
            "transaction": {
                "id": "tx-2",
                "date": "2026-06-05",
                "description": "Vendor X",
                "amount": -15.99,
                "currency": "EUR",
            }
        }

        created = manager.create_or_update_follow_up(alert)
        self.assertEqual(created["status"], "created")
        self.assertIn("Vendor X", created["message_template"])

        updated = manager.create_or_update_follow_up(alert)
        self.assertEqual(updated["status"], "updated")

        completed = manager.mark_completed("tx-2")
        self.assertTrue(completed)

    def test_missing_receipt_follow_up_can_be_stopped(self):
        manager = MissingReceiptFollowUpManager(self.config)
        alert = {"transaction": {"id": "tx-3", "description": "Vendor Y", "amount": -1.00}}
        manager.create_or_update_follow_up(alert)

        stopped = manager.stop_follow_up("tx-3", "No receipt needed")
        self.assertTrue(stopped)


if __name__ == "__main__":
    unittest.main()
