from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from src.operations.local_health import LocalOperationsHealth
from src.operations.local_ledger import LocalOperationsLedger
from src.operations.local_master_ledger import LocalMasterLedgerService
from src.operations.local_wave_control import LocalWaveControlService


class LocalCloseReadinessService:
    """Assess whether FAB has enough evidence to close a period safely."""

    def __init__(self, ledger: LocalOperationsLedger, config: Optional[Dict[str, Any]] = None):
        self.ledger = ledger
        self.config = config or {}

    def assess(
        self,
        workflow_id: str = "daily_reconciliation_run",
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        workflow_id = str(workflow_id or "daily_reconciliation_run")
        from_date = from_date or date.today().isoformat()
        to_date = to_date or from_date
        metrics = self.ledger.dashboard_metrics()
        health = LocalOperationsHealth(self.ledger, self.config).summarize()
        master_ledger = LocalMasterLedgerService(self.ledger, self.config).project(limit=500)
        report_controls = LocalWaveControlService(self.config).evaluate_report_controls(
            self.ledger,
            workflow_id=workflow_id,
        )
        gates = _close_gates(metrics, health, report_controls, master_ledger)
        blocking_gates = [gate for gate in gates if gate["status"] == "blocked"]
        attention_gates = [gate for gate in gates if gate["status"] == "attention"]
        if blocking_gates:
            status = "blocked"
        elif attention_gates:
            status = "attention"
        else:
            status = "ready"
        return {
            "status": status,
            "workflowId": workflow_id,
            "fromDate": from_date,
            "toDate": to_date,
            "externalSubmission": "not_executed",
            "canClose": status == "ready",
            "blockingCount": len(blocking_gates),
            "attentionCount": len(attention_gates),
            "gates": gates,
            "reportControls": {
                "status": report_controls.get("status"),
                "requiredReportCount": report_controls.get("requiredReportCount"),
                "coveredReportCount": report_controls.get("coveredReportCount"),
                "readyReportCount": report_controls.get("readyReportCount"),
                "blockingCount": report_controls.get("blockingCount"),
                "resultGapCount": report_controls.get("resultGapCount"),
            },
            "masterLedger": _compact_master_ledger(master_ledger),
            "metrics": {
                "pendingReview": metrics.get("pending_review", 0),
                "unreconciledDocuments": metrics.get("unreconciled_documents", 0),
                "unreconciledBankTransactions": metrics.get("unreconciled_bank_transactions", 0),
                "exportApprovals": metrics.get("export_attempts_needing_approval", 0),
                "failedDocuments": metrics.get("failed_documents", 0),
                "routingBlocks": health.get("metrics", {}).get("routingBlocks", 0),
                "masterLedgerRows": master_ledger.get("summary", {}).get("totalRows", 0),
                "masterLedgerBlockedRows": master_ledger.get("summary", {}).get("blockedRows", 0),
                "masterLedgerReadyForApproval": master_ledger.get("summary", {}).get("readyForApproval", 0),
                "masterLedgerReadyForExternalExecution": master_ledger.get("summary", {}).get("readyForExternalExecution", 0),
            },
            "nextActions": _next_actions(status, blocking_gates, attention_gates, report_controls),
        }


def _close_gates(
    metrics: Dict[str, Any],
    health: Dict[str, Any],
    report_controls: Dict[str, Any],
    master_ledger: Dict[str, Any],
) -> List[Dict[str, Any]]:
    health_metrics = health.get("metrics") or {}
    master_summary = master_ledger.get("summary") or {}
    return [
        _gate(
            "wave_report_evidence",
            "Wave report evidence",
            "ready" if report_controls.get("status") == "ready" else "blocked",
            report_controls.get("status"),
            {
                "requiredReportCount": report_controls.get("requiredReportCount"),
                "readyReportCount": report_controls.get("readyReportCount"),
                "resultGapCount": report_controls.get("resultGapCount"),
                "blockingCount": report_controls.get("blockingCount"),
            },
        ),
        _count_gate(
            "manual_review_queue",
            "Manual review queue",
            int(metrics.get("pending_review") or 0),
            "pending review items",
        ),
        _count_gate(
            "bank_reconciliation",
            "Bank reconciliation",
            int(metrics.get("unreconciled_bank_transactions") or 0),
            "unreconciled bank transactions",
        ),
        _count_gate(
            "document_reconciliation",
            "Document reconciliation",
            int(metrics.get("unreconciled_documents") or 0),
            "unreconciled documents",
        ),
        _count_gate(
            "export_approvals",
            "Export approvals",
            int(metrics.get("export_attempts_needing_approval") or 0),
            "export approvals waiting",
        ),
        _count_gate(
            "failed_documents",
            "Failed documents",
            int(metrics.get("failed_documents") or 0),
            "failed documents",
        ),
        _count_gate(
            "routing_blocks",
            "Routing blocks",
            int(health_metrics.get("routingBlocks") or 0),
            "routing blocks",
        ),
        _gate(
            "master_ledger_projection",
            "Master ledger projection",
            "blocked" if int(master_summary.get("blockedRows") or 0) > 0 else "ready",
            "clear" if int(master_summary.get("blockedRows") or 0) == 0
            else f"{master_summary.get('blockedRows')} blocked master-ledger rows",
            {
                "ledgerChecksum": master_ledger.get("ledgerChecksum"),
                "totalRows": master_summary.get("totalRows", 0),
                "blockedRows": master_summary.get("blockedRows", 0),
                "readyForDraft": master_summary.get("readyForDraft", 0),
                "readyForApproval": master_summary.get("readyForApproval", 0),
                "readyForExternalExecution": master_summary.get("readyForExternalExecution", 0),
                "downstreamStatuses": master_summary.get("downstreamStatuses") or {},
                "blockers": master_summary.get("blockers") or {},
            },
        ),
        _gate(
            "operations_health",
            "Operations health",
            "blocked" if health.get("status") == "blocked" else ("attention" if health.get("status") == "attention" else "ready"),
            health.get("status"),
            {
                "high": (health.get("severityCounts") or {}).get("high", 0),
                "medium": (health.get("severityCounts") or {}).get("medium", 0),
                "low": (health.get("severityCounts") or {}).get("low", 0),
            },
        ),
    ]


def _count_gate(gate_id: str, label: str, count: int, noun: str) -> Dict[str, Any]:
    return _gate(
        gate_id,
        label,
        "blocked" if count > 0 else "ready",
        "clear" if count == 0 else f"{count} {noun}",
        {"count": count},
    )


def _gate(gate_id: str, label: str, status: str, message: Any, evidence: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": gate_id,
        "label": label,
        "status": status,
        "message": str(message or status),
        "evidence": evidence,
    }


def _next_actions(
    status: str,
    blocking_gates: List[Dict[str, Any]],
    attention_gates: List[Dict[str, Any]],
    report_controls: Dict[str, Any],
) -> List[str]:
    if status == "ready":
        return ["Close readiness passed. Keep external submission approval-gated and archive the supporting report evidence."]
    actions: List[str] = []
    blocked_ids = {gate["id"] for gate in blocking_gates}
    if "wave_report_evidence" in blocked_ids:
        actions.extend(report_controls.get("nextActions") or ["Capture required Wave report results before close."])
    if "manual_review_queue" in blocked_ids:
        actions.append("Resolve pending manual review items before close.")
    if "bank_reconciliation" in blocked_ids:
        actions.append("Resolve unreconciled bank transactions, including missing receipt exceptions.")
    if "document_reconciliation" in blocked_ids:
        actions.append("Reconcile or explicitly resolve all eligible source documents.")
    if "export_approvals" in blocked_ids:
        actions.append("Approve, reject, or execute pending export attempts before close.")
    if "failed_documents" in blocked_ids:
        actions.append("Fix or explicitly ignore failed document processing items.")
    if "routing_blocks" in blocked_ids:
        actions.append("Resolve routing blocks before close.")
    if "master_ledger_projection" in blocked_ids:
        actions.append("Resolve blocked master-ledger rows and regenerate the checksum-bound projection before close.")
    if not actions and attention_gates:
        actions.append("Review attention gates and record an audit decision before closing.")
    return actions


def _compact_master_ledger(master_ledger: Dict[str, Any]) -> Dict[str, Any]:
    summary = master_ledger.get("summary") or {}
    return {
        "projectionVersion": master_ledger.get("projectionVersion"),
        "ledgerChecksum": master_ledger.get("ledgerChecksum"),
        "externalSubmission": master_ledger.get("externalSubmission"),
        "totalRows": summary.get("totalRows", 0),
        "blockedRows": summary.get("blockedRows", 0),
        "readyForDraft": summary.get("readyForDraft", 0),
        "readyForApproval": summary.get("readyForApproval", 0),
        "readyForExternalExecution": summary.get("readyForExternalExecution", 0),
        "downstreamStatuses": summary.get("downstreamStatuses") or {},
        "byTargetSystem": summary.get("byTargetSystem") or {},
    }
