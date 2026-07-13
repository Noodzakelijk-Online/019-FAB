import os
import sqlite3
import tempfile
import unittest

from src.operations.local_ledger import LocalOperationsLedger
from src.operations.local_notifications import LocalNotificationService


class TestLocalNotificationService(unittest.TestCase):
    def test_health_refresh_is_idempotent_and_resolves_cleared_issue(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = os.path.join(temp_dir, "fab.sqlite3")
            ledger = LocalOperationsLedger(ledger_path)
            document_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "notification-failure",
                "originalFilename": "failed.pdf",
                "processingStatus": "failed",
            })
            service = LocalNotificationService(ledger)

            first = service.refresh(actor="test")
            second = service.refresh(actor="test")

            self.assertEqual(first["created"], 1)
            self.assertEqual(second["created"], 0)
            self.assertEqual(len(ledger.list_notifications()), 1)
            notification = ledger.list_notifications()[0]
            self.assertEqual(notification["event_type"], "failed_document")
            self.assertEqual(notification["severity"], "high")
            self.assertEqual(notification["status"], "unread")
            self.assertEqual(notification["occurrence_count"], 1)
            self.assertEqual(notification["external_delivery"], "not_executed")

            connection = sqlite3.connect(ledger_path)
            try:
                connection.execute(
                    "UPDATE bookkeeping_documents SET processing_status = 'processed' WHERE id = ?",
                    (document_id,),
                )
                connection.commit()
            finally:
                connection.close()

            cleared = service.refresh(actor="test")
            self.assertEqual(cleared["resolved"], 1)
            self.assertEqual(ledger.list_notifications()[0]["status"], "resolved")

    def test_preferences_suppress_low_severity_and_reopen_when_enabled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            service = LocalNotificationService(ledger)
            service.update_preference({
                "eventType": "*",
                "enabled": True,
                "inAppEnabled": True,
                "minimumSeverity": "high",
            })
            health = {
                "generatedAt": "2026-07-13T12:00:00Z",
                "issues": [{
                    "type": "stale_review_item",
                    "severity": "medium",
                    "entityType": "review_item",
                    "entityId": "7",
                    "message": "Review item is overdue.",
                    "details": {"accessToken": "must-not-persist"},
                }],
            }

            suppressed = service.refresh(health, actor="test")
            self.assertEqual(suppressed["suppressed"], 1)
            notification = ledger.list_notifications()[0]
            self.assertEqual(notification["status"], "suppressed")
            self.assertEqual(notification["payload"]["details"]["accessToken"], "<redacted>")

            service.update_preference({
                "eventType": "stale_review_item",
                "enabled": True,
                "inAppEnabled": True,
                "minimumSeverity": "low",
            })
            reopened = service.refresh(health, actor="test")
            self.assertEqual(reopened["reopened"], 1)
            self.assertEqual(ledger.list_notifications()[0]["status"], "unread")

    def test_notification_status_actions_are_audited(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            service = LocalNotificationService(ledger)
            service.refresh({
                "generatedAt": "2026-07-13T12:00:00Z",
                "issues": [{
                    "type": "api_quota_exhausted",
                    "severity": "high",
                    "entityType": "api_quota",
                    "entityId": "waveapps",
                    "message": "Wave quota exhausted.",
                }],
            })
            notification_id = ledger.list_notifications()[0]["id"]

            acknowledged = service.update_status(notification_id, "acknowledged", actor="tester")

            self.assertTrue(acknowledged["success"])
            self.assertEqual(acknowledged["notification"]["status"], "acknowledged")
            self.assertIsNotNone(acknowledged["notification"]["acknowledged_at"])
            audit = ledger.list_audit_events()[0]
            self.assertEqual(audit["action"], "local_notifications.status_changed")
            self.assertEqual(audit["details"]["actor"], "tester")

    def test_source_connector_alert_links_to_sources_dashboard(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            ledger.upsert_source_account({
                "sourceType": "gmail",
                "sourceIdentifier": "me",
                "label": "Gmail",
                "status": "failed",
            })

            result = LocalNotificationService(ledger).refresh(actor="test")

            self.assertEqual(result["created"], 1)
            notification = ledger.list_notifications()[0]
            self.assertEqual(notification["event_type"], "source_connector_unavailable")
            self.assertEqual(notification["payload"]["dashboardPath"], "#sources")


if __name__ == "__main__":
    unittest.main()
