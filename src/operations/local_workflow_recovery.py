from typing import Any, Callable, Dict, Iterable, Optional
from uuid import uuid4

from src.operations.local_autonomy import AUTONOMY_EXECUTION_ORDER, LocalAutonomousService
from src.operations.local_connector_intake import CONNECTOR_SOURCES, LocalConnectorIntakeService
from src.operations.local_ledger import LocalOperationsLedger


AUTONOMY_RECOVERY_TRIGGER = "local_autonomous_recovery"
CONNECTOR_RECOVERY_TRIGGER = "connector_intake_recovery"
AUTONOMY_TRIGGERS = {"local_autonomous_cycle", AUTONOMY_RECOVERY_TRIGGER}
CONNECTOR_TRIGGERS = {"connector_intake", CONNECTOR_RECOVERY_TRIGGER}
RECOVERABLE_RUN_STATUSES = {"failed", "completed_with_errors", "attention_required"}
RECOVERABLE_STEP_STATUSES = {"failed", "blocked", "skipped", "not_run"}
SAFE_AUTONOMY_MODES = {"safe_auto", "safe_draft", "read_only"}


class LocalWorkflowRecoveryService:
    """Plan and execute linked retries without replaying high-risk actions."""

    def __init__(
        self,
        ledger: LocalOperationsLedger,
        config: Optional[Dict[str, Any]] = None,
        readiness: Optional[Any] = None,
        intake_paths: Optional[Iterable[str]] = None,
        intake_extensions: Optional[Iterable[str]] = None,
        connector_fetcher_factories: Optional[Dict[str, Callable[[Dict[str, Any]], Any]]] = None,
    ):
        self.ledger = ledger
        self.config = dict(config or {})
        self.readiness = readiness
        self.intake_paths = list(intake_paths or [])
        self.intake_extensions = list(intake_extensions or [])
        self.connector_fetcher_factories = connector_fetcher_factories

    def plan(self, workflow_run_id: int) -> Dict[str, Any]:
        workflow_run = self.ledger.get_workflow_run_with_steps(int(workflow_run_id))
        if workflow_run is None:
            return self._unavailable_plan(workflow_run_id, "not_found", "Workflow run not found.")

        child = self._recovery_child(int(workflow_run_id))
        if child:
            return {
                **self._base_plan(workflow_run),
                "status": "superseded",
                "canRetry": False,
                "supersededByWorkflowRunId": child.get("id"),
                "nextAction": f"Inspect recovery workflow #{child.get('id')}.",
            }

        if workflow_run.get("status") not in RECOVERABLE_RUN_STATUSES:
            return {
                **self._base_plan(workflow_run),
                "status": "not_retryable",
                "canRetry": False,
                "nextAction": "Only failed or attention-required workflow runs can be retried.",
            }

        trigger_source = str(workflow_run.get("trigger_source") or "")
        if trigger_source in CONNECTOR_TRIGGERS:
            return self._connector_plan(workflow_run)
        if trigger_source in AUTONOMY_TRIGGERS:
            return self._autonomy_plan(workflow_run)
        return {
            **self._base_plan(workflow_run),
            "status": "unsupported_trigger",
            "canRetry": False,
            "nextAction": f"Workflow trigger {trigger_source or 'unknown'} has no governed retry contract.",
        }

    def retry(
        self,
        workflow_run_id: int,
        actor: str = "local_workflow_recovery",
        limit: int = 25,
    ) -> Dict[str, Any]:
        recovery_plan = self.plan(workflow_run_id)
        if not recovery_plan.get("canRetry"):
            return self._not_started_result(workflow_run_id, recovery_plan)

        lease_name = f"workflow_recovery:{int(workflow_run_id)}"
        owner_token = uuid4().hex
        lease = self.ledger.acquire_runtime_lease(
            lease_name,
            owner_token,
            ttl_seconds=1800,
            metadata={"workflowRunId": int(workflow_run_id), "actor": actor},
        )
        if not lease.get("acquired"):
            return {
                **self._not_started_result(workflow_run_id, recovery_plan),
                "status": "already_running",
                "runtimeLease": lease.get("lease"),
            }

        try:
            recovery_plan = self.plan(workflow_run_id)
            if not recovery_plan.get("canRetry"):
                result = self._not_started_result(workflow_run_id, recovery_plan)
            else:
                self.ledger.record_audit_event({
                    "action": "local_workflow_recovery.started",
                    "entityType": "workflow_run",
                    "entityId": str(workflow_run_id),
                    "details": {
                        "actor": actor,
                        "recoveryType": recovery_plan.get("recoveryType"),
                        "selectedStepKeys": recovery_plan.get("selectedStepKeys") or [],
                        "nextAttempt": recovery_plan.get("nextAttempt"),
                        "externalSubmission": "not_executed",
                    },
                })
                if recovery_plan.get("recoveryType") == "connector_intake":
                    result = self._retry_connector(recovery_plan, actor)
                else:
                    result = self._retry_autonomy(recovery_plan, actor, limit)

                self.ledger.record_audit_event({
                    "action": "local_workflow_recovery.completed",
                    "entityType": "workflow_run",
                    "entityId": str(result.get("workflowRunId") or workflow_run_id),
                    "details": {
                        "actor": actor,
                        "success": result.get("success"),
                        "status": result.get("status"),
                        "sourceWorkflowRunId": int(workflow_run_id),
                        "recoveryType": recovery_plan.get("recoveryType"),
                        "selectedStepKeys": recovery_plan.get("selectedStepKeys") or [],
                        "externalSubmission": "not_executed",
                    },
                })
        finally:
            released = self.ledger.release_runtime_lease(lease_name, owner_token)
        result.setdefault("plan", recovery_plan)
        result["runtimeLease"] = {"name": lease_name, "released": released}
        return result

    def _connector_plan(self, workflow_run: Dict[str, Any]) -> Dict[str, Any]:
        source_steps = []
        for step in workflow_run.get("steps") or []:
            step_key = str(step.get("step_key") or "")
            source = step_key.partition(":")[2] if step_key.startswith("source:") else ""
            if source not in CONNECTOR_SOURCES or step.get("status") not in RECOVERABLE_STEP_STATUSES:
                continue
            source_steps.append((source, step))
        if not source_steps:
            return {
                **self._base_plan(workflow_run),
                "status": "no_failed_sources",
                "canRetry": False,
                "recoveryType": "connector_intake",
                "nextAction": "No failed connector source remains on this workflow run.",
            }

        current_sources = {
            item["source"]: item
            for item in LocalConnectorIntakeService(
                self.ledger,
                self.config,
                fetcher_factories=self.connector_fetcher_factories,
            ).plan()["sources"]
        }
        unresolved_sources = [source for source, _step in source_steps]
        ready_sources = [
            source
            for source in unresolved_sources
            if (current_sources.get(source) or {}).get("canSync")
        ]
        blocked_sources = [
            {
                "source": source,
                "status": (current_sources.get(source) or {}).get("status") or "unknown",
                "nextAction": (current_sources.get(source) or {}).get("nextAction"),
            }
            for source in unresolved_sources
            if source not in ready_sources
        ]
        attempts = {
            source: max(int(step.get("attempt") or 1) + 1, 2)
            for source, step in source_steps
            if source in ready_sources
        }
        can_retry = bool(ready_sources)
        return {
            **self._base_plan(workflow_run),
            "status": "ready" if can_retry else "waiting_for_configuration",
            "canRetry": can_retry,
            "recoveryType": "connector_intake",
            "strategy": "failed_sources_only",
            "unresolvedSources": unresolved_sources,
            "retrySources": ready_sources,
            "readySources": ready_sources,
            "blockedSources": blocked_sources,
            "selectedStepKeys": [f"source:{source}" for source in ready_sources],
            "stepAttempts": attempts,
            "nextAttempt": max(attempts.values()) if attempts else None,
            "nextAction": (
                "Retry the failed read-only connector sources."
                if can_retry
                else "Resolve connector configuration before retrying this run."
            ),
        }

    def _autonomy_plan(self, workflow_run: Dict[str, Any]) -> Dict[str, Any]:
        execution_steps = [
            step
            for step in workflow_run.get("steps") or []
            if step.get("step_key") in AUTONOMY_EXECUTION_ORDER
        ]
        failed_step = next(
            (
                step
                for status in ("failed", "blocked", "skipped")
                for step in execution_steps
                if step.get("status") == status
            ),
            None,
        )
        if failed_step is None:
            return {
                **self._base_plan(workflow_run),
                "status": "no_failed_step",
                "canRetry": False,
                "recoveryType": "local_autonomy",
                "nextAction": "No failed autonomous step remains on this workflow run.",
            }

        action_id = str(failed_step.get("step_key"))
        metadata = failed_step.get("metadata") or {}
        risk = str(metadata.get("risk") or "unknown")
        mode = str(metadata.get("mode") or "unknown")
        safe = risk == "low" and mode in SAFE_AUTONOMY_MODES and action_id != "execute_approved_exports"
        if not safe:
            return {
                **self._base_plan(workflow_run),
                "status": "approval_required",
                "canRetry": False,
                "recoveryType": "local_autonomy",
                "retryActionId": action_id,
                "selectedStepKeys": [action_id],
                "excludedActions": [{"id": action_id, "risk": risk, "mode": mode}],
                "nextAction": "Open the original evidence and use the action-specific approval workflow.",
            }

        autonomy = self._autonomy_service()
        current_plan = autonomy.plan(include_wave_plan=True, include_wave_sync=True)
        current_action = next(
            (action for action in current_plan.get("actions") or [] if action.get("id") == action_id),
            {},
        )
        can_run = bool(current_action.get("canRun"))
        if action_id == "process_imported":
            can_run = can_run or bool(self.ledger.list_documents(status="failed", limit=1))
        attempt = max(int(failed_step.get("attempt") or 1) + 1, 2)
        return {
            **self._base_plan(workflow_run),
            "status": "ready" if can_run else "waiting_for_precondition",
            "canRetry": can_run,
            "recoveryType": "local_autonomy",
            "strategy": "failed_step_only",
            "retryActionId": action_id,
            "selectedStepKeys": [action_id],
            "stepAttempts": {action_id: attempt},
            "nextAttempt": attempt,
            "currentAction": {
                "id": action_id,
                "canRun": can_run,
                "blockedReason": current_action.get("blockedReason"),
                "risk": risk,
                "mode": mode,
            },
            "excludedActions": [
                {
                    "id": "execute_approved_exports",
                    "risk": "high",
                    "reason": "External execution is never replayed by workflow recovery.",
                }
            ],
            "nextAction": (
                f"Retry autonomous step {action_id} without running downstream actions."
                if can_run
                else current_action.get("blockedReason") or "Resolve the failed step precondition before retrying."
            ),
        }

    def _retry_connector(self, recovery_plan: Dict[str, Any], actor: str) -> Dict[str, Any]:
        source_workflow_run_id = int(recovery_plan["workflowRunId"])
        recovery_metadata = self._recovery_metadata(recovery_plan)
        execution = LocalConnectorIntakeService(
            self.ledger,
            self.config,
            fetcher_factories=self.connector_fetcher_factories,
        ).sync(
            sources=recovery_plan["retrySources"],
            actor=actor,
            trigger_source=CONNECTOR_RECOVERY_TRIGGER,
            workflow_metadata={"recovery": recovery_metadata},
            step_attempts=recovery_plan["stepAttempts"],
        )
        new_run_id = execution.get("workflowRunId")
        detail = self.ledger.get_workflow_run_with_steps(int(new_run_id)) if new_run_id else None
        all_completed = bool(detail and detail.get("steps")) and all(
            step.get("status") == "completed"
            for step in detail.get("steps") or []
        )
        return {
            "success": all_completed,
            "status": "completed" if all_completed else execution.get("status"),
            "workflowRunId": new_run_id,
            "sourceWorkflowRunId": source_workflow_run_id,
            "recoveryType": "connector_intake",
            "selectedStepKeys": recovery_plan["selectedStepKeys"],
            "execution": execution,
            "externalSubmission": "not_executed",
        }

    def _retry_autonomy(
        self,
        recovery_plan: Dict[str, Any],
        actor: str,
        limit: int,
    ) -> Dict[str, Any]:
        source_workflow_run_id = int(recovery_plan["workflowRunId"])
        action_id = str(recovery_plan["retryActionId"])
        recovery_metadata = self._recovery_metadata(recovery_plan)
        recovery_metadata["actor"] = actor
        execution = self._autonomy_service().run_cycle(
            limit=limit,
            include_wave_plan=action_id == "plan_wave_daily_reconciliation",
            include_wave_sync=action_id == "refresh_wave_entity_mirror",
            allowed_action_ids=[action_id],
            trigger_source=AUTONOMY_RECOVERY_TRIGGER,
            workflow_metadata={"recovery": recovery_metadata},
            step_attempts=recovery_plan["stepAttempts"],
            recovery_mode=True,
        )
        new_run_id = execution.get("workflowRunId")
        detail = self.ledger.get_workflow_run_with_steps(int(new_run_id)) if new_run_id else None
        retried_step = (detail.get("steps") or [None])[0] if detail else None
        completed = bool(retried_step and retried_step.get("status") == "completed")
        if detail and not completed and detail.get("status") == "completed":
            self.ledger.update_workflow_run(int(new_run_id), {"status": "completed_with_errors"})
        return {
            "success": completed,
            "status": "completed" if completed else execution.get("status"),
            "workflowRunId": new_run_id,
            "sourceWorkflowRunId": source_workflow_run_id,
            "recoveryType": "local_autonomy",
            "selectedStepKeys": recovery_plan["selectedStepKeys"],
            "execution": execution,
            "externalSubmission": "not_executed",
        }

    def _autonomy_service(self) -> LocalAutonomousService:
        recovery_config = dict(self.config)
        recovery_config["fab_autonomy_execute_approved_exports"] = False
        recovery_config["fab_autonomy_ignore_health_blocks"] = True
        return LocalAutonomousService(
            self.ledger,
            recovery_config,
            readiness=self.readiness,
            intake_paths=self.intake_paths,
            intake_extensions=self.intake_extensions,
        )

    def _recovery_child(self, workflow_run_id: int) -> Optional[Dict[str, Any]]:
        return self.ledger.get_workflow_recovery_child(int(workflow_run_id))

    def _recovery_metadata(self, recovery_plan: Dict[str, Any]) -> Dict[str, Any]:
        source_run = self.ledger.get_workflow_run(int(recovery_plan["workflowRunId"])) or {}
        prior_recovery = (source_run.get("metadata") or {}).get("recovery") or {}
        root_workflow_run_id = int(
            prior_recovery.get("rootWorkflowRunId")
            or recovery_plan["workflowRunId"]
        )
        return {
            "sourceWorkflowRunId": int(recovery_plan["workflowRunId"]),
            "rootWorkflowRunId": root_workflow_run_id,
            "retryDepth": int(prior_recovery.get("retryDepth") or 0) + 1,
            "strategy": recovery_plan.get("strategy"),
            "selectedStepKeys": recovery_plan.get("selectedStepKeys") or [],
            "externalSubmission": "not_executed",
        }

    @staticmethod
    def _base_plan(workflow_run: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "workflowRunId": int(workflow_run["id"]),
            "triggerSource": workflow_run.get("trigger_source"),
            "workflowStatus": workflow_run.get("status"),
            "externalSubmission": "not_executed",
        }

    @staticmethod
    def _unavailable_plan(workflow_run_id: int, status: str, next_action: str) -> Dict[str, Any]:
        return {
            "workflowRunId": int(workflow_run_id),
            "status": status,
            "canRetry": False,
            "nextAction": next_action,
            "externalSubmission": "not_executed",
        }

    @staticmethod
    def _not_started_result(workflow_run_id: int, recovery_plan: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "success": False,
            "status": recovery_plan.get("status"),
            "workflowRunId": None,
            "sourceWorkflowRunId": int(workflow_run_id),
            "plan": recovery_plan,
            "externalSubmission": "not_executed",
        }
