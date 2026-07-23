from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, Optional

from src.config_loader import ConfigLoader
from src.document_fetchers.drive_archiver import DriveArchiveClient


def authorize_google_drive(
    config: Optional[Dict[str, Any]] = None,
    client_factory: Callable[[Dict[str, Any]], DriveArchiveClient] = DriveArchiveClient,
) -> Dict[str, Any]:
    settings = dict(
        config
        or ConfigLoader(config_file="config/config.ini").get_all_config()
    )
    credentials_path = _absolute_config_path(
        settings.get("google_drive_credentials_file")
        or settings.get("drive_credentials_path")
        or "credentials/drive_credentials.json"
    )
    token_path = _absolute_config_path(
        settings.get("google_drive_token_file")
        or settings.get("drive_token_path")
        or "tokens/drive_token.pickle"
    )
    folder_id = str(
        settings.get("google_drive_folder_id")
        or settings.get("drive_folder_id")
        or ""
    ).strip()

    if not os.path.isfile(credentials_path):
        return {
            "success": False,
            "status": "credentials_required",
            "error": (
                "Google OAuth desktop credentials are missing. Download the OAuth "
                f"client JSON and place it at {credentials_path}."
            ),
            "credentialsPath": credentials_path,
            "tokenPath": token_path,
        }
    if not folder_id:
        return {
            "success": False,
            "status": "folder_required",
            "error": "Configure google_drive.folder_id before authorizing Drive.",
            "credentialsPath": credentials_path,
            "tokenPath": token_path,
        }

    settings["google_drive_credentials_file"] = credentials_path
    settings["google_drive_token_file"] = token_path
    settings["google_drive_interactive_auth"] = True
    try:
        client = client_factory(settings)
        folder = client.inspect_file(folder_id)
    except Exception as exc:
        return {
            "success": False,
            "status": "authorization_failed",
            "error": _safe_error(exc),
            "credentialsPath": credentials_path,
            "tokenPath": token_path,
        }

    if folder.get("trashed") or folder.get("mimeType") != "application/vnd.google-apps.folder":
        return {
            "success": False,
            "status": "folder_unavailable",
            "error": "The configured Google Drive source is unavailable or is not a folder.",
            "credentialsPath": credentials_path,
            "tokenPath": token_path,
        }
    if not os.path.isfile(token_path):
        return {
            "success": False,
            "status": "token_not_written",
            "error": "Google authorization completed without writing the configured token file.",
            "credentialsPath": credentials_path,
            "tokenPath": token_path,
        }
    return {
        "success": True,
        "status": "authorized",
        "scope": "full_drive_move_and_read",
        "folderVerified": True,
        "tokenPath": token_path,
    }


def main() -> int:
    result = authorize_google_drive()
    print(json.dumps(result, indent=2))
    return 0 if result.get("success") else 2


def _absolute_config_path(value: Any) -> str:
    return os.path.abspath(os.path.expanduser(str(value or "")))


def _safe_error(error: Exception) -> str:
    message = " ".join(str(error or type(error).__name__).split())
    return message[:500] or type(error).__name__


if __name__ == "__main__":
    raise SystemExit(main())
