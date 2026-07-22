import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, Optional
from uuid import uuid4

from src.document_fetchers.drive_fetcher import DriveFetcher
from src.document_fetchers.freshdesk_fetcher import FreshdeskFetcher
from src.document_fetchers.gmail_fetcher import GmailFetcher
from src.operations.local_intake import LocalFolderIntake
from src.operations.local_ledger import LocalOperationsLedger


CONNECTOR_SOURCES = ("gmail", "google_drive", "freshdesk", "google_photos")
CONNECTOR_INTAKE_LEASE_NAME = "local_connector_intake"
SOURCE_ALIASES = {
    "drive": "google_drive",
    "photos": "google_photos",
}


class LocalConnectorIntakeService:
    """Sync configured read-only document connectors into FAB's local ledger."""

    def __init__(
        self,
        ledger: LocalOperationsLedger,
        config: Optional[Dict[str, Any]] = None,
        fetcher_factories: Optional[Dict[str, Callable[[Dict[str, Any]], Any]]] = None,
    ):
        self.ledger = ledger
        self.config = config or {}
        self.fetcher_factories = fetcher_factories or {
            "gmail": GmailFetcher,
            "google_drive": DriveFetcher,
            "freshdesk": FreshdeskFetcher,
        }

    def plan(self) -> Dict[str, Any]:
        sources = [self._source_plan(source) for source in CONNECTOR_SOURCES]
        return {
            "sources": sources,
            "enabledSources": [item["source"] for item in sources if item["enabled"]],
            "syncableSources": [item["source"] for item in sources if item["canSync"]],
            "canSync": any(item["canSync"] for item in sources),
            "externalSubmission": "not_executed",
        }

    def sync(
        self,
        sources: Optional[Iterable[str]] = None,
        actor: str = "local_connector_intake",
        trigger_source: str = "connector_intake",
        workflow_metadata: Optional[Dict[str, Any]] = None,
        step_attempts: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        owner_token = uuid4().hex
        lease = self.ledger.acquire_runtime_lease(
            CONNECTOR_INTAKE_LEASE_NAME,
            owner_token,
            ttl_seconds=_positive_float_config(
                self.config,
                "fab_connector_intake_lease_seconds",
                "operations_connector_intake_lease_seconds",
                "connector_intake_lease_seconds",
                default=21600.0,
            ),
            metadata={"actor": actor, "trigger": trigger_source},
        )
        if not lease.get("acquired"):
            self.ledger.record_audit_event({
                "action": "local_connector_intake.sync_skipped_already_running",
                "entityType": "runtime_lease",
                "entityId": CONNECTOR_INTAKE_LEASE_NAME,
                "details": {
                    "actor": actor,
                    "triggerSource": trigger_source,
                    "lease": lease.get("lease"),
                    "externalSubmission": "not_executed",
                },
            })
            return {
                "success": False,
                "status": "already_running",
                "workflowRunId": None,
                "triggerSource": trigger_source,
                "results": [],
                "summary": _empty_summary(),
                "runtimeLease": lease.get("lease"),
                "externalSubmission": "not_executed",
            }

        result = None
        try:
            result = self._sync_once(
                sources=sources,
                actor=actor,
                trigger_source=trigger_source,
                workflow_metadata=workflow_metadata,
                step_attempts=step_attempts,
            )
            return result
        finally:
            released = self.ledger.release_runtime_lease(
                CONNECTOR_INTAKE_LEASE_NAME,
                owner_token,
            )
            released_lease = {
                **(lease.get("lease") or {}),
                "active": False if released else (lease.get("lease") or {}).get("active"),
                "released": released,
            }
            if isinstance(result, dict):
                result["runtimeLease"] = released_lease
            if not released:
                self.ledger.record_audit_event({
                    "action": "local_connector_intake.lease_release_failed",
                    "entityType": "runtime_lease",
                    "entityId": CONNECTOR_INTAKE_LEASE_NAME,
                    "details": {
                        "actor": actor,
                        "triggerSource": trigger_source,
                        "externalSubmission": "not_executed",
                    },
                })

    def _sync_once(
        self,
        sources: Optional[Iterable[str]] = None,
        actor: str = "local_connector_intake",
        trigger_source: str = "connector_intake",
        workflow_metadata: Optional[Dict[str, Any]] = None,
        step_attempts: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        requested = _normalize_sources(sources)
        selected = requested or [item["source"] for item in self.plan()["sources"] if item["enabled"]]
        if not selected:
            return {
                "success": True,
                "status": "no_sources_enabled",
                "workflowRunId": None,
                "results": [],
                "summary": _empty_summary(),
                "externalSubmission": "not_executed",
            }

        unknown = [source for source in selected if source not in CONNECTOR_SOURCES]
        if unknown:
            raise ValueError(f"Unsupported connector source(s): {', '.join(sorted(unknown))}")

        started_at = _now()
        run_metadata = {
            "requestedSources": selected,
            "actor": actor,
            "externalSubmission": "not_executed",
        }
        run_metadata.update(workflow_metadata or {})
        workflow_run_id = self.ledger.create_workflow_run({
            "status": "running",
            "triggerSource": trigger_source,
            "startedAt": started_at,
            "metadata": run_metadata,
        })
        results = []
        for step_order, source in enumerate(selected, start=1):
            source_plan = self._source_plan(source)
            step_metadata = {
                "label": source_plan.get("label"),
                "mode": source_plan.get("mode"),
                "configured": source_plan.get("configured"),
                "enabled": source_plan.get("enabled"),
                "canSync": source_plan.get("canSync"),
                "externalSubmission": "not_executed",
            }
            workflow_step_id = self.ledger.create_workflow_step({
                "workflowRunId": workflow_run_id,
                "stepKey": f"source:{source}",
                "stage": "collect",
                "status": "pending",
                "attempt": max(1, int((step_attempts or {}).get(source, 1))),
                "stepOrder": step_order,
                "metadata": step_metadata,
            })
            started = time.perf_counter()
            self.ledger.update_workflow_step(workflow_step_id, {
                "status": "running",
                "startedAt": _now(),
            })
            try:
                result = self._sync_source(source)
            except Exception as exc:
                error = _safe_error(exc, self.config) or type(exc).__name__
                result = {
                    "source": source,
                    "sourceAccountId": None,
                    "status": "failed",
                    "seen": 0,
                    "registered": 0,
                    "duplicates": 0,
                    "revisions": 0,
                    "alreadyRegistered": 0,
                    "skipped": 0,
                    "error": error,
                    "externalSubmission": "not_executed",
                }
            duration_ms = int((time.perf_counter() - started) * 1000)
            self.ledger.update_workflow_step(workflow_step_id, {
                "status": _connector_step_status(result.get("status")),
                "finishedAt": _now(),
                "durationMs": duration_ms,
                "errorMessage": result.get("error"),
                "metadata": {
                    **step_metadata,
                    "result": _compact_connector_step_result(result),
                },
            })
            results.append(result)
        summary = _summarize(results)
        failures = [item for item in results if item["status"] in {"failed", "partial"}]
        attention = [
            item for item in results
            if item["status"] in {"needs_configuration", "disabled", "supervision_required"}
        ]
        if failures:
            status = "failed" if len(failures) == len(results) else "completed_with_errors"
        elif attention:
            status = "attention_required"
        else:
            status = "completed"
        finished_at = _now()
        self.ledger.update_workflow_run(workflow_run_id, {
            "status": status,
            "documentsImported": summary["registered"],
            "documentsProcessed": 0,
            "documentsNeedingReview": summary["duplicates"] + summary["revisions"],
            "errorMessage": "; ".join(item.get("error") or item["status"] for item in failures) or None,
            "finishedAt": finished_at,
            "metadata": {
                **(workflow_metadata or {}),
                "actor": actor,
                "requestedSources": selected,
                "summary": summary,
                "sourceStatuses": [
                    {"source": item["source"], "status": item["status"]}
                    for item in results
                ],
                "externalSubmission": "not_executed",
            },
        })
        self.ledger.record_audit_event({
            "action": "local_connector_intake.sync_completed",
            "entityType": "workflow_run",
            "entityId": str(workflow_run_id),
            "details": {
                "actor": actor,
                "status": status,
                "sources": [item["source"] for item in results],
                "sourceStatuses": [
                    {"source": item["source"], "status": item["status"]}
                    for item in results
                ],
                "summary": summary,
                "startedAt": started_at,
                "finishedAt": finished_at,
                "externalSubmission": "not_executed",
            },
        })
        return {
            "success": not failures,
            "status": status,
            "workflowRunId": workflow_run_id,
            "triggerSource": trigger_source,
            "results": results,
            "summary": summary,
            "externalSubmission": "not_executed",
        }

    def _sync_source(self, source: str) -> Dict[str, Any]:
        plan = self._source_plan(source)
        source_account_id = self.ledger.upsert_source_account({
            "sourceType": source,
            "sourceIdentifier": plan["sourceIdentifier"],
            "label": plan["label"],
            "status": "syncing" if plan["canSync"] else plan["status"],
            "lastScanAt": _now(),
            "metadata": {
                "configured": plan["configured"],
                "enabled": plan["enabled"],
                "mode": plan["mode"],
                "nextAction": plan.get("nextAction"),
                "externalSubmission": "not_executed",
            },
        })
        if not plan["canSync"]:
            return {
                "source": source,
                "sourceAccountId": source_account_id,
                "status": plan["status"],
                "seen": 0,
                "registered": 0,
                "duplicates": 0,
                "revisions": 0,
                "alreadyRegistered": 0,
                "skipped": 0,
                "nextAction": plan.get("nextAction"),
                "externalSubmission": "not_executed",
            }

        scan_started_at = _now()
        try:
            fetcher = self.fetcher_factories[source](self.config)
        except Exception as exc:
            return self._source_failure(plan, source_account_id, exc, scan_started_at)

        try:
            documents = fetcher.fetch_documents()
        except Exception as exc:
            return self._source_failure(plan, source_account_id, exc, scan_started_at)
        if not isinstance(documents, list):
            return self._source_failure(
                plan,
                source_account_id,
                TypeError("Connector returned a non-list document payload"),
                scan_started_at,
            )
        registrar = LocalFolderIntake(self.ledger, allowed_extensions={"*"}, source=source)
        counters = {
            "seen": len(documents),
            "registered": 0,
            "duplicates": 0,
            "revisions": 0,
            "alreadyRegistered": 0,
            "skipped": 0,
        }
        registered_documents = []
        registration_errors = []
        for document in documents:
            if not isinstance(document, dict):
                counters["skipped"] += 1
                continue
            root = self._download_root(source, document)
            try:
                result = registrar.register_fetched_document(
                    document,
                    source_account_id=source_account_id,
                    root=root,
                )
            except Exception as exc:
                counters["skipped"] += 1
                registration_errors.append(_safe_error(exc, self.config))
                continue
            if result.get("skipped"):
                counters["skipped"] += 1
                skipped = result["skipped"]
                registration_errors.append(
                    f"{skipped.get('reason') or 'registration_failed'}: {skipped.get('path') or 'unknown path'}"
                )
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
            registered_documents.append(result.get("document"))

        diagnostics = getattr(fetcher, "last_run", {})
        fetch_error = getattr(fetcher, "last_error", None) or getattr(fetcher, "auth_error", None)
        errors = [item for item in [_safe_error(fetch_error, self.config)] if item]
        errors.extend(item for item in registration_errors if item)
        successful_evidence = counters["registered"] + counters["alreadyRegistered"]
        status = "partial" if errors and successful_evidence else "failed" if errors else "ready"
        error = "; ".join(errors)[:500] if errors else None
        self.ledger.upsert_source_account({
            "sourceType": source,
            "sourceIdentifier": plan["sourceIdentifier"],
            "label": plan["label"],
            "status": status,
            "lastScanAt": scan_started_at,
            "lastSeenAt": _now() if documents else None,
            "documentsSeen": counters["seen"],
            "documentsImported": counters["registered"],
            "duplicatesDetected": counters["duplicates"],
            "metadata": {
                "configured": True,
                "enabled": True,
                "mode": plan["mode"],
                "diagnostics": diagnostics,
                "run": counters,
                "error": error,
                "externalSubmission": "not_executed",
            },
        })
        if errors:
            self.ledger.record_audit_event({
                "action": "local_connector_intake.source_failed",
                "entityType": "source_account",
                "entityId": str(source_account_id),
                "details": {
                    "source": source,
                    "status": status,
                    "error": error,
                    "run": counters,
                    "externalSubmission": "not_executed",
                },
            })
        return {
            "source": source,
            "sourceAccountId": source_account_id,
            "status": status,
            **counters,
            "documents": registered_documents,
            "diagnostics": diagnostics,
            "error": error,
            "externalSubmission": "not_executed",
        }

    def _source_failure(
        self,
        plan: Dict[str, Any],
        source_account_id: int,
        error: Exception,
        scan_started_at: str,
    ) -> Dict[str, Any]:
        message = _safe_error(error, self.config)
        self.ledger.upsert_source_account({
            "sourceType": plan["source"],
            "sourceIdentifier": plan["sourceIdentifier"],
            "label": plan["label"],
            "status": "failed",
            "lastScanAt": scan_started_at,
            "metadata": {
                "configured": plan["configured"],
                "enabled": plan["enabled"],
                "mode": plan["mode"],
                "error": message,
                "externalSubmission": "not_executed",
            },
        })
        self.ledger.record_audit_event({
            "action": "local_connector_intake.source_failed",
            "entityType": "source_account",
            "entityId": str(source_account_id),
            "details": {
                "source": plan["source"],
                "status": "failed",
                "error": message,
                "externalSubmission": "not_executed",
            },
        })
        return {
            "source": plan["source"],
            "sourceAccountId": source_account_id,
            "status": "failed",
            "seen": 0,
            "registered": 0,
            "duplicates": 0,
            "revisions": 0,
            "alreadyRegistered": 0,
            "skipped": 0,
            "error": message,
            "externalSubmission": "not_executed",
        }

    def _source_plan(self, source: str) -> Dict[str, Any]:
        configured = self._configured(source)
        enabled = _configured_bool(
            self.config,
            f"{source}_enabled",
            f"source_{source}_enabled",
            default=False,
        )
        source_identifier = self._source_identifier(source)
        label = {
            "gmail": "Gmail",
            "google_drive": "Google Drive",
            "freshdesk": "Freshdesk",
            "google_photos": "Google Photos Picker",
        }[source]
        if source == "google_photos":
            if not enabled:
                status = "disabled"
            elif not configured:
                status = "needs_configuration"
            else:
                status = "supervision_required"
            return {
                "source": source,
                "sourceIdentifier": source_identifier,
                "label": label,
                "configured": configured,
                "enabled": enabled,
                "canSync": False,
                "status": status,
                "mode": "picker_required",
                "nextAction": (
                    "Configure a Picker-scoped OAuth token before starting a supervised selection session."
                    if status == "needs_configuration"
                    else "Start a supervised Google Photos selection from Sources; background whole-library access is no longer available."
                    if status == "supervision_required"
                    else "Enable the supervised Google Photos Picker integration when needed."
                ),
            }
        if not enabled:
            status = "disabled"
        elif not configured:
            status = "needs_configuration"
        else:
            status = "ready"
        return {
            "source": source,
            "sourceIdentifier": source_identifier,
            "label": label,
            "configured": configured,
            "enabled": enabled,
            "canSync": status == "ready",
            "status": status,
            "mode": "read_only_connector",
            "nextAction": _next_action(source, status),
        }

    def _configured(self, source: str) -> bool:
        if source == "gmail":
            return _existing_config_path(self.config, "gmail_credentials_file", "gmail_credentials_path") and _existing_config_path(
                self.config, "gmail_token_file", "gmail_token_path"
            )
        if source == "google_drive":
            return _existing_config_path(
                self.config,
                "google_drive_credentials_file",
                "drive_credentials_path",
            ) and _existing_config_path(
                self.config,
                "google_drive_token_file",
                "drive_token_path",
            ) and bool(
                str(
                    self.config.get("google_drive_folder_id")
                    or self.config.get("drive_folder_id")
                    or ""
                ).strip()
            )
        if source == "freshdesk":
            return bool(self.config.get("freshdesk_api_key") and self.config.get("freshdesk_domain"))
        token_path = _config_path(
            self.config,
            "google_photos_picker_token_file",
            "google_photos_token_file",
            "photos_token_path",
        )
        return _existing_config_path(
            self.config,
            "google_photos_credentials_file",
            "photos_credentials_path",
        ) and bool(token_path and token_path.lower().endswith(".json") and os.path.isfile(token_path))

    def _source_identifier(self, source: str) -> str:
        if source == "gmail":
            return str(self.config.get("gmail_user_id") or "me")
        if source == "google_drive":
            return str(self.config.get("drive_folder_id") or self.config.get("google_drive_folder_id") or "all-files")
        if source == "freshdesk":
            return str(self.config.get("freshdesk_domain") or "unconfigured")
        return "supervised-picker"

    def _download_root(self, source: str, document: Dict[str, Any]) -> str:
        keys = {
            "gmail": ("gmail_attachment_download_dir", "gmail_download_dir"),
            "google_drive": ("google_drive_download_dir", "drive_download_dir"),
            "freshdesk": ("freshdesk_download_dir",),
        }.get(source, ())
        for key in keys:
            value = self.config.get(key)
            if str(value or "").strip():
                return os.path.abspath(os.path.expanduser(os.path.expandvars(str(value))))
        path = document.get("local_path") or document.get("storage_path") or "."
        return os.path.dirname(os.path.abspath(str(path)))


def _normalize_sources(values: Optional[Iterable[str]]) -> list:
    if values is None:
        return []
    if isinstance(values, str):
        values = values.replace(";", ",").split(",")
    normalized = []
    for value in values:
        source = SOURCE_ALIASES.get(str(value or "").strip().lower(), str(value or "").strip().lower())
        if source and source not in normalized:
            normalized.append(source)
    return normalized


def _empty_summary() -> Dict[str, int]:
    return {
        "sources": 0,
        "seen": 0,
        "registered": 0,
        "duplicates": 0,
        "revisions": 0,
        "alreadyRegistered": 0,
        "skipped": 0,
        "failedSources": 0,
    }


def _summarize(results: list) -> Dict[str, int]:
    summary = _empty_summary()
    summary["sources"] = len(results)
    for item in results:
        for key in ("seen", "registered", "duplicates", "revisions", "alreadyRegistered", "skipped"):
            summary[key] += int(item.get(key) or 0)
        if item.get("status") in {"failed", "partial"}:
            summary["failedSources"] += 1
    return summary


def _connector_step_status(status: Any) -> str:
    normalized = str(status or "failed").strip().lower()
    if normalized in {"ready", "completed"}:
        return "completed"
    if normalized in {"failed", "partial", "error", "completed_with_errors"}:
        return "failed"
    return "skipped"


def _compact_connector_step_result(result: Dict[str, Any]) -> Dict[str, Any]:
    keys = (
        "source",
        "sourceAccountId",
        "status",
        "seen",
        "registered",
        "duplicates",
        "revisions",
        "alreadyRegistered",
        "skipped",
        "nextAction",
        "externalSubmission",
    )
    return {
        key: result.get(key)
        for key in keys
        if result.get(key) is not None
    }


def _configured_bool(config: Dict[str, Any], *keys: str, default: bool) -> bool:
    for key in keys:
        if key in config and config.get(key) not in (None, ""):
            value = config.get(key)
            if isinstance(value, str):
                return value.strip().lower() not in {"0", "false", "no", "off", ""}
            return bool(value)
    return default


def _positive_float_config(
    config: Dict[str, Any],
    *keys: str,
    default: float,
) -> float:
    value = next((config.get(key) for key in keys if config.get(key) not in (None, "")), default)
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _existing_config_path(config: Dict[str, Any], *keys: str) -> bool:
    return bool(_config_path(config, *keys))


def _config_path(config: Dict[str, Any], *keys: str) -> Optional[str]:
    for key in keys:
        value = config.get(key)
        if str(value or "").strip():
            path = os.path.abspath(os.path.expanduser(os.path.expandvars(str(value))))
            return path if os.path.isfile(path) else None
    return None


def _next_action(source: str, status: str) -> Optional[str]:
    if status == "ready":
        return None
    if status == "disabled":
        return f"Enable {source} after its read-only credentials and approved source scope are configured."
    if source == "google_drive":
        return (
            "Install the OAuth desktop credentials, confirm folder_id, then run "
            "Authorize-FAB-GoogleDrive.cmd."
        )
    return f"Configure the read-only credentials and token required for {source}."


def _safe_error(error: Any, config: Dict[str, Any]) -> Optional[str]:
    if not error:
        return None
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
    message = re.sub(
        r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+",
        r"\1[REDACTED]",
        message,
    )
    return message[:500]


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
