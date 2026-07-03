from typing import Dict, Any
try:
    import langdetect
except ImportError:
    langdetect = None

from src.document_processors.base import BaseProcessor
from src.document_processors.dutch_ocr_processor import DutchOcrProcessor
from src.document_processors.vision_processor import VisionProcessor # Assuming VisionProcessor for English OCR

class BilingualProcessor(BaseProcessor):
    """Detects document language and routes to the appropriate OCR processor."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.dutch_processor = DutchOcrProcessor(config)
        self.english_processor = VisionProcessor(config) # Using VisionProcessor for general English OCR

    def process_document(self, document_path: str) -> Dict[str, Any]:
        # First, attempt a quick OCR pass to get some text for language detection
        # Using Tesseract for a quick pass as it's local and fast for this purpose
        try:
            import pytesseract
            from PIL import Image
            temp_text = pytesseract.image_to_string(Image.open(document_path), lang="+eng+nld")
        except Exception:
            temp_text = "" # Fallback if Tesseract is not available or fails

        detected_language = "en" # Default to English
        if temp_text:
            try:
                # langdetect might need more text for accurate detection
                if langdetect is not None:
                    detected_language = langdetect.detect(temp_text)
            except Exception:
                pass # Keep default if detection fails

        if detected_language == "nl":
            print(f"Detected Dutch for {document_path}, using Dutch OCR processor.")
            return self.dutch_processor.process_document(document_path)
        else:
            print(f"Detected {detected_language} (or default English) for {document_path}, using English OCR processor.")
            return self.english_processor.process_document(document_path)


