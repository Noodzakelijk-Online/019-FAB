from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
import os
import io
from typing import List, Dict, Any
import pickle

from src.document_fetchers.base import BaseFetcher

class DriveFetcher(BaseFetcher):
    """Fetches documents from Google Drive based on specified folder ID."""

    SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.creds = None
        self.service = None
        self._authenticate()

    def _authenticate(self):
        token_path = self.config.get("drive_token_path", "token_drive.pickle")
        credentials_path = self.config.get("drive_credentials_path", "credentials_drive.json")

        if os.path.exists(token_path):
            with open(token_path, "rb") as token:
                self.creds = pickle.load(token)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, self.SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            with open(token_path, "wb") as token:
                pickle.dump(self.creds, token)

        self.service = build("drive", "v3", credentials=self.creds)

    def fetch_documents(self) -> List[Dict[str, Any]]:
        folder_id = self.config.get("drive_folder_id")
        if not folder_id:
            print("Google Drive folder ID not configured.")
            return []

        attachments_dir = self.config.get("attachments_save_dir", "/tmp/drive_attachments")
        os.makedirs(attachments_dir, exist_ok=True)

        documents = []
        try:
            # Search for files within the specified folder
            query = f"'{folder_id}' in parents and trashed = false"
            results = (
                self.service.files()
                .list(
                    q=query,
                    fields="nextPageToken, files(id, name, mimeType, createdTime)",
                    spaces="drive",
                )
                .execute()
            )
            items = results.get("files", [])

            if not items:
                print("No files found in the specified Google Drive folder.")
                return []

            for item in items:
                file_id = item["id"]
                file_name = item["name"]
                mime_type = item["mimeType"]
                created_time = item["createdTime"]

                # Download the file
                request = self.service.files().get_media(fileId=file_id)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()

                local_path = os.path.join(attachments_dir, file_name)
                with open(local_path, "wb") as f:
                    f.write(fh.getvalue())

                documents.append(
                    {
                        "id": file_id,
                        "source": "google_drive",
                        "original_filename": file_name,
                        "local_path": local_path,
                        "timestamp": created_time,
                        "metadata": {"mime_type": mime_type},
                    }
                )
        except HttpError as error:
            print(f"An error occurred: {error}")
        return documents


