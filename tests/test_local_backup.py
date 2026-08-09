import json
import hashlib
import os
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from src.operations.local_backup import (
    BACKUP_FORMAT_V1,
    BACKUP_FORMAT_V2,
    LocalBackupService,
    RESTORE_CONFIRMATION_PHRASE,
)
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

            result = LocalBackupService(ledger, {"fab_local_backup_dir": backup_dir}).create_backup(
                note="test",
                actor="test-operator",
            )

            self.assertTrue(result["success"])
            self.assertTrue(os.path.exists(result["backupPath"]))
            self.assertEqual(result["manifest"]["format"], BACKUP_FORMAT_V2)
            self.assertEqual(
                result["manifest"]["sourceEvidence"]["coverageStatus"],
                "incomplete",
            )
            with zipfile.ZipFile(result["backupPath"], "r") as archive:
                manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
                self.assertEqual(manifest["ledgerFilename"], "fab_operations.sqlite3")
                self.assertIn("fab_operations.sqlite3", archive.namelist())
            audit_event = ledger.list_audit_events()[0]
            self.assertEqual(audit_event["action"], "local_backup.created")
            self.assertEqual(audit_event["details"]["actor"], "test-operator")

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

            manifest_only = service.list_backups(deep_verify=False)
            self.assertEqual(manifest_only["verificationMode"], "manifest_only")
            self.assertEqual(manifest_only["backups"][0]["status"], "manifest_valid")
            self.assertEqual(
                manifest_only["schedule"]["integrityVerification"],
                "manifest_only",
            )

    def test_manifest_inspection_cache_reuses_only_an_unchanged_archive(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            service = LocalBackupService(
                ledger,
                {"fab_local_backup_dir": os.path.join(temp_dir, "backups")},
            )
            backup = service.create_backup()
            first = service.inspect_backup_manifest(backup["backupPath"])

            with patch(
                "src.operations.local_backup.zipfile.ZipFile",
                side_effect=AssertionError("unchanged manifest cache miss"),
            ):
                cached = service.inspect_backup_manifest(backup["backupPath"])

            self.assertEqual(first, cached)

    def test_inspect_rejects_checksum_mismatched_ledger_bytes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            backup_dir = os.path.join(temp_dir, "backups")
            service = LocalBackupService(
                ledger,
                {"fab_local_backup_dir": backup_dir},
            )
            backup = service.create_backup()
            with zipfile.ZipFile(backup["backupPath"], "r") as archive:
                manifest = archive.read("manifest.json")
                ledger_bytes = bytearray(archive.read("fab_operations.sqlite3"))
            ledger_bytes[-1] ^= 1
            with zipfile.ZipFile(
                backup["backupPath"],
                "w",
                zipfile.ZIP_DEFLATED,
            ) as archive:
                archive.writestr("manifest.json", manifest)
                archive.writestr("fab_operations.sqlite3", ledger_bytes)

            with self.assertRaisesRegex(ValueError, "checksum"):
                service.inspect_backup(backup["backupPath"])

    def test_source_complete_backup_includes_and_verifies_document_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = os.path.join(temp_dir, "fab.sqlite3")
            backup_dir = os.path.join(temp_dir, "backups")
            source_path = os.path.join(temp_dir, "receipt.pdf")
            source_bytes = b"%PDF-1.4 source-complete evidence"
            with open(source_path, "wb") as handle:
                handle.write(source_bytes)
            source_sha256 = hashlib.sha256(source_bytes).hexdigest()
            ledger = LocalOperationsLedger(ledger_path)
            document_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "source-complete-1",
                "originalFilename": "receipt.pdf",
                "storagePath": source_path,
                "contentSha256": source_sha256,
            })
            service = LocalBackupService(
                ledger,
                {"fab_local_backup_dir": backup_dir},
            )

            backup = service.create_backup(
                note="source complete",
                require_complete_source_evidence=True,
            )
            inspected = service.inspect_backup(backup["backupPath"])
            source_evidence = inspected["manifest"]["sourceEvidence"]

            self.assertEqual(source_evidence["coverageStatus"], "complete")
            self.assertEqual(source_evidence["totalDocuments"], 1)
            self.assertEqual(source_evidence["includedDocuments"], 1)
            self.assertEqual(source_evidence["includedFiles"], 1)
            self.assertEqual(source_evidence["includedBytes"], len(source_bytes))
            self.assertEqual(source_evidence["entries"][0]["documentId"], document_id)
            with zipfile.ZipFile(backup["backupPath"], "r") as archive:
                evidence_name = source_evidence["entries"][0]["archivePath"]
                self.assertEqual(archive.read(evidence_name), source_bytes)

    def test_source_complete_backup_blocks_missing_evidence_without_partial_archive(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = os.path.join(temp_dir, "fab.sqlite3")
            backup_dir = os.path.join(temp_dir, "backups")
            ledger = LocalOperationsLedger(ledger_path)
            ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "missing-source-1",
                "originalFilename": "missing.pdf",
                "storagePath": os.path.join(temp_dir, "missing.pdf"),
                "contentSha256": "a" * 64,
            })
            service = LocalBackupService(
                ledger,
                {"fab_local_backup_dir": backup_dir},
            )

            with self.assertRaisesRegex(ValueError, "Source-complete backup blocked"):
                service.create_backup(require_complete_source_evidence=True)

            self.assertEqual(os.listdir(backup_dir), [])

    def test_source_checksum_drift_blocks_backup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = os.path.join(temp_dir, "fab.sqlite3")
            source_path = os.path.join(temp_dir, "receipt.pdf")
            with open(source_path, "wb") as handle:
                handle.write(b"changed evidence")
            ledger = LocalOperationsLedger(ledger_path)
            ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "drifted-source-1",
                "originalFilename": "receipt.pdf",
                "storagePath": source_path,
                "contentSha256": hashlib.sha256(b"original evidence").hexdigest(),
            })
            service = LocalBackupService(
                ledger,
                {"fab_local_backup_dir": os.path.join(temp_dir, "backups")},
            )

            with self.assertRaisesRegex(ValueError, "no longer matches"):
                service.create_backup(require_complete_source_evidence=True)

    def test_inspect_rejects_tampered_source_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = os.path.join(temp_dir, "fab.sqlite3")
            backup_dir = os.path.join(temp_dir, "backups")
            source_path = os.path.join(temp_dir, "receipt.pdf")
            source_bytes = b"verified evidence"
            with open(source_path, "wb") as handle:
                handle.write(source_bytes)
            ledger = LocalOperationsLedger(ledger_path)
            ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "tamper-source-1",
                "originalFilename": "receipt.pdf",
                "storagePath": source_path,
                "contentSha256": hashlib.sha256(source_bytes).hexdigest(),
            })
            service = LocalBackupService(
                ledger,
                {"fab_local_backup_dir": backup_dir},
            )
            backup = service.create_backup(require_complete_source_evidence=True)
            with zipfile.ZipFile(backup["backupPath"], "r") as archive:
                members = {
                    name: archive.read(name)
                    for name in archive.namelist()
                }
            evidence_name = next(
                name for name in members
                if name.startswith("source_evidence/")
            )
            members[evidence_name] = b"tampered evidence"
            with zipfile.ZipFile(
                backup["backupPath"],
                "w",
                zipfile.ZIP_DEFLATED,
            ) as archive:
                for name, content in members.items():
                    archive.writestr(name, content)

            with self.assertRaisesRegex(ValueError, "size|checksum"):
                service.inspect_backup(backup["backupPath"])

    def test_inspect_remains_compatible_with_legacy_ledger_only_backup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = os.path.join(temp_dir, "fab.sqlite3")
            backup_dir = os.path.join(temp_dir, "backups")
            os.makedirs(backup_dir)
            ledger = LocalOperationsLedger(ledger_path)
            ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "legacy-backup-1",
                "originalFilename": "legacy.pdf",
            })
            legacy_path = os.path.join(backup_dir, "legacy.zip")
            with open(ledger_path, "rb") as handle:
                ledger_sha256 = hashlib.sha256(handle.read()).hexdigest()
            manifest = {
                "format": BACKUP_FORMAT_V1,
                "createdAt": "2026-07-25T00:00:00Z",
                "ledgerFilename": "fab_operations.sqlite3",
                "ledgerSha256": ledger_sha256,
                "ledgerBytes": os.path.getsize(ledger_path),
            }
            with zipfile.ZipFile(legacy_path, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("manifest.json", json.dumps(manifest))
                archive.write(ledger_path, "fab_operations.sqlite3")

            inspected = LocalBackupService(
                ledger,
                {"fab_local_backup_dir": backup_dir},
            ).inspect_backup(legacy_path)

            self.assertEqual(inspected["manifest"]["format"], BACKUP_FORMAT_V1)

    def test_run_due_creates_one_source_complete_package_then_reports_current(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = os.path.join(temp_dir, "fab.sqlite3")
            source_path = os.path.join(temp_dir, "receipt.pdf")
            source_bytes = b"scheduled backup evidence"
            with open(source_path, "wb") as handle:
                handle.write(source_bytes)
            ledger = LocalOperationsLedger(ledger_path)
            ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "scheduled-source-1",
                "originalFilename": "receipt.pdf",
                "storagePath": source_path,
                "contentSha256": hashlib.sha256(source_bytes).hexdigest(),
            })
            service = LocalBackupService(ledger, {
                "fab_local_backup_dir": os.path.join(temp_dir, "backups"),
                "backup_schedule_interval_hours": 24,
                "backup_require_complete_source_evidence": True,
            })

            first = service.run_due(actor="test-worker")
            second = service.run_due(actor="test-worker")

            self.assertEqual(first["status"], "created")
            self.assertEqual(
                first["backup"]["manifest"]["sourceEvidence"]["coverageStatus"],
                "complete",
            )
            self.assertEqual(second["status"], "not_due")
            self.assertFalse(second["schedule"]["due"])


if __name__ == "__main__":
    unittest.main()
