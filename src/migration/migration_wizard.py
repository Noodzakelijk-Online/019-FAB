from typing import Dict, Any, List
from src.migration.data_migration import DataMigration

class MigrationWizard:
    """Guides the user through the data migration process."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.data_migration = DataMigration(config)

    def start_migration_wizard(self):
        """Starts an interactive wizard for data migration."""
        print("\n--- Data Migration Wizard ---")
        print("This wizard will help you import historical financial data.")

        file_path = input("Enter the full path to your historical data file (CSV or XLSX): ")
        if not file_path:
            print("File path cannot be empty. Exiting migration wizard.")
            return

        # In a real wizard, you'd parse the file headers and ask the user to map them
        # For simplicity, we'll ask for a predefined mapping or assume a standard one.
        print("\nNow, let's define the column mapping. Enter the source column name for each target field.")
        print("Leave blank if a field does not exist in your file.")

        mapping = {}
        mapping["transaction_date"] = input("Source column for Transaction Date (e.g., 'Date', 'Datum'): ") or "Date"
        mapping["total_amount"] = input("Source column for Total Amount (e.g., 'Amount', 'Bedrag'): ") or "Amount"
        mapping["description"] = input("Source column for Description (e.g., 'Description', 'Omschrijving'): ") or "Description"
        mapping["category"] = input("Source column for Category (e.g., 'Category', 'Categorie'): ") or "Category"
        mapping["vendor_name"] = input("Source column for Vendor Name (e.g., 'Vendor', 'Leverancier'): ") or "Vendor"

        # Filter out empty mappings
        mapping = {k: v for k, v in mapping.items() if v}

        print(f"\nAttempting to import data from {file_path} with mapping: {mapping}")
        imported_data = self.data_migration.import_data(file_path, mapping)

        if imported_data:
            print(f"Successfully imported {len(imported_data)} records.")
            print("You can now use this data to train your learning models or for analysis.")
            # Further steps: offer to train ML model, reconcile with existing data, etc.
            # self.data_migration.reconcile_imported_data(imported_data, existing_system_data)
        else:
            print("Data migration failed or no data imported.")

        print("--- Data Migration Wizard Finished ---")

    def get_standard_mapping(self) -> Dict[str, str]:
        """Returns a predefined standard mapping for common export formats."""
        return {
            "transaction_date": "Date",
            "total_amount": "Amount",
            "description": "Description",
            "category": "Category",
            "vendor_name": "Vendor"
        }


