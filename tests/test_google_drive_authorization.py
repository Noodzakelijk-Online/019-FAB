import json
import os
import tempfile
import unittest

from src.authorize_google_drive import authorize_google_drive


class FakeDriveClient:
    def __init__(self, config):
        self.config = config
        os.makedirs(os.path.dirname(config["google_drive_token_file"]), exist_ok=True)
        with open(config["google_drive_token_file"], "wb") as handle:
            handle.write(b"authorized-token")

    def inspect_file(self, file_id):
        return {
            "id": file_id,
            "mimeType": "application/vnd.google-apps.folder",
            "trashed": False,
        }


class TestGoogleDriveAuthorization(unittest.TestCase):
    def test_missing_desktop_credentials_fails_before_oauth(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = authorize_google_drive({
                "google_drive_credentials_file": os.path.join(temp_dir, "missing.json"),
                "google_drive_token_file": os.path.join(temp_dir, "token.pickle"),
                "google_drive_folder_id": "source-folder",
            })

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "credentials_required")

    def test_authorization_verifies_folder_and_token_postconditions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            credentials_path = os.path.join(temp_dir, "credentials.json")
            token_path = os.path.join(temp_dir, "tokens", "drive.pickle")
            with open(credentials_path, "w", encoding="utf-8") as handle:
                json.dump({"installed": {}}, handle)

            result = authorize_google_drive(
                {
                    "google_drive_credentials_file": credentials_path,
                    "google_drive_token_file": token_path,
                    "google_drive_folder_id": "source-folder",
                },
                client_factory=FakeDriveClient,
            )

            self.assertTrue(result["success"])
            self.assertEqual(result["status"], "authorized")
            self.assertTrue(result["folderVerified"])
            self.assertTrue(os.path.isfile(token_path))

    def test_authorization_rejects_a_trashed_or_non_folder_source(self):
        class InvalidFolderDriveClient(FakeDriveClient):
            def inspect_file(self, file_id):
                return {
                    "id": file_id,
                    "mimeType": "application/pdf",
                    "trashed": True,
                }

        with tempfile.TemporaryDirectory() as temp_dir:
            credentials_path = os.path.join(temp_dir, "credentials.json")
            token_path = os.path.join(temp_dir, "tokens", "drive.pickle")
            with open(credentials_path, "w", encoding="utf-8") as handle:
                json.dump({"installed": {}}, handle)

            result = authorize_google_drive(
                {
                    "google_drive_credentials_file": credentials_path,
                    "google_drive_token_file": token_path,
                    "google_drive_folder_id": "not-a-live-folder",
                },
                client_factory=InvalidFolderDriveClient,
            )

            self.assertFalse(result["success"])
            self.assertEqual(result["status"], "folder_unavailable")


if __name__ == "__main__":
    unittest.main()
