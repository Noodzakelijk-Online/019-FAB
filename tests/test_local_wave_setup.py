import json
import os
import tempfile
import unittest

from src.operations.local_api import create_app
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
        self.assertEqual(saved["activation"]["currentStep"], "validation")
        self.assertTrue(saved["activation"]["canValidate"])
        self.assertFalse(saved["activation"]["canPrepareWaveDrafts"])
        self.assertNotIn("private-wave-token", json.dumps(saved))

        self._record_discovery()
        mapped = self.service.save(
            self.ledger,
            {
                "targetSystem": "waveapps_business",
                "anchorAccountId": "anchor-1",
                "defaultCategoryAccountId": "expense-1",
                "categoryAccountIds": {"Office Expenses": "expense-1"},
            },
            actor="operator-1",
        )

        self.assertEqual(mapped["status"], "ready")
        self.assertTrue(mapped["ready"])
        self.assertEqual(mapped["activation"]["currentStep"], "complete")
        self.assertTrue(mapped["activation"]["canPrepareWaveDrafts"])
        self.assertFalse(mapped["activation"]["canSubmitExternally"])
        self.assertTrue(mapped["mapping"]["verified"])
        self.assertEqual(mapped["accountOptions"]["anchor"][0]["id"], "anchor-1")
        self.assertEqual(mapped["accountOptions"]["expense"][0]["id"], "expense-1")
        self.assertEqual(mapped["mappingCoverage"]["percentage"], 100.0)
        office_intent = next(
            row for row in mapped["categoryIntents"]
            if row["category"] == "Office Expenses"
        )
        self.assertTrue(office_intent["mapped"])
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

    def test_default_expense_account_alone_is_not_autonomy_ready(self):
        self.service.save(
            self.ledger,
            {"accessToken": "token", "businessId": "business-1"},
            actor="operator",
        )
        self._record_discovery()

        result = self.service.save(
            self.ledger,
            {
                "anchorAccountId": "anchor-1",
                "defaultCategoryAccountId": "expense-1",
            },
            actor="operator",
        )

        self.assertEqual(result["status"], "needs_mapping")
        self.assertFalse(result["ready"])
        self.assertIn("categoryAccountIds", result["mapping"]["requiredMissing"])

    def test_unmapped_in_use_category_keeps_connection_out_of_ready_state(self):
        self.service.save(
            self.ledger,
            {"accessToken": "token", "businessId": "business-1"},
            actor="operator",
        )
        self._record_discovery()
        self.ledger.register_document({
            "source": "scanner",
            "sourceDocumentId": "office-document",
            "originalFilename": "office.pdf",
            "processingStatus": "reviewed",
            "documentType": "receipt",
            "category": "Office Supplies",
            "targetSystem": "waveapps_business",
        })

        result = self.service.save(
            self.ledger,
            {
                "anchorAccountId": "anchor-1",
                "categoryAccountIds": {"Other Business Expense": "expense-1"},
            },
            actor="operator",
        )

        self.assertEqual(result["status"], "needs_mapping")
        self.assertFalse(result["ready"])
        self.assertEqual(result["activation"]["currentStep"], "category_mapping")
        self.assertIn("Office Supplies", result["activation"]["nextAction"])
        self.assertEqual(
            result["mappingCoverage"]["unmappedInUseCategories"],
            ["Office Supplies"],
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

    def test_health_reports_unready_wave_core_target_as_attention(self):
        app_config = dict(self.config)
        app_config["fab_local_ledger_path"] = os.path.join(
            self.temp_dir.name,
            "health.sqlite3",
        )
        health = create_app(app_config).test_client().get("/api/health").get_json()

        self.assertEqual(health["operations"]["status"], "ok")
        self.assertEqual(health["status"], "attention")
        self.assertEqual(health["readiness"]["status"], "attention")
        self.assertEqual(
            health["readiness"]["coreTarget"],
            {
                "id": "waveapps_business",
                "label": "Wave - Noodzakelijk Online",
                "status": "needs_token",
                "ready": False,
                "currentStep": "connection",
                "nextAction": "Create a user-owned Wave access token and store it in FAB.",
                "externalSubmission": "not_executed",
            },
        )

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
