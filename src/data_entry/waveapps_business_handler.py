import requests
from typing import Dict, Any, List
import csv
import os

from src.data_entry.base import BaseDataEntryHandler

class WaveappsBusinessHandler(BaseDataEntryHandler):
    """Handles data entry into Waveapps Business account via API or CSV fallback."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.access_token = self.config.get("waveapps_business_access_token")
        self.business_id = self.config.get("waveapps_business_id")
        self.api_url = "https://gql.waveapps.com/graphql/v1alpha"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        self.category_mapping = self.config.get("waveapps_business_category_mapping", {})

    def _map_category_to_waveapps(self, category: str) -> str:
        # This mapping should be configurable and potentially learned
        return self.category_mapping.get(category, "Uncategorized Expense") # Default Waveapps category

    def _create_expense_via_api(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # This is a simplified GraphQL mutation. Real implementation needs more fields.
        category_name = self._map_category_to_waveapps(data["category"])
        
        # In a real scenario, you'd need to fetch the actual category ID from Waveapps
        # based on the category name. For simplicity, we'll assume a direct mapping or ID.
        # For now, we'll use a placeholder for category ID.
        # You would typically query Waveapps for categories first: 
        # query = "{ business(id: \"YOUR_BUSINESS_ID\") { expenseCategories { id name } } }"
        # and then map your internal category to Waveapps category ID.
        
        # Placeholder for fetching category ID based on name
        # For this example, we'll hardcode a dummy ID or rely on exact name match if API supports it
        # A more robust solution would involve a lookup or creating categories if they don't exist.
        dummy_category_id = "QnVzaW5lc3M6OTc3NDQyNzYtNjk3Mi00Y2E3LWEwMDYtYjQ1M2Y1N2U1M2Qx"

        mutation = f"""
            mutation {{ 
                expenseCreate(input: {{ 
                    businessId: \"{self.business_id}\",
                    description: \"{data.get("extracted_data", {}).get("description", "Automated Expense")}\",
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
                return {"status": "success", "message": f"Expense created in Waveapps: {expense_id}", "external_id": expense_id}
            else:
                errors = result.get("data", {}).get("expenseCreate", {}).get("errors", [])
                error_messages = ", ".join([e["message"] for e in errors])
                return {"status": "failure", "message": f"Waveapps API error: {error_messages}", "requires_manual_review": True}
        except requests.exceptions.RequestException as e:
            return {"status": "failure", "message": f"Waveapps API request failed: {e}", "requires_manual_review": True}

    def _generate_csv_fallback(self, data: Dict[str, Any], filename: str) -> str:
        csv_path = os.path.join("/tmp", filename)
        with open(csv_path, "w", newline="") as csvfile:
            # Waveapps CSV import format is specific. This is a placeholder.
            fieldnames = ["Date", "Amount", "Description", "Category"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow({
                "Date": data.get("extracted_data", {}).get("transaction_date", ""),
                "Amount": data.get("extracted_data", {}).get("total_amount", 0.0),
                "Description": data.get("extracted_data", {}).get("description", ""),
                "Category": self._map_category_to_waveapps(data["category"])
            })
        return csv_path

    def enter_data(self, categorized_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.access_token or not self.business_id:
            print("Waveapps Business API credentials not configured. Using CSV fallback.")
            csv_filename = f"waveapps_business_import_{categorized_data["document_id"]}.csv"
            csv_file_path = self._generate_csv_fallback(categorized_data, csv_filename)
            return {"status": "csv_generated", "message": f"CSV generated for manual upload: {csv_file_path}", "requires_manual_review": True}

        api_result = self._create_expense_via_api(categorized_data)
        return api_result


