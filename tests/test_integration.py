import unittest
from unittest.mock import MagicMock, patch
import os
import shutil

from src.workflow.controller import WorkflowController
from src.config_loader import ConfigLoader

class TestIntegration(unittest.TestCase):

    def setUp(self):
        self.base_dir = "/tmp/integration_test"
        os.makedirs(self.base_dir, exist_ok=True)
        self.config_file = os.path.join(self.base_dir, "config.ini")
        self.log_file = os.path.join(self.base_dir, "app.log")
        self.manual_review_queue_file = os.path.join(self.base_dir, "manual_review_queue.json")

        # Create a dummy config.ini for integration tests
        with open(self.config_file, "w") as f:
            f.write("""
[app]
log_file = {}

[gmail]
credentials_file = /tmp/gmail_credentials.json
token_file = /tmp/gmail_token.json
attachment_download_dir = /tmp/gmail_downloads

[google_drive]
credentials_file = /tmp/drive_credentials.json
token_file = /tmp/drive_token.json
download_dir = /tmp/drive_downloads

[freshdesk]
api_key = dummy_key
domain = dummy_domain
download_dir = /tmp/freshdesk_downloads

[google_photos]
credentials_file = /tmp/photos_credentials.json
token_file = /tmp/photos_token.json
album_name = Test Album
download_dir = /tmp/photos_downloads

[processor]
ocr_processor = tesseract

[categorizer]
ml_model_path = /tmp/ml_categorizer_model.joblib
ml_vectorizer_path = /tmp/tfidf_vectorizer.joblib
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
budget_file = /tmp/budgets.json

[banking]
banking_api_endpoint = http://banking.api/
banking_api_credentials = {"client_id": "test", "client_secret": "test"}

[reconciliation]
reconciliation_threshold = 0.05

[manual_review]
manual_review_queue_file = {}

[backup]
backup_base_dir = /tmp/backups
backup_paths = []
backup_config = {\"type\": \"zip\"}

[error_handling]
error_recovery_max_retries = 1
error_recovery_retry_delay_seconds = 0
email_notifications_enabled = False
            """.format(self.log_file, self.manual_review_queue_file))

        # Create dummy credential files for fetchers
        for f in ["/tmp/gmail_credentials.json", "/tmp/gmail_token.json",
                  "/tmp/drive_credentials.json", "/tmp/drive_token.json",
                  "/tmp/photos_credentials.json", "/tmp/photos_token.json"]:
            with open(f, "w") as f_obj:
                f_obj.write("{}")
        
        # Create dummy download directories
        for d in ["/tmp/gmail_downloads", "/tmp/drive_downloads",
                  "/tmp/freshdesk_downloads", "/tmp/photos_downloads"]:
            os.makedirs(d, exist_ok=True)

        # Create a dummy image file for processing
        from PIL import Image
        self.dummy_image_path = os.path.join(self.base_dir, "dummy_receipt.png")
        img = Image.new("RGB", (100, 50), color = (255, 255, 255))
        img.save(self.dummy_image_path)

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
                                       mock_fetch_documents):
        # Mock return values for each stage
        mock_fetch_documents.return_value = [
            {"id": "doc1", "original_filename": "receipt.png", "local_path": self.dummy_image_path}
        ]
        mock_process_document.return_value = {
            "ocr_text": "Test OCR text for Business",
            "extracted_data": {"vendor_name": "Test Vendor", "total_amount": 100.0, "transaction_date": "2025-01-01"}
        }
        mock_categorize.return_value = {"category": "Business", "confidence_score": 0.95}
        mock_validate_receipt.return_value = {"is_valid": True, "errors": []}
        mock_enter_data.return_value = {"status": "success", "message": "Data entered successfully"}
        mock_perform_backup.return_value = {"status": "success"}

        # Initialize ConfigLoader with the dummy config file
        config_loader = ConfigLoader(config_file=self.config_file)
        config = config_loader.get_all_config()

        # Initialize and run the WorkflowController
        controller = WorkflowController(config)
        controller.run_workflow()

        # Assert that each stage was called with appropriate arguments
        mock_fetch_documents.assert_called_once()
        mock_process_document.assert_called_once_with(self.dummy_image_path)
        mock_categorize.assert_called_once_with(mock_process_document.return_value)
        mock_validate_receipt.assert_called_once_with(mock_process_document.return_value)
        mock_enter_data.assert_called_once_with({
            'ocr_text': 'Test OCR text for Business',
            'extracted_data': {'vendor_name': 'Test Vendor', 'total_amount': 100.0, 'transaction_date': '2025-01-01'},
            'category': 'Business',
            'confidence_score': 0.95,
            'id': 'doc1',
            'original_filename': 'receipt.png',
            'local_path': self.dummy_image_path
        })
        mock_perform_backup.assert_called_once()

    def tearDown(self):
        # Clean up all dummy files and directories created during tests
        if os.path.exists(self.base_dir):
            shutil.rmtree(self.base_dir)
        
        for f in ["/tmp/gmail_credentials.json", "/tmp/gmail_token.json",
                  "/tmp/drive_credentials.json", "/tmp/drive_token.json",
                  "/tmp/photos_credentials.json", "/tmp/photos_token.json"]:
            if os.path.exists(f):
                os.remove(f)
        
        for d in ["/tmp/gmail_downloads", "/tmp/drive_downloads",
                  "/tmp/freshdesk_downloads", "/tmp/photos_downloads"]:
            if os.path.exists(d):
                shutil.rmtree(d)

        # Clean up any files created by the workflow itself (e.g., manual review queue)
        if os.path.exists(self.manual_review_queue_file):
            os.remove(self.manual_review_queue_file)
        if os.path.exists(self.log_file):
            os.remove(self.log_file)

if __name__ == "__main__":
    unittest.main()


