from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseCategorizer(ABC):
    """Abstract base class for all document categorizers."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    def categorize(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Categorizes the processed document data.

        Args:
            processed_data: A dictionary containing extracted data from the document.

        Returns:
            A dictionary containing the assigned category and a confidence score.
        """
        pass


