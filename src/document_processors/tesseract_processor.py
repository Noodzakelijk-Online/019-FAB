import re
from typing import Any, Dict

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    from pdf2image import convert_from_path
except ImportError:
    convert_from_path = None

from src.document_processors.base import BaseProcessor
from src.utils.tesseract_runtime import (
    configured_tesseract_languages,
    resolve_poppler_path,
    resolve_tesseract_command,
    tesseract_cli_config,
)


class TesseractProcessor(BaseProcessor):
    """Process image and PDF documents through local Tesseract OCR."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.tesseract_cmd = resolve_tesseract_command(self.config)
        self.ocr_lang = "+".join(configured_tesseract_languages(self.config))
        self.ocr_config = tesseract_cli_config(self.config)
        if pytesseract is not None:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd or "tesseract"

    def process_document(self, document_path: str) -> Dict[str, Any]:
        if pytesseract is None or Image is None:
            return {
                "ocr_text": "",
                "extracted_data": {},
                "language": "",
                "error": "Tesseract dependencies are not installed.",
            }
        if not self.tesseract_cmd:
            return {
                "ocr_text": "",
                "extracted_data": {},
                "language": "",
                "error": "Tesseract executable is not available.",
            }

        pages = []
        try:
            pages = self._load_pages(document_path)
            full_text = "\n\n".join(
                pytesseract.image_to_string(page, lang=self.ocr_lang, config=self.ocr_config).strip()
                for page in pages
            ).strip()
            return {
                "ocr_text": full_text,
                "extracted_data": self._extract_data_from_text(full_text),
                "language": self.ocr_lang,
            }
        except Exception as exc:
            return {
                "ocr_text": "",
                "extracted_data": {},
                "language": self.ocr_lang,
                "error": str(exc),
            }
        finally:
            for page in pages:
                close = getattr(page, "close", None)
                if callable(close):
                    close()

    def _load_pages(self, document_path: str) -> list:
        if not str(document_path).lower().endswith(".pdf"):
            return [Image.open(document_path)]
        if convert_from_path is None:
            raise RuntimeError("pdf2image is required for PDF OCR.")
        try:
            max_pages = max(1, min(int(self.config.get("tesseract_pdf_max_pages", 20)), 100))
            dpi = max(100, min(int(self.config.get("tesseract_pdf_dpi", 220)), 400))
        except (TypeError, ValueError):
            max_pages, dpi = 20, 220
        return convert_from_path(
            document_path,
            dpi=dpi,
            first_page=1,
            last_page=max_pages,
            poppler_path=resolve_poppler_path(self.config),
        )

    @staticmethod
    def _extract_data_from_text(text: str) -> Dict[str, Any]:
        """Extract conservative receipt fields from Dutch or English OCR text."""
        text = str(text or "")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        data = {
            "vendor_name": lines[0][:200] if lines else None,
            "transaction_date": None,
            "total_amount": None,
            "currency": "EUR" if "\u20ac" in text or re.search(r"\bEUR\b", text, re.IGNORECASE) else None,
            "vat_amount": None,
            "line_items": [],
        }

        date_match = re.search(r"\b(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})\b", text)
        if date_match:
            data["transaction_date"] = date_match.group(1)

        amount_match = re.search(
            r"(?:te\s+betalen|totaal(?:bedrag)?|total|amount\s+due|bedrag)\s*:?\s*"
            r"(?:EUR|USD|GBP)?\s*[\u20ac$\u00a3]?\s*(\d[\d.,]*[.,]\d{2})",
            text,
            re.IGNORECASE,
        )
        if amount_match:
            data["total_amount"] = _parse_amount(amount_match.group(1))

        vat_match = re.search(
            r"(?:btw|biw|vat)(?:\s+\d{1,2}(?:[.,]\d+)?\s*%)?\s*:?[\s\u20ac$\u00a3]*(\d[\d.,]*[.,]\d{2})",
            text,
            re.IGNORECASE,
        )
        if vat_match:
            data["vat_amount"] = _parse_amount(vat_match.group(1))
        return data


def _parse_amount(value: str) -> Any:
    normalized = re.sub(r"[^0-9.,-]", "", str(value or ""))
    if not normalized:
        return None
    if "," in normalized and "." in normalized:
        if normalized.rfind(",") > normalized.rfind("."):
            normalized = normalized.replace(".", "").replace(",", ".")
        else:
            normalized = normalized.replace(",", "")
    elif "," in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    elif normalized.count(".") > 1:
        normalized = normalized.replace(".", "")
    try:
        return float(normalized)
    except ValueError:
        return value
