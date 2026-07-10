import configparser
import json
import os
from typing import Any, Dict

class ConfigLoader:
    """Loads sectioned config while preserving legacy flat config keys."""

    def __init__(self, config_file: str = "config/config.ini"):
        self.config_file = config_file
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        config_data: Dict[str, Any] = {}
        parser = configparser.ConfigParser()
        
        if os.path.exists(self.config_file):
            parser.read(self.config_file)
            for section in parser.sections():
                config_data[section] = {}
                for key, value in parser.items(section):
                    parsed_value = self._parse_value(value)
                    config_data[section][key] = parsed_value
                    config_data[key] = parsed_value
        
        # Override with environment variables (e.g., for sensitive data)
        for key, value in os.environ.items():
            parsed_value = self._parse_value(value)
            if key.startswith("APP_"):
                # Example: APP_GMAIL_CLIENT_ID -> gmail.client_id
                parts = key[len("APP_"):].lower().split("_", 1)
                if len(parts) == 2:
                    section, option = parts
                    if section not in config_data:
                        config_data[section] = {}
                    config_data[section][option] = parsed_value
                    config_data[option] = parsed_value
                else:
                    config_data[key.lower()] = parsed_value # For single-level env vars
            elif key.startswith("FAB_"):
                # Example: FAB_LOCAL_LEDGER_PATH -> fab_local_ledger_path
                config_data[key.lower()] = parsed_value

        self._add_flat_aliases(config_data)
        return config_data

    @staticmethod
    def _parse_value(value: Any) -> Any:
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        lowered = stripped.lower()
        if lowered in {"true", "yes", "on"}:
            return True
        if lowered in {"false", "no", "off"}:
            return False
        if lowered in {"none", "null"}:
            return None
        if stripped.startswith(("{", "[")):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                pass
        return stripped

    def _add_flat_aliases(self, config_data: Dict[str, Any]) -> None:
        """Expose sectioned values as flat keys for legacy workflow modules."""
        for section, values in list(config_data.items()):
            if not isinstance(values, dict):
                continue
            for key, value in values.items():
                config_data.setdefault(f"{section}_{key}", value)
                if key.startswith(f"{section}_"):
                    config_data.setdefault(key, value)

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Retrieves a configuration value."""
        return self.config.get(section, {}).get(key, default)

    def get_section(self, section: str) -> Dict[str, Any]:
        """Retrieves an entire configuration section."""
        return self.config.get(section, {})

    def get_all_config(self) -> Dict[str, Any]:
        """Returns the entire loaded configuration."""
        return self.config


