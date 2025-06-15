import unittest
from unittest.mock import MagicMock, patch
import os
from PIL import Image

from src.document_processors.vision_processor import VisionProcessor
from src.document_processors.tesseract_processor import TesseractProcessor
from src.document_processors.template_matching_processor import TemplateMatchingProcessor
from src.document_processors.line_item_extractor import LineItemExtractor
from src.document_processors.enhanced_processor import EnhancedProcessor
from src.document_processors.processor_pipeline import ProcessorPipeline
from src.document_processors.dutch_ocr_processor import DutchOcrProcessor
from src.document_processors.handwritten_recognition_processor import HandwrittenRecognitionProcessor
from src.document_processors.vendor_template_processor import VendorTemplateProcessor
from src.document_processors.bilingual_processor import BilingualProcessor

class TestDocumentProcessors(unittest.TestCase):

    def setUp(self):
        self.config = {
            "google_vision_credentials_file": "/tmp/vision_credentials.json",
            "tesseract_cmd": "tesseract",
            "tesseract_lang": "eng",
            "dutch_ocr_lang": "nld",
            "handwritten_model_path": "/tmp/handwritten_model.pth",
            "template_matching_templates_dir": "/tmp/templates",
            "vendor_templates_file": "/tmp/vendor_templates.json"
        }
        # Create dummy credential file for VisionProcessor
        with open(self.config["google_vision_credentials_file"], "w") as f:
            f.write("{}")
        os.makedirs(self.config["template_matching_templates_dir"], exist_ok=True)

        # Create a dummy image file for testing
        self.dummy_image_path = "/tmp/dummy_receipt.png"
        img = Image.new("RGB", (100, 50), color = (255, 255, 255))
        img.save(self.dummy_image_path)

        # Create a dummy PDF file for testing
        self.dummy_pdf_path = "/tmp/dummy_invoice.pdf"
        # This is a very basic way to create a dummy PDF, for real tests, use a library like reportlab
        with open(self.dummy_pdf_path, "w") as f:
            f.write("%PDF-1.4\n1 0 obj<</Type/Page/Contents 2 0 R>>endobj 2 0 obj<</Length 11>>stream\nHello World\nendstream endobj\nxref\n0 3\n0000000000 65535 f\n0000000009 00000 n\n0000000045 00000 n\ntrailer<</Size 3/Root 1 0 R>>startxref\n103\n%%EOF")

    @patch("src.document_processors.vision_processor.vision.ImageAnnotatorClient")
    def test_vision_processor(self, mock_client):
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.document_text_detection.return_value = MagicMock(
            full_text_annotation=MagicMock(text="Vision OCR Text")
        )

        processor = VisionProcessor(self.config)
        result = processor.process_document(self.dummy_image_path)
        self.assertIn("Vision OCR Text", result["ocr_text"])

    @patch("src.document_processors.tesseract_processor.pytesseract.image_to_string")
    @patch("src.document_processors.tesseract_processor.Image.open")
    def test_tesseract_processor(self, mock_image_open, mock_image_to_string):
        mock_image_to_string.return_value = "Tesseract OCR Text"
        mock_image_open.return_value = MagicMock()

        processor = TesseractProcessor(self.config)
        result = processor.process_document(self.dummy_image_path)
        self.assertIn("Tesseract OCR Text", result["ocr_text"])

    @patch("src.document_processors.dutch_ocr_processor.pytesseract.image_to_string")
    @patch("src.document_processors.dutch_ocr_processor.Image.open")
    def test_dutch_ocr_processor(self, mock_image_open, mock_image_to_string):
        mock_image_to_string.return_value = "Dutch OCR Text"
        mock_image_open.return_value = MagicMock()

        processor = DutchOcrProcessor(self.config)
        result = processor.process_document(self.dummy_image_path)
        self.assertIn("Dutch OCR Text", result["ocr_text"])
        mock_image_to_string.assert_called_with(mock_image_open.return_value, lang="nld")

    @patch("src.document_processors.handwritten_recognition_processor.HandwrittenRecognitionModel")
    def test_handwritten_recognition_processor(self, mock_model):
        mock_model_instance = MagicMock()
        mock_model.return_value = mock_model_instance
        mock_model_instance.recognize.return_value = "Handwritten Text"

        processor = HandwrittenRecognitionProcessor(self.config)
        result = processor.process_document(self.dummy_image_path)
        self.assertIn("Handwritten Text", result["ocr_text"])

    def test_template_matching_processor(self):
        config = {"template_matching_templates_dir": "/tmp/templates"}
        processor = TemplateMatchingProcessor(config)
        # For a real test, you'd need to create dummy template files and test matching logic
        result = processor.process_document(self.dummy_image_path, ocr_text="Some text with a template pattern")
        self.assertIn("ocr_text", result)

    def test_line_item_extractor(self):
        config = {}
        processor = LineItemExtractor(config)
        ocr_text = "Item A 10.00\nItem B 20.00"
        result = processor.process_document(self.dummy_image_path, ocr_text=ocr_text)
        self.assertIn("line_items", result["extracted_data"])
        self.assertEqual(len(result["extracted_data"]["line_items"]), 2)

    def test_enhanced_processor(self):
        config = {"ocr_processor": "tesseract", "line_item_extraction_enabled": True}
        processor = EnhancedProcessor(config)
        # This test would require mocking internal calls to Tesseract and LineItemExtractor
        # For simplicity, we'll just check if it runs without error.
        ocr_text = "Enhanced Processor Test\nTotal: 100.00"
        result = processor.process_document(self.dummy_image_path, ocr_text=ocr_text)
        self.assertIn("ocr_text", result)

    @patch("src.document_processors.vendor_template_processor.json")
    @patch("src.document_processors.vendor_template_processor.os.path.exists")
    def test_vendor_template_processor(self, mock_exists, mock_json):
        mock_exists.return_value = True
        mock_json.load.return_value = {
            "VendorA": {
                "keywords": "VendorA",
                "extraction_patterns": {"total_amount": r"Total: (\d+\.\d{2})"}
            }
        }
        processor = VendorTemplateProcessor(self.config)
        ocr_text = "This is a document from VendorA. Total: 123.45"
        result = processor.process_document(self.dummy_image_path, ocr_text=ocr_text)
        self.assertEqual(result["extracted_data"]["vendor_name"], "VendorA")
        self.assertEqual(result["extracted_data"]["total_amount"], 123.45)

    @patch("src.document_processors.bilingual_processor.pytesseract.image_to_string")
    @patch("src.document_processors.bilingual_processor.langdetect.detect")
    @patch("src.document_processors.bilingual_processor.DutchOcrProcessor")
    @patch("src.document_processors.bilingual_processor.VisionProcessor")
    def test_bilingual_processor(self, MockVisionProcessor, MockDutchOcrProcessor, mock_langdetect, mock_image_to_string):
        mock_image_to_string.return_value = "Some text in Dutch"
        mock_langdetect.return_value = "nl"

        mock_dutch_processor_instance = MagicMock()
        MockDutchOcrProcessor.return_value = mock_dutch_processor_instance
        mock_dutch_processor_instance.process_document.return_value = {"ocr_text": "Dutch Processed Text"}

        processor = BilingualProcessor(self.config)
        result = processor.process_document(self.dummy_image_path)
        self.assertIn("Dutch Processed Text", result["ocr_text"])
        MockDutchOcrProcessor.assert_called_once()
        MockVisionProcessor.assert_not_called()

        # Test with English
        mock_langdetect.return_value = "en"
        mock_vision_processor_instance = MagicMock()
        MockVisionProcessor.return_value = mock_vision_processor_instance
        mock_vision_processor_instance.process_document.return_value = {"ocr_text": "English Processed Text"}

        result = processor.process_document(self.dummy_image_path)
        self.assertIn("English Processed Text", result["ocr_text"])
        MockVisionProcessor.assert_called_once()

    def test_processor_pipeline(self):
        config = {
            "processor_pipeline_steps": [
                {"name": "tesseract", "type": "tesseract"},
                {"name": "line_item_extractor", "type": "line_item_extractor"}
            ]
        }
        # Mock the individual processors within the pipeline
        with patch("src.document_processors.processor_pipeline.ProcessorFactory.create_processor") as mock_create_processor:
            mock_tesseract = MagicMock()
            mock_tesseract.process_document.return_value = {"ocr_text": "Pipeline Test\nItem 1 10.00", "extracted_data": {}}
            mock_line_item = MagicMock()
            mock_line_item.process_document.return_value = {"ocr_text": "Pipeline Test\nItem 1 10.00", "extracted_data": {"line_items": [{"description": "Item 1", "total": 10.00}]}}

            mock_create_processor.side_effect = [mock_tesseract, mock_line_item]

            pipeline = ProcessorPipeline(config)
            result = pipeline.process_document(self.dummy_image_path)
            self.assertIn("Pipeline Test", result["ocr_text"])
            self.assertIn("line_items", result["extracted_data"])
            self.assertEqual(len(result["extracted_data"]["line_items"]), 1)

    def tearDown(self):
        # Clean up dummy files
        if os.path.exists(self.config["google_vision_credentials_file"]):
            os.remove(self.config["google_vision_credentials_file"])
        if os.path.exists(self.dummy_image_path):
            os.remove(self.dummy_image_path)
        if os.path.exists(self.dummy_pdf_path):
            os.remove(self.dummy_pdf_path)
        if os.path.exists(self.config["template_matching_templates_dir"]):
            shutil.rmtree(self.config["template_matching_templates_dir"])
        if os.path.exists(self.config["vendor_templates_file"]):
            os.remove(self.config["vendor_templates_file"])

if __name__ == "__main__":
    unittest.main()


