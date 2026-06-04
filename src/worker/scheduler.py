import signal
import time
from typing import Any, Dict

from src.storage.database import Database
from src.workflow.controller import WorkflowController


class FabWorker:
    """Simple local scheduler for repeated FAB workflow runs."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.interval_seconds = int(self.config.get("worker_interval_seconds", 300))
        self.run_once = bool(self.config.get("worker_run_once", False))
        self.database = Database(config)
        self._stop_requested = False

    def install_signal_handlers(self) -> None:
        def handle_stop(signum, frame):
            self._stop_requested = True
            self.database.add_audit_log("worker", "local", "stop_requested", None, {"signal": signum}, "Worker stop requested", "system")
        signal.signal(signal.SIGINT, handle_stop)
        signal.signal(signal.SIGTERM, handle_stop)

    def run(self) -> None:
        self.install_signal_handlers()
        self.database.add_audit_log("worker", "local", "started", None, {"interval_seconds": self.interval_seconds}, "Worker started", "system")
        while not self._stop_requested:
            started_at = self.database.now()
            try:
                self.database.add_audit_log("worker", "local", "cycle_started", None, {"started_at": started_at}, "Worker cycle started", "system")
                WorkflowController(self.config).run_workflow()
                self.database.add_audit_log("worker", "local", "cycle_completed", {"started_at": started_at}, {"completed_at": self.database.now()}, "Worker cycle completed", "system")
            except Exception as exc:
                self.database.add_audit_log("worker", "local", "cycle_failed", {"started_at": started_at}, {"error": str(exc)}, str(exc), "system")
            if self.run_once:
                break
            self._sleep_until_next_cycle()
        self.database.add_audit_log("worker", "local", "stopped", None, None, "Worker stopped", "system")

    def _sleep_until_next_cycle(self) -> None:
        slept = 0
        while slept < self.interval_seconds and not self._stop_requested:
            time.sleep(1)
            slept += 1
