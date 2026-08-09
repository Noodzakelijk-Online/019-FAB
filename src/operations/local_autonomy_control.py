from typing import Any, Dict, Optional

from src.operations.local_ledger import LocalOperationsLedger


AUTONOMY_EMERGENCY_STOP = "autonomy_emergency_stop"
AUTONOMY_RESUME_CONFIRMATION = "RESUME FAB AUTONOMY"
AUTONOMY_LEASE_NAME = "local_autonomous_cycle"


class LocalAutonomyControlService:
    """Persist and audit the operator's fail-closed autonomy stop."""

    def __init__(self, ledger: LocalOperationsLedger):
        self.ledger = ledger

    def status(self) -> Dict[str, Any]:
        control = self.ledger.get_runtime_control(AUTONOMY_EMERGENCY_STOP)
        lease = self.ledger.get_runtime_lease(AUTONOMY_LEASE_NAME)
        return {
            **control,
            "status": "stopped" if control["active"] else "ready",
            "resumeConfirmationPhrase": AUTONOMY_RESUME_CONFIRMATION,
            "cycleActive": bool(lease and lease.get("active")),
            "runtimeLease": lease,
            "externalSubmission": "not_executed",
        }

    def engage(
        self,
        *,
        actor: str,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        control = self.ledger.set_runtime_control(
            AUTONOMY_EMERGENCY_STOP,
            True,
            actor=actor,
            reason=reason,
            metadata=metadata,
        )
        return {
            "success": True,
            "status": "stopped",
            "control": control,
            "nextAction": (
                "Wait for any active step to finish, inspect the audit trail, then clear the stop "
                f"with the exact phrase {AUTONOMY_RESUME_CONFIRMATION}."
            ),
            "externalSubmission": "not_executed",
        }

    def clear(
        self,
        *,
        actor: str,
        reason: str,
        confirmation: str,
    ) -> Dict[str, Any]:
        if str(confirmation or "").strip() != AUTONOMY_RESUME_CONFIRMATION:
            return {
                "success": False,
                "status": "confirmation_required",
                "error": f"Enter the exact confirmation phrase: {AUTONOMY_RESUME_CONFIRMATION}",
                "externalSubmission": "not_executed",
            }
        lease = self.ledger.get_runtime_lease(AUTONOMY_LEASE_NAME)
        if lease and lease.get("active"):
            return {
                "success": False,
                "status": "cycle_still_active",
                "error": "The active cycle has not released its runtime lease; keep the stop engaged and retry after the current step finishes.",
                "runtimeLease": lease,
                "externalSubmission": "not_executed",
            }
        control = self.ledger.set_runtime_control(
            AUTONOMY_EMERGENCY_STOP,
            False,
            actor=actor,
            reason=reason,
        )
        return {
            "success": True,
            "status": "ready",
            "control": control,
            "nextAction": "Review the autonomy plan before starting another cycle.",
            "externalSubmission": "not_executed",
        }
