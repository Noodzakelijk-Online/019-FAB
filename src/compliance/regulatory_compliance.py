from typing import Dict, Any, List
import datetime
import json
import os

class RegulatoryCompliance:
    """Manages regulatory compliance features like tax classification and document retention."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.btw_rates = self.config.get("btw_rates", {
            "high": 0.21, # 21% BTW
            "low": 0.09,  # 9% BTW
            "zero": 0.00  # 0% BTW
        })
        self.document_retention_years = self.config.get("document_retention_years", 7) # Dutch legal requirement
        self.compliance_rules = self._load_compliance_rules()

    def _load_compliance_rules(self) -> List[Dict[str, Any]]:
        rules = self.config.get("compliance_rules", [])
        rules_file = self.config.get("compliance_rules_file")
        if rules or not rules_file or not os.path.exists(rules_file):
            return rules

        try:
            with open(rules_file, "r") as f:
                data = json.load(f)
            return data.get("rules", [])
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Could not load compliance rules from {rules_file}: {exc}")
            return []

    def classify_btw(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Classifies the BTW (VAT) rate based on extracted data."""
        total_amount = extracted_data.get("total_amount")
        vat_amount = extracted_data.get("vat_amount")

        if total_amount and vat_amount is not None:
            if total_amount == 0:
                return {"btw_rate": "zero", "btw_percentage": 0.0}
            
            calculated_percentage = (vat_amount / total_amount)
            
            # Compare with known BTW rates, allowing for small floating point inaccuracies
            for rate_name, percentage in self.btw_rates.items():
                if abs(calculated_percentage - percentage) < 0.005: # 0.5% tolerance
                    return {"btw_rate": rate_name, "btw_percentage": percentage}
        
        # Fallback if VAT amount is not clearly identifiable or doesn't match known rates
        return {"btw_rate": "unknown", "btw_percentage": None}

    def check_document_retention(self, document_date: str) -> bool:
        """Checks if a document should still be retained based on its date."""
        try:
            doc_date = datetime.datetime.strptime(document_date, "%Y-%m-%d").date()
            retention_deadline = doc_date + datetime.timedelta(days=self.document_retention_years * 365.25) # Account for leap years
            return datetime.date.today() < retention_deadline
        except ValueError:
            print(f"Invalid document date format: {document_date}")
            return True # Assume retention if date is unparseable

    def check_compliance(self, document: Dict[str, Any]) -> Dict[str, Any]:
        rules = self.compliance_rules
        compliant_rules = []

        for rule in rules:
            criteria = rule.get("criteria", {})
            if all(document.get(key) == value for key, value in criteria.items()):
                compliant_rules.append(rule.get("id"))

        if not rules and document.get("category"):
            compliant_rules.append("basic_category_present")

        return {
            "is_compliant": bool(compliant_rules),
            "compliant_rules": compliant_rules,
        }

    def generate_tax_export(self, categorized_data_list: List[Dict[str, Any]], export_format: str = "csv") -> str:
        """Generates a tax export file (placeholder)."""
        # This would involve aggregating data and formatting it according to tax authority requirements.
        print(f"Generating tax export in {export_format} format...")
        # For demonstration, just return a dummy path
        export_path = f"/tmp/tax_export_{datetime.date.today().isoformat()}.{export_format}"
        with open(export_path, "w") as f:
            f.write("Dummy tax export content\n")
            for data in categorized_data_list:
                extracted_data = data.get("extracted_data", {})
                f.write(
                    f"{extracted_data.get('transaction_date')},"
                    f"{extracted_data.get('total_amount')},"
                    f"{data.get('category')}\n"
                )
        return export_path


