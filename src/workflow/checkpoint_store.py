import json
import os
import time
import uuid
import hashlib
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from src.document_handling.source_identity import source_document_id


class WorkflowCheckpointStore:
    """Persist autonomous workflow state between runs.

    The checkpoint keeps source-document ids and duplicate fingerprints out of
    the hot path on subsequent scheduled runs, while remaining optional for
    local/manual execution.
    """

    DEFAULT_SKIP_STATUSES = {
        "processed",
        "routed",
        "reconciled",
        "skipped_duplicate",
        "skipped_lower_priority",
        "needs_review_processing_failed",
        "needs_review_low_confidence",
        "needs_review_categorization_failed",
        "needs_review_validation_failed",
        "needs_review_validation_budget_error",
        "needs_review_budget_exceeded",
        "needs_review_data_entry_failed",
        "needs_review_data_entry_error",
        "needs_review_routing_failed",
        "needs_review_no_target_system",
        "needs_review_unmatched_reconciliation",
    }

    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.enabled = self._as_bool(self._config_value("workflow_state_enabled", default=True), True)
        self.autosave = self._as_bool(
            self._config_value("workflow_checkpoint_autosave", default=True),
            True,
        )
        self.path = str(
            self._config_value("workflow_state_file")
            or self._config_value("workflow_checkpoint_file")
            or os.path.join("data", "workflow_state.json")
        )
        self.run_lock_enabled = self._as_bool(
            self._config_value("workflow_run_lock_enabled", default=True),
            True,
        )
        self.run_lock_path = str(
            self._config_value("workflow_run_lock_file")
            or f"{self.path}.lock"
        )
        self.run_lock_stale_seconds = self._positive_float(
            self._config_value("workflow_run_lock_stale_seconds", default=21600),
            21600.0,
        )
        self.fail_closed = self._as_bool(
            self._config_value("workflow_checkpoint_fail_closed", default=True),
            True,
        )
        self._run_lock_token: Optional[str] = None
        self.load_error: Optional[str] = None
        self._state = self._load()
        self.last_save_error: Optional[str] = None
        self.skip_statuses = self._status_set(
            self._config_value("workflow_checkpoint_skip_statuses"),
            self.DEFAULT_SKIP_STATUSES,
        )

    def filter_new_documents(self, source: str, documents: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self.enabled:
            return list(documents)

        new_documents = []
        for document in documents:
            checkpoint = self._state["source_documents"].get(self.source_document_key(source, document))
            if checkpoint is not None and self._checkpoint_status(checkpoint) in self.skip_statuses:
                continue
            new_documents.append(document)
        return new_documents

    def known_documents(self) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        return list(self._state.get("known_documents", []))

    def mark_source_document(
        self,
        source: str,
        document: Dict[str, Any],
        status: str = "processed",
    ) -> bool:
        if not self.enabled:
            return True

        key = self.source_document_key(source, document)
        self._state["source_documents"][key] = {
            "source": source,
            "sourceDocumentId": source_document_id(document),
            "originalFilename": document.get("original_filename") or document.get("filename"),
            "localPath": document.get("local_path"),
            "status": status,
            "lastSeenAt": self._now(),
        }
        return self._autosave()

    def remember_processed_document(self, document: Dict[str, Any]) -> bool:
        if not self.enabled:
            return True

        fingerprint = document.get("duplicate_fingerprint")
        if not fingerprint:
            return True

        known_documents = [
            existing
            for existing in self._state.get("known_documents", [])
            if existing.get("duplicate_fingerprint") != fingerprint
        ]
        known_documents.append(
            {
                "document_id": document.get("document_id"),
                "duplicate_fingerprint": fingerprint,
                "document_type": document.get("document_type"),
                "category": document.get("category"),
                "extracted_data": document.get("extracted_data", {}),
                "ocr_text": document.get("ocr_text", ""),
                "updatedAt": self._now(),
            }
        )
        known_documents_limit = self._positive_int(
            self._config_value("workflow_known_documents_limit", 1000),
            1000,
        )
        self._state["known_documents"] = known_documents[-known_documents_limit:]
        return self._autosave()

    def save(self) -> bool:
        if not self.enabled:
            return True

        tmp_path = f"{self.path}.tmp"
        try:
            directory = os.path.dirname(self.path)
            if directory:
                os.makedirs(directory, exist_ok=True)

            with open(tmp_path, "w", encoding="utf-8") as handle:
                json.dump(
                    self._json_safe(self._state),
                    handle,
                    indent=2,
                    sort_keys=True,
                )
            os.replace(tmp_path, self.path)
        except (OSError, TypeError, ValueError) as exc:
            self.last_save_error = str(exc)
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass
            return False

        self.last_save_error = None
        self.refresh_run_lock()
        return True

    def _autosave(self) -> bool:
        if not self.autosave:
            return True
        return self.save()

    def acquire_run_lock(self) -> bool:
        if not self.run_lock_enabled:
            return True

        directory = os.path.dirname(self.run_lock_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        for attempt in range(2):
            token = uuid.uuid4().hex
            try:
                descriptor = os.open(
                    self.run_lock_path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                )
            except FileExistsError:
                if attempt == 0 and self._remove_stale_run_lock():
                    continue
                return False
            except OSError:
                return False

            try:
                payload = json.dumps(
                    {
                        "token": token,
                        "pid": os.getpid(),
                        "acquiredAt": self._now(),
                    },
                    sort_keys=True,
                ).encode("utf-8")
                os.write(descriptor, payload)
            except OSError:
                os.close(descriptor)
                try:
                    os.remove(self.run_lock_path)
                except OSError:
                    pass
                return False
            else:
                os.close(descriptor)
                self._run_lock_token = token
                return True

        return False

    def release_run_lock(self) -> bool:
        if not self.run_lock_enabled or self._run_lock_token is None:
            return True

        try:
            with open(self.run_lock_path, "r", encoding="utf-8") as handle:
                lock_data = json.load(handle)
            if lock_data.get("token") != self._run_lock_token:
                return False
            os.remove(self.run_lock_path)
        except (OSError, json.JSONDecodeError, AttributeError):
            return False
        finally:
            self._run_lock_token = None

        return True

    def refresh_run_lock(self) -> bool:
        if not self.run_lock_enabled or self._run_lock_token is None:
            return True

        try:
            with open(self.run_lock_path, "r", encoding="utf-8") as handle:
                lock_data = json.load(handle)
            if lock_data.get("token") != self._run_lock_token:
                return False
            os.utime(self.run_lock_path, None)
            return True
        except (OSError, json.JSONDecodeError, AttributeError):
            return False

    def _remove_stale_run_lock(self) -> bool:
        try:
            age_seconds = time.time() - os.path.getmtime(self.run_lock_path)
            if age_seconds <= self.run_lock_stale_seconds:
                return False
            os.remove(self.run_lock_path)
            return True
        except OSError:
            return False

    def source_document_key(self, source: str, document: Dict[str, Any]) -> str:
        identity = source_document_id(document)
        if identity is None:
            identity = f"runtime:{id(document)}"
        return f"{source}:{identity}"

    def _load(self) -> Dict[str, Any]:
        empty = {"source_documents": {}, "known_documents": []}
        if not self.enabled or not os.path.exists(self.path):
            return empty

        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            self.load_error = str(exc)
            return empty

        if not isinstance(data, dict):
            self.load_error = "Checkpoint root must be a JSON object."
            return empty

        source_documents = data.get("source_documents", {})
        known_documents = data.get("known_documents", [])
        if not isinstance(source_documents, dict):
            self.load_error = "Checkpoint source_documents must be a JSON object."
            return empty
        if not isinstance(known_documents, list):
            self.load_error = "Checkpoint known_documents must be a JSON array."
            return empty

        return {
            "source_documents": source_documents,
            "known_documents": known_documents,
        }

    def _config_value(self, key: str, default: Optional[Any] = None) -> Any:
        if key in self.config:
            return self.config[key]

        workflow_config = self.config.get("workflow")
        if isinstance(workflow_config, dict) and key in workflow_config:
            return workflow_config[key]

        app_config = self.config.get("app")
        if isinstance(app_config, dict) and key in app_config:
            return app_config[key]

        return default

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _as_bool(value: Any, default: bool = False) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() not in {"0", "false", "no", "off", ""}
        return bool(value)

    @staticmethod
    def _positive_float(value: Any, default: float) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return default
        return parsed if parsed > 0 else default

    @staticmethod
    def _positive_int(value: Any, default: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return default
        return parsed if parsed > 0 else default

    @classmethod
    def _json_safe(cls, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, bytes):
            return {
                "type": "bytes",
                "size": len(value),
                "sha256": hashlib.sha256(value).hexdigest(),
            }
        if isinstance(value, dict):
            return {
                str(key): cls._json_safe(item)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [cls._json_safe(item) for item in value]
        if isinstance(value, (set, frozenset)):
            normalized = [cls._json_safe(item) for item in value]
            return sorted(
                normalized,
                key=lambda item: json.dumps(item, sort_keys=True, default=str),
            )
        return str(value)

    @staticmethod
    def _checkpoint_status(checkpoint: Any) -> str:
        if isinstance(checkpoint, dict):
            return str(checkpoint.get("status") or "processed")
        return "processed"

    @classmethod
    def _status_set(cls, value: Any, default: set) -> set:
        if value is None:
            return set(default)
        if isinstance(value, str):
            return {status.strip() for status in value.split(",") if status.strip()}
        if isinstance(value, (list, tuple, set)):
            return {str(status) for status in value if str(status)}
        return set(default)
