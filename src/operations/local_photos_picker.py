from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlparse

from src.document_fetchers.photos_picker_client import (
    GooglePhotosPickerClient,
    UnsupportedPickerMedia,
)
from src.operations.local_connector_intake import LocalConnectorIntakeService
from src.operations.local_intake import LocalFolderIntake
from src.operations.local_ledger import LocalOperationsLedger


TRIGGER_SOURCE = "google_photos_picker"
ACTIVE_SESSION_STATUSES = (
    "creating",
    "awaiting_user_selection",
    "collecting",
    "partial",
    "completed_cleanup_required",
)
TERMINAL_SESSION_STATUSES = (
    "completed",
    "completed_with_skips",
    "completed_no_selection",
    "cancelled",
)
MAX_RECORDED_ERRORS = 25


class LocalGooglePhotosPickerService:
    """Persist supervised Picker sessions and register selected photos as FAB evidence."""

    def __init__(
        self,
        ledger: LocalOperationsLedger,
        config: Optional[Dict[str, Any]] = None,
        client_factory: Optional[Callable[[Dict[str, Any]], Any]] = None,
    ):
        self.ledger = ledger
        self.config = config or {}
        self.client_factory = client_factory or GooglePhotosPickerClient

    def plan(self) -> Dict[str, Any]:
        connector_plan = LocalConnectorIntakeService(self.ledger, self.config).plan()
        photos = next(
            item for item in connector_plan["sources"]
            if item["source"] == "google_photos"
        )
        sessions = self.list_sessions(limit=25)
        active = [item for item in sessions if _session_requires_attention(item)]
        return {
            "source": photos,
            "canStartSession": bool(
                photos["enabled"] and photos["configured"] and not active
            ),
            "activeSessionCount": len(active),
            "latestSession": sessions[0] if sessions else None,
            "externalSubmission": "not_executed",
        }

    def list_sessions(self, limit: int = 25) -> list:
        rows = self.ledger.list_workflow_runs(
            trigger_source=TRIGGER_SOURCE,
            limit=limit,
        )
        return [self._public_session(row) for row in rows]

    def get_session(self, workflow_run_id: int) -> Optional[Dict[str, Any]]:
        row = self.ledger.get_workflow_run(workflow_run_id)
        if not row or row.get("trigger_source") != TRIGGER_SOURCE:
            return None
        return self._public_session(row)

    def create_session(self, actor: str = "local_user") -> Dict[str, Any]:
        plan = self.plan()
        photos = plan["source"]
        if not photos["enabled"]:
            raise ValueError("Google Photos Picker is disabled.")
        if not photos["configured"]:
            raise ValueError("Google Photos Picker credentials and JSON token are not ready.")
        active = next(
            (item for item in self.list_sessions(limit=25) if _session_requires_attention(item)),
            None,
        )
        if active:
            return {
                "success": True,
                "status": "already_active",
                "session": active,
                "externalSubmission": "not_executed",
            }

        source_account_id = self.ledger.upsert_source_account({
            "sourceType": "google_photos",
            "sourceIdentifier": "supervised-picker",
            "label": "Google Photos Picker",
            "status": "creating",
            "lastScanAt": _now(),
            "metadata": {
                "mode": "supervised_picker",
                "externalSubmission": "not_executed",
            },
        })
        workflow_run_id = self.ledger.create_workflow_run({
            "status": "creating",
            "triggerSource": TRIGGER_SOURCE,
            "startedAt": _now(),
            "metadata": {
                "actor": actor,
                "sourceAccountId": source_account_id,
                "externalSubmission": "not_executed",
            },
        })
        client = None
        provider_session = None
        try:
            client = self.client_factory(self.config)
            provider_session = client.create_session()
            picker_uri = _picker_uri(provider_session.get("pickerUri"), self.config)
        except Exception as exc:
            provider_session_id = str((provider_session or {}).get("id") or "").strip()
            if provider_session_id and client is not None:
                try:
                    client.delete_session(provider_session_id)
                except Exception:
                    pass
            return self._fail_session(
                workflow_run_id,
                source_account_id,
                exc,
                action="session_create_failed",
            )

        metadata = {
            "actor": actor,
            "sourceAccountId": source_account_id,
            "providerSessionId": provider_session["id"],
            "pickerUri": picker_uri,
            "pollingConfig": provider_session.get("pollingConfig") or {},
            "mediaItemsSet": bool(provider_session.get("mediaItemsSet")),
            "providerSessionDeleted": False,
            "externalSubmission": "not_executed",
        }
        self.ledger.update_workflow_run(workflow_run_id, {
            "status": "awaiting_user_selection",
            "metadata": metadata,
        })
        self.ledger.upsert_source_account({
            "sourceType": "google_photos",
            "sourceIdentifier": "supervised-picker",
            "label": "Google Photos Picker",
            "status": "awaiting_user_selection",
            "lastScanAt": _now(),
            "metadata": {
                "mode": "supervised_picker",
                "activeWorkflowRunId": workflow_run_id,
                "externalSubmission": "not_executed",
            },
        })
        self.ledger.record_audit_event({
            "action": "local_photos_picker.session_created",
            "entityType": "workflow_run",
            "entityId": str(workflow_run_id),
            "details": {
                "actor": actor,
                "sourceAccountId": source_account_id,
                "providerSessionId": provider_session["id"],
                "externalSubmission": "not_executed",
            },
        })
        return {
            "success": True,
            "status": "awaiting_user_selection",
            "session": self.get_session(workflow_run_id),
            "externalSubmission": "not_executed",
        }

    def collect_session(
        self,
        workflow_run_id: int,
        actor: str = "local_user",
    ) -> Dict[str, Any]:
        run = self._require_session(workflow_run_id)
        if run.get("status") in TERMINAL_SESSION_STATUSES:
            return {
                "success": True,
                "status": "already_complete",
                "session": self._public_session(run),
                "externalSubmission": "not_executed",
            }
        metadata = dict(run.get("metadata") or {})
        provider_session_id = str(metadata.get("providerSessionId") or "").strip()
        source_account_id = int(metadata.get("sourceAccountId") or 0)
        if not provider_session_id or not source_account_id:
            return self._fail_session(
                workflow_run_id,
                source_account_id,
                ValueError("Picker workflow is missing provider session provenance."),
                action="session_collect_failed",
            )

        self.ledger.update_workflow_run(workflow_run_id, {"status": "collecting"})
        try:
            client = self.client_factory(self.config)
            provider_session = client.get_session(provider_session_id)
        except Exception as exc:
            return self._fail_session(
                workflow_run_id,
                source_account_id,
                exc,
                action="session_poll_failed",
                metadata=metadata,
            )
        metadata.update({
            "actor": actor,
            "lastPolledAt": _now(),
            "pollingConfig": provider_session.get("pollingConfig") or metadata.get("pollingConfig") or {},
            "mediaItemsSet": bool(provider_session.get("mediaItemsSet")),
        })
        if not metadata["mediaItemsSet"]:
            self.ledger.update_workflow_run(workflow_run_id, {
                "status": "awaiting_user_selection",
                "metadata": metadata,
            })
            return {
                "success": True,
                "status": "awaiting_user_selection",
                "session": self.get_session(workflow_run_id),
                "externalSubmission": "not_executed",
            }

        try:
            listed = client.list_media_items(provider_session_id)
        except Exception as exc:
            return self._fail_session(
                workflow_run_id,
                source_account_id,
                exc,
                action="media_list_failed",
                metadata=metadata,
            )

        items = listed.get("items") or []
        registrar = LocalFolderIntake(
            self.ledger,
            allowed_extensions={"*"},
            source="google_photos",
        )
        counters = {
            "seen": len(items),
            "registered": 0,
            "duplicates": 0,
            "revisions": 0,
            "alreadyRegistered": 0,
            "skipped": 0,
        }
        errors = []
        error_count = 0
        documents = []

        def record_error(message: Any) -> None:
            nonlocal error_count
            error_count += 1
            if len(errors) < MAX_RECORDED_ERRORS:
                errors.append(str(message)[:500])

        for item in items:
            try:
                downloaded = client.download_media_item(item, provider_session_id)
            except UnsupportedPickerMedia:
                counters["skipped"] += 1
                continue
            except Exception as exc:
                counters["skipped"] += 1
                record_error(_safe_error(exc, self.config))
                continue
            try:
                result = registrar.register_fetched_document(
                    downloaded,
                    source_account_id=source_account_id,
                    root=client.download_dir,
                )
            except Exception as exc:
                counters["skipped"] += 1
                record_error(_safe_error(exc, self.config))
                continue
            if result.get("skipped"):
                counters["skipped"] += 1
                skipped = result["skipped"]
                record_error(skipped.get("reason") or "registration_failed")
                continue
            result_status = result.get("status")
            if result_status == "already_registered":
                counters["alreadyRegistered"] += 1
            else:
                counters["registered"] += 1
                if result_status == "duplicate":
                    counters["duplicates"] += 1
                elif result_status == "revision":
                    counters["revisions"] += 1
            documents.append(result.get("document"))
        if listed.get("truncated"):
            record_error("Selected media exceeded the configured page or item completeness limit.")

        cleanup_error = None
        session_deleted = False
        if not error_count:
            try:
                client.delete_session(provider_session_id)
                session_deleted = True
            except Exception as exc:
                cleanup_error = _safe_error(exc, self.config)
                record_error(cleanup_error)

        if error_count:
            evidence_count = counters["registered"] + counters["alreadyRegistered"]
            status = (
                "completed_cleanup_required"
                if cleanup_error and error_count == 1
                else "partial" if evidence_count else "failed"
            )
        elif not items:
            status = "completed_no_selection"
        elif counters["skipped"]:
            status = "completed_with_skips"
        else:
            status = "completed"
        metadata.update({
            "providerSessionDeleted": session_deleted,
            "selectedItemCount": len(items),
            "listPages": listed.get("pages"),
            "listTruncated": bool(listed.get("truncated")),
            "counts": counters,
            "lastCollectedAt": _now(),
            "errors": errors,
            "errorCount": error_count,
            "errorDetailsTruncated": error_count > len(errors),
            "externalSubmission": "not_executed",
        })
        terminal = status in TERMINAL_SESSION_STATUSES
        self.ledger.update_workflow_run(workflow_run_id, {
            "status": status,
            "documentsImported": counters["registered"],
            "documentsProcessed": 0,
            "documentsNeedingReview": counters["duplicates"] + counters["revisions"],
            "errorMessage": _error_summary(errors, error_count),
            "finishedAt": _now() if terminal else None,
            "metadata": metadata,
        })
        self.ledger.upsert_source_account({
            "sourceType": "google_photos",
            "sourceIdentifier": "supervised-picker",
            "label": "Google Photos Picker",
            "status": "ready" if terminal else "partial",
            "lastScanAt": _now(),
            "lastSeenAt": _now() if items else None,
            "documentsSeen": counters["seen"],
            "documentsImported": counters["registered"],
            "duplicatesDetected": counters["duplicates"],
            "metadata": {
                "mode": "supervised_picker",
                "lastWorkflowRunId": workflow_run_id,
                "lastStatus": status,
                "counts": counters,
                "externalSubmission": "not_executed",
            },
        })
        self.ledger.record_audit_event({
            "action": "local_photos_picker.selection_collected",
            "entityType": "workflow_run",
            "entityId": str(workflow_run_id),
            "details": {
                "actor": actor,
                "status": status,
                "providerSessionDeleted": session_deleted,
                "counts": counters,
                "errors": errors,
                "errorCount": error_count,
                "errorDetailsTruncated": error_count > len(errors),
                "externalSubmission": "not_executed",
            },
        })
        return {
            "success": error_count == 0,
            "status": status,
            "session": self.get_session(workflow_run_id),
            "summary": counters,
            "documents": documents,
            "externalSubmission": "not_executed",
        }

    def cancel_session(
        self,
        workflow_run_id: int,
        actor: str = "local_user",
    ) -> Dict[str, Any]:
        run = self._require_session(workflow_run_id)
        if run.get("status") in TERMINAL_SESSION_STATUSES:
            return {
                "success": True,
                "status": (
                    "already_cancelled"
                    if run.get("status") == "cancelled"
                    else "already_complete"
                ),
                "session": self._public_session(run),
                "externalSubmission": "not_executed",
            }
        metadata = dict(run.get("metadata") or {})
        provider_session_id = str(metadata.get("providerSessionId") or "").strip()
        if provider_session_id and not metadata.get("providerSessionDeleted"):
            try:
                self.client_factory(self.config).delete_session(provider_session_id)
            except Exception as exc:
                return self._fail_session(
                    workflow_run_id,
                    int(metadata.get("sourceAccountId") or 0),
                    exc,
                    action="session_cancel_failed",
                    metadata=metadata,
                )
        metadata.update({
            "actor": actor,
            "providerSessionDeleted": True,
            "cancelledAt": _now(),
        })
        self.ledger.update_workflow_run(workflow_run_id, {
            "status": "cancelled",
            "finishedAt": _now(),
            "metadata": metadata,
        })
        source_account_id = int(metadata.get("sourceAccountId") or 0)
        if source_account_id:
            self.ledger.upsert_source_account({
                "sourceType": "google_photos",
                "sourceIdentifier": "supervised-picker",
                "label": "Google Photos Picker",
                "status": "ready",
                "lastScanAt": _now(),
                "metadata": {
                    "mode": "supervised_picker",
                    "lastWorkflowRunId": workflow_run_id,
                    "lastStatus": "cancelled",
                    "externalSubmission": "not_executed",
                },
            })
        self.ledger.record_audit_event({
            "action": "local_photos_picker.session_cancelled",
            "entityType": "workflow_run",
            "entityId": str(workflow_run_id),
            "details": {
                "actor": actor,
                "providerSessionId": provider_session_id,
                "externalSubmission": "not_executed",
            },
        })
        return {
            "success": True,
            "status": "cancelled",
            "session": self.get_session(workflow_run_id),
            "externalSubmission": "not_executed",
        }

    def _require_session(self, workflow_run_id: int) -> Dict[str, Any]:
        run = self.ledger.get_workflow_run(workflow_run_id)
        if not run or run.get("trigger_source") != TRIGGER_SOURCE:
            raise LookupError(f"Google Photos Picker workflow run {workflow_run_id} was not found.")
        return run

    def _fail_session(
        self,
        workflow_run_id: int,
        source_account_id: int,
        error: Exception,
        action: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        message = _safe_error(error, self.config)
        existing = self.ledger.get_workflow_run(workflow_run_id) or {}
        merged_metadata = dict(metadata or existing.get("metadata") or {})
        merged_metadata.update({
            "lastError": message,
            "lastErrorAt": _now(),
            "externalSubmission": "not_executed",
        })
        self.ledger.update_workflow_run(workflow_run_id, {
            "status": "failed",
            "errorMessage": message,
            "metadata": merged_metadata,
        })
        if source_account_id:
            self.ledger.upsert_source_account({
                "sourceType": "google_photos",
                "sourceIdentifier": "supervised-picker",
                "label": "Google Photos Picker",
                "status": "failed",
                "lastScanAt": _now(),
                "metadata": {
                    "mode": "supervised_picker",
                    "lastWorkflowRunId": workflow_run_id,
                    "error": message,
                    "externalSubmission": "not_executed",
                },
            })
        self.ledger.record_audit_event({
            "action": f"local_photos_picker.{action}",
            "entityType": "workflow_run",
            "entityId": str(workflow_run_id),
            "details": {
                "error": message,
                "externalSubmission": "not_executed",
            },
        })
        return {
            "success": False,
            "status": "failed",
            "error": message,
            "session": self.get_session(workflow_run_id),
            "externalSubmission": "not_executed",
        }

    @staticmethod
    def _public_session(row: Dict[str, Any]) -> Dict[str, Any]:
        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        return {
            "id": row.get("id"),
            "status": row.get("status"),
            "providerSessionId": metadata.get("providerSessionId"),
            "pickerUri": metadata.get("pickerUri") if not metadata.get("providerSessionDeleted") else None,
            "pollingConfig": metadata.get("pollingConfig") or {},
            "mediaItemsSet": bool(metadata.get("mediaItemsSet")),
            "providerSessionDeleted": bool(metadata.get("providerSessionDeleted")),
            "selectedItemCount": int(metadata.get("selectedItemCount") or 0),
            "counts": metadata.get("counts") or {},
            "error": row.get("error_message"),
            "startedAt": row.get("started_at"),
            "finishedAt": row.get("finished_at"),
            "updatedAt": row.get("updated_at"),
            "externalSubmission": "not_executed",
        }


def _picker_uri(value: Any, config: Dict[str, Any]) -> str:
    uri = str(value or "").strip()
    parsed = urlparse(uri)
    if (
        parsed.scheme.lower() != "https"
        or str(parsed.hostname or "").lower() != "photos.google.com"
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Google Photos Picker returned an untrusted pickerUri.")
    autoclose = _as_bool(config.get("google_photos_picker_autoclose", True))
    if autoclose and uri and not uri.rstrip("/").endswith("/autoclose"):
        return f"{uri.rstrip('/')}/autoclose"
    return uri


def _session_requires_attention(session: Dict[str, Any]) -> bool:
    if session.get("status") in ACTIVE_SESSION_STATUSES:
        return True
    return bool(
        session.get("status") == "failed"
        and session.get("providerSessionId")
        and not session.get("providerSessionDeleted")
    )


def _safe_error(error: Any, config: Dict[str, Any]) -> str:
    message = f"{type(error).__name__}: {error}"
    for key, value in config.items():
        if not re.search(r"(?i)(token|secret|password|api[_-]?key|authorization|credential)", str(key)):
            continue
        secret = str(value or "")
        if len(secret) >= 4:
            message = message.replace(secret, "[REDACTED]")
    message = re.sub(
        r"(?i)((?:access[_-]?token|refresh[_-]?token|token|password|secret|(?:x[_-]?)?api[_-]?key)\s*[:=]\s*)[^&,;\s]+",
        r"\1[REDACTED]",
        message,
    )
    message = re.sub(
        r"(?i)(authorization\s*[:=]\s*)(?:bearer\s+)?[^,;\s]+",
        r"\1[REDACTED]",
        message,
    )
    return message[:500]


def _as_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() not in {"", "0", "false", "no", "off"}
    return bool(value)


def _error_summary(errors: list, error_count: int) -> Optional[str]:
    if not error_count:
        return None
    summary = "; ".join(str(item) for item in errors)
    omitted = error_count - len(errors)
    if omitted > 0:
        summary = f"{summary}; {omitted} additional error(s) omitted"
    return summary[:500]


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
