from typing import Dict, Any
import csv
import os
import tempfile

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

from src.data_entry.base import BaseDataEntryHandler

class MijngeldzakenHandler(BaseDataEntryHandler):
    """Handles data entry into mijngeldzaken.nl via automated browser upload."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.username = self.config.get("mijngeldzaken_username")
        self.password = self.config.get("mijngeldzaken_password")
        self.login_url = self.config.get("mijngeldzaken_login_url", "https://www.mijngeldzaken.nl/login")
        self.import_url = self.config.get("mijngeldzaken_import_url", "https://www.mijngeldzaken.nl/import")
        self.csv_template = self.config.get("mijngeldzaken_csv_template", {})

    def _generate_csv(self, data: Dict[str, Any], filename: str) -> str:
        csv_dir = self.config.get("temp_dir") or tempfile.gettempdir()
        os.makedirs(csv_dir, exist_ok=True)
        csv_path = os.path.join(csv_dir, filename)
        with open(csv_path, "w", newline="") as csvfile:
            fieldnames = self.csv_template.get("columns", [])
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=self.csv_template.get("delimiter", ";"))
            
            writer.writeheader()
            # Map your processed_data to the CSV template
            row = {}
            for col, source_key in self.csv_template.get("mapping", {}).items():
                # This is a simplified mapping. Real implementation needs robust type conversion and formatting.
                if source_key == "category":
                    row[col] = self._map_category_to_mijngeldzaken(data.get(source_key))
                elif source_key == "transaction_date":
                    # Assuming date is in YYYY-MM-DD, convert to DD-MM-YYYY if needed
                    date_obj = data.get("extracted_data", {}).get(source_key)
                    if date_obj:
                        row[col] = date_obj # Needs proper date formatting
                else:
                    row[col] = data.get("extracted_data", {}).get(source_key)
            writer.writerow(row)
        return csv_path

    def _map_category_to_mijngeldzaken(self, category: str) -> str:
        # This mapping should be configurable
        mapping = self.config.get("mijngeldzaken_category_mapping", {})
        return mapping.get(category, "Overig") # Default to 'Overig' or a manual review category

    def enter_data(self, categorized_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.username or not self.password:
            return {"status": "failure", "message": "Mijngeldzaken credentials not configured.", "requires_manual_review": True}

        if sync_playwright is None:
            return {
                "status": "failure",
                "message": "Playwright is not installed; browser upload is unavailable.",
                "requires_manual_review": True,
            }

        rate_limit_result = self.acquire_outbound_slot("mijngeldzaken")
        if rate_limit_result:
            return rate_limit_result

        csv_filename = f"mijngeldzaken_import_{categorized_data['document_id']}.csv"
        csv_file_path = self._generate_csv(categorized_data, csv_filename)

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True) # Set to False for debugging UI
                page = browser.new_page()

                # Login
                page.goto(self.login_url)
                page.fill("input[name=\"username\"]", self.username)
                page.fill("input[name=\"password\"]", self.password)
                page.click("button[type=\"submit\"]")
                page.wait_for_url(self.import_url) # Wait for successful login redirect

                # Navigate to import page and upload CSV
                page.goto(self.import_url)
                page.set_input_files("input[type=\"file\"]", csv_file_path)
                page.click("button:has-text(\"Upload\")") # Assuming an upload button
                
                # Wait for upload confirmation or success message
                page.wait_for_selector(".success-message", timeout=10000) # Adjust selector as needed
                status_message = page.inner_text(".success-message")

                browser.close()
                return {"status": "success", "message": f"Successfully uploaded to Mijngeldzaken: {status_message}"}

        except Exception as e:
            print(f"Error during Mijngeldzaken automation: {e}")
            return {"status": "failure", "message": f"Mijngeldzaken upload failed: {e}", "requires_manual_review": True}
        finally:
            if os.path.exists(csv_file_path):
                os.remove(csv_file_path) # Clean up generated CSV


