from typing import Dict, Any, List
import re
import json
import os

from src.document_processors.base import BaseProcessor
from src.document_processors.tesseract_processor import _parse_amount

class VendorTemplateProcessor(BaseProcessor):
    """Processes documents using predefined templates for specific vendors, with self-learning capabilities."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.templates_file = self.config.get("vendor_templates_file", "config/vendor_templates.json")
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, Any]:
        if os.path.exists(self.templates_file):
            try:
                with open(self.templates_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                return loaded if isinstance(loaded, dict) else {}
            except (OSError, json.JSONDecodeError):
                return {}
        return {}

    def _save_templates(self):
        parent = os.path.dirname(os.path.abspath(self.templates_file))
        os.makedirs(parent, exist_ok=True)
        with open(self.templates_file, "w", encoding="utf-8") as f:
            json.dump(self.templates, f, indent=4)

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
            # Check for keywords or patterns to identify the vendor
            if "keywords" in template_config and re.search(template_config["keywords"], ocr_text, re.IGNORECASE):
                extracted_data["vendor_name"] = vendor
                # Apply regex patterns from template_config to extract data
                for field, pattern in template_config.get("extraction_patterns", {}).items():
                    match = re.search(pattern, ocr_text, re.IGNORECASE)
                    if match:
                        # Basic handling for common fields, needs more robust parsing
                        if field == "total_amount":
                            extracted_data[field] = _parse_amount(match.group(1))
                        elif field == "transaction_date":
                            extracted_data[field] = match.group(1) # Date parsing needed
                        else:
                            extracted_data[field] = match.group(1)
                
                # Line item extraction if defined in template
                if "line_item_pattern" in template_config:
                    # This is a simplified example; real line item extraction is complex
                    line_items_raw = re.findall(template_config["line_item_pattern"], ocr_text, re.IGNORECASE)
                    extracted_data["line_items"] = [{
                        "description": item[0],
                        "total": float(item[1].replace(",", "."))
                    } for item in line_items_raw]

                break # Found a matching template, stop searching
        
        return {
            "ocr_text": ocr_text, 
            "extracted_data": extracted_data,
            "language": "en" # Language detection should happen before this processor
        }

    def add_or_update_template(self, vendor_name: str, template_config: Dict[str, Any]):
        """Adds or updates a vendor template."""
        self.templates[vendor_name] = template_config
        self._save_templates()

    def learn_from_correction(self, ocr_text: str, corrected_data: Dict[str, Any]):
        """Placeholder for self-learning capability based on manual corrections."""
        # This method would analyze the ocr_text and corrected_data
        # to infer new patterns or refine existing ones for a vendor.
        # For example, if a vendor name is consistently extracted incorrectly,
        # it could suggest a new keyword or regex pattern.
        print(f"Learning from correction for {corrected_data.get("vendor_name", "Unknown Vendor")}")
        # Implementation would involve NLP techniques, pattern mining, etc.


