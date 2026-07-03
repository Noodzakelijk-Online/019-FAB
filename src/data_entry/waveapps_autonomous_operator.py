from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from src.data_entry.waveapps_surface import WAVE_SURFACE_CATALOG, plan_wave_action
from src.workflow.autonomous_playbook import AutonomousBookkeeperPlaybook


WaveActionHandler = Callable[[Dict[str, Any]], Dict[str, Any]]


class WaveappsAutonomousOperator:
    """Plans and gates Wave actions for autonomous bookkeeping.

    The operator is intentionally policy-first. It can prepare every known Wave
    action, run read/safe-draft actions through injected handlers, and blocks
    high-impact actions until a caller provides explicit confirmation.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        action_handlers: Optional[Dict[str, WaveActionHandler]] = None,
    ):
        self.config = config
        self.action_handlers = action_handlers or {}
        self.allow_confirmed_actions = bool(config.get("waveapps_allow_confirmed_actions", False))
        self.allow_credential_actions = bool(config.get("waveapps_allow_credential_actions", False))
        self.default_mode = config.get("waveapps_autonomous_mode", "prepare")
        self.playbook = AutonomousBookkeeperPlaybook(config)

    def plan(
        self,
        action_id: str,
        payload: Optional[Dict[str, Any]] = None,
        surface: Optional[str] = None,
        allow_write: bool = False,
    ) -> Dict[str, Any]:
        action = WAVE_SURFACE_CATALOG["actions"].get(action_id)
        resolved_surface = surface or (action or {}).get("surface") or ""
        return plan_wave_action(resolved_surface, action_id, payload or {}, allow_write=allow_write)

    def plan_capability(
        self,
        capability_id: str,
        available_signals: Optional[list[str]] = None,
        confidence: Optional[float] = None,
        approvals: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        return self.playbook.plan(capability_id, available_signals, confidence, approvals)

    def plan_document_capabilities(
        self,
        document: Dict[str, Any],
        available_signals: Optional[list[str]] = None,
        confidence: Optional[float] = None,
    ) -> list[Dict[str, Any]]:
        return self.playbook.plan_document(document, available_signals, confidence)

    def prepare_workflow(
        self,
        workflow_id: str,
        from_date: str,
        to_date: str,
        actor: str = "autonomous_bookkeeper",
        available_signals: Optional[list[str]] = None,
        confidence: Optional[float] = None,
        approvals: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        workflow_plan = self.playbook.plan_workflow(
            workflow_id,
            from_date,
            to_date,
            available_signals=available_signals,
            confidence=confidence,
            approvals=approvals,
            **kwargs,
        )
        operations = [
            self.prepare_operation(
                step["action"],
                step["payload"],
                surface=step["surface"],
                actor=actor,
                capability_id=step["capability_id"],
                available_signals=available_signals,
                confidence=confidence,
            )
            for step in workflow_plan["steps"]
        ]
        return {
            "status": workflow_plan["status"],
            "can_run_autonomously": workflow_plan["can_run_autonomously"],
            "workflow_plan": workflow_plan,
            "operations": operations,
        }

    def prepare_operation(
        self,
        action_id: str,
        payload: Optional[Dict[str, Any]] = None,
        surface: Optional[str] = None,
        actor: str = "autonomous_bookkeeper",
        idempotency_key: Optional[str] = None,
        allow_write: bool = False,
        capability_id: Optional[str] = None,
        available_signals: Optional[list[str]] = None,
        confidence: Optional[float] = None,
    ) -> Dict[str, Any]:
        payload = payload or {}
        plan = self.plan(action_id, payload, surface, allow_write=allow_write)
        capability_plan = (
            self.plan_capability(capability_id, available_signals, confidence)
            if capability_id
            else None
        )
        action = WAVE_SURFACE_CATALOG["actions"].get(action_id, {})
        operation = {
            "operation_id": idempotency_key or self._idempotency_key(action_id, payload),
            "action_id": action_id,
            "surface": plan.get("surface") or action.get("surface"),
            "mode": plan.get("mode") or action.get("mode"),
            "safety": plan.get("safety") or action.get("safety", "unsupported"),
            "payload": payload,
            "plan": plan,
            "capability_plan": capability_plan,
            "actor": actor,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return operation

    def execute(
        self,
        action_id: str,
        payload: Optional[Dict[str, Any]] = None,
        surface: Optional[str] = None,
        actor: str = "autonomous_bookkeeper",
        confirmed: bool = False,
        idempotency_key: Optional[str] = None,
        mode: Optional[str] = None,
        capability_id: Optional[str] = None,
        available_signals: Optional[list[str]] = None,
        confidence: Optional[float] = None,
    ) -> Dict[str, Any]:
        mode = mode or self.default_mode
        operation = self.prepare_operation(
            action_id,
            payload,
            surface,
            actor=actor,
            idempotency_key=idempotency_key,
            allow_write=confirmed,
            capability_id=capability_id,
            available_signals=available_signals,
            confidence=confidence,
        )
        plan = operation["plan"]
        capability_plan = operation.get("capability_plan")

        if plan["status"] != "planned":
            return {
                "status": "needs_review",
                "message": "Wave action cannot run until its plan is complete.",
                "operation": operation,
            }

        if capability_plan and capability_plan["status"] != "ready":
            return {
                "status": "needs_review",
                "message": capability_plan["next_action"],
                "operation": operation,
            }

        safety = operation["safety"]
        if safety == "requires_credentials" and not self.allow_credential_actions:
            return {
                "status": "blocked_requires_credentials",
                "message": "Wave action requires external credentials or provider authorization.",
                "operation": operation,
            }

        if safety == "requires_confirmation" and not (confirmed and self.allow_confirmed_actions):
            return {
                "status": "blocked_requires_confirmation",
                "message": "Wave action changes external state and needs explicit confirmation.",
                "operation": operation,
            }

        if mode == "dry_run":
            return {
                "status": "planned",
                "message": "Wave action passed policy checks in dry-run mode.",
                "operation": operation,
            }

        handler = self.action_handlers.get(action_id)
        if not handler:
            return {
                "status": "queued",
                "message": "Wave action is policy-approved and ready for a Wave API or browser executor.",
                "operation": operation,
            }

        result = handler(operation["payload"])
        return {
            "status": result.get("status", "success"),
            "message": result.get("message", "Wave action executed."),
            "external_id": result.get("external_id"),
            "operation": operation,
            "result": result,
        }

    @staticmethod
    def _idempotency_key(action_id: str, payload: Dict[str, Any]) -> str:
        body = json.dumps(payload, sort_keys=True, default=str)
        digest = hashlib.sha256(f"{action_id}:{body}".encode("utf-8")).hexdigest()
        return f"wave:{digest}"
