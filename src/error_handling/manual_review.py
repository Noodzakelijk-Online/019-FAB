from typing import Dict, Any, List
import json
import os

class ManualReviewInterface:
    """Manages documents that require manual review."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.review_queue_file = self.config.get("manual_review_queue_file", "data/manual_review_queue.json")
        self.review_queue = self._load_review_queue()

    def _load_review_queue(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.review_queue_file):
            with open(self.review_queue_file, "r") as f:
                return json.load(f)
        return []

    def _save_review_queue(self):
        os.makedirs(os.path.dirname(self.review_queue_file), exist_ok=True)
        with open(self.review_queue_file, "w") as f:
            json.dump(self.review_queue, f, indent=4)

    def add_to_review_queue(self, document_id: str, reason: str, details: str = ""):
        """Adds a document to the manual review queue."""
        entry = {
            "document_id": document_id,
            "reason": reason,
            "details": details,
            "timestamp": os.fspath(os.path.getmtime(self.review_queue_file)), # Placeholder for actual timestamp
            "status": "pending"
        }
        self.review_queue.append(entry)
        self._save_review_queue()
        print(f"Document {document_id} added to manual review queue. Reason: {reason}")

    def get_pending_reviews(self) -> List[Dict[str, Any]]:
        """Returns all documents currently pending manual review."""
        return [item for item in self.review_queue if item["status"] == "pending"]

    def mark_reviewed(self, document_id: str, new_status: str = "reviewed", resolution: str = ""):
        """Marks a document as reviewed and optionally updates its status/resolution."""
        for item in self.review_queue:
            if item["document_id"] == document_id and item["status"] == "pending":
                item["status"] = new_status
                item["resolution"] = resolution
                self._save_review_queue()
                print(f"Document {document_id} marked as {new_status}.")
                return True
        return False


