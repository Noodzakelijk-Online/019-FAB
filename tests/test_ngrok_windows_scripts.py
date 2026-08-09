import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TestNgrokWindowsScripts(unittest.TestCase):
    def test_managed_launcher_is_authenticated_isolated_and_non_pooling(self):
        script = (ROOT / "Start-FAB-Ngrok.ps1").read_text(encoding="utf-8")

        self.assertIn(".venv\\Scripts\\python.exe", script)
        self.assertIn("Another ngrok endpoint is already active", script)
        self.assertIn("FAB will not stop or pool the existing endpoint", script)
        self.assertIn('"--name", "fab-managed"', script)
        self.assertIn("/api/live", script)
        self.assertIn("/api/hai/manifest", script)
        self.assertIn("authRequired", script)
        self.assertIn("maintenanceMode", script)
        self.assertIn("Test-CleanHttpsOrigin -Uri $publicUri", script)
        self.assertIn("Write-JsonAtomic", script)
        self.assertNotIn("pooling-enabled", script.lower())

    def test_managed_stop_requires_checkout_process_and_overlay_ownership(self):
        script = (ROOT / "Stop-FAB-Ngrok.ps1").read_text(encoding="utf-8")

        self.assertIn("instanceId", script)
        self.assertIn("fab-ngrok-tunnel", script)
        self.assertIn("ngrok.exe", script)
        self.assertIn("fab-managed", script)
        self.assertIn("overlayMarker", script)
        self.assertIn("Test-OwnedManagedPath", script)
        self.assertIn("Refusing to stop", script)

    def test_main_shutdown_stops_cloud_before_api_and_uses_isolated_python(self):
        script = (ROOT / "Stop-FAB.ps1").read_text(encoding="utf-8")

        ngrok_stop = script.index("Stop-FAB-Ngrok.ps1")
        api_stop = script.index(
            'Stop-FabProcessTree -ProcessId $ownedApiPid -CommandMarker "src.operations.local_api"'
        )
        self.assertLess(ngrok_stop, api_stop)
        self.assertIn(".venv\\Scripts\\python.exe", script)
        self.assertIn("name_prefix='hai_command:'", script)
        self.assertIn("owned_hai_api_stopped", script)
        self.assertNotIn("Get-Command python -ErrorAction Stop", script)

    def test_cmd_launchers_forward_operator_arguments(self):
        start_cmd = (ROOT / "Start-FAB-Ngrok.cmd").read_text(encoding="utf-8")
        stop_cmd = (ROOT / "Stop-FAB-Ngrok.cmd").read_text(encoding="utf-8")

        self.assertIn("Start-FAB-Ngrok.ps1", start_cmd)
        self.assertIn("Stop-FAB-Ngrok.ps1", stop_cmd)
        self.assertIn("%*", start_cmd)
        self.assertIn("%*", stop_cmd)

    def test_managed_and_verification_tunnels_refuse_maintenance_mode(self):
        managed = (ROOT / "Start-FAB-Ngrok.ps1").read_text(encoding="utf-8")
        verification = (ROOT / "Test-FAB-Ngrok.ps1").read_text(encoding="utf-8")

        self.assertIn("disabled during maintenance", managed)
        self.assertIn("localLive.maintenanceMode", managed)
        self.assertIn("disabled during maintenance", verification)
        self.assertIn("localLive.maintenanceMode", verification)


if __name__ == "__main__":
    unittest.main()
