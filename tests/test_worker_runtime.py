import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.utils.runtime_identity import local_instance_id
from src.worker.runtime import WorkerAlreadyRunningError, managed_worker_runtime


class TestWorkerRuntime(unittest.TestCase):
    def test_runtime_descriptor_tracks_the_owned_process_and_cleans_up(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime_path = root / "data" / "fab-worker-runtime.json"

            with managed_worker_runtime(root) as runtime:
                saved = json.loads(runtime_path.read_text(encoding="utf-8"))
                self.assertEqual(saved["service"], "fab-autonomous-worker")
                self.assertEqual(saved["pid"], os.getpid())
                self.assertEqual(saved["instanceRoot"], str(root.resolve()))
                self.assertEqual(saved["instanceId"], local_instance_id(root))
                self.assertEqual(saved, runtime)

            self.assertFalse(runtime_path.exists())

    def test_runtime_lock_rejects_a_second_worker_process(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script = (
                "import sys,time\n"
                "from pathlib import Path\n"
                "from src.worker.runtime import managed_worker_runtime\n"
                "with managed_worker_runtime(Path(sys.argv[1])):\n"
                " print('ready', flush=True)\n"
                " time.sleep(30)\n"
            )
            child = subprocess.Popen(
                [sys.executable, "-c", script, temp_dir],
                cwd=Path(__file__).resolve().parents[1],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                self.assertEqual(child.stdout.readline().strip(), "ready")
                with self.assertRaises(WorkerAlreadyRunningError):
                    with managed_worker_runtime(Path(temp_dir)):
                        self.fail("A second worker unexpectedly acquired the runtime lock.")
            finally:
                child.terminate()
                child.wait(timeout=10)


if __name__ == "__main__":
    unittest.main()
