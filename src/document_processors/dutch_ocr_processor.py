from typing import Dict, Any
import re

from src.document_processors.base import BaseProcessor
from src.document_processors.vision_processor import VisionProcessor # Assuming Vision API for Dutch OCR

class DutchOcrProcessor(BaseProcessor):
    """Specialized OCR processor for Dutch financial documents."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.vision_processor = VisionProcessor(config) # Use Vision API as backend

    def process_document(self, document_path: str) -> Dict[str, Any]:
        # First, get raw OCR text and basic extraction from Vision API
        vision_result = self.vision_processor.process_document(document_path)
        full_text = vision_result.get("ocr_text", "")
        extracted_data = vision_result.get("extracted_data", {})
        language = vision_result.get("language", "")

        # Enhance extraction with Dutch-specific patterns
        self._enhance_dutch_extraction(full_text, extracted_data)

        return {
            "ocr_text": full_text,
            "extracted_data": extracted_data,
            "language": language # Should be 'nl' if detected correctly
        }

    def _enhance_dutch_extraction(self, text: str, data: Dict[str, Any]):
        """Applies Dutch-specific regex patterns for better data extraction."""
        # Example: BTW (VAT) number
        btw_match = re.search(r"BTW(?:-nummer)?\s*[:]?\s*([A-Z]{2}\d{9}B\d{2})", text, re.IGNORECASE)
        if btw_match:
            data["btw_number"] = btw_match.group(1)

        # Example: IBAN
        iban_match = re.search(r"NL\d{2}[A-Z]{4}\d{10}", text)
        if iban_match:
            data["iban"] = iban_match.group(0)

        # Example: Dutch date formats (dd-mm-yyyy, dd/mm/yyyy)
        date_match = re.search(r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b", text)
        if date_match:
            # Further parsing might be needed to standardize date format
            data["transaction_date"] = date_match.group(1)

        # Example: Total amount with Dutch currency symbol (Euro)
        # This is a more robust regex for amounts, considering comma as decimal separator
        amount_match = re.search(r"Totaal|Totaalbedrag|Te betalen|Bedrag\s*[:]?\s*€\s*(\d{1,3}(?:\.\d{3})*?,\d{2})", text, re.IGNORECASE)
        if amount_match:
            # Replace comma with dot for float conversion
            data["total_amount"] = float(amount_match.group(1).replace(".", "").replace(",", "."))
            data["currency"] = "EUR"

        # Add more Dutch-specific patterns as needed


