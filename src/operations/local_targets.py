from typing import Any, Dict, Optional


MISSING_TARGET_SYSTEMS = {"", "none", "unknown"}


def resolve_document_target_system(
    document: Dict[str, Any],
    extracted_data: Optional[Dict[str, Any]] = None,
    *,
    default: str = "",
) -> str:
    """Resolve a document ledger target without replacing an explicit decision."""
    metadata = document.get("metadata") if isinstance(document.get("metadata"), dict) else {}
    routing = metadata.get("routing") if isinstance(metadata.get("routing"), dict) else {}
    extracted = (
        extracted_data
        if isinstance(extracted_data, dict)
        else document.get("extracted_data")
        if isinstance(document.get("extracted_data"), dict)
        else {}
    )
    candidates = (
        document.get("targetSystem"),
        document.get("target_system"),
        metadata.get("targetSystem"),
        metadata.get("target_system"),
        routing.get("targetSystem"),
        routing.get("target_system"),
        extracted.get("targetSystem"),
        extracted.get("target_system"),
    )
    for candidate in candidates:
        value = str(candidate or "").strip()
        if value.lower() not in MISSING_TARGET_SYSTEMS:
            return value
    return str(default or "").strip()
