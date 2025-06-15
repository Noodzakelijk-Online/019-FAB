import configparser
import os
from typing import Dict, Any

class ConfigLoader:
    """Loads configuration from a .ini file and environment variables."""

    def __init__(self, config_file: str = "config/config.ini"):
        self.config_file = config_file
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        config_data = {}
        parser = configparser.ConfigParser()
        
        if os.path.exists(self.config_file):
            parser.read(self.config_file)
            for section in parser.sections():
                config_data[section] = {}
                for key, value in parser.items(section):
                    config_data[section][key] = value
        
        # Override with environment variables (e.g., for sensitive data)
        for key, value in os.environ.items():
            if key.startswith("APP_"):
                # Example: APP_GMAIL_CLIENT_ID -> gmail.client_id
                parts = key[len("APP_"):].lower().split("_", 1)
                if len(parts) == 2:
                    section, option = parts
                    if section not in config_data:
                        config_data[section] = {}
                    config_data[section][option] = value
                else:
                    config_data[key.lower()] = value # For single-level env vars

        return config_data

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Retrieves a configuration value."""
        return self.config.get(section, {}).get(key, default)

    def get_section(self, section: str) -> Dict[str, Any]:
        """Retrieves an entire configuration section."""
        return self.config.get(section, {})

    def get_all_config(self) -> Dict[str, Any]:
        """Returns the entire loaded configuration."""
        return self.config


