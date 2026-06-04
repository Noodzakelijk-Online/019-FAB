import json
from typing import Any, Dict, Optional

from src.storage.database import Database


class PostingApprovalService:
    """Controls human approval/rejection of dry-run posting attempts."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.database = Database(config)

    def list_attempts(self, status: Optional[str] = None):
        if status:
            return self.database.fetch_all(
                "SELECT * FROM posting_attempts WHERE status = ? ORDER BY updated_at DESC LIMIT 300",
                (status,),
            )
        return self.database.fetch_all("SELECT * FROM posting_attempts ORDER BY updated_at DESC LIMIT 300")

    def approve_attempt(self, attempt_id: int, approved_by: str = "user", reason: str = "") -> Dict[str, Any]:
        attempt = self.database.fetch_one("SELECT * FROM posting_attempts WHERE id = ?", (attempt_id,))
        if not attempt:
            return {"status": "not_found", "attempt_id": attempt_id}
        if attempt["status"] not in {"dry_run_created", "approval_required", "rejected"}:
            return {"status": "not_approvable", "attempt_id": attempt_id, "current_status": attempt["status"]}
        now = self.database.now()
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE posting_attempts SET status = 'approved', updated_at = ? WHERE id = ?",
                (now, attempt_id),
            )
        self.database.add_audit_log("posting_attempt", str(attempt_id), "approved", attempt, {"status": "approved"}, reason, approved_by)
        return {"status": "approved", "attempt_id": attempt_id}

    def reject_attempt(self, attempt_id: int, rejected_by: str = "user", reason: str = "") -> Dict[str, Any]:
        attempt = self.database.fetch_one("SELECT * FROM posting_attempts WHERE id = ?", (attempt_id,))
        if not attempt:
            return {"status": "not_found", "attempt_id": attempt_id}
        now = self.database.now()
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE posting_attempts SET status = 'rejected', updated_at = ? WHERE id = ?",
                (now, attempt_id),
            )
        self.database.add_audit_log("posting_attempt", str(attempt_id), "rejected", attempt, {"status": "rejected"}, reason, rejected_by)
        return {"status": "rejected", "attempt_id": attempt_id}

    def mark_executed(self, attempt_id: int, external_id: str = None, result: Dict[str, Any] = None) -> Dict[str, Any]:
        attempt = self.database.fetch_one("SELECT * FROM posting_attempts WHERE id = ?", (attempt_id,))
        if not attempt:
            return {"status": "not_found", "attempt_id": attempt_id}
        now = self.database.now()
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE posting_attempts SET status = 'posted', external_id = ?, updated_at = ? WHERE id = ?",
                (external_id, now, attempt_id),
            )
        self.database.add_audit_log("posting_attempt", str(attempt_id), "posted", attempt, result or {}, "Posting executed", "system")
        return {"status": "posted", "attempt_id": attempt_id, "external_id": external_id}

    def mark_failed(self, attempt_id: int, result: Dict[str, Any]) -> Dict[str, Any]:
        now = self.database.now()
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE posting_attempts SET status = 'posting_failed', updated_at = ? WHERE id = ?",
                (now, attempt_id),
            )
        self.database.add_audit_log("posting_attempt", str(attempt_id), "posting_failed", None, result, result.get("message", "Posting failed"), "system")
        return {"status": "posting_failed", "attempt_id": attempt_id}

    def payload_for_attempt(self, attempt_id: int) -> Optional[Dict[str, Any]]:
        attempt = self.database.fetch_one("SELECT * FROM posting_attempts WHERE id = ?", (attempt_id,))
        if not attempt:
            return None
        try:
            return json.loads(attempt.get("payload_json") or "{}")
        except json.JSONDecodeError:
            return {}
