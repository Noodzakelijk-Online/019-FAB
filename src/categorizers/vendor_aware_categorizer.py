from typing import Dict, Any

from src.categorizers.base import BaseCategorizer
from src.vendor_management.vendor_manager import VendorManager


class VendorAwareCategorizer(BaseCategorizer):
    """Categorize FAB documents by vendor profile, vendor history, and rules."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.rules = self.config.get("categorization_rules", {})
        self.vendor_manager = VendorManager(config)

    def categorize(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        ocr_text = processed_data.get("ocr_text", "")
        extracted_data = processed_data.get("extracted_data", {})
        vendor_name = extracted_data.get("vendor_name", "")
        vendor_result = self.vendor_manager.identify_vendor(ocr_text, vendor_name)
        matched_vendor = vendor_result.get("vendor_name") or vendor_name

        category_result = self.vendor_manager.assign_category(
            matched_vendor,
            extracted_data.get("line_items", []),
            fallback_category="Uncategorized",
        )
        if category_result["category"] != "Uncategorized" and category_result["confidence_score"] >= 0.75:
            return {
                "category": category_result["category"],
                "category_path": category_result.get("category_path", []),
                "confidence_score": category_result["confidence_score"],
                "categorization_reason": category_result["reason"],
                "vendor_result": vendor_result,
            }

        normalized_text = ocr_text.lower()
        normalized_vendor = (matched_vendor or "").lower()
        for category, rule_config in self.rules.items():
            vendors = [vendor.lower() for vendor in rule_config.get("vendors", [])]
            keywords = [keyword.lower() for keyword in rule_config.get("keywords", [])]
            if normalized_vendor and normalized_vendor in vendors:
                return {
                    "category": category,
                    "category_path": self.vendor_manager.get_category_path(category),
                    "confidence_score": 0.9,
                    "categorization_reason": "configured_vendor_rule",
                    "vendor_result": vendor_result,
                }
            if any(keyword in normalized_text for keyword in keywords):
                return {
                    "category": category,
                    "category_path": self.vendor_manager.get_category_path(category),
                    "confidence_score": 0.8,
                    "categorization_reason": "configured_keyword_rule",
                    "vendor_result": vendor_result,
                }

        return {
            "category": "Uncategorized",
            "category_path": self.vendor_manager.get_category_path("Uncategorized"),
            "confidence_score": 0.0,
            "categorization_reason": "no_match",
            "vendor_result": vendor_result,
        }
