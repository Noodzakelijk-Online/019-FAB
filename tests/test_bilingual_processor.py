import os
import tempfile
import unittest
from unittest.mock import patch

import src.document_processors.bilingual_processor as bilingual_module
from src.document_processors.bilingual_processor import BilingualProcessor


class TestBilingualProcessor(unittest.TestCase):
    def setUp(self):
        if bilingual_module.langdetect is None:
            self.skipTest("langdetect is required for language-specific routing tests")

        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.config = {"tesseract_cmd": "tesseract", "tesseract_lang": "nld+eng"}
        self.document_path = os.path.join(self.temp_dir.name, "receipt.png")

    @patch("src.document_processors.bilingual_processor.langdetect.detect", return_value="nl")
    @patch("src.document_processors.bilingual_processor.TesseractProcessor")
    def test_dutch_result_is_enriched(self, MockTesseractProcessor, _mock_detect):
        MockTesseractProcessor.return_value.process_document.return_value = {
            "ocr_text": "Winkel\nTotaal EUR 12,10",
            "extracted_data": {},
        }

        result = BilingualProcessor(self.config).process_document(self.document_path)

        self.assertEqual(result["language"], "nl")
        self.assertEqual(result["extracted_data"]["total_amount"], 12.1)

    @patch("src.document_processors.bilingual_processor.langdetect.detect", return_value="en")
    @patch("src.document_processors.bilingual_processor.TesseractProcessor")
    def test_english_result_preserves_local_ocr(self, MockTesseractProcessor, _mock_detect):
        MockTesseractProcessor.return_value.process_document.return_value = {
            "ocr_text": "Shop\nTotal EUR 12.10",
            "extracted_data": {"total_amount": 12.1},
        }

        result = BilingualProcessor(self.config).process_document(self.document_path)

        self.assertEqual(result["language"], "en")
        self.assertEqual(result["extracted_data"]["total_amount"], 12.1)

    @patch("src.document_processors.bilingual_processor.langdetect.detect", side_effect=Exception("short text"))
    @patch("src.document_processors.bilingual_processor.TesseractProcessor")
    def test_language_detection_falls_back_to_english(self, MockTesseractProcessor, _mock_detect):
        MockTesseractProcessor.return_value.process_document.return_value = {
            "ocr_text": "X",
            "extracted_data": {},
        }

        result = BilingualProcessor(self.config).process_document(self.document_path)

        self.assertEqual(result["language"], "en")


if __name__ == "__main__":
    unittest.main()
