from __future__ import annotations

import hashlib
import io
import os
import pickle
from typing import Any, Dict, Optional

try:
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
except ImportError:
    Request = None
    InstalledAppFlow = None
    build = None
    MediaIoBaseDownload = None


class DriveArchiveClient:
    """Move a verified Drive source while preserving its provider file ID."""

    SCOPES = ["https://www.googleapis.com/auth/drive"]
    FILE_FIELDS = "id,name,mimeType,parents,size,md5Checksum,trashed,webViewLink"

    def __init__(self, config: Optional[Dict[str, Any]] = None, service: Any = None):
        self.config = config or {}
        self.service = service or self._authenticate()

    def inspect_file(self, file_id: str) -> Dict[str, Any]:
        return self.service.files().get(
            fileId=str(file_id),
            fields=self.FILE_FIELDS,
            supportsAllDrives=True,
        ).execute()

    def download_sha256(self, file_id: str) -> str:
        if MediaIoBaseDownload is None:
            raise RuntimeError("Google Drive download support is unavailable.")
        request = self.service.files().get_media(fileId=str(file_id), supportsAllDrives=True)
        stream = io.BytesIO()
        downloader = MediaIoBaseDownload(stream, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return hashlib.sha256(stream.getvalue()).hexdigest()

    def move_file(self, file_id: str, source_folder_id: str, archive_folder_id: str) -> Dict[str, Any]:
        before = self.inspect_file(file_id)
        parents = set(before.get("parents") or [])
        if archive_folder_id in parents and source_folder_id not in parents:
            return {"status": "already_archived", "before": before, "after": before}
        if source_folder_id not in parents:
            raise RuntimeError("Drive source file is no longer in the configured intake folder.")

        self.service.files().update(
            fileId=str(file_id),
            addParents=str(archive_folder_id),
            removeParents=str(source_folder_id),
            fields=self.FILE_FIELDS,
            supportsAllDrives=True,
        ).execute()
        after = self.inspect_file(file_id)
        after_parents = set(after.get("parents") or [])
        if archive_folder_id not in after_parents or source_folder_id in after_parents:
            try:
                self.service.files().update(
                    fileId=str(file_id),
                    addParents=str(source_folder_id),
                    removeParents=str(archive_folder_id),
                    fields=self.FILE_FIELDS,
                    supportsAllDrives=True,
                ).execute()
            except Exception:
                pass
            raise RuntimeError("Drive archive postcondition failed; rollback was attempted.")
        return {"status": "archived", "before": before, "after": after}

    def _authenticate(self) -> Any:
        if build is None or Request is None or InstalledAppFlow is None:
            raise RuntimeError("Google Drive API dependencies are required for verified archiving.")
        token_path = str(
            self.config.get("google_drive_token_file")
            or self.config.get("drive_token_path")
            or "tokens/drive_token.pickle"
        )
        credentials_path = str(
            self.config.get("google_drive_credentials_file")
            or self.config.get("drive_credentials_path")
            or "credentials/drive_credentials.json"
        )
        credentials = None
        force_reauthorization = _as_bool(
            self.config.get("google_drive_force_reauthorization"),
            False,
        )
        if os.path.exists(token_path) and not force_reauthorization:
            with open(token_path, "rb") as handle:
                credentials = pickle.load(handle)

        scopes_valid = bool(credentials) and (
            not hasattr(credentials, "has_scopes") or credentials.has_scopes(self.SCOPES)
        )
        if credentials and credentials.expired and credentials.refresh_token and scopes_valid:
            credentials.refresh(Request())
        if not credentials or not credentials.valid or not scopes_valid:
            if not _as_bool(self.config.get("google_drive_interactive_auth"), False):
                raise RuntimeError(
                    "Google Drive archiving needs a valid full-Drive OAuth token; "
                    "run supervised authorization with google_drive.interactive_auth enabled."
                )
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, self.SCOPES)
            credentials = flow.run_local_server(port=0)
            os.makedirs(os.path.dirname(os.path.abspath(token_path)), exist_ok=True)
            with open(token_path, "wb") as handle:
                pickle.dump(credentials, handle)
        return build("drive", "v3", credentials=credentials)


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "enabled"}
