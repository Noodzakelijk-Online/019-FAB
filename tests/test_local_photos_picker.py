import os
import tempfile
import unittest

from src.document_fetchers.photos_picker_client import UnsupportedPickerMedia
from src.operations.local_ledger import LocalOperationsLedger
from src.operations.local_photos_picker import LocalGooglePhotosPickerService


class _PickerClient:
    def __init__(self, download_dir, media_items_set=True, items=None):
        self.download_dir = download_dir
        self.media_items_set = media_items_set
        self.items = list(items or [])
        self.created = 0
        self.polled = 0
        self.listed = 0
        self.deleted = []

    def create_session(self):
        self.created += 1
        return {
            "id": "picker-session-1",
            "pickerUri": "https://photos.google.com/picker/picker-session-1",
            "pollingConfig": {"pollInterval": "5s", "timeoutIn": "600s"},
        }

    def get_session(self, session_id):
        self.polled += 1
        return {
            "id": session_id,
            "mediaItemsSet": self.media_items_set,
            "pollingConfig": {"pollInterval": "5s", "timeoutIn": "600s"},
        }

    def list_media_items(self, session_id):
        self.listed += 1
        return {"items": list(self.items), "pages": 1, "truncated": False}

    def download_media_item(self, item, session_id):
        if item.get("type") != "PHOTO":
            raise UnsupportedPickerMedia("not a photo")
        path = os.path.join(self.download_dir, f"{item['id']}.jpg")
        with open(path, "wb") as handle:
            handle.write(item.get("content") or b"receipt-image")
        return {
            "id": item["id"],
            "source": "google_photos",
            "original_filename": f"{item['id']}.jpg",
            "mime_type": "image/jpeg",
            "local_path": path,
            "timestamp": "2026-07-13T08:00:00Z",
            "metadata": {"picker_session_id": session_id},
        }

    def delete_session(self, session_id):
        self.deleted.append(session_id)


class TestLocalGooglePhotosPickerService(unittest.TestCase):
    def _service(self, temp_dir, client):
        credentials_path = os.path.join(temp_dir, "picker-credentials.json")
        token_path = os.path.join(temp_dir, "picker-token.json")
        for path in (credentials_path, token_path):
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("{}")
        ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
        config = {
            "google_photos_enabled": True,
            "google_photos_credentials_file": credentials_path,
            "google_photos_picker_token_file": token_path,
            "google_photos_download_dir": temp_dir,
            "google_photos_picker_autoclose": True,
        }
        service = LocalGooglePhotosPickerService(
            ledger,
            config,
            client_factory=lambda _config: client,
        )
        return ledger, service

    def test_supervised_selection_registers_evidence_and_cleans_up_session(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = _PickerClient(temp_dir, items=[{
                "id": "photo-1",
                "type": "PHOTO",
                "content": b"receipt-v1",
            }])
            ledger, service = self._service(temp_dir, client)

            created = service.create_session(actor="test")
            collected = service.collect_session(created["session"]["id"], actor="test")
            repeated = service.collect_session(created["session"]["id"], actor="test")

            self.assertEqual(created["status"], "awaiting_user_selection")
            self.assertTrue(created["session"]["pickerUri"].endswith("/autoclose"))
            self.assertEqual(collected["status"], "completed")
            self.assertEqual(collected["summary"]["registered"], 1)
            self.assertEqual(repeated["status"], "already_complete")
            self.assertEqual(client.deleted, ["picker-session-1"])
            documents = ledger.list_documents()
            self.assertEqual(len(documents), 1)
            self.assertEqual(documents[0]["source"], "google_photos")
            self.assertEqual(documents[0]["source_document_id"], "photo-1")
            source = ledger.list_source_accounts(source_type="google_photos")[0]
            self.assertEqual(source["status"], "ready")
            self.assertEqual(source["documents_imported"], 1)
            actions = [item["action"] for item in ledger.list_audit_events(limit=20)]
            self.assertIn("local_photos_picker.session_created", actions)
            self.assertIn("local_photos_picker.selection_collected", actions)

    def test_poll_before_selection_keeps_session_open(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = _PickerClient(temp_dir, media_items_set=False)
            ledger, service = self._service(temp_dir, client)
            created = service.create_session(actor="test")

            result = service.collect_session(created["session"]["id"], actor="test")

            self.assertEqual(result["status"], "awaiting_user_selection")
            self.assertEqual(client.listed, 0)
            self.assertEqual(client.deleted, [])
            run = ledger.get_workflow_run(created["session"]["id"])
            self.assertFalse(run["metadata"]["mediaItemsSet"])
            self.assertIsNotNone(run["metadata"]["lastPolledAt"])

    def test_non_photo_selection_is_skipped_without_entering_document_pipeline(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = _PickerClient(temp_dir, items=[{"id": "video-1", "type": "VIDEO"}])
            ledger, service = self._service(temp_dir, client)
            created = service.create_session(actor="test")

            result = service.collect_session(created["session"]["id"], actor="test")

            self.assertEqual(result["status"], "completed_with_skips")
            self.assertEqual(result["summary"]["skipped"], 1)
            self.assertEqual(ledger.list_documents(), [])
            self.assertEqual(client.deleted, ["picker-session-1"])

    def test_per_item_errors_are_counted_but_bounded_in_persisted_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            items = [{"id": f"photo-{index}", "type": "PHOTO"} for index in range(30)]
            client = _PickerClient(temp_dir, items=items)

            def fail_download(_item, _session_id):
                raise RuntimeError("media download failed")

            client.download_media_item = fail_download
            ledger, service = self._service(temp_dir, client)
            created = service.create_session(actor="test")

            result = service.collect_session(created["session"]["id"], actor="test")

            self.assertFalse(result["success"])
            self.assertEqual(result["status"], "failed")
            run = ledger.get_workflow_run(created["session"]["id"])
            self.assertEqual(run["metadata"]["errorCount"], 30)
            self.assertEqual(len(run["metadata"]["errors"]), 25)
            self.assertTrue(run["metadata"]["errorDetailsTruncated"])
            self.assertLessEqual(len(run["error_message"]), 500)

    def test_cancel_deletes_provider_session_and_records_terminal_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = _PickerClient(temp_dir)
            ledger, service = self._service(temp_dir, client)
            created = service.create_session(actor="test")

            result = service.cancel_session(created["session"]["id"], actor="test")

            self.assertEqual(result["status"], "cancelled")
            self.assertTrue(result["session"]["providerSessionDeleted"])
            self.assertIsNone(result["session"]["pickerUri"])
            self.assertEqual(client.deleted, ["picker-session-1"])
            self.assertEqual(
                ledger.get_workflow_run(created["session"]["id"])["status"],
                "cancelled",
            )

    def test_untrusted_picker_uri_fails_closed_and_cleans_provider_session(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = _PickerClient(temp_dir)
            client.create_session = lambda: {
                "id": "picker-session-1",
                "pickerUri": "https://example.test/not-google-photos",
            }
            ledger, service = self._service(temp_dir, client)

            result = service.create_session(actor="test")

            self.assertFalse(result["success"])
            self.assertEqual(result["status"], "failed")
            self.assertEqual(client.deleted, ["picker-session-1"])
            self.assertEqual(ledger.list_workflow_runs(limit=1)[0]["status"], "failed")

    def test_completed_session_cannot_be_rewritten_as_cancelled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = _PickerClient(temp_dir, items=[{
                "id": "photo-1",
                "type": "PHOTO",
                "content": b"receipt-v1",
            }])
            ledger, service = self._service(temp_dir, client)
            created = service.create_session(actor="test")
            service.collect_session(created["session"]["id"], actor="test")

            result = service.cancel_session(created["session"]["id"], actor="test")

            self.assertEqual(result["status"], "already_complete")
            self.assertEqual(result["session"]["status"], "completed")
            self.assertEqual(
                ledger.get_workflow_run(created["session"]["id"])["status"],
                "completed",
            )

    def test_client_initialization_failure_does_not_leave_creating_session(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger, service = self._service(temp_dir, _PickerClient(temp_dir))

            def fail_client(_config):
                raise RuntimeError("Picker client unavailable")

            service.client_factory = fail_client
            result = service.create_session(actor="test")

            self.assertFalse(result["success"])
            self.assertEqual(result["status"], "failed")
            self.assertEqual(ledger.list_workflow_runs(limit=1)[0]["status"], "failed")
            source = ledger.list_source_accounts(source_type="google_photos")[0]
            self.assertEqual(source["status"], "failed")

    def test_client_initialization_failure_does_not_leave_collecting_session(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger, service = self._service(temp_dir, _PickerClient(temp_dir))
            created = service.create_session(actor="test")

            def fail_client(_config):
                raise RuntimeError("Picker client unavailable")

            service.client_factory = fail_client
            result = service.collect_session(created["session"]["id"], actor="test")

            self.assertFalse(result["success"])
            self.assertEqual(result["status"], "failed")
            run = ledger.get_workflow_run(created["session"]["id"])
            self.assertEqual(run["status"], "failed")
            self.assertEqual(run["metadata"]["providerSessionId"], "picker-session-1")


if __name__ == "__main__":
    unittest.main()
