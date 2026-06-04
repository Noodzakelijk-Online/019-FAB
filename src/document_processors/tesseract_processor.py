import os
import re
import tempfile
from typing import Any, Dict, List

import pytesseract
from PIL import Image

from src.document_processors.base import BaseProcessor
from src.document_processors.financial_field_extractor import FinancialFieldExtractor


class TesseractProcessor(BaseProcessor):
    """Processes images and image-based PDFs using Tesseract OCR."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.tesseract_cmd = self.config.get("tesseract_cmd", "tesseract")
        pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
        self.extractor = FinancialFieldExtractor()

    def process_document(self, document_path: str) -> Dict[str, Any]:
        try:
            ocr_text_parts: List[str] = []
            image_paths = self._document_to_images(document_path)
            for image_path in image_paths:
                image = Image.open(image_path)
                ocr_text_parts.append(
                    pytesseract.image_to_string(image, lang=self.config.get("tesseract_lang", "eng"))
                )

            full_text = "\n".join(part for part in ocr_text_parts if part).strip()
            extraction = self.extractor.extract(full_text)

            return {
                "ocr_text": full_text,
                "extracted_data": extraction["extracted_data"],
                "field_confidences": extraction["field_confidences"],
                "language": self.config.get("tesseract_lang", "eng"),
                "ocr_confidence": 0.75 if full_text else 0.0,
            }
        except Exception as exc:
            print(f"Error processing document with Tesseract: {exc}")
            return {"ocr_text": "", "extracted_data": {}, "field_confidences": {}, "language": "", "ocr_confidence": 0.0}

    def _document_to_images(self, document_path: str) -> List[str]:
        extension = os.path.splitext(document_path)[1].lower()
        if extension != ".pdf":
            return [document_path]

        try:
            from pdf2image import convert_from_path
        except ImportError as exc:
            raise RuntimeError("PDF OCR requires pdf2image and Poppler to be installed.") from exc

        output_dir = tempfile.mkdtemp(prefix="fab_pdf_pages_")
        pages = convert_from_path(document_path, dpi=int(self.config.get("pdf_ocr_dpi", 250)))
        image_paths = []
        for index, page in enumerate(pages, start=1):
            page_path = os.path.join(output_dir, f"page_{index}.png")
            page.save(page_path, "PNG")
            image_paths.append(page_path)
        return image_paths

    def _extract_data_from_text(self, text: str) -> Dict[str, Any]:
        """Backward-compatible helper for older tests/callers."""
        return self.extractor.extract(text).get("extracted_data", {})
