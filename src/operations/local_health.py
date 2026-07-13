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
DEFERRED_EXPORT_STATUSES = ("deferred",)
REPORT_ATTENTION_STATUSES = ("failed", "prepared_needs_review", "running")


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
        self.wave_entity_sync_stale_hours = _float_config(
            self.config,
            "fab_local_wave_entity_sync_stale_hours",
            "operations_wave_entity_sync_stale_hours",
            "wave_entity_sync_stale_hours",
            default=24.0,
        )
        self.report_stale_hours = _float_config(
            self.config,
            "fab_local_report_stale_hours",
            "operations_report_stale_hours",
            "report_stale_hours",
            default=2.0,
        )
        self.invoice_due_soon_days = _float_config(
            self.config,
            "fab_invoice_due_soon_days",
            "operations_invoice_due_soon_days",
            "invoice_due_soon_days",
            default=7.0,
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
        deferred_exports = self.ledger.list_export_attempts(status=DEFERRED_EXPORT_STATUSES, limit=500)
        failed_exports = self.ledger.list_export_attempts(status="failed", limit=500)
        wave_sync_runs = self.ledger.list_wave_sync_runs(limit=100)
        wave_invoices = self.ledger.list_wave_entities(
            entity_type="invoice",
            presence_status="present",
            limit=500,
        )
        report_runs = self.ledger.list_financial_report_runs(status=REPORT_ATTENTION_STATUSES, limit=100)
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

        for export_attempt in deferred_exports:
            metadata = export_attempt.get("metadata") if isinstance(export_attempt.get("metadata"), dict) else {}
            retry = metadata.get("retry") if isinstance(metadata.get("retry"), dict) else {}
            next_retry_at = _parse_datetime(retry.get("nextRetryAt"))
            if next_retry_at and next_retry_at <= now:
                issues.append(_issue(
                    "low",
                    "deferred_export_retry_due",
                    "export_attempt",
                    export_attempt.get("id"),
                    f"Deferred export attempt #{export_attempt.get('id')} is ready for retry.",
                    _age_hours(retry.get("nextRetryAt"), now),
                    {
                        "documentId": export_attempt.get("document_id"),
                        "reason": retry.get("reason"),
                        "nextRetryAt": retry.get("nextRetryAt"),
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

        for report_run in report_runs:
            report_status = str(report_run.get("status") or "unknown")
            if report_status == "failed":
                issues.append(_issue(
                    "medium",
                    "failed_financial_report_run",
                    "financial_report_run",
                    report_run.get("id"),
                    f"Scheduled financial report #{report_run.get('id')} failed generation.",
                    _age_hours(report_run.get("updated_at"), now),
                    {
                        "scheduleId": report_run.get("schedule_id"),
                        "scheduleSlot": report_run.get("schedule_slot"),
                        "nextRetryAt": report_run.get("next_retry_at"),
                        "error": report_run.get("error_message"),
                    },
                ))
            elif report_status == "prepared_needs_review":
                issues.append(_issue(
                    "low",
                    "financial_report_needs_review",
                    "financial_report_run",
                    report_run.get("id"),
                    f"Scheduled financial report #{report_run.get('id')} has completeness blockers.",
                    _age_hours(report_run.get("finished_at") or report_run.get("updated_at"), now),
                    {
                        "scheduleId": report_run.get("schedule_id"),
                        "scheduleSlot": report_run.get("schedule_slot"),
                        "blockerCount": report_run.get("blocker_count"),
                    },
                ))
            elif report_status == "running":
                age_hours = _age_hours(report_run.get("started_at"), now)
                if age_hours is not None and age_hours >= self.report_stale_hours:
                    issues.append(_issue(
                        "high",
                        "stale_financial_report_run",
                        "financial_report_run",
                        report_run.get("id"),
                        f"Scheduled financial report #{report_run.get('id')} has been running for {age_hours:.1f} hours.",
                        age_hours,
                        {
                            "scheduleId": report_run.get("schedule_id"),
                            "scheduleSlot": report_run.get("schedule_slot"),
                        },
                    ))

        latest_wave_sync_by_target: Dict[str, Dict[str, Any]] = {}
        for sync_run in wave_sync_runs:
            latest_wave_sync_by_target.setdefault(str(sync_run.get("target_system") or "waveapps"), sync_run)
        for target_system, sync_run in latest_wave_sync_by_target.items():
            sync_status = str(sync_run.get("status") or "unknown")
            age_hours = _age_hours(sync_run.get("finished_at") or sync_run.get("started_at"), now)
            if sync_status not in {"completed", "running"}:
                issues.append(_issue(
                    "medium",
                    "failed_wave_entity_sync",
                    "wave_sync_run",
                    sync_run.get("id"),
                    f"Latest Wave entity sync for {target_system} ended as {sync_status}.",
                    age_hours,
                    {"targetSystem": target_system, "status": sync_status, "error": sync_run.get("error_message")},
                ))
            elif age_hours is not None and age_hours >= self.wave_entity_sync_stale_hours:
                issues.append(_issue(
                    "low",
                    "stale_wave_entity_sync",
                    "wave_sync_run",
                    sync_run.get("id"),
                    f"Wave entity mirror for {target_system} is {age_hours:.1f} hours old.",
                    age_hours,
                    {"targetSystem": target_system, "status": sync_status},
                ))

        settled_invoice_statuses = {"paid", "cancelled", "canceled", "void", "deleted"}
        for invoice in wave_invoices:
            invoice_status = str(invoice.get("status") or "unknown").strip().lower()
            if invoice_status in settled_invoice_statuses:
                continue
            due_date = _parse_date(invoice.get("due_date"))
            if not due_date:
                continue
            days_until_due = (due_date - now.date()).days
            invoice_label = invoice.get("name") or invoice.get("external_id") or invoice.get("id")
            if days_until_due < 0:
                issues.append(_issue(
                    "medium",
                    "wave_invoice_overdue",
                    "wave_entity",
                    invoice.get("id"),
                    f"Wave invoice {invoice_label} is {abs(days_until_due)} day(s) overdue.",
                    abs(days_until_due) * 24.0,
                    {
                        "targetSystem": invoice.get("target_system"),
                        "externalId": invoice.get("external_id"),
                        "dueDate": invoice.get("due_date"),
                        "status": invoice.get("status"),
                        "amount": invoice.get("amount"),
                        "currency": invoice.get("currency"),
                    },
                ))
            elif days_until_due <= self.invoice_due_soon_days:
                issues.append(_issue(
                    "low",
                    "wave_invoice_due_soon",
                    "wave_entity",
                    invoice.get("id"),
                    f"Wave invoice {invoice_label} is due in {days_until_due} day(s).",
                    None,
                    {
                        "targetSystem": invoice.get("target_system"),
                        "externalId": invoice.get("external_id"),
                        "dueDate": invoice.get("due_date"),
                        "daysUntilDue": days_until_due,
                        "status": invoice.get("status"),
                        "amount": invoice.get("amount"),
                        "currency": invoice.get("currency"),
                    },
                ))

        missing_wave_entities = int(metrics.get("wave_entities_missing_downstream") or 0)
        if missing_wave_entities:
            issues.append(_issue(
                "medium",
                "wave_entities_missing_downstream",
                "wave_entity",
                "missing_downstream",
                f"{missing_wave_entities} mirrored Wave record(s) are no longer present downstream.",
                None,
                {"count": missing_wave_entities},
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
                "waveEntitySyncStaleHours": self.wave_entity_sync_stale_hours,
                "reportStaleHours": self.report_stale_hours,
                "invoiceDueSoonDays": self.invoice_due_soon_days,
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
                "deferredExports": len(deferred_exports),
                "deferredExportsDue": _issue_count(issues, "deferred_export_retry_due"),
                "failedExports": len(failed_exports),
                "waveEntitySyncRuns": len(wave_sync_runs),
                "waveEntitySyncFailures": _issue_count(issues, "failed_wave_entity_sync"),
                "financialReportRuns": metrics.get("financial_report_runs", 0),
                "financialReportRunsNeedingAttention": metrics.get("financial_report_runs_needing_attention", 0),
                "failedFinancialReportRuns": _issue_count(issues, "failed_financial_report_run"),
                "staleFinancialReportRuns": _issue_count(issues, "stale_financial_report_run"),
                "waveEntities": metrics.get("wave_entities", 0),
                "waveEntitiesMissingDownstream": missing_wave_entities,
                "waveInvoicesOverdue": _issue_count(issues, "wave_invoice_overdue"),
                "waveInvoicesDueSoon": _issue_count(issues, "wave_invoice_due_soon"),
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
    if "deferred_export_retry_due" in issue_types:
        actions.append("Run the approved-export worker to retry due quota-deferred Wave attempts.")
    if "failed_export_attempt" in issue_types:
        actions.append("Inspect failed export attempts and retry after fixing the source issue.")
    if "failed_wave_entity_sync" in issue_types or "stale_wave_entity_sync" in issue_types:
        actions.append("Refresh the Wave entity mirror and inspect the latest sync run before creating downstream records.")
    if "wave_entities_missing_downstream" in issue_types:
        actions.append("Review Wave records marked missing downstream before reusing their customer, product, or invoice IDs.")
    if "master_ledger_blockers" in issue_types:
        actions.append("Open the master ledger projection and resolve blocked rows before close or downstream execution.")
    if "wave_invoice_overdue" in issue_types or "wave_invoice_due_soon" in issue_types:
        actions.append("Open Wave invoice evidence, confirm payment state, and approve any reminder or follow-up separately.")
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


def _parse_date(value: Any):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
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
