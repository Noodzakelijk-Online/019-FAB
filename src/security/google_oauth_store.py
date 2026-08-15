from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Iterable, Optional

try:
    from google.oauth2.credentials import Credentials
except ImportError:
    Credentials = None


LEGACY_TOKEN_SUFFIXES = {".pickle", ".pkl"}


class LegacyGoogleOAuthTokenError(RuntimeError):
    """Raised when only an unsafe legacy pickle token is available."""


def normalize_google_token_path(value: Any) -> str:
    configured = os.path.abspath(
        os.path.expandvars(os.path.expanduser(str(value or "")))
    )
    root, extension = os.path.splitext(configured)
    if extension.lower() == ".json":
        return configured
    return f"{root}.json" if extension else f"{configured}.json"


class GoogleOAuthTokenStore:
    """Load and persist Google user credentials without executable formats."""

    def __init__(
        self,
        configured_path: Any,
        scopes: Iterable[str],
        *,
        credentials_type: Optional[Any] = None,
    ) -> None:
        self.configured_path = os.path.abspath(
            os.path.expandvars(os.path.expanduser(str(configured_path or "")))
        )
        self.token_path = normalize_google_token_path(self.configured_path)
        self.scopes = list(scopes)
        self.credentials_type = credentials_type or Credentials

    @property
    def legacy_paths(self) -> list[str]:
        extension = os.path.splitext(self.configured_path)[1].lower()
        root = os.path.splitext(self.token_path)[0]
        candidates = []
        if extension and extension != ".json":
            candidates.append(self.configured_path)
        candidates.extend(f"{root}{suffix}" for suffix in sorted(LEGACY_TOKEN_SUFFIXES))
        return list(dict.fromkeys(candidates))

    @property
    def legacy_path(self) -> Optional[str]:
        existing = next((path for path in self.legacy_paths if os.path.isfile(path)), None)
        if existing:
            return existing
        extension = os.path.splitext(self.configured_path)[1].lower()
        return self.configured_path if extension in LEGACY_TOKEN_SUFFIXES else None

    @property
    def marker_path(self) -> str:
        return f"{self.token_path}.reauthorize"

    @property
    def marker_paths(self) -> list[str]:
        paths = [self.marker_path]
        for legacy_path in self.legacy_paths:
            legacy_marker = f"{legacy_path}.reauthorize"
            if legacy_marker not in paths:
                paths.append(legacy_marker)
        return paths

    def status(self) -> dict[str, Any]:
        token_present = os.path.isfile(self.token_path)
        legacy_path = next(
            (path for path in self.legacy_paths if os.path.isfile(path)),
            None,
        )
        legacy_present = bool(legacy_path)
        marker = next((path for path in self.marker_paths if os.path.isfile(path)), None)
        reason = self._marker_reason(marker)
        if not reason and legacy_present and not token_present:
            reason = "legacy_pickle_token_unsupported"
        return {
            "configuredTokenPath": self.configured_path,
            "tokenPath": self.token_path,
            "tokenPresent": token_present,
            "legacyTokenPath": legacy_path,
            "legacyTokenPresent": legacy_present,
            "reauthorizationRequired": bool(marker or (legacy_present and not token_present)),
            "reauthorizationReason": reason,
            "markerPath": self.marker_path,
        }

    def load(self) -> Any:
        if self.credentials_type is None:
            raise ImportError("google-auth is required for Google OAuth access.")
        if not os.path.isfile(self.token_path):
            if any(os.path.isfile(path) for path in self.legacy_paths):
                raise LegacyGoogleOAuthTokenError(
                    "Legacy Google OAuth pickle tokens are unsupported; complete supervised reauthorization to create a JSON token."
                )
            raise FileNotFoundError(
                f"Google OAuth token is missing; complete supervised authorization to create {self.token_path}."
            )
        return self.credentials_type.from_authorized_user_file(
            self.token_path,
            self.scopes,
        )

    def save(self, credentials: Any) -> str:
        serialized = credentials.to_json()
        try:
            payload = json.loads(serialized)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Google OAuth credentials did not serialize as valid JSON.") from exc
        if not isinstance(payload, dict):
            raise ValueError("Google OAuth credentials must serialize as a JSON object.")

        directory = os.path.dirname(self.token_path)
        os.makedirs(directory, exist_ok=True)
        descriptor, temporary_path = tempfile.mkstemp(
            prefix=".fab-google-oauth-",
            suffix=".tmp",
            dir=directory,
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle, separators=(",", ":"), sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            _make_private(temporary_path)
            os.replace(temporary_path, self.token_path)
            _make_private(self.token_path)
        finally:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)
        self.clear_reauthorization()
        return self.token_path

    def mark_reauthorization(self, reason: str) -> None:
        payload = json.dumps(
            {"reason": str(reason or "oauth_token_revoked_or_expired")},
            separators=(",", ":"),
        ).encode("utf-8")
        _atomic_private_write(self.marker_path, payload)

    def clear_reauthorization(self) -> None:
        for path in self.marker_paths:
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass

    @staticmethod
    def _marker_reason(path: Optional[str]) -> Optional[str]:
        if not path:
            return None
        try:
            with open(path, "r", encoding="utf-8") as handle:
                content = handle.read(4096)
            payload = json.loads(content)
            reason = payload.get("reason") if isinstance(payload, dict) else None
            if reason:
                return str(reason)[:200]
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            pass
        return "oauth_token_revoked_or_expired"


def _atomic_private_write(path: str, content: bytes) -> None:
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary_path = tempfile.mkstemp(
        prefix=".fab-google-oauth-marker-",
        suffix=".tmp",
        dir=directory,
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        _make_private(temporary_path)
        os.replace(temporary_path, path)
        _make_private(path)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)


def _make_private(path: str) -> None:
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
