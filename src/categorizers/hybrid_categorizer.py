from typing import Dict, Any

from src.categorizers.base import BaseCategorizer
from src.categorizers.rule_based_categorizer import RuleBasedCategorizer
from src.categorizers.ml_categorizer import MLCategorizer
from src.categorizers.fallback_categorizer import FallbackCategorizer

class HybridCategorizer(BaseCategorizer):
    """Combines rule-based and ML-based categorization."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.rule_based_categorizer = RuleBasedCategorizer(config)
        self.ml_categorizer = MLCategorizer(config)
        self.fallback_categorizer = FallbackCategorizer(config)
        try:
            self.ml_threshold = float(self.config.get("ml_confidence_threshold", 0.7))
        except (TypeError, ValueError):
            self.ml_threshold = 0.7

    def categorize(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        # First, try rule-based categorization
        rule_based_result = self.rule_based_categorizer.categorize(processed_data)
        if rule_based_result["category"] != "Uncategorized":
            return rule_based_result

        # If rule-based fails, try ML-based categorization
        ml_result = self.ml_categorizer.categorize(processed_data)
        if ml_result["confidence_score"] >= self.ml_threshold:
            return ml_result

        # If both fail or ML confidence is low, use fallback
        return self.fallback_categorizer.categorize(processed_data)


