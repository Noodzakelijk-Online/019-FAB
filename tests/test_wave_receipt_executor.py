import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from src.operations.local_api import create_app
from src.operations.local_ledger import LocalOperationsLedger
from src.operations.local_wave_receipt_executor import (
    LocalWaveReceiptExecutorService,
    REQUIRED_CAPABILITIES,
)


class FakeWorkOrders:
    def __init__(self, work_orders):
        self.work_orders = work_orders

    def list_work_orders(self, limit=100):
        return {
            "status": "ready",
            "count": len(self.work_orders[:limit]),
            "workOrders": self.work_orders[:limit],
        }


class TestLocalWaveReceiptExecutorService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ledger = LocalOperationsLedger(os.path.join(self.temp_dir.name, "fab.sqlite3"))
        self.state_path = os.path.join(self.temp_dir.name, "wave-receipt-executor.json")
        self.config = {
            "waveapps_business_id": "wave-business",
            "wave_receipt_executor_enabled": True,
            "wave_receipt_executor_state_file": self.state_path,
            "wave_receipt_executor_heartbeat_ttl_seconds": 60,
            "wave_receipt_executor_claim_lease_seconds": 120,
        }
        self.service = LocalWaveReceiptExecutorService(self.ledger, self.config)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _session(self, **updates):
        payload = {
            "executorId": "hai-wave-browser",
            "sessionId": "session-1",
            "businessId": "wave-business",
            "status": "ready",
            "capabilities": list(REQUIRED_CAPABILITIES),
            "browser": "chromium",
            "version": "1.0.0",
            "message": "Wave transactions are available.",
        }
        payload.update(updates)
        return payload

    def test_status_is_fail_closed_until_executor_connects(self):
        status = self.service.status()

        self.assertEqual(status["status"], "not_connected")
        self.assertFalse(status["ready"])
        self.assertFalse(status["credentialFieldsAccepted"])
        self.assertEqual(status["requiredCapabilities"], list(REQUIRED_CAPABILITIES))

    def test_ready_session_requires_business_and_all_capabilities(self):
        missing = self.service.register(self._session(capabilities=["transaction_locate"]))

        self.assertTrue(missing["success"])
        self.assertEqual(missing["status"], "incompatible")
        self.assertIn("receipt_upload", missing["missingCapabilities"])

        ready = self.service.register(self._session())

        self.assertTrue(ready["success"])
        self.assertEqual(ready["status"], "ready")
        self.assertTrue(ready["businessMatches"])
        self.assertNotIn("password", json.dumps(ready).lower())

    def test_sensitive_browser_state_is_rejected_and_not_written(self):
        result = self.service.register({
            **self._session(),
            "storageState": {"cookies": [{"name": "session", "value": "private"}]},
        })

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "invalid")
        self.assertIn("forbidden", result["error"])
        self.assertFalse(os.path.exists(self.state_path))

    def test_wrong_business_and_expired_heartbeat_are_not_ready(self):
        wrong_business = self.service.register(self._session(businessId="other-business"))

        self.assertEqual(wrong_business["status"], "wrong_business")
        self.service.disconnect(self._session(businessId="other-business"))
        self.service.register(self._session())
        with open(self.state_path, "r", encoding="utf-8") as handle:
            state = json.load(handle)
        state["heartbeatAt"] = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        with open(self.state_path, "w", encoding="utf-8") as handle:
            json.dump(state, handle)

        stale = self.service.status()

        self.assertEqual(stale["status"], "stale")
        self.assertFalse(stale["ready"])

    def test_fresh_session_cannot_be_replaced_without_disconnect(self):
        self.service.register(self._session())

        conflict = self.service.register(self._session(executorId="other-executor", sessionId="session-2"))

        self.assertFalse(conflict["success"])
        self.assertEqual(conflict["status"], "session_conflict")
        self.assertEqual(self.service.status()["executorId"], "hai-wave-browser")

    def test_executor_cannot_self_assign_busy_work_or_release_another_document(self):
        self.service.register(self._session())

        self_assigned = self.service.register(self._session(
            status="busy",
            currentDocumentId=9,
        ))

        self.assertFalse(self_assigned["success"])
        self.assertEqual(self_assigned["status"], "active_claim_required")

        provider = FakeWorkOrders([{
            "documentId": 2,
            "stage": "upload_and_verify_attachment",
            "source": {"localAvailable": True},
            "wave": {"externalTransactionId": "wave-transaction-2"},
        }])
        self.service.claim_next(provider, self._session())

        mismatched_release = self.service.release(3, {
            "executorId": "hai-wave-browser",
            "sessionId": "session-1",
            "outcome": "verified",
        })

        self.assertFalse(mismatched_release["success"])
        self.assertEqual(mismatched_release["status"], "invalid_claim")
        self.assertEqual(self.service.status()["currentDocumentId"], 2)
        self.assertTrue(self.ledger.get_runtime_lease("wave-receipt-execution:2")["active"])

    def test_claims_only_attachment_work_and_releases_owned_lease(self):
        self.service.register(self._session())
        provider = FakeWorkOrders([
            {
                "documentId": 1,
                "stage": "locate_or_create_transaction",
                "source": {"localAvailable": True},
                "wave": {"externalTransactionId": None},
            },
            {
                "documentId": 2,
                "stage": "upload_and_verify_attachment",
                "source": {"localAvailable": True, "localPath": "C:/evidence/invoice.pdf"},
                "wave": {"externalTransactionId": "wave-transaction-2"},
            },
        ])

        claimed = self.service.claim_next(provider, self._session())

        self.assertTrue(claimed["success"])
        self.assertEqual(claimed["status"], "claimed")
        self.assertEqual(claimed["documentId"], 2)
        self.assertEqual(self.service.status()["status"], "busy")
        self.assertTrue(self.ledger.get_runtime_lease("wave-receipt-execution:2")["active"])

        skipped_release = self.service.register(self._session())

        self.assertFalse(skipped_release["success"])
        self.assertEqual(skipped_release["status"], "active_claim")

        released = self.service.release(2, {
            "executorId": "hai-wave-browser",
            "sessionId": "session-1",
            "outcome": "verified",
        })

        self.assertTrue(released["success"])
        self.assertTrue(released["leaseReleased"])
        self.assertIsNone(self.ledger.get_runtime_lease("wave-receipt-execution:2"))
        self.assertEqual(self.service.status()["status"], "ready")

    def test_api_exposes_session_status_and_manifest_contract(self):
        app = create_app({
            **self.config,
            "fab_local_ledger_path": self.ledger.path,
        })
        client = app.test_client()

        disconnected = client.get("/api/wave/receipt-executor/status")
        registered = client.post(
            "/api/wave/receipt-executor/session",
            json={**self._session(), "actor": "test-executor"},
        )
        manifest = client.get("/api/hai/manifest")

        self.assertEqual(disconnected.status_code, 200)
        self.assertEqual(disconnected.get_json()["status"], "not_connected")
        self.assertEqual(registered.status_code, 200)
        self.assertTrue(registered.get_json()["ready"])
        resources = {
            item["resourceId"]: item for item in manifest.get_json()["resources"]
        }
        self.assertEqual(
            resources["wave_receipt_executor_claim"]["path"],
            "/api/wave/receipt-executor/claim",
        )
        self.assertEqual(
            resources["wave_receipt_executor_session"]["mode"],
            "non_secret_executor_coordination",
        )


if __name__ == "__main__":
    unittest.main()
