import json
import os
import tempfile
import time
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from src.workflow.checkpoint_store import WorkflowCheckpointStore


class TestWorkflowCheckpointStore(unittest.TestCase):
    def test_filter_new_documents_skips_only_terminal_statuses(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = os.path.join(temp_dir, "workflow_state.json")
            with open(state_path, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "source_documents": {
                            "gmail:done": {"status": "processed"},
                            "gmail:review": {"status": "needs_review_low_confidence"},
                            "gmail:retry": {"status": "failed_data_entry"},
                            "gmail:legacy": {},
                        },
                        "known_documents": [],
                    },
                    handle,
                )

            store = WorkflowCheckpointStore({"workflow_state_file": state_path})
            documents = [
                {"id": "done"},
                {"id": "review"},
                {"id": "retry"},
                {"id": "legacy"},
                {"id": "new"},
            ]

            self.assertEqual(
                store.filter_new_documents("gmail", documents),
                [{"id": "retry"}, {"id": "new"}],
            )

    def test_filter_new_documents_allows_configured_skip_statuses(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = os.path.join(temp_dir, "workflow_state.json")
            with open(state_path, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "source_documents": {
                            "gmail:retry": {"status": "failed_data_entry"},
                        },
                        "known_documents": [],
                    },
                    handle,
                )

            store = WorkflowCheckpointStore(
                {
                    "workflow_state_file": state_path,
                    "workflow_checkpoint_skip_statuses": "failed_data_entry",
                }
            )

            self.assertEqual(store.filter_new_documents("gmail", [{"id": "retry"}]), [])

    def test_file_metadata_identity_survives_equivalent_document_object(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = WorkflowCheckpointStore(
                {"workflow_state_file": os.path.join(temp_dir, "workflow_state.json")}
            )
            document = {
                "local_path": "/tmp/receipt.pdf",
                "original_filename": "receipt.pdf",
            }
            store.mark_source_document("filesystem", document)

            self.assertEqual(
                store.filter_new_documents("filesystem", [dict(document)]),
                [],
            )

    def test_file_metadata_prevents_unrelated_documents_from_colliding(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = WorkflowCheckpointStore(
                {"workflow_state_file": os.path.join(temp_dir, "workflow_state.json")}
            )
            first = {"local_path": "/tmp/receipt-1.pdf"}
            second = {"local_path": "/tmp/receipt-2.pdf"}
            store.mark_source_document("filesystem", first)

            self.assertEqual(
                store.filter_new_documents("filesystem", [first, second]),
                [second],
            )

    def test_terminal_transition_is_persisted_immediately(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = os.path.join(temp_dir, "workflow_state.json")
            store = WorkflowCheckpointStore({"workflow_state_file": state_path})

            self.assertTrue(
                store.mark_source_document("gmail", {"id": "message-1"}, "processed")
            )

            with open(state_path, "r", encoding="utf-8") as handle:
                state = json.load(handle)
            self.assertEqual(
                state["source_documents"]["gmail:message-1"]["status"],
                "processed",
            )

    def test_autosave_can_be_disabled_for_batched_persistence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = os.path.join(temp_dir, "workflow_state.json")
            store = WorkflowCheckpointStore(
                {
                    "workflow_state_file": state_path,
                    "workflow_checkpoint_autosave": False,
                }
            )

            store.mark_source_document("gmail", {"id": "message-1"}, "processed")

            self.assertFalse(os.path.exists(state_path))
            self.assertTrue(store.save())
            self.assertTrue(os.path.exists(state_path))

    def test_save_failure_is_reported_without_raising(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = os.path.join(temp_dir, "workflow_state.json")
            store = WorkflowCheckpointStore(
                {
                    "workflow_state_file": state_path,
                    "workflow_checkpoint_autosave": False,
                }
            )
            store.mark_source_document("gmail", {"id": "message-1"}, "processed")

            with patch(
                "src.workflow.checkpoint_store.os.replace",
                side_effect=OSError("disk unavailable"),
            ):
                self.assertFalse(store.save())

            self.assertEqual(store.last_save_error, "disk unavailable")
            self.assertFalse(os.path.exists(f"{state_path}.tmp"))

    def test_run_lock_prevents_overlapping_store_instances(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = os.path.join(temp_dir, "workflow_state.json")
            first = WorkflowCheckpointStore({"workflow_state_file": state_path})
            second = WorkflowCheckpointStore({"workflow_state_file": state_path})

            self.assertTrue(first.acquire_run_lock())
            self.assertFalse(second.acquire_run_lock())
            self.assertTrue(first.release_run_lock())
            self.assertTrue(second.acquire_run_lock())
            self.assertTrue(second.release_run_lock())

    def test_stale_run_lock_is_recovered(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = os.path.join(temp_dir, "workflow_state.json")
            store = WorkflowCheckpointStore(
                {
                    "workflow_state_file": state_path,
                    "workflow_run_lock_stale_seconds": 1,
                }
            )
            with open(store.run_lock_path, "w", encoding="utf-8") as handle:
                json.dump({"token": "abandoned"}, handle)
            stale_time = time.time() - 10
            os.utime(store.run_lock_path, (stale_time, stale_time))

            self.assertTrue(store.acquire_run_lock())
            self.assertTrue(store.release_run_lock())

    def test_run_lock_release_requires_ownership(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = os.path.join(temp_dir, "workflow_state.json")
            store = WorkflowCheckpointStore({"workflow_state_file": state_path})
            self.assertTrue(store.acquire_run_lock())
            with open(store.run_lock_path, "w", encoding="utf-8") as handle:
                json.dump({"token": "replacement"}, handle)

            self.assertFalse(store.release_run_lock())
            self.assertTrue(os.path.exists(store.run_lock_path))

    def test_checkpoint_save_refreshes_owned_run_lock(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = os.path.join(temp_dir, "workflow_state.json")
            store = WorkflowCheckpointStore({"workflow_state_file": state_path})
            self.assertTrue(store.acquire_run_lock())
            old_time = time.time() - 100
            os.utime(store.run_lock_path, (old_time, old_time))

            store.mark_source_document("gmail", {"id": "message-1"}, "processed")

            self.assertGreater(os.path.getmtime(store.run_lock_path), old_time)
            self.assertTrue(store.release_run_lock())

    def test_checkpoint_serializes_financial_and_filesystem_types(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = os.path.join(temp_dir, "workflow_state.json")
            store = WorkflowCheckpointStore({"workflow_state_file": state_path})
            document = {
                "document_id": "doc-1",
                "duplicate_fingerprint": "fingerprint-1",
                "extracted_data": {
                    "total_amount": Decimal("1234.56"),
                    "transaction_date": date(2026, 6, 25),
                    "processed_at": datetime(2026, 6, 25, 8, 0, tzinfo=timezone.utc),
                    "source_path": Path("receipts/invoice.pdf"),
                    "tags": {"business", "vat"},
                    "content": b"binary receipt",
                },
            }

            self.assertTrue(store.remember_processed_document(document))

            with open(state_path, "r", encoding="utf-8") as handle:
                saved = json.load(handle)["known_documents"][0]["extracted_data"]
            self.assertEqual(saved["total_amount"], "1234.56")
            self.assertEqual(saved["transaction_date"], "2026-06-25")
            self.assertEqual(saved["processed_at"], "2026-06-25T08:00:00+00:00")
            self.assertEqual(saved["source_path"], os.path.join("receipts", "invoice.pdf"))
            self.assertEqual(saved["tags"], ["business", "vat"])
            self.assertEqual(saved["content"]["type"], "bytes")
            self.assertEqual(saved["content"]["size"], len(b"binary receipt"))

    def test_invalid_known_document_limit_uses_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = WorkflowCheckpointStore(
                {
                    "workflow_state_file": os.path.join(temp_dir, "workflow_state.json"),
                    "workflow_checkpoint_autosave": False,
                    "workflow_known_documents_limit": "invalid",
                }
            )

            self.assertTrue(
                store.remember_processed_document(
                    {
                        "document_id": "doc-1",
                        "duplicate_fingerprint": "fingerprint-1",
                    }
                )
            )
            self.assertEqual(len(store.known_documents()), 1)

    def test_corrupt_checkpoint_is_reported_and_preserved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = os.path.join(temp_dir, "workflow_state.json")
            corrupt_content = '{"source_documents":'
            with open(state_path, "w", encoding="utf-8") as handle:
                handle.write(corrupt_content)

            store = WorkflowCheckpointStore({"workflow_state_file": state_path})

            self.assertIsNotNone(store.load_error)
            self.assertTrue(store.fail_closed)
            self.assertEqual(store.known_documents(), [])
            with open(state_path, "r", encoding="utf-8") as handle:
                self.assertEqual(handle.read(), corrupt_content)

    def test_checkpoint_fail_closed_can_be_explicitly_disabled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = os.path.join(temp_dir, "workflow_state.json")
            with open(state_path, "w", encoding="utf-8") as handle:
                handle.write("invalid json")

            store = WorkflowCheckpointStore(
                {
                    "workflow_state_file": state_path,
                    "workflow_checkpoint_fail_closed": False,
                }
            )

            self.assertFalse(store.fail_closed)
            self.assertIsNotNone(store.load_error)


if __name__ == "__main__":
    unittest.main()
