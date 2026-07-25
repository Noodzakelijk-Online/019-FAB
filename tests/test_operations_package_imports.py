import subprocess
import sys
import unittest


class TestOperationsPackageImports(unittest.TestCase):
    def test_wave_entity_sync_imports_cleanly_in_a_cold_process(self):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "from src.data_entry.waveapps_entity_sync "
                    "import WaveappsEntitySyncService; "
                    "from src.operations import LocalAutonomousService; "
                    "assert WaveappsEntitySyncService and LocalAutonomousService"
                ),
            ],
            capture_output=True,
            check=False,
            text=True,
            timeout=30,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_operations_public_exports_remain_available(self):
        from src.operations import LocalBackupService, LocalOperationsLedger

        self.assertEqual(LocalBackupService.__name__, "LocalBackupService")
        self.assertEqual(LocalOperationsLedger.__name__, "LocalOperationsLedger")


if __name__ == "__main__":
    unittest.main()
