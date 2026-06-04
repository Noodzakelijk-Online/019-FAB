from typing import Dict, Any
import csv
import os
import tempfile
from playwright.sync_api import sync_playwright

from src.data_entry.base import BaseDataEntryHandler


class MijngeldzakenHandler(BaseDataEntryHandler):
    """Handles data entry into Mijngeldzaken via automated browser upload."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.username = self.config.get("mijngeldzaken_username")
        self.password = self.config.get("mijngeldzaken_password")
        self.login_url = self.config.get("mijngeldzaken_login_url", "https://www.mijngeldzaken.nl/login")
        self.import_url = self.config.get("mijngeldzaken_import_url", "https://www.mijngeldzaken.nl/import")
        self.csv_template = self.config.get("mijngeldzaken_csv_template", {})

    def _generate_csv(self, data: Dict[str, Any], filename: str) -> str:
        csv_path = os.path.join(tempfile.gettempdir(), filename)
        with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = self.csv_template.get("columns", [])
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=self.csv_template.get("delimiter", ";"))

            writer.writeheader()
            row = {}
            for col, source_key in self.csv_template.get("mapping", {}).items():
                if source_key == "category":
                    row[col] = self._map_category_to_mijngeldzaken(data.get(source_key))
                elif source_key == "transaction_date":
                    row[col] = data.get("extracted_data", {}).get(source_key)
                else:
                    row[col] = data.get("extracted_data", {}).get(source_key)
            writer.writerow(row)
        return csv_path

    def _map_category_to_mijngeldzaken(self, category: str) -> str:
        mapping = self.config.get("mijngeldzaken_category_mapping", {})
        return mapping.get(category, "Overig")

    def enter_data(self, categorized_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.username or not self.password:
            return {
                "status": "failure",
                "message": "Mijngeldzaken credentials not configured.",
                "requires_manual_review": True,
            }

        document_id = categorized_data.get("document_id", "unknown")
        csv_filename = f"mijngeldzaken_import_{document_id}.csv"
        csv_file_path = self._generate_csv(categorized_data, csv_filename)

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                page.goto(self.login_url)
                page.fill('input[name="username"]', self.username)
                page.fill('input[name="password"]', self.password)
                page.click('button[type="submit"]')
                page.wait_for_url(self.import_url)

                page.goto(self.import_url)
                page.set_input_files('input[type="file"]', csv_file_path)
                page.click('button:has-text("Upload")')
                page.wait_for_selector(".success-message", timeout=10000)
                status_message = page.inner_text(".success-message")

                browser.close()
                return {"status": "success", "message": f"Successfully uploaded to Mijngeldzaken: {status_message}"}

        except Exception as exc:
            print(f"Error during Mijngeldzaken automation: {exc}")
            return {
                "status": "failure",
                "message": f"Mijngeldzaken upload failed: {exc}",
                "requires_manual_review": True,
            }
        finally:
            if os.path.exists(csv_file_path):
                os.remove(csv_file_path)
