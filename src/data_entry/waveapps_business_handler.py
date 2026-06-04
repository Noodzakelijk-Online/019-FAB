import csv
import os
import tempfile
from typing import Dict, Any

import requests

from src.data_entry.base import BaseDataEntryHandler


class WaveappsBusinessHandler(BaseDataEntryHandler):
    """Handles data entry into a Waveapps business account via API or CSV fallback."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.access_token = self.config.get("waveapps_business_access_token")
        self.business_id = self.config.get("waveapps_business_id")
        self.api_url = "https://gql.waveapps.com/graphql/v1alpha"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        self.category_mapping = self.config.get("waveapps_business_category_mapping", {})

    def _map_category_to_waveapps(self, category: str) -> str:
        return self.category_mapping.get(category, "Uncategorized Expense")

    def _create_expense_via_api(self, data: Dict[str, Any]) -> Dict[str, Any]:
        extracted_data = data.get("extracted_data", {})
        description = extracted_data.get("description", "Automated Expense")
        amount = extracted_data.get("total_amount", 0.0)
        currency = extracted_data.get("currency", "EUR")
        transaction_date = extracted_data.get("transaction_date", "2025-01-01")
        dummy_category_id = "QnVzaW5lc3M6OTc3NDQyNzYtNjk3Mi00Y2E3LWEwMDYtYjQ1M2Y1N2U1M2Qx"

        mutation = """
            mutation CreateExpense($input: ExpenseCreateInput!) {
                expenseCreate(input: $input) {
                    didSucceed
                    expense { id }
                    errors { message code }
                }
            }
        """
        variables = {
            "input": {
                "businessId": self.business_id,
                "description": description,
                "amount": {"value": amount, "currency": currency},
                "incurredAt": transaction_date,
                "categoryId": dummy_category_id,
            }
        }

        try:
            response = requests.post(self.api_url, headers=self.headers, json={"query": mutation, "variables": variables})
            response.raise_for_status()
            result = response.json()

            expense_create = result.get("data", {}).get("expenseCreate", {})
            if expense_create.get("didSucceed"):
                expense_id = expense_create["expense"]["id"]
                return {"status": "success", "message": f"Expense created in Waveapps: {expense_id}", "external_id": expense_id}

            errors = expense_create.get("errors", [])
            error_messages = ", ".join([error.get("message", "Unknown error") for error in errors])
            return {"status": "failure", "message": f"Waveapps API error: {error_messages}", "requires_manual_review": True}
        except requests.exceptions.RequestException as exc:
            return {"status": "failure", "message": f"Waveapps API request failed: {exc}", "requires_manual_review": True}

    def _generate_csv_fallback(self, data: Dict[str, Any], filename: str) -> str:
        csv_path = os.path.join(tempfile.gettempdir(), filename)
        with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["Date", "Amount", "Description", "Category"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(
                {
                    "Date": data.get("extracted_data", {}).get("transaction_date", ""),
                    "Amount": data.get("extracted_data", {}).get("total_amount", 0.0),
                    "Description": data.get("extracted_data", {}).get("description", ""),
                    "Category": self._map_category_to_waveapps(data.get("category")),
                }
            )
        return csv_path

    def enter_data(self, categorized_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.access_token or not self.business_id:
            print("Waveapps Business API credentials not configured. Using CSV fallback.")
            document_id = categorized_data.get("document_id", "unknown")
            csv_filename = f"waveapps_business_import_{document_id}.csv"
            csv_file_path = self._generate_csv_fallback(categorized_data, csv_filename)
            return {
                "status": "csv_generated",
                "message": f"CSV generated for manual upload: {csv_file_path}",
                "requires_manual_review": True,
            }

        return self._create_expense_via_api(categorized_data)
