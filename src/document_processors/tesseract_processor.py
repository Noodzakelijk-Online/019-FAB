import pytesseract
from PIL import Image
from typing import Dict, Any
import re

from src.document_processors.base import BaseProcessor

class TesseractProcessor(BaseProcessor):
    """Processes documents using Tesseract OCR for text extraction."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.tesseract_cmd = self.config.get("tesseract_cmd", "tesseract")
        pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

    def process_document(self, document_path: str) -> Dict[str, Any]:
        try:
            image = Image.open(document_path)
            full_text = pytesseract.image_to_string(image, lang=self.config.get("tesseract_lang", "eng"))

            extracted_data = self._extract_data_from_text(full_text)

            return {
                "ocr_text": full_text,
                "extracted_data": extracted_data,
                "language": self.config.get("tesseract_lang", "eng") # Tesseract doesn't detect language directly in this simple usage
            }
        except Exception as e:
            print(f"Error processing document with Tesseract: {e}")
            return {"ocr_text": "", "extracted_data": {}, "language": ""}

    def _extract_data_from_text(self, text: str) -> Dict[str, Any]:
        """Placeholder for extracting structured data from the OCR text."""
        data = {
            "vendor_name": None,
            "transaction_date": None,
            "total_amount": None,
            "currency": None,
            "vat_amount": None,
            "line_items": []
        }

        # Example: Simple regex for amount (highly simplified)
        amount_match = re.search(r"Total[:\]?\s*([€$£]?\s*\d+[.,]\d{2})", text, re.IGNORECASE)
        if amount_match:
            data["total_amount"] = amount_match.group(1).replace(",", ".").replace("€", "").strip()
            try:
                data["total_amount"] = float(data["total_amount"])
            except ValueError:
                pass # Keep as string if conversion fails

        return data


