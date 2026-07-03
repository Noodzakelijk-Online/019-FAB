import os
import tempfile
import unittest

from src.operations.local_api import create_app
from src.operations.local_exceptions import LocalExceptionQueueService
from src.operations.local_exports import EXPORT_APPROVAL_PHRASE, LocalExportAttemptService
from src.operations.local_ledger import LocalOperationsLedger
from src.operations.local_routing import LocalRoutingService


class TestLocalExceptionQueueService(unittest.TestCase):
    def test_exception_queue_enriches_failed_documents_and_exports(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            document_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "failed-doc",
                "originalFilename": "failed.pdf",
                "processingStatus": "failed",
                "metadata": {"processingError": "OCR timeout"},
            })
            export_id = ledger.upsert_export_attempt({
                "documentId": document_id,
                "targetSystem": "waveapps",
                "actionId": "transaction_create",
                "status": "failed",
                "externalSubmission": "failed",
                "message": "Wave rejected the payload",
            })
            workflow_id = ledger.create_workflow_run({
                "status": "failed",
                "triggerSource": "local_autonomous_cycle",
                "errorMessage": "Pipeline crashed",
            })

            payload = LocalExceptionQueueService(ledger).list_exceptions()
            exceptions = {item["id"]: item for item in payload["exceptions"]}
            failed_doc = exceptions[f"failed_document:bookkeeping_document:{document_id}"]
            failed_export = exceptions[f"failed_export_attempt:export_attempt:{export_id}"]
            failed_workflow = exceptions[f"failed_workflow_run:workflow_run:{workflow_id}"]

            self.assertEqual(payload["externalSubmission"], "not_executed")
            self.assertEqual(payload["summary"]["bySeverity"]["high"], 2)
            self.assertEqual(failed_doc["entity"]["processingError"], "OCR timeout")
            self.assertIn("retry_processing", {action["id"] for action in failed_doc["actions"]})
            self.assertEqual(failed_doc["actions"][1]["path"], f"/api/documents/{document_id}/retry-processing")
            self.assertEqual(failed_doc["actions"][1]["dashboardPath"], f"/documents/{document_id}/retry-processing")
            self.assertEqual(failed_export["entity"]["message"], "Wave rejected the payload")
            self.assertEqual(failed_export["entity"]["externalSubmission"], "failed")
            self.assertIn("reject_export_attempt", {action["id"] for action in failed_export["actions"]})
            self.assertEqual(failed_workflow["entity"]["errorMessage"], "Pipeline crashed")

    def test_api_exposes_exception_queue_and_dashboard_section(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = os.path.join(temp_dir, "fab.sqlite3")
            ledger = LocalOperationsLedger(ledger_path)
            document_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "failed-api-doc",
                "originalFilename": "failed-api.pdf",
                "processingStatus": "failed",
                "metadata": {"processingError": "Missing OCR dependency"},
            })
            app = create_app({"fab_local_ledger_path": ledger_path})
            client = app.test_client()

            response = client.get("/api/exceptions")
            dashboard = client.get("/")

            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertEqual(payload["summary"]["total"], 1)
            self.assertEqual(payload["exceptions"][0]["entityId"], str(document_id))
            self.assertEqual(payload["exceptions"][0]["entity"]["originalFilename"], "failed-api.pdf")
            self.assertIn("retry_processing", {action["id"] for action in payload["exceptions"][0]["actions"]})
            html = dashboard.data.decode("utf-8")
            self.assertIn("Exception Queue", html)
            self.assertIn("failed_document", html)
            self.assertIn("failed-api.pdf", html)
            self.assertIn(f"/documents/{document_id}", html)
            self.assertIn(f"/documents/{document_id}/retry-processing", html)

    def test_exception_queue_surfaces_regenerable_stale_master_ledger_drafts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            config = {"mijngeldzaken_category_mapping": {"Personal": "Huishouden"}}
            document_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "stale-master-exception",
                "originalFilename": "groceries.txt",
                "documentType": "receipt",
                "processingStatus": "reviewed",
                "vendorName": "Local Supermarket",
                "category": "Personal",
                "transactionDate": "2026-06-28",
                "totalAmount": 42.5,
                "extractedData": {
                    "vendor_name": "Local Supermarket",
                    "transaction_date": "2026-06-28",
                    "total_amount": 42.5,
                    "description": "Weekly groceries",
                },
                "metadata": {"targetSystem": "mijngeldzaken"},
            })
            route = LocalRoutingService(ledger, config).prepare_document_route(document_id)
            export_service = LocalExportAttemptService(ledger, config)
            prepared = export_service.prepare_from_routing_attempt(route["routingAttemptId"])
            approved = export_service.approve_attempt(
                prepared["exportAttemptId"],
                actor="tester",
                confirmation=EXPORT_APPROVAL_PHRASE,
            )
            original_checksum = approved["exportAttempt"]["metadata"]["masterLedgerChecksum"]
            ledger.update_document(document_id, {
                "source": "scanner",
                "sourceDocumentId": "stale-master-exception",
                "originalFilename": "groceries.txt",
                "documentType": "receipt",
                "processingStatus": "export_draft_prepared",
                "vendorName": "Local Supermarket",
                "category": "Personal",
                "transactionDate": "2026-06-28",
                "totalAmount": 99.99,
                "extractedData": {
                    "vendor_name": "Local Supermarket",
                    "transaction_date": "2026-06-28",
                    "total_amount": 99.99,
                    "description": "Weekly groceries",
                },
                "metadata": {"targetSystem": "mijngeldzaken"},
            })

            payload = LocalExceptionQueueService(ledger, config).list_exceptions()
            stale = next(
                item for item in payload["exceptions"]
                if item["type"] == "stale_master_ledger_draft"
            )

            self.assertEqual(stale["entityType"], "export_attempt")
            self.assertEqual(stale["entityId"], prepared["exportAttemptId"])
            self.assertEqual(stale["details"]["storedChecksum"], original_checksum)
            self.assertNotEqual(stale["details"]["currentChecksum"], original_checksum)
            self.assertEqual(stale["details"]["freshnessStatus"], "checksum_mismatch")
            self.assertIn("regenerate_export_attempt", {action["id"] for action in stale["actions"]})
            regenerate_action = next(action for action in stale["actions"] if action["id"] == "regenerate_export_attempt")
            self.assertEqual(regenerate_action["path"], f"/api/export-attempts/{prepared['exportAttemptId']}/regenerate")
            self.assertEqual(regenerate_action["dashboardPath"], f"/export-attempts/{prepared['exportAttemptId']}/regenerate")
            self.assertEqual(regenerate_action["safety"], "safe_auto")
            self.assertEqual(stale["entity"]["status"], "approved")

            app = create_app({
                "fab_local_ledger_path": os.path.join(temp_dir, "fab.sqlite3"),
                "mijngeldzaken_category_mapping": {"Personal": "Huishouden"},
            })
            html = app.test_client().get("/").data.decode("utf-8")
            self.assertIn("stale_master_ledger_draft", html)
            self.assertIn(f"/export-attempts/{prepared['exportAttemptId']}/regenerate", html)

    def test_exception_queue_surfaces_record_level_master_ledger_blockers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            record_id = ledger.upsert_bookkeeping_record({
                "sourceType": "document",
                "status": "needs_review",
                "exportStatus": "blocked_by_review",
                "targetSystem": "waveapps",
                "vendorName": "Unknown Vendor",
                "category": "Manual Review",
                "amount": 10,
                "currency": "EUR",
                "reviewRequired": True,
            })

            payload = LocalExceptionQueueService(ledger).list_exceptions()
            record_issue = next(
                item for item in payload["exceptions"]
                if item["type"] == "master_ledger_record_review"
            )

            self.assertEqual(record_issue["entityType"], "bookkeeping_record")
            self.assertEqual(record_issue["entityId"], record_id)
            self.assertEqual(record_issue["entity"]["vendorName"], "Unknown Vendor")
            self.assertEqual(record_issue["entity"]["status"], "needs_review")
            self.assertIn("record_needs_review", record_issue["details"]["blockers"])
            self.assertIn("open_bookkeeping_record", {action["id"] for action in record_issue["actions"]})
            self.assertIn("open_master_ledger", {action["id"] for action in record_issue["actions"]})
            self.assertEqual(
                next(action for action in record_issue["actions"] if action["id"] == "open_bookkeeping_record")["path"],
                f"/api/bookkeeping-records/{record_id}",
            )
            self.assertEqual(
                next(
                    action for action in record_issue["actions"]
                    if action["id"] == "open_bookkeeping_record"
                )["dashboardPath"],
                f"/bookkeeping-records/{record_id}",
            )

            app = create_app({"fab_local_ledger_path": os.path.join(temp_dir, "fab.sqlite3")})
            html = app.test_client().get("/").data.decode("utf-8")
            self.assertIn("master_ledger_record_review", html)
            self.assertIn(f"/bookkeeping-records/{record_id}", html)

    def test_exception_queue_surfaces_reconciliation_master_ledger_blockers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            record_id = ledger.upsert_bookkeeping_record({
                "sourceType": "bank_transaction",
                "status": "ready_to_route",
                "exportStatus": "ready",
                "reconciliationStatus": "missing_receipt",
                "targetSystem": "waveapps",
                "vendorName": "Unknown Supplier",
                "description": "Bank row without receipt",
                "category": "Office Supplies",
                "amount": -12.5,
                "currency": "EUR",
                "reviewRequired": False,
            })

            payload = LocalExceptionQueueService(ledger).list_exceptions()
            reconciliation_issue = next(
                item for item in payload["exceptions"]
                if item["type"] == "master_ledger_reconciliation_blocker"
            )

            self.assertEqual(reconciliation_issue["entityType"], "bookkeeping_record")
            self.assertEqual(reconciliation_issue["entityId"], record_id)
            self.assertEqual(reconciliation_issue["entity"]["reconciliationStatus"], "missing_receipt")
            self.assertIn("reconciliation_missing_receipt", reconciliation_issue["details"]["blockers"])
            actions = {action["id"]: action for action in reconciliation_issue["actions"]}
            self.assertIn("open_bookkeeping_record", actions)
            self.assertIn("open_reconciliation", actions)
            self.assertEqual(actions["open_reconciliation"]["path"], "/api/reconciliation")
            self.assertEqual(actions["open_reconciliation"]["dashboardPath"], "/#reconciliation")


if __name__ == "__main__":
    unittest.main()
