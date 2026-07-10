from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from src.data_entry.mijngeldzaken_surface import MIJNGELDZAKEN_SURFACE_CATALOG, plan_mijngeldzaken_action


MijngeldzakenActionHandler = Callable[[Dict[str, Any]], Dict[str, Any]]


class MijngeldzakenAutonomousOperator:
    """Plans and gates MijnGeldzaken actions for FAB master-ledger sync."""

    def __init__(
        self,
        config: Dict[str, Any],
        action_handlers: Optional[Dict[str, MijngeldzakenActionHandler]] = None,
    ):
        self.config = config
        self.action_handlers = action_handlers or {}
        self.allow_confirmed_actions = bool(config.get("mijngeldzaken_allow_confirmed_actions", False))
        self.allow_credential_actions = bool(config.get("mijngeldzaken_allow_credential_actions", False))
        self.default_mode = config.get("mijngeldzaken_autonomous_mode", "prepare")

    def plan(
        self,
        action_id: str,
        payload: Optional[Dict[str, Any]] = None,
        surface: Optional[str] = None,
        allow_write: bool = False,
    ) -> Dict[str, Any]:
        action = MIJNGELDZAKEN_SURFACE_CATALOG["actions"].get(action_id)
        resolved_surface = surface or (action or {}).get("surface") or ""
        return plan_mijngeldzaken_action(resolved_surface, action_id, payload or {}, allow_write=allow_write)

    def prepare_operation(
        self,
        action_id: str,
        payload: Optional[Dict[str, Any]] = None,
        surface: Optional[str] = None,
        actor: str = "autonomous_bookkeeper",
        idempotency_key: Optional[str] = None,
        allow_write: bool = False,
    ) -> Dict[str, Any]:
        payload = payload or {}
        plan = self.plan(action_id, payload, surface, allow_write=allow_write)
        action = MIJNGELDZAKEN_SURFACE_CATALOG["actions"].get(action_id, {})
        return {
            "operation_id": idempotency_key or self._idempotency_key(action_id, payload),
            "action_id": action_id,
            "surface": plan.get("surface") or action.get("surface"),
            "mode": plan.get("mode") or action.get("mode"),
            "safety": plan.get("safety") or action.get("safety", "unsupported"),
            "payload": payload,
            "plan": plan,
            "actor": actor,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def execute(
        self,
        action_id: str,
        payload: Optional[Dict[str, Any]] = None,
        surface: Optional[str] = None,
        actor: str = "autonomous_bookkeeper",
        confirmed: bool = False,
        idempotency_key: Optional[str] = None,
        mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        mode = mode or self.default_mode
        operation = self.prepare_operation(
            action_id,
            payload,
            surface=surface,
            actor=actor,
            idempotency_key=idempotency_key,
            allow_write=confirmed,
        )
        plan = operation["plan"]
        if plan["status"] != "planned":
            return {
                "status": "needs_review",
                "message": "MijnGeldzaken action cannot run until its plan is complete.",
                "operation": operation,
            }
        safety = operation["safety"]
        if safety == "requires_credentials" and not self.allow_credential_actions:
            return {
                "status": "blocked_requires_credentials",
                "message": (
                    "MijnGeldzaken action requires a supervised user-owned sign-in. "
                    "FAB does not use stored MijnGeldzaken passwords."
                ),
                "operation": operation,
            }
        if safety == "requires_confirmation" and not (confirmed and self.allow_confirmed_actions):
            return {
                "status": "blocked_requires_confirmation",
                "message": "MijnGeldzaken action changes external state and needs explicit confirmation.",
                "operation": operation,
            }
        if mode == "dry_run":
            return {
                "status": "planned",
                "message": "MijnGeldzaken action passed policy checks in dry-run mode.",
                "operation": operation,
            }
        handler = self.action_handlers.get(action_id)
        if not handler:
            return {
                "status": "queued",
                "message": "MijnGeldzaken action is policy-approved and ready for an API or browser executor.",
                "operation": operation,
            }
        result = handler(operation["payload"])
        return {
            "status": result.get("status", "success"),
            "message": result.get("message", "MijnGeldzaken action executed."),
            "external_id": result.get("external_id"),
            "operation": operation,
            "result": result,
        }

    @staticmethod
    def _idempotency_key(action_id: str, payload: Dict[str, Any]) -> str:
        body = json.dumps(payload, sort_keys=True, default=str)
        digest = hashlib.sha256(f"{action_id}:{body}".encode("utf-8")).hexdigest()
        return f"mijngeldzaken:{digest}"
