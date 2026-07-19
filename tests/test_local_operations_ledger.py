import os
import sqlite3
import tempfile
import unittest

from src.operations.local_ledger import LocalOperationsLedger


class TestLocalOperationsLedger(unittest.TestCase):
    def test_existing_ledger_gets_workflow_recovery_linkage_columns_and_indexes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = os.path.join(temp_dir, "fab.sqlite3")
            connection = sqlite3.connect(ledger_path)
            try:
                connection.execute(
                    """
                    CREATE TABLE workflow_runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        status TEXT NOT NULL,
                        trigger_source TEXT NOT NULL,
                        documents_imported INTEGER NOT NULL DEFAULT 0,
                        documents_processed INTEGER NOT NULL DEFAULT 0,
                        documents_needing_review INTEGER NOT NULL DEFAULT 0,
                        error_message TEXT,
                        metadata_json TEXT,
                        started_at TEXT,
                        finished_at TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                connection.commit()
            finally:
                connection.close()

            ledger = LocalOperationsLedger(ledger_path)
            source_id = ledger.create_workflow_run({"status": "failed", "triggerSource": "test"})
            child_id = ledger.create_workflow_run({
                "status": "completed",
                "triggerSource": "test_recovery",
                "metadata": {
                    "recovery": {
                        "sourceWorkflowRunId": source_id,
                        "rootWorkflowRunId": source_id,
                    }
                },
            })

            connection = sqlite3.connect(ledger_path)
            try:
                columns = {row[1] for row in connection.execute("PRAGMA table_info(workflow_runs)")}
                indexes = {row[1] for row in connection.execute("PRAGMA index_list(workflow_runs)")}
            finally:
                connection.close()

            self.assertIn("recovery_source_workflow_run_id", columns)
            self.assertIn("recovery_root_workflow_run_id", columns)
            self.assertIn("idx_local_workflow_recovery_source", indexes)
            self.assertIn("idx_local_workflow_recovery_root", indexes)
            self.assertEqual(ledger.get_workflow_recovery_child(source_id)["id"], child_id)

    def test_workflow_steps_are_ordered_filterable_and_redacted(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            workflow_run_id = ledger.create_workflow_run({
                "status": "running",
                "triggerSource": "test_cycle",
            })
            first_step_id = ledger.create_workflow_step({
                "workflowRunId": workflow_run_id,
                "stepKey": "collect",
                "stage": "collect",
                "status": "pending",
                "stepOrder": 1,
                "metadata": {"apiToken": "must-not-persist", "scope": "receipts"},
            })
            ledger.create_workflow_step({
                "workflowRunId": workflow_run_id,
                "stepKey": "extract",
                "stage": "extract_validate",
                "status": "skipped",
                "stepOrder": 2,
                "durationMs": -10,
            })

            ledger.update_workflow_step(first_step_id, {
                "status": "completed",
                "startedAt": "2026-07-13T08:00:00Z",
                "finishedAt": "2026-07-13T08:00:01Z",
                "durationMs": 1000,
                "metadata": {"access_token": "must-not-persist", "registered": 2},
            })

            detail = ledger.get_workflow_run_with_steps(workflow_run_id)
            completed = ledger.list_workflow_steps(status="completed")
            metrics = ledger.dashboard_metrics()

            self.assertEqual([step["step_key"] for step in detail["steps"]], ["collect", "extract"])
            self.assertEqual(detail["step_count"], 2)
            self.assertEqual(completed[0]["duration_ms"], 1000)
            self.assertEqual(completed[0]["metadata"]["access_token"], "<redacted>")
            self.assertEqual(detail["steps"][1]["duration_ms"], 0)
            self.assertEqual(metrics["workflow_runs"], 1)
            self.assertEqual(metrics["workflow_steps"], 2)

    def test_runtime_lease_is_atomic_owner_checked_and_redacted(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))

            first = ledger.acquire_runtime_lease(
                "autonomy",
                "owner-one",
                ttl_seconds=60,
                metadata={"trigger": "worker", "accessToken": "secret"},
            )
            blocked = ledger.acquire_runtime_lease("autonomy", "owner-two", ttl_seconds=60)

            self.assertTrue(first["acquired"])
            self.assertTrue(first["lease"]["active"])
            self.assertNotIn("owner_token", first["lease"])
            self.assertEqual(first["lease"]["metadata"]["accessToken"], "<redacted>")
            self.assertFalse(blocked["acquired"])
            self.assertEqual(blocked["status"], "already_held")
            self.assertFalse(ledger.release_runtime_lease("autonomy", "owner-two"))
            connection = sqlite3.connect(ledger.path)
            try:
                connection.execute(
                    "UPDATE runtime_leases SET expires_at = ? WHERE lease_name = ?",
                    ("2000-01-01T00:00:00+00:00", "autonomy"),
                )
                connection.commit()
            finally:
                connection.close()
            recovered = ledger.acquire_runtime_lease("autonomy", "owner-two", ttl_seconds=60)
            self.assertTrue(recovered["acquired"])
            self.assertFalse(ledger.release_runtime_lease("autonomy", "owner-one"))
            self.assertTrue(ledger.release_runtime_lease("autonomy", "owner-two"))
            self.assertIsNone(ledger.get_runtime_lease("autonomy"))
            self.assertTrue(
                ledger.acquire_runtime_lease("autonomy", "owner-three", ttl_seconds=60)["acquired"]
            )

    def test_source_accounts_are_upserted_and_counted(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))

            source_id = ledger.upsert_source_account({
                "sourceType": "local_folder",
                "sourceIdentifier": os.path.join(temp_dir, "sort-out"),
                "label": "sort-out",
                "status": "ready",
                "documentsSeen": 2,
                "documentsImported": 1,
                "duplicatesDetected": 1,
            })
            same_source_id = ledger.upsert_source_account({
                "sourceType": "local_folder",
                "sourceIdentifier": os.path.join(temp_dir, "sort-out"),
                "label": "sort-out",
                "status": "ready",
                "documentsSeen": 3,
                "documentsImported": 2,
            })
            document_id = ledger.register_document({
                "sourceAccountId": source_id,
                "source": "local_folder",
                "sourceDocumentId": "receipt-1",
                "originalFilename": "receipt.pdf",
            })

            sources = ledger.list_source_accounts(source_type="local_folder")
            document = ledger.get_document(document_id)

            self.assertEqual(source_id, same_source_id)
            self.assertEqual(len(sources), 1)
            self.assertEqual(sources[0]["documents_seen"], 5)
            self.assertEqual(sources[0]["documents_imported"], 3)
            self.assertEqual(sources[0]["duplicates_detected"], 1)
            self.assertEqual(document["source_account_id"], source_id)

    def test_extracted_fields_are_replaced_and_returned_with_document_detail(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            document_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "scan-fields",
                "originalFilename": "receipt.pdf",
            })

            ledger.replace_extracted_fields(document_id, [
                {
                    "fieldName": "vendor_name",
                    "value": "Field Vendor",
                    "confidenceScore": 0.92,
                    "provenance": {"source": "ocr"},
                },
                {
                    "fieldName": "total_amount",
                    "value": 42.5,
                    "confidenceScore": 0.9,
                    "provenance": {"source": "regex"},
                },
            ])
            ledger.replace_extracted_fields(document_id, [
                {
                    "fieldName": "vendor_name",
                    "value": "Corrected Vendor",
                    "confidenceScore": 0.95,
                    "provenance": {"source": "rerun"},
                },
            ])

            fields = ledger.list_extracted_fields(document_id=document_id)
            detail = ledger.get_document(document_id)

            self.assertEqual(len(fields), 1)
            self.assertEqual(fields[0]["field_name"], "vendor_name")
            self.assertEqual(fields[0]["field_value"], "Corrected Vendor")
            self.assertEqual(fields[0]["normalized_value"], "Corrected Vendor")
            self.assertEqual(detail["extracted_fields"][0]["provenance"]["source"], "rerun")

    def test_wave_report_snapshots_are_upserted_and_filterable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))

            snapshot_id = ledger.record_wave_report_snapshot({
                "operationId": "wave:report:1",
                "workflowId": "daily_reconciliation_run",
                "reportType": "account-transactions",
                "reportSection": "detailed_reporting",
                "actionId": "report_table_read",
                "fromDate": "2026-06-28",
                "toDate": "2026-06-28",
                "basis": "accrual",
                "accountOption": "-1",
                "accountName": "All Accounts",
                "contactOption": "0",
                "contactName": "All Contacts",
                "cashMode": "1",
                "metadata": {"token": "secret", "source": "plan"},
            })
            same_snapshot_id = ledger.record_wave_report_snapshot({
                "operationId": "wave:report:1",
                "workflowId": "daily_reconciliation_run",
                "reportType": "account-transactions",
                "actionId": "report_export",
                "format": "csv",
                "status": "planned",
                "rowCount": 0,
            })

            snapshots = ledger.list_wave_report_snapshots(report_type="account-transactions")
            metrics = ledger.dashboard_metrics()

            self.assertEqual(snapshot_id, same_snapshot_id)
            self.assertEqual(len(snapshots), 1)
            self.assertEqual(snapshots[0]["action_id"], "report_export")
            self.assertEqual(snapshots[0]["export_format"], "csv")
            self.assertEqual(snapshots[0]["row_count"], 0)
            self.assertEqual(snapshots[0]["metadata"]["token"], "<redacted>")
            self.assertEqual(metrics["wave_report_snapshots"], 1)

    def test_wave_operation_snapshots_are_upserted_filterable_and_counted(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))

            snapshot_id = ledger.record_wave_operation_snapshot({
                "operationId": "wave:operation:1",
                "workflowId": "daily_reconciliation_run",
                "surface": "transactions",
                "actionId": "transaction_add",
                "mode": "prepare",
                "safety": "safe_draft",
                "status": "planned",
                "planStatus": "planned",
                "requiresConfirmation": True,
                "requiresCredentials": False,
                "requiredFields": ["amount", "date", "vendor_name"],
                "missingFields": [],
                "payload": {"transactionId": "tx-1"},
                "metadata": {"token": "secret"},
            })
            same_snapshot_id = ledger.record_wave_operation_snapshot({
                "operationId": "wave:operation:1",
                "workflowId": "daily_reconciliation_run",
                "surface": "transactions",
                "actionId": "transaction_add",
                "status": "completed",
                "planStatus": "ready",
                "requiresConfirmation": False,
                "payload": {"transactionId": "tx-1", "amount": 42.5},
            })
            snapshots = ledger.list_wave_operation_snapshots(surface="transactions")
            filtered = ledger.list_wave_operation_snapshots(safety="safe_draft", status="completed")
            metrics = ledger.dashboard_metrics()

            self.assertEqual(snapshot_id, same_snapshot_id)
            self.assertEqual(len(snapshots), 1)
            self.assertEqual(snapshots[0]["operation_id"], "wave:operation:1")
            self.assertEqual(snapshots[0]["required_fields"], ["amount", "date", "vendor_name"])
            self.assertEqual(snapshots[0]["metadata"]["token"], "<redacted>")
            self.assertEqual(len(filtered), 1)
            self.assertEqual(filtered[0]["plan_status"], "ready")
            self.assertEqual(metrics["wave_operation_snapshots"], 1)

    def test_vendor_category_rule_status_updates_are_governed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))

            rule_id = ledger.upsert_vendor_category_rule({
                "vendorName": "Office Shop",
                "category": "Office Supplies",
                "targetSystem": "waveapps_business",
                "status": "suggested",
            })
            approved_rule = ledger.update_vendor_category_rule_status(
                rule_id,
                "approved",
                resolution="Verified from recurring receipts.",
                actor="test",
            )
            same_rule_id = ledger.upsert_vendor_category_rule({
                "vendorName": "Office Shop",
                "category": "Office Supplies",
                "targetSystem": "waveapps_business",
                "status": "suggested",
            })

            self.assertEqual(rule_id, same_rule_id)
            rule = ledger.get_vendor_category_rule(rule_id)
            metrics = ledger.dashboard_metrics()

            self.assertEqual(approved_rule["status"], "approved")
            self.assertEqual(rule["status"], "approved")
            self.assertEqual(rule["usage_count"], 2)
            self.assertEqual(rule["metadata"]["statusHistory"][0]["to"], "approved")
            self.assertEqual(metrics["suggested_vendor_rules"], 0)

    def test_duplicate_candidates_are_upserted_listed_and_resolved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            original_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "original",
                "originalFilename": "original.pdf",
            })
            duplicate_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "copy",
                "originalFilename": "copy.pdf",
                "duplicateOfDocumentId": original_id,
            })

            candidate_id = ledger.record_duplicate_candidate({
                "documentId": duplicate_id,
                "candidateDocumentId": original_id,
                "matchType": "exact_content_hash",
                "confidenceScore": 1.0,
                "evidence": {"token": "secret", "contentSha256": "abc"},
            })
            same_candidate_id = ledger.record_duplicate_candidate({
                "documentId": duplicate_id,
                "candidateDocumentId": original_id,
                "matchType": "exact_content_hash",
                "status": "in_review",
                "confidenceScore": 0.99,
            })

            self.assertEqual(candidate_id, same_candidate_id)
            self.assertEqual(ledger.dashboard_metrics()["duplicate_candidates"], 1)
            self.assertEqual(ledger.dashboard_metrics()["open_duplicate_candidates"], 1)
            candidates = ledger.list_duplicate_candidates(status="in_review", document_id=duplicate_id)
            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0]["evidence"]["token"], "<redacted>")
            detail = ledger.get_document(duplicate_id)
            self.assertEqual(detail["duplicate_candidates"][0]["candidate_document_id"], original_id)

            resolved = ledger.resolve_duplicate_candidates_for_document(duplicate_id, "rejected", "Not the same receipt.")

            self.assertEqual(resolved, 1)
            self.assertEqual(ledger.dashboard_metrics()["open_duplicate_candidates"], 0)
            self.assertEqual(ledger.list_duplicate_candidates()[0]["status"], "rejected")

    def test_document_groups_are_persisted_with_members_and_status(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            first_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "scan-page-1",
                "originalFilename": "scan_001.pdf",
            })
            second_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "scan-page-2",
                "originalFilename": "scan_002.pdf",
            })

            group_id = ledger.upsert_document_group({
                "groupKey": "scanner:scan",
                "groupType": "scanner_batch",
                "title": "Scanner batch",
                "status": "candidate",
                "primaryDocumentId": first_id,
                "confidenceScore": 0.82,
                "metadata": {"token": "secret"},
            })
            same_group_id = ledger.upsert_document_group({
                "groupKey": "scanner:scan",
                "status": "needs_review",
                "confidenceScore": 0.9,
            })
            ledger.add_document_to_group(group_id, first_id, {"role": "primary", "sortOrder": 0})
            ledger.add_document_to_group(group_id, second_id, {"role": "page", "sortOrder": 1})

            self.assertEqual(group_id, same_group_id)
            groups = ledger.list_document_groups(status="needs_review")
            detail = ledger.get_document(first_id)
            self.assertEqual(len(groups), 1)
            self.assertEqual(groups[0]["member_count"], 2)
            self.assertEqual(groups[0]["metadata"]["token"], "<redacted>")
            self.assertEqual(detail["document_groups"][0]["members"][0]["document_id"], first_id)
            self.assertEqual(ledger.dashboard_metrics()["document_groups"], 1)
            self.assertEqual(ledger.dashboard_metrics()["open_document_groups"], 1)

            removed = ledger.remove_document_from_group(group_id, second_id, "Wrong page.")
            ledger.update_document_group_status(group_id, "split", "Split during review.")

            self.assertEqual(removed, 1)
            updated_group = ledger.get_document_group(group_id)
            self.assertEqual(updated_group["status"], "split")
            self.assertEqual(updated_group["member_count"], 1)
            self.assertEqual(ledger.dashboard_metrics()["open_document_groups"], 0)

    def test_register_document_is_idempotent_by_source_identity(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))

            first_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "scan-001",
                "originalFilename": "receipt.pdf",
                "processingStatus": "imported",
                "duplicateFingerprint": "fingerprint-1",
            })
            second_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "scan-001",
                "originalFilename": "receipt.pdf",
                "processingStatus": "validated",
                "vendorName": "Vendor",
            })
            ledger.create_review_item({
                "documentId": first_id,
                "reason": "low_confidence",
                "status": "pending",
            })
            ledger.record_audit_event({
                "action": "workflow.document.imported",
                "entityType": "bookkeeping_document",
                "entityId": str(first_id),
            })

            self.assertEqual(first_id, second_id)
            self.assertEqual(
                ledger.dashboard_metrics(),
                {
                    "documents": 1,
                    "pending_review": 1,
                    "duplicates": 0,
                    "duplicate_candidates": 0,
                    "open_duplicate_candidates": 0,
                    "document_groups": 0,
                    "open_document_groups": 0,
                    "suggested_vendor_rules": 0,
                    "unreconciled_documents": 1,
                    "failed_documents": 0,
                    "bank_statement_imports": 0,
                    "bank_transactions": 0,
                    "unreconciled_bank_transactions": 0,
                    "bookkeeping_records": 0,
                    "bookkeeping_record_line_items": 0,
                    "bookkeeping_records_needing_review": 0,
                    "export_ready_records": 0,
                    "export_attempts": 0,
                    "export_attempts_needing_approval": 0,
                    "approved_export_attempts": 0,
                    "attention_export_attempts": 0,
                    "supervised_export_attempts": 0,
                    "deferred_export_attempts": 0,
                    "executed_export_attempts": 0,
                    "wave_report_snapshots": 0,
                    "wave_operation_snapshots": 0,
                    "wave_sync_runs": 0,
                    "wave_entities": 0,
                    "wave_entities_missing_downstream": 0,
                    "financial_report_runs": 0,
                    "financial_report_runs_needing_attention": 0,
                    "notifications": 0,
                    "unread_notifications": 0,
                    "active_notifications": 0,
                    "notification_preferences": 0,
                    "compliance_assessments": 0,
                    "open_compliance_findings": 0,
                    "blocking_compliance_findings": 0,
                    "retention_records": 0,
                    "workflow_runs": 0,
                    "workflow_steps": 0,
                    "failed_workflow_steps": 0,
                    "audit_events": 1,
                },
            )

    def test_bookkeeping_records_are_upserted_and_filterable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            document_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "scan-record-1",
                "originalFilename": "receipt.txt",
                "processingStatus": "processed",
            })

            record_id = ledger.upsert_bookkeeping_record({
                "documentId": document_id,
                "sourceType": "document",
                "recordType": "expense",
                "status": "ready_to_route",
                "targetSystem": "waveapps_business",
                "vendorName": "Office Shop",
                "category": "Office Supplies",
                "recordDate": "2026-06-28",
                "amount": 42.5,
                "vatAmount": 7.38,
                "currency": "EUR",
                "reviewRequired": False,
                "exportStatus": "ready",
                "reconciliationStatus": "candidate",
                "metadata": {"token": "secret", "source": "test"},
            })
            same_record_id = ledger.upsert_bookkeeping_record({
                "documentId": document_id,
                "status": "export_draft_prepared",
                "exportStatus": "draft_prepared",
                "metadata": {"apiKey": "secret", "source": "rerun"},
            })
            line_count = ledger.replace_bookkeeping_record_line_items(record_id, [
                {
                    "itemName": "Printer paper",
                    "description": "A4 paper",
                    "quantity": 2,
                    "unitPrice": 17.56,
                    "amount": 35.12,
                    "taxAmount": 7.38,
                    "taxRate": 21,
                    "taxCode": "BTW 21%",
                    "category": "Office Supplies",
                    "accountName": "Office Supplies",
                    "metadata": {"token": "secret"},
                }
            ])

            records = ledger.list_bookkeeping_records(export_status="draft_prepared")
            detail = ledger.get_document(document_id)
            lines = ledger.list_bookkeeping_record_line_items(bookkeeping_record_id=record_id)
            metrics = ledger.dashboard_metrics()

            self.assertEqual(record_id, same_record_id)
            self.assertEqual(line_count, 1)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["status"], "export_draft_prepared")
            self.assertEqual(records[0]["vendor_name"], "Office Shop")
            self.assertEqual(records[0]["line_item_count"], 1)
            self.assertEqual(records[0]["line_items"][0]["tax_code"], "BTW 21%")
            self.assertEqual(records[0]["line_items"][0]["metadata"]["token"], "<redacted>")
            self.assertEqual(lines[0]["account_name"], "Office Supplies")
            self.assertEqual(records[0]["metadata"]["apiKey"], "<redacted>")
            self.assertEqual(detail["bookkeeping_record"]["id"], record_id)
            self.assertEqual(detail["bookkeeping_record"]["line_items"][0]["item_name"], "Printer paper")
            self.assertEqual(metrics["bookkeeping_records"], 1)
            self.assertEqual(metrics["bookkeeping_record_line_items"], 1)

    def test_vendor_and_category_directories_summarize_records_documents_and_rules(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            document_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "vendor-dir-doc",
                "originalFilename": "receipt.txt",
                "processingStatus": "processed",
                "vendorName": "Office Shop",
                "category": "Office Supplies",
                "transactionDate": "2026-06-28",
                "totalAmount": 42.5,
            })
            ledger.upsert_bookkeeping_record({
                "documentId": document_id,
                "sourceType": "document",
                "status": "ready_to_route",
                "targetSystem": "waveapps_business",
                "vendorName": "Office Shop",
                "category": "Office Supplies",
                "recordDate": "2026-06-28",
                "amount": 42.5,
                "currency": "EUR",
                "exportStatus": "ready",
            })
            ledger.upsert_bookkeeping_record({
                "bankTransactionId": 99,
                "sourceType": "bank_transaction",
                "status": "needs_review",
                "targetSystem": "mijngeldzaken",
                "vendorName": "Office Shop",
                "category": "Travel",
                "recordDate": "2026-06-29",
                "amount": 10.0,
                "currency": "EUR",
                "reviewRequired": True,
            })
            ledger.upsert_vendor_category_rule({
                "vendorName": "Office Shop",
                "category": "Office Supplies",
                "targetSystem": "waveapps_business",
                "status": "approved",
            })
            ledger.upsert_vendor_category_rule({
                "vendorName": "Office Shop",
                "category": "Travel",
                "targetSystem": "mijngeldzaken",
                "status": "suggested",
            })

            vendors = ledger.list_vendor_summaries()
            categories = ledger.list_category_summaries()
            office_vendor = next(item for item in vendors if item["vendorName"] == "Office Shop")
            office_category = next(item for item in categories if item["category"] == "Office Supplies")
            travel_category = next(item for item in categories if item["category"] == "Travel")

            self.assertEqual(office_vendor["recordCount"], 2)
            self.assertEqual(office_vendor["documentCount"], 1)
            self.assertEqual(office_vendor["bankTransactionCount"], 1)
            self.assertEqual(office_vendor["amountByCurrency"]["EUR"], 52.5)
            self.assertEqual(office_vendor["reviewRequiredCount"], 1)
            self.assertEqual(office_vendor["exportReadyCount"], 1)
            self.assertEqual(office_vendor["ruleCount"], 2)
            self.assertEqual(office_vendor["approvedRuleCount"], 1)
            self.assertEqual(office_vendor["suggestedRuleCount"], 1)
            self.assertTrue(office_vendor["needsAttention"])
            self.assertIn("Office Supplies", {item["value"] for item in office_vendor["categories"]})
            self.assertIn("mijngeldzaken", {item["value"] for item in office_vendor["targetSystems"]})
            self.assertEqual(office_category["recordCount"], 1)
            self.assertEqual(office_category["documentCount"], 1)
            self.assertEqual(office_category["amountByCurrency"]["EUR"], 42.5)
            self.assertIn("Office Shop", {item["value"] for item in office_category["vendors"]})
            self.assertEqual(travel_category["reviewRequiredCount"], 1)
            self.assertTrue(travel_category["needsAttention"])

    def test_export_attempts_are_idempotent_filterable_and_counted(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            document_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "scan-export-ledger",
                "originalFilename": "receipt.txt",
                "processingStatus": "export_draft_prepared",
            })
            record_id = ledger.upsert_bookkeeping_record({
                "documentId": document_id,
                "status": "export_draft_prepared",
                "exportStatus": "draft_prepared",
            })
            routing_id = ledger.create_routing_attempt({
                "documentId": document_id,
                "target": "waveapps:transactions",
                "status": "draft_prepared",
                "metadata": {"operation": {"operation_id": "op-ledger-1"}},
            })

            export_id = ledger.upsert_export_attempt({
                "bookkeepingRecordId": record_id,
                "documentId": document_id,
                "routingAttemptId": routing_id,
                "targetSystem": "waveapps",
                "targetAccount": "Office Supplies",
                "actionId": "transaction_add",
                "surface": "transactions",
                "operationId": "op-ledger-1",
                "payload": {"token": "secret", "amount": 42.5},
                "metadata": {"apiKey": "secret", "source": "test"},
            })
            same_export_id = ledger.upsert_export_attempt({
                "routingAttemptId": routing_id,
                "operationId": "op-ledger-1",
                "status": "approved",
                "approvalRequired": False,
                "externalSubmission": "approved_not_executed",
                "result": {"credential": "hidden"},
            })

            exports = ledger.list_export_attempts(status="approved")
            detail = ledger.get_document(document_id)
            metrics = ledger.dashboard_metrics()

            self.assertEqual(export_id, same_export_id)
            self.assertEqual(len(exports), 1)
            self.assertEqual(exports[0]["payload"]["token"], "<redacted>")
            self.assertEqual(exports[0]["metadata"]["apiKey"], "<redacted>")
            self.assertEqual(exports[0]["result"]["credential"], "<redacted>")
            self.assertEqual(detail["export_attempts"][0]["id"], export_id)
            self.assertEqual(metrics["export_attempts"], 1)
            self.assertEqual(metrics["export_attempts_needing_approval"], 0)
            self.assertEqual(metrics["approved_export_attempts"], 1)

    def test_bank_transactions_are_imported_idempotently_and_filterable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))

            import_id = ledger.create_bank_statement_import({
                "source": "wave_export",
                "accountIdentifier": "wave-checking",
                "filename": "account-transactions.csv",
                "format": "csv",
                "status": "running",
                "rowsSeen": 2,
            })
            transaction_id = ledger.upsert_bank_transaction({
                "importId": import_id,
                "accountIdentifier": "wave-checking",
                "transactionId": "tx-bank-1",
                "transactionDate": "2026-06-28",
                "amount": -42.5,
                "currency": "EUR",
                "description": "Office Shop",
                "counterparty": "Office Shop",
                "duplicateFingerprint": "fingerprint-1",
                "metadata": {"apiToken": "secret", "source": "csv"},
            })
            same_transaction_id = ledger.upsert_bank_transaction({
                "importId": import_id,
                "accountIdentifier": "wave-checking",
                "transactionId": "tx-bank-1",
                "transactionDate": "2026-06-28",
                "amount": -42.5,
                "currency": "EUR",
                "description": "Office Shop updated",
                "reconciliationStatus": "candidate",
            })
            ledger.update_bank_statement_import(import_id, {
                "status": "completed",
                "rowsImported": 1,
                "duplicates": 1,
            })

            transactions = ledger.list_bank_transactions(
                account_identifier="wave-checking",
                reconciliation_status="candidate",
            )
            imports = ledger.list_bank_statement_imports(account_identifier="wave-checking")
            metrics = ledger.dashboard_metrics()

            self.assertEqual(transaction_id, same_transaction_id)
            self.assertEqual(len(transactions), 1)
            self.assertEqual(transactions[0]["description"], "Office Shop updated")
            self.assertEqual(transactions[0]["metadata"]["apiToken"], "<redacted>")
            self.assertEqual(imports[0]["status"], "completed")
            self.assertEqual(imports[0]["rows_imported"], 1)
            self.assertEqual(imports[0]["duplicates"], 1)
            self.assertEqual(metrics["bank_statement_imports"], 1)
            self.assertEqual(metrics["bank_transactions"], 1)
            self.assertEqual(metrics["unreconciled_bank_transactions"], 1)

    def test_list_review_items_accepts_open_status_collection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            document_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "scan-002",
                "originalFilename": "receipt.pdf",
            })
            pending_id = ledger.create_review_item({
                "documentId": document_id,
                "reason": "pending_check",
                "status": "pending",
            })
            in_review_id = ledger.create_review_item({
                "documentId": document_id,
                "reason": "active_check",
                "status": "in_review",
            })
            ledger.create_review_item({
                "documentId": document_id,
                "reason": "closed_check",
                "status": "resolved",
            })

            open_items = ledger.list_review_items(status=("pending", "in_review"))

            self.assertEqual({item["id"] for item in open_items}, {pending_id, in_review_id})

    def test_reconciliation_matches_can_be_filtered_and_resolved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            document_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "scan-reconcile",
                "originalFilename": "receipt.pdf",
                "processingStatus": "processed",
            })
            match_id = ledger.create_reconciliation_match({
                "documentId": document_id,
                "bankTransactionId": "tx-1",
                "status": "candidate",
                "confidenceScore": 0.98,
                "amountDifference": 0,
            })

            matches = ledger.list_reconciliation_matches(document_id=document_id, bank_transaction_id="tx-1")
            ledger.update_reconciliation_match(match_id, {"status": "approved", "matchedAt": "2026-06-28T00:00:00Z"})

            self.assertEqual(matches[0]["id"], match_id)
            self.assertEqual(ledger.get_reconciliation_match(match_id)["status"], "approved")

    def test_existing_ledger_gets_reconciliation_status_column(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = os.path.join(temp_dir, "fab.sqlite3")
            connection = sqlite3.connect(ledger_path)
            try:
                connection.execute(
                    """
                    CREATE TABLE bookkeeping_documents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source TEXT NOT NULL,
                        source_document_id TEXT,
                        original_filename TEXT NOT NULL,
                        mime_type TEXT,
                        storage_path TEXT,
                        document_type TEXT NOT NULL DEFAULT 'unknown',
                        processing_status TEXT NOT NULL DEFAULT 'imported',
                        duplicate_fingerprint TEXT,
                        duplicate_of_document_id INTEGER,
                        vendor_name TEXT,
                        category TEXT,
                        transaction_date TEXT,
                        total_amount REAL,
                        vat_amount REAL,
                        confidence_score REAL,
                        ocr_text TEXT,
                        extracted_data_json TEXT,
                        metadata_json TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        UNIQUE(source, source_document_id)
                    )
                    """
                )
                connection.commit()
            finally:
                connection.close()

            ledger = LocalOperationsLedger(ledger_path)
            document_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "legacy-1",
                "originalFilename": "legacy.pdf",
                "processingStatus": "processed",
            })

            self.assertEqual(ledger.get_document(document_id)["reconciliation_status"], "not_started")

    def test_audit_event_details_redact_nested_credentials(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))

            ledger.record_audit_event({
                "action": "test.secret_redaction",
                "entityType": "test",
                "details": {
                    "accessToken": "top-secret",
                    "nested": {"password": "also-secret", "status": "failed"},
                    "error": "provider failed?access_token=query-secret Authorization: Bearer header-secret",
                },
            })

            event = ledger.list_audit_events(limit=1)[0]
            self.assertEqual(event["details"]["accessToken"], "<redacted>")
            self.assertEqual(event["details"]["nested"]["password"], "<redacted>")
            self.assertEqual(event["details"]["nested"]["status"], "failed")
            self.assertNotIn("query-secret", event["details"]["error"])
            self.assertNotIn("header-secret", event["details"]["error"])
            self.assertIn("[REDACTED]", event["details"]["error"])


if __name__ == "__main__":
    unittest.main()
