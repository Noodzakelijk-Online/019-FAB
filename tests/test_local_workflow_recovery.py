import os
import tempfile
import unittest
from unittest.mock import patch

from src.operations.local_autonomy import LocalAutonomousService
from src.operations.local_connector_intake import LocalConnectorIntakeService
from src.operations.local_ledger import LocalOperationsLedger
from src.operations.local_workflow_recovery import LocalWorkflowRecoveryService


class _Fetcher:
    def __init__(self, error=None):
        self.last_error = error
        self.auth_error = None
        self.last_run = {
            "status": "failed" if error else "completed",
            "fetched": 0,
            "skipped": 0,
            "pages": 1,
        }

    def fetch_documents(self):
        return []


class TestLocalWorkflowRecovery(unittest.TestCase):
    def _connector_config(self, temp_dir):
        credentials_path = os.path.join(temp_dir, "gmail-credentials.json")
        token_path = os.path.join(temp_dir, "gmail-token.pickle")
        for path in (credentials_path, token_path):
            with open(path, "wb") as handle:
                handle.write(b"configured")
        return {
            "gmail_enabled": True,
            "gmail_credentials_file": credentials_path,
            "gmail_token_file": token_path,
            "gmail_attachment_download_dir": temp_dir,
            "google_drive_enabled": False,
            "freshdesk_enabled": False,
            "google_photos_enabled": False,
        }

    def test_restricted_autonomy_rejects_unknown_action(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            service = LocalAutonomousService(ledger, {}, intake_paths=[])

            with self.assertRaisesRegex(ValueError, "Unsupported autonomous action"):
                service.run_cycle(
                    allowed_action_ids=["unknown_action"],
                    dry_run=True,
                )

    def test_connector_recovery_retries_only_failed_source_as_linked_attempt(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            config = self._connector_config(temp_dir)
            failed = LocalConnectorIntakeService(
                ledger,
                config,
                fetcher_factories={"gmail": lambda _config: _Fetcher(RuntimeError("provider down"))},
            ).sync(["gmail"], actor="test")
            service = LocalWorkflowRecoveryService(
                ledger,
                config,
                connector_fetcher_factories={"gmail": lambda _config: _Fetcher()},
            )

            plan = service.plan(failed["workflowRunId"])
            result = service.retry(failed["workflowRunId"], actor="test")
            recovered = ledger.get_workflow_run_with_steps(result["workflowRunId"])

            self.assertEqual(plan["status"], "ready")
            self.assertEqual(plan["retrySources"], ["gmail"])
            self.assertEqual(plan["selectedStepKeys"], ["source:gmail"])
            self.assertTrue(result["success"])
            self.assertEqual(recovered["trigger_source"], "connector_intake_recovery")
            self.assertEqual(
                recovered["recovery_source_workflow_run_id"],
                failed["workflowRunId"],
            )
            self.assertEqual(
                recovered["recovery_root_workflow_run_id"],
                failed["workflowRunId"],
            )
            self.assertEqual(len(recovered["steps"]), 1)
            self.assertEqual(recovered["steps"][0]["status"], "completed")
            self.assertEqual(recovered["steps"][0]["attempt"], 2)
            self.assertEqual(
                recovered["metadata"]["recovery"]["sourceWorkflowRunId"],
                failed["workflowRunId"],
            )
            self.assertEqual(
                recovered["metadata"]["recovery"]["rootWorkflowRunId"],
                failed["workflowRunId"],
            )
            self.assertEqual(
                service.plan(failed["workflowRunId"])["supersededByWorkflowRunId"],
                result["workflowRunId"],
            )

    def test_connector_recovery_excludes_failed_source_that_is_no_longer_ready(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            config = self._connector_config(temp_dir)
            workflow_run_id = ledger.create_workflow_run({
                "status": "failed",
                "triggerSource": "connector_intake",
            })
            for step_order, source in enumerate(("gmail", "google_drive"), start=1):
                ledger.create_workflow_step({
                    "workflowRunId": workflow_run_id,
                    "stepKey": f"source:{source}",
                    "stage": "collect",
                    "status": "failed",
                    "attempt": 1,
                    "stepOrder": step_order,
                })
            service = LocalWorkflowRecoveryService(
                ledger,
                config,
                connector_fetcher_factories={"gmail": lambda _config: _Fetcher()},
            )

            plan = service.plan(workflow_run_id)
            result = service.retry(workflow_run_id, actor="test")
            recovered = ledger.get_workflow_run_with_steps(result["workflowRunId"])

            self.assertEqual(plan["unresolvedSources"], ["gmail", "google_drive"])
            self.assertEqual(plan["retrySources"], ["gmail"])
            self.assertEqual(plan["selectedStepKeys"], ["source:gmail"])
            self.assertEqual(plan["blockedSources"][0]["source"], "google_drive")
            self.assertTrue(result["success"])
            self.assertEqual([step["step_key"] for step in recovered["steps"]], ["source:gmail"])

    def test_autonomy_recovery_runs_only_failed_low_risk_step(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            intake_dir = os.path.join(temp_dir, "sort-out")
            os.makedirs(intake_dir)
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            config = {"fab_autonomy_ignore_health_blocks": True}
            autonomy = LocalAutonomousService(
                ledger,
                config,
                intake_paths=[intake_dir],
            )
            with patch.object(autonomy, "_run_rescan", side_effect=RuntimeError("scan failed")):
                failed = autonomy.run_cycle(
                    include_wave_plan=False,
                    include_wave_sync=False,
                )
            service = LocalWorkflowRecoveryService(
                ledger,
                config,
                intake_paths=[intake_dir],
            )

            plan = service.plan(failed["workflowRunId"])
            result = service.retry(failed["workflowRunId"], actor="test")
            recovered = ledger.get_workflow_run_with_steps(result["workflowRunId"])

            self.assertEqual(plan["retryActionId"], "rescan_intake")
            self.assertTrue(result["success"])
            self.assertEqual(recovered["trigger_source"], "local_autonomous_recovery")
            self.assertEqual(len(recovered["steps"]), 1)
            self.assertEqual(recovered["steps"][0]["step_key"], "rescan_intake")
            self.assertEqual(recovered["steps"][0]["status"], "completed")
            self.assertEqual(recovered["steps"][0]["attempt"], 2)
            self.assertEqual(
                recovered["metadata"]["plan"]["selectedActionIds"],
                ["rescan_intake"],
            )
            self.assertNotIn(
                "execute_approved_exports",
                {step["step_key"] for step in recovered["steps"]},
            )

    def test_high_risk_autonomy_step_requires_action_specific_approval(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            workflow_run_id = ledger.create_workflow_run({
                "status": "failed",
                "triggerSource": "local_autonomous_cycle",
            })
            ledger.create_workflow_step({
                "workflowRunId": workflow_run_id,
                "stepKey": "execute_approved_exports",
                "stage": "export",
                "status": "failed",
                "attempt": 1,
                "metadata": {"risk": "high", "mode": "safe_auto"},
            })

            plan = LocalWorkflowRecoveryService(ledger).plan(workflow_run_id)

            self.assertFalse(plan["canRetry"])
            self.assertEqual(plan["status"], "approval_required")
            self.assertEqual(plan["retryActionId"], "execute_approved_exports")
            self.assertEqual(plan["externalSubmission"], "not_executed")

    def test_autonomy_recovery_prioritizes_failure_over_earlier_skipped_step(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            workflow_run_id = ledger.create_workflow_run({
                "status": "failed",
                "triggerSource": "local_autonomous_cycle",
            })
            ledger.create_workflow_step({
                "workflowRunId": workflow_run_id,
                "stepKey": "rescan_intake",
                "stage": "intake",
                "status": "skipped",
                "stepOrder": 1,
                "metadata": {"risk": "low", "mode": "safe_auto"},
            })
            ledger.create_workflow_step({
                "workflowRunId": workflow_run_id,
                "stepKey": "prepare_master_ledger_projection",
                "stage": "ledger",
                "status": "failed",
                "stepOrder": 2,
                "metadata": {"risk": "low", "mode": "read_only"},
            })

            plan = LocalWorkflowRecoveryService(
                ledger,
                {"fab_autonomy_ignore_health_blocks": True},
            ).plan(workflow_run_id)

            self.assertEqual(plan["retryActionId"], "prepare_master_ledger_projection")
            self.assertEqual(plan["selectedStepKeys"], ["prepare_master_ledger_projection"])

    def test_recovery_lease_prevents_duplicate_concurrent_attempt(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            config = self._connector_config(temp_dir)
            failed = LocalConnectorIntakeService(
                ledger,
                config,
                fetcher_factories={"gmail": lambda _config: _Fetcher(RuntimeError("provider down"))},
            ).sync(["gmail"], actor="test")
            lease_name = f"workflow_recovery:{failed['workflowRunId']}"
            lease = ledger.acquire_runtime_lease(lease_name, "other-owner", ttl_seconds=60)
            service = LocalWorkflowRecoveryService(
                ledger,
                config,
                connector_fetcher_factories={"gmail": lambda _config: _Fetcher()},
            )

            result = service.retry(failed["workflowRunId"], actor="test")

            self.assertTrue(lease["acquired"])
            self.assertFalse(result["success"])
            self.assertEqual(result["status"], "already_running")
            self.assertIsNone(result["workflowRunId"])
            self.assertEqual(len(ledger.list_workflow_runs(limit=10)), 1)
            self.assertTrue(ledger.release_runtime_lease(lease_name, "other-owner"))


if __name__ == "__main__":
    unittest.main()
