import re
import signal
import time
from datetime import datetime, timezone
from typing import Any, Dict

from src.data_entry.posting_executor import PostingExecutor
from src.operations.local_autonomy import LocalAutonomousService
from src.operations.local_compliance import LocalComplianceService
from src.operations.local_connector_intake import LocalConnectorIntakeService
from src.operations.drive_wave_delivery import DriveWaveDeliveryService
from src.operations.local_exports import LocalExportAttemptService
from src.operations.local_notifications import LocalNotificationService
from src.operations.local_reporting import LocalScheduledReportService
from src.operations.local_runtime import build_local_operations_ledger
from src.operations.local_workflow_recovery import LocalWorkflowRecoveryScheduler
from src.storage.database import Database
from src.workflow.controller import WorkflowController


class FabWorker:
    """Simple local scheduler for repeated FAB workflow, retry handling, and approved posting execution."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.interval_seconds = int(self.config.get("worker_interval_seconds", 300))
        self.run_once = _as_bool(self.config.get("worker_run_once", False))
        self.process_postings = _as_bool(self.config.get("worker_process_approved_postings", True))
        self.process_retries = _as_bool(self.config.get("worker_process_due_retries", True))
        self.operations_ledger = build_local_operations_ledger(self.config)
        self.run_legacy_workflow = _as_bool(self.config.get("worker_run_legacy_workflow", True))
        self.sync_source_connectors = bool(self.operations_ledger) and _as_bool(
            self.config.get("worker_sync_source_connectors", True)
        )
        self.source_connectors = _list_config(
            self.config,
            "worker_source_connectors",
            "source_connectors",
        )
        self.run_local_autonomy = bool(self.operations_ledger) and _as_bool(
            self.config.get("worker_run_local_autonomy", True)
        )
        self.recover_workflows = bool(self.operations_ledger) and _as_bool(
            self.config.get("worker_recover_workflows", True)
        )
        self.recovery_batch_limit = _bounded_positive_int(
            self.config.get("worker_recovery_batch_limit"),
            default=5,
            maximum=50,
        )
        self.include_wave_plan = _as_bool(self.config.get("worker_include_wave_plan", True))
        self.include_wave_sync = _as_bool(self.config.get("worker_include_wave_sync", True))
        self.generate_scheduled_reports = bool(self.operations_ledger) and _as_bool(
            self.config.get("worker_generate_scheduled_reports", True)
        )
        self.refresh_notifications = bool(self.operations_ledger) and _as_bool(
            self.config.get("worker_refresh_notifications", True)
        )
        self.assess_compliance = bool(self.operations_ledger) and _as_bool(
            self.config.get("worker_assess_compliance", True)
        )
        self.archive_verified_drive_sources = bool(self.operations_ledger) and _as_bool(
            self.config.get("worker_archive_verified_drive_sources", True)
        )
        self.process_legacy_postings = _as_bool(
            self.config.get("worker_process_legacy_postings", self.operations_ledger is None)
        )
        self.database = Database(config) if self.process_legacy_postings or not self.operations_ledger else None
        self._stop_requested = False
        self._recovery_held_connector_sources = set()

    def install_signal_handlers(self) -> None:
        def handle_stop(signum, frame):
            self._stop_requested = True
            self._record_audit("stop_requested", {"signal": signum}, "Worker stop requested")
        signal.signal(signal.SIGINT, handle_stop)
        signal.signal(signal.SIGTERM, handle_stop)

    def run(self) -> None:
        self.install_signal_handlers()
        self._record_audit("started", {"intervalSeconds": self.interval_seconds}, "Worker started")
        while not self._stop_requested:
            started_at = self._now()
            self._recovery_held_connector_sources = set()
            self._record_audit("cycle_started", {"startedAt": started_at}, "Worker cycle started")
            stage_errors = []
            stages = (
                ("workflow_recovery", self._recover_workflows),
                ("connector_intake", self._sync_source_connectors),
                ("legacy_workflow", self._run_legacy_workflow),
                ("local_autonomy", self._run_local_autonomy),
                ("scheduled_reports", self._process_scheduled_reports),
                ("compliance", self._assess_compliance),
                ("notifications", self._refresh_notifications),
                ("operations_exports", self._process_operations_exports),
                ("drive_wave_archive", self._archive_verified_drive_sources),
                ("legacy_queue", self._process_legacy_queue),
            )
            for stage, action in stages:
                try:
                    action()
                except Exception as exc:
                    safe_error = _safe_worker_error(exc, self.config)
                    failure = {"stage": stage, "error": safe_error}
                    stage_errors.append(failure)
                    self._record_audit(
                        "stage_failed",
                        {"startedAt": started_at, **failure},
                        f"Worker stage {stage} failed: {safe_error}",
                    )
            if stage_errors:
                self._record_audit(
                    "cycle_finished_with_error",
                    {
                        "startedAt": started_at,
                        "completedAt": self._now(),
                        "stageErrors": stage_errors,
                    },
                    "Worker cycle finished with one or more stage errors",
                )
            else:
                self._record_audit(
                    "cycle_completed",
                    {"startedAt": started_at, "completedAt": self._now()},
                    "Worker cycle completed",
                )
            if self.run_once:
                break
            self._sleep_until_next_cycle()
        self._record_audit("stopped", {}, "Worker stopped")

    def _run_legacy_workflow(self) -> None:
        if not self.run_legacy_workflow:
            return
        WorkflowController(self.config).run_workflow()

    def _sync_source_connectors(self) -> None:
        if not self.sync_source_connectors or not self.operations_ledger:
            return
        service = LocalConnectorIntakeService(
            self.operations_ledger,
            self.config,
        )
        selected_sources = list(self.source_connectors)
        if not selected_sources:
            selected_sources = list(service.plan().get("syncableSources") or [])
        selected_sources = [
            source
            for source in selected_sources
            if source not in self._recovery_held_connector_sources
        ]
        if not selected_sources:
            status = (
                "held_back_by_recovery"
                if self._recovery_held_connector_sources
                else "no_syncable_sources"
            )
            self._record_audit(
                "connector_intake_cycle",
                {
                    "success": True,
                    "status": status,
                    "workflowRunId": None,
                    "summary": {},
                    "sources": [],
                    "heldBackSources": sorted(self._recovery_held_connector_sources),
                    "externalSubmission": "not_executed",
                },
                f"Connector intake cycle ended as {status}",
            )
            return
        result = service.sync(
            sources=selected_sources,
            actor="local_worker",
        )
        self._record_audit(
            "connector_intake_cycle",
            _compact_connector_intake(result),
            f"Connector intake cycle ended as {result.get('status')}",
        )
        if not result.get("success"):
            raise RuntimeError("One or more configured source connectors failed")

    def _recover_workflows(self) -> None:
        if not self.recover_workflows or not self.operations_ledger:
            return
        result = LocalWorkflowRecoveryScheduler(
            self.operations_ledger,
            self.config,
            intake_paths=_list_config(
                self.config,
                "fab_local_intake_paths",
                "operations_local_intake_paths",
                "local_intake_paths",
            ),
            intake_extensions=_list_config(
                self.config,
                "fab_local_intake_extensions",
                "operations_local_intake_extensions",
                "local_intake_extensions",
            ),
        ).run_due(
            actor="local_worker",
            limit=self.recovery_batch_limit,
        )
        self._recovery_held_connector_sources = set(
            result.get("connectorSourcesHeldBack") or []
        )
        self._record_audit(
            "workflow_recovery_cycle",
            _compact_workflow_recovery(result),
            f"Governed workflow recovery ended as {result.get('status')}",
        )
        if result.get("status") == "already_running":
            return
        if not result.get("success"):
            raise RuntimeError("One or more due governed workflow recoveries failed")

    def _run_local_autonomy(self) -> None:
        if not self.run_local_autonomy or not self.operations_ledger:
            return
        autonomy_config = dict(self.config)
        # The worker's approved-export stage remains the sole external executor.
        autonomy_config["fab_autonomy_execute_approved_exports"] = False
        result = LocalAutonomousService(
            self.operations_ledger,
            autonomy_config,
            intake_paths=_list_config(
                self.config,
                "fab_local_intake_paths",
                "operations_local_intake_paths",
                "local_intake_paths",
            ),
            intake_extensions=_list_config(
                self.config,
                "fab_local_intake_extensions",
                "operations_local_intake_extensions",
                "local_intake_extensions",
            ),
        ).run_cycle(
            limit=25,
            include_wave_plan=self.include_wave_plan,
            include_wave_sync=self.include_wave_sync,
        )
        self._record_audit(
            "autonomy_cycle",
            _compact_autonomy_cycle(result),
            f"Local autonomous cycle ended as {result.get('status')}",
        )

    def _process_operations_exports(self) -> None:
        if not self.operations_ledger:
            return
        service = LocalExportAttemptService(self.operations_ledger, self.config)
        preparation = service.prepare_ready_exports(limit=25)
        self._record_audit(
            "export_preparation_cycle",
            _compact_export_preparation(preparation),
            "Operations-ledger export preparation completed",
        )
        if self.process_postings:
            result = service.process_approved_attempts(limit=20, actor="local_worker")
            self._record_audit(
                "approved_export_cycle",
                _compact_export_execution(result),
                "Operations-ledger approved export cycle completed",
            )

    def _process_scheduled_reports(self) -> None:
        if not self.generate_scheduled_reports or not self.operations_ledger:
            return
        result = LocalScheduledReportService(self.operations_ledger, self.config).run_due(
            actor="local_worker",
        )
        self._record_audit(
            "scheduled_report_cycle",
            _compact_scheduled_report(result),
            f"Scheduled report cycle ended as {result.get('status')}",
        )
        if not result.get("success"):
            raise RuntimeError(result.get("error") or "Scheduled report generation failed")

    def _archive_verified_drive_sources(self) -> None:
        if not self.archive_verified_drive_sources or not self.operations_ledger:
            return
        result = DriveWaveDeliveryService(self.operations_ledger, self.config).archive_ready(
            limit=25,
            actor="local_worker",
        )
        self._record_audit(
            "drive_wave_archive_cycle",
            result,
            f"Verified Drive archive cycle ended as {result.get('status')}",
        )

    def _refresh_notifications(self) -> None:
        if not self.refresh_notifications or not self.operations_ledger:
            return
        result = LocalNotificationService(self.operations_ledger, self.config).refresh(
            actor="local_worker",
        )
        self._record_audit(
            "notification_cycle",
            _compact_notification_refresh(result),
            "Local notification refresh completed",
        )

    def _assess_compliance(self) -> None:
        if not self.assess_compliance or not self.operations_ledger:
            return
        result = LocalComplianceService(self.operations_ledger, self.config).assess(
            actor="local_worker",
        )
        self._record_audit(
            "compliance_cycle",
            _compact_compliance_assessment(result),
            f"Local compliance cycle ended as {result.get('status')}",
        )

    def _process_legacy_queue(self) -> None:
        if not self.process_legacy_postings:
            return
        posting_executor = PostingExecutor(self.config)
        if self.process_retries:
            retry_result = posting_executor.process_due_retries()
            self._record_audit("legacy_retry_cycle", retry_result, "Legacy retry cycle completed")
        if self.process_postings:
            posting_result = posting_executor.process_approved_attempts()
            self._record_audit(
                "legacy_approved_posting_cycle",
                posting_result,
                "Legacy approved posting cycle completed",
            )

    def _record_audit(self, action: str, details: Dict[str, Any], reason: str) -> None:
        if self.operations_ledger:
            self.operations_ledger.record_audit_event({
                "action": f"local_worker.{action}",
                "entityType": "worker",
                "entityId": "local",
                "details": details,
                "reason": reason,
                "actor": "system",
            })
            return
        if not self.database:
            return
        self.database.add_audit_log(
            "worker",
            "local",
            action,
            None,
            details,
            reason,
            "system",
        )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _sleep_until_next_cycle(self) -> None:
        slept = 0
        while slept < self.interval_seconds and not self._stop_requested:
            time.sleep(1)
            slept += 1


def _compact_export_preparation(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "requested": result.get("requested", 0),
        "prepared": result.get("prepared", 0),
        "alreadyPrepared": result.get("alreadyPrepared", 0),
        "blocked": result.get("blocked", 0),
        "externalSubmission": result.get("externalSubmission", "not_executed"),
    }


def _compact_export_execution(result: Dict[str, Any]) -> Dict[str, Any]:
    processed = []
    for item in result.get("processed") or []:
        attempt = item.get("exportAttempt") if isinstance(item.get("exportAttempt"), dict) else {}
        processed.append({
            "exportAttemptId": attempt.get("id"),
            "status": item.get("status"),
            "executionStatus": item.get("executionStatus"),
            "externalSubmission": item.get("externalSubmission"),
        })
    return {
        "status": result.get("status"),
        "count": result.get("count", 0),
        "processed": processed,
        "preExecutionBackup": result.get("preExecutionBackup"),
    }


def _compact_autonomy_cycle(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "success": result.get("success"),
        "status": result.get("status"),
        "workflowRunId": result.get("workflowRunId"),
        "executedActionIds": [action.get("id") for action in result.get("executedActions") or []],
        "skippedActionIds": [action.get("id") for action in result.get("skippedActions") or []],
        "masterLedger": result.get("masterLedger"),
        "externalSubmission": "not_executed",
    }


def _compact_connector_intake(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "success": result.get("success"),
        "status": result.get("status"),
        "workflowRunId": result.get("workflowRunId"),
        "summary": result.get("summary") or {},
        "sources": [
            {
                "source": item.get("source"),
                "status": item.get("status"),
                "registered": item.get("registered", 0),
                "duplicates": item.get("duplicates", 0),
                "revisions": item.get("revisions", 0),
            }
            for item in result.get("results") or []
        ],
        "externalSubmission": "not_executed",
    }


def _compact_workflow_recovery(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "success": result.get("success"),
        "status": result.get("status"),
        "attempted": result.get("attempted", 0),
        "succeeded": result.get("succeeded", 0),
        "failed": result.get("failed", 0),
        "interruptedWorkflowRunIds": result.get("interruptedWorkflowRunIds") or [],
        "connectorSourcesHeldBack": result.get("connectorSourcesHeldBack") or [],
        "externalSubmission": "not_executed",
    }


def _compact_scheduled_report(result: Dict[str, Any]) -> Dict[str, Any]:
    report_run = result.get("reportRun") if isinstance(result.get("reportRun"), dict) else {}
    return {
        "success": result.get("success"),
        "status": result.get("status"),
        "reportRunId": report_run.get("id"),
        "scheduleId": report_run.get("schedule_id"),
        "scheduleSlot": report_run.get("schedule_slot"),
        "readiness": report_run.get("readiness"),
        "rowCount": report_run.get("row_count", 0),
        "blockerCount": report_run.get("blocker_count", 0),
        "externalSubmission": "not_executed",
    }


def _compact_notification_refresh(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "success": result.get("success"),
        "status": result.get("status"),
        "created": result.get("created", 0),
        "reopened": result.get("reopened", 0),
        "resolved": result.get("resolved", 0),
        "suppressed": result.get("suppressed", 0),
        "activeIssues": result.get("activeIssues", 0),
        "externalDelivery": "not_executed",
    }


def _compact_compliance_assessment(result: Dict[str, Any]) -> Dict[str, Any]:
    assessment = result.get("assessment") if isinstance(result.get("assessment"), dict) else {}
    return {
        "success": result.get("success"),
        "status": result.get("status"),
        "assessmentId": assessment.get("id"),
        "assessmentStatus": assessment.get("status"),
        "periodFrom": assessment.get("period_from"),
        "periodTo": assessment.get("period_to"),
        "recordCount": assessment.get("record_count", 0),
        "findingCount": assessment.get("finding_count", 0),
        "blockingCount": assessment.get("blocking_count", 0),
        "statutoryStatus": "provisional",
        "externalFiling": "not_executed",
    }


def _list_config(config: Dict[str, Any], *keys: str) -> list:
    value = None
    for key in keys:
        if config.get(key) not in (None, ""):
            value = config.get(key)
            break
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        items = value
    else:
        items = str(value).replace("\n", ",").replace(";", ",").split(",")
    return [str(item).strip() for item in items if str(item).strip()]


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in {"", "0", "false", "no", "off"}
    return bool(value)


def _bounded_positive_int(value: Any, default: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(1, min(parsed, maximum))


def _safe_worker_error(error: Any, config: Dict[str, Any]) -> str:
    message = f"{type(error).__name__}: {error}"
    for key, value in config.items():
        if not re.search(
            r"(?i)(token|secret|password|api[_-]?key|authorization|credential)",
            str(key),
        ):
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
        r"(?i)(Authorization\s*:\s*(?:Bearer|Basic)\s+)[^\s,;]+",
        r"\1[REDACTED]",
        message,
    )
    return message[:2000]
