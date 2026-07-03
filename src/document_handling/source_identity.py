import hashlib
import json
from typing import Any, Dict, Optional


EXPLICIT_ID_KEYS = ("id", "source_document_id", "file_id", "message_id", "photo_id")


def source_document_id(document: Dict[str, Any]) -> Optional[str]:
    """Return a stable source identity shared by checkpoints and operations."""
    for key in EXPLICIT_ID_KEYS:
        if document.get(key) is not None and str(document[key]).strip():
            return _bounded_identity(str(document[key]).strip())

    identity_fields = {
        key: document.get(key)
        for key in (
            "local_path",
            "original_filename",
            "filename",
            "mime_type",
            "created_time",
            "modified_time",
            "size",
        )
        if document.get(key) is not None
    }
    content = document.get("content")
    if isinstance(content, bytes):
        identity_fields["content_sha256"] = hashlib.sha256(content).hexdigest()

    if not identity_fields:
        return None

    serialized = json.dumps(identity_fields, sort_keys=True, default=str, separators=(",", ":"))
    return f"generated:{hashlib.sha256(serialized.encode('utf-8')).hexdigest()}"


def _bounded_identity(value: str) -> str:
    if len(value) <= 255:
        return value
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"
