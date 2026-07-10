import requests
from typing import Dict, Any
import csv
import os
import tempfile

from src.data_entry.base import BaseDataEntryHandler
from src.data_entry.waveapps_surface import (
    build_wave_expense_import_row,
    build_wave_action_payload,
    classify_wave_destination,
    plan_wave_action,
    resolve_wave_action_for_document,
)

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
        self.default_account = self.config.get("waveapps_personal_default_account", "Uncategorized")

    def _map_category_to_waveapps(self, category: str) -> str:
        # This mapping should be configurable and potentially learned
        return self.category_mapping.get(category, "Uncategorized Expense") # Default Waveapps category

    def _create_expense_via_api(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # This is a simplified GraphQL mutation. Real implementation needs more fields.
        self._map_category_to_waveapps(data["category"])
        destination = classify_wave_destination(data)
        action_id = resolve_wave_action_for_document(data)
        wave_category = self._map_category_to_waveapps(data["category"])
        action_payload = build_wave_action_payload(data, wave_category, self.default_account)
        
        # Placeholder for fetching category ID based on name
        # Similar to the Business handler, you would need to query Waveapps for categories first.
        dummy_category_id = "QnVzaW5lc3M6OTc3NDQyNzYtNjk3Mi00Y2E3LWEwMDYtYjQ1M2Y1N2U1M2Qx" # Use a different dummy ID or fetch actual ID

        description = data.get("extracted_data", {}).get("description", "Automated Personal Expense")
        if data.get("category") == "Handicaps":
             description = f"{description} {self.handicap_tag}" # Add handicap tag to description

        extracted_data = data.get("extracted_data", {})
        total_amount = extracted_data.get("total_amount", 0.0)
        currency = extracted_data.get("currency", "CAD")
        transaction_date = extracted_data.get("transaction_date", "2025-01-01")
        mutation = """
            mutation {
                expenseCreate(input: {
                    businessId: "%s",
                    description: "%s",
                    amount: { value: %s, currency: %s },
                    incurredAt: "%s",
                    categoryId: "%s"
                }) {
                    didSucceed
                    expense { id }
                    errors { message code }
                }
            }
        """ % (self.business_id, description, total_amount, currency, transaction_date, dummy_category_id)
        # Note: The above mutation is highly simplified. Waveapps API requires more fields
        # like account ID, vendor ID, etc. You would need to query these first.

        rate_limit_result = self.acquire_outbound_slot("waveapps")
        if rate_limit_result:
            rate_limit_result.update({
                "target_surface": destination["target_surface"],
                "action_plan": plan_wave_action(destination["target_surface"], action_id, action_payload),
            })
            return rate_limit_result

        try:
            response = requests.post(self.api_url, headers=self.headers, json={
                "query": mutation
            })
            response.raise_for_status()
            result = response.json()
            
            if result.get("data", {}).get("expenseCreate", {}).get("didSucceed"):
                expense_id = result["data"]["expenseCreate"]["expense"]["id"]
                return {
                    "status": "success",
                    "message": f"Expense created in Waveapps Personal: {expense_id}",
                    "external_id": expense_id,
                    "target_surface": destination["target_surface"],
                    "action_plan": plan_wave_action(
                        destination["target_surface"],
                        action_id,
                        action_payload,
                        allow_write=True,
                    ),
                }
            else:
                errors = result.get("data", {}).get("expenseCreate", {}).get("errors", [])
                error_messages = ", ".join([e["message"] for e in errors])
                return {
                    "status": "failure",
                    "message": f"Waveapps Personal API error: {error_messages}",
                    "requires_manual_review": True,
                    "target_surface": destination["fallback_surface"],
                    "action_plan": plan_wave_action(destination["target_surface"], action_id, action_payload),
                }
        except requests.exceptions.RequestException as e:
            return {
                "status": "failure",
                "message": f"Waveapps Personal API request failed: {e}",
                "requires_manual_review": True,
                "target_surface": destination["fallback_surface"],
                "action_plan": plan_wave_action(destination["target_surface"], action_id, action_payload),
            }

    def _generate_csv_fallback(self, data: Dict[str, Any], filename: str) -> str:
        csv_dir = self.config.get("temp_dir") or tempfile.gettempdir()
        os.makedirs(csv_dir, exist_ok=True)
        csv_path = os.path.join(csv_dir, filename)
        with open(csv_path, "w", newline="") as csvfile:
            fieldnames = [
                "Date",
                "Amount",
                "Description",
                "Category",
                "Vendor",
                "Wave Surface",
                "Wave Action",
                "Wave Fallback",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            suffix = self.handicap_tag if data.get("category") == "Handicaps" else ""
            writer.writerow(build_wave_expense_import_row(data, self._map_category_to_waveapps(data["category"]), suffix))
        return csv_path

    def enter_data(self, categorized_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.access_token or not self.business_id:
            print("Waveapps Personal API credentials not configured. Using CSV fallback.")
            csv_filename = f"waveapps_personal_import_{categorized_data['document_id']}.csv"
            csv_file_path = self._generate_csv_fallback(categorized_data, csv_filename)
            destination = classify_wave_destination(categorized_data)
            action_id = resolve_wave_action_for_document(categorized_data)
            wave_category = self._map_category_to_waveapps(categorized_data["category"])
            action_payload = build_wave_action_payload(categorized_data, wave_category, self.default_account)
            return {
                "status": "csv_generated",
                "message": f"CSV generated for manual upload: {csv_file_path}",
                "requires_manual_review": True,
                "target_surface": destination["target_surface"],
                "action_plan": plan_wave_action(destination["target_surface"], action_id, action_payload),
            }

        api_result = self._create_expense_via_api(categorized_data)
        return api_result


