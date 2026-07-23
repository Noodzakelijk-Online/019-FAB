import os
from pathlib import Path

from src.config_loader import ConfigLoader
from src.worker.scheduler import FabWorker
from src.worker.runtime import WorkerAlreadyRunningError, managed_worker_runtime


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[1]
    os.chdir(project_root)
    try:
        with managed_worker_runtime(project_root):
            config = ConfigLoader(config_file="config/config.ini").get_all_config()
            FabWorker(config).run()
    except WorkerAlreadyRunningError as exc:
        raise SystemExit(f"FAB worker not started: {exc}") from None
