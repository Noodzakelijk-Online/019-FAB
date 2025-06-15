from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
from typing import List, Dict, Any
import pickle
import requests

from src.document_fetchers.base import BaseFetcher

class PhotosFetcher(BaseFetcher):
    """Fetches documents (images) from Google Photos."""

    # The Photos API does not have a direct way to search for 'documents' or 'receipts'.
    # This fetcher will iterate through media items and download them. Further processing
    # (like OCR) will determine if they are financial documents.
    SCOPES = ["https://www.googleapis.com/auth/photoslibrary.readonly"]

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.creds = None
        self.service = None
        self._authenticate()

    def _authenticate(self):
        token_path = self.config.get("photos_token_path", "token_photos.pickle")
        credentials_path = self.config.get("photos_credentials_path", "credentials_photos.json")

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

        self.service = build("photoslibrary", "v1", credentials=self.creds, static_discovery=False)

    def fetch_documents(self) -> List[Dict[str, Any]]:
        attachments_dir = self.config.get("attachments_save_dir", "/tmp/photos_attachments")
        os.makedirs(attachments_dir, exist_ok=True)

        documents = []
        page_token = None
        try:
            while True:
                results = self.service.mediaItems().list(pageSize=100, pageToken=page_token).execute()
                items = results.get("mediaItems", [])

                if not items:
                    print("No media items found in Google Photos.")
                    break

                for item in items:
                    # The Google Photos API provides a 'baseUrl' for downloading the image.
                    # We can append '=d' to download the original size.
                    download_url = item["baseUrl"] + "=d"
                    file_name = item["filename"]
                    
                    try:
                        response = requests.get(download_url, stream=True)
                        response.raise_for_status()
                        
                        local_path = os.path.join(attachments_dir, file_name)
                        with open(local_path, "wb") as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)

                        documents.append({
                            "id": item["id"],
                            "source": "google_photos",
                            "original_filename": file_name,
                            "local_path": local_path,
                            "timestamp": item["creationTime"],
                            "metadata": {
                                "mime_type": item["mimeType"],
                                "product_url": item["productUrl"]
                            }
                        })
                    except requests.exceptions.RequestException as e:
                        print(f"Error downloading {file_name}: {e}")

                page_token = results.get("nextPageToken")
                if not page_token:
                    break

        except HttpError as error:
            print(f"An error occurred: {error}")
        return documents


