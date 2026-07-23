import unittest
from unittest.mock import MagicMock, patch

from src.validation.receipt_validator import ReceiptValidator

class TestReceiptValidator(unittest.TestCase):

    def setUp(self):
        self.config = {
            "receipt_validation_required_fields": ["vendor_name", "total_amount", "transaction_date"],
            "btw_number_pattern": r"NL\d{9}B\d{2}"
        }
        self.validator = ReceiptValidator(self.config)

    def test_validate_receipt_success(self):
        processed_data = {
            "extracted_data": {
                "vendor_name": "Example Shop",
                "total_amount": 100.00,
                "transaction_date": "2025-01-01",
                "btw_number": "NL123456789B01"
            },
            "ocr_text": "Some text with NL123456789B01"
        }
        result = self.validator.validate_receipt(processed_data)
        self.assertTrue(result["is_valid"])
        self.assertEqual(len(result["errors"]), 0)

    def test_validate_receipt_missing_required_field(self):
        processed_data = {
            "extracted_data": {
                "vendor_name": "Example Shop",
                "transaction_date": "2025-01-01"
            },
            "ocr_text": "Some text"
        }
        result = self.validator.validate_receipt(processed_data)
        self.assertFalse(result["is_valid"])
        self.assertIn("Missing required field: total_amount", result["errors"])

    def test_validate_receipt_invalid_btw_number(self):
        processed_data = {
            "extracted_data": {
                "vendor_name": "Example Shop",
                "total_amount": 100.00,
                "transaction_date": "2025-01-01",
                "btw_number": "INVALID_BTW"
            },
            "ocr_text": "Some text with INVALID_BTW"
        }
        result = self.validator.validate_receipt(processed_data)
        self.assertFalse(result["is_valid"])
        self.assertIn("Invalid BTW number format", result["errors"])

    def test_validate_receipt_no_btw_number_in_text(self):
        processed_data = {
            "extracted_data": {
                "vendor_name": "Example Shop",
                "total_amount": 100.00,
                "transaction_date": "2025-01-01",
                "btw_number": "NL123456789B01"
            },
            "ocr_text": "Some text without BTW number"
        }
        result = self.validator.validate_receipt(processed_data)
        self.assertFalse(result["is_valid"])
        self.assertIn("Extracted BTW number not found in OCR text", result["errors"])

    def test_validate_receipt_rejects_impossible_vat_amount(self):
        processed_data = {
            "extracted_data": {
                "vendor_name": "Example Shop",
                "total_amount": 59.60,
                "vat_amount": 8075.08,
                "transaction_date": "2025-01-01",
            },
            "ocr_text": "BTW-nummer: NL8075.08.093.B.01",
        }

        result = self.validator.validate_receipt(processed_data)

        self.assertFalse(result["is_valid"])
        self.assertIn(
            "VAT amount exceeds the configured 25.0% of total safety limit.",
            result["errors"],
        )
        self.assertEqual(
            result["fieldControls"]["vat"]["reason"],
            "vat_exceeds_total_ratio",
        )

    def test_validate_receipt_all_failures(self):
        processed_data = {
            "extracted_data": {
                "vendor_name": "", # Empty required field
                "total_amount": None, # Missing required field
                "transaction_date": "invalid-date", # Invalid format
                "btw_number": "NL123"
            },
            "ocr_text": "No relevant text"
        }
        result = self.validator.validate_receipt(processed_data)
        self.assertFalse(result["is_valid"])
        self.assertIn("Missing required field: total_amount", result["errors"])
        self.assertIn("Invalid or empty vendor_name", result["errors"])
        self.assertIn("Invalid transaction_date format", result["errors"])
        self.assertIn("Invalid BTW number format", result["errors"])
        self.assertIn("Extracted BTW number not found in OCR text", result["errors"])

if __name__ == "__main__":
    unittest.main()


