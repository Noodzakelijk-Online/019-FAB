import unittest
from unittest.mock import patch

from src.document_processors.processor_pipeline import ProcessorPipeline
from src.document_processors.tesseract_processor import TesseractProcessor


class TestProcessorPipeline(unittest.TestCase):
    def test_financial_field_extractor_enriches_ocr_result(self):
        config = {
            "enable_enhanced_preprocessing": False,
            "primary_ocr_method": "tesseract",
            "enable_template_matching": False,
            "enable_line_item_extraction": False,
        }
        ocr_result = {
            "ocr_text": (
                "Receipt from getimg.ai\n$9.00\nDate paid Aug 7, 2023\n"
                "Amount charged $9.00"
            ),
            "extracted_data": {
                "vendor_name": "Receipt from getimg.ai",
                "transaction_date": None,
                "total_amount": None,
                "currency": None,
            },
            "language": "eng",
        }

        with patch.object(TesseractProcessor, "process_document", return_value=ocr_result):
            result = ProcessorPipeline(config).process_document("unused.pdf")

        self.assertEqual(result["extracted_data"]["vendor_name"], "getimg.ai")
        self.assertEqual(result["extracted_data"]["transaction_date"], "2023-08-07")
        self.assertEqual(result["extracted_data"]["total_amount"], 9.0)
        self.assertEqual(result["extracted_data"]["currency"], "USD")


if __name__ == "__main__":
    unittest.main()
