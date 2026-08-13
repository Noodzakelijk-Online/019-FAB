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
        self.assertIn("$env:FAB_LOCAL_API_PUBLIC_URL = $apiBaseUrl", script)
        self.assertIn("$previousLocalApiPublicUrl = $env:FAB_LOCAL_API_PUBLIC_URL", script)
        self.assertIn("Remove-Item Env:FAB_LOCAL_API_PUBLIC_URL", script)
        self.assertIn("$env:FAB_INSTANCE_ROOT = $root", script)
        self.assertIn("$previousApiInstanceRoot = $env:FAB_INSTANCE_ROOT", script)
        self.assertIn("$previousWorkerInstanceRoot = $env:FAB_INSTANCE_ROOT", script)
        self.assertIn("$previousWebInstanceRoot = $env:FAB_INSTANCE_ROOT", script)
        self.assertIn("Remove-Item Env:FAB_INSTANCE_ROOT", script)
        self.assertIn('dist\\fab-standalone.js', script)
        self.assertIn('"dist/fab-standalone.js"', script)
        self.assertIn('$env:FAB_WEB_HOST = "127.0.0.1"', script)
        self.assertIn('$env:FAB_OPERATOR_LOCAL_MODE = "true"', script)
        self.assertIn("Remove-Item Env:FAB_WEB_HOST", script)
        self.assertIn("Remove-Item Env:FAB_OPERATOR_LOCAL_MODE", script)

    def test_stop_launcher_recognizes_the_lean_operator_server(self):
        script = (ROOT / "Stop-FAB.ps1").read_text(encoding="utf-8")

        self.assertIn('dist/fab-standalone.js', script)

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

    def test_maintenance_launcher_is_quiescent_local_and_argument_aware(self):
        script = (ROOT / "Start-FAB.ps1").read_text(encoding="utf-8")
        start_cmd = (ROOT / "Start-FAB.cmd").read_text(encoding="utf-8")
        maintenance_cmd = (ROOT / "Start-FAB-Maintenance.cmd").read_text(encoding="utf-8")

        self.assertIn("[switch]$Maintenance", script)
        self.assertIn("FAB_MAINTENANCE_MODE", script)
        self.assertIn("ExpectedMaintenanceMode", script)
        self.assertIn("-not $requestedMaintenanceMode -and -not $workerPid", script)
        self.assertIn("maintenanceMode = $requestedMaintenanceMode", script)
        self.assertIn("Start-FAB.ps1", start_cmd)
        self.assertIn("%*", start_cmd)
        self.assertIn("-Maintenance", maintenance_cmd)
        self.assertIn("%*", maintenance_cmd)


if __name__ == "__main__":
    unittest.main()
