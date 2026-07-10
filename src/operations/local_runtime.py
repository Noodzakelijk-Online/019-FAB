from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from src.operations.local_ledger import LocalOperationsLedger, default_ledger_path


def build_local_operations_ledger(
    config: Dict[str, Any],
    on_error: Optional[Callable[[str], None]] = None,
) -> Optional[LocalOperationsLedger]:
    """Build the configured authoritative local ledger, or return None."""
    config = config or {}
    configured_enabled = config.get(
        "fab_local_ledger_enabled",
        config.get("operations_local_ledger_enabled"),
    )
    configured_path = (
        config.get("fab_local_ledger_path")
        or config.get("operations_ledger_path")
    )
    enabled = (
        bool(configured_path)
        if configured_enabled is None
        else _as_bool(configured_enabled)
    )
    if not enabled:
        return None
    try:
        return LocalOperationsLedger(str(configured_path or default_ledger_path()))
    except Exception as exc:
        if on_error:
            on_error(f"FAB local operations ledger unavailable: {exc}")
        return None


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in {"", "0", "false", "no", "off"}
    return bool(value)
