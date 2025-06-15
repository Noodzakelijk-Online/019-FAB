from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseFetcher(ABC):
    """Abstract base class for all document fetchers."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    def fetch_documents(self) -> List[Dict[str, Any]]:
        """Fetches documents from the source.

        Returns:
            A list of dictionaries, where each dictionary represents a document
            and contains its metadata and local path.
        """
        pass

    @abstractmethod
    def _authenticate(self):
        """Handles authentication with the document source."""
        pass

    def _save_document(self, content: bytes, filename: str) -> str:
        """Saves the document content to a local file.

        Args:
            content: The binary content of the document.
            filename: The desired filename for the document.

        Returns:
            The local path where the document was saved.
        """
        # This is a placeholder. In a real implementation, you'd save to a temp directory
        # or a designated input directory.
        local_path = f"/tmp/{filename}"
        with open(local_path, "wb") as f:
            f.write(content)
        return local_path


