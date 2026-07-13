import os
import tempfile
import unittest

from src.operations.local_connector_intake import LocalConnectorIntakeService
from src.operations.local_ledger import LocalOperationsLedger


class _Fetcher:
    def __init__(self, documents, error=None):
        self.documents = documents
        self.last_error = error
        self.auth_error = None
        self.last_run = {
            "status": "partial" if error and documents else "failed" if error else "completed",
            "fetched": len(documents),
            "skipped": 0,
            "pages": 2,
        }

    def fetch_documents(self):
        return list(self.documents)


class TestLocalConnectorIntake(unittest.TestCase):
    def _service(self, temp_dir, documents, error=None):
        credentials_path = os.path.join(temp_dir, "gmail-credentials.json")
        token_path = os.path.join(temp_dir, "gmail-token.pickle")
        for path in (credentials_path, token_path):
            with open(path, "wb") as handle:
                handle.write(b"configured")
        ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
        config = {
            "gmail_enabled": True,
            "gmail_credentials_file": credentials_path,
            "gmail_token_file": token_path,
            "gmail_attachment_download_dir": temp_dir,
            "google_drive_enabled": False,
            "freshdesk_enabled": False,
            "google_photos_enabled": False,
        }
        service = LocalConnectorIntakeService(
            ledger,
            config,
            fetcher_factories={"gmail": lambda _config: _Fetcher(documents, error=error)},
        )
        return ledger, service

    def test_sync_registers_source_provenance_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            document_path = os.path.join(temp_dir, "receipt.pdf")
            with open(document_path, "wb") as handle:
                handle.write(b"receipt-v1")
            documents = [{
                "id": "gmail-message-1_attachment-1",
                "source": "gmail",
                "original_filename": "receipt.pdf",
                "mime_type": "application/pdf",
                "local_path": document_path,
                "metadata": {"subject": "Invoice", "access_token": "must-not-persist"},
            }]
            ledger, service = self._service(temp_dir, documents)

            first = service.sync(["gmail"], actor="test")
            second = service.sync(["gmail"], actor="test")

            self.assertTrue(first["success"])
            self.assertEqual(first["status"], "completed")
            self.assertEqual(first["summary"]["registered"], 1)
            self.assertEqual(second["summary"]["alreadyRegistered"], 1)
            self.assertEqual(len(ledger.list_documents()), 1)
            source = ledger.list_source_accounts(source_type="gmail")[0]
            self.assertEqual(source["status"], "ready")
            self.assertEqual(source["documents_seen"], 2)
            self.assertEqual(source["documents_imported"], 1)
            document = ledger.list_documents()[0]
            self.assertEqual(document["source_account_id"], source["id"])
            self.assertEqual(document["source_document_id"], "gmail-message-1_attachment-1")
            self.assertEqual(document["metadata"]["providerMetadata"]["access_token"], "<redacted>")
            runs = ledger.list_workflow_runs(limit=10)
            self.assertEqual([run["status"] for run in runs[:2]], ["completed", "completed"])
            self.assertEqual(runs[0]["metadata"]["summary"]["alreadyRegistered"], 1)
            self.assertEqual(first["externalSubmission"], "not_executed")

    def test_changed_provider_document_creates_reviewable_revision(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            first_path = os.path.join(temp_dir, "receipt-v1.pdf")
            second_path = os.path.join(temp_dir, "receipt-v2.pdf")
            with open(first_path, "wb") as handle:
                handle.write(b"receipt-v1")
            with open(second_path, "wb") as handle:
                handle.write(b"receipt-v2")
            documents = [{
                "id": "drive-file-1",
                "original_filename": "receipt.pdf",
                "local_path": first_path,
            }]
            ledger, service = self._service(temp_dir, documents)
            service.sync(["gmail"], actor="test")

            documents[0]["local_path"] = second_path
            refreshed = service.sync(["gmail"], actor="test")

            self.assertEqual(refreshed["summary"]["revisions"], 1)
            records = sorted(ledger.list_documents(), key=lambda item: item["id"])
            self.assertEqual(len(records), 2)
            self.assertNotEqual(records[0]["storage_path"], records[1]["storage_path"])
            self.assertIn(":revision:", records[1]["source_document_id"])
            reviews = ledger.list_review_items(status="pending", limit=10)
            self.assertEqual(reviews[0]["reason"], "source_revision_detected")
            self.assertEqual(reviews[0]["document_id"], records[1]["id"])

    def test_partial_provider_failure_keeps_downloaded_evidence_and_redacts_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            document_path = os.path.join(temp_dir, "receipt.pdf")
            with open(document_path, "wb") as handle:
                handle.write(b"partial-receipt")
            documents = [{
                "id": "gmail-partial-1",
                "original_filename": "receipt.pdf",
                "local_path": document_path,
            }]
            ledger, service = self._service(
                temp_dir,
                documents,
                error=RuntimeError(
                    "provider failed?access_token=top-secret; Authorization: Bearer header-secret; X-Api-Key: key-secret"
                ),
            )

            result = service.sync(["gmail"], actor="test")

            self.assertFalse(result["success"])
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["summary"]["registered"], 1)
            self.assertEqual(result["results"][0]["status"], "partial")
            self.assertNotIn("top-secret", result["results"][0]["error"])
            self.assertNotIn("header-secret", result["results"][0]["error"])
            self.assertNotIn("key-secret", result["results"][0]["error"])
            self.assertIn("[REDACTED]", result["results"][0]["error"])
            self.assertEqual(ledger.list_source_accounts(source_type="gmail")[0]["status"], "partial")
            self.assertEqual(len(ledger.list_documents()), 1)

    def test_download_outside_configured_root_fails_source_completeness(self):
        with tempfile.TemporaryDirectory() as temp_dir, tempfile.TemporaryDirectory() as outside_dir:
            document_path = os.path.join(outside_dir, "unexpected.pdf")
            with open(document_path, "wb") as handle:
                handle.write(b"unexpected")
            ledger, service = self._service(temp_dir, [{
                "id": "gmail-outside-root",
                "original_filename": "unexpected.pdf",
                "local_path": document_path,
            }])

            result = service.sync(["gmail"], actor="test")

            self.assertFalse(result["success"])
            self.assertEqual(result["results"][0]["status"], "failed")
            self.assertEqual(result["summary"]["skipped"], 1)
            self.assertIn("path_outside_source_root", result["results"][0]["error"])
            self.assertEqual(ledger.list_documents(), [])
            self.assertEqual(ledger.list_source_accounts(source_type="gmail")[0]["status"], "failed")

    def test_configured_connector_stays_disabled_without_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            credentials_path = os.path.join(temp_dir, "gmail-credentials.json")
            token_path = os.path.join(temp_dir, "gmail-token.pickle")
            for path in (credentials_path, token_path):
                with open(path, "wb") as handle:
                    handle.write(b"configured")
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            service = LocalConnectorIntakeService(
                ledger,
                {
                    "gmail_credentials_file": credentials_path,
                    "gmail_token_file": token_path,
                    "gmail_attachment_download_dir": temp_dir,
                },
                fetcher_factories={"gmail": lambda _config: self.fail("disabled connector was invoked")},
            )

            gmail = next(item for item in service.plan()["sources"] if item["source"] == "gmail")
            result = service.sync(actor="test")

            self.assertTrue(gmail["configured"])
            self.assertFalse(gmail["enabled"])
            self.assertEqual(gmail["status"], "disabled")
            self.assertEqual(result["status"], "no_sources_enabled")

    def test_drive_requires_an_approved_folder_scope(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            credentials_path = os.path.join(temp_dir, "drive-credentials.json")
            token_path = os.path.join(temp_dir, "drive-token.pickle")
            for path in (credentials_path, token_path):
                with open(path, "wb") as handle:
                    handle.write(b"configured")
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            service = LocalConnectorIntakeService(ledger, {
                "google_drive_enabled": True,
                "google_drive_credentials_file": credentials_path,
                "google_drive_token_file": token_path,
                "google_drive_download_dir": temp_dir,
            })

            drive = next(item for item in service.plan()["sources"] if item["source"] == "google_drive")
            result = service.sync(["google_drive"], actor="test")

            self.assertFalse(drive["configured"])
            self.assertEqual(drive["status"], "needs_configuration")
            self.assertEqual(result["status"], "attention_required")
            self.assertIn("folder_id", drive["nextAction"])

    def test_google_photos_requires_supervised_picker_instead_of_background_scan(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            token_path = os.path.join(temp_dir, "photos-picker-token.json")
            credentials_path = os.path.join(temp_dir, "photos-picker-credentials.json")
            for path in (token_path, credentials_path):
                with open(path, "wb") as handle:
                    handle.write(b"configured")
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            service = LocalConnectorIntakeService(ledger, {
                "google_photos_enabled": True,
                "google_photos_credentials_file": credentials_path,
                "google_photos_picker_token_file": token_path,
            })

            plan = service.plan()
            photos = next(item for item in plan["sources"] if item["source"] == "google_photos")
            result = service.sync(["google_photos"], actor="test")

            self.assertEqual(photos["status"], "supervision_required")
            self.assertFalse(photos["canSync"])
            self.assertEqual(result["status"], "attention_required")
            self.assertEqual(result["results"][0]["status"], "supervision_required")
            source = ledger.list_source_accounts(source_type="google_photos")[0]
            self.assertEqual(source["status"], "supervision_required")
            self.assertEqual(result["externalSubmission"], "not_executed")


if __name__ == "__main__":
    unittest.main()
