from typing import Any, Dict, List


class SafetyEngine:
    """Decides whether FAB may proceed automatically or must ask for review."""

    DEFAULT_THRESHOLDS = {
        "auto_process": 0.95,
        "approval_required": 0.85,
        "manual_review": 0.70,
        "posting": 0.95,
    }

    REQUIRED_POSTING_FIELDS = [
        "vendor_name",
        "transaction_date",
        "total_amount",
        "currency",
    ]

    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.thresholds = dict(self.DEFAULT_THRESHOLDS)
        self.thresholds.update(self.config.get("confidence_thresholds", {}))
        self.required_posting_fields = self.config.get("required_posting_fields", self.REQUIRED_POSTING_FIELDS)

    def evaluate_extraction(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        extracted = processed_data.get("extracted_data", {})
        warnings: List[str] = []
        field_confidences = processed_data.get("field_confidences", {})

        for field_name in self.required_posting_fields:
            if not extracted.get(field_name):
                warnings.append(f"Missing required field: {field_name}")

        confidence_values = [float(value) for value in field_confidences.values()] if field_confidences else []
        confidence_score = min(confidence_values) if confidence_values else (0.95 if not warnings else 0.4)

        return self._decision(confidence_score, warnings, "extraction")

    def evaluate_posting_readiness(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        warnings: List[str] = []
        extracted = document_data.get("extracted_data", {})

        for field_name in self.required_posting_fields:
            if not extracted.get(field_name):
                warnings.append(f"Missing required posting field: {field_name}")

        if document_data.get("is_duplicate") or document_data.get("duplicate_result", {}).get("is_duplicate"):
            warnings.append("Duplicate or suspected duplicate document")

        if document_data.get("requires_manual_review"):
            warnings.append("Document is already marked for manual review")

        if document_data.get("target_system") is None:
            warnings.append("No target bookkeeping system resolved")

        confidence_score = min(
            float(document_data.get("confidence_score", 0.0) or 0.0),
            float(document_data.get("routing_confidence", 1.0) or 1.0),
        )
        if not warnings and confidence_score == 0.0:
            confidence_score = 0.85

        decision = self._decision(confidence_score, warnings, "posting")
        decision["may_post"] = decision["decision"] == "auto_process" and not warnings
        return decision

    def _decision(self, confidence_score: float, warnings: List[str], context: str) -> Dict[str, Any]:
        if warnings:
            return {
                "context": context,
                "decision": "manual_review",
                "confidence_score": round(confidence_score, 4),
                "warnings": warnings,
                "reason": "warnings_present",
            }

        if confidence_score >= self.thresholds["auto_process"]:
            decision = "auto_process"
        elif confidence_score >= self.thresholds["approval_required"]:
            decision = "approval_required"
        else:
            decision = "manual_review"

        return {
            "context": context,
            "decision": decision,
            "confidence_score": round(confidence_score, 4),
            "warnings": warnings,
            "reason": "confidence_threshold",
        }
