import os
import tempfile
import unittest

from src.config_loader import ConfigLoader
from src.document_fetchers.local_folder_fetcher import LocalFolderFetcher
from src.routing.bookkeeping_router import BookkeepingRouter


class TestLocalWiring(unittest.TestCase):
    def test_config_loader_returns_sectioned_and_flat_values(self):
        with tempfile.TemporaryDirectory() as tempdir:
            config_path = os.path.join(tempdir, "config.ini")
            with open(config_path, "w", encoding="utf-8") as handle:
                handle.write("[app]\nlog_file = logs/test.log\nenabled_fetchers = local_folder\n")

            config = ConfigLoader(config_path).get_all_config()
            self.assertEqual(config["app"]["log_file"], "logs/test.log")
            self.assertEqual(config["log_file"], "logs/test.log")
            self.assertEqual(config["enabled_fetchers"], "local_folder")

    def test_local_folder_fetcher_finds_supported_documents(self):
        with tempfile.TemporaryDirectory() as tempdir:
            receipt_path = os.path.join(tempdir, "receipt.pdf")
            ignored_path = os.path.join(tempdir, "notes.txt")
            with open(receipt_path, "wb") as handle:
                handle.write(b"%PDF-1.4 test")
            with open(ignored_path, "w", encoding="utf-8") as handle:
                handle.write("ignore")

            fetcher = LocalFolderFetcher({"local_input_dir": tempdir})
            documents = fetcher.fetch_documents()
            self.assertEqual(len(documents), 1)
            self.assertEqual(documents[0]["source"], "local_folder")
            self.assertEqual(documents[0]["original_filename"], "receipt.pdf")
            self.assertTrue(documents[0]["id"].startswith("local_"))

    def test_router_supports_category_a_b_c(self):
        router = BookkeepingRouter({})
        self.assertEqual(router.resolve_target({"category": "A"}), "mijngeldzaken")
        self.assertEqual(router.resolve_target({"category": "B"}), "waveapps_business")
        self.assertEqual(router.resolve_target({"category": "C"}), "waveapps_personal")


if __name__ == "__main__":
    unittest.main()
