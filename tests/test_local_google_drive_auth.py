import json
import os
import tempfile
import threading
import time
import unittest

from src.operations.local_google_drive_auth import LocalGoogleDriveAuthorizationCoordinator
from src.operations.local_ledger import LocalOperationsLedger


def desktop_credentials(client_secret="local-desktop-secret"):
    return json.dumps({
        "installed": {
            "client_id": "fab-test.apps.googleusercontent.com",
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }).encode("utf-8")


class TestLocalGoogleDriveAuthorizationCoordinator(unittest.TestCase):
    def test_installs_only_valid_desktop_credentials_and_audits_without_secret(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            credentials_path = os.path.join(temp_dir, "credentials", "drive.json")
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            coordinator = LocalGoogleDriveAuthorizationCoordinator(ledger, {
                "google_drive_credentials_file": credentials_path,
                "google_drive_token_file": os.path.join(temp_dir, "tokens", "drive.pickle"),
                "google_drive_folder_id": "approved-source-folder",
            })

            with self.assertRaises(ValueError):
                coordinator.install_credentials(b'{"web": {}}', filename="web-client.json")
            result = coordinator.install_credentials(
                desktop_credentials(),
                filename="desktop-client.json",
                actor="test_operator",
            )

            self.assertTrue(result["success"])
            self.assertEqual(coordinator.status()["status"], "ready_to_authorize")
            self.assertTrue(os.path.isfile(credentials_path))
            with self.assertRaises(FileExistsError):
                coordinator.install_credentials(
                    desktop_credentials("rotated-secret"),
                    filename="desktop-client.json",
                )
            audit_json = json.dumps(ledger.list_audit_events(limit=10))
            self.assertIn("google_drive.oauth_credentials.installed", audit_json)
            self.assertNotIn("local-desktop-secret", audit_json)

    def test_runs_one_background_authorization_and_reports_completion(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            credentials_path = os.path.join(temp_dir, "credentials", "drive.json")
            token_path = os.path.join(temp_dir, "tokens", "drive.pickle")
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            authorization_started = threading.Event()
            allow_completion = threading.Event()

            def authorize(config):
                authorization_started.set()
                allow_completion.wait(timeout=3)
                os.makedirs(os.path.dirname(config["google_drive_token_file"]), exist_ok=True)
                with open(config["google_drive_token_file"], "wb") as handle:
                    handle.write(b"test-token")
                return {
                    "success": True,
                    "status": "authorized",
                    "folderVerified": True,
                }

            coordinator = LocalGoogleDriveAuthorizationCoordinator(
                ledger,
                {
                    "google_drive_credentials_file": credentials_path,
                    "google_drive_token_file": token_path,
                    "google_drive_folder_id": "approved-source-folder",
                },
                authorize=authorize,
            )
            missing = coordinator.start(actor="test_operator")
            self.assertEqual(missing["status"], "credentials_required")
            coordinator.install_credentials(desktop_credentials(), filename="desktop-client.json")

            started = coordinator.start(actor="test_operator")
            self.assertTrue(started["success"])
            self.assertTrue(authorization_started.wait(timeout=2))
            repeated = coordinator.start(actor="test_operator")
            self.assertEqual(repeated["status"], "authorization_in_progress")
            allow_completion.set()
            for _ in range(100):
                if not coordinator.status()["authorizationInProgress"]:
                    break
                time.sleep(0.02)

            status = coordinator.status()
            self.assertEqual(status["status"], "authorized")
            self.assertTrue(status["tokenPresent"])
            actions = [item["action"] for item in ledger.list_audit_events(limit=10)]
            self.assertIn("google_drive.authorization.started", actions)
            self.assertIn("google_drive.authorization.completed", actions)
            self.assertLess(
                actions.index("google_drive.authorization.completed"),
                actions.index("google_drive.authorization.started"),
            )

    def test_redacts_provider_urls_from_failed_authorization_status(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            credentials_path = os.path.join(temp_dir, "drive.json")

            def authorize(_config):
                raise RuntimeError("failed at https://accounts.google.com/?code=secret-code")

            coordinator = LocalGoogleDriveAuthorizationCoordinator(
                ledger,
                {
                    "google_drive_credentials_file": credentials_path,
                    "google_drive_token_file": os.path.join(temp_dir, "drive.pickle"),
                    "google_drive_folder_id": "approved-source-folder",
                },
                authorize=authorize,
            )
            coordinator.install_credentials(desktop_credentials(), filename="desktop-client.json")
            coordinator.start()
            for _ in range(100):
                if not coordinator.status()["authorizationInProgress"]:
                    break
                time.sleep(0.02)

            error = coordinator.status()["error"]
            self.assertNotIn("secret-code", error)
            self.assertNotIn("https://", error)

    def test_credential_rotation_forces_fresh_authorization_before_token_is_ready(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            credentials_path = os.path.join(temp_dir, "drive.json")
            token_path = os.path.join(temp_dir, "drive.pickle")
            observed_force = []

            def authorize(config):
                observed_force.append(config.get("google_drive_force_reauthorization"))
                with open(config["google_drive_token_file"], "wb") as handle:
                    handle.write(b"rotated-token")
                return {"success": True, "status": "authorized", "folderVerified": True}

            coordinator = LocalGoogleDriveAuthorizationCoordinator(
                ledger,
                {
                    "google_drive_credentials_file": credentials_path,
                    "google_drive_token_file": token_path,
                    "google_drive_folder_id": "approved-source-folder",
                },
                authorize=authorize,
            )
            coordinator.install_credentials(desktop_credentials(), filename="desktop-client.json")
            with open(token_path, "wb") as handle:
                handle.write(b"old-token")
            coordinator.install_credentials(
                desktop_credentials("rotated-secret"),
                filename="desktop-client.json",
                replace=True,
            )

            pending = coordinator.status()
            self.assertTrue(pending["reauthorizationRequired"])
            self.assertEqual(pending["status"], "reauthorization_required")
            coordinator.start()
            for _ in range(100):
                if not coordinator.status()["authorizationInProgress"]:
                    break
                time.sleep(0.02)

            self.assertEqual(observed_force, [True])
            self.assertFalse(coordinator.status()["reauthorizationRequired"])
            self.assertEqual(coordinator.status()["status"], "authorized")


if __name__ == "__main__":
    unittest.main()
