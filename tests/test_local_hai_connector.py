import os
import tempfile
import unittest

from src.operations.local_api import create_app
from src.operations.local_hai_connector import LocalHaiConnector
from src.operations.local_ledger import LocalOperationsLedger


class TestLocalHaiConnector(unittest.TestCase):
    def test_manifest_is_discoverable_but_execution_is_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            connector = LocalHaiConnector(ledger, executors={"refresh_notifications": lambda payload, actor: {}})

            manifest = connector.manifest()
            result = connector.execute("request-1", "refresh_notifications")

            self.assertEqual(manifest["status"], "prepared_disabled")
            self.assertEqual(manifest["sourceOfTruth"], "fab_local_ledger")
            self.assertEqual(manifest["transport"], "loopback_local_http")
            self.assertEqual(manifest["authentication"], "loopback_origin_controls")
            self.assertIn("submit_to_wave", manifest["excludedCapabilities"])
            self.assertFalse(result["success"])
            self.assertEqual(result["status"], "connector_disabled")

    def test_execution_requires_allowlist_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            executions = []
            connector = LocalHaiConnector(
                ledger,
                {
                    "fab_hai_connector_enabled": True,
                    "fab_hai_allowed_commands": "refresh_notifications",
                },
                executors={
                    "refresh_notifications": lambda payload, actor: executions.append(actor) or {
                        "status": "refreshed",
                    }
                },
            )

            first = connector.execute("request-2", "refresh_notifications", actor="hai-controller")
            second = connector.execute("request-2", "refresh_notifications", actor="different-actor")
            blocked = connector.execute("request-3", "run_reconciliation")

            self.assertEqual(first["status"], "completed")
            self.assertEqual(second["status"], "already_executed")
            self.assertEqual(second["result"], {"status": "refreshed"})
            self.assertEqual(executions, ["hai-controller"])
            self.assertEqual(blocked["status"], "not_allowed")
            self.assertEqual(
                ledger.find_audit_event(
                    "hai.command.completed",
                    "hai_command_request",
                    "request-2",
                )["details"]["commandId"],
                "refresh_notifications",
            )

    def test_manifest_reports_bearer_transport_when_api_token_is_configured(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            connector = LocalHaiConnector(ledger, {"fab_local_api_token": "configured-secret"})

            manifest = connector.manifest()

            self.assertEqual(manifest["transport"], "authenticated_local_http")
            self.assertEqual(manifest["authentication"], "bearer_token")
            self.assertNotIn("configured-secret", str(manifest))

    def test_payload_validation_rejects_unknown_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            connector = LocalHaiConnector(
                ledger,
                {
                    "fab_hai_connector_enabled": True,
                    "fab_hai_allowed_commands": "run_reconciliation",
                },
                executors={"run_reconciliation": lambda payload, actor: payload},
            )

            result = connector.plan("run_reconciliation", {"bankTransactions": []})

            self.assertEqual(result["status"], "invalid")
            self.assertIn("bankTransactions", result["error"])

    def test_api_exposes_manifest_plan_and_audited_execution(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = os.path.join(temp_dir, "fab.sqlite3")
            app = create_app({
                "fab_local_ledger_path": ledger_path,
                "fab_hai_connector_enabled": True,
                "fab_hai_allowed_commands": "process_imported",
            })
            client = app.test_client()

            manifest = client.get("/api/hai/manifest")
            plan = client.post("/api/hai/commands/plan", json={
                "commandId": "process_imported",
                "payload": {"limit": 1},
            })
            executed = client.post("/api/hai/commands/execute", json={
                "requestId": "api-request-1",
                "commandId": "process_imported",
                "actor": "dashboard-test",
                "payload": {"limit": 1},
            })

            self.assertEqual(manifest.status_code, 200)
            self.assertEqual(len(manifest.get_json()["commands"]), 13)
            self.assertIn(
                "reprocess_review_queue",
                {
                    command["commandId"]
                    for command in manifest.get_json()["commands"]
                },
            )
            resources = {
                item["resourceId"] for item in manifest.get_json()["resources"]
            }
            self.assertEqual(len(resources), 3)
            self.assertIn("google_drive_binary_relay", resources)
            self.assertIn("wave_attachment_work_orders", resources)
            self.assertIn("wave_attachment_binary_readback", resources)
            self.assertEqual(plan.status_code, 200)
            self.assertEqual(plan.get_json()["status"], "ready")
            self.assertEqual(executed.status_code, 200)
            self.assertEqual(executed.get_json()["status"], "completed")
            self.assertEqual(executed.get_json()["externalSubmission"], "not_executed")


if __name__ == "__main__":
    unittest.main()
