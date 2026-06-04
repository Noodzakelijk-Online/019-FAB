from google.cloud import vision
from typing import Dict, Any

from src.document_processors.base import BaseProcessor
from src.document_processors.financial_field_extractor import FinancialFieldExtractor


class VisionProcessor(BaseProcessor):
    """Processes documents using Google Cloud Vision API for OCR and field extraction."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client = vision.ImageAnnotatorClient()
        self.extractor = FinancialFieldExtractor()

    def process_document(self, document_path: str) -> Dict[str, Any]:
        try:
            with open(document_path, "rb") as image_file:
                content = image_file.read()

            image = vision.Image(content=content)
            response = self.client.document_text_detection(image=image)
            if getattr(response, "error", None) and response.error.message:
                raise RuntimeError(response.error.message)

            full_text = response.full_text_annotation.text if response.full_text_annotation else ""
            extraction = self.extractor.extract(full_text)
            language = "en"
            pages = response.full_text_annotation.pages if response.full_text_annotation else []
            if pages and pages[0].property.detected_languages:
                language = pages[0].property.detected_languages[0].language_code

            return {
                "ocr_text": full_text,
                "extracted_data": extraction["extracted_data"],
                "field_confidences": extraction["field_confidences"],
                "language": language,
                "ocr_confidence": 0.85 if full_text else 0.0,
            }
        except Exception as exc:
            print(f"Error processing document with Google Vision: {exc}")
            return {"ocr_text": "", "extracted_data": {}, "field_confidences": {}, "language": "", "ocr_confidence": 0.0}

    def _extract_data_from_text(self, text: str) -> Dict[str, Any]:
        """Backward-compatible helper for older tests/callers."""
        return self.extractor.extract(text).get("extracted_data", {})
