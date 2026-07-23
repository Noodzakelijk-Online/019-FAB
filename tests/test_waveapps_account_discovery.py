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

    @patch("src.data_entry.waveapps_account_discovery.requests.post")
    def test_provider_authentication_and_rate_limit_failures_are_actionable(self, mock_post):
        cases = (
            (401, "authentication_failed", "Replace"),
            (403, "authorization_failed", "Confirm"),
            (429, "rate_limited", "Wait"),
        )
        for status_code, expected_status, next_action in cases:
            with self.subTest(status_code=status_code):
                reset_all_limiters()
                response = MagicMock()
                response.status_code = status_code
                mock_post.return_value = response

                result = WaveappsAccountDiscoveryService(self.config).discover("waveapps_business")

                self.assertFalse(result["success"])
                self.assertEqual(result["status"], expected_status)
                self.assertIn(next_action, result["nextAction"])
                self.assertEqual(result["externalSubmission"], "not_executed")
                self.assertNotIn("business-secret-token", str(result))

    @patch("src.data_entry.waveapps_account_discovery.requests.post")
    def test_invalid_json_and_graphql_business_errors_are_classified(self, mock_post):
        invalid_json = MagicMock()
        invalid_json.status_code = 200
        invalid_json.raise_for_status.return_value = None
        invalid_json.json.side_effect = ValueError("invalid json")
        mock_post.return_value = invalid_json

        invalid_result = WaveappsAccountDiscoveryService(self.config).discover("waveapps_business")

        self.assertEqual(invalid_result["status"], "provider_error")
        self.assertIn("invalid response", invalid_result["message"])

        missing_business = MagicMock()
        missing_business.status_code = 200
        missing_business.raise_for_status.return_value = None
        missing_business.json.return_value = {
            "data": {"business": None},
            "errors": [{"message": "Business not found for the supplied id."}],
        }
        mock_post.return_value = missing_business

        missing_result = WaveappsAccountDiscoveryService(self.config).discover("waveapps_business")

        self.assertEqual(missing_result["status"], "business_not_found")
        self.assertIn("business ID", missing_result["nextAction"])

    def test_default_category_account_does_not_replace_explicit_category_mapping(self):
        config = dict(self.config)
        config["waveapps_business_category_account_ids"] = {}
        config["waveapps_business_default_category_account_id"] = "default-expense"

        mapping = WaveappsAccountDiscoveryService(config).mapping_status("waveapps_business")["targets"][0]

        self.assertFalse(mapping["configured"])
        self.assertIn("categoryAccountIds", mapping["requiredMissing"])
        self.assertIsNone(mapping["defaultCategoryAccount"]["verified"])
        self.assertFalse(mapping["verified"])


if __name__ == "__main__":
    unittest.main()
