from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
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
        self._authenticate()

    def _authenticate(self):
        token_path = self.config.get('gmail_token_path', 'token.pickle')
        credentials_path = self.config.get('gmail_credentials_path', 'credentials.json')

        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                self.creds = pickle.load(token)
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, self.SCOPES)
                self.creds = flow.run_local_server(port=0)
            with open(token_path, 'wb') as token:
                pickle.dump(self.creds, token)

        self.service = build('gmail', 'v1', credentials=self.creds)

    def fetch_documents(self) -> List[Dict[str, Any]]:
        query = self.config.get('gmail_query', 'has:attachment')
        attachments_dir = self.config.get('attachments_save_dir', '/tmp/gmail_attachments')
        os.makedirs(attachments_dir, exist_ok=True)

        documents = []
        try:
            results = self.service.users().messages().list(userId='me', q=query).execute()
            messages = results.get('messages', [])

            if not messages:
                print('No messages found matching the query.')
                return []

            for message in messages:
                msg = self.service.users().messages().get(userId='me', id=message['id']).execute()
                for part in msg['payload']['parts']:
                    if part['filename'] and part['body'] and 'attachmentId' in part['body']:
                        attachment_id = part['body']['attachmentId']
                        attachment = self.service.users().messages().attachments().get(
                            userId='me', messageId=message['id'], id=attachment_id).execute()
                        
                        file_data = base64.urlsafe_b64decode(attachment['data'])
                        file_name = part['filename']
                        local_path = os.path.join(attachments_dir, file_name)
                        
                        with open(local_path, 'wb') as f:
                            f.write(file_data)
                        
                        documents.append({
                            'id': message['id'] + '_' + attachment_id,
                            'source': 'gmail',
                            'original_filename': file_name,
                            'local_path': local_path,
                            'timestamp': msg['internalDate'],
                            'metadata': {
                                'subject': next(header['value'] for header in msg['payload']['headers'] if header['name'] == 'Subject'),
                                'from': next(header['value'] for header in msg['payload']['headers'] if header['name'] == 'From')
                            }
                        })
        except HttpError as error:
            print(f'An error occurred: {error}')
        return documents


