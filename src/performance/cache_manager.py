from typing import Any, Dict
import json
import os
import time

class CacheManager:
    """Manages caching of data to improve performance."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.cache_dir = self.config.get("cache_dir", "./cache")
        self.default_ttl = self.config.get("cache_default_ttl_seconds", 3600) # 1 hour
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_path(self, key: str) -> str:
        return os.path.join(self.cache_dir, f"{key}.json")

    def get(self, key: str) -> Any:
        cache_path = self._get_cache_path(key)
        if os.path.exists(cache_path):
            with open(cache_path, "r") as f:
                data = json.load(f)
                if time.time() < data["expiry"]:
                    return data["value"]
                else:
                    os.remove(cache_path) # Cache expired
        return None

    def set(self, key: str, value: Any, ttl: int = None):
        cache_path = self._get_cache_path(key)
        expiry = time.time() + (ttl if ttl is not None else self.default_ttl)
        data = {"value": value, "expiry": expiry}
        with open(cache_path, "w") as f:
            json.dump(data, f, indent=4)

    def invalidate(self, key: str):
        cache_path = self._get_cache_path(key)
        if os.path.exists(cache_path):
            os.remove(cache_path)

    def clear_all(self):
        for filename in os.listdir(self.cache_dir):
            file_path = os.path.join(self.cache_dir, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)


