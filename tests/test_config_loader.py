import os
import tempfile
import unittest

from src.config_loader import ConfigLoader


class TestConfigLoader(unittest.TestCase):
    def setUp(self):
        self._original_env = {
            key: os.environ.get(key)
            for key in ("FAB_LOCAL_LEDGER_PATH", "FAB_LOCAL_API_PORT")
        }

    def tearDown(self):
        for key, value in self._original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_sectioned_config_values_are_available_as_flat_aliases(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.ini")
            with open(config_path, "w", encoding="utf-8") as handle:
                handle.write(
                    "[gmail]\nquery=has:attachment\n"
                    "[google_drive]\nfolder_id=sort-out\n"
                    "[reconciliation]\n"
                    "reconciliation_threshold=0.05\n"
                    "reconciliation_date_tolerance_days=2\n"
                )

            config = ConfigLoader(config_file=config_path).get_all_config()

        self.assertEqual(config["gmail"]["query"], "has:attachment")
        self.assertEqual(config["gmail_query"], "has:attachment")
        self.assertEqual(config["google_drive_folder_id"], "sort-out")
        self.assertEqual(config["reconciliation_threshold"], "0.05")
        self.assertEqual(config["reconciliation_date_tolerance_days"], "2")

    def test_direct_fab_local_environment_values_are_flat_aliases(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = os.path.join(temp_dir, "env-ledger.sqlite3")
            os.environ["FAB_LOCAL_LEDGER_PATH"] = ledger_path
            os.environ["FAB_LOCAL_API_PORT"] = "5052"
            config_path = os.path.join(temp_dir, "missing.ini")

            config = ConfigLoader(config_file=config_path).get_all_config()

        self.assertEqual(config["fab_local_ledger_path"], ledger_path)
        self.assertEqual(config["fab_local_api_port"], "5052")


if __name__ == "__main__":
    unittest.main()
