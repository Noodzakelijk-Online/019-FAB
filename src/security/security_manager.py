from cryptography.fernet import Fernet
import os
from typing import Dict, Any

class SecurityManager:
    """Manages secure storage and retrieval of credentials and sensitive data."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.key = self._load_or_generate_key()
        self.fernet = Fernet(self.key)

    def _load_or_generate_key(self) -> bytes:
        key_path = self.config.get("encryption_key_path", "./.encryption_key")
        if os.path.exists(key_path):
            with open(key_path, "rb") as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(key_path, "wb") as f:
                f.write(key)
            os.chmod(key_path, 0o600) # Set restrictive permissions
        return key

    def encrypt_data(self, data: str) -> bytes:
        """Encrypts a string."""
        return self.fernet.encrypt(data.encode())

    def decrypt_data(self, encrypted_data: bytes) -> str:
        """Decrypts a string."""
        return self.fernet.decrypt(encrypted_data).decode()

    def get_credential(self, key: str) -> str:
        """Retrieves a decrypted credential from configuration or environment variables."""
        encrypted_value = self.config.get(key)
        if encrypted_value:
            try:
                return self.decrypt_data(encrypted_value.encode()) # Assuming it's stored as base64 string
            except Exception as e:
                print(f"Error decrypting credential {key}: {e}. Trying as plain text.")
                return encrypted_value # Fallback to plain text if decryption fails
        
        # Try environment variable as fallback
        env_var_name = key.upper().replace(".", "_") # Convert config key to env var name
        env_value = os.getenv(env_var_name)
        if env_value:
            return env_value

        return None

    def set_credential(self, key: str, value: str):
        """Encrypts and sets a credential in the configuration."""
        encrypted_value = self.encrypt_data(value).decode() # Store as base64 string
        self.config[key] = encrypted_value


