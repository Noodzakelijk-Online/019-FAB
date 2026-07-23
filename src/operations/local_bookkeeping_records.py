from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.document_processors.document_type_classifier import is_non_posting_document_type
from src.operations.local_ledger import LocalOperationsLedger
from src.operations.local_targets import resolve_document_target_system


BOOKKEEPING_RECORD_RESOLUTION_STATUSES = {"approved", "rejected", "resolved", "ignored", "needs_review"}
OPEN_REVIEW_STATUSES = {"pending", "in_review"}
READY_DOCUMENT_STATUSES = {"processed", "reviewed", "validated", "ready_to_route"}
EXPORT_PREPARED_STATUSES = {"draft_prepared", "needs_confirmation", "queued"}
MANUAL_REVIEW_CATEGORIES = {"", "manual review", "uncategorized", "unknown"}
PRESERVED_EXPORT_STATUSES = {
    "draft_prepared",
    "needs_confirmation",
    "queued",
    "approved_not_submitted",
    "submitted",
    "confirmed",
}


class LocalBookkeepingRecordService:
    """Maintain FAB's normalized financial record beside raw document evidence."""

    def __init__(self, ledger: LocalOperationsLedger, config: Optional[Dict[str, Any]] = None):
        self.ledger = ledger
        self.config = config or {}
        self.review_confidence_threshold = _float_config(
            self.config,
            "fab_local_review_confidence_threshold",
            "operations_local_review_confidence_threshold",
            "categorization_review_confidence_threshold",
            "operations_categorization_review_confidence_threshold",
            "ml_confidence_threshold",
            default=0.7,
        )

    def upsert_from_document(self, document_id: int, status: Optional[str] = None) -> Dict[str, Any]:
        document = self.ledger.get_document(document_id)
        if not document:
            return {"success": False, "status": "not_found", "error": "Document not found"}

        payload = self._document_record_payload(document, status=status)
        record_id = self.ledger.upsert_bookkeeping_record(payload)
        if payload.get("recordType") == "supporting_document":
            self.ledger.clear_bookkeeping_record_financial_values(record_id)
        line_items = _document_line_items(document, payload)
        self.ledger.replace_bookkeeping_record_line_items(record_id, line_items)
        return {
            "success": True,
            "recordId": record_id,
            "documentId": document_id,
            "status": payload["status"],
            "exportStatus": payload["exportStatus"],
            "reconciliationStatus": payload["reconciliationStatus"],
            "reviewRequired": bool(payload["reviewRequired"]),
            "lineItemCount": len(line_items),
        }

    def upsert_from_bank_transaction(
        self,
        bank_transaction_id: int,
        status: Optional[str] = None,
        reconciliation_status: Optional[str] = None,
    ) -> Dict[str, Any]:
        transaction = self.ledger.get_bank_transaction(bank_transaction_id)
        if not transaction:
            return {"success": False, "status": "not_found", "error": "Bank transaction not found"}

        payload = self._bank_transaction_record_payload(
            transaction,
            status=status,
            reconciliation_status=reconciliation_status,
        )
        existing_record = self.ledger.get_bookkeeping_record_by_bank_transaction(bank_transaction_id)
        record_id = self.ledger.upsert_bookkeeping_record(payload)
        line_items = _bank_transaction_line_items(transaction, payload)
        self.ledger.replace_bookkeeping_record_line_items(record_id, line_items)
        applied_rule = payload.get("metadata", {}).get("appliedVendorCategoryRule")
        existing_rule = (existing_record or {}).get("metadata", {}).get("appliedVendorCategoryRule")
        if applied_rule and applied_rule != existing_rule:
            self.ledger.record_audit_event({
                "action": "local_bookkeeping_records.vendor_category_rule.applied",
                "entityType": "bank_transaction",
                "entityId": str(bank_transaction_id),
                "details": {
                    "bookkeepingRecordId": record_id,
                    "vendorName": payload.get("vendorName"),
                    "category": payload.get("category"),
                    "appliedVendorCategoryRule": applied_rule,
                },
            })
        return {
            "success": True,
            "recordId": record_id,
            "bankTransactionId": bank_transaction_id,
            "status": payload["status"],
            "reconciliationStatus": payload["reconciliationStatus"],
            "reviewRequired": bool(payload["reviewRequired"]),
            "lineItemCount": len(line_items),
        }

    def refresh_bank_transactions(self, limit: int = 100) -> Dict[str, Any]:
        transactions = self.ledger.list_bank_transactions(limit=limit)
        summary = {
            "requested": len(transactions),
            "updated": 0,
            "failed": 0,
            "ruleApplied": 0,
            "records": [],
        }
        for transaction in transactions:
            result = self.upsert_from_bank_transaction(int(transaction["id"]))
            if result.get("success"):
                summary["updated"] += 1
                record = self.ledger.get_bookkeeping_record(int(result["recordId"])) or {}
                if (record.get("metadata") or {}).get("appliedVendorCategoryRule"):
                    summary["ruleApplied"] += 1
            else:
                summary["failed"] += 1
            summary["records"].append(result)
        self.ledger.record_audit_event({
            "action": "local_bookkeeping_records.bank_transactions_refreshed",
            "entityType": "bookkeeping_record",
            "details": {
                "requested": summary["requested"],
                "updated": summary["updated"],
                "failed": summary["failed"],
                "ruleApplied": summary["ruleApplied"],
                "externalSubmission": "not_executed",
            },
        })
        return summary

    def refresh_documents(self, limit: int = 100) -> Dict[str, Any]:
        documents = self.ledger.list_documents(limit=limit)
        summary = {"requested": len(documents), "updated": 0, "failed": 0, "records": []}
        for document in documents:
            result = self.upsert_from_document(int(document["id"]))
            if result.get("success"):
                summary["updated"] += 1
            else:
                summary["failed"] += 1
            summary["records"].append(result)
        return summary

    def resolve_record(
        self,
        record_id: int,
        status: str = "resolved",
        resolution: Optional[str] = None,
        corrections: Optional[Dict[str, Any]] = None,
        actor: str = "fab_local_api",
    ) -> Dict[str, Any]:
        status = str(status or "resolved").strip().lower()
        if status not in BOOKKEEPING_RECORD_RESOLUTION_STATUSES:
            raise ValueError(f"Unsupported bookkeeping record resolution status: {status}")

        record = self.ledger.get_bookkeeping_record(record_id)
        if not record:
            return {
                "success": False,
                "status": "not_found",
                "error": "Bookkeeping record not found",
                "externalSubmission": "not_executed",
            }

        corrected_fields = _record_corrections(corrections or {})
        next_status = _record_status_for_resolution(status)
        next_review_required = status == "needs_review"
        next_export_status = _export_status_for_resolution(status, record.get("export_status"))
        metadata = dict(record.get("metadata") or {})
        resolved_at = _utc_now()
        history_entry = {
            "resolutionStatus": status,
            "fromStatus": record.get("status"),
            "toStatus": next_status,
            "fromExportStatus": record.get("export_status"),
            "toExportStatus": next_export_status,
            "fromReviewRequired": bool(record.get("review_required")),
            "toReviewRequired": next_review_required,
            "correctedFields": sorted(corrected_fields.keys()),
            "resolution": resolution,
            "actor": actor,
            "resolvedAt": resolved_at,
        }
        history = list(metadata.get("resolutionHistory") or [])
        history.append(history_entry)
        metadata["resolutionHistory"] = history
        metadata["lastResolution"] = history_entry
        metadata["externalSubmission"] = "not_executed"

        update: Dict[str, Any] = {
            "status": next_status,
            "reviewRequired": next_review_required,
            "exportStatus": next_export_status,
            "metadata": metadata,
        }
        update.update(corrected_fields)
        self.ledger.update_bookkeeping_record(record_id, update)

        updated = self.ledger.get_bookkeeping_record(record_id) or {}
        self._refresh_line_items_after_resolution(updated, corrected_fields)
        updated = self.ledger.get_bookkeeping_record(record_id) or updated
        self.ledger.record_audit_event({
            "action": "local_bookkeeping_records.record.resolve",
            "entityType": "bookkeeping_record",
            "entityId": str(record_id),
            "details": {
                "resolutionStatus": status,
                "fromStatus": record.get("status"),
                "toStatus": next_status,
                "fromExportStatus": record.get("export_status"),
                "toExportStatus": next_export_status,
                "correctedFields": sorted(corrected_fields.keys()),
                "actor": actor,
                "resolution": resolution,
                "externalSubmission": "not_executed",
            },
        })
        return {
            "success": True,
            "status": next_status,
            "resolutionStatus": status,
            "recordId": record_id,
            "bookkeepingRecord": updated,
            "correctedFields": sorted(corrected_fields.keys()),
            "externalSubmission": "not_executed",
        }

    def _refresh_line_items_after_resolution(
        self,
        record: Dict[str, Any],
        corrected_fields: Dict[str, Any],
    ) -> None:
        if not corrected_fields:
            return
        line_items = list(record.get("line_items") or [])
        if not line_items:
            line_items = [{
                "description": record.get("description"),
                "amount": record.get("amount"),
                "taxAmount": record.get("vat_amount"),
                "category": record.get("category"),
                "accountName": record.get("target_account"),
                "source": "record_resolution",
                "metadata": {"fallback": "record_resolution"},
            }]
        patched = []
        single_line = len(line_items) == 1
        for item in line_items:
            next_item = dict(item)
            if "category" in corrected_fields:
                next_item["category"] = corrected_fields["category"]
            if "targetAccount" in corrected_fields:
                next_item["accountName"] = corrected_fields["targetAccount"]
            if "description" in corrected_fields:
                next_item["description"] = corrected_fields["description"]
            if single_line and "amount" in corrected_fields:
                next_item["amount"] = corrected_fields["amount"]
            if single_line and "vatAmount" in corrected_fields:
                next_item["taxAmount"] = corrected_fields["vatAmount"]
            metadata = dict(next_item.get("metadata") or {})
            metadata["latestRecordResolution"] = {
                "correctedFields": sorted(corrected_fields.keys()),
                "resolvedAt": _utc_now(),
            }
            next_item["metadata"] = metadata
            patched.append(next_item)
        self.ledger.replace_bookkeeping_record_line_items(int(record["id"]), patched)

    def record_export_state(
        self,
        document_id: int,
        export_status: str,
        status: Optional[str] = None,
        routing_attempt_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        result = self.upsert_from_document(document_id, status=status)
        if not result.get("success"):
            return result
        record = self.ledger.get_bookkeeping_record(int(result["recordId"])) or {}
        metadata = dict(record.get("metadata") or {})
        metadata["latestExport"] = {
            "status": export_status,
            "routingAttemptId": routing_attempt_id,
            "details": details or {},
        }
        update: Dict[str, Any] = {
            "exportStatus": export_status,
            "metadata": metadata,
        }
        if status:
            update["status"] = status
        self.ledger.update_bookkeeping_record(int(result["recordId"]), update)
        result["exportStatus"] = export_status
        if status:
            result["status"] = status
        return result

    def record_reconciliation_state(
        self,
        document_id: int,
        reconciliation_status: str,
        status: Optional[str] = None,
        reconciliation_match_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        result = self.upsert_from_document(document_id, status=status)
        if not result.get("success"):
            return result
        record = self.ledger.get_bookkeeping_record(int(result["recordId"])) or {}
        metadata = dict(record.get("metadata") or {})
        metadata["latestReconciliation"] = {
            "status": reconciliation_status,
            "reconciliationMatchId": reconciliation_match_id,
        }
        update: Dict[str, Any] = {
            "reconciliationStatus": reconciliation_status,
            "metadata": metadata,
        }
        if status:
            update["status"] = status
        self.ledger.update_bookkeeping_record(int(result["recordId"]), update)
        result["reconciliationStatus"] = reconciliation_status
        if status:
            result["status"] = status
        return result

    def _document_record_payload(
        self,
        document: Dict[str, Any],
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        extracted = dict(document.get("extracted_data") or {})
        metadata = dict(document.get("metadata") or {})
        document_type = str(_first_present(document.get("document_type"), extracted.get("document_type"), "") or "").lower()
        non_posting = is_non_posting_document_type(document_type)
        vendor_name = _first_present(document.get("vendor_name"), extracted.get("vendor_name"))
        category = _first_present(document.get("category"), extracted.get("category"))
        record_date = _first_present(document.get("transaction_date"), extracted.get("transaction_date"))
        amount = _float(_first_present(document.get("total_amount"), extracted.get("total_amount"), extracted.get("amount")))
        vat_amount = _float(_first_present(document.get("vat_amount"), extracted.get("vat_amount")))
        currency = str(_first_present(extracted.get("currency"), metadata.get("currency"), "EUR") or "EUR").upper()
        confidence = _float(document.get("confidence_score"))
        target_account = _first_present(
            metadata.get("targetAccount"),
            metadata.get("target_account"),
            extracted.get("target_account"),
        )
        description = _first_present(extracted.get("description"), document.get("original_filename"))
        open_reviews = [
            item for item in document.get("review_items") or []
            if item.get("status") in OPEN_REVIEW_STATUSES
        ]
        missing_fields = [] if non_posting else _missing_document_fields(
            vendor_name=vendor_name,
            category=category,
            record_date=record_date,
            amount=amount,
        )
        review_required = self._document_review_required(
            document,
            category=category,
            confidence=confidence,
            open_reviews=open_reviews,
            missing_fields=missing_fields,
        )
        latest_routing = _latest_routing_attempt(document)
        if non_posting and not review_required:
            record_status = status or "supporting_evidence"
        else:
            record_status = status or _record_status_for_document(
                str(document.get("processing_status") or "draft"),
                review_required=review_required,
            )
        export_status = "not_applicable" if non_posting else _export_status_for_document(
            document,
            latest_routing,
            review_required=review_required,
        )
        line_items = [] if non_posting else _document_line_items_from_values(
            extracted=extracted,
            category=category,
            target_account=target_account,
            amount=amount,
            vat_amount=vat_amount,
            description=description,
            confidence=confidence,
        )
        export_readiness = (
            {
                "lineItemCount": 0,
                "hasTaxEvidence": False,
                "missingAccountMapping": [],
                "missingTaxCode": [],
                "postingEligible": False,
                "readyForWaveDraft": False,
            }
            if non_posting
            else _line_item_export_readiness(line_items, vat_amount)
        )
        return {
            "documentId": document.get("id"),
            "sourceType": "document",
            "recordType": "supporting_document" if non_posting else _record_type(document, extracted, amount),
            "status": record_status,
            "targetSystem": _target_system(document, extracted),
            "targetAccount": target_account,
            "vendorName": vendor_name,
            "category": category,
            "recordDate": record_date,
            "amount": None if non_posting else amount,
            "vatAmount": None if non_posting else vat_amount,
            "currency": currency,
            "description": description,
            "confidenceScore": confidence,
            "reviewRequired": review_required,
            "exportStatus": export_status,
            "reconciliationStatus": document.get("reconciliation_status") or "not_started",
            "metadata": {
                "source": document.get("source"),
                "sourceDocumentId": document.get("source_document_id"),
                "originalFilename": document.get("original_filename"),
                "documentType": document.get("document_type"),
                "nonPostingDocumentType": non_posting,
                "evidenceAmount": amount if non_posting else None,
                "evidenceVatAmount": vat_amount if non_posting else None,
                "documentProcessingStatus": document.get("processing_status"),
                "duplicateOfDocumentId": document.get("duplicate_of_document_id"),
                "missingFields": missing_fields,
                "openReviewItemIds": [item.get("id") for item in open_reviews],
                "latestRoutingAttemptId": latest_routing.get("id") if latest_routing else None,
                "extractedFieldKeys": sorted(extracted.keys()),
                "lineItemCount": len(line_items),
                "exportReadiness": export_readiness,
            },
        }

    def _bank_transaction_record_payload(
        self,
        transaction: Dict[str, Any],
        status: Optional[str] = None,
        reconciliation_status: Optional[str] = None,
    ) -> Dict[str, Any]:
        amount = _float(transaction.get("amount"))
        applied_reconciliation_status = reconciliation_status or transaction.get("reconciliation_status") or "not_started"
        record_status = status or _record_status_for_bank_reconciliation(applied_reconciliation_status)
        applied_rule = self._approved_vendor_category_rule(transaction)
        category = applied_rule.get("category") if applied_rule else None
        target_account = category if applied_rule else None
        rule_confidence = _float(applied_rule.get("confidence_score")) if applied_rule else None
        return {
            "bankTransactionId": transaction.get("id"),
            "sourceType": "bank_transaction",
            "recordType": "income" if amount is not None and amount > 0 else "expense",
            "status": record_status,
            "targetSystem": "waveapps",
            "targetAccount": target_account,
            "vendorName": transaction.get("counterparty"),
            "category": category,
            "recordDate": transaction.get("transaction_date"),
            "amount": amount,
            "currency": transaction.get("currency") or "EUR",
            "description": transaction.get("description"),
            "confidenceScore": rule_confidence,
            "reviewRequired": record_status in {"needs_review", "missing_receipt"},
            "exportStatus": _bank_export_status(applied_reconciliation_status),
            "reconciliationStatus": applied_reconciliation_status,
            "metadata": {
                "accountIdentifier": transaction.get("account_identifier"),
                "transactionId": transaction.get("transaction_id"),
                "source": transaction.get("source"),
                "transactionStatus": transaction.get("status"),
                "duplicateFingerprint": transaction.get("duplicate_fingerprint"),
                "appliedVendorCategoryRule": _rule_summary(applied_rule),
            },
        }

    def _approved_vendor_category_rule(self, transaction: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        vendor_name = str(transaction.get("counterparty") or transaction.get("description") or "").strip()
        if not vendor_name:
            return None
        rules = self.ledger.list_vendor_category_rules(
            vendor_name=vendor_name,
            status="approved",
            limit=50,
        )
        if not rules:
            return None
        exact_target = [
            rule for rule in rules
            if str(rule.get("target_system") or "none") == "waveapps"
        ]
        universal = [
            rule for rule in rules
            if str(rule.get("target_system") or "none") == "none"
        ]
        candidates = exact_target or universal
        if not candidates:
            return None
        return candidates[0]

    def _document_review_required(
        self,
        document: Dict[str, Any],
        category: Any,
        confidence: Optional[float],
        open_reviews: list,
        missing_fields: list,
    ) -> bool:
        status = str(document.get("processing_status") or "")
        if document.get("duplicate_of_document_id"):
            return True
        if status in {"needs_review", "failed", "duplicate"}:
            return True
        if open_reviews or missing_fields:
            return True
        if confidence is not None and confidence < self.review_confidence_threshold:
            return True
        return str(category or "").strip().lower() in MANUAL_REVIEW_CATEGORIES


def _missing_document_fields(
    vendor_name: Any,
    category: Any,
    record_date: Any,
    amount: Any,
) -> list:
    missing = []
    if _blank(vendor_name):
        missing.append("vendorName")
    if _blank(category) or str(category).strip().lower() in MANUAL_REVIEW_CATEGORIES:
        missing.append("category")
    if _blank(record_date):
        missing.append("recordDate")
    if amount is None:
        missing.append("amount")
    return missing


def _record_status_for_document(processing_status: str, review_required: bool) -> str:
    if processing_status == "export_draft_prepared":
        return "export_draft_prepared"
    if processing_status == "routed":
        return "routed"
    if processing_status == "duplicate":
        return "duplicate"
    if processing_status == "failed":
        return "failed"
    if review_required or processing_status == "needs_review":
        return "needs_review"
    if processing_status in READY_DOCUMENT_STATUSES:
        return "ready_to_route"
    return "draft"


def _export_status_for_document(
    document: Dict[str, Any],
    latest_routing: Optional[Dict[str, Any]],
    review_required: bool,
) -> str:
    if latest_routing:
        routing_status = str(latest_routing.get("status") or "")
        if routing_status in EXPORT_PREPARED_STATUSES:
            return "draft_prepared"
        if routing_status.startswith("blocked"):
            return routing_status
        if routing_status == "needs_review":
            return "blocked_by_review"
    processing_status = str(document.get("processing_status") or "")
    if processing_status == "export_draft_prepared":
        return "draft_prepared"
    if processing_status == "duplicate":
        return "blocked_duplicate"
    if processing_status == "failed":
        return "blocked_processing"
    if review_required:
        return "blocked_by_review"
    if processing_status in READY_DOCUMENT_STATUSES:
        return "ready"
    return "not_started"


def _target_system(document: Dict[str, Any], extracted: Dict[str, Any]) -> str:
    return resolve_document_target_system(document, extracted, default="waveapps")


def _record_type(document: Dict[str, Any], extracted: Dict[str, Any], amount: Optional[float]) -> str:
    document_type = str(_first_present(document.get("document_type"), extracted.get("document_type"), "") or "").lower()
    if document_type in {"invoice", "sales_invoice", "estimate"}:
        return "income"
    if document_type in {"bill", "purchase_invoice", "vendor_invoice", "unpaid_purchase"}:
        return "bill"
    if amount is not None and amount < 0:
        return "expense"
    return "expense"


def _latest_routing_attempt(document: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    attempts = document.get("routing_attempts") or []
    return attempts[0] if attempts else None


def _record_status_for_bank_reconciliation(status: str) -> str:
    if status in {"approved", "reconciled"}:
        return "reconciled"
    if status == "missing_receipt":
        return "missing_receipt"
    if status in {"candidate", "needs_review"}:
        return "needs_review"
    if status in {"ignored", "rejected", "resolved"}:
        return status
    return "draft"


def _bank_export_status(reconciliation_status: str) -> str:
    if reconciliation_status == "missing_receipt":
        return "blocked_missing_receipt"
    if reconciliation_status in {"candidate", "needs_review"}:
        return "blocked_by_review"
    if reconciliation_status in {"approved", "reconciled", "ignored", "rejected", "resolved"}:
        return "not_applicable"
    return "not_started"


def _record_status_for_resolution(status: str) -> str:
    if status in {"approved", "resolved"}:
        return "ready_to_route"
    return status


def _export_status_for_resolution(status: str, current_status: Any) -> str:
    current = str(current_status or "")
    if status in {"approved", "resolved"}:
        return current if current in PRESERVED_EXPORT_STATUSES else "ready"
    if status == "needs_review":
        return "blocked_by_review"
    return "not_applicable"


def _record_corrections(corrections: Dict[str, Any]) -> Dict[str, Any]:
    aliases = {
        "vendorName": ("vendorName", "vendor_name"),
        "category": ("category",),
        "recordDate": ("recordDate", "record_date", "transactionDate", "transaction_date"),
        "amount": ("amount", "totalAmount", "total_amount"),
        "vatAmount": ("vatAmount", "vat_amount"),
        "currency": ("currency",),
        "description": ("description",),
        "targetSystem": ("targetSystem", "target_system"),
        "targetAccount": ("targetAccount", "target_account"),
        "recordType": ("recordType", "record_type"),
        "confidenceScore": ("confidenceScore", "confidence_score"),
    }
    normalized = {}
    for canonical, keys in aliases.items():
        value = _first_present(*(corrections.get(key) for key in keys))
        if value in (None, ""):
            continue
        if canonical in {"amount", "vatAmount", "confidenceScore"}:
            value = _float(value)
            if value is None:
                continue
        if canonical == "currency":
            value = str(value).upper()
        normalized[canonical] = value
    return normalized


def _document_line_items(document: Dict[str, Any], record_payload: Dict[str, Any]) -> list:
    if record_payload.get("recordType") == "supporting_document":
        return []
    extracted = dict(document.get("extracted_data") or {})
    return _document_line_items_from_values(
        extracted=extracted,
        category=record_payload.get("category"),
        target_account=record_payload.get("targetAccount"),
        amount=record_payload.get("amount"),
        vat_amount=record_payload.get("vatAmount"),
        description=record_payload.get("description"),
        confidence=record_payload.get("confidenceScore"),
    )


def _document_line_items_from_values(
    extracted: Dict[str, Any],
    category: Any,
    target_account: Any,
    amount: Any,
    vat_amount: Any,
    description: Any,
    confidence: Optional[float],
) -> list:
    raw_items = extracted.get("line_items") or extracted.get("lineItems") or []
    if not isinstance(raw_items, list):
        raw_items = []
    normalized = [
        _normalize_line_item(
            item,
            category=category,
            target_account=target_account,
            fallback_description=description,
            fallback_confidence=confidence,
            fallback_source="extracted_line_item",
        )
        for item in raw_items
        if isinstance(item, dict)
    ]
    normalized = [item for item in normalized if _line_item_has_value(item)]
    if normalized:
        return normalized

    return [_normalize_line_item(
        {
            "description": description,
            "amount": amount,
            "taxAmount": vat_amount,
            "metadata": {"fallback": "document_total"},
        },
        category=category,
        target_account=target_account,
        fallback_description=description,
        fallback_confidence=confidence,
        fallback_source="document_total",
    )]


def _bank_transaction_line_items(transaction: Dict[str, Any], record_payload: Dict[str, Any]) -> list:
    return [_normalize_line_item(
        {
            "description": record_payload.get("description"),
            "amount": record_payload.get("amount"),
            "accountName": (
                record_payload.get("targetAccount")
                or (transaction.get("metadata") or {}).get("accountName")
                or transaction.get("account_identifier")
            ),
            "metadata": {
                "transactionId": transaction.get("transaction_id"),
                "accountIdentifier": transaction.get("account_identifier"),
                "appliedVendorCategoryRule": record_payload.get("metadata", {}).get("appliedVendorCategoryRule"),
            },
        },
        category=record_payload.get("category"),
        target_account=record_payload.get("targetAccount"),
        fallback_description=record_payload.get("description"),
        fallback_confidence=None,
        fallback_source="bank_transaction",
    )]


def _normalize_line_item(
    item: Dict[str, Any],
    category: Any,
    target_account: Any,
    fallback_description: Any,
    fallback_confidence: Optional[float],
    fallback_source: str,
) -> Dict[str, Any]:
    quantity = _float(_first_present(item.get("quantity"), item.get("qty")))
    amount = _float(_first_present(item.get("amount"), item.get("total_amount"), item.get("totalAmount")))
    unit_price = _float(_first_present(item.get("unit_price"), item.get("unitPrice"), item.get("price")))
    if amount is None and unit_price is not None and quantity not in (None, 0):
        amount = unit_price * quantity
    if unit_price is None and amount is not None and quantity not in (None, 0):
        unit_price = amount / quantity

    tax_amount = _float(_first_present(
        item.get("tax_amount"),
        item.get("taxAmount"),
        item.get("vat_amount"),
        item.get("vatAmount"),
    ))
    tax_rate = _float(_first_present(
        item.get("tax_rate"),
        item.get("taxRate"),
        item.get("vat_rate"),
        item.get("vatRate"),
    ))
    if tax_rate is None and amount not in (None, 0) and tax_amount not in (None, 0):
        net_amount = amount - tax_amount
        if net_amount:
            tax_rate = round((tax_amount / net_amount) * 100, 4)

    description = _first_present(item.get("description"), fallback_description)
    item_name = _first_present(item.get("item_name"), item.get("itemName"), item.get("name"), item.get("item"))
    account_name = _first_present(
        item.get("account_name"),
        item.get("accountName"),
        item.get("account"),
        item.get("target_account"),
        item.get("targetAccount"),
        target_account,
    )
    return {
        "itemName": item_name,
        "description": description,
        "quantity": quantity,
        "unitPrice": unit_price,
        "amount": amount,
        "taxAmount": tax_amount,
        "taxRate": tax_rate,
        "taxCode": _first_present(item.get("tax_code"), item.get("taxCode"), item.get("sales_tax"), item.get("salesTax"), item.get("tax")),
        "category": _first_present(item.get("category"), category),
        "accountName": account_name,
        "source": item.get("source") or fallback_source,
        "confidenceScore": _float(_first_present(item.get("confidence_score"), item.get("confidenceScore"), fallback_confidence)),
        "metadata": item.get("metadata") or {},
    }


def _line_item_has_value(item: Dict[str, Any]) -> bool:
    return any(not _blank(item.get(field)) for field in ("description", "itemName", "amount", "category", "accountName"))


def _line_item_export_readiness(line_items: list, vat_amount: Optional[float]) -> Dict[str, Any]:
    missing_account_mapping = [
        index for index, item in enumerate(line_items)
        if _blank(item.get("accountName"))
    ]
    missing_tax_code = [
        index for index, item in enumerate(line_items)
        if item.get("taxAmount") not in (None, 0) and _blank(item.get("taxCode"))
    ]
    return {
        "lineItemCount": len(line_items),
        "hasTaxEvidence": bool(vat_amount not in (None, 0) or any(item.get("taxAmount") not in (None, 0) for item in line_items)),
        "missingAccountMapping": missing_account_mapping,
        "missingTaxCode": missing_tax_code,
        "readyForWaveDraft": not missing_account_mapping,
    }


def _rule_summary(rule: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not rule:
        return None
    return {
        "ruleId": rule.get("id"),
        "vendorName": rule.get("vendor_name"),
        "category": rule.get("category"),
        "targetSystem": rule.get("target_system"),
        "status": rule.get("status"),
    }


def _blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def _float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _float_config(config: Dict[str, Any], *keys: str, default: float) -> float:
    for key in keys:
        value = config.get(key)
        if value not in (None, ""):
            try:
                return float(value)
            except (TypeError, ValueError):
                return default
    return default
