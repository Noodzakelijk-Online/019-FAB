import os
import tempfile
import unittest

from src.security.local_secret_store import (
    LocalSecretStore,
    LocalSecretStoreError,
    apply_local_wave_settings,
)


class TestLocalSecretStore(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config = {
            "fab_local_secret_store_path": os.path.join(self.temp_dir.name, "credentials", "secrets.enc"),
            "fab_local_secret_key_path": os.path.join(self.temp_dir.name, "credentials", "secrets.key"),
        }
        self.original_token = os.environ.pop("FAB_WAVEAPPS_BUSINESS_ACCESS_TOKEN", None)

    def tearDown(self):
        if self.original_token is not None:
            os.environ["FAB_WAVEAPPS_BUSINESS_ACCESS_TOKEN"] = self.original_token
        else:
            os.environ.pop("FAB_WAVEAPPS_BUSINESS_ACCESS_TOKEN", None)
        self.temp_dir.cleanup()

    def test_round_trip_encrypts_wave_token_and_mapping_at_rest(self):
        store = LocalSecretStore(self.config)

        status = store.update_wave_target("waveapps_business", {
            "access_token": "private-wave-token",
            "business_id": "business-1",
            "anchor_account_id": "anchor-1",
            "default_category_account_id": "expense-1",
            "category_account_ids": {"Office": "expense-1"},
        })
        loaded = LocalSecretStore(self.config).load()
        with open(self.config["fab_local_secret_store_path"], "rb") as handle:
            encrypted_bytes = handle.read()
        with open(self.config["fab_local_secret_key_path"], "rb") as handle:
            key_envelope = handle.read()

        self.assertTrue(status["encryptedAtRest"])
        self.assertTrue(status["accessTokenStored"])
        self.assertEqual(
            loaded["wave"]["waveapps_business"]["access_token"],
            "private-wave-token",
        )
        self.assertNotIn(b"private-wave-token", encrypted_bytes)
        self.assertNotIn(b"private-wave-token", key_envelope)
        self.assertIn(status["keyProtector"], {"windows_dpapi_current_user", "file_permissions"})

    def test_local_settings_overlay_keeps_environment_token_authoritative(self):
        LocalSecretStore(self.config).update_wave_target("waveapps_business", {
            "access_token": "stored-token",
            "business_id": "stored-business",
        })
        os.environ["FAB_WAVEAPPS_BUSINESS_ACCESS_TOKEN"] = "environment-token"
        base = {
            **self.config,
            "waveapps_business_access_token": "environment-token",
            "waveapps_business": {"access_token": "environment-token"},
        }

        effective = apply_local_wave_settings(base)

        self.assertEqual(effective["waveapps_business_access_token"], "environment-token")
        self.assertEqual(effective["waveapps_business_id"], "stored-business")

    def test_corrupt_ciphertext_fails_closed_without_plaintext_fallback(self):
        store = LocalSecretStore(self.config)
        store.update_wave_target("waveapps_business", {"access_token": "private-token"})
        with open(self.config["fab_local_secret_store_path"], "wb") as handle:
            handle.write(b"not-valid-ciphertext")

        with self.assertRaisesRegex(LocalSecretStoreError, "could not be decrypted"):
            LocalSecretStore(self.config).load()

        effective = apply_local_wave_settings(self.config)
        self.assertNotIn("waveapps_business_access_token", effective)
        self.assertIn("could not be decrypted", effective["fab_local_secret_store_error"])

    def test_token_clear_revokes_a_previously_loaded_worker_value(self):
        store = LocalSecretStore(self.config)
        store.update_wave_target("waveapps_business", {
            "access_token": "previous-worker-token",
            "business_id": "business-1",
        })
        worker_config = apply_local_wave_settings(self.config)
        self.assertEqual(worker_config["waveapps_business_access_token"], "previous-worker-token")

        store.update_wave_target("waveapps_business", {}, clear_access_token=True)
        apply_local_wave_settings(worker_config, mutate=True)

        self.assertIsNone(worker_config["waveapps_business_access_token"])
        self.assertIsNone(worker_config["waveapps_business"]["access_token"])
        self.assertFalse(store.public_wave_status("waveapps_business")["accessTokenStored"])


if __name__ == "__main__":
    unittest.main()
