import json
import os
import tempfile
import unittest

from src.operations.local_ledger import LocalOperationsLedger
from src.operations.local_wave_setup import LocalWaveSetupService


class TestLocalWaveSetupService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ledger = LocalOperationsLedger(os.path.join(self.temp_dir.name, "fab.sqlite3"))
        self.config = {
            "fab_local_secret_store_path": os.path.join(self.temp_dir.name, "credentials", "secrets.enc"),
            "fab_local_secret_key_path": os.path.join(self.temp_dir.name, "credentials", "secrets.key"),
        }
        self.service = LocalWaveSetupService(self.config)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_connection_becomes_ready_only_after_validated_account_mapping(self):
        saved = self.service.save(
            self.ledger,
            {
                "targetSystem": "waveapps_business",
                "accessToken": "private-wave-token",
                "businessId": "business-1",
            },
            actor="operator-1",
        )

        self.assertEqual(saved["status"], "needs_validation")
        self.assertTrue(saved["accessTokenConfigured"])
        self.assertNotIn("private-wave-token", json.dumps(saved))

        self._record_discovery()
        mapped = self.service.save(
            self.ledger,
            {
                "targetSystem": "waveapps_business",
                "anchorAccountId": "anchor-1",
                "defaultCategoryAccountId": "expense-1",
            },
            actor="operator-1",
        )

        self.assertEqual(mapped["status"], "ready")
        self.assertTrue(mapped["ready"])
        self.assertTrue(mapped["mapping"]["verified"])
        self.assertEqual(mapped["accountOptions"]["anchor"][0]["id"], "anchor-1")
        self.assertEqual(mapped["accountOptions"]["expense"][0]["id"], "expense-1")
        events = self.ledger.list_audit_events(limit=10)
        rendered = json.dumps(events)
        self.assertNotIn("private-wave-token", rendered)
        self.assertIn("local_wave.settings_updated", {event["action"] for event in events})

    def test_mapping_must_come_from_latest_validated_business(self):
        self.service.save(
            self.ledger,
            {"accessToken": "token", "businessId": "business-1"},
            actor="operator",
        )
        self._record_discovery()

        with self.assertRaisesRegex(ValueError, "not present"):
            self.service.save(
                self.ledger,
                {"anchorAccountId": "unknown-account"},
                actor="operator",
            )

    def test_clear_token_disconnects_without_removing_nonsecret_mapping(self):
        self.service.save(
            self.ledger,
            {"accessToken": "token", "businessId": "business-1"},
            actor="operator",
        )

        result = self.service.save(
            self.ledger,
            {"clearAccessToken": True},
            actor="operator",
        )

        self.assertEqual(result["status"], "needs_token")
        self.assertFalse(result["accessTokenConfigured"])
        self.assertEqual(result["businessId"], "business-1")

    def _record_discovery(self):
        self.ledger.record_wave_operation_snapshot({
            "operationId": "wave-account-discovery:test",
            "workflowId": "wave_account_discovery",
            "surface": "chart_of_accounts",
            "actionId": "chart_account_list_read",
            "mode": "read_only",
            "safety": "read_only",
            "status": "read_result_captured",
            "externalSubmission": "not_executed",
            "metadata": {
                "accountDiscovery": {
                    "targetSystem": "waveapps_business",
                    "business": {"id": "business-1", "name": "FAB Test Business"},
                    "accounts": [
                        {"id": "anchor-1", "name": "Current Account", "subtype": {"name": "Cash and Bank", "value": "CASH_AND_BANK"}},
                        {"id": "expense-1", "name": "Office Expenses", "subtype": {"name": "Expense", "value": "EXPENSE"}},
                    ],
                },
            },
        })


if __name__ == "__main__":
    unittest.main()
