import unittest
from unittest.mock import MagicMock, patch
import os
import tempfile

import src.document_processors.bilingual_processor as bilingual_module
from src.document_processors.bilingual_processor import BilingualProcessor

class TestBilingualProcessor(unittest.TestCase):

    def setUp(self):
        if bilingual_module.langdetect is None:
            self.skipTest("langdetect is required for language-specific routing tests")

        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.config = {
            "tesseract_cmd": "tesseract",
            "dutch_ocr_lang": "nld",
            "google_vision_credentials_file": os.path.join(self.temp_dir.name, "vision_credentials.json")
        }
        # Create dummy credential file for VisionProcessor
        with open(self.config["google_vision_credentials_file"], "w") as f:
            f.write("{}")

        # Create a dummy image file for testing
        self.dummy_image_path = os.path.join(self.temp_dir.name, "dummy_bilingual_receipt.png")
        with open(self.dummy_image_path, "wb") as f:
            f.write(b"dummy image")

    @patch("src.document_processors.bilingual_processor.pytesseract.image_to_string")
    @patch("src.document_processors.bilingual_processor.langdetect.detect")
    @patch("src.document_processors.bilingual_processor.DutchOcrProcessor")
    @patch("src.document_processors.bilingual_processor.VisionProcessor")
    def test_bilingual_processor_dutch(self, MockVisionProcessor, MockDutchOcrProcessor, mock_langdetect, mock_image_to_string):
        # Mock Tesseract for initial language detection
        mock_image_to_string.return_value = "Dit is een Nederlandse tekst."
        # Mock langdetect to return Dutch
        mock_langdetect.detect.return_value = "nl"

        # Mock DutchOcrProcessor
        mock_dutch_processor_instance = MagicMock()
        mock_dutch_processor_instance.process_document.return_value = {"ocr_text": "Processed Dutch Text", "language": "nl"}
        MockDutchOcrProcessor.return_value = mock_dutch_processor_instance

        processor = BilingualProcessor(self.config)
        result = processor.process_document(self.dummy_image_path)

        self.assertEqual(result["ocr_text"], "Processed Dutch Text")
        self.assertEqual(result["language"], "nl")
        MockDutchOcrProcessor.assert_called_once_with(self.config)
        mock_dutch_processor_instance.process_document.assert_called_once_with(self.dummy_image_path)
        MockVisionProcessor.assert_not_called()

    @patch("src.document_processors.bilingual_processor.pytesseract.image_to_string")
    @patch("src.document_processors.bilingual_processor.langdetect.detect")
    @patch("src.document_processors.bilingual_processor.DutchOcrProcessor")
    @patch("src.document_processors.bilingual_processor.VisionProcessor")
    def test_bilingual_processor_english(self, MockVisionProcessor, MockDutchOcrProcessor, mock_langdetect, mock_image_to_string):
        # Mock Tesseract for initial language detection
        mock_image_to_string.return_value = "This is an English text."
        # Mock langdetect to return English
        mock_langdetect.detect.return_value = "en"

        # Mock VisionProcessor
        mock_vision_processor_instance = MagicMock()
        mock_vision_processor_instance.process_document.return_value = {"ocr_text": "Processed English Text", "language": "en"}
        MockVisionProcessor.return_value = mock_vision_processor_instance

        processor = BilingualProcessor(self.config)
        result = processor.process_document(self.dummy_image_path)

        self.assertEqual(result["ocr_text"], "Processed English Text")
        self.assertEqual(result["language"], "en")
        MockVisionProcessor.assert_called_once_with(self.config)
        mock_vision_processor_instance.process_document.assert_called_once_with(self.dummy_image_path)
        MockDutchOcrProcessor.assert_not_called()

    @patch("src.document_processors.bilingual_processor.pytesseract.image_to_string")
    @patch("src.document_processors.bilingual_processor.langdetect.detect")
    @patch("src.document_processors.bilingual_processor.DutchOcrProcessor")
    @patch("src.document_processors.bilingual_processor.VisionProcessor")
    def test_bilingual_processor_fallback(self, MockVisionProcessor, MockDutchOcrProcessor, mock_langdetect, mock_image_to_string):
        # Mock Tesseract to return empty string (e.g., unreadable image)
        mock_image_to_string.return_value = ""
        # Mock langdetect to raise an exception (e.g., not enough text)
        mock_langdetect.detect.side_effect = Exception("Language detection failed")

        # Mock VisionProcessor (as it's the default fallback)
        mock_vision_processor_instance = MagicMock()
        mock_vision_processor_instance.process_document.return_value = {"ocr_text": "Fallback English Text", "language": "en"}
        MockVisionProcessor.return_value = mock_vision_processor_instance

        processor = BilingualProcessor(self.config)
        result = processor.process_document(self.dummy_image_path)

        self.assertEqual(result["ocr_text"], "Fallback English Text")
        self.assertEqual(result["language"], "en")
        MockVisionProcessor.assert_called_once_with(self.config)
        mock_vision_processor_instance.process_document.assert_called_once_with(self.dummy_image_path)
        MockDutchOcrProcessor.assert_not_called()

if __name__ == "__main__":
    unittest.main()


