import json
import os
import tempfile
import unittest

from src.operations.local_api import create_app
from src.operations.local_exports import LocalExportAttemptService
from src.operations.local_ledger import LocalOperationsLedger
from src.operations.local_mijngeldzaken_control import LocalMijngeldzakenControlService
from src.operations.local_routing import LocalRoutingService


class TestLocalMijngeldzakenControlService(unittest.TestCase):
    def test_overview_models_mijngeldzaken_without_leaking_credentials(self):
        service = LocalMijngeldzakenControlService({
            "mijngeldzaken_username": "person@example.test",
            "mijngeldzaken_password": "mgz-secret",
        })

        overview = service.overview()
        rendered = json.dumps(overview, sort_keys=True)

        self.assertEqual(overview["status"], "modeled")
        self.assertEqual(overview["externalSubmission"], "not_executed")
        self.assertGreaterEqual(overview["summary"]["feature_pages"], 11)
        self.assertGreaterEqual(overview["summary"]["actions"], 55)
        self.assertTrue(overview["credentials"]["usernameConfigured"])
        self.assertTrue(overview["credentials"]["passwordConfigured"])
        self.assertTrue(overview["credentials"]["legacyCredentialsDetected"])
        self.assertTrue(overview["credentials"]["legacyCredentialsIgnored"])
        self.assertTrue(overview["credentials"]["supervisedSessionRequired"])
        self.assertIn("master_ledger_downstream_sync", {workflow["id"] for workflow in overview["workflows"]})
        self.assertNotIn("person@example.test", rendered)
        self.assertNotIn("mgz-secret", rendered)

    def test_workflow_plan_prepares_read_and_safe_draft_operations(self):
        result = LocalMijngeldzakenControlService().plan_workflow({
            "workflowId": "master_ledger_downstream_sync",
            "fromDate": "2026-06-01",
            "toDate": "2026-06-30",
        })

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["externalSubmission"], "not_executed")
        self.assertGreaterEqual(result["operationCount"], 10)
        action_ids = {operation["action_id"] for operation in result["operations"]}
        self.assertIn("transaction_list_read", action_ids)
        self.assertIn("transaction_export_download", action_ids)
        self.assertIn("import_mapping_prepare", action_ids)
        self.assertEqual(result["blockingOperations"], [])
        self.assertTrue(all(operation["safety"] in {"read_only", "safe_draft"} for operation in result["operations"]))

    def test_master_ledger_controls_track_mijngeldzaken_downstream_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            config = {"mijngeldzaken_category_mapping": {"Personal": "Huishouden"}}
            document_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "scan-mgz-control",
                "originalFilename": "groceries.txt",
                "documentType": "receipt",
                "processingStatus": "reviewed",
                "vendorName": "Local Supermarket",
                "category": "Personal",
                "transactionDate": "2026-06-29",
                "totalAmount": 31.25,
                "extractedData": {
                    "vendor_name": "Local Supermarket",
                    "transaction_date": "2026-06-29",
                    "total_amount": 31.25,
                    "description": "Weekly groceries",
                },
                "metadata": {"targetSystem": "mijngeldzaken"},
            })
            route = LocalRoutingService(ledger, config).prepare_document_route(document_id)
            LocalExportAttemptService(ledger, config).prepare_from_routing_attempt(route["routingAttemptId"])

            controls = LocalMijngeldzakenControlService(config).evaluate_master_ledger_controls(ledger)

            self.assertEqual(controls["status"], "awaiting_export_approval")
            self.assertEqual(controls["rowCount"], 1)
            self.assertEqual(controls["readyForApproval"], 1)
            self.assertEqual(controls["blockingCount"], 0)
            self.assertIn("Approval required", {gate["label"] for gate in controls["gates"]})

    def test_api_and_dashboard_expose_mijngeldzaken_control_center(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = os.path.join(temp_dir, "fab.sqlite3")
            app = create_app({
                "fab_local_ledger_path": ledger_path,
                "mijngeldzaken_username": "person@example.test",
                "mijngeldzaken_password": "mgz-secret",
            })
            client = app.test_client()

            overview = client.get("/api/mijngeldzaken")
            self.assertEqual(overview.status_code, 200)
            overview_payload = overview.get_json()
            self.assertEqual(overview_payload["status"], "modeled")
            self.assertIn("masterLedgerControls", overview_payload)
            self.assertNotIn("mgz-secret", json.dumps(overview_payload, sort_keys=True))

            plan = client.post("/api/mijngeldzaken/workflows/plan", json={
                "workflowId": "master_ledger_downstream_sync",
                "fromDate": "2026-06-01",
                "toDate": "2026-06-30",
            })
            self.assertEqual(plan.status_code, 200)
            self.assertEqual(plan.get_json()["status"], "ready")
            self.assertIn("masterLedgerControls", plan.get_json())

            dashboard = client.get("/")
            html = dashboard.get_data(as_text=True)
            self.assertEqual(dashboard.status_code, 200)
            self.assertIn("MijnGeldzaken Control Center", html)
            self.assertIn("Master ledger sync", html)
            self.assertNotIn("mgz-secret", html)


if __name__ == "__main__":
    unittest.main()
