import unittest
from unittest.mock import MagicMock, patch
import os
import shutil

from src.data_entry.mijngeldzaken_handler import MijngeldzakenHandler
from src.data_entry.waveapps_business_handler import WaveappsBusinessHandler
from src.data_entry.waveapps_personal_handler import WaveappsPersonalHandler

class TestDataEntry(unittest.TestCase):

    def setUp(self):
        self.config = {
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
            "waveapps_handicap_tag": "#handicap"
        }
        self.dummy_doc_id = "doc123"
        self.dummy_processed_data = {
            "document_id": self.dummy_doc_id,
            "ocr_text": "Test receipt for groceries",
            "extracted_data": {
                "vendor_name": "Local Supermarket",
                "transaction_date": "2025-01-15",
                "total_amount": 45.50,
                "currency": "EUR",
                "description": "Weekly groceries"
            },
            "language": "en",
            "category": "Personal",
            "confidence_score": 0.95
        }

    @patch("src.data_entry.mijngeldzaken_handler.sync_playwright")
    def test_mijngeldzaken_handler(self, mock_sync_playwright):
        mock_playwright = MagicMock()
        mock_sync_playwright.return_value.__enter__.return_value = mock_playwright
        mock_browser = MagicMock()
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_page = MagicMock()
        mock_browser.new_page.return_value = mock_page

        # Mock page interactions
        mock_page.wait_for_url.return_value = None
        mock_page.wait_for_selector.return_value = None
        mock_page.inner_text.return_value = "Upload successful!"

        handler = MijngeldzakenHandler(self.config)
        result = handler.enter_data(self.dummy_processed_data)

        self.assertEqual(result["status"], "success")
        self.assertIn("Successfully uploaded", result["message"])
        mock_page.fill.assert_any_call("input[name=\"username\"]", "test_user")
        mock_page.fill.assert_any_call("input[name=\"password\"]", "test_pass")
        mock_page.set_input_files.assert_called_once()

        # Test with missing credentials
        self.config["mijngeldzaken_username"] = None
        handler = MijngeldzakenHandler(self.config)
        result = handler.enter_data(self.dummy_processed_data)
        self.assertEqual(result["status"], "failure")
        self.assertIn("credentials not configured", result["message"])
        self.assertTrue(result["requires_manual_review"])

    @patch("src.data_entry.waveapps_business_handler.requests.post")
    def test_waveapps_business_handler(self, mock_post):
        # Test successful API call
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "data": {
                "expenseCreate": {
                    "didSucceed": True,
                    "expense": {"id": "new_expense_id"}
                }
            }
        }
        mock_post.return_value = mock_response

        handler = WaveappsBusinessHandler(self.config)
        business_data = self.dummy_processed_data.copy()
        business_data["category"] = "Business"
        result = handler.enter_data(business_data)

        self.assertEqual(result["status"], "success")
        self.assertIn("Expense created", result["message"])
        self.assertEqual(result["external_id"], "new_expense_id")

        # Test API failure
        mock_response.json.return_value = {
            "data": {
                "expenseCreate": {
                    "didSucceed": False,
                    "errors": [{"message": "API Error", "code": "123"}]
                }
            }
        }
        result = handler.enter_data(business_data)
        self.assertEqual(result["status"], "failure")
        self.assertIn("API Error", result["message"])
        self.assertTrue(result["requires_manual_review"])

        # Test CSV fallback
        self.config["waveapps_business_access_token"] = None
        handler = WaveappsBusinessHandler(self.config)
        result = handler.enter_data(business_data)
        self.assertEqual(result["status"], "csv_generated")
        self.assertIn("CSV generated", result["message"])
        self.assertTrue(result["requires_manual_review"])
        # Clean up generated CSV
        os.remove(result["message"].split(": ")[1])

    @patch("src.data_entry.waveapps_personal_handler.requests.post")
    def test_waveapps_personal_handler(self, mock_post):
        # Test successful API call with handicap tag
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "data": {
                "expenseCreate": {
                    "didSucceed": True,
                    "expense": {"id": "new_personal_expense_id"}
                }
            }
        }
        mock_post.return_value = mock_response

        handler = WaveappsPersonalHandler(self.config)
        personal_data = self.dummy_processed_data.copy()
        personal_data["category"] = "Handicaps"
        result = handler.enter_data(personal_data)

        self.assertEqual(result["status"], "success")
        self.assertIn("Expense created", result["message"])
        self.assertEqual(result["external_id"], "new_personal_expense_id")
        # Verify handicap tag was added to description in the API call
        self.assertIn("#handicap", mock_post.call_args[1]["json"]["query"])

        # Test CSV fallback
        self.config["waveapps_personal_access_token"] = None
        handler = WaveappsPersonalHandler(self.config)
        result = handler.enter_data(personal_data)
        self.assertEqual(result["status"], "csv_generated")
        self.assertIn("CSV generated", result["message"])
        self.assertTrue(result["requires_manual_review"])
        # Clean up generated CSV
        os.remove(result["message"].split(": ")[1])

if __name__ == "__main__":
    unittest.main()


