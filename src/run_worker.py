from src.config_loader import ConfigLoader
from src.worker.scheduler import FabWorker


if __name__ == "__main__":
    config = ConfigLoader(config_file="config/config.ini").get_all_config()
    FabWorker(config).run()
