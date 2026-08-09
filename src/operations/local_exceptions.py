from typing import Any, Dict, List, Optional

from src.operations.local_anomalies import LocalLedgerAnomalyService
from src.operations.local_health import LocalOperationsHealth
from src.operations.local_ledger import LocalOperationsLedger
from src.operations.local_master_ledger import LocalMasterLedgerService


class LocalExceptionQueueService:
    """Build an operator-facing exception queue from FAB health evidence."""

    def __init__(self, ledger: LocalOperationsLedger, config: Optional[Dict[str, Any]] = None):
        self.ledger = ledger
        self.config = config or {}

    def list_exceptions(
        self,
        limit: int = 50,
        include_entities: bool = True,
        *,
        health: Optional[Dict[str, Any]] = None,
        master_ledger: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        with self.ledger.read_snapshot():
            return self._list_exceptions(
                limit=limit,
                include_entities=include_entities,
                health=health,
                master_ledger=master_ledger,
            )

    def _list_exceptions(
        self,
        limit: int,
        include_entities: bool,
        *,
        health: Optional[Dict[str, Any]],
        master_ledger: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if health is None:
            health = LocalOperationsHealth(self.ledger, self.config).summarize(
                master_ledger=master_ledger,
            )
        bounded_limit = _bounded_limit(limit)
        issues = [
            *self._master_ledger_row_issues(
                limit=bounded_limit,
                master_ledger=master_ledger,
            ),
            *list(health.get("issues") or []),
            *LocalLedgerAnomalyService(self.ledger, self.config).list_issues(limit=bounded_limit),
        ]
        issues = _prioritized_issues(issues)[:bounded_limit]
        entity_context = (
            self.ledger.get_exception_entity_context(
                _entity_references(issues),
            )
            if include_entities
            else {}
        )
        exceptions = [
            self._exception_from_issue(
                issue,
                include_entities=include_entities,
                entity_context=entity_context,
            )
            for issue in issues
        ]
        return {
            "status": health.get("status"),
            "generatedAt": health.get("generatedAt"),
            "externalSubmission": "not_executed",
            "summary": _exception_summary(exceptions),
            "exceptions": exceptions,
            "nextActions": health.get("nextActions") or [],
        }

    def _exception_from_issue(
        self,
        issue: Dict[str, Any],
        include_entities: bool,
        entity_context: Dict[str, Dict[int, Dict[str, Any]]],
    ) -> Dict[str, Any]:
        exception = {
            "id": _exception_id(issue),
            "severity": issue.get("severity"),
            "type": issue.get("type"),
            "entityType": issue.get("entityType"),
            "entityId": issue.get("entityId"),
            "message": issue.get("message"),
            "ageHours": issue.get("ageHours"),
            "details": issue.get("details") or {},
            "nextAction": _next_action_for_issue(issue),
            "actions": _actions_for_issue(issue),
            "externalSubmission": "not_executed",
        }
        if include_entities:
            exception["entity"] = self._entity_summary(issue, entity_context)
        return exception

    def _master_ledger_row_issues(
        self,
        limit: int,
        master_ledger: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        projection = master_ledger
        if projection is None:
            projection = LocalMasterLedgerService(self.ledger, self.config).project(limit=limit)
        issues = []
        for row in projection.get("rows") or []:
            row_issues = _issues_for_master_ledger_row(row)
            if row_issues:
                issues.extend(row_issues)
            if len(issues) >= limit:
                break
        return issues

    def _entity_summary(
        self,
        issue: Dict[str, Any],
        entity_context: Dict[str, Dict[int, Dict[str, Any]]],
    ) -> Optional[Dict[str, Any]]:
        entity_type = str(issue.get("entityType") or "")
        entity_id = issue.get("entityId")
        if entity_id in (None, ""):
            return None
        try:
            parsed_id = int(entity_id)
        except (TypeError, ValueError):
            parsed_id = None
        if parsed_id is None:
            return None
        entity = (entity_context.get(entity_type) or {}).get(parsed_id)
        if not entity:
            return None
        summarizers = {
            "bookkeeping_document": _document_summary,
            "review_item": _review_summary,
            "bookkeeping_record": _bookkeeping_record_summary,
            "export_attempt": _export_summary,
            "routing_attempt": _routing_summary,
            "workflow_run": _workflow_summary,
            "source_account": _source_account_summary,
        }
        summarizer = summarizers.get(entity_type)
        if summarizer:
            return summarizer(entity)
        return None


def _issues_for_master_ledger_row(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    blockers = [str(blocker) for blocker in (row.get("blockers") or [])]
    if not blockers:
        return []
    if row.get("externalSubmission") in {"queued", "submitted", "executed"}:
        return []

    issues: List[Dict[str, Any]] = []
    if (
        row.get("downstreamStatus") == "stale_master_ledger_draft"
        and row.get("exportAttemptId")
    ):
        freshness = row.get("draftFreshness") if isinstance(row.get("draftFreshness"), dict) else {}
        issues.append({
            "severity": "medium",
            "type": "stale_master_ledger_draft",
            "entityType": "export_attempt",
            "entityId": row.get("exportAttemptId"),
            "message": (
                f"Export attempt #{row.get('exportAttemptId')} has a stale "
                f"{row.get('targetSystem')} master-ledger draft for record #{row.get('recordId')}."
            ),
            "ageHours": None,
            "details": {
                "recordId": row.get("recordId"),
                "documentId": row.get("documentId"),
                "bookkeepingRecordId": (row.get("sourceProof") or {}).get("recordId"),
                "targetSystem": row.get("targetSystem"),
                "storedChecksum": freshness.get("storedChecksum"),
                "currentChecksum": freshness.get("currentChecksum"),
                "freshnessStatus": freshness.get("status"),
                "blockers": blockers,
                "externalSubmission": "not_executed",
            },
        })

    record_blockers = [
        blocker for blocker in blockers
        if blocker in {"review_required", "record_needs_review", "record_failed", "record_duplicate"}
    ]
    if record_blockers and row.get("recordId"):
        issues.append(_record_blocker_issue(row, record_blockers))

    reconciliation_blockers = [
        blocker for blocker in blockers
        if blocker.startswith("reconciliation_")
    ]
    if reconciliation_blockers and row.get("recordId"):
        issues.append(_reconciliation_blocker_issue(row, reconciliation_blockers))

    export_blockers = [
        blocker for blocker in blockers
        if (
            blocker.startswith("blocked")
            or blocker == "downstream_failed"
        )
    ]
    if export_blockers:
        issues.append(_export_blocker_issue(row, export_blockers))

    return issues


def _record_blocker_issue(row: Dict[str, Any], blockers: List[str]) -> Dict[str, Any]:
    severity = "high" if "record_failed" in blockers else "medium"
    return {
        "severity": severity,
        "type": "master_ledger_record_review",
        "entityType": "bookkeeping_record",
        "entityId": row.get("recordId"),
        "message": (
            f"Bookkeeping record #{row.get('recordId')} blocks the master ledger "
            f"because it needs record review: {', '.join(blockers)}."
        ),
        "ageHours": None,
        "details": _row_issue_details(row, blockers),
    }


def _reconciliation_blocker_issue(row: Dict[str, Any], blockers: List[str]) -> Dict[str, Any]:
    return {
        "severity": "medium",
        "type": "master_ledger_reconciliation_blocker",
        "entityType": "bookkeeping_record",
        "entityId": row.get("recordId"),
        "message": (
            f"Bookkeeping record #{row.get('recordId')} blocks the master ledger "
            f"because reconciliation is incomplete: {', '.join(blockers)}."
        ),
        "ageHours": None,
        "details": _row_issue_details(row, blockers),
    }


def _export_blocker_issue(row: Dict[str, Any], blockers: List[str]) -> Dict[str, Any]:
    export_attempt_id = row.get("exportAttemptId")
    return {
        "severity": "high" if "downstream_failed" in blockers else "medium",
        "type": "master_ledger_export_blocker",
        "entityType": "export_attempt" if export_attempt_id else "bookkeeping_record",
        "entityId": export_attempt_id or row.get("recordId"),
        "message": (
            f"Master-ledger row for record #{row.get('recordId')} is blocked by export state: "
            f"{', '.join(blockers)}."
        ),
        "ageHours": None,
        "details": _row_issue_details(row, blockers),
    }


def _row_issue_details(row: Dict[str, Any], blockers: List[str]) -> Dict[str, Any]:
    return {
        "recordId": row.get("recordId"),
        "documentId": row.get("documentId"),
        "bankTransactionId": row.get("bankTransactionId"),
        "targetSystem": row.get("targetSystem"),
        "recordStatus": row.get("recordStatus"),
        "exportStatus": row.get("exportStatus"),
        "reconciliationStatus": row.get("reconciliationStatus"),
        "downstreamStatus": row.get("downstreamStatus"),
        "exportAttemptId": row.get("exportAttemptId"),
        "routingAttemptId": row.get("routingAttemptId"),
        "blockers": blockers,
        "externalSubmission": "not_executed",
    }


def _exception_summary(exceptions: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_severity: Dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    by_type: Dict[str, int] = {}
    for item in exceptions:
        severity = str(item.get("severity") or "")
        if severity in by_severity:
            by_severity[severity] += 1
        item_type = str(item.get("type") or "unknown")
        by_type[item_type] = by_type.get(item_type, 0) + 1
    return {
        "total": len(exceptions),
        "bySeverity": by_severity,
        "byType": dict(sorted(by_type.items())),
    }


def _exception_id(issue: Dict[str, Any]) -> str:
    return ":".join([
        str(issue.get("type") or "issue"),
        str(issue.get("entityType") or "global"),
        str(issue.get("entityId") or "none"),
    ])


def _next_action_for_issue(issue: Dict[str, Any]) -> str:
    issue_type = str(issue.get("type") or "")
    mapping = {
        "failed_document": "Inspect the processing error, fix the source problem, then retry processing.",
        "stuck_document": "Retry processing or move the document into manual review with a concrete reason.",
        "stale_review_item": "Resolve the review item with approve, reject, ignore, or corrected field values.",
        "routing_block": "Open the routing attempt and fix duplicate, review, status, or missing-plan blockers.",
        "stale_routing_draft": "Review the prepared draft and either prepare an export attempt or resolve the route.",
        "stale_export_approval": "Approve, reject, or regenerate the export attempt before any external submission.",
        "stale_export_approved": "Execute the approved attempt only when credentials/handlers are ready, or cancel it.",
        "failed_export_attempt": "Inspect the failed export result and regenerate the source draft after fixing the cause.",
        "stale_master_ledger_draft": "Regenerate the export attempt from current FAB source data, then review approval again.",
        "master_ledger_record_review": "Open the normalized bookkeeping record and resolve its review, failed, or duplicate state.",
        "master_ledger_reconciliation_blocker": "Open reconciliation evidence and resolve the missing receipt, unmatched, or needs-review state.",
        "master_ledger_export_blocker": "Open the blocked export or record and regenerate, reject, or reroute only after fixing the source cause.",
        "vendor_amount_anomaly": "Compare the amount with source evidence and the vendor history before approving or correcting the record.",
        "category_amount_anomaly": "Compare the amount with source evidence and similar category records before approving or correcting it.",
        "future_dated_record": "Verify the source date and correct the record before approval or downstream delivery.",
        "stale_workflow_run": "Check the running process or lock before starting another autonomous cycle.",
        "failed_workflow_run": "Review workflow error details and rerun only the safe local cycle.",
        "master_ledger_blockers": "Open the master-ledger projection and resolve blocked rows before close/export.",
    }
    return mapping.get(issue_type, "Inspect the linked entity and record an audited resolution.")


def _actions_for_issue(issue: Dict[str, Any]) -> List[Dict[str, Any]]:
    issue_type = str(issue.get("type") or "")
    entity_type = str(issue.get("entityType") or "")
    entity_id = issue.get("entityId")
    actions: List[Dict[str, Any]] = []
    if entity_type == "bookkeeping_document" and entity_id:
        actions.append(_action(
            "open_document",
            "GET",
            f"/api/documents/{entity_id}",
            "read_only",
            dashboard_path=f"/documents/{entity_id}",
        ))
        if issue_type in {"failed_document", "stuck_document"}:
            actions.append(_action(
                "retry_processing",
                "POST",
                f"/api/documents/{entity_id}/retry-processing",
                "safe_auto",
                dashboard_path=f"/documents/{entity_id}/retry-processing",
            ))
    if entity_type == "review_item" and entity_id:
        actions.append(_action("open_review_queue", "GET", "/api/review?status=pending", "read_only"))
    if entity_type == "bookkeeping_record" and entity_id:
        actions.append(_action(
            "open_bookkeeping_record",
            "GET",
            f"/api/bookkeeping-records/{entity_id}",
            "read_only",
            dashboard_path=f"/bookkeeping-records/{entity_id}",
        ))
        actions.append(_action("open_master_ledger", "GET", "/api/master-ledger", "read_only"))
        if issue_type == "master_ledger_reconciliation_blocker":
            actions.append(_action(
                "open_reconciliation",
                "GET",
                "/api/reconciliation",
                "read_only",
                dashboard_path="/#reconciliation",
            ))
    if entity_type == "export_attempt" and entity_id:
        actions.append(_action("open_export_attempts", "GET", f"/api/export-attempts/{entity_id}", "read_only"))
        if issue_type == "stale_master_ledger_draft":
            actions.append(_action(
                "regenerate_export_attempt",
                "POST",
                f"/api/export-attempts/{entity_id}/regenerate",
                "safe_auto",
                dashboard_path=f"/export-attempts/{entity_id}/regenerate",
            ))
        if issue_type in {"stale_export_approval", "stale_export_approved", "failed_export_attempt", "master_ledger_export_blocker"}:
            actions.append(_action("reject_export_attempt", "POST", f"/api/export-attempts/{entity_id}/reject", "requires_confirmation"))
    if entity_type == "routing_attempt" and entity_id:
        actions.append(_action("open_routing_attempts", "GET", f"/api/routing?id={entity_id}", "read_only"))
    if entity_type == "workflow_run" and entity_id:
        actions.append(_action(
            "open_workflow_run",
            "GET",
            f"/api/workflows/{entity_id}",
            "read_only",
            dashboard_path="/#workflows",
        ))
    if issue_type == "master_ledger_blockers":
        actions.append(_action("open_master_ledger", "GET", "/api/master-ledger", "read_only"))
    return actions


def _action(
    action_id: str,
    method: str,
    path: str,
    safety: str,
    dashboard_path: Optional[str] = None,
) -> Dict[str, Any]:
    action = {
        "id": action_id,
        "method": method,
        "path": path,
        "safety": safety,
        "externalSubmission": "not_executed",
    }
    if dashboard_path:
        action["dashboardPath"] = dashboard_path
    return action


def _document_summary(document: Dict[str, Any]) -> Dict[str, Any]:
    review_item_count = document.get("review_item_count")
    return {
        "id": document.get("id"),
        "source": document.get("source"),
        "sourceDocumentId": document.get("source_document_id"),
        "originalFilename": document.get("original_filename"),
        "processingStatus": document.get("processing_status"),
        "vendorName": document.get("vendor_name"),
        "category": document.get("category"),
        "transactionDate": document.get("transaction_date"),
        "totalAmount": document.get("total_amount"),
        "confidenceScore": document.get("confidence_score"),
        "reviewItemCount": (
            int(review_item_count)
            if review_item_count is not None
            else len(document.get("review_items") or [])
        ),
        "processingError": (document.get("metadata") or {}).get("processingError"),
    }


def _review_summary(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": item.get("id"),
        "documentId": item.get("document_id"),
        "reason": item.get("reason"),
        "status": item.get("status"),
        "details": item.get("details"),
    }


def _bookkeeping_record_summary(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": record.get("id"),
        "documentId": record.get("document_id"),
        "bankTransactionId": record.get("bank_transaction_id"),
        "sourceType": record.get("source_type"),
        "recordType": record.get("record_type"),
        "recordDate": record.get("record_date"),
        "vendorName": record.get("vendor_name"),
        "description": record.get("description"),
        "category": record.get("category"),
        "amount": record.get("amount"),
        "currency": record.get("currency"),
        "targetSystem": record.get("target_system"),
        "status": record.get("status"),
        "exportStatus": record.get("export_status"),
        "reconciliationStatus": record.get("reconciliation_status"),
        "reviewRequired": bool(record.get("review_required")),
    }


def _export_summary(attempt: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": attempt.get("id"),
        "documentId": attempt.get("document_id"),
        "bookkeepingRecordId": attempt.get("bookkeeping_record_id"),
        "targetSystem": attempt.get("target_system"),
        "actionId": attempt.get("action_id"),
        "status": attempt.get("status"),
        "externalSubmission": attempt.get("external_submission"),
        "message": attempt.get("message"),
    }


def _routing_summary(route: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": route.get("id"),
        "documentId": route.get("document_id"),
        "bookkeepingRecordId": route.get("bookkeeping_record_id"),
        "target": route.get("target"),
        "status": route.get("status"),
        "message": route.get("message"),
    }


def _workflow_summary(run: Dict[str, Any]) -> Dict[str, Any]:
    steps = run.get("steps") or []
    step_summary: Dict[str, int] = {}
    for step in steps:
        status = str(step.get("status") or "unknown")
        step_summary[status] = step_summary.get(status, 0) + 1
    return {
        "id": run.get("id"),
        "status": run.get("status"),
        "triggerSource": run.get("trigger_source"),
        "errorMessage": run.get("error_message"),
        "startedAt": run.get("started_at"),
        "finishedAt": run.get("finished_at"),
        "stepSummary": step_summary,
        "failedSteps": [
            {
                "id": step.get("id"),
                "stepKey": step.get("step_key"),
                "stage": step.get("stage"),
                "status": step.get("status"),
                "errorMessage": step.get("error_message"),
            }
            for step in steps
            if step.get("status") in {"failed", "blocked"}
        ],
    }


def _source_account_summary(account: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": account.get("id"),
        "sourceType": account.get("source_type"),
        "label": account.get("label"),
        "status": account.get("status"),
        "lastSeenAt": account.get("last_seen_at"),
        "lastScanAt": account.get("last_scan_at"),
        "documentsSeen": account.get("documents_seen"),
        "documentsImported": account.get("documents_imported"),
        "duplicatesDetected": account.get("duplicates_detected"),
    }


def _entity_references(issues: List[Dict[str, Any]]) -> Dict[str, List[int]]:
    references: Dict[str, List[int]] = {}
    for issue in issues:
        entity_type = str(issue.get("entityType") or "")
        try:
            entity_id = int(issue.get("entityId"))
        except (TypeError, ValueError):
            continue
        references.setdefault(entity_type, []).append(entity_id)
    return references


def _bounded_limit(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = 50
    return max(1, min(parsed, 500))


def _prioritized_issues(issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    severity_order = {"high": 0, "medium": 1, "low": 2}
    return sorted(
        issues,
        key=lambda issue: severity_order.get(str(issue.get("severity") or ""), 3),
    )
