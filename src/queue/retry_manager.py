from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from src.storage.database import Database


class RetryManager:
    """Tracks retry/dead-letter state for fragile external operations."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.database = Database(config)
        self.default_max_attempts = int(self.config.get("retry_max_attempts", 3))
        self.base_delay_seconds = int(self.config.get("retry_base_delay_seconds", 300))

    def ensure_schema(self) -> None:
        with self.database.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS retry_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    last_error TEXT,
                    next_retry_at TEXT,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(entity_type, entity_id, operation)
                );

                CREATE TABLE IF NOT EXISTS dead_letter_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    final_error TEXT,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );
                """
            )

    def schedule_retry(
        self,
        entity_type: str,
        entity_id: str,
        operation: str,
        error: str,
        payload: Optional[Dict[str, Any]] = None,
        max_attempts: Optional[int] = None,
    ) -> Dict[str, Any]:
        self.ensure_schema()
        max_attempts = max_attempts or self.default_max_attempts
        now = datetime.now(timezone.utc)
        existing = self.database.fetch_one(
            "SELECT * FROM retry_queue WHERE entity_type = ? AND entity_id = ? AND operation = ?",
            (entity_type, entity_id, operation),
        )
        attempt_count = int(existing["attempt_count"]) + 1 if existing else 1
        if attempt_count >= max_attempts:
            return self.move_to_dead_letter(entity_type, entity_id, operation, error, payload or {})

        delay_seconds = self.base_delay_seconds * (2 ** max(0, attempt_count - 1))
        next_retry_at = (now + timedelta(seconds=delay_seconds)).isoformat()
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO retry_queue (
                    entity_type, entity_id, operation, status, attempt_count, max_attempts,
                    last_error, next_retry_at, payload_json, created_at, updated_at
                ) VALUES (?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(entity_type, entity_id, operation) DO UPDATE SET
                    status='pending',
                    attempt_count=excluded.attempt_count,
                    max_attempts=excluded.max_attempts,
                    last_error=excluded.last_error,
                    next_retry_at=excluded.next_retry_at,
                    payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at
                """,
                (
                    entity_type,
                    entity_id,
                    operation,
                    attempt_count,
                    max_attempts,
                    error,
                    next_retry_at,
                    self.database.json_dumps(payload or {}),
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
        self.database.add_audit_log(entity_type, entity_id, "retry_scheduled", None, {"operation": operation, "attempt_count": attempt_count, "next_retry_at": next_retry_at}, error, "system")
        return {"status": "retry_scheduled", "entity_type": entity_type, "entity_id": entity_id, "operation": operation, "attempt_count": attempt_count, "next_retry_at": next_retry_at}

    def defer_retry(
        self,
        entity_type: str,
        entity_id: str,
        operation: str,
        reason: str,
        payload: Optional[Dict[str, Any]] = None,
        delay_seconds: int = 60,
    ) -> Dict[str, Any]:
        """Schedule a known temporary pause without spending failure attempts."""
        self.ensure_schema()
        now = datetime.now(timezone.utc)
        existing = self.database.fetch_one(
            "SELECT * FROM retry_queue WHERE entity_type = ? AND entity_id = ? AND operation = ?",
            (entity_type, entity_id, operation),
        )
        next_retry_at = (now + timedelta(seconds=max(int(delay_seconds), 1))).isoformat()
        attempt_count = int(existing["attempt_count"]) if existing else 0
        max_attempts = int(existing["max_attempts"]) if existing else self.default_max_attempts
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO retry_queue (
                    entity_type, entity_id, operation, status, attempt_count, max_attempts,
                    last_error, next_retry_at, payload_json, created_at, updated_at
                ) VALUES (?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(entity_type, entity_id, operation) DO UPDATE SET
                    status='pending',
                    last_error=excluded.last_error,
                    next_retry_at=excluded.next_retry_at,
                    payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at
                """,
                (
                    entity_type,
                    entity_id,
                    operation,
                    attempt_count,
                    max_attempts,
                    reason,
                    next_retry_at,
                    self.database.json_dumps(payload or {}),
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
        details = {
            "operation": operation,
            "attempt_count": attempt_count,
            "next_retry_at": next_retry_at,
            "reason": reason,
        }
        self.database.add_audit_log(entity_type, entity_id, "retry_deferred", None, details, reason, "system")
        return {
            "status": "retry_deferred",
            "entity_type": entity_type,
            "entity_id": entity_id,
            "operation": operation,
            "attempt_count": attempt_count,
            "next_retry_at": next_retry_at,
        }

    def move_to_dead_letter(self, entity_type: str, entity_id: str, operation: str, error: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.ensure_schema()
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO dead_letter_queue (entity_type, entity_id, operation, final_error, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (entity_type, entity_id, operation, error, self.database.json_dumps(payload), self.database.now()),
            )
            connection.execute(
                "UPDATE retry_queue SET status = 'dead_letter', updated_at = ? WHERE entity_type = ? AND entity_id = ? AND operation = ?",
                (self.database.now(), entity_type, entity_id, operation),
            )
        self.database.add_audit_log(entity_type, entity_id, "dead_lettered", None, {"operation": operation}, error, "system")
        return {"status": "dead_lettered", "entity_type": entity_type, "entity_id": entity_id, "operation": operation}

    def mark_complete(self, entity_type: str, entity_id: str, operation: str) -> None:
        self.ensure_schema()
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE retry_queue SET status = 'completed', updated_at = ? WHERE entity_type = ? AND entity_id = ? AND operation = ?",
                (self.database.now(), entity_type, entity_id, operation),
            )

    def due_items(self):
        self.ensure_schema()
        return self.database.fetch_all(
            "SELECT * FROM retry_queue WHERE status = 'pending' AND next_retry_at <= ? ORDER BY next_retry_at ASC",
            (self.database.now(),),
        )
