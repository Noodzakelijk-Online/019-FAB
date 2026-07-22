import json
import os
import tempfile
import unittest

from src.operations.local_api import create_app
from src.operations.local_readiness import LocalReadinessService


class TestLocalReadinessService(unittest.TestCase):
    def test_readiness_reports_sources_and_redacts_secret_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            intake_dir = os.path.join(temp_dir, "sort-out")
            os.makedirs(intake_dir)
            gmail_credentials = os.path.join(temp_dir, "gmail_credentials.json")
            gmail_token = os.path.join(temp_dir, "gmail_token.pickle")
            for path in (gmail_credentials, gmail_token):
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write("{}")

            summary = LocalReadinessService(
                {
                    "gmail": {
                        "credentials_file": gmail_credentials,
                        "token_file": gmail_token,
                    },
                    "waveapps_business": {
                        "access_token": "wave-business-secret",
                        "business_id": "business-123",
                    },
                    "mijngeldzaken_password": "mgz-secret",
                    "freshdesk_api_key": "freshdesk-secret",
                    "freshdesk_domain": "example",
                },
                ledger_path=os.path.join(temp_dir, "fab.sqlite3"),
                api_host="127.0.0.1",
                api_port=5055,
                api_token_configured=True,
                intake_paths=[intake_dir],
                intake_extensions=["pdf", "txt"],
            ).summarize()
            rendered = json.dumps(summary, sort_keys=True)
            sources = {source["id"]: source for source in summary["sources"]}
            credentials = {credential["id"]: credential for credential in summary["credentials"]}

            self.assertEqual(sources["local_folder"]["status"], "ready")
            self.assertEqual(sources["gmail"]["status"], "ready")
            self.assertEqual(sources["waveapps_business"]["status"], "ready")
            self.assertEqual(sources["mijngeldzaken"]["status"], "supervision_required")
            self.assertTrue(sources["mijngeldzaken"]["localArtifactReady"])
            self.assertFalse(sources["mijngeldzaken"]["ready"])
            self.assertIn("stored passwords are ignored", sources["mijngeldzaken"]["details"])
            self.assertTrue(credentials["wave_business_token"]["configured"])
            self.assertIn("ignored", credentials["mijngeldzaken_password"]["label"])
            self.assertTrue(summary["security"]["secretValuesRedacted"])
            self.assertEqual(summary["localAccess"]["dashboardUrl"], "http://127.0.0.1:5055/")
            self.assertEqual(summary["localAccess"]["apiBaseUrl"], "http://127.0.0.1:5055/api")
            self.assertEqual(summary["localAccess"]["authMode"], "bearer_token_or_dashboard_login")
            self.assertEqual(summary["localAccess"]["ngrokSafety"], "safe_with_token")
            self.assertIn("FAB_LOCAL_API_TOKEN", summary["localAccess"]["windows"]["recommendedEnvironment"])
            self.assertNotIn("wave-business-secret", rendered)
            self.assertNotIn("mgz-secret", rendered)
            self.assertNotIn("freshdesk-secret", rendered)
            self.assertNotIn("api-secret-token", rendered)

    def test_remote_host_without_api_token_is_blocked(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            summary = LocalReadinessService(
                {},
                ledger_path=os.path.join(temp_dir, "fab.sqlite3"),
                api_host="0.0.0.0",
                api_token_configured=False,
                intake_paths=[],
                intake_extensions=[],
            ).summarize()

            self.assertEqual(summary["status"], "blocked")
            self.assertFalse(summary["security"]["remoteExposureSafe"])
            self.assertEqual(summary["localAccess"]["ngrokSafety"], "blocked_without_token")
            self.assertIn("remote_api_without_token", {issue["type"] for issue in summary["issues"]})

    def test_drive_readiness_blocks_sync_during_oauth_client_rotation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            credentials_path = os.path.join(temp_dir, "drive.json")
            token_path = os.path.join(temp_dir, "drive.pickle")
            for path in (credentials_path, token_path, f"{token_path}.reauthorize"):
                with open(path, "wb") as handle:
                    handle.write(b"configured")

            summary = LocalReadinessService({
                "google_drive_credentials_file": credentials_path,
                "google_drive_token_file": token_path,
                "google_drive_folder_id": "approved-source-folder",
            }).summarize()
            drive = next(item for item in summary["sources"] if item["id"] == "google_drive")

            self.assertFalse(drive["ready"])
            self.assertEqual(drive["status"], "needs_authorization")
            self.assertIn("fresh Google consent", drive["details"])

    def test_base_url_overrides_displayed_local_access_without_exposing_token(self):
        summary = LocalReadinessService(
            {"fab_local_api_base_url": "https://fab-local.example.ngrok-free.app", "fab_local_api_token": "secret-token"},
            ledger_path="data/fab.sqlite3",
            api_host="127.0.0.1",
            api_port=5001,
            api_token_configured=True,
            intake_paths=[],
            intake_extensions=[],
        ).summarize()
        rendered = json.dumps(summary, sort_keys=True)

        self.assertEqual(summary["localAccess"]["dashboardUrl"], "https://fab-local.example.ngrok-free.app/")
        self.assertEqual(summary["localAccess"]["apiBaseUrl"], "https://fab-local.example.ngrok-free.app/api")
        self.assertEqual(summary["localAccess"]["authHeaderExample"], "Authorization: Bearer <FAB_LOCAL_API_TOKEN>")
        self.assertNotIn("secret-token", rendered)

    def test_connector_api_url_cannot_replace_local_fab_access_url(self):
        summary = LocalReadinessService(
            {
                "api_url": "https://gql.waveapps.com/graphql/public",
                "waveapps_api_url": "https://gql.waveapps.com/graphql/public",
            },
            ledger_path="data/fab.sqlite3",
            api_host="127.0.0.1",
            api_port=5001,
            api_token_configured=False,
            intake_paths=[],
            intake_extensions=[],
        ).summarize()

        self.assertEqual(summary["localAccess"]["dashboardUrl"], "http://127.0.0.1:5001/")
        self.assertEqual(summary["localAccess"]["apiBaseUrl"], "http://127.0.0.1:5001/api")

    def test_local_ocr_readiness_requires_pdf_tools_and_configured_languages(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            executable = os.path.join(temp_dir, "tesseract.exe")
            poppler_dir = os.path.join(temp_dir, "poppler")
            tessdata_dir = os.path.join(temp_dir, "tessdata")
            os.makedirs(poppler_dir)
            os.makedirs(tessdata_dir)
            for path in (executable, os.path.join(poppler_dir, "pdftoppm.exe")):
                with open(path, "wb") as handle:
                    handle.write(b"test")
            for language in ("eng", "nld"):
                with open(os.path.join(tessdata_dir, f"{language}.traineddata"), "wb") as handle:
                    handle.write(b"test")

            summary = LocalReadinessService({
                "tesseract_cmd": executable,
                "tesseract_data_dir": tessdata_dir,
                "tesseract_lang": "nld+eng",
                "poppler_path": poppler_dir,
            }).summarize()
            dependencies = {item["id"]: item for item in summary["dependencies"]}
            sources = {item["id"]: item for item in summary["sources"]}

            self.assertEqual(dependencies["tesseract_languages"]["status"], "ok")
            self.assertEqual(dependencies["poppler"]["status"], "ok")
            self.assertEqual(sources["tesseract_ocr"]["status"], "ready")

    def test_category_model_readiness_does_not_claim_an_untrained_model(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = os.path.join(temp_dir, "model.joblib")
            vectorizer_path = os.path.join(temp_dir, "vectorizer.joblib")
            missing_summary = LocalReadinessService({
                "ml_model_path": model_path,
                "ml_vectorizer_path": vectorizer_path,
            }).summarize()
            missing = next(
                item for item in missing_summary["dependencies"]
                if item["id"] == "category_model"
            )

            self.assertEqual(missing["status"], "attention")
            self.assertFalse(missing["configured"])

            for path in (model_path, vectorizer_path):
                with open(path, "wb") as handle:
                    handle.write(b"approved-test-artifact")
            ready_summary = LocalReadinessService({
                "ml_model_path": model_path,
                "ml_vectorizer_path": vectorizer_path,
            }).summarize()
            ready = next(
                item for item in ready_summary["dependencies"]
                if item["id"] == "category_model"
            )

            self.assertEqual(ready["status"], "ok")
            self.assertTrue(ready["configured"])

    def test_api_settings_and_dashboard_render_readiness_without_secrets(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            intake_dir = os.path.join(temp_dir, "sort-out")
            os.makedirs(intake_dir)
            app = create_app({
                "fab_local_ledger_path": os.path.join(temp_dir, "fab.sqlite3"),
                "fab_local_intake_paths": intake_dir,
                "fab_local_api_token": "api-secret-token",
                "waveapps_business_access_token": "wave-secret-token",
                "waveapps_business_id": "business-123",
            })
            client = app.test_client()
            headers = {"Authorization": "Bearer api-secret-token"}

            settings = client.get("/api/settings", headers=headers)
            health = client.get("/api/health", headers=headers)
            dashboard = client.get("/", headers=headers)
            settings_text = settings.data.decode("utf-8")
            dashboard_html = dashboard.data.decode("utf-8")

            self.assertEqual(settings.status_code, 200)
            self.assertEqual(health.status_code, 200)
            self.assertIn("readiness", health.get_json())
            self.assertEqual(health.get_json()["readiness"]["authMode"], "bearer_token_or_dashboard_login")
            self.assertEqual(settings.get_json()["sources"][0]["id"], "local_folder")
            self.assertIn("localAccess", settings.get_json())
            self.assertEqual(settings.get_json()["localAccess"]["authHeaderExample"], "Authorization: Bearer <FAB_LOCAL_API_TOKEN>")
            self.assertIn("Source Status", dashboard_html)
            self.assertIn("Dependency Status", dashboard_html)
            self.assertIn("Credential Status", dashboard_html)
            self.assertIn("Windows Local Runbook", dashboard_html)
            self.assertIn("python -m src.operations.local_api", dashboard_html)
            self.assertIn("Authorization: Bearer &lt;FAB_LOCAL_API_TOKEN&gt;", dashboard_html)
            self.assertNotIn("api-secret-token", settings_text)
            self.assertNotIn("wave-secret-token", settings_text)
            self.assertNotIn("api-secret-token", dashboard_html)
            self.assertNotIn("wave-secret-token", dashboard_html)


if __name__ == "__main__":
    unittest.main()
