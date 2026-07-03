from typing import Dict, Any
try:
    import cv2
except ImportError:
    cv2 = None
try:
    import numpy as np
except ImportError:
    np = None
try:
    from PIL import Image
except ImportError:
    Image = None
try:
    import pytesseract
except ImportError:
    pytesseract = None

from src.document_processors.base import BaseProcessor

class HandwrittenRecognitionProcessor(BaseProcessor):
    """Processes documents to recognize handwritten text using image preprocessing and OCR."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.tesseract_cmd = self.config.get("tesseract_cmd", "tesseract")
        if pytesseract is not None:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
        self.psm = self.config.get("handwritten_psm", 6) # Page segmentation mode for Tesseract
        self.ocr_lang = self.config.get("handwritten_ocr_lang", "eng")

    def process_document(self, document_path: str) -> Dict[str, Any]:
        if cv2 is None or np is None or Image is None or pytesseract is None:
            return {"ocr_text": "", "extracted_data": {}, "language": ""}

        try:
            img = cv2.imread(document_path)
            if img is None:
                raise ValueError(f"Could not load image from {document_path}")

            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Apply adaptive thresholding to enhance handwritten text
            # This helps separate text from background, especially for varied lighting
            thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, \
                                           cv2.THRESH_BINARY_INV, 11, 2)

            # Optional: Dilation to make text thicker (can help with thin handwriting)
            kernel = np.ones((2,2),np.uint8)
            dilated = cv2.dilate(thresh, kernel, iterations = 1)

            # Convert OpenCV image to PIL Image for Tesseract
            pil_image = Image.fromarray(dilated)

            # Use Tesseract with specific PSM for handwritten text
            # PSM 6: Assume a single uniform block of text.
            # PSM 11: Sparse text. Find as much text as possible in no particular order.
            # PSM 13: Raw line. Treat the image as a single text line.
            custom_config = f'--psm {self.psm} --oem 3'
            full_text = pytesseract.image_to_string(pil_image, lang=self.ocr_lang, config=custom_config)

            # Basic extraction (can be enhanced)
            extracted_data = self._extract_data_from_text(full_text)

            return {
                "ocr_text": full_text,
                "extracted_data": extracted_data,
                "language": self.ocr_lang # Tesseract doesn't detect language directly in this simple usage
            }
        except Exception as e:
            print(f"Error processing document with HandwrittenRecognitionProcessor: {e}")
            return {"ocr_text": "", "extracted_data": {}, "language": ""}

    def _extract_data_from_text(self, text: str) -> Dict[str, Any]:
        """Placeholder for extracting structured data from the OCR text."""
        # This would involve more sophisticated regex or NLP for handwritten specifics
        data = {
            "vendor_name": None,
            "transaction_date": None,
            "total_amount": None,
            "currency": None,
            "vat_amount": None,
            "line_items": []
        }
        # Example: Simple regex for amount (highly simplified)
        import re
        amount_match = re.search(r"Total[:\]?\s*([€$£]?\s*\d+[.,]\d{2})", text, re.IGNORECASE)
        if amount_match:
            data["total_amount"] = amount_match.group(1).replace(",", ".").replace("€", "").strip()
            try:
                data["total_amount"] = float(data["total_amount"])
            except ValueError:
                pass # Keep as string if conversion fails
        return data


