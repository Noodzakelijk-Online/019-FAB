import re
from datetime import datetime
from typing import Any, Dict, List


class ReceiptValidator:
    """Validates receipts for completeness, confidence, and basic consistency."""

    DEFAULT_REQUIRED_FIELDS = ["vendor_name", "transaction_date", "total_amount", "currency"]

    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.required_fields = self.config.get("receipt_validation_required_fields", self.DEFAULT_REQUIRED_FIELDS)
        self.minimum_field_confidence = float(self.config.get("minimum_field_confidence", 0.70))
        self.minimum_required_field_confidence = float(self.config.get("minimum_required_field_confidence", 0.75))
        self.btw_number_pattern = self.config.get("btw_number_pattern", r"NL\d{9}B\d{2}")
        self.require_btw_number_when_vat_present = bool(self.config.get("require_btw_number_when_vat_present", False))

    def validate_receipt(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        extracted_data = processed_data.get("extracted_data", {}) or {}
        field_confidences = processed_data.get("field_confidences", {}) or {}
        ocr_text = processed_data.get("ocr_text", "") or ""
        is_valid = True
        reasons: List[str] = []
        warnings: List[str] = []

        for field in self.required_fields:
            value = extracted_data.get(field)
            confidence = float(field_confidences.get(field, 1.0 if value else 0.0) or 0.0)
            if self._is_empty(value):
                is_valid = False
                reasons.append(f"Missing required field: {field}")
            elif confidence < self.minimum_required_field_confidence:
                is_valid = False
                reasons.append(f"Low confidence for required field {field}: {confidence:.2f}")

        total_amount = self._to_float(extracted_data.get("total_amount"))
        vat_amount = self._to_float(extracted_data.get("vat_amount"))

        if total_amount is not None and total_amount <= 0:
            is_valid = False
            reasons.append("Total amount is zero or negative.")

        if total_amount is not None and vat_amount is not None:
            if vat_amount < 0:
                is_valid = False
                reasons.append("VAT amount is negative.")
            if abs(vat_amount) > abs(total_amount):
                is_valid = False
                reasons.append("VAT amount is larger than the total amount.")

        btw_number = extracted_data.get("btw_number")
        if btw_number and not re.match(self.btw_number_pattern, str(btw_number)):
            is_valid = False
            reasons.append(f"Invalid BTW number format: {btw_number}")
        elif self.require_btw_number_when_vat_present and vat_amount and vat_amount > 0:
            if not re.search(self.btw_number_pattern, ocr_text, re.IGNORECASE):
                warnings.append("VAT amount is present but no valid Dutch BTW number was found in the OCR text.")

        transaction_date = extracted_data.get("transaction_date")
        if transaction_date and not self._is_valid_iso_date(str(transaction_date)):
            is_valid = False
            reasons.append(f"Invalid transaction date format: {transaction_date}")

        for field, confidence in field_confidences.items():
            try:
                confidence_value = float(confidence)
            except (TypeError, ValueError):
                continue
            if confidence_value < self.minimum_field_confidence:
                warnings.append(f"Low confidence field: {field}={confidence_value:.2f}")

        return {
            "is_valid": is_valid,
            "reason": "; ".join(reasons) if reasons else "",
            "warnings": warnings,
            "confidence_summary": self._confidence_summary(field_confidences),
        }

    @staticmethod
    def _is_empty(value: Any) -> bool:
        return value is None or value == "" or value == [] or value == {}

    @staticmethod
    def _to_float(value: Any):
        if value is None or value == "":
            return None
        try:
            return float(str(value).replace(",", "."))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _is_valid_iso_date(value: str) -> bool:
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    @staticmethod
    def _confidence_summary(field_confidences: Dict[str, Any]) -> Dict[str, float]:
        values = []
        for confidence in field_confidences.values():
            try:
                values.append(float(confidence))
            except (TypeError, ValueError):
                continue
        if not values:
            return {"min": 0.0, "average": 0.0, "max": 0.0}
        return {
            "min": round(min(values), 4),
            "average": round(sum(values) / len(values), 4),
            "max": round(max(values), 4),
        }
