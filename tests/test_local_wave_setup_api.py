import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from src.operations.local_api import create_app
from src.utils.rate_limiter import reset_all_limiters


class TestLocalWaveSetupApi(unittest.TestCase):
    def tearDown(self):
        reset_all_limiters()

    @patch("src.data_entry.waveapps_account_discovery.requests.post")
    def test_dashboard_api_saves_validates_and_maps_wave_without_exposing_token(self, mock_post):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "data": {
                "business": {
                    "id": "business-1",
                    "name": "FAB Test Business",
                    "accounts": {
                        "edges": [
                            {"node": {"id": "anchor-1", "name": "Current Account", "subtype": {"name": "Cash and Bank", "value": "CASH_AND_BANK"}}},
                            {"node": {"id": "expense-1", "name": "Office Expenses", "subtype": {"name": "Expense", "value": "EXPENSE"}}},
                        ],
                    },
                },
            },
        }
        mock_post.return_value = response
        with tempfile.TemporaryDirectory() as temp_dir:
            app = create_app({
                "fab_local_ledger_path": os.path.join(temp_dir, "fab.sqlite3"),
                "fab_local_secret_store_path": os.path.join(temp_dir, "credentials", "secrets.enc"),
                "fab_local_secret_key_path": os.path.join(temp_dir, "credentials", "secrets.key"),
            })
            client = app.test_client()

            saved = client.put("/api/wave/setup", json={
                "targetSystem": "waveapps_business",
                "accessToken": "private-wave-token",
                "businessId": "business-1",
                "actor": "dashboard-test",
            })
            validated = client.post("/api/wave/setup/validate", json={
                "targetSystem": "waveapps_business",
            })
            mapped = client.put("/api/wave/setup", json={
                "targetSystem": "waveapps_business",
                "anchorAccountId": "anchor-1",
                "defaultCategoryAccountId": "expense-1",
                "categoryAccountIds": {"Office Expenses": "expense-1"},
                "actor": "dashboard-test",
            })
            status = client.get("/api/wave/setup")
            audit = client.get("/api/audit?limit=20")
            with open(os.path.join(temp_dir, "credentials", "secrets.enc"), "rb") as handle:
                encrypted_bytes = handle.read()

        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.get_json()["status"], "needs_validation")
        self.assertEqual(validated.status_code, 200)
        self.assertEqual(validated.get_json()["setup"]["accounts"][0]["id"], "anchor-1")
        self.assertEqual(mapped.status_code, 200)
        self.assertTrue(mapped.get_json()["ready"])
        self.assertEqual(status.get_json()["status"], "ready")
        rendered = "\n".join(
            response.data.decode("utf-8")
            for response in (saved, validated, mapped, status, audit)
        )
        self.assertNotIn("private-wave-token", rendered)
        self.assertIn(
            "local_wave.settings_updated",
            {event["action"] for event in audit.get_json()["auditEvents"]},
        )
        self.assertNotIn(b"private-wave-token", encrypted_bytes)

    def test_setup_rejects_empty_tokens_and_unknown_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = create_app({
                "fab_local_ledger_path": os.path.join(temp_dir, "fab.sqlite3"),
                "fab_local_secret_store_path": os.path.join(temp_dir, "credentials", "secrets.enc"),
                "fab_local_secret_key_path": os.path.join(temp_dir, "credentials", "secrets.key"),
            }).test_client()

            empty = client.put("/api/wave/setup", json={"accessToken": ""})
            unknown = client.put("/api/wave/setup", json={"browserCookie": "unsafe"})
            malformed_mapping = client.put("/api/wave/setup", json={"categoryAccountIds": ["unsafe"]})
            conflicting_clear = client.put("/api/wave/setup", json={
                "accessToken": "private-token",
                "clearAccessToken": True,
            })
            malformed_validation = client.post("/api/wave/setup/validate", json=["unsafe"])

        self.assertEqual(empty.status_code, 400)
        self.assertIn("clearAccessToken", empty.get_json()["error"])
        self.assertEqual(unknown.status_code, 400)
        self.assertIn("Unsupported", unknown.get_json()["error"])
        self.assertEqual(malformed_mapping.status_code, 400)
        self.assertIn("categoryAccountIds", malformed_mapping.get_json()["error"])
        self.assertEqual(conflicting_clear.status_code, 400)
        self.assertIn("cannot be supplied together", conflicting_clear.get_json()["error"])
        self.assertEqual(malformed_validation.status_code, 400)
        self.assertIn("must be an object", malformed_validation.get_json()["error"])

    @patch("src.data_entry.waveapps_account_discovery.requests.post")
    def test_validation_returns_safe_actionable_authentication_failure(self, mock_post):
        response = MagicMock()
        response.status_code = 401
        mock_post.return_value = response
        with tempfile.TemporaryDirectory() as temp_dir:
            client = create_app({
                "fab_local_ledger_path": os.path.join(temp_dir, "fab.sqlite3"),
                "fab_local_secret_store_path": os.path.join(temp_dir, "credentials", "secrets.enc"),
                "fab_local_secret_key_path": os.path.join(temp_dir, "credentials", "secrets.key"),
            }).test_client()
            client.put("/api/wave/setup", json={
                "accessToken": "private-wave-token",
                "businessId": "business-1",
            })

            validated = client.post("/api/wave/setup/validate", json={
                "targetSystem": "waveapps_business",
            })

        payload = validated.get_json()
        self.assertEqual(validated.status_code, 401)
        self.assertEqual(payload["status"], "authentication_failed")
        self.assertIn("rejected the access token", payload["error"])
        self.assertIn("Replace", payload["nextAction"])
        self.assertNotIn("private-wave-token", validated.data.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
