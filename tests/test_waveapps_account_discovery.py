import unittest
from unittest.mock import MagicMock, patch

from src.data_entry.waveapps_account_discovery import WaveappsAccountDiscoveryService
from src.utils.rate_limiter import reset_all_limiters


class TestWaveappsAccountDiscoveryService(unittest.TestCase):
    def setUp(self):
        reset_all_limiters()
        self.config = {
            "waveapps_business_access_token": "business-secret-token",
            "waveapps_business_id": "business-1",
            "waveapps_business_anchor_account_id": "anchor-1",
            "waveapps_business_category_account_ids": {"Office Supplies": "expense-1"},
        }

    def tearDown(self):
        reset_all_limiters()

    @patch("src.data_entry.waveapps_account_discovery.requests.post")
    def test_discovers_and_verifies_configured_accounts_without_exposing_token(self, mock_post):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "data": {
                "business": {
                    "id": "business-1",
                    "name": "FAB Test Business",
                    "accounts": {
                        "edges": [
                            {"node": {"id": "anchor-1", "name": "Checking", "subtype": {"name": "Cash and Bank", "value": "CASH_AND_BANK"}}},
                            {"node": {"id": "expense-1", "name": "Office Supplies", "subtype": {"name": "Expense", "value": "EXPENSE"}}},
                        ],
                    },
                },
            },
        }
        mock_post.return_value = response

        result = WaveappsAccountDiscoveryService(self.config).discover("waveapps_business")

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "read_result_captured")
        self.assertEqual(result["mapping"]["anchorAccount"]["verified"], True)
        self.assertTrue(result["mapping"]["categoryAccounts"][0]["verified"])
        self.assertTrue(result["mapping"]["verified"])
        self.assertEqual(result["operation"]["action_id"], "chart_account_list_read")
        request = mock_post.call_args.kwargs["json"]
        self.assertEqual(request["variables"], {"businessId": "business-1"})
        self.assertIn("accounts", request["query"])
        self.assertNotIn("business-secret-token", str(result))

    def test_missing_credentials_are_reported_without_provider_call(self):
        result = WaveappsAccountDiscoveryService({}).discover("waveapps_business")

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "not_configured")
        self.assertEqual(result["missingFields"], ["accessToken", "businessId"])

    def test_default_category_account_is_not_marked_verified_before_discovery(self):
        config = dict(self.config)
        config["waveapps_business_category_account_ids"] = {}
        config["waveapps_business_default_category_account_id"] = "default-expense"

        mapping = WaveappsAccountDiscoveryService(config).mapping_status("waveapps_business")["targets"][0]

        self.assertTrue(mapping["configured"])
        self.assertIsNone(mapping["defaultCategoryAccount"]["verified"])
        self.assertFalse(mapping["verified"])


if __name__ == "__main__":
    unittest.main()
