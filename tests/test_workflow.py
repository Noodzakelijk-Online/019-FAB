import unittest
import json
import logging
import os
import tempfile
from unittest.mock import MagicMock, patch, ANY

from src.workflow.controller import WorkflowController


class TestWorkflow(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.addCleanup(self._close_logger_handlers)
        self.config = {
            "log_file": os.path.join(self.temp_dir.name, "test_workflow.log"),
            "manual_review_queue_file": os.path.join(self.temp_dir.name, "manual_review_queue.json"),
            "error_recovery_max_retries": 1,
            "error_recovery_retry_delay_seconds": 0,
            "email_notifications_enabled": False,
            "workflow_execute_external_posting": True,
            "mijngeldzaken_username": "test_user",
            "mijngeldzaken_password": "test_pass",
            "mijngeldzaken_login_url": "http://mijngeldzaken.test/login",
            "mijngeldzaken_import_url": "http://mijngeldzaken.test/import",
            "mijngeldzaken_csv_template": {
                "columns": ["Date", "Description", "Amount", "Category"],
                "mapping": {
                    "Date": "extracted_data.transaction_date",
                    "Description": "extracted_data.description",
                    "Amount": "extracted_data.total_amount",
                    "Category": "category",
                },
                "delimiter": ";",
            },
            "mijngeldzaken_category_mapping": {"Personal": "Huishouden"},
            "waveapps_business_access_token": "business_token",
            "waveapps_business_id": "business_id",
            "waveapps_business_category_mapping": {"Business": "Office Supplies"},
            "waveapps_personal_access_token": "personal_token",
            "waveapps_personal_id": "personal_id",
            "waveapps_personal_category_mapping": {"Handicaps": "Medical Expenses"},
            "waveapps_handicap_tag": "#handicap",
            "ml_model_path": "/tmp/ml_categorizer_model.joblib",
            "ml_vectorizer_path": "/tmp/tfidf_vectorizer.joblib",
            "categorization_rules": {
                "Personal": {"keywords": ["supermarket"], "vendors": []},
                "Business": {"keywords": ["office"], "vendors": []},
                "Handicaps": {"keywords": ["therapy"], "vendors": []},
            },
            "default_fallback_category": "Manual Review",
            "ml_confidence_threshold": 0.7,
            "receipt_validation_required_fields": ["vendor_name", "total_amount"],
            "btw_number_pattern": r"NL\d{9}B\d{2}",
            "budget_file": os.path.join(self.temp_dir.name, "budgets.json"),
            "banking_api_endpoint": "http://banking.api/",
            "banking_api_credentials": {"client_id": "test", "client_secret": "test"},
            "backup_base_dir": os.path.join(self.temp_dir.name, "backups"),
            "backup_paths": [],
            "backup_config": {"type": "zip"},
            "document_version_manifest_path": os.path.join(self.temp_dir.name, "document_versions.json"),
            "workflow_state_file": os.path.join(self.temp_dir.name, "workflow_state.json"),
        }
        self.patchers = {
            name: patch(f"src.workflow.controller.{name}")
            for name in [
                "GmailFetcher",
                "DriveFetcher",
                "FreshdeskFetcher",
                "PhotosFetcher",
                "ProcessorPipeline",
                "HybridCategorizer",
                "MijngeldzakenHandler",
                "WaveappsBusinessHandler",
                "WaveappsPersonalHandler",
                "LearningManager",
                "EnhancedErrorRecovery",
                "ValidationManager",
                "BudgetManager",
                "BankingAPI",
                "AutomatedReconciliation",
                "ManualReviewInterface",
                "BackupManager",
                "SecurityManager",
                "PerformanceOptimizer",
                "OperationsClient",
            ]
        }
        self.mocks = {name: patcher.start() for name, patcher in self.patchers.items()}
        self.addCleanup(self._stop_patchers)

    def _stop_patchers(self):
        for patcher in self.patchers.values():
            patcher.stop()

    def _close_logger_handlers(self):
        logger = logging.getLogger("automated_bookkeeping")
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()

    def _configure_successful_run(self, category="Business", entry_result=None):
        self.mocks["GmailFetcher"].return_value.fetch_documents.return_value = [
            {"id": "doc1", "original_filename": "receipt.pdf", "local_path": os.path.join(self.temp_dir.name, "receipt.pdf")}
        ]
        self.mocks["DriveFetcher"].return_value.fetch_documents.return_value = []
        self.mocks["FreshdeskFetcher"].return_value.fetch_documents.return_value = []
        self.mocks["PhotosFetcher"].return_value.fetch_documents.return_value = []
        self.mocks["ProcessorPipeline"].return_value.process_document.return_value = {
            "ocr_text": "dummy ocr text",
            "extracted_data": {
                "vendor_name": "Test Vendor",
                "total_amount": 100.0,
                "transaction_date": "2025-01-01",
            },
        }
        self.mocks["HybridCategorizer"].return_value.categorize.return_value = {
            "category": category,
            "confidence_score": 0.9,
        }
        self.mocks["ValidationManager"].return_value.validate_receipt.return_value = {"is_valid": True}
        self.mocks["BudgetManager"].return_value.check_budget.return_value = {"is_within_budget": True}
        self.mocks["BankingAPI"].return_value.fetch_transactions.return_value = []
        self.mocks["AutomatedReconciliation"].return_value.reconcile.return_value = []
        self.mocks["BackupManager"].return_value.perform_backup.return_value = {"status": "success"}
        self.mocks["OperationsClient"].return_value.create_workflow_run.return_value = 34
        self.mocks["OperationsClient"].return_value.register_document.return_value = 12

        result = entry_result or {"status": "success", "external_id": "expense-1"}
        self.mocks["WaveappsBusinessHandler"].return_value.enter_data.return_value = result
        self.mocks["MijngeldzakenHandler"].return_value.enter_data.return_value = result
        self.mocks["WaveappsPersonalHandler"].return_value.enter_data.return_value = result

    def test_workflow_records_autonomous_operations(self):
        self._configure_successful_run()

        controller = WorkflowController(self.config)
        controller.run_workflow()

        operations = self.mocks["OperationsClient"].return_value
        self.mocks["GmailFetcher"].return_value.fetch_documents.assert_called_once()
        self.mocks["ProcessorPipeline"].return_value.process_document.assert_called_once_with(os.path.join(self.temp_dir.name, "receipt.pdf"))
        self.mocks["HybridCategorizer"].return_value.categorize.assert_called_once()
        self.mocks["WaveappsBusinessHandler"].return_value.enter_data.assert_called_once()
        self.mocks["BackupManager"].return_value.perform_backup.assert_called_once()
        reconciliation_documents = self.mocks["AutomatedReconciliation"].return_value.reconcile.call_args.args[1]
        self.assertEqual([document["document_id"] for document in reconciliation_documents], ["doc1"])
        operations.register_document.assert_called_once_with(
            "gmail",
            ANY,
            processing_status="imported",
        )
        operations.create_routing_attempt.assert_called_with(
            12,
            "waveapps_business",
            "success",
            workflow_run_id=34,
            external_id="expense-1",
            metadata=ANY,
        )
        operations.update_workflow_run.assert_called_with(
            34,
            status="completed",
            documentsImported=1,
            documentsProcessed=1,
            documentsNeedingReview=0,
        )
        operations.record_audit_event.assert_any_call(
            "workflow.run.completed",
            "workflow_run",
            "34",
            {
                "status": "completed",
                "documentsImported": 1,
                "documentsProcessed": 1,
                "documentsNeedingReview": 0,
            },
        )

    def test_overlapping_workflow_run_is_skipped_and_audited(self):
        self._configure_successful_run()
        controller = WorkflowController(self.config)
        controller.checkpoint_store.acquire_run_lock = MagicMock(return_value=False)

        controller.run_workflow()

        self.mocks["GmailFetcher"].return_value.fetch_documents.assert_not_called()
        operations = self.mocks["OperationsClient"].return_value
        operations.create_workflow_run.assert_not_called()
        operations.record_audit_event.assert_called_once_with(
            "workflow.run.skipped_already_running",
            "workflow_run",
            details={"lockPath": controller.checkpoint_store.run_lock_path},
        )

    def test_workflow_sends_unroutable_documents_to_review(self):
        self._configure_successful_run(category="Unknown")

        controller = WorkflowController(self.config)
        controller.run_workflow()

        operations = self.mocks["OperationsClient"].return_value
        self.mocks["ManualReviewInterface"].return_value.add_to_review_queue.assert_called_with(
            "doc1",
            "no_target_system",
            "Category Unknown has no defined target system.",
        )
        operations.create_review_item.assert_called_with(
            12,
            "no_target_system",
            "Category Unknown has no defined target system.",
        )
        operations.record_audit_event.assert_any_call(
            "workflow.review_item.queued",
            "bookkeeping_document",
            "12",
            {
                "documentId": "doc1",
                "reason": "no_target_system",
                "details": "Category Unknown has no defined target system.",
            },
        )
        operations.create_routing_attempt.assert_called_with(
            12,
            "none",
            "requires_review",
            workflow_run_id=34,
            message="no_route_for_category",
            metadata=ANY,
        )
        operations.update_workflow_run.assert_called_with(
            34,
            status="completed_with_review",
            documentsImported=1,
            documentsProcessed=1,
            documentsNeedingReview=1,
        )

    def test_routing_failure_is_reviewed_without_aborting_workflow(self):
        self._configure_successful_run()

        controller = WorkflowController(self.config)
        controller.bookkeeping_router.route = MagicMock(
            side_effect=RuntimeError("Routing rules unavailable")
        )
        controller.run_workflow()

        self.mocks["WaveappsBusinessHandler"].return_value.enter_data.assert_not_called()
        self.mocks["ManualReviewInterface"].return_value.add_to_review_queue.assert_called_once_with(
            "doc1",
            "routing_failed",
            "Routing rules unavailable",
        )
        self.mocks["BackupManager"].return_value.perform_backup.assert_called_once()
        operations = self.mocks["OperationsClient"].return_value
        operations.create_routing_attempt.assert_called_with(
            12,
            "manual_review",
            "requires_review",
            workflow_run_id=34,
            message="Routing rules unavailable",
            metadata={"reason": "routing_failed"},
        )
        operations.update_workflow_run.assert_called_with(
            34,
            status="completed_with_review",
            documentsImported=1,
            documentsProcessed=1,
            documentsNeedingReview=1,
        )
        with open(self.config["workflow_state_file"], "r", encoding="utf-8") as handle:
            workflow_state = json.load(handle)
        self.assertEqual(
            workflow_state["source_documents"]["gmail:doc1"]["status"],
            "needs_review_routing_failed",
        )

    def test_workflow_sends_low_confidence_categories_to_review(self):
        self._configure_successful_run(category="Business")
        self.mocks["HybridCategorizer"].return_value.categorize.return_value = {
            "category": "Business",
            "confidence_score": 0.42,
        }

        controller = WorkflowController(self.config)
        controller.run_workflow()

        operations = self.mocks["OperationsClient"].return_value
        self.mocks["ValidationManager"].return_value.validate_receipt.assert_not_called()
        self.mocks["WaveappsBusinessHandler"].return_value.enter_data.assert_not_called()
        self.mocks["AutomatedReconciliation"].return_value.reconcile.assert_called_once_with([], [])
        operations.create_routing_attempt.assert_any_call(
            12,
            "manual_review",
            "requires_review",
            workflow_run_id=34,
            message=ANY,
            metadata={
                "reason": "low_categorization_confidence",
                "category": "Business",
                "confidenceScore": 0.42,
                "threshold": 0.7,
            },
        )
        operations.create_review_item.assert_called_with(
            12,
            "low_categorization_confidence",
            ANY,
        )
        operations.update_workflow_run.assert_called_with(
            34,
            status="completed_with_review",
            documentsImported=1,
            documentsProcessed=1,
            documentsNeedingReview=1,
        )
        with open(self.config["workflow_state_file"], "r", encoding="utf-8") as handle:
            workflow_state = json.load(handle)
        self.assertEqual(
            workflow_state["source_documents"]["gmail:doc1"]["status"],
            "needs_review_low_confidence",
        )
        self.assertEqual(workflow_state["known_documents"], [])

    def test_workflow_does_not_reconcile_failed_data_entry(self):
        self._configure_successful_run(
            entry_result={
                "status": "failure",
                "message": "Temporary bookkeeping API outage.",
                "requires_manual_review": False,
            }
        )

        controller = WorkflowController(self.config)
        controller.run_workflow()

        self.mocks["AutomatedReconciliation"].return_value.reconcile.assert_called_once_with([], [])
        with open(self.config["workflow_state_file"], "r", encoding="utf-8") as handle:
            workflow_state = json.load(handle)
        self.assertEqual(
            workflow_state["source_documents"]["gmail:doc1"]["status"],
            "failed_data_entry",
        )
        self.assertEqual(workflow_state["known_documents"], [])
        self.mocks["OperationsClient"].return_value.update_workflow_run.assert_called_with(
            34,
            status="failed",
            documentsImported=1,
            documentsProcessed=1,
            documentsNeedingReview=0,
        )

    def test_workflow_defaults_to_draft_first_external_posting(self):
        self.config["workflow_execute_external_posting"] = False
        self._configure_successful_run()

        controller = WorkflowController(self.config)
        controller.run_workflow()

        operations = self.mocks["OperationsClient"].return_value
        self.mocks["WaveappsBusinessHandler"].return_value.enter_data.assert_not_called()
        operations.create_routing_attempt.assert_any_call(
            12,
            "waveapps_business",
            "approval_required",
            workflow_run_id=34,
            message=ANY,
            metadata=ANY,
        )
        operations.create_review_item.assert_any_call(
            12,
            "external_posting_approval_required",
            ANY,
        )
        operations.record_audit_event.assert_any_call(
            "workflow.document.external_submission_blocked",
            "bookkeeping_document",
            "12",
            ANY,
        )
        with open(self.config["workflow_state_file"], "r", encoding="utf-8") as handle:
            workflow_state = json.load(handle)
        self.assertEqual(
            workflow_state["source_documents"]["gmail:doc1"]["status"],
            "needs_review_external_posting_approval",
        )
        operations.update_workflow_run.assert_called_with(
            34,
            status="completed_with_review",
            documentsImported=1,
            documentsProcessed=1,
            documentsNeedingReview=1,
        )

    def test_workflow_defers_rate_limited_data_entry_without_review_or_failure(self):
        self._configure_successful_run(
            entry_result={
                "status": "rate_limited",
                "message": "WaveApps dispatch deferred because its configured quota is currently unavailable.",
                "retryable": True,
                "retry_after_seconds": 60,
                "requires_manual_review": False,
                "rate_limit": {"name": "WaveApps", "quotaExhausted": False},
            }
        )

        controller = WorkflowController(self.config)
        controller.run_workflow()

        operations = self.mocks["OperationsClient"].return_value
        self.mocks["AutomatedReconciliation"].return_value.reconcile.assert_called_once_with([], [])
        operations.create_routing_attempt.assert_any_call(
            12,
            "waveapps_business",
            "deferred",
            workflow_run_id=34,
            message="WaveApps dispatch deferred because its configured quota is currently unavailable.",
            metadata=ANY,
        )
        operations.update_document.assert_any_call(12, ANY, processing_status="deferred")
        operations.record_audit_event.assert_any_call(
            "workflow.document.data_entry_deferred",
            "bookkeeping_document",
            "12",
            ANY,
        )
        self.assertNotIn("data_entry_failed", [call.args[1] for call in operations.create_review_item.call_args_list])
        with open(self.config["workflow_state_file"], "r", encoding="utf-8") as handle:
            workflow_state = json.load(handle)
        self.assertEqual(
            workflow_state["source_documents"]["gmail:doc1"]["status"],
            "deferred_data_entry",
        )
        self.assertEqual(workflow_state["known_documents"], [])
        operations.update_workflow_run.assert_called_with(
            34,
            status="completed",
            documentsImported=1,
            documentsProcessed=1,
            documentsNeedingReview=0,
        )

    def test_workflow_pauses_mijngeldzaken_submission_for_supervision(self):
        self._configure_successful_run(
            category="Personal",
            entry_result={
                "status": "supervised_action_required",
                "message": "MijnGeldzaken CSV prepared for supervised import.",
                "artifact": {"filename": "mgz.csv", "sha256": "a" * 64},
                "external_submission": "not_executed",
                "requires_supervision": True,
                "requires_manual_review": True,
            },
        )

        controller = WorkflowController(self.config)
        controller.run_workflow()

        operations = self.mocks["OperationsClient"].return_value
        self.mocks["MijngeldzakenHandler"].return_value.enter_data.assert_called_once()
        operations.create_routing_attempt.assert_any_call(
            12,
            "mijngeldzaken",
            "requires_review",
            workflow_run_id=34,
            message="MijnGeldzaken CSV prepared for supervised import.",
            metadata=ANY,
        )
        operations.update_document.assert_any_call(
            12,
            ANY,
            processing_status="awaiting_supervised_submission",
        )
        operations.create_review_item.assert_any_call(
            12,
            "mijngeldzaken_supervision_required",
            "MijnGeldzaken CSV prepared for supervised import.",
        )
        operations.record_audit_event.assert_any_call(
            "workflow.document.supervised_submission_required",
            "bookkeeping_document",
            "12",
            ANY,
        )
        with open(self.config["workflow_state_file"], "r", encoding="utf-8") as handle:
            workflow_state = json.load(handle)
        self.assertEqual(
            workflow_state["source_documents"]["gmail:doc1"]["status"],
            "needs_supervised_external_submission",
        )
        operations.update_workflow_run.assert_called_with(
            34,
            status="completed_with_review",
            documentsImported=1,
            documentsProcessed=1,
            documentsNeedingReview=1,
        )

    def test_fetch_errors_are_recovered_and_run_is_marked_failed(self):
        self.mocks["GmailFetcher"].return_value.fetch_documents.side_effect = Exception("Fetch error")
        self.mocks["DriveFetcher"].return_value.fetch_documents.return_value = []
        self.mocks["FreshdeskFetcher"].return_value.fetch_documents.return_value = []
        self.mocks["PhotosFetcher"].return_value.fetch_documents.return_value = []
        self.mocks["OperationsClient"].return_value.create_workflow_run.return_value = 34

        controller = WorkflowController(self.config)
        controller.run_workflow()

        self.mocks["EnhancedErrorRecovery"].return_value.handle_error.assert_called_with(ANY, "fetch_gmail")
        operations = self.mocks["OperationsClient"].return_value
        operations.record_audit_event.assert_any_call(
            "workflow.error",
            "workflow_run",
            "34",
            {
                "operation": "fetch_gmail",
                "error": "Fetch error",
                "source": "gmail",
            },
        )
        operations.update_workflow_run.assert_called_with(
            34,
            status="failed",
            documentsImported=0,
            documentsProcessed=0,
            documentsNeedingReview=0,
        )

    def test_checkpoint_persistence_failure_marks_run_failed(self):
        self._configure_successful_run()

        controller = WorkflowController(self.config)
        controller.checkpoint_store.save = MagicMock(return_value=False)
        controller.checkpoint_store.last_save_error = "disk unavailable"
        controller.run_workflow()

        operations = self.mocks["OperationsClient"].return_value
        operations.update_workflow_run.assert_called_with(
            34,
            status="failed",
            documentsImported=1,
            documentsProcessed=1,
            documentsNeedingReview=0,
        )
        operations.record_audit_event.assert_any_call(
            "workflow.error",
            "workflow_run",
            "34",
            {
                "operation": "checkpoint_save",
                "error": "disk unavailable",
                "checkpointPath": self.config["workflow_state_file"],
            },
        )

    def test_corrupt_checkpoint_blocks_fetching_and_marks_run_failed(self):
        self._configure_successful_run()
        with open(self.config["workflow_state_file"], "w", encoding="utf-8") as handle:
            handle.write('{"source_documents":')

        controller = WorkflowController(self.config)
        controller.run_workflow()

        self.mocks["GmailFetcher"].return_value.fetch_documents.assert_not_called()
        self.mocks["ProcessorPipeline"].return_value.process_document.assert_not_called()
        operations = self.mocks["OperationsClient"].return_value
        operations.update_workflow_run.assert_called_with(
            34,
            status="failed",
            documentsImported=0,
            documentsProcessed=0,
            documentsNeedingReview=0,
        )
        operations.record_audit_event.assert_any_call(
            "workflow.error",
            "workflow_run",
            "34",
            {
                "operation": "checkpoint_load",
                "error": ANY,
                "checkpointPath": self.config["workflow_state_file"],
            },
        )
        with open(self.config["workflow_state_file"], "r", encoding="utf-8") as handle:
            self.assertEqual(handle.read(), '{"source_documents":')

    def test_processing_failure_is_checkpointed_without_duplicate_review_items(self):
        self._configure_successful_run()
        self.mocks["ProcessorPipeline"].return_value.process_document.side_effect = RuntimeError("OCR unavailable")

        controller = WorkflowController(self.config)
        controller.run_workflow()
        controller.run_workflow()

        self.mocks["ProcessorPipeline"].return_value.process_document.assert_called_once()
        self.mocks["ManualReviewInterface"].return_value.add_to_review_queue.assert_called_once_with(
            "doc1",
            "processing_failed",
            "OCR unavailable",
        )
        self.mocks["OperationsClient"].return_value.create_review_item.assert_called_once_with(
            12,
            "processing_failed",
            "OCR unavailable",
        )
        with open(self.config["workflow_state_file"], "r", encoding="utf-8") as handle:
            workflow_state = json.load(handle)
        self.assertEqual(
            workflow_state["source_documents"]["gmail:doc1"]["status"],
            "needs_review_processing_failed",
        )

    def test_workflow_normalizes_alternate_source_identifiers(self):
        self._configure_successful_run()
        receipt_path = os.path.join(self.temp_dir.name, "legacy-receipt.pdf")
        self.mocks["GmailFetcher"].return_value.fetch_documents.return_value = [
            {
                "message_id": "message-42",
                "filename": "legacy-receipt.pdf",
                "local_path": receipt_path,
            }
        ]

        controller = WorkflowController(self.config)
        controller.run_workflow()

        registered_document = (
            self.mocks["OperationsClient"].return_value.register_document.call_args.args[1]
        )
        self.assertEqual(registered_document["id"], "message-42")
        self.assertEqual(registered_document["original_filename"], "legacy-receipt.pdf")
        self.mocks["ProcessorPipeline"].return_value.process_document.assert_called_once_with(receipt_path)
        routed_document = self.mocks["WaveappsBusinessHandler"].return_value.enter_data.call_args.args[0]
        self.assertEqual(routed_document["document_id"], "message-42")

    def test_missing_local_path_is_reviewed_without_aborting_workflow(self):
        self._configure_successful_run()
        self.mocks["GmailFetcher"].return_value.fetch_documents.return_value = [
            {"file_id": "drive-file-1", "filename": "missing.pdf"}
        ]

        controller = WorkflowController(self.config)
        controller.run_workflow()

        self.mocks["ProcessorPipeline"].return_value.process_document.assert_not_called()
        self.mocks["ManualReviewInterface"].return_value.add_to_review_queue.assert_called_once_with(
            "drive-file-1",
            "processing_failed",
            "Fetched document has no local file path.",
        )
        self.mocks["BackupManager"].return_value.perform_backup.assert_called_once()
        self.mocks["OperationsClient"].return_value.update_workflow_run.assert_called_with(
            34,
            status="completed_with_review",
            documentsImported=1,
            documentsProcessed=0,
            documentsNeedingReview=1,
        )

    def test_workflow_skips_previously_completed_source_documents(self):
        self._configure_successful_run()
        with open(self.config["workflow_state_file"], "w", encoding="utf-8") as handle:
            handle.write(
                '{"source_documents":{"gmail:doc1":{"source":"gmail","sourceDocumentId":"doc1","status":"processed"}},"known_documents":[]}'
            )

        controller = WorkflowController(self.config)
        controller.run_workflow()

        operations = self.mocks["OperationsClient"].return_value
        operations.register_document.assert_not_called()
        self.mocks["ProcessorPipeline"].return_value.process_document.assert_not_called()
        operations.update_workflow_run.assert_called_with(
            34,
            status="completed",
            documentsImported=0,
            documentsProcessed=0,
            documentsNeedingReview=0,
        )

    def test_workflow_skips_duplicate_documents_before_data_entry(self):
        receipt_path = os.path.join(self.temp_dir.name, "receipt.pdf")
        self.config["duplicate_similarity_threshold"] = 0.8
        self.config["known_documents"] = [
            {
                "id": 99,
                "extracted_data": {
                    "vendor_name": "Test Vendor",
                    "total_amount": 100.0,
                    "transaction_date": "2025-01-01",
                },
            }
        ]
        self._configure_successful_run()

        controller = WorkflowController(self.config)
        controller.run_workflow()

        self.mocks["ProcessorPipeline"].return_value.process_document.assert_called_once_with(receipt_path)
        self.mocks["HybridCategorizer"].return_value.categorize.assert_not_called()
        self.mocks["WaveappsBusinessHandler"].return_value.enter_data.assert_not_called()
        operations = self.mocks["OperationsClient"].return_value
        operations.create_routing_attempt.assert_called_with(
            12,
            "none",
            "skipped",
            workflow_run_id=34,
            message="Duplicate document detected: exact_fingerprint_match.",
            metadata=ANY,
        )
        operations.update_workflow_run.assert_called_with(
            34,
            status="completed",
            documentsImported=1,
            documentsProcessed=1,
            documentsNeedingReview=0,
        )

    def test_workflow_prefers_invoice_over_order_confirmation(self):
        invoice_path = os.path.join(self.temp_dir.name, "invoice.pdf")
        confirmation_path = os.path.join(self.temp_dir.name, "confirmation.pdf")
        self.mocks["GmailFetcher"].return_value.fetch_documents.return_value = [
            {"id": "doc-invoice", "original_filename": "invoice.pdf", "local_path": invoice_path},
            {"id": "doc-confirmation", "original_filename": "order-confirmation.pdf", "local_path": confirmation_path},
        ]
        self.mocks["DriveFetcher"].return_value.fetch_documents.return_value = []
        self.mocks["FreshdeskFetcher"].return_value.fetch_documents.return_value = []
        self.mocks["PhotosFetcher"].return_value.fetch_documents.return_value = []
        self.mocks["ProcessorPipeline"].return_value.process_document.side_effect = [
            {
                "ocr_text": "Invoice INV-123",
                "extracted_data": {
                    "vendor_name": "Test Vendor",
                    "invoice_number": "INV-123",
                    "total_amount": 100.0,
                    "transaction_date": "2025-01-01",
                },
            },
            {
                "ocr_text": "Order confirmation INV-123",
                "extracted_data": {
                    "vendor_name": "Test Vendor",
                    "order_number": "INV-123",
                    "total_amount": 100.0,
                    "transaction_date": "2025-01-01",
                },
            },
        ]
        self.mocks["HybridCategorizer"].return_value.categorize.return_value = {
            "category": "Business",
            "confidence_score": 0.9,
        }
        self.mocks["ValidationManager"].return_value.validate_receipt.return_value = {"is_valid": True}
        self.mocks["BudgetManager"].return_value.check_budget.return_value = {"is_within_budget": True}
        self.mocks["BankingAPI"].return_value.fetch_transactions.return_value = []
        self.mocks["AutomatedReconciliation"].return_value.reconcile.return_value = []
        self.mocks["BackupManager"].return_value.perform_backup.return_value = {"status": "success"}
        self.mocks["OperationsClient"].return_value.create_workflow_run.return_value = 34
        self.mocks["OperationsClient"].return_value.register_document.side_effect = [12, 13]
        self.mocks["WaveappsBusinessHandler"].return_value.enter_data.return_value = {
            "status": "success",
            "external_id": "expense-1",
        }

        controller = WorkflowController(self.config)
        controller.run_workflow()

        self.assertEqual(self.mocks["HybridCategorizer"].return_value.categorize.call_count, 1)
        self.mocks["WaveappsBusinessHandler"].return_value.enter_data.assert_called_once()
        operations = self.mocks["OperationsClient"].return_value
        operations.create_routing_attempt.assert_any_call(
            13,
            "none",
            "skipped",
            workflow_run_id=34,
            message="A higher-priority document exists for the same order.",
            metadata=ANY,
        )
        operations.update_workflow_run.assert_called_with(
            34,
            status="completed",
            documentsImported=2,
            documentsProcessed=2,
            documentsNeedingReview=0,
        )

    def test_workflow_records_matched_reconciliation(self):
        self._configure_successful_run()
        matched_document = {
            "document_id": "doc1",
            "_operations_document_id": 12,
            "extracted_data": {
                "vendor_name": "Test Vendor",
                "total_amount": 100.0,
                "transaction_date": "2025-01-01",
            },
        }
        self.mocks["AutomatedReconciliation"].return_value.reconcile.return_value = [
            {
                "type": "match",
                "bank_transaction": {"id": "tx-1", "date": "2025-01-01", "amount": 100.0},
                "document": matched_document,
                "matched": True,
            }
        ]

        controller = WorkflowController(self.config)
        controller.run_workflow()

        operations = self.mocks["OperationsClient"].return_value
        operations.create_reconciliation_match.assert_called_with(
            "tx-1",
            "matched",
            document_id=12,
            confidence_score=1.0,
            amount_difference=0.0,
            metadata=ANY,
        )
        operations.update_document.assert_any_call(
            12,
            matched_document,
            processing_status="reconciled",
            metadata={"reconciliation": {"bankTransactionId": "tx-1"}},
        )

    def test_workflow_flags_unmatched_bank_transaction_as_missing_receipt(self):
        self._configure_successful_run()
        self.mocks["AutomatedReconciliation"].return_value.reconcile.return_value = [
            {
                "type": "unmatched_bank_transaction",
                "bank_transaction": {"id": "tx-missing", "date": "2025-01-01", "amount": 100.0},
                "matched": False,
            }
        ]

        controller = WorkflowController(self.config)
        controller.run_workflow()

        operations = self.mocks["OperationsClient"].return_value
        operations.create_reconciliation_match.assert_called_with(
            "tx-missing",
            "unmatched",
            metadata=ANY,
        )
        operations.create_review_item.assert_called_with(
            None,
            "missing_receipt",
            "Possible missing receipt for unmatched bank transaction.",
        )
        operations.update_workflow_run.assert_called_with(
            34,
            status="completed_with_review",
            documentsImported=1,
            documentsProcessed=1,
            documentsNeedingReview=1,
        )


if __name__ == "__main__":
    unittest.main()
