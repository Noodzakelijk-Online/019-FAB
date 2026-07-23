import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from src.operations.local_connector_intake import (
    CONNECTOR_INTAKE_LEASE_NAME,
    LocalConnectorIntakeService,
)
from src.operations.local_ledger import LocalOperationsLedger
from src.operations.local_workflow_recovery import (
    DEFAULT_INTERRUPTED_RUN_GRACE_SECONDS,
    WORKFLOW_RECOVERY_SCHEDULER_LEASE_NAME,
    LocalWorkflowRecoveryScheduler,
)


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


class TestLocalWorkflowRecoveryScheduler(unittest.TestCase):
    def test_default_interrupted_run_grace_is_fifteen_minutes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))

            scheduler = LocalWorkflowRecoveryScheduler(ledger)

            self.assertEqual(DEFAULT_INTERRUPTED_RUN_GRACE_SECONDS, 900.0)
            self.assertEqual(scheduler.stale_after_seconds, 900.0)

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

    def _failed_connector_run(self, ledger, config):
        return LocalConnectorIntakeService(
            ledger,
            config,
            fetcher_factories={
                "gmail": lambda _config: _Fetcher(RuntimeError("provider unavailable"))
            },
        ).sync(["gmail"], actor="test")

    def test_due_failure_is_retried_as_a_linked_safe_recovery(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            config = {
                **self._connector_config(temp_dir),
                "fab_workflow_recovery_base_delay_seconds": 0,
            }
            failed = self._failed_connector_run(ledger, config)
            scheduler = LocalWorkflowRecoveryScheduler(
                ledger,
                config,
                connector_fetcher_factories={"gmail": lambda _config: _Fetcher()},
            )

            plan = scheduler.plan()
            result = scheduler.run_due(actor="test")

            self.assertEqual(plan["dueCount"], 1)
            self.assertEqual(plan["connectorSourcesHeldBack"], ["gmail"])
            self.assertTrue(result["success"])
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["attempted"], 1)
            recovery_run_id = result["recoveries"][0]["result"]["workflowRunId"]
            recovery_run = ledger.get_workflow_run_with_steps(recovery_run_id)
            self.assertEqual(
                recovery_run["recovery_source_workflow_run_id"],
                failed["workflowRunId"],
            )
            self.assertEqual(recovery_run["steps"][0]["attempt"], 2)
            self.assertTrue(result["runtimeLease"]["released"])

    def test_backoff_holds_failed_connector_out_of_normal_worker_sync(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            config = {
                **self._connector_config(temp_dir),
                "fab_workflow_recovery_base_delay_seconds": 600,
            }
            self._failed_connector_run(ledger, config)
            scheduler = LocalWorkflowRecoveryScheduler(ledger, config)

            plan = scheduler.plan()

            self.assertEqual(plan["dueCount"], 0)
            self.assertEqual(plan["statusCounts"]["deferred"], 1)
            self.assertEqual(plan["connectorSourcesHeldBack"], ["gmail"])
            self.assertGreater(plan["candidates"][0]["delaySeconds"], 0)

    def test_retry_depth_cap_stops_an_unbounded_failure_loop(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            config = {
                **self._connector_config(temp_dir),
                "fab_workflow_recovery_base_delay_seconds": 0,
                "fab_workflow_recovery_max_retries": 3,
            }
            root_workflow_run_id = ledger.create_workflow_run({
                "status": "completed_with_errors",
                "triggerSource": "connector_intake",
            })
            workflow_run_id = ledger.create_workflow_run({
                "status": "failed",
                "triggerSource": "connector_intake_recovery",
                "metadata": {
                    "recovery": {
                        "sourceWorkflowRunId": root_workflow_run_id,
                        "rootWorkflowRunId": root_workflow_run_id,
                        "retryDepth": 3,
                    }
                },
            })
            ledger.create_workflow_step({
                "workflowRunId": workflow_run_id,
                "stepKey": "source:gmail",
                "stage": "collect",
                "status": "failed",
                "attempt": 4,
                "stepOrder": 1,
            })

            plan = LocalWorkflowRecoveryScheduler(ledger, config).plan()

            self.assertEqual(plan["dueCount"], 0)
            self.assertEqual(plan["statusCounts"]["exhausted"], 1)
            self.assertFalse(plan["candidates"][0]["canRun"])
            self.assertEqual(plan["candidates"][0]["retryDepth"], 3)

    def test_stale_run_without_active_lease_is_finalized_before_recovery(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = os.path.join(temp_dir, "fab.sqlite3")
            ledger = LocalOperationsLedger(ledger_path)
            config = {
                **self._connector_config(temp_dir),
                "fab_workflow_recovery_stale_seconds": 60,
                "fab_workflow_recovery_base_delay_seconds": 300,
            }
            workflow_run_id = ledger.create_workflow_run({
                "status": "running",
                "triggerSource": "connector_intake",
            })
            step_id = ledger.create_workflow_step({
                "workflowRunId": workflow_run_id,
                "stepKey": "source:gmail",
                "stage": "collect",
                "status": "running",
                "stepOrder": 1,
            })
            now = datetime.now(timezone.utc)
            old_timestamp = (now - timedelta(minutes=10)).isoformat()
            connection = sqlite3.connect(ledger_path)
            try:
                connection.execute(
                    "UPDATE workflow_runs SET updated_at = ?, started_at = ? WHERE id = ?",
                    (old_timestamp, old_timestamp, workflow_run_id),
                )
                connection.commit()
            finally:
                connection.close()

            result = LocalWorkflowRecoveryScheduler(
                ledger,
                config,
                connector_fetcher_factories={"gmail": lambda _config: _Fetcher()},
            ).run_due(actor="test", now=now)

            self.assertEqual(result["interruptedWorkflowRunIds"], [workflow_run_id])
            self.assertEqual(result["status"], "no_recovery_due")
            self.assertEqual(ledger.get_workflow_run(workflow_run_id)["status"], "failed")
            self.assertEqual(ledger.get_workflow_step(step_id)["status"], "failed")
            self.assertIn(
                "local_workflow_recovery.interrupted_run_finalized",
                [event["action"] for event in ledger.list_audit_events(limit=10)],
            )

    def test_stale_run_with_active_connector_lease_is_left_running(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = os.path.join(temp_dir, "fab.sqlite3")
            ledger = LocalOperationsLedger(ledger_path)
            workflow_run_id = ledger.create_workflow_run({
                "status": "running",
                "triggerSource": "connector_intake",
            })
            old_timestamp = (
                datetime.now(timezone.utc) - timedelta(minutes=10)
            ).isoformat()
            connection = sqlite3.connect(ledger_path)
            try:
                connection.execute(
                    "UPDATE workflow_runs SET updated_at = ?, started_at = ? WHERE id = ?",
                    (old_timestamp, old_timestamp, workflow_run_id),
                )
                connection.commit()
            finally:
                connection.close()
            lease = ledger.acquire_runtime_lease(
                CONNECTOR_INTAKE_LEASE_NAME,
                "active-owner",
                ttl_seconds=600,
            )

            result = LocalWorkflowRecoveryScheduler(
                ledger,
                {"fab_workflow_recovery_stale_seconds": 60},
            ).run_due(actor="test")

            self.assertTrue(lease["acquired"])
            self.assertEqual(result["interruptedWorkflowRunIds"], [])
            self.assertEqual(ledger.get_workflow_run(workflow_run_id)["status"], "running")
            self.assertTrue(
                ledger.release_runtime_lease(CONNECTOR_INTAKE_LEASE_NAME, "active-owner")
            )

    def test_scheduler_does_not_overlap_an_active_recovery_cycle(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            lease = ledger.acquire_runtime_lease(
                WORKFLOW_RECOVERY_SCHEDULER_LEASE_NAME,
                "active-owner",
                ttl_seconds=600,
            )

            result = LocalWorkflowRecoveryScheduler(ledger).run_due(actor="test")

            self.assertTrue(lease["acquired"])
            self.assertFalse(result["success"])
            self.assertEqual(result["status"], "already_running")
            self.assertEqual(result["attempted"], 0)
            self.assertTrue(
                ledger.release_runtime_lease(
                    WORKFLOW_RECOVERY_SCHEDULER_LEASE_NAME,
                    "active-owner",
                )
            )


if __name__ == "__main__":
    unittest.main()
