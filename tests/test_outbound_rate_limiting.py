import unittest
from unittest.mock import MagicMock, patch

from src.data_entry.mijngeldzaken_handler import MijngeldzakenHandler
from src.data_entry.waveapps_business_handler import WaveappsBusinessHandler
from src.utils.rate_limiter import reset_all_limiters, set_rate_limiter


class TestOutboundRateLimiting(unittest.TestCase):
    def setUp(self):
        reset_all_limiters()
        self.document = {
            "document_id": "doc-rate-limit",
            "category": "Business",
            "extracted_data": {
                "description": "Printer paper",
                "total_amount": 42.5,
                "currency": "EUR",
                "transaction_date": "2026-07-10",
            },
        }

    def tearDown(self):
        reset_all_limiters()

    @patch("src.data_entry.waveapps_business_handler.requests.post")
    def test_wave_request_is_not_sent_when_daily_quota_is_exhausted(self, mock_post):
        set_rate_limiter("waveapps", calls_per_day=0, name="WaveApps")
        handler = WaveappsBusinessHandler({
            "waveapps_business_access_token": "token",
            "waveapps_business_id": "business-id",
        })

        result = handler.enter_data(self.document)

        self.assertEqual(result["status"], "quota_exhausted")
        self.assertTrue(result["retryable"])
        self.assertFalse(result["requires_manual_review"])
        self.assertEqual(result["retry_after_seconds"], 3600.0)
        mock_post.assert_not_called()

    @patch("src.data_entry.mijngeldzaken_handler.sync_playwright")
    def test_mijngeldzaken_browser_is_not_started_when_throttled(self, mock_sync_playwright):
        limiter = set_rate_limiter("mijngeldzaken", calls_per_second=1, calls_per_day=10, name="MijnGeldzaken")
        self.assertTrue(limiter.acquire(block=False))
        handler = MijngeldzakenHandler({
            "mijngeldzaken_username": "user",
            "mijngeldzaken_password": "password",
            "mijngeldzaken_csv_template": {"columns": [], "mapping": {}},
        })

        result = handler.enter_data(self.document)

        self.assertEqual(result["status"], "rate_limited")
        self.assertTrue(result["retryable"])
        self.assertFalse(result["requires_manual_review"])
        mock_sync_playwright.assert_not_called()


if __name__ == "__main__":
    unittest.main()
