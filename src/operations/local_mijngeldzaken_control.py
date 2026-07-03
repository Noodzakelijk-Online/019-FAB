from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from src.data_entry.mijngeldzaken_autonomous_operator import MijngeldzakenAutonomousOperator
from src.data_entry.mijngeldzaken_surface import (
    MIJNGELDZAKEN_IMPORT_COLUMNS,
    MIJNGELDZAKEN_SURFACE_CATALOG,
    list_mijngeldzaken_actions,
    summarize_mijngeldzaken_parity,
)
from src.operations.local_master_ledger import LocalMasterLedgerService


DEFAULT_MGZ_WORKFLOW_ACTIONS: Dict[str, List[str]] = {
    "master_ledger_downstream_sync": [
        "current_month_read",
        "transaction_list_read",
        "account_list_read",
        "account_balance_read",
        "category_list_read",
        "budget_list_read",
        "budget_report_read",
        "cashflow_report_read",
        "transaction_export_download",
        "import_history_read",
        "import_mapping_prepare",
    ],
    "document_vault_sync": [
        "document_list_read",
        "contract_list_read",
        "receipt_list_read",
        "payslip_list_read",
    ],
    "planning_context_read": [
        "goal_list_read",
        "scenario_list_read",
        "mortgage_planning_read",
        "pension_planning_read",
        "savings_planning_read",
    ],
    "connection_health_check": [
        "data_connections_read",
        "profile_settings_read",
        "security_settings_read",
        "account_update_prompt_read",
    ],
}


class LocalMijngeldzakenControlService:
    """Expose MijnGeldzaken as a policy-gated downstream surface for FAB."""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        operator: Optional[MijngeldzakenAutonomousOperator] = None,
    ):
        self.config = config or {}
        self.operator = operator or MijngeldzakenAutonomousOperator(self.config)

    def overview(self, ledger: Optional[Any] = None) -> Dict[str, Any]:
        overview = {
            "status": "modeled",
            "externalSubmission": "not_executed",
            "summary": summarize_mijngeldzaken_parity(),
            "credentials": _credential_status(self.config),
            "safetyPolicy": {
                "read_only": "FAB may read modeled page/report state without changing MijnGeldzaken.",
                "safe_draft": "FAB may prepare local import files, mappings, and upload drafts.",
                "requires_confirmation": "FAB blocks external changes until a user confirms the exact action.",
                "requires_credentials": "FAB keeps account login and security steps user-owned.",
                "unsupported": "FAB records the surface but does not automate it.",
            },
            "modules": MIJNGELDZAKEN_SURFACE_CATALOG["modules"],
            "syncContracts": MIJNGELDZAKEN_SURFACE_CATALOG["sync_contracts"],
            "featureInventory": MIJNGELDZAKEN_SURFACE_CATALOG["feature_inventory"],
            "workflows": [
                {
                    "id": "master_ledger_downstream_sync",
                    "label": "Master ledger downstream sync",
                    "mode": "read_only_and_safe_draft",
                    "defaultActions": DEFAULT_MGZ_WORKFLOW_ACTIONS["master_ledger_downstream_sync"],
                },
                {
                    "id": "document_vault_sync",
                    "label": "Document vault evidence sync",
                    "mode": "read_only",
                    "defaultActions": DEFAULT_MGZ_WORKFLOW_ACTIONS["document_vault_sync"],
                },
                {
                    "id": "planning_context_read",
                    "label": "Planning and advice context read",
                    "mode": "read_only",
                    "defaultActions": DEFAULT_MGZ_WORKFLOW_ACTIONS["planning_context_read"],
                },
                {
                    "id": "connection_health_check",
                    "label": "Connection and account health check",
                    "mode": "read_only",
                    "defaultActions": DEFAULT_MGZ_WORKFLOW_ACTIONS["connection_health_check"],
                },
            ],
            "nextActions": [
                "Use /api/mijngeldzaken/workflows/plan to prepare a modeled MGZ read/sync run.",
                "Use /api/mijngeldzaken/plan for a single policy-gated MGZ action.",
                "Use FAB export approvals for master-ledger rows before any MGZ import/upload is executed.",
            ],
        }
        if ledger is not None:
            overview["masterLedgerControls"] = self.evaluate_master_ledger_controls(ledger)
        return overview

    def actions(
        self,
        surface: Optional[str] = None,
        safety: Optional[str] = None,
        mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        actions = list_mijngeldzaken_actions(surface=surface)
        if safety:
            actions = [action for action in actions if action.get("safety") == safety]
        if mode:
            actions = [action for action in actions if action.get("mode") == mode]
        return {
            "surface": surface,
            "safety": safety,
            "mode": mode,
            "count": len(actions),
            "actions": actions,
            "externalSubmission": "not_executed",
        }

    def plan_action(self, request_payload: Dict[str, Any]) -> Dict[str, Any]:
        action_id = _coalesce(request_payload, "actionId", "action_id")
        if not action_id:
            return {
                "success": False,
                "status": "unsupported",
                "error": "actionId is required.",
                "externalSubmission": "not_executed",
            }
        payload = request_payload.get("payload") or {}
        if not isinstance(payload, dict):
            return {
                "success": False,
                "status": "invalid_payload",
                "error": "payload must be an object.",
                "externalSubmission": "not_executed",
            }
        action = MIJNGELDZAKEN_SURFACE_CATALOG["actions"].get(str(action_id), {})
        operation = self.operator.prepare_operation(
            str(action_id),
            payload,
            surface=_coalesce(request_payload, "surface", "mijngeldzakenSurface") or action.get("surface"),
            actor=str(request_payload.get("actor") or "fab_mijngeldzaken_control"),
            idempotency_key=request_payload.get("idempotencyKey"),
            allow_write=bool(request_payload.get("allowWrite", False)),
        )
        return _operation_response(operation)

    def plan_workflow(self, request_payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        request_payload = request_payload or {}
        workflow_id = str(
            _coalesce(request_payload, "workflowId", "workflow_id")
            or "master_ledger_downstream_sync"
        )
        actions = DEFAULT_MGZ_WORKFLOW_ACTIONS.get(workflow_id)
        if not actions:
            return {
                "success": False,
                "status": "unsupported",
                "workflowPlan": {"workflowId": workflow_id},
                "operations": [],
                "operationCount": 0,
                "externalSubmission": "not_executed",
                "error": "MijnGeldzaken workflow is not modeled in FAB.",
            }
        from_date = str(_coalesce(request_payload, "fromDate", "from_date") or _today())
        to_date = str(_coalesce(request_payload, "toDate", "to_date") or from_date)
        operations = [
            self.operator.prepare_operation(
                action_id,
                _workflow_payload(action_id, from_date, to_date, request_payload),
                surface=(MIJNGELDZAKEN_SURFACE_CATALOG["actions"].get(action_id) or {}).get("surface"),
                actor=str(request_payload.get("actor") or "fab_mijngeldzaken_control"),
                idempotency_key=request_payload.get("idempotencyKey"),
            )
            for action_id in actions
        ]
        blocking = [operation for operation in operations if (operation.get("plan") or {}).get("status") != "planned"]
        return {
            "success": not blocking,
            "status": "ready" if not blocking else "needs_review",
            "workflowPlan": {
                "workflowId": workflow_id,
                "fromDate": from_date,
                "toDate": to_date,
                "actionCount": len(actions),
            },
            "operations": operations,
            "operationCount": len(operations),
            "blockingOperations": [
                {
                    "actionId": operation.get("action_id"),
                    "surface": operation.get("surface"),
                    "status": (operation.get("plan") or {}).get("status"),
                    "missingFields": (operation.get("plan") or {}).get("missing_fields") or [],
                }
                for operation in blocking
            ],
            "externalSubmission": "not_executed",
            "guardrail": "Prepared only. FAB has not read from or written to MijnGeldzaken.",
        }

    def evaluate_master_ledger_controls(self, ledger: Any, limit: int = 500) -> Dict[str, Any]:
        projection = LocalMasterLedgerService(ledger, self.config).project(target_system="mijngeldzaken", limit=limit)
        summary = projection.get("summary") or {}
        rows = projection.get("rows") or []
        blocked_rows = int(summary.get("blockedRows") or 0)
        ready_for_draft = int(summary.get("readyForDraft") or 0)
        ready_for_approval = int(summary.get("readyForApproval") or 0)
        ready_for_execution = int(summary.get("readyForExternalExecution") or 0)
        stale_rows = int((summary.get("blockers") or {}).get("stale_master_ledger_draft") or 0)
        if not rows:
            status = "no_mijngeldzaken_rows"
        elif blocked_rows:
            status = "blocked_master_ledger"
        elif ready_for_draft:
            status = "ready_for_draft_preparation"
        elif ready_for_approval:
            status = "awaiting_export_approval"
        elif ready_for_execution:
            status = "awaiting_external_execution"
        else:
            status = "ready"
        return {
            "status": status,
            "targetSystem": "mijngeldzaken",
            "ledgerChecksum": projection.get("ledgerChecksum"),
            "rowCount": len(rows),
            "blockingCount": blocked_rows,
            "readyForDraft": ready_for_draft,
            "readyForApproval": ready_for_approval,
            "readyForExternalExecution": ready_for_execution,
            "staleDrafts": stale_rows,
            "gates": [
                _gate(
                    "source_records",
                    "MGZ source records",
                    "ready" if rows else "empty",
                    len(rows),
                    "Normalized FAB rows targeting MijnGeldzaken.",
                ),
                _gate(
                    "master_ledger_blockers",
                    "Master-ledger blockers",
                    "blocked" if blocked_rows else "ready",
                    blocked_rows,
                    "Rows blocked by review, reconciliation, export, or stale-draft issues.",
                ),
                _gate(
                    "draft_preparation",
                    "Draft preparation",
                    "ready_for_draft" if ready_for_draft else "ready",
                    ready_for_draft,
                    "Rows that can become MGZ import/upload drafts.",
                ),
                _gate(
                    "approval_required",
                    "Approval required",
                    "awaiting_approval" if ready_for_approval else "ready",
                    ready_for_approval,
                    "Prepared MGZ drafts waiting for FAB export approval.",
                ),
                _gate(
                    "external_execution",
                    "External execution",
                    "awaiting_execution" if ready_for_execution else "ready",
                    ready_for_execution,
                    "Approved MGZ drafts waiting for a browser/API executor.",
                ),
                _gate(
                    "stale_drafts",
                    "Stale draft protection",
                    "blocked" if stale_rows else "ready",
                    stale_rows,
                    "MGZ drafts whose current FAB row checksum no longer matches the approved draft.",
                ),
            ],
            "nextActions": _next_actions(status, ready_for_draft, ready_for_approval, ready_for_execution, blocked_rows),
            "externalSubmission": "not_executed",
        }


def _operation_response(operation: Dict[str, Any]) -> Dict[str, Any]:
    plan = operation.get("plan") or {}
    status = plan.get("status") or "unknown"
    return {
        "success": status == "planned",
        "status": status,
        "externalSubmission": "not_executed",
        "operation": operation,
        "guardrail": "Prepared only. External MijnGeldzaken execution remains approval-gated.",
    }


def _workflow_payload(action_id: str, from_date: str, to_date: str, request_payload: Dict[str, Any]) -> Dict[str, Any]:
    if action_id == "transaction_export_download":
        return {
            "dateRange": {
                "fromDate": from_date,
                "toDate": to_date,
            },
            "format": request_payload.get("format") or "csv",
        }
    if action_id == "import_mapping_prepare":
        return {
            "sourceColumns": request_payload.get("sourceColumns") or MIJNGELDZAKEN_IMPORT_COLUMNS,
            "targetColumns": request_payload.get("targetColumns") or MIJNGELDZAKEN_IMPORT_COLUMNS,
        }
    return {}


def _credential_status(config: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "usernameConfigured": _has_config(config, "mijngeldzaken_username", "mijngeldzaken.username"),
        "passwordConfigured": _has_config(config, "mijngeldzaken_password", "mijngeldzaken.password"),
        "autonomousMode": str(config.get("mijngeldzaken_autonomous_mode") or "prepare"),
        "confirmedActionsEnabled": bool(config.get("mijngeldzaken_allow_confirmed_actions", False)),
        "credentialActionsEnabled": bool(config.get("mijngeldzaken_allow_credential_actions", False)),
        "valuesRedacted": True,
    }


def _has_config(config: Dict[str, Any], *keys: str) -> bool:
    for key in keys:
        if "." in key:
            section, option = key.split(".", 1)
            section_values = config.get(section)
            if isinstance(section_values, dict) and section_values.get(option) not in (None, ""):
                return True
        if config.get(key) not in (None, ""):
            return True
    return False


def _coalesce(values: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = values.get(key)
        if value not in (None, ""):
            return value
    return None


def _gate(gate_id: str, label: str, status: str, count: int, description: str) -> Dict[str, Any]:
    return {
        "id": gate_id,
        "label": label,
        "status": status,
        "count": count,
        "description": description,
    }


def _next_actions(
    status: str,
    ready_for_draft: int,
    ready_for_approval: int,
    ready_for_execution: int,
    blocked_rows: int,
) -> List[str]:
    if status == "no_mijngeldzaken_rows":
        return ["Route reviewed Category A or household records to MijnGeldzaken first."]
    actions: List[str] = []
    if blocked_rows:
        actions.append("Resolve the row-level exception queue before preparing or executing MGZ drafts.")
    if ready_for_draft:
        actions.append(f"Prepare MGZ export drafts for {ready_for_draft} ready master-ledger row(s).")
    if ready_for_approval:
        actions.append(f"Review and approve {ready_for_approval} prepared MGZ draft(s) in FAB.")
    if ready_for_execution:
        actions.append(f"Execute {ready_for_execution} approved MGZ draft(s) through an approved browser/API executor.")
    if not actions:
        actions.append("MGZ master-ledger controls are clear.")
    return actions


def _today() -> str:
    return date.today().isoformat()
