from typing import Any, Dict, List, Optional

from src.data_entry.mijngeldzaken_handler import MijngeldzakenHandler
from src.data_entry.posting_approval import PostingApprovalService
from src.data_entry.waveapps_business_handler import WaveappsBusinessHandler
from src.data_entry.waveapps_personal_handler import WaveappsPersonalHandler
from src.storage.database import Database


class PostingExecutor:
    """Executes approved posting attempts against the configured bookkeeping handlers."""

    def __init__(self, config: Dict[str, Any], handlers: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.database = Database(config)
        self.approval_service = PostingApprovalService(config)
        self.execute_approved_postings = bool(self.config.get("execute_approved_postings", False))
        self.handlers = handlers or {
            "mijngeldzaken": MijngeldzakenHandler(config),
            "waveapps_business": WaveappsBusinessHandler(config),
            "waveapps_personal": WaveappsPersonalHandler(config),
        }

    def process_approved_attempts(self, force: bool = False, limit: int = 20) -> Dict[str, Any]:
        if not self.execute_approved_postings and not force:
            return {
                "status": "skipped",
                "reason": "execute_approved_postings is disabled",
                "processed": [],
            }

        attempts = self.database.fetch_all(
            "SELECT * FROM posting_attempts WHERE status = 'approved' ORDER BY updated_at ASC LIMIT ?",
            (limit,),
        )
        processed: List[Dict[str, Any]] = []
        for attempt in attempts:
            processed.append(self.execute_attempt(int(attempt["id"]), force=True))
        return {"status": "completed", "processed": processed, "count": len(processed)}

    def execute_attempt(self, attempt_id: int, force: bool = False) -> Dict[str, Any]:
        if not self.execute_approved_postings and not force:
            return {"status": "skipped", "reason": "execute_approved_postings is disabled", "attempt_id": attempt_id}

        attempt = self.database.fetch_one("SELECT * FROM posting_attempts WHERE id = ?", (attempt_id,))
        if not attempt:
            return {"status": "not_found", "attempt_id": attempt_id}
        if attempt["status"] != "approved" and not force:
            return {"status": "not_approved", "attempt_id": attempt_id, "current_status": attempt["status"]}

        payload = self.approval_service.payload_for_attempt(attempt_id) or {}
        target_system = payload.get("target_system") or attempt.get("target_system")
        handler = self.handlers.get(target_system)
        if not handler:
            result = {"status": "failure", "message": f"No handler configured for target system: {target_system}"}
            self.approval_service.mark_failed(attempt_id, result)
            return {"attempt_id": attempt_id, **result}

        categorized_data = self._payload_to_categorized_data(payload, attempt)
        self._mark_attempt_status(attempt_id, "posting_in_progress")
        self.database.add_audit_log(
            "posting_attempt",
            str(attempt_id),
            "execution_started",
            attempt,
            {"target_system": target_system, "document_id": categorized_data.get("document_id")},
            "Approved posting execution started",
            "system",
        )

        try:
            result = handler.enter_data(categorized_data)
        except Exception as exc:
            result = {"status": "failure", "message": str(exc), "requires_manual_review": True}

        if result.get("status") == "success":
            external_id = result.get("external_id") or result.get("id")
            self.approval_service.mark_executed(attempt_id, external_id=external_id, result=result)
            self._mark_document_posted(categorized_data.get("document_id"), result)
            return {"attempt_id": attempt_id, "status": "posted", "result": result}

        self.approval_service.mark_failed(attempt_id, result)
        document_id = categorized_data.get("document_id")
        if document_id:
            self.database.add_manual_review_item(document_id, "posting_execution_failed", str(result), severity="high")
        return {"attempt_id": attempt_id, "status": "posting_failed", "result": result}

    def _payload_to_categorized_data(self, payload: Dict[str, Any], attempt: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "document_id": payload.get("document_id") or attempt.get("document_id"),
            "target_system": payload.get("target_system") or attempt.get("target_system"),
            "target_account": payload.get("target_account") or attempt.get("target_account"),
            "category": payload.get("category"),
            "extracted_data": payload.get("extracted_data", {}),
            "safety_result": payload.get("safety_result", {}),
            "posting_attempt_id": attempt.get("id"),
            "idempotency_key": attempt.get("idempotency_key"),
        }

    def _mark_attempt_status(self, attempt_id: int, status: str) -> None:
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE posting_attempts SET status = ?, updated_at = ? WHERE id = ?",
                (status, self.database.now(), attempt_id),
            )

    def _mark_document_posted(self, document_id: str, result: Dict[str, Any]) -> None:
        if not document_id:
            return
        with self.database.connect() as connection:
            current = connection.execute("SELECT current_state FROM documents WHERE id = ?", (document_id,)).fetchone()
            if current:
                connection.execute(
                    "UPDATE documents SET current_state = 'posted', updated_at = ? WHERE id = ?",
                    (self.database.now(), document_id),
                )
        self.database.add_audit_log("document", document_id, "posted", None, result, "Posting attempt executed successfully", "system")
