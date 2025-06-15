from typing import Dict, Any
import os
import json

from src.learning.waveapps_analyzer import WaveappsAnalyzer
from src.learning.mijngeldzaken_analyzer import MijngeldzakenAnalyzer
from src.learning.feedback_learner import FeedbackLearner

class LearningManager:
    """Manages the learning process from existing data and user feedback."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.waveapps_analyzer = WaveappsAnalyzer(config)
        self.mijngeldzaken_analyzer = MijngeldzakenAnalyzer(config)
        self.feedback_learner = FeedbackLearner(config)
        self.learned_patterns_file = self.config.get("learned_patterns_file", "data/learned_patterns.json")
        self.learned_patterns = self._load_learned_patterns()

    def _load_learned_patterns(self) -> Dict[str, Any]:
        if os.path.exists(self.learned_patterns_file):
            with open(self.learned_patterns_file, "r") as f:
                return json.load(f)
        return {
            "waveapps_business": {},
            "waveapps_personal": {},
            "mijngeldzaken": {}
        }

    def _save_learned_patterns(self):
        os.makedirs(os.path.dirname(self.learned_patterns_file), exist_ok=True)
        with open(self.learned_patterns_file, "w") as f:
            json.dump(self.learned_patterns, f, indent=4)

    def learn_from_existing_data(self):
        """Initiates learning from existing Waveapps and Mijngeldzaken data."""
        print("Learning from existing Waveapps Business data...")
        waveapps_business_tx = self.waveapps_analyzer.analyze_transactions() # Assuming business ID is configured
        if waveapps_business_tx:
            self.learned_patterns["waveapps_business"] = self.waveapps_analyzer.learn_patterns(waveapps_business_tx)
            print(f"Learned patterns from Waveapps Business: {self.learned_patterns["waveapps_business"]}")

        # Assuming separate config for personal or dynamic switching
        # For now, using the same analyzer instance, but in reality, it would be a separate instance
        # with personal account credentials.
        # print("Learning from existing Waveapps Personal data...")
        # waveapps_personal_tx = self.waveapps_analyzer.analyze_transactions() 
        # if waveapps_personal_tx:
        #     self.learned_patterns["waveapps_personal"] = self.waveapps_analyzer.learn_patterns(waveapps_personal_tx)

        mijngeldzaken_export_path = self.config.get("mijngeldzaken_export_file_path")
        if mijngeldzaken_export_path and os.path.exists(mijngeldzaken_export_path):
            print(f"Learning from existing Mijngeldzaken data from {mijngeldzaken_export_path}...")
            self.learned_patterns["mijngeldzaken"] = self.mijngeldzaken_analyzer.analyze_data(mijngeldzaken_export_path)
            print(f"Learned patterns from Mijngeldzaken: {self.learned_patterns["mijngeldzaken"]}")
        else:
            print("Mijngeldzaken export file path not configured or file not found. Skipping learning from Mijngeldzaken.")

        self._save_learned_patterns()

    def get_learned_patterns(self, system_type: str) -> Dict[str, Any]:
        """Retrieves learned patterns for a specific system type."""
        return self.learned_patterns.get(system_type, {})

    def provide_feedback(self, document_id: str, original_category: str, corrected_category: str):
        """Provides feedback to the learning system based on manual corrections."""
        self.feedback_learner.record_feedback(document_id, original_category, corrected_category)
        # Trigger retraining or pattern adjustment in ML model or rule-based system
        # This would involve calling a method on MLCategorizer or RuleBasedCategorizer
        # to update their internal models/rules based on the feedback.
        print(f"Feedback recorded for document {document_id}: {original_category} -> {corrected_category}")

    def apply_learned_patterns(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Applies learned patterns to processed data for categorization assistance."""
        # This method would be called by the categorizer to get suggestions
        # based on learned vendor maps and keyword patterns.
        # For example, if a vendor is in the learned_patterns["waveapps_business"]["vendor_category_map"],
        # suggest that category.
        suggested_category = None
        confidence = 0.0

        # Example: Apply Waveapps Business patterns
        waveapps_business_patterns = self.get_learned_patterns("waveapps_business")
        vendor_name = processed_data.get("extracted_data", {}).get("vendor_name", "").lower()
        ocr_text = processed_data.get("ocr_text", "").lower()

        if vendor_name and vendor_name in waveapps_business_patterns.get("vendor_category_map", {}):
            suggested_category = waveapps_business_patterns["vendor_category_map"][vendor_name]
            confidence = 0.8 # High confidence for direct vendor match

        # More logic to apply Mijngeldzaken patterns, keyword patterns, etc.

        return {"suggested_category": suggested_category, "confidence": confidence}


