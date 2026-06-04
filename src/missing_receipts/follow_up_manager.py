from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from src.storage.database import Database


class MissingReceiptFollowUpManager:
    """Creates and tracks missing-receipt follow-up workflows."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.database = Database(config)
        self.default_follow_up_days = int(self.config.get("missing_receipt_follow_up_days", 7))
        self.max_reminders = int(self.config.get("missing_receipt_max_reminders", 3))

    def create_or_update_follow_up(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        transaction = alert.get("transaction", {}) or {}
        transaction_id = transaction.get("id")
        if not transaction_id:
            raise ValueError("Missing receipt follow-up requires a transaction id")

        now = self.database.now()
        next_reminder = (datetime.now(timezone.utc) + timedelta(days=self.default_follow_up_days)).isoformat()
        message = self.build_request_message(alert)

        with self.database.connect() as connection:
            existing = connection.execute(
                "SELECT * FROM outreach_reminders WHERE transaction_id = ? AND status NOT IN ('stopped', 'completed')",
                (transaction_id,),
            ).fetchone()
            if existing:
                connection.execute(
                    """
                    UPDATE outreach_reminders
                    SET message_template = ?, next_reminder_at = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (message, next_reminder, now, existing["id"]),
                )
                reminder_id = existing["id"]
                status = "updated"
            else:
                cursor = connection.execute(
                    """
                    INSERT INTO outreach_reminders (
                        transaction_id, vendor_id, status, message_template,
                        reminder_count, next_reminder_at, created_at, updated_at
                    ) VALUES (?, NULL, 'open', ?, 0, ?, ?, ?)
                    """,
                    (transaction_id, message, next_reminder, now, now),
                )
                reminder_id = cursor.lastrowid
                status = "created"

        self.database.add_audit_log(
            "outreach_reminder",
            str(reminder_id),
            f"missing_receipt_follow_up_{status}",
            None,
            {"transaction_id": transaction_id, "next_reminder_at": next_reminder},
            "Missing receipt follow-up prepared",
        )
        return {
            "status": status,
            "reminder_id": reminder_id,
            "transaction_id": transaction_id,
            "message_template": message,
            "next_reminder_at": next_reminder,
        }

    def build_request_message(self, alert: Dict[str, Any]) -> str:
        transaction = alert.get("transaction", {}) or {}
        vendor = transaction.get("counterparty") or transaction.get("description") or "your organization"
        date = transaction.get("date") or transaction.get("transaction_date") or "the transaction date"
        amount = transaction.get("amount")
        currency = transaction.get("currency", "EUR")
        return (
            f"Dear {vendor},\n\n"
            f"I am trying to complete my bookkeeping and appear to be missing the receipt/invoice "
            f"for a transaction dated {date} with amount {amount} {currency}.\n\n"
            f"Could you please provide a copy of the receipt or invoice for this transaction?\n\n"
            f"Thank you."
        )

    def mark_completed(self, transaction_id: str, reason: str = "Receipt received and processed") -> bool:
        now = self.database.now()
        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE outreach_reminders
                SET status = 'completed', stopped_reason = ?, updated_at = ?
                WHERE transaction_id = ? AND status NOT IN ('stopped', 'completed')
                """,
                (reason, now, transaction_id),
            )
            connection.execute(
                "UPDATE missing_receipt_alerts SET status = 'resolved', resolved_at = ? WHERE transaction_id = ? AND status = 'open'",
                (now, transaction_id),
            )
        self.database.add_audit_log("outreach_reminder", transaction_id, "completed", None, None, reason, "system")
        return cursor.rowcount > 0

    def stop_follow_up(self, transaction_id: str, reason: str) -> bool:
        now = self.database.now()
        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE outreach_reminders
                SET status = 'stopped', stopped_reason = ?, updated_at = ?
                WHERE transaction_id = ? AND status NOT IN ('stopped', 'completed')
                """,
                (reason, now, transaction_id),
            )
        self.database.add_audit_log("outreach_reminder", transaction_id, "stopped", None, None, reason, "user")
        return cursor.rowcount > 0

    def reminders_due(self):
        now = self.database.now()
        return self.database.fetch_all(
            """
            SELECT * FROM outreach_reminders
            WHERE status = 'open'
              AND next_reminder_at IS NOT NULL
              AND next_reminder_at <= ?
              AND reminder_count < ?
            ORDER BY next_reminder_at ASC
            """,
            (now, self.max_reminders),
        )
