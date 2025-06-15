from typing import Dict, Any, List
import json
import os

class ManualReviewInterface:
    """Provides a web interface for manual review of flagged documents."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.review_queue_file = self.config.get("manual_review_queue_file", "data/manual_review_queue.json")
        # In a real web interface, you would use a framework like Flask or FastAPI
        # and serve HTML templates. This is a simplified representation.
        print("Manual Review Interface initialized. Review queue file:", self.review_queue_file)

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
            "timestamp": datetime.datetime.now().isoformat(),
            "status": "pending"
        }
        review_queue = self._load_review_queue()
        review_queue.append(entry)
        self._save_review_queue()
        print(f"Document {document_id} added to manual review queue. Reason: {reason}")

    def get_pending_reviews(self) -> List[Dict[str, Any]]:
        """Returns all documents currently pending manual review."""
        review_queue = self._load_review_queue()
        return [item for item in review_queue if item["status"] == "pending"]

    def mark_reviewed(self, document_id: str, new_status: str = "reviewed", resolution: str = ""):
        """Marks a document as reviewed and optionally updates its status/resolution."""
        review_queue = self._load_review_queue()
        for item in review_queue:
            if item["document_id"] == document_id and item["status"] == "pending":
                item["status"] = new_status
                item["resolution"] = resolution
                self._save_review_queue()
                print(f"Document {document_id} marked as {new_status}.")
                return True
        return False

    # Placeholder for web interface methods (using Flask/FastAPI in a real implementation)
    def run_web_interface(self, host: str = "0.0.0.0", port: int = 5001):
        """Placeholder to indicate running a web interface."""
        print(f"Manual review web interface would run on http://{host}:{port}")
        print("This requires a web framework like Flask or FastAPI and associated templates.")



