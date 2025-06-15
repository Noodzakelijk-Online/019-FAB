import requests
from typing import Dict, Any, List
import csv
import os

from src.data_entry.base import BaseDataEntryHandler

class WaveappsPersonalHandler(BaseDataEntryHandler):
    """Handles data entry into Waveapps Personal account via API or CSV fallback, specifically for handicap-related expenses."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.access_token = self.config.get("waveapps_personal_access_token")
        self.business_id = self.config.get("waveapps_personal_id") # Personal account might still be a 'business' in Wave API terms
        self.api_url = "https://gql.waveapps.com/graphql/v1alpha"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        self.category_mapping = self.config.get("waveapps_personal_category_mapping", {})
        self.handicap_tag = self.config.get("waveapps_handicap_tag", "#handicap")

    def _map_category_to_waveapps(self, category: str) -> str:
        # This mapping should be configurable and potentially learned
        return self.category_mapping.get(category, "Uncategorized Expense") # Default Waveapps category

    def _create_expense_via_api(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # This is a simplified GraphQL mutation. Real implementation needs more fields.
        category_name = self._map_category_to_waveapps(data["category"])
        
        # Placeholder for fetching category ID based on name
        # Similar to the Business handler, you would need to query Waveapps for categories first.
        dummy_category_id = "QnVzaW5lc3M6OTc3NDQyNzYtNjk3Mi00Y2E3LWEwMDYtYjQ1M2Y1N2U1M2Qx" # Use a different dummy ID or fetch actual ID

        description = data.get("extracted_data", {}).get("description", "Automated Personal Expense")
        if data.get("category") == "Handicaps":
             description = f"{description} {self.handicap_tag}" # Add handicap tag to description

        mutation = f"""
            mutation {{ 
                expenseCreate(input: {{ 
                    businessId: \"{self.business_id}\",
                    description: \"{description}\",
                    amount: {{ value: {data.get("extracted_data", {}).get("total_amount", 0.0)}, currency: {data.get("extracted_data", {}).get("currency", "CAD")} }},
                    incurredAt: \"{data.get("extracted_data", {}).get("transaction_date", "2025-01-01")}\",
                    categoryId: \"{dummy_category_id}\" # This needs to be a real ID
                }}) {{ 
                    didSucceed
                    expense {{ id }}
                    errors {{ message code }}
                }}
            }
        """
        # Note: The above mutation is highly simplified. Waveapps API requires more fields
        # like account ID, vendor ID, etc. You would need to query these first.

        try:
            response = requests.post(self.api_url, headers=self.headers, json={
                "query": mutation
            })
            response.raise_for_status()
            result = response.json()
            
            if result.get("data", {}).get("expenseCreate", {}).get("didSucceed"):
                expense_id = result["data"]["expenseCreate"]["expense"]["id"]
                return {"status": "success", "message": f"Expense created in Waveapps Personal: {expense_id}", "external_id": expense_id}
            else:
                errors = result.get("data", {}).get("expenseCreate", {}).get("errors", [])
                error_messages = ", ".join([e["message"] for e in errors])
                return {"status": "failure", "message": f"Waveapps Personal API error: {error_messages}", "requires_manual_review": True}
        except requests.exceptions.RequestException as e:
            return {"status": "failure", "message": f"Waveapps Personal API request failed: {e}", "requires_manual_review": True}

    def _generate_csv_fallback(self, data: Dict[str, Any], filename: str) -> str:
        csv_path = os.path.join("/tmp", filename)
        with open(csv_path, "w", newline="") as csvfile:
            # Waveapps CSV import format is specific. This is a placeholder.
            fieldnames = ["Date", "Amount", "Description", "Category"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            description = data.get("extracted_data", {}).get("description", "")
            if data.get("category") == "Handicaps":
                 description = f"{description} {self.handicap_tag}"

            writer.writerow({
                "Date": data.get("extracted_data", {}).get("transaction_date", ""),
                "Amount": data.get("extracted_data", {}).get("total_amount", 0.0),
                "Description": description,
                "Category": self._map_category_to_waveapps(data["category"])
            })
        return csv_path

    def enter_data(self, categorized_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.access_token or not self.business_id:
            print("Waveapps Personal API credentials not configured. Using CSV fallback.")
            csv_filename = f"waveapps_personal_import_{categorized_data["document_id"]}.csv"
            csv_file_path = self._generate_csv_fallback(categorized_data, csv_filename)
            return {"status": "csv_generated", "message": f"CSV generated for manual upload: {csv_file_path}", "requires_manual_review": True}

        api_result = self._create_expense_via_api(categorized_data)
        return api_result


