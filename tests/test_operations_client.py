import unittest
import os
import sqlite3
import tempfile
from unittest.mock import MagicMock

import requests

from src.document_handling.source_identity import source_document_id
from src.operations.operations_client import OperationsClient


class TestOperationsClient(unittest.TestCase):
    def test_disabled_client_skips_without_http_request(self):
        client = OperationsClient({})
        client.session.request = MagicMock()

        result = client.update_workflow_run(1, status="completed")

        self.assertEqual(result["status"], "skipped")
        client.session.request.assert_not_called()

    def test_string_false_disables_configured_client(self):
        client = OperationsClient({
            "fab_operations_api_url": "http://localhost:3000",
            "fab_operations_enabled": "false",
        })
        client.session.request = MagicMock()

        result = client.update_workflow_run(1, status="completed")

        self.assertEqual(result["status"], "skipped")
        client.session.request.assert_not_called()

    def test_invalid_timeout_uses_safe_default(self):
        client = OperationsClient({
            "fab_operations_api_url": "http://localhost:3000",
            "fab_operations_timeout_seconds": "invalid",
        })

        self.assertEqual(client.timeout, 5.0)

    def test_serialization_error_does_not_escape_best_effort_client(self):
        client = OperationsClient({"fab_operations_api_url": "http://localhost:3000"})
        client.session.request = MagicMock(side_effect=TypeError("bytes are not JSON serializable"))

        result = client.update_workflow_run(1, metadata={"content": b"data"})

        self.assertEqual(result["status"], "failed")
        self.assertIn("not JSON serializable", result["error"])

    def test_register_document_posts_normalized_payload(self):
        client = OperationsClient({
            "fab_operations_api_url": "http://localhost:3000",
            "fab_operations_api_token": "secret",
        })
        response = MagicMock()
        response.content = b'{"id": 12}'
        response.json.return_value = {"id": 12}
        response.raise_for_status.return_value = None
        client.session.request = MagicMock(return_value=response)

        result = client.register_document(
            "gmail",
            {
                "id": "msg-1",
                "original_filename": "receipt.pdf",
                "local_path": "/tmp/receipt.pdf",
                "content": b"ignored",
            },
            {
                "ocr_text": "Vendor\n100.00",
                "confidence_score": 0.91,
                "extracted_data": {
                    "vendor_name": "Vendor",
                    "total_amount": 100.0,
                    "transaction_date": "2026-01-15",
                },
            },
            processing_status="extracted",
        )

        self.assertEqual(result, 12)
        client.session.request.assert_called_once()
        _, kwargs = client.session.request.call_args
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer secret")
        self.assertEqual(kwargs["json"]["source"], "gmail")
        self.assertEqual(kwargs["json"]["sourceDocumentId"], "msg-1")
        self.assertEqual(kwargs["json"]["processingStatus"], "extracted")
        self.assertEqual(kwargs["json"]["vendorName"], "Vendor")
        self.assertNotIn("content", kwargs["json"]["metadata"]["source_document"])

    def test_register_document_uses_alternate_source_identifier(self):
        client = OperationsClient({"fab_operations_api_url": "http://localhost:3000"})
        response = MagicMock()
        response.content = b'{"id": 13}'
        response.json.return_value = {"id": 13}
        response.raise_for_status.return_value = None
        client.session.request = MagicMock(return_value=response)

        client.register_document("drive", {"file_id": "drive-file-1"})

        _, kwargs = client.session.request.call_args
        self.assertEqual(kwargs["json"]["sourceDocumentId"], "drive-file-1")

    def test_register_document_uses_deterministic_file_identity(self):
        client = OperationsClient({"fab_operations_api_url": "http://localhost:3000"})
        response = MagicMock()
        response.content = b'{"id": 14}'
        response.json.return_value = {"id": 14}
        response.raise_for_status.return_value = None
        client.session.request = MagicMock(return_value=response)
        document = {
            "original_filename": "receipt.pdf",
            "local_path": "/tmp/receipt.pdf",
        }

        client.register_document("filesystem", document)

        _, kwargs = client.session.request.call_args
        self.assertEqual(
            kwargs["json"]["sourceDocumentId"],
            source_document_id(document),
        )

    def test_record_audit_event_posts_service_payload(self):
        client = OperationsClient({
            "fab_operations_api_url": "http://localhost:3000",
            "fab_operations_api_token": "secret",
        })
        response = MagicMock()
        response.content = b'{"id": 44}'
        response.json.return_value = {"id": 44}
        response.raise_for_status.return_value = None
        client.session.request = MagicMock(return_value=response)

        result = client.record_audit_event(
            "workflow.document.skipped",
            "bookkeeping_document",
            "12",
            {"reason": "duplicate_document"},
        )

        self.assertEqual(result, 44)
        client.session.request.assert_called_once()
        _, kwargs = client.session.request.call_args
        self.assertEqual(kwargs["json"]["action"], "workflow.document.skipped")
        self.assertEqual(kwargs["json"]["entityType"], "bookkeeping_document")
        self.assertEqual(kwargs["json"]["entityId"], "12")
        self.assertEqual(kwargs["json"]["details"]["reason"], "duplicate_document")

    def test_local_ledger_persists_operations_when_service_is_not_configured(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = os.path.join(temp_dir, "fab.sqlite3")
            client = OperationsClient({
                "fab_local_ledger_enabled": True,
                "fab_local_ledger_path": ledger_path,
            })
            client.session.request = MagicMock()

            workflow_run_id = client.create_workflow_run("manual", {"source": "unit_test"})
            document_id = client.register_document(
                "filesystem",
                {
                    "id": "file-1",
                    "original_filename": "receipt.pdf",
                    "local_path": os.path.join(temp_dir, "receipt.pdf"),
                    "content": b"do-not-store",
                },
                {
                    "ocr_text": "Vendor\n100.00",
                    "confidence_score": 0.92,
                    "extracted_data": {
                        "vendor_name": "Vendor",
                        "total_amount": 100.0,
                        "transaction_date": "2026-06-28",
                    },
                },
                processing_status="extracted",
            )
            update_result = client.update_document(document_id, {"category": "Business"}, processing_status="validated")
            review_id = client.create_review_item(document_id, "missing_date", "Date needs confirmation.")
            routing_id = client.create_routing_attempt(
                document_id,
                "waveapps_business",
                "requires_review",
                workflow_run_id=workflow_run_id,
                message="Needs approval before export.",
            )
            export_id = client.upsert_export_attempt(
                document_id,
                "approval_required",
                routing_attempt_id=routing_id,
                workflow_run_id=workflow_run_id,
                action_id="transaction_add",
                operation_id="op-client-1",
                payload_data={"token": "secret"},
                metadata={"source": "unit_test"},
            )
            reconciliation_id = client.create_reconciliation_match(
                "bank-tx-1",
                "review",
                document_id=document_id,
                confidence_score=0.74,
            )
            audit_id = client.record_audit_event(
                "workflow.document.reviewed",
                "bookkeeping_document",
                str(document_id),
                {"reviewItemId": review_id},
            )

            client.session.request.assert_not_called()
            self.assertEqual(update_result["status"], "persisted_local")
            self.assertEqual(workflow_run_id, 1)
            self.assertEqual(document_id, 1)
            self.assertEqual(review_id, 1)
            self.assertEqual(routing_id, 1)
            self.assertEqual(export_id, 1)
            self.assertEqual(reconciliation_id, 1)
            self.assertEqual(audit_id, 1)

            connection = sqlite3.connect(ledger_path)
            try:
                connection.row_factory = sqlite3.Row
                document = connection.execute(
                    "SELECT * FROM bookkeeping_documents WHERE id = ?",
                    (document_id,),
                ).fetchone()
                self.assertEqual(document["source"], "filesystem")
                self.assertEqual(document["processing_status"], "validated")
                self.assertEqual(document["vendor_name"], "Vendor")
                self.assertNotIn("do-not-store", document["metadata_json"])
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM review_items").fetchone()[0],
                    1,
                )
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM routing_attempts").fetchone()[0],
                    1,
                )
                export = connection.execute("SELECT * FROM export_attempts").fetchone()
                self.assertEqual(export["operation_id"], "op-client-1")
                self.assertIn("<redacted>", export["payload_json"])
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM reconciliation_matches").fetchone()[0],
                    1,
                )
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0],
                    1,
                )
            finally:
                connection.close()

    def test_service_failure_falls_back_to_local_ledger(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = os.path.join(temp_dir, "fab.sqlite3")
            client = OperationsClient({
                "fab_operations_api_url": "http://localhost:3000",
                "fab_local_ledger_enabled": True,
                "fab_local_ledger_path": ledger_path,
            })
            client.session.request = MagicMock(side_effect=requests.RequestException("network blocked"))

            document_id = client.register_document(
                "gmail",
                {"id": "message-1", "original_filename": "invoice.pdf"},
            )

            self.assertEqual(document_id, 1)
            connection = sqlite3.connect(ledger_path)
            try:
                row = connection.execute(
                    "SELECT source, source_document_id FROM bookkeeping_documents WHERE id = 1"
                ).fetchone()
            finally:
                connection.close()
            self.assertEqual(row, ("gmail", "message-1"))

    def test_local_fallback_creates_bookkeeping_record_routing_attempt(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = os.path.join(temp_dir, "fab.sqlite3")
            client = OperationsClient({
                "fab_operations_api_url": "",
                "fab_local_ledger_enabled": True,
                "fab_local_ledger_path": ledger_path,
            })

            record_id = client.local_ledger.upsert_bookkeeping_record({
                "sourceType": "bank_transaction",
                "bankTransactionId": 42,
                "vendorName": "Office Shop",
                "category": "Office Supplies",
                "recordDate": "2026-06-28",
                "amount": -42.5,
            })
            routing_id = client.create_routing_attempt(
                None,
                "waveapps_business",
                "draft_prepared",
                bookkeeping_record_id=record_id,
                message="Bank transaction draft prepared.",
            )

            self.assertEqual(routing_id, 1)
            connection = sqlite3.connect(ledger_path)
            try:
                connection.row_factory = sqlite3.Row
                route = connection.execute("SELECT * FROM routing_attempts WHERE id = 1").fetchone()
            finally:
                connection.close()
            self.assertIsNone(route["document_id"])
            self.assertEqual(route["bookkeeping_record_id"], record_id)
            self.assertEqual(route["target"], "waveapps_business")


if __name__ == "__main__":
    unittest.main()
