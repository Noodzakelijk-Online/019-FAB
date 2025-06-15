from typing import Dict, Any, List
import re

from src.categorizers.base import BaseCategorizer

class RuleBasedCategorizer(BaseCategorizer):
    """Categorizes documents based on predefined rules (keywords, vendor names)."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.rules = self.config.get("categorization_rules", {})

    def categorize(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        ocr_text = processed_data.get("ocr_text", "").lower()
        extracted_data = processed_data.get("extracted_data", {})
        vendor_name = extracted_data.get("vendor_name", "").lower()

        for category, rule_config in self.rules.items():
            keywords = [k.lower() for k in rule_config.get("keywords", [])]
            vendors = [v.lower() for v in rule_config.get("vendors", [])]

            # Check for vendor match
            if vendor_name and vendor_name in vendors:
                return {"category": category, "confidence_score": 0.9}

            # Check for keyword match in OCR text
            for keyword in keywords:
                if keyword in ocr_text:
                    return {"category": category, "confidence_score": 0.8}

        return {"category": "Uncategorized", "confidence_score": 0.0}


