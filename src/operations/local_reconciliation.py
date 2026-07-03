from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from src.operations.local_bookkeeping_records import LocalBookkeepingRecordService
from src.operations.local_ledger import LocalOperationsLedger
from src.reconciliation.automated_reconciliation import AutomatedReconciliation


RECONCILIABLE_DOCUMENT_STATUSES = (
    "processed",
    "reviewed",
    "validated",
    "ready_to_route",
    "export_draft_prepared",
    "routed",
)
FINAL_RECONCILIATION_STATUSES = {"approved", "reconciled"}
RESOLUTION_STATUSES = {"approved", "reconciled", "rejected", "resolved", "ignored", "needs_review"}
OPEN_REVIEW_STATUSES = ("pending", "in_review")


class LocalReconciliationService:
    """Match local ledger documents to bank transactions without posting externally."""

    def __init__(
        self,
        ledger: LocalOperationsLedger,
        config: Optional[Dict[str, Any]] = None,
        reconciler: Optional[Any] = None,
    ):
        self.ledger = ledger
        self.config = config or {}
        self.reconciler = reconciler or AutomatedReconciliation(self.config)

    def run(
        self,
        bank_transactions: List[Dict[str, Any]],
        document_ids: Optional[Iterable[int]] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        if not isinstance(bank_transactions, list):
            raise ValueError("bankTransactions must be a list")

        documents = self._candidate_documents(document_ids=document_ids, limit=limit)
        reconciler_documents = [self._document_for_reconciler(document) for document in documents]
        raw_results = self.reconciler.reconcile(bank_transactions, reconciler_documents)
        summary: Dict[str, Any] = {
            "requestedTransactions": len(bank_transactions),
            "candidateDocuments": len(documents),
            "matchedCandidates": 0,
            "missingReceipts": 0,
            "unmatchedDocuments": 0,
            "matchesRecorded": 0,
            "reviewItemsCreated": 0,
            "results": [],
        }

        for result in raw_results:
            result_type = result.get("type")
            if result_type == "match":
                summary["matchedCandidates"] += 1
                record = self._record_candidate(result)
            elif result_type == "unmatched_bank_transaction":
                summary["missingReceipts"] += 1
                record = self._record_missing_receipt(result)
            elif result_type == "unmatched_document":
                summary["unmatchedDocuments"] += 1
                record = self._record_unmatched_document(result)
            else:
                record = {"status": "ignored", "type": result_type or "unknown"}

            if record.get("recorded"):
                summary["matchesRecorded"] += 1
            if record.get("reviewItemCreated"):
                summary["reviewItemsCreated"] += 1
            summary["results"].append(record)

        self.ledger.record_audit_event({
            "action": "local_reconciliation.run_completed",
            "entityType": "reconciliation_run",
            "details": {
                "requestedTransactions": summary["requestedTransactions"],
                "candidateDocuments": summary["candidateDocuments"],
                "matchedCandidates": summary["matchedCandidates"],
                "missingReceipts": summary["missingReceipts"],
                "unmatchedDocuments": summary["unmatchedDocuments"],
                "matchesRecorded": summary["matchesRecorded"],
                "reviewItemsCreated": summary["reviewItemsCreated"],
            },
        })
        return summary

    def resolve_match(
        self,
        reconciliation_match_id: int,
        status: str,
        resolution: Optional[str] = None,
    ) -> Dict[str, Any]:
        status = str(status or "").strip()
        if status not in RESOLUTION_STATUSES:
            return {
                "success": False,
                "status": "invalid_status",
                "error": f"Invalid reconciliation status: {status}",
            }

        match = self.ledger.get_reconciliation_match(reconciliation_match_id)
        if not match:
            return {
                "success": False,
                "status": "not_found",
                "error": "Reconciliation match not found",
            }

        metadata = dict(match.get("metadata") or {})
        metadata["resolution"] = {
            "status": status,
            "note": resolution,
            "resolvedAt": _now(),
        }
        update_payload: Dict[str, Any] = {
            "status": status,
            "metadata": metadata,
        }
        if status in FINAL_RECONCILIATION_STATUSES:
            update_payload["matchedAt"] = _now()
        self.ledger.update_reconciliation_match(reconciliation_match_id, update_payload)

        document_id = match.get("document_id")
        if document_id:
            document_reconciliation_status = _document_reconciliation_status(status)
            self.ledger.update_document(int(document_id), {
                "reconciliationStatus": document_reconciliation_status,
            })
            LocalBookkeepingRecordService(self.ledger, self.config).record_reconciliation_state(
                int(document_id),
                document_reconciliation_status,
                reconciliation_match_id=reconciliation_match_id,
            )
            self._resolve_linked_review_items(
                int(document_id),
                resolution or f"Reconciliation match #{reconciliation_match_id} marked {status}.",
            )

        self._update_bank_transaction_reconciliation(
            metadata.get("bankTransaction") or {},
            _bank_reconciliation_status(status),
            reconciliation_match_id,
            document_id,
        )

        self.ledger.record_audit_event({
            "action": "local_reconciliation.match.resolve",
            "entityType": "reconciliation_match",
            "entityId": str(reconciliation_match_id),
            "details": {
                "status": status,
                "documentId": document_id,
                "bankTransactionId": match.get("bank_transaction_id"),
                "resolution": resolution,
            },
        })
        return {
            "success": True,
            "status": status,
            "reconciliationMatchId": reconciliation_match_id,
            "documentId": document_id,
        }

    def _candidate_documents(
        self,
        document_ids: Optional[Iterable[int]],
        limit: int,
    ) -> List[Dict[str, Any]]:
        if document_ids:
            documents = []
            for document_id in document_ids:
                document = self.ledger.get_document(int(document_id))
                if document:
                    documents.append(document)
            return documents[: _bounded_limit(limit)]
        return self.ledger.list_documents(status=RECONCILIABLE_DOCUMENT_STATUSES, limit=limit)

    def _record_candidate(self, result: Dict[str, Any]) -> Dict[str, Any]:
        document = result.get("document") or {}
        document_id = _int_or_none(document.get("id") or result.get("document_id"))
        bank_transaction = result.get("bank_transaction") or {}
        bank_transaction_id = _bank_transaction_id(bank_transaction)
        if document_id is None:
            return {"status": "skipped", "type": "match", "reason": "missing_document_id"}

        existing = self._existing_reconciliation(document_id, bank_transaction_id)
        if existing and existing.get("status") in FINAL_RECONCILIATION_STATUSES | {"rejected", "ignored"}:
            self._update_bank_transaction_reconciliation(
                bank_transaction,
                _bank_reconciliation_status(str(existing.get("status") or "")),
                int(existing["id"]),
                document_id,
            )
            return {
                "status": "already_final",
                "type": "match",
                "reconciliationMatchId": existing["id"],
                "documentId": document_id,
                "bankTransactionId": bank_transaction_id,
            }

        payload = {
            "documentId": document_id,
            "bankTransactionId": bank_transaction_id,
            "status": "candidate",
            "confidenceScore": result.get("confidence_score"),
            "amountDifference": result.get("amount_difference"),
            "metadata": {
                "resultType": "match",
                "bankTransaction": bank_transaction,
                "document": _document_snapshot(document),
                "requiresApproval": True,
                "externalMutation": "not_performed",
            },
        }
        if existing:
            reconciliation_match_id = int(existing["id"])
            self.ledger.update_reconciliation_match(reconciliation_match_id, payload)
            recorded = False
        else:
            reconciliation_match_id = self.ledger.create_reconciliation_match(payload)
            recorded = True

        self.ledger.update_document(document_id, {"reconciliationStatus": "candidate"})
        self._update_bank_transaction_reconciliation(
            bank_transaction,
            "candidate",
            reconciliation_match_id,
            document_id,
        )
        review_created = self._queue_document_review(
            document_id,
            "reconciliation_candidate",
            (
                f"Bank transaction {bank_transaction_id} matches document #{document_id} "
                f"with {float(result.get('confidence_score') or 0) * 100:.0f}% confidence. Confirm before final close."
            ),
            {
                "reconciliationMatchId": reconciliation_match_id,
                "bankTransactionId": bank_transaction_id,
            },
        )
        LocalBookkeepingRecordService(self.ledger, self.config).record_reconciliation_state(
            document_id,
            "candidate",
            status="needs_review",
            reconciliation_match_id=reconciliation_match_id,
        )
        return {
            "status": "candidate",
            "type": "match",
            "recorded": recorded,
            "reviewItemCreated": review_created,
            "reconciliationMatchId": reconciliation_match_id,
            "documentId": document_id,
            "bankTransactionId": bank_transaction_id,
            "confidenceScore": result.get("confidence_score"),
        }

    def _record_missing_receipt(self, result: Dict[str, Any]) -> Dict[str, Any]:
        bank_transaction = result.get("bank_transaction") or {}
        bank_transaction_id = _bank_transaction_id(bank_transaction)
        existing = self._existing_reconciliation(None, bank_transaction_id)
        if existing:
            self._update_bank_transaction_reconciliation(
                bank_transaction,
                str(existing.get("status") or "missing_receipt"),
                int(existing["id"]),
                None,
            )
            return {
                "status": "already_recorded",
                "type": "unmatched_bank_transaction",
                "reconciliationMatchId": existing["id"],
                "bankTransactionId": bank_transaction_id,
            }

        reconciliation_match_id = self.ledger.create_reconciliation_match({
            "bankTransactionId": bank_transaction_id,
            "status": "missing_receipt",
            "confidenceScore": 0,
            "metadata": {
                "resultType": "unmatched_bank_transaction",
                "bankTransaction": bank_transaction,
                "requiresReceiptReview": True,
                "externalMutation": "not_performed",
            },
        })
        self._update_bank_transaction_reconciliation(
            bank_transaction,
            "missing_receipt",
            reconciliation_match_id,
            None,
        )
        review_item_id = self.ledger.create_review_item({
            "reason": "missing_receipt",
            "details": f"Bank transaction {bank_transaction_id} has no matching processed document.",
            "correctedData": {
                "reconciliationMatchId": reconciliation_match_id,
                "bankTransactionId": bank_transaction_id,
                "bankTransaction": bank_transaction,
            },
        })
        bank_record_id = _ledger_bank_transaction_id(bank_transaction)
        if bank_record_id is not None:
            LocalBookkeepingRecordService(self.ledger, self.config).upsert_from_bank_transaction(
                bank_record_id,
                status="missing_receipt",
                reconciliation_status="missing_receipt",
            )
        return {
            "status": "missing_receipt",
            "type": "unmatched_bank_transaction",
            "recorded": True,
            "reviewItemCreated": True,
            "reviewItemId": review_item_id,
            "reconciliationMatchId": reconciliation_match_id,
            "bankTransactionId": bank_transaction_id,
        }

    def _record_unmatched_document(self, result: Dict[str, Any]) -> Dict[str, Any]:
        document = result.get("document") or {}
        document_id = _int_or_none(document.get("id") or result.get("document_id"))
        if document_id is None:
            return {"status": "skipped", "type": "unmatched_document", "reason": "missing_document_id"}

        bank_transaction_id = f"unmatched_document:{document_id}"
        existing = self._existing_reconciliation(document_id, bank_transaction_id)
        if existing:
            return {
                "status": "already_recorded",
                "type": "unmatched_document",
                "reconciliationMatchId": existing["id"],
                "documentId": document_id,
            }

        reconciliation_match_id = self.ledger.create_reconciliation_match({
            "documentId": document_id,
            "bankTransactionId": bank_transaction_id,
            "status": "unmatched_document",
            "confidenceScore": 0,
            "metadata": {
                "resultType": "unmatched_document",
                "document": _document_snapshot(document),
                "requiresBankEvidenceReview": True,
                "externalMutation": "not_performed",
            },
        })
        self.ledger.update_document(document_id, {"reconciliationStatus": "unmatched"})
        LocalBookkeepingRecordService(self.ledger, self.config).record_reconciliation_state(
            document_id,
            "unmatched",
            status="needs_review",
            reconciliation_match_id=reconciliation_match_id,
        )
        review_created = self._queue_document_review(
            document_id,
            "unmatched_document",
            f"Document #{document_id} has no matching bank transaction in this reconciliation run.",
            {"reconciliationMatchId": reconciliation_match_id},
        )
        return {
            "status": "unmatched_document",
            "type": "unmatched_document",
            "recorded": True,
            "reviewItemCreated": review_created,
            "reconciliationMatchId": reconciliation_match_id,
            "documentId": document_id,
        }

    def _existing_reconciliation(
        self,
        document_id: Optional[int],
        bank_transaction_id: str,
    ) -> Optional[Dict[str, Any]]:
        matches = self.ledger.list_reconciliation_matches(
            document_id=document_id,
            bank_transaction_id=bank_transaction_id,
            limit=1,
        )
        return matches[0] if matches else None

    def _queue_document_review(
        self,
        document_id: int,
        reason: str,
        details: str,
        corrected_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        for item in self.ledger.list_review_items(
            status=OPEN_REVIEW_STATUSES,
            document_id=document_id,
            limit=50,
        ):
            if item.get("reason") == reason:
                return False
        self.ledger.create_review_item({
            "documentId": document_id,
            "reason": reason,
            "details": details,
            "correctedData": corrected_data,
        })
        return True

    def _resolve_linked_review_items(self, document_id: int, resolution: str) -> None:
        for item in self.ledger.list_review_items(
            status=OPEN_REVIEW_STATUSES,
            document_id=document_id,
            limit=50,
        ):
            if item.get("reason") in {"reconciliation_candidate", "unmatched_document"}:
                self.ledger.resolve_review_item(
                    int(item["id"]),
                    status="resolved",
                    resolution=resolution,
                    corrected_data=item.get("corrected_data"),
                )

    @staticmethod
    def _document_for_reconciler(document: Dict[str, Any]) -> Dict[str, Any]:
        extracted_data = dict(document.get("extracted_data") or {})
        extracted_data.setdefault("vendor_name", document.get("vendor_name"))
        extracted_data.setdefault("transaction_date", document.get("transaction_date"))
        extracted_data.setdefault("total_amount", document.get("total_amount"))
        extracted_data.setdefault("amount", document.get("total_amount"))
        return {
            **document,
            "document_id": str(document.get("id")),
            "extracted_data": extracted_data,
        }

    def _update_bank_transaction_reconciliation(
        self,
        bank_transaction: Dict[str, Any],
        status: str,
        reconciliation_match_id: Optional[int],
        document_id: Optional[int],
    ) -> None:
        bank_transaction_record_id = _ledger_bank_transaction_id(bank_transaction)
        if bank_transaction_record_id is None:
            return
        current = self.ledger.get_bank_transaction(bank_transaction_record_id)
        if not current:
            return
        metadata = dict(current.get("metadata") or {})
        metadata["latestReconciliation"] = {
            "status": status,
            "reconciliationMatchId": reconciliation_match_id,
            "documentId": document_id,
            "bankTransactionId": current.get("transaction_id"),
            "updatedAt": _now(),
        }
        self.ledger.update_bank_transaction(bank_transaction_record_id, {
            "reconciliationStatus": status,
            "metadata": metadata,
        })
        LocalBookkeepingRecordService(self.ledger, self.config).upsert_from_bank_transaction(
            bank_transaction_record_id,
            reconciliation_status=status,
        )


def _document_snapshot(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": document.get("id"),
        "source": document.get("source"),
        "sourceDocumentId": document.get("source_document_id"),
        "originalFilename": document.get("original_filename"),
        "vendorName": document.get("vendor_name"),
        "category": document.get("category"),
        "transactionDate": document.get("transaction_date"),
        "totalAmount": document.get("total_amount"),
        "reconciliationStatus": document.get("reconciliation_status"),
    }


def _bank_transaction_id(bank_transaction: Dict[str, Any]) -> str:
    explicit_id = bank_transaction.get("id") or bank_transaction.get("transaction_id")
    if explicit_id:
        return str(explicit_id)
    parts = [
        str(bank_transaction.get("date") or bank_transaction.get("transaction_date") or ""),
        str(bank_transaction.get("amount") or ""),
        str(bank_transaction.get("description") or bank_transaction.get("counterparty") or ""),
    ]
    return "bank:" + "|".join(parts)


def _ledger_bank_transaction_id(bank_transaction: Dict[str, Any]) -> Optional[int]:
    return _int_or_none(
        bank_transaction.get("ledgerBankTransactionId")
        or bank_transaction.get("ledger_bank_transaction_id")
        or bank_transaction.get("bankTransactionRecordId")
        or bank_transaction.get("bank_transaction_record_id")
    )


def _document_reconciliation_status(status: str) -> str:
    if status in FINAL_RECONCILIATION_STATUSES:
        return "reconciled"
    if status == "rejected":
        return "rejected"
    if status == "ignored":
        return "ignored"
    if status == "resolved":
        return "resolved"
    return "needs_review"


def _bank_reconciliation_status(status: str) -> str:
    if status in FINAL_RECONCILIATION_STATUSES:
        return "reconciled"
    if status == "rejected":
        return "rejected"
    if status == "ignored":
        return "ignored"
    if status == "resolved":
        return "resolved"
    if status == "missing_receipt":
        return "missing_receipt"
    if status == "candidate":
        return "candidate"
    return "needs_review"


def _int_or_none(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bounded_limit(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = 100
    return max(1, min(parsed, 500))


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
