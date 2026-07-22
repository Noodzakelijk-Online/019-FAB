from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, Optional

from src.config_loader import ConfigLoader
from src.document_fetchers.gmail_fetcher import GmailFetcher


def authorize_gmail(
    config: Optional[Dict[str, Any]] = None,
    fetcher_factory: Callable[[Dict[str, Any]], GmailFetcher] = GmailFetcher,
) -> Dict[str, Any]:
    """Run supervised Gmail OAuth and verify read-only mailbox access."""

    settings = dict(
        config
        or ConfigLoader(config_file="config/config.ini").get_all_config()
    )
    credentials_path = _absolute_config_path(
        settings.get("gmail_credentials_file")
        or settings.get("gmail_credentials_path")
        or "credentials/gmail_credentials.json"
    )
    token_path = _absolute_config_path(
        settings.get("gmail_token_file")
        or settings.get("gmail_token_path")
        or "tokens/gmail_token.pickle"
    )

    if not os.path.isfile(credentials_path):
        return {
            "success": False,
            "status": "credentials_required",
            "error": "Google OAuth desktop credentials are missing for Gmail.",
            "credentialsPath": credentials_path,
            "tokenPath": token_path,
        }

    settings["gmail_credentials_file"] = credentials_path
    settings["gmail_token_file"] = token_path
    settings["gmail_interactive_auth"] = True
    try:
        fetcher = fetcher_factory(settings)
        if fetcher.auth_error:
            raise fetcher.auth_error
        profile = fetcher.service.users().getProfile(userId="me").execute()
    except Exception as exc:
        return {
            "success": False,
            "status": "authorization_failed",
            "error": _safe_error(exc),
            "credentialsPath": credentials_path,
            "tokenPath": token_path,
        }

    if not os.path.isfile(token_path):
        return {
            "success": False,
            "status": "token_not_written",
            "error": "Google authorization completed without writing the configured Gmail token file.",
            "credentialsPath": credentials_path,
            "tokenPath": token_path,
        }
    return {
        "success": True,
        "status": "authorized",
        "scope": "gmail_readonly",
        "mailboxVerified": True,
        "emailAddress": str(profile.get("emailAddress") or "") or None,
        "tokenPath": token_path,
    }


def main() -> int:
    result = authorize_gmail()
    print(json.dumps(result, indent=2))
    return 0 if result.get("success") else 2


def _absolute_config_path(value: Any) -> str:
    return os.path.abspath(os.path.expanduser(str(value or "")))


def _safe_error(error: Exception) -> str:
    message = " ".join(str(error or type(error).__name__).split())
    lowered = message.lower()
    if "http://" in lowered or "https://" in lowered or any(
        marker in lowered
        for marker in ("client_secret", "access_token", "refresh_token", "authorization:")
    ):
        return "Gmail authorization failed; sensitive provider details were omitted."
    return message[:500] or type(error).__name__


if __name__ == "__main__":
    raise SystemExit(main())
