import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock

from src.security.google_oauth_store import (
    GoogleOAuthTokenStore,
    LegacyGoogleOAuthTokenError,
    normalize_google_token_path,
)


class FakeCredentialsType:
    loaded = []

    @classmethod
    def from_authorized_user_file(cls, path, scopes):
        cls.loaded.append((path, list(scopes)))
        return {"path": path, "scopes": list(scopes)}


class TestGoogleOAuthTokenStore(unittest.TestCase):
    def setUp(self):
        FakeCredentialsType.loaded = []

    def test_normalizes_legacy_pickle_path_to_sibling_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            configured = os.path.join(temp_dir, "tokens", "drive_token.pickle")

            self.assertEqual(
                normalize_google_token_path(configured),
                os.path.join(temp_dir, "tokens", "drive_token.json"),
            )

    def test_legacy_pickle_is_never_loaded_and_requires_reauthorization(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            legacy_path = os.path.join(temp_dir, "gmail_token.pickle")
            with open(legacy_path, "wb") as handle:
                handle.write(b"not-safe-to-deserialize")
            store = GoogleOAuthTokenStore(
                legacy_path,
                ["gmail.readonly"],
                credentials_type=FakeCredentialsType,
            )

            status = store.status()
            self.assertFalse(status["tokenPresent"])
            self.assertTrue(status["legacyTokenPresent"])
            self.assertTrue(status["reauthorizationRequired"])
            self.assertEqual(status["reauthorizationReason"], "legacy_pickle_token_unsupported")
            with self.assertRaises(LegacyGoogleOAuthTokenError):
                store.load()
            self.assertEqual(FakeCredentialsType.loaded, [])
            self.assertTrue(os.path.isfile(legacy_path))

    def test_json_configuration_still_detects_an_existing_legacy_sibling(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            json_path = os.path.join(temp_dir, "gmail_token.json")
            legacy_path = os.path.join(temp_dir, "gmail_token.pickle")
            with open(legacy_path, "wb") as handle:
                handle.write(b"legacy-token-evidence")
            store = GoogleOAuthTokenStore(
                json_path,
                ["gmail.readonly"],
                credentials_type=FakeCredentialsType,
            )

            status = store.status()

            self.assertFalse(status["tokenPresent"])
            self.assertTrue(status["legacyTokenPresent"])
            self.assertEqual(status["legacyTokenPath"], legacy_path)
            self.assertEqual(
                status["reauthorizationReason"],
                "legacy_pickle_token_unsupported",
            )
            with self.assertRaises(LegacyGoogleOAuthTokenError):
                store.load()
            self.assertEqual(FakeCredentialsType.loaded, [])

    def test_safe_json_sibling_takes_precedence_without_touching_legacy_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            legacy_path = os.path.join(temp_dir, "drive_token.pickle")
            json_path = os.path.join(temp_dir, "drive_token.json")
            with open(legacy_path, "wb") as handle:
                handle.write(b"legacy-evidence")
            with open(json_path, "w", encoding="utf-8") as handle:
                json.dump({"token": "redacted"}, handle)
            store = GoogleOAuthTokenStore(
                legacy_path,
                ["drive"],
                credentials_type=FakeCredentialsType,
            )

            credentials = store.load()

            self.assertEqual(credentials["path"], json_path)
            self.assertEqual(FakeCredentialsType.loaded, [(json_path, ["drive"])])
            self.assertFalse(store.status()["reauthorizationRequired"])
            with open(legacy_path, "rb") as handle:
                self.assertEqual(handle.read(), b"legacy-evidence")

    def test_save_writes_private_json_atomically_and_clears_markers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            configured = os.path.join(temp_dir, "tokens", "photos.pickle")
            store = GoogleOAuthTokenStore(configured, ["photos"])
            os.makedirs(os.path.dirname(store.marker_path), exist_ok=True)
            with open(store.marker_path, "w", encoding="utf-8") as handle:
                handle.write("reauthorize")
            credentials = MagicMock()
            credentials.to_json.return_value = json.dumps({"token": "secret"})

            written_path = store.save(credentials)

            self.assertEqual(written_path, os.path.join(temp_dir, "tokens", "photos.json"))
            with open(written_path, "r", encoding="utf-8") as handle:
                self.assertEqual(json.load(handle), {"token": "secret"})
            self.assertFalse(os.path.exists(store.marker_path))
            self.assertFalse(os.path.exists(f"{written_path}.tmp"))


if __name__ == "__main__":
    unittest.main()
