from typing import Dict, Any

from src.document_processors.base import BaseProcessor
from src.document_processors.enhanced_processor import EnhancedProcessor
from src.document_processors.vision_processor import VisionProcessor
from src.document_processors.tesseract_processor import TesseractProcessor
from src.document_processors.template_matching_processor import TemplateMatchingProcessor
from src.document_processors.line_item_extractor import LineItemExtractor
from src.document_processors.processor_factory import ProcessorFactory
from src.document_processors.financial_field_extractor import FinancialFieldExtractor


class ProcessorPipeline(BaseProcessor):
    """Orchestrates OCR, extraction, template matching, and line-item extraction."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.pipeline_steps = []
        self.field_extractor = FinancialFieldExtractor()
        self._initialize_pipeline()

    def _initialize_pipeline(self):
        configured_steps = self.config.get("processor_pipeline_steps")
        if configured_steps:
            for step in configured_steps:
                processor_type = step.get("type") or step.get("name")
                if not processor_type:
                    raise ValueError("Each processor pipeline step requires a type.")
                self.pipeline_steps.append(ProcessorFactory.create_processor(processor_type, self.config))
            return

        if self.config.get("enable_enhanced_preprocessing", True):
            self.pipeline_steps.append(EnhancedProcessor(self.config))

        # Local OCR is the reliable default; Vision remains opt-in for users
        # who explicitly configure Google credentials.
        ocr_method = self.config.get("primary_ocr_method", "tesseract")
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
            "field_confidences": {},
            "field_evidence": {},
            "language": "",
            "ocr_confidence": 0.0,
            "ocr_strategy": "not_run",
            "ocr_fallback_pages": 0,
            "ocr_fallback_recovered_pages": 0,
        }
        current_path = document_path

        for step in self.pipeline_steps:
            if isinstance(step, EnhancedProcessor):
                result = step.process_document(current_path)
                if result.get("processed_image_path"):
                    current_path = result["processed_image_path"]
                continue

            if isinstance(step, (VisionProcessor, TesseractProcessor)):
                result = step.process_document(current_path)
                if result.get("error") and not str(result.get("ocr_text") or "").strip():
                    raise RuntimeError(f"OCR failed: {result['error']}")
                processed_data["ocr_text"] = result.get("ocr_text", "")
                self._merge_extracted_data(processed_data, result)
                self._merge_extracted_data(
                    processed_data,
                    self.field_extractor.extract(processed_data["ocr_text"]),
                )
                processed_data["language"] = result.get("language", "")
                processed_data["ocr_confidence"] = result.get("ocr_confidence", 0.0)
                processed_data["ocr_strategy"] = result.get("ocr_strategy", "standard")
                processed_data["ocr_fallback_pages"] = result.get("ocr_fallback_pages", 0)
                processed_data["ocr_fallback_recovered_pages"] = result.get("ocr_fallback_recovered_pages", 0)
                continue

            if isinstance(step, (TemplateMatchingProcessor, LineItemExtractor)):
                result = step.process_document(current_path, processed_data["ocr_text"])
                self._merge_extracted_data(processed_data, result)
                continue

            result = step.process_document(current_path)
            self._merge_extracted_data(processed_data, result)
            if result.get("ocr_text"):
                processed_data["ocr_text"] = result["ocr_text"]
            if result.get("language"):
                processed_data["language"] = result["language"]

        return processed_data

    def _merge_extracted_data(self, processed_data: Dict[str, Any], result: Dict[str, Any]) -> None:
        incoming_data = result.get("extracted_data", {}) or {}
        incoming_confidences = result.get("field_confidences", {}) or {}
        incoming_evidence = result.get("field_evidence", {}) or {}

        for key, value in incoming_data.items():
            if self._is_empty(value):
                continue
            existing_confidence = processed_data["field_confidences"].get(key, 0.0)
            incoming_confidence = incoming_confidences.get(key, 0.5)
            existing_value = processed_data["extracted_data"].get(key)
            if self._is_empty(existing_value) or incoming_confidence >= existing_confidence:
                processed_data["extracted_data"][key] = value
                processed_data["field_confidences"][key] = incoming_confidence
                if key in incoming_evidence:
                    processed_data["field_evidence"][key] = incoming_evidence[key]
                else:
                    processed_data["field_evidence"].pop(key, None)

    @staticmethod
    def _is_empty(value: Any) -> bool:
        return value is None or value == "" or value == [] or value == {}
