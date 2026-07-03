import hashlib
import mimetypes
import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional, Sequence, Set

from src.document_handling.source_identity import source_document_id
from src.operations.local_ledger import LocalOperationsLedger


DEFAULT_ALLOWED_EXTENSIONS = {
    ".csv",
    ".heic",
    ".jpeg",
    ".jpg",
    ".pdf",
    ".png",
    ".tif",
    ".tiff",
    ".txt",
}


class LocalFolderIntake:
    """Import document metadata from local or synced folders into the ledger."""

    def __init__(
        self,
        ledger: LocalOperationsLedger,
        allowed_extensions: Optional[Iterable[str]] = None,
        source: str = "local_folder",
    ):
        self.ledger = ledger
        self.allowed_extensions = _normalize_extensions(allowed_extensions)
        self.source = source

    def rescan(self, folders: Sequence[str]) -> Dict[str, Any]:
        roots = [_normalize_path(folder) for folder in folders if str(folder or "").strip()]
        summary: Dict[str, Any] = {
            "folders": roots,
            "allowedExtensions": sorted(self.allowed_extensions),
            "scanned": 0,
            "registered": 0,
            "duplicates": 0,
            "alreadyRegistered": 0,
            "skipped": [],
            "documents": [],
        }

        for root in roots:
            scan_started_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            if not os.path.isdir(root):
                summary["skipped"].append({"path": root, "reason": "folder_missing"})
                self.ledger.upsert_source_account({
                    "sourceType": self.source,
                    "sourceIdentifier": root,
                    "label": os.path.basename(root) or root,
                    "status": "missing",
                    "lastScanAt": scan_started_at,
                    "metadata": {
                        "path": root,
                        "reason": "folder_missing",
                        "allowedExtensions": sorted(self.allowed_extensions),
                    },
                })
                continue
            source_account_id = self.ledger.upsert_source_account({
                "sourceType": self.source,
                "sourceIdentifier": root,
                "label": os.path.basename(root) or root,
                "status": "ready",
                "lastScanAt": scan_started_at,
                "metadata": {
                    "path": root,
                    "allowedExtensions": sorted(self.allowed_extensions),
                },
            })
            root_summary = {
                "scanned": 0,
                "registered": 0,
                "duplicates": 0,
                "alreadyRegistered": 0,
            }
            for path in self._iter_document_paths(root):
                result = self._register_file(root, path, source_account_id)
                if result.get("skipped"):
                    summary["skipped"].append(result["skipped"])
                    continue
                summary["scanned"] += 1
                root_summary["scanned"] += 1
                status = result["status"]
                if status == "already_registered":
                    summary["alreadyRegistered"] += 1
                    root_summary["alreadyRegistered"] += 1
                else:
                    summary["registered"] += 1
                    root_summary["registered"] += 1
                    if status == "duplicate":
                        summary["duplicates"] += 1
                        root_summary["duplicates"] += 1
                summary["documents"].append(result["document"])
            self.ledger.upsert_source_account({
                "sourceType": self.source,
                "sourceIdentifier": root,
                "label": os.path.basename(root) or root,
                "status": "ready",
                "lastSeenAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                "lastScanAt": scan_started_at,
                "documentsSeen": root_summary["scanned"],
                "documentsImported": root_summary["registered"],
                "duplicatesDetected": root_summary["duplicates"],
                "metadata": {
                    "path": root,
                    "allowedExtensions": sorted(self.allowed_extensions),
                    **root_summary,
                },
            })

        self.ledger.record_audit_event({
            "action": "local_intake.rescan",
            "entityType": "folder_intake",
            "details": {
                "folders": roots,
                "scanned": summary["scanned"],
                "registered": summary["registered"],
                "duplicates": summary["duplicates"],
                "alreadyRegistered": summary["alreadyRegistered"],
                "skipped": len(summary["skipped"]),
            },
        })
        return summary

    def _iter_document_paths(self, root: str):
        for current_root, dir_names, file_names in os.walk(root, followlinks=False):
            dir_names[:] = [
                name
                for name in dir_names
                if not os.path.islink(os.path.join(current_root, name))
            ]
            for file_name in sorted(file_names):
                path = os.path.join(current_root, file_name)
                if os.path.islink(path):
                    continue
                extension = os.path.splitext(file_name)[1].lower()
                if "*" not in self.allowed_extensions and extension not in self.allowed_extensions:
                    continue
                yield path

    def _register_file(self, root: str, path: str, source_account_id: Optional[int] = None) -> Dict[str, Any]:
        try:
            stat = os.stat(path)
            content_hash = _sha256_file(path)
        except OSError as exc:
            return {"skipped": {"path": path, "reason": "read_error", "message": str(exc)}}

        mime_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
        original_filename = os.path.basename(path)
        modified_at = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
        source_document = {
            "local_path": path,
            "original_filename": original_filename,
            "mime_type": mime_type,
            "modified_time": modified_at,
            "size": stat.st_size,
        }
        source_id = source_document_id(source_document)
        existing = self.ledger.get_document_by_source(self.source, source_id) if source_id else None
        if existing:
            if source_account_id and not existing.get("source_account_id"):
                self.ledger.update_document(int(existing["id"]), {"sourceAccountId": source_account_id})
            return {
                "status": "already_registered",
                "document": {
                    "id": existing["id"],
                    "path": path,
                    "sourceAccountId": source_account_id or existing.get("source_account_id"),
                    "sourceDocumentId": source_id,
                    "status": existing["processing_status"],
                },
            }

        duplicate = self.ledger.find_document_by_fingerprint(
            content_hash,
            exclude_source_document_id=source_id,
        )
        duplicate_of_document_id = duplicate["id"] if duplicate else None
        processing_status = "needs_review" if duplicate_of_document_id else "imported"
        payload = {
            "sourceAccountId": source_account_id,
            "source": self.source,
            "sourceDocumentId": source_id,
            "originalFilename": original_filename,
            "mimeType": mime_type,
            "storagePath": path,
            "documentType": _document_type(path, mime_type),
            "processingStatus": processing_status,
            "duplicateFingerprint": content_hash,
            "duplicateOfDocumentId": duplicate_of_document_id,
            "metadata": {
                "contentSha256": content_hash,
                "folder": root,
                "relativePath": os.path.relpath(path, root),
                "sizeBytes": stat.st_size,
                "modifiedAt": modified_at,
                "intakeSource": self.source,
                "sourceAccountId": source_account_id,
                "sourceIdentifier": root,
            },
        }
        document_id = self.ledger.register_document(payload)

        if duplicate_of_document_id:
            duplicate_candidate_id = self.ledger.record_duplicate_candidate({
                "documentId": document_id,
                "candidateDocumentId": duplicate_of_document_id,
                "matchType": "exact_content_hash",
                "confidenceScore": 1.0,
                "status": "pending",
                "reason": "Exact content hash match during folder intake.",
                "evidence": {
                    "contentSha256": content_hash,
                    "sourceDocumentId": source_id,
                    "path": path,
                    "duplicateOfDocumentId": duplicate_of_document_id,
                    "source": self.source,
                },
            })
            self.ledger.create_review_item({
                "documentId": document_id,
                "reason": "duplicate_candidate",
                "details": f"Exact content match with document #{duplicate_of_document_id}.",
                "correctedData": {
                    "duplicateCandidateId": duplicate_candidate_id,
                    "duplicateOfDocumentId": duplicate_of_document_id,
                    "contentSha256": content_hash,
                    "sourceDocumentId": source_id,
                },
            })
            self.ledger.record_audit_event({
                "action": "local_intake.duplicate_candidate",
                "entityType": "bookkeeping_document",
                "entityId": str(document_id),
                "details": {
                    "duplicateCandidateId": duplicate_candidate_id,
                    "duplicateOfDocumentId": duplicate_of_document_id,
                    "contentSha256": content_hash,
                    "path": path,
                },
            })
            status = "duplicate"
        else:
            self.ledger.record_audit_event({
                "action": "local_intake.document_imported",
                "entityType": "bookkeeping_document",
                "entityId": str(document_id),
                "details": {
                    "contentSha256": content_hash,
                    "path": path,
                    "sourceDocumentId": source_id,
                },
            })
            status = "registered"

        return {
            "status": status,
            "document": {
                "id": document_id,
                "path": path,
                "sourceAccountId": source_account_id,
                "sourceDocumentId": source_id,
                "status": processing_status,
                "duplicateOfDocumentId": duplicate_of_document_id,
            },
        }


def _normalize_extensions(extensions: Optional[Iterable[str]]) -> Set[str]:
    if extensions is None:
        return set(DEFAULT_ALLOWED_EXTENSIONS)
    normalized = set()
    for extension in extensions:
        value = str(extension).strip().lower()
        if not value:
            continue
        if value == "*":
            normalized.add("*")
            continue
        normalized.add(value if value.startswith(".") else f".{value}")
    return normalized or set(DEFAULT_ALLOWED_EXTENSIONS)


def _normalize_path(path: str) -> str:
    return os.path.abspath(os.path.expandvars(os.path.expanduser(str(path).strip())))


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _document_type(path: str, mime_type: str) -> str:
    extension = os.path.splitext(path)[1].lower()
    if extension == ".pdf" or mime_type == "application/pdf":
        return "pdf"
    if mime_type.startswith("image/"):
        return "image"
    if extension == ".csv" or mime_type in {"text/csv", "application/csv"}:
        return "csv"
    if mime_type.startswith("text/"):
        return "text"
    return "unknown"
