import hashlib
import os
from pathlib import Path


def local_instance_id(project_root: Path) -> str:
    normalized = str(project_root.resolve()).replace("\\", "/").rstrip("/")
    if os.name == "nt":
        normalized = normalized.lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
