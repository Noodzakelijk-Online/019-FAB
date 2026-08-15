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

    def test_runtime_signing_secret_is_stable_and_encrypted_at_rest(self):
        store = LocalSecretStore(self.config)

        first = store.get_or_create_runtime_secret("web_jwt_secret")
        second = LocalSecretStore(self.config).get_or_create_runtime_secret(
            "web_jwt_secret"
        )
        with open(self.config["fab_local_secret_store_path"], "rb") as handle:
            encrypted_bytes = handle.read()

        self.assertEqual(first, second)
        self.assertGreaterEqual(len(first), 32)
        self.assertNotIn(first.encode("ascii"), encrypted_bytes)
        self.assertEqual(
            LocalSecretStore(self.config).load()["runtime"]["web_jwt_secret"],
            first,
        )

    def test_operator_and_hai_credentials_are_distinct_encrypted_runtime_secrets(self):
        store = LocalSecretStore(self.config)

        operator_token = store.get_or_create_runtime_secret("operator_api_token")
        hai_token = store.get_or_create_runtime_secret("hai_api_token")
        loaded = LocalSecretStore(self.config).load()["runtime"]
        with open(self.config["fab_local_secret_store_path"], "rb") as handle:
            encrypted_bytes = handle.read()

        self.assertGreaterEqual(len(operator_token), 32)
        self.assertGreaterEqual(len(hai_token), 32)
        self.assertNotEqual(operator_token, hai_token)
        self.assertEqual(loaded["operator_api_token"], operator_token)
        self.assertEqual(loaded["hai_api_token"], hai_token)
        self.assertNotIn(operator_token.encode("ascii"), encrypted_bytes)
        self.assertNotIn(hai_token.encode("ascii"), encrypted_bytes)

    def test_runtime_signing_secret_rejects_unknown_names(self):
        with self.assertRaisesRegex(ValueError, "Unsupported FAB runtime secret"):
            LocalSecretStore(self.config).get_or_create_runtime_secret("unknown")

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

    def test_unreadable_store_revokes_managed_settings_until_recovery(self):
        store = LocalSecretStore(self.config)
        store.update_wave_target("waveapps_business", {
            "access_token": "first-token",
            "business_id": "first-business",
            "category_account_ids": {"Office": "expense-1"},
        })
        worker_config = apply_local_wave_settings(self.config)

        with open(self.config["fab_local_secret_store_path"], "wb") as handle:
            handle.write(b"not-valid-ciphertext")
        apply_local_wave_settings(worker_config, mutate=True)

        self.assertIsNone(worker_config["waveapps_business_access_token"])
        self.assertIsNone(worker_config["waveapps_business_id"])
        self.assertIsNone(worker_config["waveapps_business_category_account_ids"])
        self.assertIn("could not be decrypted", worker_config["fab_local_secret_store_error"])

        os.remove(self.config["fab_local_secret_store_path"])
        store.update_wave_target("waveapps_business", {
            "access_token": "replacement-token",
            "business_id": "replacement-business",
        })
        apply_local_wave_settings(worker_config, mutate=True)

        self.assertEqual(worker_config["waveapps_business_access_token"], "replacement-token")
        self.assertEqual(worker_config["waveapps_business_id"], "replacement-business")
        self.assertNotIn("fab_local_secret_store_error", worker_config)


if __name__ == "__main__":
    unittest.main()
