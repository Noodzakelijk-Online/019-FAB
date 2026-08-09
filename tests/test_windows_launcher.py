import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TestWindowsLauncher(unittest.TestCase):
    def test_launcher_provisions_and_scopes_dashboard_signing_secret(self):
        script = (ROOT / "Start-FAB.ps1").read_text(encoding="utf-8")

        self.assertIn("get_or_create_runtime_secret('web_jwt_secret')", script)
        self.assertIn("$env:JWT_SECRET = $webJwtSecret", script)
        self.assertIn("$previousJwtSecret = $env:JWT_SECRET", script)
        self.assertIn("Remove-Item Env:JWT_SECRET", script)


if __name__ == "__main__":
    unittest.main()
