from abc import ABC, abstractmethod
import hashlib
import os
import re
from typing import List, Dict, Any

class BaseFetcher(ABC):
    """Abstract base class for all document fetchers."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.last_error = None
        self.last_run = {
            "status": "idle",
            "fetched": 0,
            "skipped": 0,
            "pages": 0,
        }

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
        local_path = self._download_path("/tmp", filename, filename)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(content)
        return local_path

    def _start_run(self) -> None:
        self.last_error = None
        self.last_run = {"status": "running", "fetched": 0, "skipped": 0, "pages": 0}

    def _finish_run(self, fetched: int, skipped: int = 0, pages: int = 0) -> None:
        self.last_run = {
            "status": "completed",
            "fetched": int(fetched),
            "skipped": int(skipped),
            "pages": int(pages),
        }

    def _fail_run(self, error: Exception, fetched: int = 0, skipped: int = 0, pages: int = 0) -> None:
        self.last_error = error
        self.last_run = {
            "status": "partial" if fetched else "failed",
            "fetched": int(fetched),
            "skipped": int(skipped),
            "pages": int(pages),
            "errorType": type(error).__name__,
        }

    def _download_path(self, directory: str, filename: str, identity: Any) -> str:
        safe_name = os.path.basename(str(filename or "document"))
        safe_name = re.sub(r"[^A-Za-z0-9._ -]+", "_", safe_name).strip(" .") or "document"
        if len(safe_name) > 180:
            stem, extension = os.path.splitext(safe_name)
            extension = extension[:20]
            safe_name = f"{stem[:max(1, 180 - len(extension))]}{extension}"
        prefix = hashlib.sha256(str(identity or safe_name).encode("utf-8")).hexdigest()[:12]
        return os.path.join(directory, f"{prefix}-{safe_name}")

    def _content_download_path(
        self,
        directory: str,
        filename: str,
        identity: Any,
        content: bytes,
    ) -> str:
        content_hash = hashlib.sha256(content).hexdigest()
        return self._download_path(directory, filename, f"{identity}:{content_hash}")

    def _request_timeout(self, default: float = 30.0) -> float:
        for key in (
            "source_request_timeout_seconds",
            "document_fetch_timeout_seconds",
            "request_timeout_seconds",
        ):
            value = self.config.get(key)
            if value not in (None, ""):
                try:
                    parsed = float(value)
                except (TypeError, ValueError):
                    continue
                return max(1.0, min(parsed, 300.0))
        return default

    def _interactive_auth_enabled(self, source: str) -> bool:
        value = self.config.get(
            f"{source}_interactive_auth",
            self.config.get("source_interactive_auth", False),
        )
        if isinstance(value, str):
            return value.strip().lower() not in {"", "0", "false", "no", "off"}
        return bool(value)


