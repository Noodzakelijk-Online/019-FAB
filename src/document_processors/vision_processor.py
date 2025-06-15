from google.cloud import vision
import os
from typing import Dict, Any

from src.document_processors.base import BaseProcessor

class VisionProcessor(BaseProcessor):
    """Processes documents using Google Cloud Vision API for OCR and data extraction."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Ensure GOOGLE_APPLICATION_CREDENTIALS environment variable is set
        # or pass credentials directly if preferred.
        self.client = vision.ImageAnnotatorClient()

    def process_document(self, document_path: str) -> Dict[str, Any]:
        with open(document_path, "rb") as image_file:
            content = image_file.read()

        image = vision.Image(content=content)

        response = self.client.document_text_detection(image=image)
        full_text = response.full_text_annotation.text

        # Basic extraction (can be enhanced with more sophisticated parsing)
        extracted_data = self._extract_data_from_text(full_text)

        return {
            "ocr_text": full_text,
            "extracted_data": extracted_data,
            "language": response.full_text_annotation.pages[0].property.detected_languages[0].language_code if response.full_text_annotation.pages and response.full_text_annotation.pages[0].property.detected_languages else "en" # Default to English
        }

    def _extract_data_from_text(self, text: str) -> Dict[str, Any]:
        """Placeholder for extracting structured data from the OCR text."""
        # This is a very basic example. Real-world extraction would involve regex, NLP, etc.
        data = {
            "vendor_name": None,
            "transaction_date": None,
            "total_amount": None,
            "currency": None,
            "vat_amount": None,
            "line_items": []
        }

        # Example: Simple regex for amount (highly simplified)
        import re
        amount_match = re.search(r"Total[:\]?\s*([€$£]?\s*\d+[.,]\d{2})", text, re.IGNORECASE)
        if amount_match:
            data["total_amount"] = amount_match.group(1).replace(",", ".").replace("€", "").strip()
            try:
                data["total_amount"] = float(data["total_amount"])
            except ValueError:
                pass # Keep as string if conversion fails

        # More sophisticated parsing would go here

        return data


