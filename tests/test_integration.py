import unittest
from unittest.mock import MagicMock, patch
import os
import shutil
import tempfile

from src.workflow.controller import WorkflowController
from src.config_loader import ConfigLoader

class TestIntegration(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.base_dir = self.temp_dir.name
        self.config_file = os.path.join(self.base_dir, "config.ini")
        self.log_file = os.path.join(self.base_dir, "app.log")
        self.manual_review_queue_file = os.path.join(self.base_dir, "manual_review_queue.json")
        self.gmail_credentials_file = os.path.join(self.base_dir, "gmail_credentials.json")
        self.gmail_token_file = os.path.join(self.base_dir, "gmail_token.json")
        self.gmail_download_dir = os.path.join(self.base_dir, "gmail_downloads")
        self.drive_credentials_file = os.path.join(self.base_dir, "drive_credentials.json")
        self.drive_token_file = os.path.join(self.base_dir, "drive_token.json")
        self.drive_download_dir = os.path.join(self.base_dir, "drive_downloads")
        self.freshdesk_download_dir = os.path.join(self.base_dir, "freshdesk_downloads")
        self.photos_credentials_file = os.path.join(self.base_dir, "photos_credentials.json")
        self.photos_token_file = os.path.join(self.base_dir, "photos_token.json")
        self.photos_download_dir = os.path.join(self.base_dir, "photos_downloads")
        self.budget_file = os.path.join(self.base_dir, "budgets.json")
        self.backup_base_dir = os.path.join(self.base_dir, "backups")
        self.workflow_state_file = os.path.join(self.base_dir, "workflow_state.json")

        # Create a dummy config.ini for integration tests
        with open(self.config_file, "w") as f:
            config_template = """
[app]
log_file = __LOG_FILE__

[gmail]
credentials_file = __GMAIL_CREDENTIALS_FILE__
token_file = __GMAIL_TOKEN_FILE__
attachment_download_dir = __GMAIL_DOWNLOAD_DIR__

[google_drive]
credentials_file = __DRIVE_CREDENTIALS_FILE__
token_file = __DRIVE_TOKEN_FILE__
download_dir = __DRIVE_DOWNLOAD_DIR__

[freshdesk]
api_key = dummy_key
domain = dummy_domain
download_dir = __FRESHDESK_DOWNLOAD_DIR__

[google_photos]
credentials_file = __PHOTOS_CREDENTIALS_FILE__
token_file = __PHOTOS_TOKEN_FILE__
album_name = Test Album
download_dir = __PHOTOS_DOWNLOAD_DIR__

[processor]
ocr_processor = tesseract

[categorizer]
ml_model_path = __ML_MODEL_PATH__
ml_vectorizer_path = __ML_VECTORIZER_PATH__
categorization_rules = {"Personal": {"keywords": ["supermarket"], "vendors": []}}
default_fallback_category = Manual Review
ml_confidence_threshold = 0.7

[mijngeldzaken]
username = test_user
password = test_pass
login_url = http://mijngeldzaken.test/login
import_url = http://mijngeldzaken.test/import
csv_template = {"columns": ["Date", "Description", "Amount", "Category"], "mapping": {"Date": "extracted_data.transaction_date"}, "delimiter": ";"}
category_mapping = {"Personal": "Huishouden"}

[waveapps_business]
access_token = business_token
business_id = business_id
category_mapping = {"Business": "Office Supplies"}

[waveapps_personal]
access_token = personal_token
personal_id = personal_id
category_mapping = {"Handicaps": "Medical Expenses"}
handicap_tag = #handicap

[validation]
receipt_validation_required_fields = vendor_name,total_amount
btw_number_pattern = NL\\d{9}B\\d{2}

[budget]
budget_file = __BUDGET_FILE__

[banking]
banking_api_endpoint = http://banking.api/
banking_api_credentials = {"client_id": "test", "client_secret": "test"}

[reconciliation]
reconciliation_threshold = 0.05

[manual_review]
manual_review_queue_file = __MANUAL_REVIEW_QUEUE_FILE__

[backup]
backup_base_dir = __BACKUP_BASE_DIR__
backup_paths = []
backup_config = {\"type\": \"zip\"}

[workflow]
workflow_state_file = __WORKFLOW_STATE_FILE__

[error_handling]
error_recovery_max_retries = 1
error_recovery_retry_delay_seconds = 0
email_notifications_enabled = False
            """
            replacements = {
                "__LOG_FILE__": self.log_file,
                "__GMAIL_CREDENTIALS_FILE__": self.gmail_credentials_file,
                "__GMAIL_TOKEN_FILE__": self.gmail_token_file,
                "__GMAIL_DOWNLOAD_DIR__": self.gmail_download_dir,
                "__DRIVE_CREDENTIALS_FILE__": self.drive_credentials_file,
                "__DRIVE_TOKEN_FILE__": self.drive_token_file,
                "__DRIVE_DOWNLOAD_DIR__": self.drive_download_dir,
                "__FRESHDESK_DOWNLOAD_DIR__": self.freshdesk_download_dir,
                "__PHOTOS_CREDENTIALS_FILE__": self.photos_credentials_file,
                "__PHOTOS_TOKEN_FILE__": self.photos_token_file,
                "__PHOTOS_DOWNLOAD_DIR__": self.photos_download_dir,
                "__ML_MODEL_PATH__": os.path.join(self.base_dir, "ml_categorizer_model.joblib"),
                "__ML_VECTORIZER_PATH__": os.path.join(self.base_dir, "tfidf_vectorizer.joblib"),
                "__BUDGET_FILE__": self.budget_file,
                "__MANUAL_REVIEW_QUEUE_FILE__": self.manual_review_queue_file,
                "__BACKUP_BASE_DIR__": self.backup_base_dir,
                "__WORKFLOW_STATE_FILE__": self.workflow_state_file,
            }
            for key, value in replacements.items():
                config_template = config_template.replace(key, value)
            f.write(config_template)

        # Create dummy credential files for fetchers
        for f in [self.gmail_credentials_file, self.gmail_token_file,
                  self.drive_credentials_file, self.drive_token_file,
                  self.photos_credentials_file, self.photos_token_file]:
            with open(f, "w") as f_obj:
                f_obj.write("{}")
        
        # Create dummy download directories
        for d in [self.gmail_download_dir, self.drive_download_dir,
                  self.freshdesk_download_dir, self.photos_download_dir]:
            os.makedirs(d, exist_ok=True)

        # Create a dummy image file for processing
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow is required for integration image fixture")
        self.dummy_image_path = os.path.join(self.base_dir, "dummy_receipt.png")
        img = Image.new("RGB", (100, 50), color = (255, 255, 255))
        img.save(self.dummy_image_path)

    @patch("src.reconciliation.automated_reconciliation.AutomatedReconciliation.reconcile")
    @patch("src.banking.banking_api.BankingAPI.fetch_transactions")
    @patch("src.document_fetchers.photos_fetcher.PhotosFetcher.fetch_documents")
    @patch("src.document_fetchers.freshdesk_fetcher.FreshdeskFetcher.fetch_documents")
    @patch("src.document_fetchers.drive_fetcher.DriveFetcher.fetch_documents")
    @patch("src.document_fetchers.gmail_fetcher.GmailFetcher.fetch_documents")
    @patch("src.document_processors.tesseract_processor.TesseractProcessor.process_document")
    @patch("src.categorizers.hybrid_categorizer.HybridCategorizer.categorize")
    @patch("src.data_entry.waveapps_business_handler.WaveappsBusinessHandler.enter_data")
    @patch("src.validation.validation_manager.ValidationManager.validate_receipt")
    @patch("src.backup.backup_manager.BackupManager.perform_backup")
    def test_full_workflow_integration(self,
                                       mock_perform_backup,
                                       mock_validate_receipt,
                                       mock_enter_data,
                                       mock_categorize,
                                       mock_process_document,
                                       mock_fetch_documents,
                                       mock_drive_fetch_documents,
                                       mock_freshdesk_fetch_documents,
                                       mock_photos_fetch_documents,
                                       mock_fetch_transactions,
                                       mock_reconcile):
        # Mock return values for each stage
        mock_fetch_documents.return_value = [
            {"id": "doc1", "original_filename": "receipt.png", "local_path": self.dummy_image_path}
        ]
        mock_drive_fetch_documents.return_value = []
        mock_freshdesk_fetch_documents.return_value = []
        mock_photos_fetch_documents.return_value = []
        mock_process_document.return_value = {
            "ocr_text": "Test OCR text for Business",
            "extracted_data": {"vendor_name": "Test Vendor", "total_amount": 100.0, "transaction_date": "2025-01-01"}
        }
        mock_categorize.return_value = {"category": "Business", "confidence_score": 0.95}
        mock_validate_receipt.return_value = {"is_valid": True, "errors": []}
        mock_enter_data.return_value = {"status": "success", "message": "Data entered successfully"}
        mock_perform_backup.return_value = {"status": "success"}
        mock_fetch_transactions.return_value = []
        mock_reconcile.return_value = []

        # Initialize ConfigLoader with the dummy config file
        config_loader = ConfigLoader(config_file=self.config_file)
        config = config_loader.get_all_config()

        # Initialize and run the WorkflowController
        controller = WorkflowController(config)
        controller.run_workflow()

        # Assert that each stage was called with appropriate arguments
        mock_fetch_documents.assert_called_once()
        mock_process_document.assert_called_once_with(self.dummy_image_path)
        mock_categorize.assert_called_once()
        mock_validate_receipt.assert_called_once()
        mock_enter_data.assert_called_once()
        entered_document = mock_enter_data.call_args.args[0]
        self.assertEqual(entered_document["ocr_text"], "Test OCR text for Business")
        self.assertEqual(entered_document["category"], "Business")
        self.assertEqual(entered_document["document_id"], "doc1")
        self.assertEqual(entered_document["_source_document"]["local_path"], self.dummy_image_path)
        mock_perform_backup.assert_called_once()

    def tearDown(self):
        pass

if __name__ == "__main__":
    unittest.main()


