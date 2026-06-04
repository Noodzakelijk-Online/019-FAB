import configparser
import os
from typing import Any, Dict


class ConfigLoader:
    """Loads configuration from an .ini file and APP_ environment variables.

    Most legacy FAB modules expect a flat config dictionary, while the config
    file is section-based. get_all_config therefore returns both forms:
    - section dictionaries remain available under their section names;
    - every option is also exposed at the top level for legacy modules.
    """

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

        for key, value in os.environ.items():
            if not key.startswith("APP_"):
                continue
            parts = key[len("APP_"):].lower().split("_", 1)
            parsed_value = self._parse_value(value)
            if len(parts) == 2:
                section, option = parts
                config_data.setdefault(section, {})[option] = parsed_value
                config_data[option] = parsed_value
            else:
                config_data[key.lower()] = parsed_value

        return config_data

    @staticmethod
    def _parse_value(value: str) -> Any:
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
        return stripped

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Retrieves a configuration value from a section."""
        return self.config.get(section, {}).get(key, default)

    def get_section(self, section: str) -> Dict[str, Any]:
        """Retrieves an entire configuration section."""
        return self.config.get(section, {})

    def get_all_config(self) -> Dict[str, Any]:
        """Returns sectioned and flat configuration values."""
        return self.config
