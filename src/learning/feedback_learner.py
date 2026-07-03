from typing import Dict, Any, List
import json
import os
from datetime import datetime, timezone

class FeedbackLearner:
    """Records and manages feedback for the learning system."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.feedback_log_file = self.config.get("feedback_log_file", "data/feedback_log.json")
        self.feedback_data = self._load_feedback()

    def _load_feedback(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.feedback_log_file):
            with open(self.feedback_log_file, "r") as f:
                return json.load(f)
        return []

    def _save_feedback(self):
        os.makedirs(os.path.dirname(self.feedback_log_file), exist_ok=True)
        with open(self.feedback_log_file, "w") as f:
            json.dump(self.feedback_data, f, indent=4)

    def record_feedback(self, document_id: str, original_category: str, corrected_category: str):
        """Records a feedback entry for a document."""
        feedback_entry = {
            "document_id": document_id,
            "original_category": original_category,
            "corrected_category": corrected_category,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.feedback_data.append(feedback_entry)
        self._save_feedback()
        print(f"Feedback recorded: Doc ID {document_id}, Original: {original_category}, Corrected: {corrected_category}")

    def get_all_feedback(self) -> List[Dict[str, Any]]:
        """Returns all recorded feedback entries."""
        return self.feedback_data


