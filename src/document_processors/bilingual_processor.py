from typing import Any, Dict

try:
    import langdetect
except ImportError:
    langdetect = None

from src.document_processors.base import BaseProcessor
from src.document_processors.dutch_ocr_processor import DutchOcrProcessor
from src.document_processors.tesseract_processor import TesseractProcessor


class BilingualProcessor(BaseProcessor):
    """Run one local OCR pass, detect its language, and apply Dutch enrichment."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.ocr_processor = TesseractProcessor(config)

    def process_document(self, document_path: str) -> Dict[str, Any]:
        result = self.ocr_processor.process_document(document_path)
        text = str(result.get("ocr_text") or "").strip()
        detected_language = "en"

        if text and langdetect is not None:
            try:
                detected_language = langdetect.detect(text)
            except Exception:
                detected_language = "en"

        if detected_language == "nl":
            extracted_data = result.get("extracted_data", {}) or {}
            DutchOcrProcessor._enhance_dutch_extraction(text, extracted_data)
            result["extracted_data"] = extracted_data

        result["language"] = detected_language
        return result
