import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from src.operations.local_api import create_app
from src.operations.local_bookkeeping_records import LocalBookkeepingRecordService
from src.operations.local_compliance import LocalComplianceService
from src.operations.local_exports import EXPORT_APPROVAL_PHRASE, LocalExportAttemptService
from src.operations.local_health import LocalOperationsHealth
from src.operations.local_ledger import LocalOperationsLedger
from src.operations.local_routing import LocalRoutingService
from src.utils.rate_limiter import RateLimiter, reset_all_limiters, set_rate_limiter


class TestLocalOperationsHealth(unittest.TestCase):
    def tearDown(self):
        reset_all_limiters()

    def test_clean_ledger_reports_ok(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))

            health = LocalOperationsHealth(ledger).summarize()

            self.assertEqual(health["status"], "ok")
            self.assertEqual(health["issues"], [])
            self.assertEqual(health["metrics"]["openReviewItems"], 0)

    def test_health_flags_completed_workflow_with_step_errors(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            workflow_run_id = ledger.create_workflow_run({
                "status": "completed_with_errors",
                "triggerSource": "connector_intake",
                "errorMessage": "One source failed",
            })

            health = LocalOperationsHealth(ledger).summarize()

            issue = next(item for item in health["issues"] if item["type"] == "failed_workflow_run")
            self.assertEqual(issue["entityId"], str(workflow_run_id))
            self.assertEqual(health["metrics"]["failedWorkflowRuns"], 1)

    def test_health_flags_failed_and_stale_source_connectors(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            ledger.upsert_source_account({
                "sourceType": "gmail",
                "sourceIdentifier": "me",
                "label": "Gmail",
                "status": "failed",
                "lastScanAt": _hours_ago(1),
            })
            ledger.upsert_source_account({
                "sourceType": "google_drive",
                "sourceIdentifier": "folder-1",
                "label": "Google Drive",
                "status": "ready",
                "lastScanAt": _hours_ago(48),
            })
            ledger.upsert_source_account({
                "sourceType": "freshdesk",
                "sourceIdentifier": "disabled",
                "label": "Freshdesk",
                "status": "disabled",
            })

            health = LocalOperationsHealth(
                ledger,
                {"operations_source_stale_hours": 24},
            ).summarize()

            self.assertEqual(health["status"], "blocked")
            issue_types = {issue["type"] for issue in health["issues"]}
            self.assertIn("source_connector_unavailable", issue_types)
            self.assertIn("stale_source_connector", issue_types)
            self.assertEqual(health["metrics"]["sourceAccounts"], 3)
            self.assertEqual(health["metrics"]["sourceConnectorsUnavailable"], 1)
            self.assertEqual(health["metrics"]["staleSourceConnectors"], 1)
            self.assertTrue(any("Open Sources" in action for action in health["nextActions"]))

    def test_health_flags_stale_supervised_picker_session(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = os.path.join(temp_dir, "fab.sqlite3")
            ledger = LocalOperationsLedger(ledger_path)
            workflow_run_id = ledger.create_workflow_run({
                "status": "awaiting_user_selection",
                "triggerSource": "google_photos_picker",
                "metadata": {
                    "providerSessionId": "picker-session-1",
                    "providerSessionDeleted": False,
                },
            })
            _set_timestamp(
                ledger_path,
                "workflow_runs",
                workflow_run_id,
                "updated_at",
                _hours_ago(48),
            )

            health = LocalOperationsHealth(
                ledger,
                {"operations_source_stale_hours": 24},
            ).summarize()

            issue = next(item for item in health["issues"] if item["type"] == "stale_picker_session")
            self.assertEqual(issue["entityId"], str(workflow_run_id))
            self.assertEqual(health["metrics"]["pickerSessionsNeedingAttention"], 1)
            self.assertTrue(any("Google Photos" in action for action in health["nextActions"]))

    def test_health_flags_picker_work_interrupted_during_collection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = os.path.join(temp_dir, "fab.sqlite3")
            ledger = LocalOperationsLedger(ledger_path)
            workflow_run_id = ledger.create_workflow_run({
                "status": "collecting",
                "triggerSource": "google_photos_picker",
                "metadata": {"providerSessionId": "picker-session-1"},
            })
            _set_timestamp(
                ledger_path,
                "workflow_runs",
                workflow_run_id,
                "updated_at",
                _hours_ago(8),
            )

            health = LocalOperationsHealth(
                ledger,
                {"operations_workflow_stale_hours": 6},
            ).summarize()

            issue = next(item for item in health["issues"] if item["type"] == "stale_picker_session")
            self.assertEqual(issue["details"]["status"], "collecting")
            self.assertEqual(health["metrics"]["pickerSessionsNeedingAttention"], 1)

    def test_health_flags_stale_review_failed_document_and_running_workflow(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = os.path.join(temp_dir, "fab.sqlite3")
            ledger = LocalOperationsLedger(ledger_path)
            stale_time = _hours_ago(72)
            document_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "scan-health-1",
                "originalFilename": "stale.pdf",
                "processingStatus": "needs_review",
            })
            review_id = ledger.create_review_item({
                "documentId": document_id,
                "reason": "manual_check",
                "status": "pending",
            })
            failed_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "scan-health-2",
                "originalFilename": "failed.pdf",
                "processingStatus": "failed",
            })
            run_id = ledger.create_workflow_run({
                "status": "running",
                "triggerSource": "scheduled",
                "startedAt": _hours_ago(12),
            })
            route_id = ledger.create_routing_attempt({
                "documentId": document_id,
                "target": "waveapps",
                "status": "blocked_review",
                "message": "Open review item",
            })
            _set_timestamp(ledger_path, "bookkeeping_documents", document_id, "updated_at", stale_time)
            _set_timestamp(ledger_path, "review_items", review_id, "created_at", stale_time)
            _set_timestamp(ledger_path, "bookkeeping_documents", failed_id, "updated_at", stale_time)
            _set_timestamp(ledger_path, "routing_attempts", route_id, "created_at", stale_time)

            health = LocalOperationsHealth(
                ledger,
                {
                    "operations_review_stale_hours": 24,
                    "operations_document_stale_hours": 24,
                    "operations_workflow_stale_hours": 6,
                },
            ).summarize()

            self.assertEqual(health["status"], "blocked")
            issue_types = {issue["type"] for issue in health["issues"]}
            self.assertIn("stale_review_item", issue_types)
            self.assertIn("stuck_document", issue_types)
            self.assertIn("failed_document", issue_types)
            self.assertIn("routing_block", issue_types)
            self.assertIn("stale_workflow_run", issue_types)
            self.assertEqual(health["metrics"]["routingBlocks"], 1)
            self.assertEqual(health["metrics"]["runningWorkflowRuns"], 1)

    def test_health_flags_stale_and_failed_export_attempts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = os.path.join(temp_dir, "fab.sqlite3")
            ledger = LocalOperationsLedger(ledger_path)
            stale_time = _hours_ago(80)
            document_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "scan-export-health",
                "originalFilename": "export.pdf",
                "processingStatus": "processed",
            })
            pending_export_id = ledger.upsert_export_attempt({
                "documentId": document_id,
                "status": "approval_required",
                "message": "Pending export approval",
                "targetSystem": "waveapps",
            })
            approved_export_id = ledger.upsert_export_attempt({
                "documentId": document_id,
                "status": "approved",
                "message": "Approved export attempt",
                "targetSystem": "waveapps",
            })
            failed_export_id = ledger.upsert_export_attempt({
                "documentId": document_id,
                "status": "failed",
                "message": "Submission failed",
                "targetSystem": "waveapps",
            })

            _set_timestamp(ledger_path, "export_attempts", pending_export_id, "created_at", stale_time)
            _set_timestamp(ledger_path, "export_attempts", pending_export_id, "updated_at", stale_time)
            _set_timestamp(ledger_path, "export_attempts", approved_export_id, "created_at", stale_time)
            _set_timestamp(ledger_path, "export_attempts", approved_export_id, "updated_at", stale_time)
            _set_timestamp(ledger_path, "export_attempts", failed_export_id, "created_at", stale_time)
            _set_timestamp(ledger_path, "export_attempts", failed_export_id, "updated_at", stale_time)

            health = LocalOperationsHealth(
                ledger,
                {
                    "operations_export_approval_stale_hours": 24,
                    "operations_export_approved_stale_hours": 24,
                },
            ).summarize()

            issue_types = {issue["type"] for issue in health["issues"]}
            self.assertIn("stale_export_approval", issue_types)
            self.assertIn("stale_export_approved", issue_types)
            self.assertIn("failed_export_attempt", issue_types)
            self.assertEqual(health["metrics"]["pendingExportApprovals"], 1)
            self.assertEqual(health["metrics"]["approvedExports"], 1)
            self.assertEqual(health["metrics"]["failedExports"], 1)

    def test_health_flags_master_ledger_blockers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            transaction_id = ledger.upsert_bank_transaction({
                "accountIdentifier": "wave-checking",
                "transactionId": "tx-health-master-ledger",
                "transactionDate": "2026-06-28",
                "amount": -42.5,
                "currency": "EUR",
                "description": "Missing receipt transaction",
                "reconciliationStatus": "missing_receipt",
            })
            LocalBookkeepingRecordService(ledger, {}).upsert_from_bank_transaction(transaction_id)

            health = LocalOperationsHealth(ledger).summarize()

            issue_types = {issue["type"] for issue in health["issues"]}
            self.assertEqual(health["status"], "attention")
            self.assertIn("master_ledger_blockers", issue_types)
            self.assertEqual(health["metrics"]["masterLedgerRows"], 1)
            self.assertEqual(health["metrics"]["masterLedgerBlockedRows"], 1)
            self.assertIn("Open the master ledger projection", " ".join(health["nextActions"]))

    def test_api_health_and_dashboard_render_operations_health(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = os.path.join(temp_dir, "fab.sqlite3")
            ledger = LocalOperationsLedger(ledger_path)
            document_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "scan-health-api",
                "originalFilename": "failed.pdf",
                "processingStatus": "failed",
            })
            _set_timestamp(ledger_path, "bookkeeping_documents", document_id, "updated_at", _hours_ago(48))
            app = create_app({"fab_local_ledger_path": ledger_path})
            client = app.test_client()

            health = client.get("/api/health").get_json()
            page = client.get("/")

            self.assertEqual(health["status"], "blocked")
            self.assertEqual(health["operations"]["metrics"]["failedDocuments"], 1)
            self.assertEqual(page.status_code, 200)
            html = page.data.decode("utf-8")
            self.assertIn("Operations Health", html)
            self.assertIn("failed_document", html)

    def test_health_flags_exhausted_downstream_api_quota(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            limiter = set_rate_limiter("waveapps", limiter=RateLimiter(calls_per_day=1, name="WaveApps"))
            limiter.acquire()

            health = LocalOperationsHealth(ledger).summarize()

            self.assertEqual(health["status"], "blocked")
            self.assertEqual(health["metrics"]["apiQuotaExhaustedServices"], 1)
            self.assertTrue(health["rateLimits"]["waveapps"]["quotaExhausted"])
            self.assertIn("api_quota_exhausted", {issue["type"] for issue in health["issues"]})

    def test_health_flags_stuck_atomic_export_claim(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = os.path.join(temp_dir, "fab.sqlite3")
            ledger = LocalOperationsLedger(ledger_path)
            document_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "scan-stuck-export",
                "originalFilename": "receipt.txt",
                "documentType": "receipt",
                "processingStatus": "reviewed",
                "vendorName": "Office Shop",
                "category": "Office Supplies",
                "transactionDate": "2026-07-10",
                "totalAmount": 42.5,
            })
            route = LocalRoutingService(ledger).prepare_document_route(document_id)
            service = LocalExportAttemptService(ledger)
            prepared = service.prepare_from_routing_attempt(route["routingAttemptId"])
            service.approve_attempt(
                prepared["exportAttemptId"],
                actor="tester",
                confirmation=EXPORT_APPROVAL_PHRASE,
            )
            ledger.claim_export_attempt(prepared["exportAttemptId"])
            _set_timestamp(
                ledger_path,
                "export_attempts",
                prepared["exportAttemptId"],
                "updated_at",
                _hours_ago(2),
            )

            health = LocalOperationsHealth(ledger).summarize()

            self.assertEqual(health["metrics"]["executingExports"], 1)
            self.assertIn("stuck_export_execution", {issue["type"] for issue in health["issues"]})
            self.assertIn("verify downstream state", " ".join(health["nextActions"]))

    def test_health_surfaces_due_quota_deferred_exports(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            export_id = ledger.upsert_export_attempt({
                "status": "deferred",
                "externalSubmission": "not_executed",
                "targetSystem": "waveapps_business",
                "message": "Wave quota unavailable.",
                "metadata": {
                    "retry": {
                        "reason": "rate_limited",
                        "attemptCount": 1,
                        "nextRetryAt": _hours_ago(1),
                    }
                },
            })

            health = LocalOperationsHealth(ledger).summarize()

            self.assertEqual(health["metrics"]["deferredExports"], 1)
            self.assertEqual(health["metrics"]["deferredExportsDue"], 1)
            issue = next(
                item for item in health["issues"]
                if item["type"] == "deferred_export_retry_due"
            )
            self.assertEqual(issue["entityId"], str(export_id))
            self.assertIn("approved-export worker", " ".join(health["nextActions"]))

    def test_health_surfaces_wave_mirror_failures_staleness_and_missing_entities(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            ledger.create_wave_sync_run({
                "targetSystem": "waveapps_business",
                "entityTypes": ["customer"],
                "status": "provider_error",
                "startedAt": _hours_ago(2),
                "errorMessage": "Wave unavailable",
            })
            ledger.create_wave_sync_run({
                "targetSystem": "waveapps_personal",
                "entityTypes": ["invoice"],
                "status": "completed",
                "startedAt": _hours_ago(72),
                "finishedAt": _hours_ago(72),
            })
            ledger.upsert_wave_entity({
                "targetSystem": "waveapps_business",
                "entityType": "customer",
                "externalId": "customer-missing",
                "name": "Removed Customer",
                "presenceStatus": "missing_downstream",
            })

            health = LocalOperationsHealth(
                ledger,
                {"wave_entity_sync_stale_hours": 24},
            ).summarize()

            issue_types = {issue["type"] for issue in health["issues"]}
            self.assertIn("failed_wave_entity_sync", issue_types)
            self.assertIn("stale_wave_entity_sync", issue_types)
            self.assertIn("wave_entities_missing_downstream", issue_types)
            self.assertEqual(health["metrics"]["waveEntitySyncRuns"], 2)
            self.assertEqual(health["metrics"]["waveEntities"], 1)
            self.assertEqual(health["metrics"]["waveEntitiesMissingDownstream"], 1)
            self.assertIn("Refresh the Wave entity mirror", " ".join(health["nextActions"]))

    def test_health_surfaces_unsettled_wave_invoice_deadlines(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            today = datetime.now(timezone.utc).date()
            ledger.upsert_wave_entity({
                "targetSystem": "waveapps_business",
                "entityType": "invoice",
                "externalId": "invoice-overdue",
                "name": "INV-OVERDUE",
                "status": "SENT",
                "dueDate": (today - timedelta(days=3)).isoformat(),
                "amount": 125.0,
                "currency": "EUR",
            })
            ledger.upsert_wave_entity({
                "targetSystem": "waveapps_business",
                "entityType": "invoice",
                "externalId": "invoice-due-soon",
                "name": "INV-DUE-SOON",
                "status": "VIEWED",
                "dueDate": (today + timedelta(days=2)).isoformat(),
                "amount": 75.0,
                "currency": "EUR",
            })
            ledger.upsert_wave_entity({
                "targetSystem": "waveapps_business",
                "entityType": "invoice",
                "externalId": "invoice-paid",
                "name": "INV-PAID",
                "status": "PAID",
                "dueDate": (today - timedelta(days=10)).isoformat(),
            })

            health = LocalOperationsHealth(ledger, {"invoice_due_soon_days": 7}).summarize()

            issue_types = [issue["type"] for issue in health["issues"]]
            self.assertEqual(issue_types.count("wave_invoice_overdue"), 1)
            self.assertEqual(issue_types.count("wave_invoice_due_soon"), 1)
            self.assertEqual(health["metrics"]["waveInvoicesOverdue"], 1)
            self.assertEqual(health["metrics"]["waveInvoicesDueSoon"], 1)
            self.assertIn("approve any reminder", " ".join(health["nextActions"]))

    def test_health_surfaces_latest_open_compliance_findings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            ledger.upsert_bookkeeping_record({
                "bankTransactionId": 77,
                "sourceType": "bank_transaction",
                "recordType": "expense",
                "status": "draft",
                "targetSystem": "waveapps_business",
                "targetAccount": "Office",
                "category": "Office",
                "recordDate": "2026-07-05",
                "amount": -10,
                "vatAmount": 12,
                "currency": "EUR",
                "reconciliationStatus": "reconciled",
            })
            LocalComplianceService(ledger).assess(
                from_date="2026-07-01",
                to_date="2026-07-31",
            )

            health = LocalOperationsHealth(ledger).summarize()

            issue_types = {issue["type"] for issue in health["issues"]}
            self.assertIn("compliance_vat_exceeds_gross", issue_types)
            self.assertEqual(health["status"], "blocked")
            self.assertEqual(health["metrics"]["complianceAssessments"], 1)
            self.assertGreater(health["metrics"]["openComplianceFindings"], 0)
            self.assertGreater(health["metrics"]["blockingComplianceFindings"], 0)
            self.assertIn("before filing", " ".join(health["nextActions"]))


def _hours_ago(hours: int) -> str:
    value = datetime.now(timezone.utc) - timedelta(hours=hours)
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _set_timestamp(path: str, table: str, record_id: int, column: str, value: str) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(f"UPDATE {table} SET {column} = ? WHERE id = ?", (value, record_id))
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    unittest.main()
