import hashlib
from typing import Any, Dict

from src.storage.database import Database
from src.workflow.safety_engine import SafetyEngine


class SafePostingService:
    """Creates dry-run and posting records with idempotency protection."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.database = Database(config)
        self.safety_engine = SafetyEngine(config)

    def build_idempotency_key(self, document_data: Dict[str, Any], target_system: str) -> str:
        document_id = str(document_data.get("document_id"))
        external_source = str(document_data.get("source_document", {}).get("source_external_id") or document_id)
        category = str(document_data.get("category", ""))
        payload = "|".join([document_id, external_source, category, target_system])
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def create_dry_run(self, document_data: Dict[str, Any], target_system: str, target_account: str = None) -> Dict[str, Any]:
        safety_result = self.safety_engine.evaluate_posting_readiness(document_data)
        idempotency_key = self.build_idempotency_key(document_data, target_system)
        payload = {
            "document_id": document_data.get("document_id"),
            "target_system": target_system,
            "target_account": target_account,
            "category": document_data.get("category"),
            "extracted_data": document_data.get("extracted_data", {}),
            "safety_result": safety_result,
        }

        now = self.database.now()
        with self.database.connect() as connection:
            existing = connection.execute(
                "SELECT * FROM posting_attempts WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if existing:
                return {
                    "status": "existing_attempt",
                    "posting_attempt_id": existing["id"],
                    "idempotency_key": idempotency_key,
                    "safety_result": safety_result,
                }

            cursor = connection.execute(
                """
                INSERT INTO posting_attempts (
                    document_id, target_system, target_account, dry_run, payload_json,
                    status, idempotency_key, created_at, updated_at
                ) VALUES (?, ?, ?, 1, ?, 'dry_run_created', ?, ?, ?)
                """,
                (
                    document_data.get("document_id"),
                    target_system,
                    target_account,
                    self.database.json_dumps(payload),
                    idempotency_key,
                    now,
                    now,
                ),
            )
            posting_attempt_id = cursor.lastrowid

        return {
            "status": "dry_run_created",
            "posting_attempt_id": posting_attempt_id,
            "idempotency_key": idempotency_key,
            "safety_result": safety_result,
            "payload": payload,
        }
