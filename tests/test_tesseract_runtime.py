import os
import tempfile
import unittest

from src.utils.tesseract_runtime import (
    available_tesseract_languages,
    configured_tesseract_languages,
    resolve_poppler_path,
    resolve_tesseract_command,
    tesseract_cli_config,
)


class TestTesseractRuntime(unittest.TestCase):
    def test_resolves_explicit_executable_languages_and_data_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            executable = os.path.join(temp_dir, "tesseract.exe")
            tessdata = os.path.join(temp_dir, "tessdata")
            os.makedirs(tessdata)
            with open(executable, "wb") as handle:
                handle.write(b"test")
            for language in ("eng", "nld"):
                with open(os.path.join(tessdata, f"{language}.traineddata"), "wb") as handle:
                    handle.write(b"test")
            config = {
                "tesseract_cmd": executable,
                "tesseract_data_dir": tessdata,
                "tesseract_lang": "nld+eng",
            }

            self.assertEqual(resolve_tesseract_command(config), executable)
            self.assertEqual(configured_tesseract_languages(config), ["nld", "eng"])
            self.assertEqual(available_tesseract_languages(config), ["eng", "nld"])
            cli_config = tesseract_cli_config(config)
            if os.name == "nt":
                self.assertEqual(os.environ["TESSDATA_PREFIX"], tessdata)
                self.assertNotIn("--tessdata-dir", cli_config)
            else:
                self.assertIn("--tessdata-dir", cli_config)

    def test_resolves_explicit_poppler_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            executable = os.path.join(temp_dir, "pdftoppm.exe")
            with open(executable, "wb") as handle:
                handle.write(b"test")

            self.assertEqual(resolve_poppler_path({"poppler_path": temp_dir}), temp_dir)


if __name__ == "__main__":
    unittest.main()
