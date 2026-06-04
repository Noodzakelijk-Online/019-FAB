import hashlib
import os
from pathlib import Path
from typing import Any, Dict, List

from src.document_fetchers.base import BaseFetcher


class LocalFolderFetcher(BaseFetcher):
    """Fetches documents from a local folder for Windows-first FAB operation."""

    SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}

    def _authenticate(self):
        return None

    def fetch_documents(self) -> List[Dict[str, Any]]:
        input_dir = Path(self.config.get("local_input_dir", "data/sort_out"))
        input_dir.mkdir(parents=True, exist_ok=True)

        documents: List[Dict[str, Any]] = []
        for file_path in sorted(input_dir.iterdir()):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                continue

            content_hash = self._sha256(file_path)
            document_id = f"local_{content_hash}"
            documents.append(
                {
                    "id": document_id,
                    "source": "local_folder",
                    "source_external_id": str(file_path),
                    "original_filename": file_path.name,
                    "local_path": str(file_path),
                    "content_hash": content_hash,
                    "metadata": {
                        "mime_type": self._guess_mime_type(file_path),
                        "size_bytes": file_path.stat().st_size,
                    },
                }
            )
        return documents

    @staticmethod
    def _sha256(file_path: Path) -> str:
        digest = hashlib.sha256()
        with file_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _guess_mime_type(file_path: Path) -> str:
        extension = file_path.suffix.lower()
        if extension == ".pdf":
            return "application/pdf"
        if extension in {".jpg", ".jpeg"}:
            return "image/jpeg"
        if extension == ".png":
            return "image/png"
        if extension in {".tif", ".tiff"}:
            return "image/tiff"
        if extension == ".webp":
            return "image/webp"
        return "application/octet-stream"
