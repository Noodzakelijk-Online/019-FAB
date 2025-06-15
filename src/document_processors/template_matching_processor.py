from typing import Dict, Any, List
import re

from src.document_processors.base import BaseProcessor

class TemplateMatchingProcessor(BaseProcessor):
    """Processes documents using predefined templates for specific vendors."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.templates = self.config.get("vendor_templates", {})

    def process_document(self, document_path: str, ocr_text: str) -> Dict[str, Any]:
        extracted_data = {
            "vendor_name": None,
            "transaction_date": None,
            "total_amount": None,
            "currency": None,
            "vat_amount": None,
            "line_items": []
        }

        for vendor, template_config in self.templates.items():
            if re.search(template_config["keywords"], ocr_text, re.IGNORECASE):
                extracted_data["vendor_name"] = vendor
                # Apply regex patterns from template_config to extract data
                # This is a simplified example; real implementation would be more complex
                if "total_pattern" in template_config:
                    match = re.search(template_config["total_pattern"], ocr_text)
                    if match:
                        extracted_data["total_amount"] = float(match.group(1).replace(",", "."))
                
                # Add more extraction logic for date, VAT, line items based on template
                break
        
        return {
            "ocr_text": ocr_text, # Pass through the original OCR text
            "extracted_data": extracted_data,
            "language": "en" # Language detection should happen before this processor
        }


