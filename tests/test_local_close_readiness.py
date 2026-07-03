import os
import tempfile
import unittest

from src.operations.local_close_readiness import LocalCloseReadinessService
from src.operations.local_bookkeeping_records import LocalBookkeepingRecordService
from src.operations.local_ledger import LocalOperationsLedger
from src.operations.local_wave_control import LocalWaveControlService


class TestLocalCloseReadinessService(unittest.TestCase):
    def test_close_readiness_blocks_without_wave_report_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))

            result = LocalCloseReadinessService(ledger).assess(
                workflow_id="daily_reconciliation_run",
                from_date="2026-06-28",
                to_date="2026-06-28",
            )

            self.assertEqual(result["status"], "blocked")
            self.assertFalse(result["canClose"])
            self.assertEqual(result["reportControls"]["status"], "blocked_missing_report_plan")
            gate = next(item for item in result["gates"] if item["id"] == "wave_report_evidence")
            self.assertEqual(gate["status"], "blocked")

    def test_close_readiness_passes_after_zero_activity_wave_report_capture(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            _capture_wave_report_result(ledger, row_count=0)

            result = LocalCloseReadinessService(ledger).assess(
                workflow_id="daily_reconciliation_run",
                from_date="2026-06-28",
                to_date="2026-06-28",
            )

            self.assertEqual(result["status"], "ready")
            self.assertTrue(result["canClose"])
            self.assertEqual(result["blockingCount"], 0)
            self.assertEqual(result["reportControls"]["status"], "ready")
            self.assertTrue(all(gate["status"] == "ready" for gate in result["gates"]))

    def test_close_readiness_blocks_when_wave_bank_rows_need_receipts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            _capture_wave_report_result(
                ledger,
                result_text=(
                    "Date;Description;Debit;Credit;Reference\n"
                    "2026-06-28;Office Shop;42,50;;wave-1\n"
                    "2026-06-29;Client payment;;100,00;wave-2\n"
                ),
                import_transactions=True,
            )

            result = LocalCloseReadinessService(ledger).assess(
                workflow_id="daily_reconciliation_run",
                from_date="2026-06-28",
                to_date="2026-06-28",
            )

            self.assertEqual(result["status"], "blocked")
            self.assertFalse(result["canClose"])
            self.assertEqual(result["reportControls"]["status"], "ready")
            self.assertEqual(result["metrics"]["pendingReview"], 2)
            self.assertEqual(result["metrics"]["unreconciledBankTransactions"], 2)
            gates = {gate["id"]: gate for gate in result["gates"]}
            self.assertEqual(gates["manual_review_queue"]["status"], "blocked")
            self.assertEqual(gates["bank_reconciliation"]["status"], "blocked")
            self.assertEqual(gates["wave_report_evidence"]["status"], "ready")

    def test_close_readiness_blocks_on_master_ledger_blockers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            _capture_wave_report_result(ledger, row_count=0)
            transaction_id = ledger.upsert_bank_transaction({
                "accountIdentifier": "wave-checking",
                "transactionId": "tx-close-master-ledger-block",
                "transactionDate": "2026-06-28",
                "amount": -42.5,
                "currency": "EUR",
                "description": "Missing receipt",
                "reconciliationStatus": "missing_receipt",
            })
            LocalBookkeepingRecordService(ledger, {}).upsert_from_bank_transaction(transaction_id)

            result = LocalCloseReadinessService(ledger).assess(
                workflow_id="daily_reconciliation_run",
                from_date="2026-06-28",
                to_date="2026-06-28",
            )

            gates = {gate["id"]: gate for gate in result["gates"]}
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(gates["master_ledger_projection"]["status"], "blocked")
            self.assertEqual(gates["master_ledger_projection"]["evidence"]["blockedRows"], 1)
            self.assertEqual(result["metrics"]["masterLedgerRows"], 1)
            self.assertEqual(result["metrics"]["masterLedgerBlockedRows"], 1)
            self.assertIn("Resolve blocked master-ledger rows", " ".join(result["nextActions"]))


def _capture_wave_report_result(
    ledger: LocalOperationsLedger,
    row_count: int = 0,
    result_text: str = "",
    import_transactions: bool = False,
):
    service = LocalWaveControlService()
    plan = service.plan_workflow({
        "workflowId": "daily_reconciliation_run",
        "fromDate": "2026-06-28",
        "toDate": "2026-06-28",
        "accountOption": "-1",
        "contactOption": "0",
    })
    service.record_workflow_report_snapshots(ledger, plan)
    payload = {
        "workflowId": "daily_reconciliation_run",
        "reportType": "account-transactions",
        "actionId": "report_table_read",
    }
    if result_text:
        payload.update({
            "format": "csv",
            "resultText": result_text,
            "accountIdentifier": "wave-checking",
            "importTransactions": import_transactions,
            "refreshBookkeepingRecords": import_transactions,
            "runReconciliation": import_transactions,
        })
    else:
        payload["result"] = {
            "rowCount": row_count,
            "totalDebits": 0,
            "totalCredits": 0,
        }
    return service.record_report_result(ledger, payload)


if __name__ == "__main__":
    unittest.main()
