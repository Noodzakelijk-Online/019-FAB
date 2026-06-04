from typing import Dict, Any, List
from datetime import datetime, timezone
import json
import os


class ManualReviewInterface:
    """Provides storage and helper methods for flagged manual-review documents."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.review_queue_file = self.config.get("manual_review_queue_file", "data/manual_review_queue.json")
        self.review_queue = self._load_review_queue()
        print("Manual Review Interface initialized. Review queue file:", self.review_queue_file)

    def _load_review_queue(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.review_queue_file):
            with open(self.review_queue_file, "r", encoding="utf-8") as handle:
                return json.load(handle)
        return []

    def _save_review_queue(self) -> None:
        os.makedirs(os.path.dirname(self.review_queue_file) or ".", exist_ok=True)
        with open(self.review_queue_file, "w", encoding="utf-8") as handle:
            json.dump(self.review_queue, handle, indent=4)

    def add_to_review_queue(self, document_id: str, reason: str, details: str = "") -> None:
        """Adds a document to the manual review queue."""
        entry = {
            "document_id": document_id,
            "reason": reason,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
        }
        self.review_queue.append(entry)
        self._save_review_queue()
        print(f"Document {document_id} added to manual review queue. Reason: {reason}")

    def get_pending_reviews(self) -> List[Dict[str, Any]]:
        """Returns all documents currently pending manual review."""
        return [item for item in self.review_queue if item.get("status") == "pending"]

    def mark_reviewed(self, document_id: str, new_status: str = "reviewed", resolution: str = "") -> bool:
        """Marks a document as reviewed and optionally stores its resolution."""
        for item in self.review_queue:
            if item.get("document_id") == document_id and item.get("status") == "pending":
                item["status"] = new_status
                item["resolution"] = resolution
                item["resolved_at"] = datetime.now(timezone.utc).isoformat()
                self._save_review_queue()
                print(f"Document {document_id} marked as {new_status}.")
                return True
        return False

    def run_web_interface(self, host: str = "0.0.0.0", port: int = 5001) -> None:
        """Placeholder to indicate where the future web interface will run."""
        print(f"Manual review web interface would run on http://{host}:{port}")
        print("This requires a web framework like Flask or FastAPI and associated templates.")
