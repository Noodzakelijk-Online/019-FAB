import unittest

from src.data_entry.waveapps_autonomous_operator import WaveappsAutonomousOperator


class TestWaveappsAutonomousOperator(unittest.TestCase):
    def test_safe_draft_action_can_execute_with_handler(self):
        operator = WaveappsAutonomousOperator(
            {"waveapps_autonomous_mode": "execute"},
            action_handlers={
                "transaction_add": lambda payload: {
                    "status": "success",
                    "message": "transaction created",
                    "external_id": "tx-123",
                    "payload": payload,
                }
            },
        )

        result = operator.execute(
            "transaction_add",
            {
                "date": "2026-06-28",
                "amount": 42.5,
                "account": "Checking",
                "category": "Office Supplies",
            },
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["external_id"], "tx-123")
        self.assertEqual(result["operation"]["safety"], "safe_draft")

    def test_missing_required_fields_route_to_review(self):
        operator = WaveappsAutonomousOperator({})

        result = operator.execute("bill_create", {"vendor": "ACME"})

        self.assertEqual(result["status"], "needs_review")
        self.assertIn("billDate", result["operation"]["plan"]["missing_fields"])
        self.assertIn("lineItems", result["operation"]["plan"]["missing_fields"])

    def test_confirmation_actions_are_blocked_without_explicit_enablement(self):
        operator = WaveappsAutonomousOperator({})

        result = operator.execute(
            "invoice_send",
            {"invoiceId": "inv-1", "recipientEmail": "customer@example.com"},
            confirmed=True,
        )

        self.assertEqual(result["status"], "blocked_requires_confirmation")

    def test_confirmed_actions_can_be_queued_when_enabled(self):
        operator = WaveappsAutonomousOperator({"waveapps_allow_confirmed_actions": True})

        result = operator.execute(
            "invoice_send",
            {"invoiceId": "inv-1", "recipientEmail": "customer@example.com"},
            confirmed=True,
        )

        self.assertEqual(result["status"], "queued")
        self.assertEqual(result["operation"]["safety"], "requires_confirmation")

    def test_credential_actions_are_blocked_by_default(self):
        operator = WaveappsAutonomousOperator({})

        result = operator.execute("connected_account_refresh", {"connectedAccountId": "bank-1"})

        self.assertEqual(result["status"], "blocked_requires_credentials")

    def test_operations_have_stable_idempotency_keys(self):
        operator = WaveappsAutonomousOperator({})
        payload = {
            "date": "2026-06-28",
            "amount": 42.5,
            "account": "Checking",
            "category": "Office Supplies",
        }

        first = operator.prepare_operation("transaction_add", payload)
        second = operator.prepare_operation("transaction_add", dict(reversed(list(payload.items()))))

        self.assertEqual(first["operation_id"], second["operation_id"])

    def test_operation_can_include_ready_playbook_capability(self):
        operator = WaveappsAutonomousOperator(
            {"waveapps_autonomous_mode": "dry_run"},
        )

        result = operator.execute(
            "transaction_categorize",
            {"transactionId": "tx-1", "category": "Software"},
            capability_id="vendor_category_learning",
            available_signals=["vendor_identity", "category_candidates"],
            confidence=0.93,
        )

        self.assertEqual(result["status"], "planned")
        self.assertEqual(result["operation"]["capability_plan"]["status"], "ready")

    def test_operation_blocks_when_playbook_capability_needs_signals(self):
        operator = WaveappsAutonomousOperator(
            {"waveapps_autonomous_mode": "dry_run"},
        )

        result = operator.execute(
            "transaction_categorize",
            {"transactionId": "tx-1", "category": "Software"},
            capability_id="vendor_category_learning",
            available_signals=["vendor_identity"],
            confidence=0.93,
        )

        self.assertEqual(result["status"], "needs_review")
        self.assertIn("category_candidates", result["operation"]["capability_plan"]["missing_signals"])

    def test_ledger_report_read_can_dry_run_with_reconciliation_capability(self):
        operator = WaveappsAutonomousOperator({"waveapps_autonomous_mode": "dry_run"})

        result = operator.execute(
            "report_table_read",
            {
                "reportType": "account-transactions",
                "fromDate": "2026-06-28",
                "toDate": "2026-06-28",
                "accountOption": "-1",
                "contactOption": "0",
            },
            capability_id="ledger_report_reconciliation",
            available_signals=["ledger_period", "account_scope", "reconciliation_status"],
            confidence=0.96,
        )

        self.assertEqual(result["status"], "planned")
        self.assertEqual(result["operation"]["safety"], "read_only")
        self.assertEqual(result["operation"]["capability_plan"]["status"], "ready")

    def test_prepare_workflow_expands_daily_reconciliation_into_wave_operations(self):
        operator = WaveappsAutonomousOperator({"waveapps_autonomous_mode": "dry_run"})

        result = operator.prepare_workflow(
            "daily_reconciliation_run",
            "2026-06-28",
            "2026-06-28",
            available_signals=[
                "ledger_period",
                "account_scope",
                "reconciliation_status",
                "source_document",
                "bank_transaction",
                "duplicate_fingerprint",
            ],
            confidence=0.96,
            account_option="-1",
            contact_option="0",
        )

        self.assertEqual(result["status"], "ready")
        self.assertTrue(result["can_run_autonomously"])
        action_ids = [operation["action_id"] for operation in result["operations"]]
        self.assertIn("report_table_read", action_ids)
        self.assertIn("report_empty_state_read", action_ids)
        self.assertTrue(all(operation["plan"]["status"] == "planned" for operation in result["operations"]))


if __name__ == "__main__":
    unittest.main()
