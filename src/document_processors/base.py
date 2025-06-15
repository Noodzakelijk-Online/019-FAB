from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseProcessor(ABC):
    """Abstract base class for all document processors."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    def process_document(self, document_path: str) -> Dict[str, Any]:
        """Processes a document to extract relevant data.

        Args:
            document_path: The local path to the document file.

        Returns:
            A dictionary containing extracted data (e.g., vendor, amount, date)
            and the full OCR text.
        """
        pass


