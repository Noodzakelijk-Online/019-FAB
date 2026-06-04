import hashlib
from typing import Any, Dict, Optional

from src.storage.database import Database


class ExceptionMemory:
    """Stores and checks approved bookkeeping exceptions so FAB stops repeating known warnings."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.database = Database(config)

    def build_fingerprint(self, exception_type: str, context: Dict[str, Any]) -> str:
        source = self.database.json_dumps({"exception_type": exception_type, "context": context})
        return hashlib.sha256(source.encode("utf-8")).hexdigest()

    def is_approved(self, exception_type: str, context: Dict[str, Any]) -> bool:
        fingerprint = self.build_fingerprint(exception_type, context)
        row = self.database.fetch_one(
            "SELECT * FROM exceptions WHERE fingerprint = ? AND active = 1",
            (fingerprint,),
        )
        return row is not None

    def get_exception(self, exception_type: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        fingerprint = self.build_fingerprint(exception_type, context)
        return self.database.fetch_one(
            "SELECT * FROM exceptions WHERE fingerprint = ? AND active = 1",
            (fingerprint,),
        )

    def approve_exception(self, exception_type: str, context: Dict[str, Any], explanation: str) -> Dict[str, Any]:
        fingerprint = self.build_fingerprint(exception_type, context)
        now = self.database.now()
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO exceptions (exception_type, fingerprint, explanation, active, created_at)
                VALUES (?, ?, ?, 1, ?)
                ON CONFLICT(fingerprint) DO UPDATE SET
                    explanation=excluded.explanation,
                    active=1
                """,
                (exception_type, fingerprint, explanation, now),
            )
        self.database.add_audit_log(
            "exception",
            fingerprint,
            "approved_exception",
            None,
            {"exception_type": exception_type, "context": context, "explanation": explanation},
            explanation,
            "user",
        )
        return {
            "exception_type": exception_type,
            "fingerprint": fingerprint,
            "explanation": explanation,
            "active": True,
        }

    def deactivate_exception(self, fingerprint: str, reason: str = "") -> bool:
        with self.database.connect() as connection:
            cursor = connection.execute(
                "UPDATE exceptions SET active = 0 WHERE fingerprint = ?",
                (fingerprint,),
            )
        self.database.add_audit_log("exception", fingerprint, "deactivated_exception", None, None, reason, "user")
        return cursor.rowcount > 0
