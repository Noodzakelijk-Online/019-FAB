import os
import re
from typing import Any, Dict, Iterable, List, Optional

from src.operations.local_ledger import LocalOperationsLedger


class LocalDocumentGroupingService:
    """Create durable, reviewable document groups for scanner and manual flows."""

    def __init__(self, ledger: LocalOperationsLedger, config: Optional[Dict[str, Any]] = None):
        self.ledger = ledger
        self.config = config or {}

    def detect_scanner_groups(self, limit: int = 100) -> Dict[str, Any]:
        documents = self.ledger.list_documents(limit=limit)
        existing_groups = {
            group.get("group_key"): group
            for group in self.ledger.list_document_groups(limit=500)
        }
        buckets: Dict[str, List[Dict[str, Any]]] = {}
        for document in documents:
            key = _scanner_group_key(document)
            if not key or self._active_group_memberships(document):
                continue
            existing_group = existing_groups.get(key)
            if existing_group:
                continue
            buckets.setdefault(key, []).append(document)

        created_groups = []
        for key, grouped_documents in buckets.items():
            if len(grouped_documents) < 2:
                continue
            grouped_documents.sort(key=_scanner_sort_key)
            group_id = self.ledger.upsert_document_group({
                "groupKey": key,
                "groupType": "scanner_batch",
                "title": _group_title(grouped_documents),
                "status": "candidate",
                "primaryDocumentId": grouped_documents[0]["id"],
                "confidenceScore": _group_confidence(grouped_documents),
                "reason": "Sequential scanner-style filenames suggest these pages belong together.",
                "metadata": {
                    "source": "local_grouping.detect_scanner_groups",
                    "documentIds": [document["id"] for document in grouped_documents],
                    "filenames": [document.get("original_filename") for document in grouped_documents],
                },
            })
            for index, document in enumerate(grouped_documents):
                self.ledger.add_document_to_group(
                    group_id,
                    int(document["id"]),
                    {
                        "role": "primary" if index == 0 else "page",
                        "sortOrder": index,
                        "metadata": {"filename": document.get("original_filename")},
                    },
                )
            self._queue_group_review(group_id, grouped_documents)
            created_groups.append(self.ledger.get_document_group(group_id))
            self.ledger.record_audit_event({
                "action": "local_grouping.scanner_group_detected",
                "entityType": "document_group",
                "entityId": str(group_id),
                "details": {
                    "groupKey": key,
                    "documentIds": [document["id"] for document in grouped_documents],
                    "externalSubmission": "not_executed",
                },
            })

        return {
            "success": True,
            "status": "completed",
            "requestedDocuments": len(documents),
            "groupsCreated": len(created_groups),
            "groups": created_groups,
            "externalSubmission": "not_executed",
        }

    def merge_documents(
        self,
        document_ids: Iterable[int],
        title: Optional[str] = None,
        reason: Optional[str] = None,
        actor: str = "api",
    ) -> Dict[str, Any]:
        parsed_ids = _unique_ints(document_ids)
        if len(parsed_ids) < 2:
            return {
                "success": False,
                "status": "invalid_request",
                "error": "At least two documentIds are required to create a group.",
                "externalSubmission": "not_executed",
            }
        documents = [self.ledger.get_document(document_id) for document_id in parsed_ids]
        if any(document is None for document in documents):
            return {
                "success": False,
                "status": "not_found",
                "error": "One or more documents were not found.",
                "externalSubmission": "not_executed",
            }
        group_key = "manual:" + "-".join(str(document_id) for document_id in parsed_ids)
        group_id = self.ledger.upsert_document_group({
            "groupKey": group_key,
            "groupType": "manual_merge",
            "title": title or _group_title(documents),
            "status": "needs_review",
            "primaryDocumentId": parsed_ids[0],
            "confidenceScore": 1.0,
            "reason": reason or "Documents manually grouped for review.",
            "metadata": {
                "source": "local_grouping.merge_documents",
                "actor": actor,
                "documentIds": parsed_ids,
            },
        })
        for index, document_id in enumerate(parsed_ids):
            self.ledger.add_document_to_group(
                group_id,
                document_id,
                {
                    "role": "primary" if index == 0 else "page",
                    "sortOrder": index,
                    "metadata": {"actor": actor},
                },
            )
        self._queue_group_review(group_id, [document for document in documents if document])
        self.ledger.record_audit_event({
            "action": "local_grouping.documents_merged_for_review",
            "entityType": "document_group",
            "entityId": str(group_id),
            "details": {
                "documentIds": parsed_ids,
                "actor": actor,
                "externalSubmission": "not_executed",
            },
        })
        return {
            "success": True,
            "status": "needs_review",
            "groupId": group_id,
            "documentGroup": self.ledger.get_document_group(group_id),
            "externalSubmission": "not_executed",
        }

    def split_document_from_group(
        self,
        group_id: int,
        document_id: int,
        reason: Optional[str] = None,
        actor: str = "api",
    ) -> Dict[str, Any]:
        group = self.ledger.get_document_group(group_id)
        if not group:
            return {"success": False, "status": "not_found", "error": "Document group not found."}
        removed = self.ledger.remove_document_from_group(group_id, document_id, reason or "Removed from group.")
        if not removed:
            return {"success": False, "status": "not_found", "error": "Document is not a group member."}
        refreshed = self.ledger.get_document_group(group_id)
        active_members = [member for member in refreshed.get("members", []) if member.get("status") == "active"]
        if len(active_members) < 2:
            self.ledger.update_document_group_status(group_id, "split", reason or "Group split below two active documents.")
        else:
            self.ledger.update_document_group_status(group_id, "needs_review", reason or "Group membership changed.")
        self.ledger.record_audit_event({
            "action": "local_grouping.document_split_from_group",
            "entityType": "document_group",
            "entityId": str(group_id),
            "details": {
                "documentId": document_id,
                "actor": actor,
                "reason": reason,
                "externalSubmission": "not_executed",
            },
        })
        return {
            "success": True,
            "status": "split" if len(active_members) < 2 else "needs_review",
            "groupId": group_id,
            "documentGroup": self.ledger.get_document_group(group_id),
            "externalSubmission": "not_executed",
        }

    def _queue_group_review(self, group_id: int, documents: List[Dict[str, Any]]) -> None:
        for document in documents:
            open_items = [
                item
                for item in self.ledger.list_review_items(document_id=int(document["id"]), status=("pending", "in_review"))
                if item.get("reason") == "document_group_candidate"
            ]
            if open_items:
                continue
            self.ledger.create_review_item({
                "documentId": int(document["id"]),
                "reason": "document_group_candidate",
                "details": f"Document may belong to group #{group_id}. Confirm merge/split before routing.",
                "correctedData": {
                    "documentGroupId": group_id,
                    "groupMemberDocumentIds": [item["id"] for item in documents],
                },
            })

    @staticmethod
    def _active_group_memberships(document: Dict[str, Any]) -> bool:
        return any(
            member.get("status") == "active"
            for group in document.get("document_groups") or []
            for member in group.get("members") or []
            if member.get("document_id") == document.get("id")
        )


def _scanner_group_key(document: Dict[str, Any]) -> Optional[str]:
    filename = str(document.get("original_filename") or "")
    stem, extension = os.path.splitext(filename.lower())
    if extension not in {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".heic", ".txt"}:
        return None
    patterns = [
        r"^(?P<base>.+?)(?:[_\-\s]?(?:page|pagina|p|scan)[_\-\s]?(?P<num>\d{1,3}))$",
        r"^(?P<base>.+?)[_\-\s](?P<num>\d{1,3})$",
    ]
    for pattern in patterns:
        match = re.match(pattern, stem, flags=re.IGNORECASE)
        if match:
            base = re.sub(r"[^a-z0-9]+", "-", match.group("base")).strip("-")
            if base:
                return "|".join([
                    str(document.get("source") or "unknown"),
                    str(document.get("source_account_id") or ""),
                    base,
                ])
    return None


def _scanner_sort_key(document: Dict[str, Any]) -> tuple:
    filename = str(document.get("original_filename") or "")
    numbers = re.findall(r"\d+", os.path.splitext(filename)[0])
    page = int(numbers[-1]) if numbers else 0
    return (page, filename)


def _group_title(documents: List[Dict[str, Any]]) -> str:
    first_name = documents[0].get("original_filename") if documents else "Document group"
    return f"{first_name} + {max(0, len(documents) - 1)} related page(s)"


def _group_confidence(documents: List[Dict[str, Any]]) -> float:
    if len(documents) >= 3:
        return 0.92
    return 0.82


def _unique_ints(values: Iterable[int]) -> List[int]:
    result: List[int] = []
    for value in values:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            continue
        if parsed not in result:
            result.append(parsed)
    return result
