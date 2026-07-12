import os
import tempfile
import unittest

from src.operations.local_ledger import LocalOperationsLedger
from src.operations.local_reporting import LocalFinancialReportingService


class TestLocalFinancialReportingService(unittest.TestCase):
    def _ledger(self, temp_dir):
        ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
        ledger.upsert_bookkeeping_record({
            "documentId": 10,
            "sourceType": "document",
            "recordType": "expense",
            "status": "ready_to_route",
            "targetSystem": "waveapps",
            "targetAccount": "Office expenses",
            "vendorName": "Office Shop",
            "category": "Office",
            "recordDate": "2026-04-01",
            "amount": 121,
            "vatAmount": 21,
            "currency": "EUR",
            "reviewRequired": False,
            "reconciliationStatus": "reconciled",
        })
        ledger.upsert_bookkeeping_record({
            "documentId": 11,
            "sourceType": "document",
            "recordType": "income",
            "status": "ready_to_route",
            "targetSystem": "waveapps",
            "targetAccount": "Sales",
            "vendorName": "Customer BV",
            "category": "Revenue",
            "recordDate": "2026-04-02",
            "amount": 242,
            "vatAmount": 42,
            "currency": "EUR",
            "reviewRequired": False,
            "reconciliationStatus": "reconciled",
        })
        ledger.upsert_bookkeeping_record({
            "bankTransactionId": 20,
            "sourceType": "bank_transaction",
            "recordType": "expense",
            "status": "reconciled",
            "targetSystem": "waveapps",
            "targetAccount": "Office expenses",
            "vendorName": "Office Shop",
            "category": "Office",
            "recordDate": "2026-04-01",
            "amount": -121,
            "currency": "EUR",
            "reviewRequired": False,
            "reconciliationStatus": "reconciled",
        })
        ledger.upsert_bookkeeping_record({
            "bankTransactionId": 21,
            "sourceType": "bank_transaction",
            "recordType": "expense",
            "status": "draft",
            "targetSystem": "waveapps",
            "targetAccount": "Bank fees",
            "vendorName": "Bank",
            "category": "Bank fees",
            "recordDate": "2026-04-03",
            "amount": -50,
            "currency": "EUR",
            "reviewRequired": False,
            "reconciliationStatus": "not_started",
        })
        return ledger

    def test_accrual_report_avoids_reconciled_bank_double_counting(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = self._ledger(temp_dir)
            report = LocalFinancialReportingService(ledger).generate(
                from_date="2026-04-01",
                to_date="2026-04-30",
                include_rows=True,
            )

            self.assertTrue(report["success"])
            self.assertEqual(report["basis"], "accrual")
            self.assertEqual(report["summary"]["scopedRecordCount"], 4)
            self.assertEqual(report["summary"]["includedRecordCount"], 3)
            self.assertEqual(report["summary"]["excludedReasons"]["reconciled_bank_evidence"], 1)
            profit_loss = report["reports"]["profitAndLoss"]["byCurrency"][0]
            self.assertEqual(profit_loss["revenueGross"], 242.0)
            self.assertEqual(profit_loss["revenueNet"], 200.0)
            self.assertEqual(profit_loss["expensesGross"], 171.0)
            self.assertEqual(profit_loss["expensesNet"], 150.0)
            self.assertEqual(profit_loss["netResult"], 50.0)
            vat = report["reports"]["vat"]["byCurrency"][0]
            self.assertEqual(vat["outputVat"], 42.0)
            self.assertEqual(vat["inputVat"], 21.0)
            self.assertEqual(vat["netVatPayable"], 21.0)
            cash = report["reports"]["cashFlow"]["byCurrency"][0]
            self.assertEqual(cash["outflow"], 171.0)
            self.assertEqual(cash["netMovement"], -171.0)

    def test_cash_basis_uses_only_bank_evidence_and_keeps_currencies_separate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = self._ledger(temp_dir)
            ledger.upsert_bookkeeping_record({
                "bankTransactionId": 22,
                "sourceType": "bank_transaction",
                "recordType": "income",
                "status": "draft",
                "targetSystem": "waveapps",
                "targetAccount": "Sales",
                "vendorName": "US Customer",
                "category": "Revenue",
                "recordDate": "2026-04-04",
                "amount": 100,
                "currency": "USD",
                "reviewRequired": False,
                "reconciliationStatus": "not_started",
            })

            report = LocalFinancialReportingService(ledger).generate(
                report_type="profit_and_loss",
                basis="cash",
                from_date="2026-04-01",
                to_date="2026-04-30",
                include_rows=True,
            )

            self.assertEqual(report["summary"]["includedRecordCount"], 3)
            self.assertEqual(report["summary"]["excludedReasons"]["not_cash_evidence"], 2)
            totals = {item["currency"]: item for item in report["report"]["byCurrency"]}
            self.assertEqual(totals["EUR"]["expensesGross"], 171.0)
            self.assertEqual(totals["USD"]["revenueGross"], 100.0)
            self.assertNotIn("reports", report)

    def test_accrual_report_suppresses_pending_linked_bank_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = self._ledger(temp_dir)
            pending = ledger.get_bookkeeping_record_by_bank_transaction(21)
            ledger.update_bookkeeping_record(int(pending["id"]), {
                "status": "needs_review",
                "reconciliationStatus": "candidate",
                "reviewRequired": True,
            })

            report = LocalFinancialReportingService(ledger).generate(
                from_date="2026-04-01",
                to_date="2026-04-30",
                include_rows=True,
            )

            self.assertEqual(report["summary"]["includedRecordCount"], 2)
            self.assertEqual(report["summary"]["excludedReasons"]["pending_reconciliation_bank_evidence"], 1)
            self.assertEqual(
                {row["sourceType"] for row in report["rows"]},
                {"document"},
            )

    def test_report_surfaces_quality_blockers_and_prepares_audited_csv(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = self._ledger(temp_dir)
            ledger.upsert_bookkeeping_record({
                "documentId": 12,
                "sourceType": "document",
                "recordType": "expense",
                "status": "needs_review",
                "targetSystem": "waveapps",
                "vendorName": "Unknown",
                "amount": 10,
                "currency": "EUR",
                "reviewRequired": True,
                "reconciliationStatus": "needs_review",
            })
            ledger.upsert_bookkeeping_record({
                "documentId": 13,
                "sourceType": "document",
                "recordType": "expense",
                "status": "rejected",
                "targetSystem": "waveapps",
                "amount": 99,
                "currency": "EUR",
                "reviewRequired": False,
                "reconciliationStatus": "ignored",
            })
            service = LocalFinancialReportingService(ledger)
            report = service.generate(from_date="2026-04-01", to_date="2026-04-30")
            artifact = service.csv_artifact(from_date="2026-04-01", to_date="2026-04-30")
            service.record_generation_audit(report, actor="test")

            blocker_codes = {item["code"] for item in report["summary"]["blockers"]}
            self.assertEqual(report["summary"]["readiness"], "needs_review")
            self.assertIn("undated_records_outside_period", blocker_codes)
            self.assertEqual(report["summary"]["undatedRecordCount"], 1)
            self.assertIn("unreconciled_record", blocker_codes)
            self.assertEqual(artifact["rowCount"], 3)
            self.assertIn("recordId,recordDate,sourceType", artifact["content"])
            self.assertEqual(artifact["externalSubmission"], "not_executed")
            self.assertEqual(
                ledger.list_audit_events(limit=1)[0]["action"],
                "local_reporting.report_generated",
            )

    def test_invalid_report_inputs_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = LocalFinancialReportingService(self._ledger(temp_dir))
            with self.assertRaisesRegex(ValueError, "Unsupported report type"):
                service.generate(report_type="balance_sheet")
            with self.assertRaisesRegex(ValueError, "Unsupported reporting basis"):
                service.generate(basis="guess")
            with self.assertRaisesRegex(ValueError, "cannot be later"):
                service.generate(from_date="2026-05-01", to_date="2026-04-01")


if __name__ == "__main__":
    unittest.main()
