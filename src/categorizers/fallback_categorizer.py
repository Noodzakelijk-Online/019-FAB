from typing import Dict, Any

from src.categorizers.base import BaseCategorizer

class FallbackCategorizer(BaseCategorizer):
    """Assigns a fallback category if no other categorizer can determine one."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.default_fallback_category = self.config.get("default_fallback_category", "Manual Review")

    def categorize(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Always returns the default fallback category.

        Args:
            processed_data: A dictionary containing extracted data from the document.

        Returns:
            A dictionary containing the assigned fallback category and a confidence score of 0.1.
        """
        return {"category": self.default_fallback_category, "confidence_score": 0.1}


