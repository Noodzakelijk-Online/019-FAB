import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.operations.local_ledger import LocalOperationsLedger


BACKUP_MANIFEST_NAME = "manifest.json"
BACKUP_LEDGER_NAME = "fab_operations.sqlite3"
RESTORE_CONFIRMATION_PHRASE = "RESTORE FAB LOCAL LEDGER"


class LocalBackupService:
    """Create and restore local FAB ledger backups with explicit restore gates."""

    def __init__(self, ledger: LocalOperationsLedger, config: Optional[Dict[str, Any]] = None):
        self.ledger = ledger
        self.config = config or {}
        self.ledger_path = os.path.abspath(ledger.path)
        self.backup_dir = self._backup_dir()
        os.makedirs(self.backup_dir, exist_ok=True)

    def create_backup(self, note: Optional[str] = None) -> Dict[str, Any]:
        timestamp = _timestamp()
        backup_filename = f"fab-local-ledger-backup_{timestamp}.zip"
        backup_path = os.path.join(self.backup_dir, backup_filename)

        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_snapshot_path = os.path.join(temp_dir, BACKUP_LEDGER_NAME)
            self._snapshot_ledger(ledger_snapshot_path)
            ledger_sha256 = _sha256_file(ledger_snapshot_path)
            ledger_bytes = os.path.getsize(ledger_snapshot_path)
            manifest = {
                "format": "fab-local-ledger-backup-v1",
                "createdAt": _now(),
                "ledgerFilename": BACKUP_LEDGER_NAME,
                "ledgerSha256": ledger_sha256,
                "ledgerBytes": ledger_bytes,
                "sourceLedgerBasename": os.path.basename(self.ledger_path),
                "note": note,
                "configSummary": self._safe_config_summary(),
                "safety": {
                    "containsSecrets": False,
                    "containsRawDocumentBytes": False,
                    "restoreRequiresConfirmation": RESTORE_CONFIRMATION_PHRASE,
                },
            }
            manifest_path = os.path.join(temp_dir, BACKUP_MANIFEST_NAME)
            with open(manifest_path, "w", encoding="utf-8") as handle:
                json.dump(manifest, handle, sort_keys=True, indent=2, default=str)

            with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.write(manifest_path, BACKUP_MANIFEST_NAME)
                archive.write(ledger_snapshot_path, BACKUP_LEDGER_NAME)

        self.ledger.record_audit_event({
            "action": "local_backup.created",
            "entityType": "backup",
            "entityId": os.path.basename(backup_path),
            "details": {
                "backupPath": backup_path,
                "ledgerSha256": ledger_sha256,
                "ledgerBytes": ledger_bytes,
                "note": note,
            },
        })
        return {
            "success": True,
            "status": "created",
            "backupPath": backup_path,
            "backupFilename": os.path.basename(backup_path),
            "manifest": manifest,
        }

    def list_backups(self, limit: int = 25) -> Dict[str, Any]:
        backups = []
        for name in os.listdir(self.backup_dir) if os.path.isdir(self.backup_dir) else []:
            if not name.lower().endswith(".zip"):
                continue
            path = os.path.join(self.backup_dir, name)
            try:
                inspected = self.inspect_backup(path)
                backups.append({
                    "backupFilename": name,
                    "backupPath": path,
                    "status": inspected["status"],
                    "createdAt": inspected.get("manifest", {}).get("createdAt"),
                    "ledgerBytes": inspected.get("manifest", {}).get("ledgerBytes"),
                    "ledgerSha256": inspected.get("manifest", {}).get("ledgerSha256"),
                    "sizeBytes": os.path.getsize(path),
                })
            except (OSError, ValueError, zipfile.BadZipFile) as exc:
                backups.append({
                    "backupFilename": name,
                    "backupPath": path,
                    "status": "invalid",
                    "error": str(exc),
                    "sizeBytes": os.path.getsize(path) if os.path.exists(path) else 0,
                })
        backups.sort(key=lambda item: item.get("createdAt") or "", reverse=True)
        return {
            "backupDir": self.backup_dir,
            "restoreConfirmationPhrase": RESTORE_CONFIRMATION_PHRASE,
            "backups": backups[: _bounded_limit(limit)],
        }

    def inspect_backup(self, backup_path: str) -> Dict[str, Any]:
        resolved_path = self._resolve_backup_path(backup_path)
        if not os.path.exists(resolved_path):
            raise ValueError(f"Backup not found: {resolved_path}")
        if not resolved_path.lower().endswith(".zip"):
            raise ValueError("Only .zip local FAB backups are supported")

        with zipfile.ZipFile(resolved_path, "r") as archive:
            self._validate_archive_names(archive.namelist())
            with archive.open(BACKUP_MANIFEST_NAME) as handle:
                manifest = json.loads(handle.read().decode("utf-8"))
            if manifest.get("format") != "fab-local-ledger-backup-v1":
                raise ValueError("Unsupported FAB backup format")
            ledger_info = archive.getinfo(BACKUP_LEDGER_NAME)
            expected_bytes = manifest.get("ledgerBytes")
            if expected_bytes is not None and int(expected_bytes) != int(ledger_info.file_size):
                raise ValueError("Backup ledger size does not match manifest")
            expected_sha256 = str(manifest.get("ledgerSha256") or "").strip().lower()
            if (
                len(expected_sha256) != 64
                or any(character not in "0123456789abcdef" for character in expected_sha256)
            ):
                raise ValueError("Backup manifest has no valid ledger SHA-256")
            with tempfile.TemporaryDirectory() as temp_dir:
                inspected_ledger_path = os.path.join(temp_dir, BACKUP_LEDGER_NAME)
                digest = hashlib.sha256()
                with archive.open(BACKUP_LEDGER_NAME) as source, open(
                    inspected_ledger_path,
                    "wb",
                ) as target:
                    while chunk := source.read(1024 * 1024):
                        digest.update(chunk)
                        target.write(chunk)
                if digest.hexdigest() != expected_sha256:
                    raise ValueError("Backup ledger checksum does not match manifest")
                connection = sqlite3.connect(
                    f"file:{inspected_ledger_path}?mode=ro",
                    uri=True,
                )
                try:
                    integrity = connection.execute("PRAGMA quick_check").fetchone()
                finally:
                    connection.close()
                if not integrity or str(integrity[0]).lower() != "ok":
                    raise ValueError("Backup ledger failed SQLite integrity validation")

        return {
            "success": True,
            "status": "valid",
            "backupPath": resolved_path,
            "backupFilename": os.path.basename(resolved_path),
            "manifest": manifest,
            "restoreConfirmationPhrase": RESTORE_CONFIRMATION_PHRASE,
        }

    def restore_backup(self, backup_path: str, confirmation: str) -> Dict[str, Any]:
        if confirmation != RESTORE_CONFIRMATION_PHRASE:
            return {
                "success": False,
                "status": "requires_confirmation",
                "error": f"Restore requires exact confirmation: {RESTORE_CONFIRMATION_PHRASE}",
            }

        inspected = self.inspect_backup(backup_path)
        resolved_path = inspected["backupPath"]
        pre_restore = self.create_backup(note=f"Automatic pre-restore backup before {os.path.basename(resolved_path)}")

        with tempfile.TemporaryDirectory() as temp_dir:
            restored_ledger_path = os.path.join(temp_dir, BACKUP_LEDGER_NAME)
            with zipfile.ZipFile(resolved_path, "r") as archive:
                with archive.open(BACKUP_LEDGER_NAME) as source, open(restored_ledger_path, "wb") as target:
                    shutil.copyfileobj(source, target)
            expected_sha256 = inspected["manifest"].get("ledgerSha256")
            actual_sha256 = _sha256_file(restored_ledger_path)
            if expected_sha256 and actual_sha256 != expected_sha256:
                raise ValueError("Backup ledger checksum does not match manifest")
            shutil.copy2(restored_ledger_path, self.ledger_path)

        restored_ledger = LocalOperationsLedger(self.ledger_path)
        restored_ledger.record_audit_event({
            "action": "local_backup.restored",
            "entityType": "backup",
            "entityId": os.path.basename(resolved_path),
            "details": {
                "backupPath": resolved_path,
                "preRestoreBackupPath": pre_restore["backupPath"],
                "restoredLedgerSha256": inspected["manifest"].get("ledgerSha256"),
            },
        })
        return {
            "success": True,
            "status": "restored",
            "backupPath": resolved_path,
            "backupFilename": os.path.basename(resolved_path),
            "preRestoreBackupPath": pre_restore["backupPath"],
            "manifest": inspected["manifest"],
        }

    def _snapshot_ledger(self, destination_path: str) -> None:
        source = sqlite3.connect(self.ledger_path)
        destination = sqlite3.connect(destination_path)
        try:
            source.backup(destination)
            destination.commit()
        finally:
            destination.close()
            source.close()

    def _backup_dir(self) -> str:
        value = _config_value(
            self.config,
            "fab_local_backup_dir",
            "operations_backup_dir",
            "backup_base_dir",
        )
        if not value:
            value = os.path.join(os.path.dirname(self.ledger_path), "backups")
        return os.path.abspath(os.path.expanduser(str(value)))

    def _resolve_backup_path(self, backup_path: str) -> str:
        if not backup_path:
            raise ValueError("backupPath is required")
        candidate = os.path.expanduser(str(backup_path))
        if not os.path.isabs(candidate):
            candidate = os.path.join(self.backup_dir, candidate)
        candidate = os.path.abspath(candidate)
        if os.path.commonpath([candidate, self.backup_dir]) != self.backup_dir:
            raise ValueError("Backup path must be inside the configured FAB backup directory")
        return candidate

    @staticmethod
    def _validate_archive_names(names: Any) -> None:
        allowed = {BACKUP_MANIFEST_NAME, BACKUP_LEDGER_NAME}
        normalized_names = set()
        for name in names:
            normalized = os.path.normpath(str(name)).replace("\\", "/")
            if normalized.startswith("../") or normalized == ".." or os.path.isabs(str(name)):
                raise ValueError("Backup archive contains an unsafe path")
            normalized_names.add(normalized.rstrip("/"))
        unexpected = normalized_names - allowed
        if unexpected:
            raise ValueError(f"Backup archive contains unexpected files: {sorted(unexpected)}")
        missing = allowed - normalized_names
        if missing:
            raise ValueError(f"Backup archive is missing required files: {sorted(missing)}")

    def _safe_config_summary(self) -> Dict[str, Any]:
        keys = (
            "fab_local_api_host",
            "fab_local_api_port",
            "fab_local_intake_paths",
            "fab_local_intake_extensions",
            "operations_local_intake_paths",
            "operations_intake_paths",
            "operations_scanner_folder",
            "operations_scanner_watch_folder",
            "scanner_folder",
            "scanner_watch_folder",
            "review_stale_hours",
            "document_stale_hours",
            "routing_stale_hours",
            "workflow_stale_hours",
        )
        summary = {"ledgerBasename": os.path.basename(self.ledger_path), "backupDir": self.backup_dir}
        for key in keys:
            value = _config_value(self.config, key)
            if value not in (None, ""):
                summary[key] = value
        return summary


def _config_value(config: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = config.get(key)
        if value not in (None, ""):
            return value
    for key in keys:
        if "_" not in key:
            continue
        section, option = key.split("_", 1)
        section_values = config.get(section)
        if isinstance(section_values, dict):
            value = section_values.get(option)
            if value not in (None, ""):
                return value
    return None


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bounded_limit(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = 25
    return max(1, min(parsed, 100))


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
