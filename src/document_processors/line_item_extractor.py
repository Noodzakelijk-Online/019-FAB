from typing import Dict, Any, List
import re

from src.document_processors.base import BaseProcessor

class LineItemExtractor(BaseProcessor):
    """Extracts line items from the OCR text of a document."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.line_item_patterns = self.config.get("line_item_patterns", [])

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
                    line_items.append(item)

        # This processor primarily adds to or modifies the 'extracted_data' part
        # of the processed document. It assumes 'ocr_text' is already available.
        return {
            "ocr_text": ocr_text,
            "extracted_data": {
                "line_items": line_items
            },
            "language": "en" # Language should be determined by a prior processor
        }


