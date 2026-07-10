from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.operations.local_ledger import LocalOperationsLedger
from src.operations.local_master_ledger import LocalMasterLedgerService
from src.utils.rate_limiter import get_all_rates


OPEN_REVIEW_STATUSES = ("pending", "in_review")
STUCK_DOCUMENT_STATUSES = ("imported", "processing", "needs_review")
ROUTING_BLOCK_STATUSES = (
    "blocked_duplicate",
    "blocked_review",
    "blocked_status",
    "needs_review",
    "unsupported_target",
)
PENDING_ROUTING_STATUSES = ("draft_prepared", "needs_confirmation", "queued")
RUNNING_WORKFLOW_STATUSES = ("running",)
FAILED_WORKFLOW_STATUSES = ("failed", "error")
PENDING_EXPORT_APPROVAL_STATUSES = ("approval_required", "prepared")
APPROVED_EXPORT_STATUSES = ("approved",)
SUPERVISED_EXPORT_STATUSES = ("supervision_required",)
EXECUTING_EXPORT_STATUSES = ("execution_in_progress",)


class LocalOperationsHealth:
    """Summarize local FAB ledger health and operational exceptions."""

    def __init__(self, ledger: LocalOperationsLedger, config: Optional[Dict[str, Any]] = None):
        self.ledger = ledger
        self.config = config or {}
        self.review_stale_hours = _float_config(
            self.config,
            "fab_local_review_stale_hours",
            "operations_review_stale_hours",
            "review_stale_hours",
            default=48.0,
        )
        self.document_stale_hours = _float_config(
            self.config,
            "fab_local_document_stale_hours",
            "operations_document_stale_hours",
            "document_stale_hours",
            default=24.0,
        )
        self.routing_stale_hours = _float_config(
            self.config,
            "fab_local_routing_stale_hours",
            "operations_routing_stale_hours",
            "routing_stale_hours",
            default=24.0,
        )
        self.workflow_stale_hours = _float_config(
            self.config,
            "fab_local_workflow_stale_hours",
            "operations_workflow_stale_hours",
            "workflow_stale_hours",
            default=6.0,
        )
        self.export_approval_stale_hours = _float_config(
            self.config,
            "fab_local_export_approval_stale_hours",
            "operations_export_approval_stale_hours",
            "export_approval_stale_hours",
            default=24.0,
        )
        self.export_approved_stale_hours = _float_config(
            self.config,
            "fab_local_export_approved_stale_hours",
            "operations_export_approved_stale_hours",
            "export_approved_stale_hours",
            default=48.0,
        )
        self.export_execution_stale_hours = _float_config(
            self.config,
            "fab_local_export_execution_stale_hours",
            "operations_export_execution_stale_hours",
            "export_execution_stale_hours",
            default=1.0,
        )

    def summarize(self) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        metrics = self.ledger.dashboard_metrics()
        review_items = self.ledger.list_review_items(status=OPEN_REVIEW_STATUSES, limit=500)
        stuck_documents = self.ledger.list_documents(status=STUCK_DOCUMENT_STATUSES, limit=500)
        failed_documents = self.ledger.list_documents(status="failed", limit=500)
        routing_blocks = self.ledger.list_routing_attempts(status=ROUTING_BLOCK_STATUSES, limit=500)
        pending_routes = self.ledger.list_routing_attempts(status=PENDING_ROUTING_STATUSES, limit=500)
        running_runs = self.ledger.list_workflow_runs(status=RUNNING_WORKFLOW_STATUSES, limit=100)
        failed_runs = self.ledger.list_workflow_runs(status=FAILED_WORKFLOW_STATUSES, limit=100)
        pending_export_approvals = self.ledger.list_export_attempts(status=PENDING_EXPORT_APPROVAL_STATUSES, limit=500)
        approved_exports = self.ledger.list_export_attempts(status=APPROVED_EXPORT_STATUSES, limit=500)
        supervised_exports = self.ledger.list_export_attempts(status=SUPERVISED_EXPORT_STATUSES, limit=500)
        executing_exports = self.ledger.list_export_attempts(status=EXECUTING_EXPORT_STATUSES, limit=500)
        failed_exports = self.ledger.list_export_attempts(status="failed", limit=500)
        master_ledger = LocalMasterLedgerService(self.ledger, self.config).project(limit=500)
        master_ledger_summary = master_ledger.get("summary") or {}
        rate_limits = get_all_rates()

        issues: List[Dict[str, Any]] = []
        if int(master_ledger_summary.get("blockedRows") or 0) > 0:
            issues.append(_issue(
                "medium",
                "master_ledger_blockers",
                "master_ledger",
                master_ledger.get("ledgerChecksum"),
                f"Master ledger projection has {master_ledger_summary.get('blockedRows')} blocked row(s).",
                None,
                {
                    "ledgerChecksum": master_ledger.get("ledgerChecksum"),
                    "blockedRows": master_ledger_summary.get("blockedRows"),
                    "blockers": master_ledger_summary.get("blockers") or {},
                    "externalSubmission": "not_executed",
                },
            ))
        for item in review_items:
            age_hours = _age_hours(item.get("created_at"), now)
            if age_hours is not None and age_hours >= self.review_stale_hours:
                issues.append(_issue(
                    "medium",
                    "stale_review_item",
                    "review_item",
                    item.get("id"),
                    f"Review item #{item.get('id')} has been open for {age_hours:.1f} hours.",
                    age_hours,
                    {"documentId": item.get("document_id"), "reason": item.get("reason")},
                ))

        for document in stuck_documents:
            age_hours = _age_hours(document.get("updated_at"), now)
            status = document.get("processing_status")
            if age_hours is not None and age_hours >= self.document_stale_hours:
                issues.append(_issue(
                    "medium",
                    "stuck_document",
                    "bookkeeping_document",
                    document.get("id"),
                    f"Document #{document.get('id')} is still {status} after {age_hours:.1f} hours.",
                    age_hours,
                    {"status": status, "filename": document.get("original_filename")},
                ))

        for document in failed_documents:
            issues.append(_issue(
                "high",
                "failed_document",
                "bookkeeping_document",
                document.get("id"),
                f"Document #{document.get('id')} failed processing.",
                _age_hours(document.get("updated_at"), now),
                {"filename": document.get("original_filename")},
            ))

        for route in routing_blocks:
            issues.append(_issue(
                "medium",
                "routing_block",
                "routing_attempt",
                route.get("id"),
                f"Routing attempt #{route.get('id')} is blocked: {route.get('status')}.",
                _age_hours(route.get("created_at"), now),
                {"documentId": route.get("document_id"), "message": route.get("message")},
            ))

        stale_pending_routes = []
        for route in pending_routes:
            age_hours = _age_hours(route.get("created_at"), now)
            if age_hours is not None and age_hours >= self.routing_stale_hours:
                stale_pending_routes.append(route)
                issues.append(_issue(
                    "low",
                    "stale_routing_draft",
                    "routing_attempt",
                    route.get("id"),
                    f"Prepared routing attempt #{route.get('id')} has waited {age_hours:.1f} hours for approval/export.",
                    age_hours,
                    {"documentId": route.get("document_id"), "target": route.get("target")},
                ))

        for export_attempt in pending_export_approvals:
            age_hours = _age_hours(export_attempt.get("created_at"), now)
            if age_hours is not None and age_hours >= self.export_approval_stale_hours:
                issues.append(_issue(
                    "low",
                    "stale_export_approval",
                    "export_attempt",
                    export_attempt.get("id"),
                    f"Export attempt #{export_attempt.get('id')} has waited {age_hours:.1f} hours for approval.",
                    age_hours,
                    {
                        "documentId": export_attempt.get("document_id"),
                        "routingAttemptId": export_attempt.get("routing_attempt_id"),
                        "status": export_attempt.get("status"),
                    },
                ))

        for export_attempt in approved_exports:
            age_hours = _age_hours(export_attempt.get("updated_at"), now)
            if age_hours is not None and age_hours >= self.export_approved_stale_hours:
                issues.append(_issue(
                    "medium",
                    "stale_export_approved",
                    "export_attempt",
                    export_attempt.get("id"),
                    f"Export attempt #{export_attempt.get('id')} has been approved for {age_hours:.1f} hours without submission.",
                    age_hours,
                    {
                        "documentId": export_attempt.get("document_id"),
                        "routingAttemptId": export_attempt.get("routing_attempt_id"),
                    },
                ))

        for export_attempt in executing_exports:
            age_hours = _age_hours(export_attempt.get("updated_at"), now)
            if age_hours is not None and age_hours >= self.export_execution_stale_hours:
                issues.append(_issue(
                    "high",
                    "stuck_export_execution",
                    "export_attempt",
                    export_attempt.get("id"),
                    f"Export attempt #{export_attempt.get('id')} has been executing for {age_hours:.1f} hours.",
                    age_hours,
                    {
                        "documentId": export_attempt.get("document_id"),
                        "routingAttemptId": export_attempt.get("routing_attempt_id"),
                    },
                ))

        for export_attempt in failed_exports:
            issues.append(_issue(
                "high",
                "failed_export_attempt",
                "export_attempt",
                export_attempt.get("id"),
                f"Export attempt #{export_attempt.get('id')} was recorded as failed.",
                _age_hours(export_attempt.get("updated_at"), now),
                {"documentId": export_attempt.get("document_id"), "message": export_attempt.get("message")},
            ))

        for run in running_runs:
            age_hours = _age_hours(run.get("started_at") or run.get("created_at"), now)
            if age_hours is not None and age_hours >= self.workflow_stale_hours:
                issues.append(_issue(
                    "high",
                    "stale_workflow_run",
                    "workflow_run",
                    run.get("id"),
                    f"Workflow run #{run.get('id')} has been running for {age_hours:.1f} hours.",
                    age_hours,
                    {"triggerSource": run.get("trigger_source")},
                ))

        for run in failed_runs:
            issues.append(_issue(
                "medium",
                "failed_workflow_run",
                "workflow_run",
                run.get("id"),
                f"Workflow run #{run.get('id')} ended as {run.get('status')}.",
                _age_hours(run.get("updated_at"), now),
                {"errorMessage": run.get("error_message")},
            ))

        exhausted_limiters = [name for name, rate in rate_limits.items() if rate.get("quotaExhausted")]
        if exhausted_limiters:
            issues.append(_issue(
                "high",
                "api_quota_exhausted",
                "rate_limiter",
                ",".join(exhausted_limiters),
                "One or more downstream API quotas are exhausted.",
                None,
                {"services": exhausted_limiters},
            ))

        severity_counts = _severity_counts(issues)
        status = "ok"
        if severity_counts["high"]:
            status = "blocked"
        elif severity_counts["medium"] or severity_counts["low"]:
            status = "attention"

        return {
            "status": status,
            "generatedAt": now.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "thresholds": {
                "reviewStaleHours": self.review_stale_hours,
                "documentStaleHours": self.document_stale_hours,
                "routingStaleHours": self.routing_stale_hours,
                "workflowStaleHours": self.workflow_stale_hours,
                "exportApprovalStaleHours": self.export_approval_stale_hours,
                "exportApprovedStaleHours": self.export_approved_stale_hours,
                "exportExecutionStaleHours": self.export_execution_stale_hours,
            },
            "metrics": {
                **metrics,
                "openReviewItems": len(review_items),
                "staleReviewItems": _issue_count(issues, "stale_review_item"),
                "stuckDocuments": _issue_count(issues, "stuck_document"),
                "failedDocuments": len(failed_documents),
                "routingBlocks": len(routing_blocks),
                "pendingRoutingDrafts": len(pending_routes),
                "staleRoutingDrafts": len(stale_pending_routes),
                "pendingExportApprovals": len(pending_export_approvals),
                "approvedExports": len(approved_exports),
                "supervisedExports": len(supervised_exports),
                "executingExports": len(executing_exports),
                "failedExports": len(failed_exports),
                "masterLedgerRows": master_ledger_summary.get("totalRows", 0),
                "masterLedgerBlockedRows": master_ledger_summary.get("blockedRows", 0),
                "masterLedgerReadyForDraft": master_ledger_summary.get("readyForDraft", 0),
                "masterLedgerReadyForApproval": master_ledger_summary.get("readyForApproval", 0),
                "masterLedgerReadyForExternalExecution": master_ledger_summary.get("readyForExternalExecution", 0),
                "runningWorkflowRuns": len(running_runs),
                "failedWorkflowRuns": len(failed_runs),
                "apiQuotaExhaustedServices": len(exhausted_limiters),
            },
            "rateLimits": rate_limits,
            "severityCounts": severity_counts,
            "issues": sorted(issues, key=_issue_sort_key),
            "nextActions": _next_actions(issues),
        }


def _issue(
    severity: str,
    issue_type: str,
    entity_type: str,
    entity_id: Any,
    message: str,
    age_hours: Optional[float],
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "severity": severity,
        "type": issue_type,
        "entityType": entity_type,
        "entityId": str(entity_id) if entity_id is not None else None,
        "message": message,
        "ageHours": round(age_hours, 2) if age_hours is not None else None,
        "details": details or {},
    }


def _issue_sort_key(issue: Dict[str, Any]) -> tuple:
    severity_rank = {"high": 0, "medium": 1, "low": 2}
    return (severity_rank.get(issue.get("severity"), 9), -(issue.get("ageHours") or 0))


def _severity_counts(issues: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {"high": 0, "medium": 0, "low": 0}
    for issue in issues:
        severity = issue.get("severity")
        if severity in counts:
            counts[severity] += 1
    return counts


def _issue_count(issues: List[Dict[str, Any]], issue_type: str) -> int:
    return sum(1 for issue in issues if issue.get("type") == issue_type)


def _next_actions(issues: List[Dict[str, Any]]) -> List[str]:
    issue_types = {issue.get("type") for issue in issues}
    actions = []
    if "failed_document" in issue_types:
        actions.append("Open failed documents, inspect processing errors, and re-run after fixing the source issue.")
    if "stale_workflow_run" in issue_types:
        actions.append("Check the workflow lock/process before starting another automated run.")
    if "stale_review_item" in issue_types or "stuck_document" in issue_types:
        actions.append("Review stale queue items or process imported documents from the dashboard.")
    if "routing_block" in issue_types:
        actions.append("Resolve routing blocks before preparing or exporting bookkeeping drafts.")
    if "stale_routing_draft" in issue_types:
        actions.append("Review prepared routing drafts and approve, export, or discard them.")
    if "stale_export_approval" in issue_types:
        actions.append("Review pending export attempts and approve or reject before external submission.")
    if "stale_export_approved" in issue_types:
        actions.append("Review approved export attempts that remain pending and decide whether to submit or cancel.")
    if "stuck_export_execution" in issue_types:
        actions.append("Inspect the claimed export attempt and verify downstream state before releasing or retrying it.")
    if "failed_export_attempt" in issue_types:
        actions.append("Inspect failed export attempts and retry after fixing the source issue.")
    if "master_ledger_blockers" in issue_types:
        actions.append("Open the master ledger projection and resolve blocked rows before close or downstream execution.")
    if "api_quota_exhausted" in issue_types:
        actions.append("Pause affected downstream sync jobs until the service quota window resets.")
    return actions


def _age_hours(value: Any, now: datetime) -> Optional[float]:
    parsed = _parse_datetime(value)
    if not parsed:
        return None
    return max(0.0, (now - parsed).total_seconds() / 3600)


def _parse_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return None
    text = str(value)
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _float_config(config: Dict[str, Any], *keys: str, default: float) -> float:
    for key in keys:
        value = config.get(key)
        if value not in (None, ""):
            try:
                return float(value)
            except (TypeError, ValueError):
                return default
    return default
