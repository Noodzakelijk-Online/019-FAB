from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlsplit

from src.authorize_google_drive import authorize_google_drive
from src.operations.local_ledger import LocalOperationsLedger


MAX_GOOGLE_OAUTH_CREDENTIAL_BYTES = 64 * 1024


class LocalGoogleDriveAuthorizationCoordinator:
    """Coordinate one user-owned Drive OAuth consent flow for the local FAB instance."""

    def __init__(
        self,
        ledger: LocalOperationsLedger,
        config: Optional[Dict[str, Any]] = None,
        authorize: Callable[[Optional[Dict[str, Any]]], Dict[str, Any]] = authorize_google_drive,
    ):
        self.ledger = ledger
        self.config = dict(config or {})
        self.authorize = authorize
        self.credentials_path = _absolute_path(
            _config_value(
                self.config,
                "google_drive_credentials_file",
                "drive_credentials_path",
                default="credentials/drive_credentials.json",
            )
        )
        self.token_path = _absolute_path(
            _config_value(
                self.config,
                "google_drive_token_file",
                "drive_token_path",
                default="tokens/drive_token.pickle",
            )
        )
        self.reauthorization_marker_path = f"{self.token_path}.reauthorize"
        self.folder_id = str(
            _config_value(
                self.config,
                "google_drive_folder_id",
                "drive_folder_id",
                default="",
            )
            or ""
        ).strip()
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._session: Dict[str, Any] = {
            "state": "idle",
            "startedAt": None,
            "finishedAt": None,
            "error": None,
        }

    def status(self) -> Dict[str, Any]:
        with self._lock:
            session = dict(self._session)
            running = bool(self._thread and self._thread.is_alive())
        credentials_present = os.path.isfile(self.credentials_path)
        token_present = os.path.isfile(self.token_path)
        reauthorization_required = os.path.isfile(self.reauthorization_marker_path)
        if running:
            state = "authorization_in_progress"
        elif session.get("state") not in {None, "idle"}:
            state = str(session["state"])
        elif reauthorization_required:
            state = "reauthorization_required"
        elif token_present:
            state = "token_present"
        elif credentials_present:
            state = "ready_to_authorize"
        else:
            state = "credentials_required"
        return {
            "status": state,
            "credentialsPresent": credentials_present,
            "tokenPresent": token_present,
            "reauthorizationRequired": reauthorization_required,
            "folderConfigured": bool(self.folder_id),
            "folderId": self.folder_id or None,
            "authorizationInProgress": running,
            "canInstallCredentials": not running,
            "canStartAuthorization": credentials_present and bool(self.folder_id) and not running,
            "startedAt": session.get("startedAt"),
            "finishedAt": session.get("finishedAt"),
            "error": session.get("error"),
            "scope": "full_drive_move_and_read",
            "archivePolicy": "move_only_after_verified_wave_attachment_readback",
            "externalSubmission": "user_owned_oauth_consent",
        }

    def install_credentials(
        self,
        content: bytes,
        *,
        filename: str,
        replace: bool = False,
        actor: str = "local_operator",
    ) -> Dict[str, Any]:
        if not str(filename or "").lower().endswith(".json"):
            raise ValueError("Google OAuth desktop credentials must be a JSON file.")
        if not content or len(content) > MAX_GOOGLE_OAUTH_CREDENTIAL_BYTES:
            raise ValueError(
                f"Google OAuth credential JSON must be between 1 and {MAX_GOOGLE_OAUTH_CREDENTIAL_BYTES} bytes."
            )
        _validate_google_desktop_credentials(content)
        with self._lock:
            if self._thread and self._thread.is_alive():
                raise RuntimeError("Google Drive authorization is already in progress.")
            existed_before = os.path.exists(self.credentials_path)
            if existed_before and not replace:
                raise FileExistsError(
                    "Google Drive credentials already exist. Confirm replacement explicitly to rotate them."
                )
            _atomic_private_write(self.credentials_path, content)
            reauthorization_required = os.path.isfile(self.token_path)
            if reauthorization_required:
                _atomic_private_write(
                    self.reauthorization_marker_path,
                    json.dumps({"requiredAt": _now(), "credentialSha256": hashlib.sha256(content).hexdigest()}).encode("utf-8"),
                )
            self._session = {
                "state": "reauthorization_required" if reauthorization_required else "ready_to_authorize",
                "startedAt": None,
                "finishedAt": None,
                "error": None,
            }
        digest = hashlib.sha256(content).hexdigest()
        self.ledger.record_audit_event({
            "action": "google_drive.oauth_credentials.installed",
            "entityType": "connector",
            "entityId": "google_drive",
            "details": {
                "actor": str(actor or "local_operator")[:200],
                "sha256": digest,
                "replacedExisting": existed_before,
                "credentialType": "installed_desktop_application",
                "secretValuesPersisted": True,
            },
        })
        return {
            "success": True,
            "status": "reauthorization_required" if reauthorization_required else "ready_to_authorize",
            "credentialsPresent": True,
            "sha256": digest,
            "externalSubmission": "not_executed",
        }

    def start(self, *, actor: str = "local_operator") -> Dict[str, Any]:
        actor = str(actor or "local_operator")[:200]
        with self._lock:
            if self._thread and self._thread.is_alive():
                return {
                    "success": True,
                    "status": "authorization_in_progress",
                    "startedAt": self._session.get("startedAt"),
                    "externalSubmission": "user_owned_oauth_consent",
                }
            if not os.path.isfile(self.credentials_path):
                return {
                    "success": False,
                    "status": "credentials_required",
                    "error": "Install Google OAuth desktop credentials before starting authorization.",
                    "externalSubmission": "not_executed",
                }
            if not self.folder_id:
                return {
                    "success": False,
                    "status": "folder_required",
                    "error": "Configure the approved Google Drive source folder before authorizing.",
                    "externalSubmission": "not_executed",
                }
            started_at = _now()
            self._session = {
                "state": "authorization_in_progress",
                "startedAt": started_at,
                "finishedAt": None,
                "error": None,
                "actor": actor,
            }
            self._thread = threading.Thread(
                target=self._run_authorization,
                args=(actor,),
                name="fab-google-drive-oauth",
                daemon=True,
            )
            self.ledger.record_audit_event({
                "action": "google_drive.authorization.started",
                "entityType": "connector",
                "entityId": "google_drive",
                "details": {
                    "actor": actor,
                    "scope": "full_drive_move_and_read",
                    "folderConfigured": True,
                    "externalSubmission": "user_owned_oauth_consent",
                },
            })
            self._thread.start()
        return {
            "success": True,
            "status": "authorization_started",
            "startedAt": started_at,
            "externalSubmission": "user_owned_oauth_consent",
        }

    def _run_authorization(self, actor: str) -> None:
        settings = dict(self.config)
        settings["google_drive_credentials_file"] = self.credentials_path
        settings["google_drive_token_file"] = self.token_path
        settings["google_drive_folder_id"] = self.folder_id
        settings["google_drive_force_reauthorization"] = os.path.isfile(
            self.reauthorization_marker_path
        )
        try:
            result = self.authorize(settings)
        except Exception as exc:
            result = {
                "success": False,
                "status": "authorization_failed",
                "error": _safe_error(exc),
            }
        success = bool(result.get("success"))
        state = "authorized" if success else str(result.get("status") or "authorization_failed")
        error = None if success else _safe_message(result.get("error"))
        finished_at = _now()
        if success and os.path.isfile(self.reauthorization_marker_path):
            os.unlink(self.reauthorization_marker_path)
        with self._lock:
            self._session = {
                "state": state,
                "startedAt": self._session.get("startedAt"),
                "finishedAt": finished_at,
                "error": error,
                "actor": actor,
            }
        self.ledger.record_audit_event({
            "action": "google_drive.authorization.completed" if success else "google_drive.authorization.failed",
            "entityType": "connector",
            "entityId": "google_drive",
            "details": {
                "actor": actor,
                "status": state,
                "folderVerified": bool(result.get("folderVerified")),
                "tokenPresent": os.path.isfile(self.token_path),
                "error": error,
                "externalSubmission": "user_owned_oauth_consent",
            },
        })


def _validate_google_desktop_credentials(content: bytes) -> None:
    try:
        payload = json.loads(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Google OAuth credentials are not valid UTF-8 JSON.") from exc
    installed = payload.get("installed") if isinstance(payload, dict) else None
    if not isinstance(installed, dict):
        raise ValueError("Use an OAuth client JSON for an installed desktop application.")
    client_id = str(installed.get("client_id") or "").strip()
    client_secret = str(installed.get("client_secret") or "").strip()
    if not client_id.endswith(".apps.googleusercontent.com") or not client_secret:
        raise ValueError("The OAuth desktop client ID or client secret is missing or invalid.")
    if not _trusted_google_url(installed.get("auth_uri"), {"accounts.google.com"}):
        raise ValueError("The OAuth authorization endpoint is not an approved Google endpoint.")
    if not _trusted_google_url(installed.get("token_uri"), {"oauth2.googleapis.com"}):
        raise ValueError("The OAuth token endpoint is not an approved Google endpoint.")
    redirect_uris = installed.get("redirect_uris")
    if not isinstance(redirect_uris, list) or not any(_local_redirect_uri(item) for item in redirect_uris):
        raise ValueError("The OAuth desktop client must allow a localhost callback URI.")


def _trusted_google_url(value: Any, hosts: set[str]) -> bool:
    parsed = urlsplit(str(value or ""))
    return parsed.scheme == "https" and (parsed.hostname or "").lower() in hosts


def _local_redirect_uri(value: Any) -> bool:
    parsed = urlsplit(str(value or ""))
    return parsed.scheme in {"http", "https"} and (parsed.hostname or "").lower() in {
        "localhost",
        "127.0.0.1",
        "::1",
    }


def _atomic_private_write(path: str, content: bytes) -> None:
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary_path = tempfile.mkstemp(prefix=".fab-drive-oauth-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.chmod(temporary_path, 0o600)
        except OSError:
            pass
        os.replace(temporary_path, path)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)


def _config_value(config: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        value = config.get(key)
        if value not in (None, ""):
            return value
    return default


def _absolute_path(value: Any) -> str:
    return os.path.abspath(os.path.expanduser(str(value or "")))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_error(error: Exception) -> str:
    return _safe_message(f"{type(error).__name__}: {error}")


def _safe_message(value: Any) -> str:
    message = " ".join(str(value or "Google Drive authorization failed.").split())
    lowered = message.lower()
    if "http://" in lowered or "https://" in lowered or any(
        marker in lowered for marker in ("client_secret", "access_token", "refresh_token", "authorization:")
    ):
        return "Google Drive authorization failed; sensitive provider details were omitted."
    return message[:500]
