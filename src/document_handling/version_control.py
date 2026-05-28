import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List


class DocumentVersionControl:
    """Maintain a lightweight JSON manifest of document versions."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.manifest_path = self.config.get("document_version_manifest_path", "data/document_versions.json")
        os.makedirs(os.path.dirname(self.manifest_path) or ".", exist_ok=True)

    def register_version(self, document_id: str, file_path: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        manifest = self._load_manifest()
        versions = manifest.setdefault(document_id, [])
        entry = {
            "version": len(versions) + 1,
            "file_path": file_path,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        versions.append(entry)
        self._save_manifest(manifest)
        return entry

    def get_versions(self, document_id: str) -> List[Dict[str, Any]]:
        return self._load_manifest().get(document_id, [])

    def _load_manifest(self) -> Dict[str, List[Dict[str, Any]]]:
        if not os.path.exists(self.manifest_path):
            return {}
        with open(self.manifest_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def _save_manifest(self, manifest: Dict[str, List[Dict[str, Any]]]) -> None:
        with open(self.manifest_path, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, sort_keys=True)
