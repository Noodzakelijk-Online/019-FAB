import re
from typing import Any, Dict

from src.document_processors.base import BaseProcessor
from src.document_processors.tesseract_processor import TesseractProcessor, _parse_amount


class DutchOcrProcessor(BaseProcessor):
    """Run local Dutch OCR and add Dutch financial-document fields."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        dutch_config = dict(config)
        dutch_config["tesseract_lang"] = dutch_config.get("dutch_ocr_lang", "nld")
        self.ocr_processor = TesseractProcessor(dutch_config)

    def process_document(self, document_path: str) -> Dict[str, Any]:
        result = self.ocr_processor.process_document(document_path)
        full_text = result.get("ocr_text", "")
        extracted_data = result.get("extracted_data", {}) or {}
        self._enhance_dutch_extraction(full_text, extracted_data)

        response = {
            "ocr_text": full_text,
            "extracted_data": extracted_data,
            "language": "nl",
        }
        if result.get("error"):
            response["error"] = result["error"]
        return response

    @staticmethod
    def _enhance_dutch_extraction(text: str, data: Dict[str, Any]) -> None:
        btw_match = re.search(r"BTW(?:-nummer)?\s*:?\s*([A-Z]{2}\d{9}B\d{2})", text, re.IGNORECASE)
        if btw_match:
            data["btw_number"] = btw_match.group(1).upper()

        iban_match = re.search(r"\bNL\d{2}[A-Z]{4}\d{10}\b", text, re.IGNORECASE)
        if iban_match:
            data["iban"] = iban_match.group(0).upper()

        date_match = re.search(r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b", text)
        if date_match:
            data["transaction_date"] = date_match.group(1)

        amount_match = re.search(
            r"(?:totaal(?:bedrag)?|te\s+betalen|bedrag)\s*:?\s*(?:EUR)?\s*\u20ac?\s*"
            r"(\d[\d.,]*[.,]\d{2})",
            text,
            re.IGNORECASE,
        )
        if amount_match:
            data["total_amount"] = _parse_amount(amount_match.group(1))
            data["currency"] = "EUR"
