import unittest
from unittest.mock import MagicMock, patch

from src.workflow.controller import WorkflowController
from src.workflow.logger import AppLogger

class TestWorkflow(unittest.TestCase):

    def setUp(self):
        self.config = {
            "log_file": "/tmp/test_workflow.log",
            "manual_review_queue_file": "/tmp/manual_review_queue.json",
            "error_recovery_max_retries": 1,
            "error_recovery_retry_delay_seconds": 0,
            "email_notifications_enabled": False,
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
                    "Category": "category"
                },
                "delimiter": ";"
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
                "Handicaps": {"keywords": ["therapy"], "vendors": []}
            },
            "default_fallback_category": "Manual Review",
            "ml_confidence_threshold": 0.7,
            "receipt_validation_required_fields": ["vendor_name", "total_amount"],
            "btw_number_pattern": r"NL\d{9}B\d{2}",
            "budget_file": "/tmp/budgets.json",
            "banking_api_endpoint": "http://banking.api/",
            "banking_api_credentials": {"client_id": "test", "client_secret": "test"},
            "backup_base_dir": "/tmp/backups",
            "backup_paths": [],
            "backup_config": {"type": "zip"}
        }

    @patch("src.document_fetchers.gmail_fetcher.GmailFetcher")
    @patch("src.document_fetchers.drive_fetcher.DriveFetcher")
    @patch("src.document_fetchers.freshdesk_fetcher.FreshdeskFetcher")
    @patch("src.document_fetchers.photos_fetcher.PhotosFetcher")
    @patch("src.document_processors.processor_pipeline.ProcessorPipeline")
    @patch("src.categorizers.hybrid_categorizer.HybridCategorizer")
    @patch("src.data_entry.mijngeldzaken_handler.MijngeldzakenHandler")
    @patch("src.data_entry.waveapps_business_handler.WaveappsBusinessHandler")
    @patch("src.data_entry.waveapps_personal_handler.WaveappsPersonalHandler")
    @patch("src.learning.learning_manager.LearningManager")
    @patch("src.error_handling.enhanced_error_recovery.EnhancedErrorRecovery")
    @patch("src.validation.validation_manager.ValidationManager")
    @patch("src.budget.budget_manager.BudgetManager")
    @patch("src.banking.banking_api.BankingAPI")
    @patch("src.reconciliation.automated_reconciliation.AutomatedReconciliation")
    @patch("src.manual_review.manual_review_interface.ManualReviewInterface")
    @patch("src.backup.backup_manager.BackupManager")
    @patch("src.security.security_manager.SecurityManager")
    @patch("src.performance.performance_optimizer.PerformanceOptimizer")
    def test_workflow_controller_full_run(self, MockPerformanceOptimizer, MockSecurityManager, MockBackupManager, MockManualReviewInterface, MockAutomatedReconciliation, MockBankingAPI, MockBudgetManager, MockValidationManager, MockEnhancedErrorRecovery, MockLearningManager, MockWaveappsPersonalHandler, MockWaveappsBusinessHandler, MockMijngeldzakenHandler, MockHybridCategorizer, MockProcessorPipeline, MockPhotosFetcher, MockFreshdeskFetcher, MockDriveFetcher, MockGmailFetcher):
        # Mock fetchers to return some dummy documents
        mock_gmail_fetcher_instance = MockGmailFetcher.return_value
        mock_gmail_fetcher_instance.fetch_documents.return_value = [
            {"id": "doc1", "original_filename": "receipt.pdf", "local_path": "/tmp/receipt.pdf"}
        ]
        mock_drive_fetcher_instance = MockDriveFetcher.return_value
        mock_drive_fetcher_instance.fetch_documents.return_value = []
        mock_freshdesk_fetcher_instance = MockFreshdeskFetcher.return_value
        mock_freshdesk_fetcher_instance.fetch_documents.return_value = []
        mock_photos_fetcher_instance = MockPhotosFetcher.return_value
        mock_photos_fetcher_instance.fetch_documents.return_value = []

        # Mock processor pipeline
        mock_processor_pipeline_instance = MockProcessorPipeline.return_value
        mock_processor_pipeline_instance.process_document.return_value = {
            "ocr_text": "dummy ocr text",
            "extracted_data": {"vendor_name": "Test Vendor", "total_amount": 100.0, "transaction_date": "2025-01-01"}
        }

        # Mock categorizer
        mock_hybrid_categorizer_instance = MockHybridCategorizer.return_value
        mock_hybrid_categorizer_instance.categorize.return_value = {"category": "Business", "confidence_score": 0.9}

        # Mock data entry handlers
        mock_mijngeldzaken_handler_instance = MockMijngeldzakenHandler.return_value
        mock_mijngeldzaken_handler_instance.enter_data.return_value = {"status": "success"}
        mock_waveapps_business_handler_instance = MockWaveappsBusinessHandler.return_value
        mock_waveapps_business_handler_instance.enter_data.return_value = {"status": "success"}
        mock_waveapps_personal_handler_instance = MockWaveappsPersonalHandler.return_value
        mock_waveapps_personal_handler_instance.enter_data.return_value = {"status": "success"}

        # Mock other components
        MockValidationManager.return_value.validate_receipt.return_value = {"is_valid": True}
        MockBudgetManager.return_value.check_budget.return_value = {"is_within_budget": True}
        MockBankingAPI.return_value.fetch_transactions.return_value = []
        MockAutomatedReconciliation.return_value.reconcile.return_value = []
        MockBackupManager.return_value.perform_backup.return_value = {"status": "success"}

        controller = WorkflowController(self.config)
        controller.run_workflow()

        # Assertions to check if key methods were called
        mock_gmail_fetcher_instance.fetch_documents.assert_called_once()
        mock_processor_pipeline_instance.process_document.assert_called_once()
        mock_hybrid_categorizer_instance.categorize.assert_called_once()
        mock_waveapps_business_handler_instance.enter_data.assert_called_once()
        MockBackupManager.return_value.perform_backup.assert_called_once()

        # Test error handling during fetching
        mock_gmail_fetcher_instance.fetch_documents.side_effect = Exception("Fetch error")
        controller = WorkflowController(self.config)
        controller.run_workflow()
        MockEnhancedErrorRecovery.return_value.handle_error.assert_called_with(unittest.mock.ANY, "fetch_gmail")

if __name__ == "__main__":
    unittest.main()


