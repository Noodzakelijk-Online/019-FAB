from src.config_loader import ConfigLoader
from src.data_entry.posting_executor import PostingExecutor


if __name__ == "__main__":
    config = ConfigLoader(config_file="config/config.ini").get_all_config()
    result = PostingExecutor(config).process_approved_attempts()
    print(result)
