import unittest

from src.workflow.autonomous_playbook import (
    AutonomousBookkeeperPlaybook,
    list_automation_capabilities,
    list_automation_benchmarks,
    list_automation_services,
    plan_autonomous_capability,
    plan_autonomous_workflow,
    summarize_automation_benchmarks,
    summarize_automation_services,
    summarize_automation_playbook,
)


class TestAutonomousPlaybook(unittest.TestCase):
    def test_summary_tracks_competitor_informed_capabilities(self):
        summary = summarize_automation_playbook()

        self.assertEqual(summary["sources"], 4)
        self.assertGreaterEqual(summary["stages"], 8)
        self.assertGreaterEqual(summary["capabilities"], 10)
        self.assertGreaterEqual(summary["service_offerings"], 20)
        self.assertGreater(summary["services_by_source"]["layernext"], 0)
        self.assertGreater(summary["services_by_status"]["planned"], 0)
        self.assertGreaterEqual(summary["benchmark_areas"], 10)
        self.assertGreater(summary["high_priority_benchmark_gaps"], 0)
        self.assertGreater(summary["wave_linked_capabilities"], 0)
        self.assertGreater(summary["capabilities_by_autonomy"]["safe_draft"], 0)
        self.assertGreater(summary["benchmark_by_status"]["partial"], 0)

    def test_benchmark_summary_tracks_competitor_gaps(self):
        summary = summarize_automation_benchmarks()
        planned = list_automation_benchmarks("planned")

        self.assertEqual(summary["benchmark_areas"], 10)
        self.assertGreaterEqual(summary["benchmark_by_status"]["covered"], 2)
        self.assertGreaterEqual(summary["benchmark_by_status"]["planned"], 2)
        self.assertIn("chat_task_execution", {benchmark["id"] for benchmark in planned})
        self.assertIn("bank_statement_import_formats", {benchmark["id"] for benchmark in planned})

    def test_service_inventory_tracks_crawled_competitor_offerings(self):
        summary = summarize_automation_services()
        layernext_services = list_automation_services(source="layernext")
        dutch_service_notes = " ".join(service["netherlands_adaptation"] for service in layernext_services)

        self.assertGreaterEqual(summary["service_offerings"], 20)
        self.assertGreaterEqual(summary["services_by_source"]["booke_ai"], 5)
        self.assertGreaterEqual(summary["services_by_source"]["outmin"], 4)
        self.assertGreaterEqual(summary["services_by_source"]["bookeeping_ai"], 5)
        self.assertGreaterEqual(summary["services_by_source"]["layernext"], 5)
        self.assertGreater(summary["services_by_category"]["platform"], 0)
        self.assertIn("BTW", dutch_service_notes)

    def test_ready_capability_requires_all_signals_and_confidence(self):
        plan = plan_autonomous_capability(
            "receipt_to_bank_match",
            ["source_document", "bank_transaction", "duplicate_fingerprint"],
            confidence=0.95,
        )

        self.assertEqual(plan["status"], "ready")
        self.assertTrue(plan["can_run_autonomously"])

    def test_missing_signals_block_capability(self):
        plan = plan_autonomous_capability("ap_invoice_workflow", ["vendor_invoice"], confidence=0.99)

        self.assertEqual(plan["status"], "needs_signals")
        self.assertIn("vendor_identity", plan["missing_signals"])
        self.assertIn("line_items", plan["missing_signals"])

    def test_low_confidence_routes_to_review(self):
        plan = plan_autonomous_capability(
            "vendor_category_learning",
            ["vendor_identity", "category_candidates"],
            confidence=0.6,
        )

        self.assertEqual(plan["status"], "blocked_by_review")
        self.assertIn("confidence below 85%", plan["review_gates"])

    def test_document_planning_infers_relevant_capabilities(self):
        playbook = AutonomousBookkeeperPlaybook()

        plans = playbook.plan_document(
            {
                "document_type": "vendor_invoice",
                "source_document": "drive:file-1",
                "ocr_text": "Invoice total 42.50",
                "vendor_name": "ACME",
                "line_items": [{"description": "hosting", "amount": 42.5}],
            },
            available_signals=["category_candidates"],
            confidence=0.91,
        )
        capability_ids = [plan["capability"]["id"] for plan in plans if plan["capability"]]

        self.assertIn("document_capture_and_ocr", capability_ids)
        self.assertIn("vendor_category_learning", capability_ids)
        self.assertIn("ap_invoice_workflow", capability_ids)

    def test_capabilities_can_be_filtered_by_stage(self):
        capabilities = list_automation_capabilities("close_report")

        self.assertEqual(
            {capability["id"] for capability in capabilities},
            {"anomaly_and_health_monitoring", "month_end_close_pack"},
        )

        match_capabilities = list_automation_capabilities("match_reconcile")
        self.assertIn("ledger_report_reconciliation", {capability["id"] for capability in match_capabilities})

    def test_ledger_report_reconciliation_is_ready_with_wave_report_signals(self):
        plan = plan_autonomous_capability(
            "ledger_report_reconciliation",
            ["ledger_period", "account_scope", "reconciliation_status"],
            confidence=0.95,
        )

        self.assertEqual(plan["status"], "ready")
        self.assertTrue(plan["can_run_autonomously"])
        self.assertIn("report_table_read", plan["capability"]["wave_actions"])

    def test_daily_reconciliation_workflow_builds_wave_ledger_steps(self):
        plan = plan_autonomous_workflow(
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

        self.assertEqual(plan["status"], "ready")
        self.assertTrue(plan["can_run_autonomously"])
        self.assertIn("report_table_read", [step["action"] for step in plan["steps"]])
        self.assertIn("report_empty_state_read", [step["action"] for step in plan["steps"]])

    def test_playbook_exposes_benchmark_filtering(self):
        playbook = AutonomousBookkeeperPlaybook()

        high_level_gaps = playbook.benchmark("partial")

        self.assertGreater(len(high_level_gaps), 0)
        self.assertIn("continuous_reconciliation", {benchmark["id"] for benchmark in high_level_gaps})
        self.assertTrue(all(benchmark["fab_status"] == "partial" for benchmark in high_level_gaps))

    def test_playbook_exposes_service_filtering(self):
        playbook = AutonomousBookkeeperPlaybook()

        planned_compliance = playbook.services(category="compliance", status="planned")

        self.assertEqual({service["id"] for service in planned_compliance}, {"bookeeping_vertical_templates"})
        self.assertIn("ZZP", planned_compliance[0]["netherlands_adaptation"])


if __name__ == "__main__":
    unittest.main()
