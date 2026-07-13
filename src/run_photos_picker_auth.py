from src.config_loader import ConfigLoader
from src.document_fetchers.photos_picker_client import GooglePhotosPickerClient


def main() -> None:
    config = ConfigLoader(config_file="config/config.ini").get_all_config()
    result = GooglePhotosPickerClient(config).authorize_interactively()
    print(f"Google Photos Picker authorization complete: {result['tokenFile']}")


if __name__ == "__main__":
    main()
