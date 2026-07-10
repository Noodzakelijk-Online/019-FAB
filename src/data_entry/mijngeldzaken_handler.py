from __future__ import annotations

import csv
import hashlib
import io
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable

from src.data_entry.base import BaseDataEntryHandler
from src.data_entry.mijngeldzaken_surface import (
    MIJNGELDZAKEN_IMPORT_COLUMNS,
    build_mijngeldzaken_import_row,
)


class MijngeldzakenHandler(BaseDataEntryHandler):
    """Prepare a reviewable MijnGeldzaken import for supervised submission.

    MijnGeldzaken does not expose a supported bookkeeping write API for this
    flow. FAB therefore never signs in with a stored username/password here.
    Approved records become durable CSV artifacts and remain explicitly
    pending until a user completes the external import in a supervised session.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.csv_template = self.config.get("mijngeldzaken_csv_template") or {}
        self.export_dir = Path(
            self.config.get("mijngeldzaken_export_dir")
            or self.config.get("operations_mijngeldzaken_export_dir")
            or "data/exports/mijngeldzaken"
        ).expanduser()

    def _generate_csv(self, data: Dict[str, Any], filename: str | None = None) -> str:
        csv_bytes = self._render_csv(data).encode("utf-8-sig")
        checksum = hashlib.sha256(csv_bytes).hexdigest()
        document_id = _safe_filename_segment(data.get("document_id") or "document")
        attempt_id = _safe_filename_segment(data.get("posting_attempt_id") or "draft")
        resolved_filename = filename or (
            f"mijngeldzaken_import_{attempt_id}_{document_id}_{checksum[:12]}.csv"
        )

        export_dir = self.export_dir.resolve()
        export_dir.mkdir(parents=True, exist_ok=True)
        csv_path = export_dir / Path(resolved_filename).name

        descriptor, temporary_path = tempfile.mkstemp(
            prefix=".fab-mijngeldzaken-",
            suffix=".tmp",
            dir=str(export_dir),
        )
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(csv_bytes)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, csv_path)
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            if os.path.exists(temporary_path):
                os.remove(temporary_path)
            raise
        return str(csv_path)

    def _render_csv(self, data: Dict[str, Any]) -> str:
        columns = [str(column) for column in self.csv_template.get("columns") or MIJNGELDZAKEN_IMPORT_COLUMNS]
        mapping = self.csv_template.get("mapping") or {}
        delimiter = str(
            self.csv_template.get("delimiter")
            or self.config.get("mijngeldzaken_csv_delimiter")
            or ";"
        )
        if len(delimiter) != 1:
            raise ValueError("mijngeldzaken_csv_delimiter must be exactly one character")

        if mapping:
            row = {
                column: self._mapped_value(data, source_key)
                for column, source_key in mapping.items()
            }
        else:
            row = build_mijngeldzaken_import_row(
                data,
                self._map_category_to_mijngeldzaken(data.get("category")),
                default_account=str(self.config.get("mijngeldzaken_default_account") or "Huishouden"),
            )

        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(
            buffer,
            fieldnames=columns,
            delimiter=delimiter,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerow({column: row.get(column, "") for column in columns})
        return buffer.getvalue()

    def _mapped_value(self, data: Dict[str, Any], source_key: Any) -> Any:
        key = str(source_key or "")
        if key == "category":
            return self._map_category_to_mijngeldzaken(data.get("category"))
        return _nested_value(data, key.split("."))

    def _map_category_to_mijngeldzaken(self, category: Any) -> str:
        mapping = self.config.get("mijngeldzaken_category_mapping") or {}
        return str(mapping.get(category, category or "Overig"))

    def enter_data(self, categorized_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            csv_file_path = self._generate_csv(categorized_data)
            with open(csv_file_path, "rb") as handle:
                checksum = hashlib.sha256(handle.read()).hexdigest()
        except Exception as exc:
            return {
                "status": "failure",
                "message": f"MijnGeldzaken import artifact could not be prepared: {exc}",
                "requires_manual_review": True,
            }

        artifact = {
            "format": "csv",
            "path": csv_file_path,
            "filename": os.path.basename(csv_file_path),
            "sha256": checksum,
            "row_count": 1,
        }
        return {
            "status": "supervised_action_required",
            "message": (
                "MijnGeldzaken CSV prepared. Complete the import in a supervised "
                "user-owned session, then record the external submission in FAB."
            ),
            "artifact": artifact,
            "artifact_path": csv_file_path,
            "external_submission": "not_executed",
            "requires_supervision": True,
            "requires_manual_review": True,
            "credentials_used": False,
        }


def _nested_value(data: Dict[str, Any], path: Iterable[str]) -> Any:
    current: Any = data
    for part in path:
        if not part or not isinstance(current, dict):
            return ""
        current = current.get(part)
    return "" if current is None else current


def _safe_filename_segment(value: Any) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "").strip())
    return text.strip(".-")[:80] or "item"
