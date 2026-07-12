import os
import tempfile
import unittest
from unittest.mock import patch

from src.data_entry.mijngeldzaken_artifacts import MijngeldzakenArtifactStore
from src.operations.local_exports import EXPORT_APPROVAL_PHRASE, LocalExportAttemptService
from src.operations.local_ledger import LocalOperationsLedger
from src.operations.local_routing import LocalRoutingService
from src.run_approved_postings import run_approved_postings
from src.worker.scheduler import FabWorker


class TestOperationsExportWorker(unittest.TestCase):
    def _config(self, temp_dir):
        return {
            "fab_local_ledger_enabled": True,
            "fab_local_ledger_path": os.path.join(temp_dir, "fab-operations.sqlite3"),
            "fab_local_backup_dir": os.path.join(temp_dir, "backups"),
            "fab_local_report_dir": os.path.join(temp_dir, "reports"),
            "mijngeldzaken_export_dir": os.path.join(temp_dir, "mijngeldzaken-exports"),
            "mijngeldzaken_category_mapping": {"Personal": "Huishouden"},
            "fab_autonomy_execute_approved_exports": True,
            "worker_run_once": True,
            "worker_process_approved_postings": True,
            "worker_process_due_retries": True,
            "worker_generate_scheduled_reports": True,
            "report_schedule_frequency": "monthly",
            "report_schedule_period_mode": "current_year_to_date",
            "worker_process_legacy_postings": False,
        }

    def _prepare_approved_mijngeldzaken_export(self, ledger, config, suffix="1"):
        document_id = ledger.register_document({
            "source": "scanner",
            "sourceDocumentId": f"worker-mgz-{suffix}",
            "originalFilename": f"receipt-{suffix}.txt",
            "documentType": "receipt",
            "processingStatus": "reviewed",
            "vendorName": "Local Supermarket",
            "category": "Personal",
            "transactionDate": "2026-07-10",
            "totalAmount": 31.25,
            "extractedData": {
                "vendor_name": "Local Supermarket",
                "transaction_date": "2026-07-10",
                "total_amount": 31.25,
                "description": "Weekly groceries",
            },
            "metadata": {"targetSystem": "mijngeldzaken"},
        })
        route = LocalRoutingService(ledger, config).prepare_document_route(document_id)
        service = LocalExportAttemptService(ledger, config)
        prepared = service.prepare_from_routing_attempt(route["routingAttemptId"])
        service.approve_attempt(
            prepared["exportAttemptId"],
            actor="tester",
            confirmation=EXPORT_APPROVAL_PHRASE,
        )
        return document_id, prepared["exportAttemptId"]

    def test_worker_uses_operations_ledger_and_does_not_open_legacy_database(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self._config(temp_dir)
            ledger = LocalOperationsLedger(config["fab_local_ledger_path"])
            document_id, export_attempt_id = self._prepare_approved_mijngeldzaken_export(
                ledger,
                config,
            )
            worker = FabWorker(config)

            with patch.object(worker, "install_signal_handlers"), patch(
                "src.worker.scheduler.WorkflowController"
            ) as workflow_controller:
                worker.run()

            self.assertIsNone(worker.database)
            workflow_controller.return_value.run_workflow.assert_called_once()
            attempt = ledger.get_export_attempt(export_attempt_id)
            self.assertEqual(attempt["status"], "supervision_required")
            self.assertEqual(attempt["external_submission"], "not_executed")
            self.assertTrue(os.path.isfile(attempt["metadata"]["supervisedArtifact"]["path"]))
            reviews = ledger.list_review_items(document_id=document_id)
            self.assertEqual(reviews[0]["reason"], "mijngeldzaken_supervision_required")
            audit_actions = {event["action"] for event in ledger.list_audit_events(limit=100)}
            self.assertIn("local_worker.autonomy_cycle", audit_actions)
            self.assertIn("local_autonomy.cycle_completed", audit_actions)
            self.assertIn("local_worker.approved_export_cycle", audit_actions)
            self.assertIn("local_worker.scheduled_report_cycle", audit_actions)
            self.assertIn("local_reporting.scheduled_report_prepared", audit_actions)
            self.assertIn("local_export_attempt.batch_execution_preflight_backup", audit_actions)
            self.assertIn("local_export_attempt.supervision_required", audit_actions)
            self.assertEqual(ledger.list_export_attempts(status="approved"), [])
            self.assertEqual(len(ledger.list_financial_report_runs()), 1)

    def test_worker_stage_failure_does_not_suppress_local_autonomy_or_exports(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self._config(temp_dir)
            worker = FabWorker(config)

            with patch.object(worker, "install_signal_handlers"), patch.object(
                worker,
                "_run_legacy_workflow",
                side_effect=RuntimeError("connector unavailable"),
            ), patch.object(worker, "_run_local_autonomy") as autonomy, patch.object(
                worker,
                "_process_scheduled_reports",
            ) as scheduled_reports, patch.object(
                worker,
                "_process_operations_exports",
            ) as exports:
                worker.run()

            autonomy.assert_called_once()
            scheduled_reports.assert_called_once()
            exports.assert_called_once()
            ledger = LocalOperationsLedger(config["fab_local_ledger_path"])
            audit_actions = [event["action"] for event in ledger.list_audit_events(limit=30)]
            self.assertIn("local_worker.stage_failed", audit_actions)
            self.assertIn("local_worker.cycle_finished_with_error", audit_actions)

    def test_worker_can_disable_legacy_pipeline_for_local_only_operation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self._config(temp_dir)
            config.update({
                "worker_run_legacy_workflow": False,
                "worker_process_approved_postings": False,
                "worker_include_wave_plan": False,
                "worker_include_wave_sync": False,
            })
            worker = FabWorker(config)

            with patch.object(worker, "install_signal_handlers"), patch(
                "src.worker.scheduler.WorkflowController"
            ) as workflow_controller:
                worker.run()

            workflow_controller.assert_not_called()
            ledger = LocalOperationsLedger(config["fab_local_ledger_path"])
            audit_actions = [event["action"] for event in ledger.list_audit_events(limit=30)]
            self.assertIn("local_worker.autonomy_cycle", audit_actions)
            self.assertIn("local_worker.cycle_completed", audit_actions)
            self.assertNotIn("local_worker.stage_failed", audit_actions)

    def test_scheduled_report_failure_does_not_suppress_export_stage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self._config(temp_dir)
            config["worker_run_legacy_workflow"] = False
            worker = FabWorker(config)

            with patch.object(worker, "install_signal_handlers"), patch.object(
                worker,
                "_run_local_autonomy",
            ), patch.object(
                worker,
                "_process_scheduled_reports",
                side_effect=RuntimeError("report disk unavailable"),
            ), patch.object(worker, "_process_operations_exports") as exports:
                worker.run()

            exports.assert_called_once()
            ledger = LocalOperationsLedger(config["fab_local_ledger_path"])
            failed_stages = [
                event for event in ledger.list_audit_events(limit=30)
                if event["action"] == "local_worker.stage_failed"
            ]
            self.assertEqual(failed_stages[0]["details"]["stage"], "scheduled_reports")
            self.assertIn(
                "local_worker.cycle_finished_with_error",
                {event["action"] for event in ledger.list_audit_events(limit=30)},
            )

    def test_manual_runner_uses_operations_ledger_and_respects_execution_flag(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self._config(temp_dir)
            config["fab_autonomy_execute_approved_exports"] = False
            ledger = LocalOperationsLedger(config["fab_local_ledger_path"])
            _, export_attempt_id = self._prepare_approved_mijngeldzaken_export(ledger, config)

            skipped = run_approved_postings(config)
            status_after_skip = ledger.get_export_attempt(export_attempt_id)["status"]
            config["fab_autonomy_execute_approved_exports"] = True
            executed = run_approved_postings(config)

            self.assertEqual(skipped["sourceOfTruth"], "local_operations_ledger")
            self.assertEqual(skipped["execution"]["status"], "skipped")
            self.assertEqual(status_after_skip, "approved")
            self.assertEqual(executed["sourceOfTruth"], "local_operations_ledger")
            self.assertEqual(executed["execution"]["count"], 1)
            self.assertEqual(
                ledger.get_export_attempt(export_attempt_id)["status"],
                "supervision_required",
            )

    def test_artifact_store_sanitizes_filename_and_writes_checksum_bound_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = MijngeldzakenArtifactStore({"mijngeldzaken_export_dir": temp_dir})

            artifact = store.write_text("../private import.csv", "Datum,Bedrag\n2026-07-10,31.25\n")

            self.assertEqual(os.path.dirname(artifact["path"]), os.path.abspath(temp_dir))
            self.assertNotIn("..", artifact["filename"])
            self.assertIn(artifact["sha256"][:12], artifact["filename"])
            self.assertTrue(os.path.isfile(artifact["path"]))
            self.assertEqual(
                [name for name in os.listdir(temp_dir) if name.endswith(".tmp")],
                [],
            )

    def test_approved_batch_does_not_execute_when_preflight_backup_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self._config(temp_dir)
            ledger = LocalOperationsLedger(config["fab_local_ledger_path"])
            _, export_attempt_id = self._prepare_approved_mijngeldzaken_export(ledger, config)
            service = LocalExportAttemptService(ledger, config)

            with patch(
                "src.operations.local_backup.LocalBackupService.create_backup",
                return_value={"success": False, "status": "failed", "error": "disk full"},
            ):
                result = service.process_approved_attempts(actor="test-worker")

            self.assertFalse(result["success"])
            self.assertEqual(result["status"], "pre_execution_backup_failed")
            self.assertEqual(result["count"], 0)
            self.assertEqual(ledger.get_export_attempt(export_attempt_id)["status"], "approved")
            self.assertFalse(os.path.exists(config["mijngeldzaken_export_dir"]))
            audit_actions = {event["action"] for event in ledger.list_audit_events(limit=50)}
            self.assertIn("local_export_attempt.batch_execution_blocked_backup", audit_actions)


if __name__ == "__main__":
    unittest.main()
