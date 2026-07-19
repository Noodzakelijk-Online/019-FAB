from typing import Dict, Any, List
import re

from src.document_processors.base import BaseProcessor

class LineItemExtractor(BaseProcessor):
    """Extracts line items from the OCR text of a document."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.line_item_patterns = self.config.get("line_item_patterns") or [
            {
                "regex": r"^(.+?)\s+(-?\d[\d.,]*[.,]\d{2})$",
                "groups": {"description": 1, "total": 2},
            }
        ]

    def process_document(self, document_path: str, ocr_text: str) -> Dict[str, Any]:
        line_items = []
        lines = ocr_text.split("\n")

        for pattern_config in self.line_item_patterns:
            regex = pattern_config["regex"]
            for line in lines:
                match = re.search(regex, line, re.IGNORECASE)
                if match:
                    item = {}
                    for key, group_index in pattern_config["groups"].items():
                        try:
                            item[key] = match.group(group_index).strip()
                        except IndexError:
                            item[key] = None
                    description = str(item.get("description") or "").strip().lower().rstrip(":")
                    if description in {"total", "totaal", "totaalbedrag", "te betalen", "btw", "vat"}:
                        continue
                    if item.get("total") is not None:
                        item["total"] = self._parse_amount(item["total"])
                    line_items.append(item)

        # This processor primarily adds to or modifies the 'extracted_data' part
        # of the processed document. It assumes 'ocr_text' is already available.
        return {
            "ocr_text": ocr_text,
            "extracted_data": {
                "line_items": line_items
            },
            "language": ""
        }

    @staticmethod
    def _parse_amount(value: str):
        normalized = re.sub(r"[^0-9.,-]", "", value)
        if "," in normalized and "." in normalized:
            if normalized.rfind(",") > normalized.rfind("."):
                normalized = normalized.replace(".", "").replace(",", ".")
            else:
                normalized = normalized.replace(",", "")
        elif "," in normalized:
            normalized = normalized.replace(".", "").replace(",", ".")
        try:
            return float(normalized)
        except ValueError:
            return value


