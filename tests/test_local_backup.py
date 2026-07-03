import json
import os
import tempfile
import unittest
import zipfile

from src.operations.local_backup import LocalBackupService, RESTORE_CONFIRMATION_PHRASE
from src.operations.local_ledger import LocalOperationsLedger


class TestLocalBackupService(unittest.TestCase):
    def test_create_backup_writes_manifest_and_audit_event(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = os.path.join(temp_dir, "fab.sqlite3")
            backup_dir = os.path.join(temp_dir, "backups")
            ledger = LocalOperationsLedger(ledger_path)
            ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "scan-backup-1",
                "originalFilename": "receipt.pdf",
            })

            result = LocalBackupService(ledger, {"fab_local_backup_dir": backup_dir}).create_backup(note="test")

            self.assertTrue(result["success"])
            self.assertTrue(os.path.exists(result["backupPath"]))
            self.assertEqual(result["manifest"]["format"], "fab-local-ledger-backup-v1")
            with zipfile.ZipFile(result["backupPath"], "r") as archive:
                manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
                self.assertEqual(manifest["ledgerFilename"], "fab_operations.sqlite3")
                self.assertIn("fab_operations.sqlite3", archive.namelist())
            self.assertEqual(ledger.list_audit_events()[0]["action"], "local_backup.created")

    def test_restore_requires_confirmation_and_restores_ledger(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = os.path.join(temp_dir, "fab.sqlite3")
            backup_dir = os.path.join(temp_dir, "backups")
            ledger = LocalOperationsLedger(ledger_path)
            original_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "scan-original",
                "originalFilename": "original.pdf",
            })
            service = LocalBackupService(ledger, {"fab_local_backup_dir": backup_dir})
            backup = service.create_backup(note="restore test")
            ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "scan-new",
                "originalFilename": "new.pdf",
            })

            blocked = service.restore_backup(backup["backupPath"], "wrong")
            restored = service.restore_backup(backup["backupPath"], RESTORE_CONFIRMATION_PHRASE)
            documents = ledger.list_documents(limit=10)

            self.assertFalse(blocked["success"])
            self.assertEqual(blocked["status"], "requires_confirmation")
            self.assertTrue(restored["success"])
            self.assertEqual([document["id"] for document in documents], [original_id])
            self.assertEqual(ledger.list_audit_events()[0]["action"], "local_backup.restored")
            self.assertTrue(os.path.exists(restored["preRestoreBackupPath"]))

    def test_inspect_rejects_unsafe_archive_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            backup_dir = os.path.join(temp_dir, "backups")
            os.makedirs(backup_dir)
            unsafe_path = os.path.join(backup_dir, "unsafe.zip")
            with zipfile.ZipFile(unsafe_path, "w") as archive:
                archive.writestr("../manifest.json", "{}")
                archive.writestr("fab_operations.sqlite3", b"not sqlite")

            with self.assertRaises(ValueError):
                LocalBackupService(ledger, {"fab_local_backup_dir": backup_dir}).inspect_backup(unsafe_path)

    def test_list_backups_returns_valid_backup_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            backup_dir = os.path.join(temp_dir, "backups")
            service = LocalBackupService(ledger, {"fab_local_backup_dir": backup_dir})
            backup = service.create_backup()

            listed = service.list_backups()

            self.assertEqual(listed["backupDir"], backup_dir)
            self.assertEqual(listed["backups"][0]["backupFilename"], backup["backupFilename"])
            self.assertEqual(listed["backups"][0]["status"], "valid")


if __name__ == "__main__":
    unittest.main()
