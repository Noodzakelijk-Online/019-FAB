import signal
import time
from datetime import datetime, timezone
from typing import Any, Dict

from src.data_entry.posting_executor import PostingExecutor
from src.operations.local_exports import LocalExportAttemptService
from src.operations.local_runtime import build_local_operations_ledger
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
        self.process_legacy_postings = _as_bool(
            self.config.get("worker_process_legacy_postings", self.operations_ledger is None)
        )
        self.database = Database(config) if self.process_legacy_postings or not self.operations_ledger else None
        self._stop_requested = False

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
            try:
                self._record_audit("cycle_started", {"startedAt": started_at}, "Worker cycle started")
                WorkflowController(self.config).run_workflow()
                self._process_operations_exports()
                self._process_legacy_queue()
                self._record_audit(
                    "cycle_completed",
                    {"startedAt": started_at, "completedAt": self._now()},
                    "Worker cycle completed",
                )
            except Exception as exc:
                self._record_audit(
                    "cycle_failed",
                    {"startedAt": started_at, "error": str(exc)},
                    str(exc),
                )
            if self.run_once:
                break
            self._sleep_until_next_cycle()
        self._record_audit("stopped", {}, "Worker stopped")

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


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in {"", "0", "false", "no", "off"}
    return bool(value)
