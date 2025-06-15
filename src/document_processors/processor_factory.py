from typing import Dict, Any

from src.document_processors.base import BaseProcessor
from src.document_processors.vision_processor import VisionProcessor
from src.document_processors.tesseract_processor import TesseractProcessor
from src.document_processors.dutch_ocr_processor import DutchOcrProcessor
from src.document_processors.handwritten_recognition_processor import HandwrittenRecognitionProcessor
from src.document_processors.template_matching_processor import TemplateMatchingProcessor
from src.document_processors.line_item_extractor import LineItemExtractor
from src.document_processors.enhanced_processor import EnhancedProcessor
from src.document_processors.bilingual_processor import BilingualProcessor

class ProcessorFactory:
    """Factory to create instances of document processors based on configuration."""

    @staticmethod
    def create_processor(processor_type: str, config: Dict[str, Any]) -> BaseProcessor:
        if processor_type == "vision":
            return VisionProcessor(config)
        elif processor_type == "tesseract":
            return TesseractProcessor(config)
        elif processor_type == "dutch_ocr":
            return DutchOcrProcessor(config)
        elif processor_type == "handwritten_recognition":
            return HandwrittenRecognitionProcessor(config)
        elif processor_type == "template_matching":
            return TemplateMatchingProcessor(config)
        elif processor_type == "line_item_extractor":
            return LineItemExtractor(config)
        elif processor_type == "enhanced_preprocessing":
            return EnhancedProcessor(config)
        elif processor_type == "bilingual":
            return BilingualProcessor(config)
        else:
            raise ValueError(f"Unknown processor type: {processor_type}")


