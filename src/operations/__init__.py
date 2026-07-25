"""Lazy public exports for FAB's local operations services."""

from importlib import import_module
from typing import Dict, Tuple


_EXPORTS: Dict[str, Tuple[str, str]] = {
    "LocalAutonomousService": (
        "src.operations.local_autonomy",
        "LocalAutonomousService",
    ),
    "LocalBackupService": (
        "src.operations.local_backup",
        "LocalBackupService",
    ),
    "LocalClosePackService": (
        "src.operations.local_close_pack",
        "LocalClosePackService",
    ),
    "LocalCloseReadinessService": (
        "src.operations.local_close_readiness",
        "LocalCloseReadinessService",
    ),
    "LocalDocumentGroupingService": (
        "src.operations.local_grouping",
        "LocalDocumentGroupingService",
    ),
    "LocalDocumentProcessor": (
        "src.operations.local_processing",
        "LocalDocumentProcessor",
    ),
    "LocalExportAttemptService": (
        "src.operations.local_exports",
        "LocalExportAttemptService",
    ),
    "LocalFolderIntake": (
        "src.operations.local_intake",
        "LocalFolderIntake",
    ),
    "LocalMijngeldzakenControlService": (
        "src.operations.local_mijngeldzaken_control",
        "LocalMijngeldzakenControlService",
    ),
    "LocalOperationsHealth": (
        "src.operations.local_health",
        "LocalOperationsHealth",
    ),
    "LocalOperationsLedger": (
        "src.operations.local_ledger",
        "LocalOperationsLedger",
    ),
    "LocalReadinessService": (
        "src.operations.local_readiness",
        "LocalReadinessService",
    ),
    "LocalReconciliationService": (
        "src.operations.local_reconciliation",
        "LocalReconciliationService",
    ),
    "LocalReviewService": (
        "src.operations.local_review",
        "LocalReviewService",
    ),
    "LocalRoutingService": (
        "src.operations.local_routing",
        "LocalRoutingService",
    ),
    "LocalWaveControlService": (
        "src.operations.local_wave_control",
        "LocalWaveControlService",
    ),
    "LocalWorkflowRecoveryScheduler": (
        "src.operations.local_workflow_recovery",
        "LocalWorkflowRecoveryScheduler",
    ),
    "LocalWorkflowRecoveryService": (
        "src.operations.local_workflow_recovery",
        "LocalWorkflowRecoveryService",
    ),
    "OperationsClient": (
        "src.operations.operations_client",
        "OperationsClient",
    ),
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str):
    target = _EXPORTS.get(name)
    if not target:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = target
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))
