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

    def test_launcher_reconciles_only_its_checksum_bound_virtual_environment(self):
        script = (ROOT / "Start-FAB.ps1").read_text(encoding="utf-8")

        self.assertIn("requirements-local.txt", script)
        self.assertIn(".fab-requirements.sha256", script)
        self.assertIn("Get-FileHash -LiteralPath $requirementsPath -Algorithm SHA256", script)
        self.assertIn("[System.IO.FileAttributes]::ReparsePoint", script)
        self.assertIn('& (Join-Path $root "Stop-FAB.ps1")', script)
        self.assertIn("Remove-Item -LiteralPath $VenvPath -Recurse -Force", script)
        self.assertIn('Get-Command uv -ErrorAction SilentlyContinue', script)
        self.assertIn('@("venv", "--seed", "--python", "3.13", $venvRoot)', script)
        self.assertIn("-m pip check", script)
        self.assertIn("Set-Content -LiteralPath $venvRequirementsMarker", script)


if __name__ == "__main__":
    unittest.main()
