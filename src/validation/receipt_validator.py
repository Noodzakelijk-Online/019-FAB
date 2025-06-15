from typing import Dict, Any
import re

class ReceiptValidator:
    """Validates receipts for legal compliance and completeness."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.required_fields = self.config.get("receipt_validation_required_fields", [
            "vendor_name", "transaction_date", "total_amount"
        ])
        self.btw_number_pattern = self.config.get("btw_number_pattern", r"NL\d{9}B\d{2}")

    def validate_receipt(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Performs validation checks on processed receipt data.

        Args:
            processed_data: A dictionary containing extracted data from the document.

        Returns:
            A dictionary with validation status and reasons for failure.
        """
        extracted_data = processed_data.get("extracted_data", {})
        ocr_text = processed_data.get("ocr_text", "")
        is_valid = True
        reasons = []

        # 1. Check for required fields
        for field in self.required_fields:
            if not extracted_data.get(field):
                is_valid = False
                reasons.append(f"Missing required field: {field}")

        # 2. Validate BTW number (if present and relevant)
        if "btw_number" in extracted_data and extracted_data["btw_number"]:
            if not re.match(self.btw_number_pattern, extracted_data["btw_number"]):
                is_valid = False
                reasons.append(f"Invalid BTW number format: {extracted_data["btw_number"]}")
        elif "vat_amount" in extracted_data and extracted_data["vat_amount"] > 0:
            # If VAT is present but no BTW number, it might be an issue for business expenses
            if not re.search(self.btw_number_pattern, ocr_text, re.IGNORECASE):
                is_valid = False
                reasons.append("VAT amount present but no valid BTW number found in document.")

        # 3. Basic amount consistency check (e.g., total > 0)
        if extracted_data.get("total_amount") is not None and extracted_data["total_amount"] <= 0:
            is_valid = False
            reasons.append("Total amount is zero or negative.")

        # 4. Date format validation (assuming YYYY-MM-DD for internal use)
        transaction_date = extracted_data.get("transaction_date")
        if transaction_date:
            try:
                # Attempt to parse date to ensure it's a valid format
                import datetime
                datetime.datetime.strptime(str(transaction_date), "%Y-%m-%d")
            except ValueError:
                is_valid = False
                reasons.append(f"Invalid transaction date format: {transaction_date}")

        return {"is_valid": is_valid, "reason": "; ".join(reasons) if reasons else ""}


