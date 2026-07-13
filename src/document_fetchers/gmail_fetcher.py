try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    Credentials = None
    InstalledAppFlow = None
    Request = None
    build = None
    HttpError = Exception
import os
import base64
from typing import List, Dict, Any
import pickle

from src.document_fetchers.base import BaseFetcher

class GmailFetcher(BaseFetcher):
    """Fetches documents (attachments) from Gmail based on specified criteria."""

    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.creds = None
        self.service = None
        self.auth_error = None
        try:
            self._authenticate()
        except Exception as exc:
            self.auth_error = exc

    def _authenticate(self):
        if build is None or InstalledAppFlow is None or Request is None:
            raise ImportError("Google API dependencies are required for Gmail fetching.")

        token_path = self.config.get("gmail_token_file") or self.config.get('gmail_token_path', 'token.pickle')
        credentials_path = self.config.get("gmail_credentials_file") or self.config.get('gmail_credentials_path', 'credentials.json')

        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                self.creds = pickle.load(token)
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not self._interactive_auth_enabled("gmail"):
                    raise RuntimeError(
                        "Gmail OAuth requires a valid token; interactive authorization is disabled for autonomous runs."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, self.SCOPES)
                self.creds = flow.run_local_server(port=0)
            with open(token_path, 'wb') as token:
                pickle.dump(self.creds, token)

        self.service = build('gmail', 'v1', credentials=self.creds)

    def fetch_documents(self) -> List[Dict[str, Any]]:
        self._start_run()
        if self.auth_error:
            self._fail_run(self.auth_error)
            return []

        query = self.config.get("gmail_query") or self.config.get("gmail_search_query") or "has:attachment"
        attachments_dir = self.config.get('gmail_attachment_download_dir') or self.config.get('attachments_save_dir', '/tmp/gmail_attachments')
        os.makedirs(attachments_dir, exist_ok=True)
        max_pages = _bounded_int(self.config.get("gmail_max_pages"), 50, 1, 500)
        max_messages = _bounded_int(self.config.get("gmail_max_messages"), 5000, 1, 50000)

        documents = []
        skipped = 0
        pages = 0
        try:
            page_token = None
            messages = []
            while pages < max_pages and len(messages) < max_messages:
                request = self.service.users().messages().list(
                    userId="me",
                    q=query,
                    maxResults=min(500, max_messages - len(messages)),
                    **({"pageToken": page_token} if page_token else {}),
                )
                results = request.execute()
                pages += 1
                messages.extend(results.get("messages", []))
                page_token = results.get("nextPageToken")
                if not page_token:
                    break

            for message in messages[:max_messages]:
                msg = self.service.users().messages().get(userId='me', id=message['id']).execute()
                for part in _attachment_parts(msg.get("payload") or {}):
                    if part['filename'] and part['body'] and 'attachmentId' in part['body']:
                        attachment_id = part['body']['attachmentId']
                        attachment = self.service.users().messages().attachments().get(
                            userId='me', messageId=message['id'], id=attachment_id).execute()

                        encoded = str(attachment.get("data") or "")
                        encoded += "=" * (-len(encoded) % 4)
                        file_data = base64.urlsafe_b64decode(encoded)
                        file_name = part['filename']
                        document_id = message['id'] + '_' + attachment_id
                        local_path = self._content_download_path(
                            attachments_dir,
                            file_name,
                            document_id,
                            file_data,
                        )

                        with open(local_path, 'wb') as f:
                            f.write(file_data)

                        documents.append({
                            'id': document_id,
                            'source': 'gmail',
                            'original_filename': file_name,
                            'mime_type': part.get("mimeType"),
                            'local_path': local_path,
                            'timestamp': msg['internalDate'],
                            'metadata': {
                                'subject': next((header['value'] for header in msg['payload'].get('headers', []) if header['name'] == 'Subject'), ''),
                                'from': next((header['value'] for header in msg['payload'].get('headers', []) if header['name'] == 'From'), ''),
                                'message_id': message['id'],
                                'attachment_id': attachment_id,
                            }
                        })
                    else:
                        skipped += 1
            self._finish_run(len(documents), skipped=skipped, pages=pages)
        except Exception as error:
            self._fail_run(error, fetched=len(documents), skipped=skipped, pages=pages)
        return documents


def _attachment_parts(payload: Dict[str, Any]):
    for part in payload.get("parts") or []:
        if part.get("parts"):
            yield from _attachment_parts(part)
        if part.get("filename") and isinstance(part.get("body"), dict):
            yield part


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(parsed, maximum))


