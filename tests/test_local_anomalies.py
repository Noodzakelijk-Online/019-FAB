import os
import tempfile
import unittest
from datetime import date, timedelta

from src.operations.local_anomalies import (
    ANOMALY_DETECTION_VERSION,
    LocalLedgerAnomalyService,
)
from src.operations.local_exceptions import LocalExceptionQueueService
from src.operations.local_ledger import LocalOperationsLedger


class TestLocalLedgerAnomalyService(unittest.TestCase):
    def test_detects_vendor_amount_outlier_with_ledger_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            for index, amount in enumerate([20, 20, 20, 20, 20, 20]):
                self._record(
                    ledger,
                    vendor="Reliable Hosting BV",
                    category="Software",
                    amount=amount,
                    record_date=f"2026-0{index + 1}-15",
                )
            outlier_id = self._record(
                ledger,
                vendor="Reliable Hosting B.V.",
                category="Software",
                amount=500,
                record_date="2026-07-15",
            )

            issues = LocalLedgerAnomalyService(ledger).list_issues()
            anomaly = next(issue for issue in issues if issue["type"] == "vendor_amount_anomaly")

            self.assertEqual(anomaly["entityId"], outlier_id)
            self.assertEqual(anomaly["severity"], "high")
            self.assertEqual(anomaly["details"]["detectionVersion"], ANOMALY_DETECTION_VERSION)
            self.assertEqual(anomaly["details"]["historicalMedian"], 20.0)
            self.assertEqual(anomaly["details"]["historicalSampleCount"], 6)
            self.assertEqual(anomaly["details"]["comparison"], "zero_variance_ratio")
            self.assertEqual(anomaly["details"]["externalSubmission"], "not_executed")

    def test_ignores_small_samples_and_can_be_disabled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            for amount in [10, 10, 1000]:
                self._record(ledger, vendor="New Vendor", category="Supplies", amount=amount)

            self.assertEqual(LocalLedgerAnomalyService(ledger).list_issues(), [])
            self.assertEqual(
                LocalLedgerAnomalyService(
                    ledger,
                    {"anomaly_detection_enabled": False},
                ).list_issues(),
                [],
            )

    def test_future_date_is_queued_with_review_actions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            future_date = date.today() + timedelta(days=45)
            record_id = self._record(
                ledger,
                vendor="Future Supplier",
                category="Office",
                amount=125,
                record_date=future_date.isoformat(),
            )

            payload = LocalExceptionQueueService(ledger).list_exceptions()
            anomaly = next(item for item in payload["exceptions"] if item["type"] == "future_dated_record")
            actions = {action["id"]: action for action in anomaly["actions"]}

            self.assertEqual(anomaly["entityId"], record_id)
            self.assertEqual(anomaly["severity"], "high")
            self.assertEqual(anomaly["details"]["recordDate"], future_date.isoformat())
            self.assertEqual(anomaly["entity"]["vendorName"], "Future Supplier")
            self.assertEqual(
                anomaly["nextAction"],
                "Verify the source date and correct the record before approval or downstream delivery.",
            )
            self.assertEqual(
                actions["open_bookkeeping_record"]["path"],
                f"/api/bookkeeping-records/{record_id}",
            )
            self.assertIn("open_master_ledger", actions)

    @staticmethod
    def _record(
        ledger: LocalOperationsLedger,
        vendor: str,
        category: str,
        amount: float,
        record_date: str = "2026-01-15",
    ) -> int:
        return ledger.upsert_bookkeeping_record({
            "sourceType": "document",
            "recordType": "expense",
            "recordDate": record_date,
            "vendorName": vendor,
            "description": f"Invoice from {vendor}",
            "category": category,
            "amount": amount,
            "currency": "EUR",
            "status": "validated",
            "exportStatus": "ready",
            "reconciliationStatus": "matched",
            "targetSystem": "waveapps",
            "reviewRequired": False,
        })


if __name__ == "__main__":
    unittest.main()
