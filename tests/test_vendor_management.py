import unittest

from src.vendor_management.vendor_manager import VendorManager


class TestVendorManagement(unittest.TestCase):
    def setUp(self):
        self.config = {
            "vendor_match_threshold": 0.7,
            "vendors": {
                "Albert Heijn": {
                    "category": "Groceries",
                    "category_path": ["Expenses", "Household", "Groceries"],
                    "aliases": ["AH"],
                },
                "Microsoft": {
                    "category": "Software",
                    "category_path": ["Expenses", "Business", "Software"],
                },
            },
            "category_hierarchy": {
                "Expenses": {
                    "Business": {"Software": {}},
                    "Household": {"Groceries": {}},
                }
            },
            "purchase_pattern_rules": {
                "Software": ["license", "subscription"]
            },
        }

    def test_identifies_existing_vendor(self):
        manager = VendorManager(self.config)
        result = manager.identify_vendor(extracted_vendor="Albert Heijn")
        self.assertEqual(result["vendor_name"], "Albert Heijn")
        self.assertTrue(result["matched_existing"])

    def test_assigns_vendor_default_category(self):
        manager = VendorManager(self.config)
        result = manager.assign_category("Microsoft")
        self.assertEqual(result["category"], "Software")


if __name__ == "__main__":
    unittest.main()
