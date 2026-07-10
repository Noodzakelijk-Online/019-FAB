from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict


class MijngeldzakenArtifactStore:
    """Persist supervised MijnGeldzaken artifacts atomically on local storage."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.export_dir = Path(
            self.config.get("mijngeldzaken_export_dir")
            or self.config.get("operations_mijngeldzaken_export_dir")
            or "data/exports/mijngeldzaken"
        ).expanduser()

    def write_text(
        self,
        filename: str,
        content: str,
        *,
        encoding: str = "utf-8",
        include_checksum: bool = True,
    ) -> Dict[str, Any]:
        payload = str(content).encode(encoding)
        checksum = hashlib.sha256(payload).hexdigest()
        safe_name = _safe_filename(filename)
        if include_checksum:
            path = Path(safe_name)
            safe_name = f"{path.stem}-{checksum[:12]}{path.suffix}"

        export_dir = self.export_dir.resolve()
        export_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = export_dir / safe_name
        descriptor, temporary_path = tempfile.mkstemp(
            prefix=".fab-mijngeldzaken-",
            suffix=".tmp",
            dir=str(export_dir),
        )
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, artifact_path)
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            if os.path.exists(temporary_path):
                os.remove(temporary_path)
            raise

        return {
            "path": str(artifact_path),
            "filename": artifact_path.name,
            "sha256": checksum,
            "size_bytes": len(payload),
        }


def _safe_filename(value: Any) -> str:
    name = Path(str(value or "artifact")).name
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(name).stem).strip(".-")[:100] or "artifact"
    suffix = re.sub(r"[^A-Za-z0-9.]", "", Path(name).suffix)[:12]
    return f"{stem}{suffix}"
