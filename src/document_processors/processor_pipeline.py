from typing import List, Dict, Any

from src.document_processors.base import BaseProcessor
from src.document_processors.enhanced_processor import EnhancedProcessor
from src.document_processors.vision_processor import VisionProcessor
from src.document_processors.tesseract_processor import TesseractProcessor
from src.document_processors.template_matching_processor import TemplateMatchingProcessor
from src.document_processors.line_item_extractor import LineItemExtractor

class ProcessorPipeline(BaseProcessor):
    """Orchestrates a pipeline of document processors."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.pipeline_steps = []
        self._initialize_pipeline()

    def _initialize_pipeline(self):
        # Example pipeline configuration. This should ideally be configurable via config.ini
        # or passed dynamically.
        if self.config.get("enable_enhanced_preprocessing", True):
            self.pipeline_steps.append(EnhancedProcessor(self.config))
        
        # Determine primary OCR method
        ocr_method = self.config.get("primary_ocr_method", "vision")
        if ocr_method == "vision":
            self.pipeline_steps.append(VisionProcessor(self.config))
        elif ocr_method == "tesseract":
            self.pipeline_steps.append(TesseractProcessor(self.config))
        else:
            raise ValueError(f"Unknown primary OCR method: {ocr_method}")

        if self.config.get("enable_template_matching", True):
            self.pipeline_steps.append(TemplateMatchingProcessor(self.config))
        
        if self.config.get("enable_line_item_extraction", True):
            self.pipeline_steps.append(LineItemExtractor(self.config))

    def process_document(self, document_path: str) -> Dict[str, Any]:
        processed_data = {
            "document_path": document_path,
            "ocr_text": "",
            "extracted_data": {},
            "language": ""
        }

        current_path = document_path

        for step in self.pipeline_steps:
            if isinstance(step, EnhancedProcessor):
                # EnhancedProcessor returns a processed image path
                result = step.process_document(current_path)
                if result.get("processed_image_path"):
                    current_path = result["processed_image_path"]
            elif isinstance(step, (VisionProcessor, TesseractProcessor)):
                # OCR processors take the current path and return text and extracted data
                result = step.process_document(current_path)
                processed_data["ocr_text"] = result.get("ocr_text", "")
                processed_data["extracted_data"].update(result.get("extracted_data", {}))
                processed_data["language"] = result.get("language", "")
            elif isinstance(step, (TemplateMatchingProcessor, LineItemExtractor)):
                # These processors need the OCR text from previous steps
                result = step.process_document(current_path, processed_data["ocr_text"])
                processed_data["extracted_data"].update(result.get("extracted_data", {}))
            else:
                # Generic processing step
                result = step.process_document(current_path)
                processed_data["extracted_data"].update(result.get("extracted_data", {}))
                if result.get("ocr_text"):
                    processed_data["ocr_text"] = result["ocr_text"]
                if result.get("language"):
                    processed_data["language"] = result["language"]

        return processed_data


