from typing import Any, Dict, List

from src.validation.receipt_validator import ReceiptValidator
from src.compliance.regulatory_compliance import RegulatoryCompliance


class ValidationManager:
    """Coordinates receipt, confidence, and compliance validation."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.receipt_validator = ReceiptValidator(config)
        self.regulatory_compliance = RegulatoryCompliance(config)

    def validate_receipt(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        overall_valid = True
        all_reasons: List[str] = []
        all_warnings: List[str] = []
        confidence_summary: Dict[str, float] = {}

        receipt_validation_result = self.receipt_validator.validate_receipt(processed_data)
        if not receipt_validation_result.get("is_valid"):
            overall_valid = False
            reason = receipt_validation_result.get("reason") or "Receipt validation failed."
            all_reasons.append(f"Receipt Validation: {reason}")

        all_warnings.extend(receipt_validation_result.get("warnings", []))
        confidence_summary = receipt_validation_result.get("confidence_summary", {})

        extracted_data = processed_data.get("extracted_data", {}) or {}
        category = processed_data.get("category")
        if category in {"Business", "B", "category_b"}:
            try:
                btw_classification = self.regulatory_compliance.classify_btw(extracted_data)
                processed_data["btw_classification"] = btw_classification
                if btw_classification.get("btw_rate") == "unknown" and extracted_data.get("vat_amount"):
                    all_warnings.append("Business/category B document has VAT amount but unknown VAT classification.")
            except Exception as exc:
                all_warnings.append(f"Regulatory compliance check could not be completed: {exc}")

        document_date = extracted_data.get("transaction_date")
        if document_date:
            try:
                if not self.regulatory_compliance.check_document_retention(document_date):
                    all_warnings.append("Document may be outside the configured retention period.")
            except Exception as exc:
                all_warnings.append(f"Document retention check could not be completed: {exc}")

        return {
            "is_valid": overall_valid,
            "reason": "; ".join(all_reasons) if all_reasons else "",
            "warnings": all_warnings,
            "confidence_summary": confidence_summary,
        }
