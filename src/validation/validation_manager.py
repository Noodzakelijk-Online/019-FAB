from typing import Dict, Any

from src.validation.receipt_validator import ReceiptValidator
from src.compliance.regulatory_compliance import RegulatoryCompliance

class ValidationManager:
    """Manages various validation processes for documents."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.receipt_validator = ReceiptValidator(config)
        self.regulatory_compliance = RegulatoryCompliance(config)

    def validate_receipt(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Performs a comprehensive validation of a receipt.

        Args:
            processed_data: A dictionary containing extracted data from the document.

        Returns:
            A dictionary with overall validation status and reasons for failure.
        """
        overall_valid = True
        all_reasons = []

        # 1. Basic receipt validation (missing fields, amount consistency)
        receipt_validation_result = self.receipt_validator.validate_receipt(processed_data)
        if not receipt_validation_result["is_valid"]:
            overall_valid = False
            all_reasons.append(f"Receipt Validation: {receipt_validation_result['reason']}")

        # 2. Regulatory compliance checks (e.g., BTW classification, if applicable)
        # This assumes BTW classification is part of regulatory compliance and might flag issues.
        # For simplicity, we are not directly using the BTW classification result for overall validity here,
        # but it could be integrated if a specific BTW classification is mandatory for validity.
        # btw_classification = self.regulatory_compliance.classify_btw(processed_data.get("extracted_data", {}))
        # if btw_classification["btw_rate"] == "unknown" and processed_data.get("category") == "Business":
        #     overall_valid = False
        #     all_reasons.append("Regulatory Compliance: Unknown BTW rate for business expense.")

        # 3. Document retention check (more for info, less for blocking processing)
        # document_date = processed_data.get("extracted_data", {}).get("transaction_date")
        # if document_date and not self.regulatory_compliance.check_document_retention(document_date):
        #     all_reasons.append("Regulatory Compliance: Document is past retention period.")

        return {
            "is_valid": overall_valid,
            "errors": all_reasons,
            "warnings": receipt_validation_result.get("warnings", []),
            "reason": "; ".join(all_reasons) if all_reasons else "",
            "blocking": not overall_valid,
            "fieldControls": receipt_validation_result.get("fieldControls", {}),
        }


