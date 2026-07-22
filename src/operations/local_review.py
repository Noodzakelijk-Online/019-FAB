from datetime import date
from typing import Any, Dict, Optional

from src.operations.local_bookkeeping_records import LocalBookkeepingRecordService
from src.operations.local_ledger import LocalOperationsLedger
from src.operations.local_reconciliation import LocalReconciliationService


APPLIED_REVIEW_STATUSES = {"approved", "resolved"}
OPEN_REVIEW_STATUSES = {"pending", "in_review"}
RECONCILIATION_REVIEW_REASONS = {"reconciliation_candidate", "missing_receipt", "unmatched_document"}
CATEGORY_REVIEW_REASONS = {"low_confidence_categorization", "manual_review_category"}


class LocalReviewService:
    """Apply manual review decisions to documents and local learning records."""

    def __init__(self, ledger: LocalOperationsLedger):
        self.ledger = ledger

    def resolve_review_item(
        self,
        review_item_id: int,
        status: str = "resolved",
        resolution: Optional[str] = None,
        corrections: Optional[Dict[str, Any]] = None,
        learn_rule: bool = True,
    ) -> Dict[str, Any]:
        review_item = self.ledger.get_review_item(review_item_id)
        if not review_item:
            return {"success": False, "error": "Review item not found", "status": "not_found"}
        if review_item.get("status") not in OPEN_REVIEW_STATUSES:
            return {
                "success": False,
                "error": "Review item is already closed",
                "status": "already_resolved",
                "reviewItemId": review_item_id,
            }

        document = self.ledger.get_document(int(review_item["document_id"])) if review_item.get("document_id") else None
        normalized_corrections = normalize_corrections(corrections or {})
        original_data = _document_snapshot(document) if document else {}
        document_update = {}
        rule_id = None
        reconciliation_resolution = None
        duplicate_candidate_resolution = None
        duplicate_decision = None

        if document:
            document_update = _build_document_update(document, normalized_corrections)
            duplicate_decision = _duplicate_decision(review_item, status, normalized_corrections)
            if duplicate_decision == "accepted":
                document_update["processingStatus"] = "duplicate"
                duplicate_candidate_resolution = self.ledger.resolve_duplicate_candidates_for_document(
                    int(document["id"]),
                    "approved",
                    resolution or "Duplicate candidate approved from manual review.",
                )
            elif duplicate_decision == "rejected":
                self.ledger.clear_document_duplicate(int(document["id"]))
                document_update["processingStatus"] = "needs_review"
                duplicate_candidate_resolution = self.ledger.resolve_duplicate_candidates_for_document(
                    int(document["id"]),
                    "rejected",
                    resolution or "Duplicate candidate rejected from manual review.",
                )

            if status in APPLIED_REVIEW_STATUSES and document_update.get("processingStatus") is None:
                document_update["processingStatus"] = "needs_review"

            if document_update:
                self.ledger.update_document(int(document["id"]), document_update)

        correction_payload = {
            "reviewItemId": review_item_id,
            "documentId": review_item.get("document_id"),
            "originalData": original_data,
            "correctedData": normalized_corrections,
            "status": status,
        }
        correction_id = self.ledger.record_review_correction(correction_payload)
        self.ledger.resolve_review_item(
            review_item_id,
            status=status,
            resolution=resolution,
            corrected_data={
                "corrections": normalized_corrections,
                "correctionId": correction_id,
            },
        )

        updated_document = self.ledger.get_document(int(review_item["document_id"])) if review_item.get("document_id") else None
        superseded_review_ids = self._resolve_superseded_document_reviews(
            review_item,
            status,
            normalized_corrections,
            updated_document,
        )
        updated_document = self.ledger.get_document(int(review_item["document_id"])) if review_item.get("document_id") else None
        remaining_review_items = [
            item
            for item in (updated_document or {}).get("review_items") or []
            if item.get("status") in OPEN_REVIEW_STATUSES
        ]
        final_processing_status = self._final_processing_status(
            review_item,
            status,
            duplicate_decision,
            remaining_review_items,
        )
        if updated_document and updated_document.get("processing_status") != final_processing_status:
            self.ledger.update_document(int(updated_document["id"]), {"processingStatus": final_processing_status})
            updated_document = self.ledger.get_document(int(updated_document["id"]))
        if learn_rule and status in APPLIED_REVIEW_STATUSES and updated_document:
            rule_id = self._learn_vendor_category_rule(updated_document, review_item_id, correction_id)

        if review_item.get("reason") in RECONCILIATION_REVIEW_REASONS:
            reconciliation_resolution = self._resolve_reconciliation_evidence(
                review_item,
                status,
                resolution,
            )

        bookkeeping_record = None
        if review_item.get("document_id"):
            bookkeeping_record = LocalBookkeepingRecordService(self.ledger).upsert_from_document(
                int(review_item["document_id"])
            )

        self.ledger.record_audit_event({
            "action": "local_review.review_item.resolve",
            "entityType": "review_item",
            "entityId": str(review_item_id),
            "details": {
                "status": status,
                "resolution": resolution,
                "documentId": review_item.get("document_id"),
                "correctionId": correction_id,
                "ruleId": rule_id,
                "reconciliationResolution": reconciliation_resolution,
                "duplicateCandidatesResolved": duplicate_candidate_resolution,
                "supersededReviewItemIds": superseded_review_ids,
                "remainingReviewItemIds": [int(item["id"]) for item in remaining_review_items],
                "processingStatus": final_processing_status,
                "bookkeepingRecordId": bookkeeping_record.get("recordId") if bookkeeping_record else None,
                "corrections": normalized_corrections,
            },
        })
        if normalized_corrections:
            self.ledger.record_audit_event({
                "action": "local_review.correction_applied",
                "entityType": "bookkeeping_document",
                "entityId": str(review_item.get("document_id")),
                "details": {
                    "reviewItemId": review_item_id,
                    "correctionId": correction_id,
                    "before": original_data,
                    "after": normalized_corrections,
                },
            })

        return {
            "success": True,
            "reviewItemId": review_item_id,
            "documentId": review_item.get("document_id"),
            "status": status,
            "correctionId": correction_id,
            "ruleId": rule_id,
            "reconciliationResolution": reconciliation_resolution,
            "duplicateCandidatesResolved": duplicate_candidate_resolution,
            "supersededReviewItemIds": superseded_review_ids,
            "remainingReviewItems": remaining_review_items,
            "processingStatus": final_processing_status,
            "bookkeepingRecordId": bookkeeping_record.get("recordId") if bookkeeping_record else None,
            "corrections": normalized_corrections,
        }

    def _resolve_superseded_document_reviews(
        self,
        review_item: Dict[str, Any],
        status: str,
        corrections: Dict[str, Any],
        document: Optional[Dict[str, Any]],
    ) -> list:
        if not document or status not in APPLIED_REVIEW_STATUSES:
            return []
        duplicate_decision = _duplicate_decision(review_item, status, corrections)
        reasons = set()
        if duplicate_decision == "accepted":
            reasons = {
                str(item.get("reason") or "")
                for item in document.get("review_items") or []
                if item.get("status") in OPEN_REVIEW_STATUSES
            }
        else:
            category = str(document.get("category") or "").strip().lower()
            if category and category not in {"manual review", "uncategorized"}:
                reasons.update(CATEGORY_REVIEW_REASONS)
            if _has_valid_required_fields(document):
                reasons.add("validation_failed")

        resolved_ids = []
        for item in document.get("review_items") or []:
            if item.get("status") not in OPEN_REVIEW_STATUSES:
                continue
            if str(item.get("reason") or "") not in reasons:
                continue
            item_id = int(item["id"])
            self.ledger.resolve_review_item(
                item_id,
                status="resolved",
                resolution=f"Superseded by approved review item #{review_item['id']}.",
                corrected_data={
                    "supersededByReviewItemId": int(review_item["id"]),
                    "appliedCorrections": corrections,
                },
            )
            resolved_ids.append(item_id)
        return resolved_ids

    @staticmethod
    def _final_processing_status(
        review_item: Dict[str, Any],
        status: str,
        duplicate_decision: Optional[str],
        remaining_review_items: list,
    ) -> str:
        if duplicate_decision == "accepted":
            return "duplicate"
        if remaining_review_items:
            return "needs_review"
        if duplicate_decision == "rejected":
            return "reviewed"
        if status in APPLIED_REVIEW_STATUSES:
            return "reviewed"
        return "needs_review"

    def _learn_vendor_category_rule(
        self,
        document: Dict[str, Any],
        review_item_id: int,
        correction_id: int,
    ) -> Optional[int]:
        vendor_name = str(document.get("vendor_name") or "").strip()
        category = str(document.get("category") or "").strip()
        if not vendor_name or not category or category.lower() in {"manual review", "uncategorized"}:
            return None
        rule_id = self.ledger.upsert_vendor_category_rule({
            "vendorName": vendor_name,
            "category": category,
            "targetSystem": _target_system(document),
            "confidenceScore": 1.0,
            "status": "suggested",
            "sourceDocumentId": document.get("source_document_id"),
            "metadata": {
                "source": "manual_review_correction",
                "documentId": document.get("id"),
                "reviewItemId": review_item_id,
                "correctionId": correction_id,
            },
        })
        self.ledger.record_audit_event({
            "action": "local_review.vendor_category_rule.suggested",
            "entityType": "vendor_category_rule",
            "entityId": str(rule_id),
            "details": {
                "vendorName": vendor_name,
                "category": category,
                "documentId": document.get("id"),
                "reviewItemId": review_item_id,
            },
        })
        return rule_id

    def _resolve_reconciliation_evidence(
        self,
        review_item: Dict[str, Any],
        review_status: str,
        resolution: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        reconciliation_match_id = _reconciliation_match_id(review_item)
        if reconciliation_match_id is None:
            return None
        reconciliation_status = _reconciliation_status_for_review(
            str(review_item.get("reason") or ""),
            review_status,
        )
        result = LocalReconciliationService(self.ledger).resolve_match(
            reconciliation_match_id,
            reconciliation_status,
            resolution or f"Review item #{review_item.get('id')} resolved as {review_status}.",
        )
        return {
            "reconciliationMatchId": reconciliation_match_id,
            "requestedReviewStatus": review_status,
            "appliedReconciliationStatus": reconciliation_status,
            "success": bool(result.get("success")),
            "status": result.get("status"),
        }


def normalize_corrections(corrections: Dict[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    mapping = {
        "vendor_name": "vendorName",
        "vendorName": "vendorName",
        "category": "category",
        "transaction_date": "transactionDate",
        "transactionDate": "transactionDate",
        "total_amount": "totalAmount",
        "totalAmount": "totalAmount",
        "vat_amount": "vatAmount",
        "vatAmount": "vatAmount",
        "target_system": "targetSystem",
        "targetSystem": "targetSystem",
        "duplicate_of_document_id": "duplicateOfDocumentId",
        "duplicateOfDocumentId": "duplicateOfDocumentId",
    }
    for key, value in corrections.items():
        mapped = mapping.get(key)
        if not mapped or value in (None, ""):
            continue
        if mapped in {"totalAmount", "vatAmount"}:
            parsed = _float(value)
            if parsed is not None:
                result[mapped] = parsed
            continue
        if mapped == "duplicateOfDocumentId":
            parsed_id = _int(value)
            if parsed_id is not None:
                result[mapped] = parsed_id
            continue
        result[mapped] = str(value).strip()
    return result


def _build_document_update(document: Dict[str, Any], corrections: Dict[str, Any]) -> Dict[str, Any]:
    extracted_data = dict(document.get("extracted_data") or {})
    metadata = dict(document.get("metadata") or {})
    update: Dict[str, Any] = {}

    if "vendorName" in corrections:
        update["vendorName"] = corrections["vendorName"]
        extracted_data["vendor_name"] = corrections["vendorName"]
    if "category" in corrections:
        update["category"] = corrections["category"]
    if "transactionDate" in corrections:
        update["transactionDate"] = corrections["transactionDate"]
        extracted_data["transaction_date"] = corrections["transactionDate"]
    if "totalAmount" in corrections:
        update["totalAmount"] = corrections["totalAmount"]
        extracted_data["total_amount"] = corrections["totalAmount"]
    if "vatAmount" in corrections:
        update["vatAmount"] = corrections["vatAmount"]
        extracted_data["vat_amount"] = corrections["vatAmount"]
    if "duplicateOfDocumentId" in corrections:
        update["duplicateOfDocumentId"] = corrections["duplicateOfDocumentId"]
    if "targetSystem" in corrections:
        metadata["targetSystem"] = corrections["targetSystem"]

    if corrections:
        extracted_data.setdefault("manual_corrections", {}).update(corrections)
        metadata.setdefault("review", {})["lastCorrections"] = corrections
        update["extractedData"] = extracted_data
        update["metadata"] = metadata
        update["confidenceScore"] = 1.0
    return update


def _duplicate_decision(review_item: Dict[str, Any], status: str, corrections: Dict[str, Any]) -> Optional[str]:
    if review_item.get("reason") != "duplicate_candidate":
        return None
    if status == "approved" or corrections.get("duplicateOfDocumentId"):
        return "accepted"
    if status == "rejected":
        return "rejected"
    return None


def _document_snapshot(document: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not document:
        return {}
    return {
        "vendorName": document.get("vendor_name"),
        "category": document.get("category"),
        "transactionDate": document.get("transaction_date"),
        "totalAmount": document.get("total_amount"),
        "vatAmount": document.get("vat_amount"),
        "processingStatus": document.get("processing_status"),
        "duplicateOfDocumentId": document.get("duplicate_of_document_id"),
        "extractedData": document.get("extracted_data"),
    }


def _has_valid_required_fields(document: Dict[str, Any]) -> bool:
    vendor_name = str(document.get("vendor_name") or "").strip()
    category = str(document.get("category") or "").strip().lower()
    transaction_date = str(document.get("transaction_date") or "").strip()
    try:
        date.fromisoformat(transaction_date)
    except ValueError:
        return False
    return bool(
        vendor_name
        and category
        and category not in {"manual review", "uncategorized"}
        and _float(document.get("total_amount")) is not None
    )


def _target_system(document: Dict[str, Any]) -> str:
    metadata = document.get("metadata") or {}
    return str(metadata.get("targetSystem") or metadata.get("target_system") or "none")


def _reconciliation_match_id(review_item: Dict[str, Any]) -> Optional[int]:
    corrected_data = review_item.get("corrected_data") or {}
    value = corrected_data.get("reconciliationMatchId") or corrected_data.get("reconciliation_match_id")
    return _int(value)


def _reconciliation_status_for_review(reason: str, review_status: str) -> str:
    if review_status == "ignored":
        return "ignored"
    if reason == "reconciliation_candidate":
        if review_status == "approved":
            return "approved"
        if review_status == "rejected":
            return "rejected"
        return "resolved"
    if reason == "missing_receipt":
        if review_status == "rejected":
            return "ignored"
        return "resolved"
    if reason == "unmatched_document":
        if review_status == "rejected":
            return "ignored"
        return "resolved"
    return "resolved"


def _float(value: Any) -> Optional[float]:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
