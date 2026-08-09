import os
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from src.document_processors.processor_pipeline import ProcessorPipeline
from src.document_processors.enhanced_processor import EnhancedProcessor
from src.document_processors.tesseract_processor import TesseractProcessor
import src.document_processors.enhanced_processor as enhanced_module


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
            "ocr_strategy": "illumination_normalized_fallback",
            "ocr_fallback_pages": 1,
            "ocr_fallback_recovered_pages": 1,
        }

        with patch.object(TesseractProcessor, "process_document", return_value=ocr_result):
            result = ProcessorPipeline(config).process_document("unused.pdf")

        self.assertEqual(result["extracted_data"]["vendor_name"], "getimg.ai")
        self.assertEqual(result["extracted_data"]["transaction_date"], "2023-08-07")
        self.assertEqual(result["extracted_data"]["total_amount"], 9.0)
        self.assertEqual(result["extracted_data"]["currency"], "USD")
        self.assertEqual(result["ocr_strategy"], "illumination_normalized_fallback")
        self.assertEqual(result["ocr_fallback_pages"], 1)
        self.assertEqual(result["ocr_fallback_recovered_pages"], 1)

    @unittest.skipIf(enhanced_module.cv2 is None, "OpenCV is optional in this test runtime")
    def test_preprocessed_image_is_private_and_removed_after_ocr(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = os.path.join(temp_dir, "receipt.with.dots.png")
            preprocessing_dir = os.path.join(temp_dir, "derived")
            Image.new("RGB", (180, 80), color=(255, 255, 255)).save(source_path)
            observed = {}

            def ocr(processed_path):
                observed["path"] = processed_path
                observed["existsDuringOcr"] = os.path.isfile(processed_path)
                return {
                    "ocr_text": "Receipt\nTotal EUR 12.10",
                    "extracted_data": {},
                    "language": "eng",
                }

            config = {
                "enable_enhanced_preprocessing": True,
                "primary_ocr_method": "tesseract",
                "enable_template_matching": False,
                "enable_line_item_extraction": False,
                "fab_preprocessing_temp_dir": preprocessing_dir,
            }
            with patch.object(TesseractProcessor, "process_document", side_effect=ocr):
                result = ProcessorPipeline(config).process_document(source_path)

            self.assertIn("12.10", result["ocr_text"])
            self.assertTrue(observed["existsDuringOcr"])
            self.assertEqual(os.path.dirname(observed["path"]), preprocessing_dir)
            self.assertFalse(os.path.exists(observed["path"]))
            self.assertTrue(os.path.isfile(source_path))
            self.assertEqual(os.listdir(preprocessing_dir), [])
            self.assertTrue(result["preprocessing"]["applied"])
            self.assertIsNone(result["preprocessing"]["reason"])
            self.assertEqual(result["preprocessing"]["deskewAngle"], 0.0)
            self.assertNotIn("path", result["preprocessing"])

    def test_preprocessed_image_is_removed_when_ocr_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = os.path.join(temp_dir, "receipt.png")
            preprocessing_dir = os.path.join(temp_dir, "derived")
            Image.new("RGB", (180, 80), color=(255, 255, 255)).save(source_path)
            observed = {}

            def preprocess(_source_path):
                os.makedirs(preprocessing_dir)
                derived_path = os.path.join(preprocessing_dir, "derived.png")
                Image.new("RGB", (180, 80), color=(255, 255, 255)).save(derived_path)
                return {
                    "processed_image_path": derived_path,
                    "cleanup_paths": [derived_path],
                }

            def failed_ocr(processed_path):
                observed["path"] = processed_path
                return {"ocr_text": "", "error": "synthetic OCR failure"}

            config = {
                "enable_enhanced_preprocessing": True,
                "primary_ocr_method": "tesseract",
                "enable_template_matching": False,
                "enable_line_item_extraction": False,
                "fab_preprocessing_temp_dir": preprocessing_dir,
            }
            with patch.object(
                EnhancedProcessor,
                "process_document",
                side_effect=preprocess,
            ), patch.object(
                TesseractProcessor,
                "process_document",
                side_effect=failed_ocr,
            ), self.assertRaisesRegex(RuntimeError, "OCR failed"):
                ProcessorPipeline(config).process_document(source_path)

            self.assertFalse(os.path.exists(observed["path"]))
            self.assertTrue(os.path.isfile(source_path))
            self.assertEqual(os.listdir(preprocessing_dir), [])


if __name__ == "__main__":
    unittest.main()
