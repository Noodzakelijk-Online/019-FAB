import json
import os
import tempfile
import threading
import time
import unittest

from src.operations.local_gmail_auth import LocalGmailAuthorizationCoordinator
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


class TestLocalGmailAuthorizationCoordinator(unittest.TestCase):
    def _config(self, temp_dir):
        return {
            "gmail_credentials_file": os.path.join(temp_dir, "credentials", "gmail.json"),
            "gmail_token_file": os.path.join(temp_dir, "tokens", "gmail.pickle"),
            "gmail_scanner_mode": True,
            "gmail_trusted_senders": "eprintcenter@hp8.us",
            "gmail_query": "label:all from:eprintcenter@hp8.us has:attachment filename:pdf",
        }

    def test_installs_credentials_and_exposes_scanner_policy_without_secret(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            coordinator = LocalGmailAuthorizationCoordinator(ledger, self._config(temp_dir))

            result = coordinator.install_credentials(
                desktop_credentials(),
                filename="desktop-client.json",
                actor="test_operator",
            )

            status = coordinator.status()
            self.assertTrue(result["success"])
            self.assertEqual(status["status"], "ready_to_authorize")
            self.assertTrue(status["scannerMode"])
            self.assertEqual(status["trustedSenders"], ["eprintcenter@hp8.us"])
            audit_json = json.dumps(ledger.list_audit_events(limit=10))
            self.assertIn("gmail.oauth_credentials.installed", audit_json)
            self.assertNotIn("local-desktop-secret", audit_json)

    def test_runs_one_read_only_authorization_and_verifies_mailbox(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self._config(temp_dir)
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            authorization_started = threading.Event()
            allow_completion = threading.Event()

            def authorize(settings):
                authorization_started.set()
                allow_completion.wait(timeout=3)
                os.makedirs(os.path.dirname(settings["gmail_token_file"]), exist_ok=True)
                with open(settings["gmail_token_file"], "wb") as handle:
                    handle.write(b"test-token")
                return {
                    "success": True,
                    "status": "authorized",
                    "mailboxVerified": True,
                    "emailAddress": "bookkeeping@example.com",
                }

            coordinator = LocalGmailAuthorizationCoordinator(ledger, config, authorize=authorize)
            self.assertEqual(coordinator.start()["status"], "credentials_required")
            coordinator.install_credentials(desktop_credentials(), filename="desktop-client.json")

            started = coordinator.start(actor="test_operator")
            self.assertTrue(started["success"])
            self.assertTrue(authorization_started.wait(timeout=2))
            self.assertEqual(coordinator.start()["status"], "authorization_in_progress")
            allow_completion.set()
            for _ in range(100):
                if not coordinator.status()["authorizationInProgress"]:
                    break
                time.sleep(0.02)

            status = coordinator.status()
            self.assertEqual(status["status"], "authorized")
            self.assertTrue(status["tokenPresent"])
            self.assertEqual(status["emailAddress"], "bookkeeping@example.com")
            actions = [item["action"] for item in ledger.list_audit_events(limit=10)]
            self.assertIn("gmail.authorization.started", actions)
            self.assertIn("gmail.authorization.completed", actions)

    def test_credential_rotation_blocks_worker_until_fresh_consent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self._config(temp_dir)
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            observed_force = []

            def authorize(settings):
                observed_force.append(settings.get("gmail_force_reauthorization"))
                with open(settings["gmail_token_file"], "wb") as handle:
                    handle.write(b"rotated-token")
                return {"success": True, "status": "authorized", "mailboxVerified": True}

            coordinator = LocalGmailAuthorizationCoordinator(ledger, config, authorize=authorize)
            coordinator.install_credentials(desktop_credentials(), filename="desktop-client.json")
            os.makedirs(os.path.dirname(config["gmail_token_file"]), exist_ok=True)
            with open(config["gmail_token_file"], "wb") as handle:
                handle.write(b"old-token")
            coordinator.install_credentials(
                desktop_credentials("rotated-secret"),
                filename="desktop-client.json",
                replace=True,
            )

            self.assertEqual(coordinator.status()["status"], "reauthorization_required")
            coordinator.start()
            for _ in range(100):
                if not coordinator.status()["authorizationInProgress"]:
                    break
                time.sleep(0.02)

            self.assertEqual(observed_force, [True])
            self.assertFalse(coordinator.status()["reauthorizationRequired"])


if __name__ == "__main__":
    unittest.main()
