import unittest
from unittest.mock import MagicMock, patch
import os

from src.document_fetchers.gmail_fetcher import GmailFetcher
from src.document_fetchers.drive_fetcher import DriveFetcher
from src.document_fetchers.freshdesk_fetcher import FreshdeskFetcher
from src.document_fetchers.photos_fetcher import PhotosFetcher

class TestDocumentFetchers(unittest.TestCase):

    def setUp(self):
        self.config = {
            "gmail_credentials_file": "/tmp/gmail_credentials.json",
            "gmail_token_file": "/tmp/gmail_token.json",
            "gmail_attachment_download_dir": "/tmp/gmail_downloads",
            "google_drive_credentials_file": "/tmp/drive_credentials.json",
            "google_drive_token_file": "/tmp/drive_token.json",
            "google_drive_download_dir": "/tmp/drive_downloads",
            "freshdesk_api_key": "test_api_key",
            "freshdesk_domain": "test_domain",
            "freshdesk_download_dir": "/tmp/freshdesk_downloads",
            "google_photos_credentials_file": "/tmp/photos_credentials.json",
            "google_photos_token_file": "/tmp/photos_token.json",
            "google_photos_album_name": "Test Album",
            "google_photos_download_dir": "/tmp/photos_downloads"
        }
        # Create dummy credential and token files for all fetchers
        for key in ["gmail", "google_drive", "google_photos"]:
            with open(self.config[f"{key}_credentials_file"], "w") as f:
                f.write("{}")
            with open(self.config[f"{key}_token_file"], "w") as f:
                f.write("{}")
        
        # Create download directories
        for key in ["gmail", "google_drive", "freshdesk", "google_photos"]:
            os.makedirs(self.config[f"{key}_download_dir"], exist_ok=True)

    @patch("src.document_fetchers.gmail_fetcher.build")
    @patch("src.document_fetchers.gmail_fetcher.InstalledAppFlow")
    @patch("src.document_fetchers.gmail_fetcher.os.path.exists")
    @patch("src.document_fetchers.gmail_fetcher.pickle")
    def test_gmail_fetcher(self, mock_pickle, mock_exists, mock_InstalledAppFlow, mock_build):
        mock_exists.return_value = True
        mock_pickle.load.return_value = MagicMock()
        
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        # Mock Gmail API calls
        mock_service.users.return_value.messages.return_value.list.return_value.execute.return_value = {"messages": [{"id": "msg1"}]}
        mock_service.users.return_value.messages.return_value.get.return_value.execute.return_value = {
            "payload": {
                "parts": [
                    {"filename": "test.pdf", "body": {"attachmentId": "att1"}, "mimeType": "application/pdf"}
                ]
            }
        }
        mock_service.users.return_value.messages.return_value.attachments.return_value.get.return_value.execute.return_value = {"data": "JVBERi0xLjQKJcOkw7zXCl..."}

        fetcher = GmailFetcher(self.config)
        documents = fetcher.fetch_documents()
        self.assertEqual(len(documents), 1)
        self.assertTrue(documents[0]["original_filename"].endswith(".pdf"))
        self.assertTrue(os.path.exists(documents[0]["local_path"]))
        os.remove(documents[0]["local_path"])

    @patch("src.document_fetchers.drive_fetcher.build")
    @patch("src.document_fetchers.drive_fetcher.InstalledAppFlow")
    @patch("src.document_fetchers.drive_fetcher.os.path.exists")
    @patch("src.document_fetchers.drive_fetcher.pickle")
    def test_drive_fetcher(self, mock_pickle, mock_exists, mock_InstalledAppFlow, mock_build):
        mock_exists.return_value = True
        mock_pickle.load.return_value = MagicMock()

        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock Drive API calls
        mock_service.files.return_value.list.return_value.execute.return_value = {
            "files": [
                {"id": "file1", "name": "document.jpg", "mimeType": "image/jpeg"}
            ]
        }
        mock_service.files.return_value.get_media.return_value.execute.return_value = b"dummy_image_content"

        fetcher = DriveFetcher(self.config)
        documents = fetcher.fetch_documents()
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0]["original_filename"], "document.jpg")
        self.assertTrue(os.path.exists(documents[0]["local_path"]))
        os.remove(documents[0]["local_path"])

    @patch("src.document_fetchers.freshdesk_fetcher.requests.get")
    def test_freshdesk_fetcher(self, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tickets": [
                {"id": 1, "attachments": [{"id": 101, "name": "report.pdf", "attachment_url": "http://example.com/report.pdf"}]}
            ]
        }
        mock_requests_get.side_effect = [mock_response, MagicMock(content=b"dummy_pdf_content")]

        fetcher = FreshdeskFetcher(self.config)
        documents = fetcher.fetch_documents()
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0]["original_filename"], "report.pdf")
        self.assertTrue(os.path.exists(documents[0]["local_path"]))
        os.remove(documents[0]["local_path"])

    @patch("src.document_fetchers.photos_fetcher.build")
    @patch("src.document_fetchers.photos_fetcher.InstalledAppFlow")
    @patch("src.document_fetchers.photos_fetcher.os.path.exists")
    @patch("src.document_fetchers.photos_fetcher.pickle")
    @patch("src.document_fetchers.photos_fetcher.requests.get")
    def test_photos_fetcher(self, mock_requests_get, mock_pickle, mock_exists, mock_InstalledAppFlow, mock_build):
        mock_exists.return_value = True
        mock_pickle.load.return_value = MagicMock()
        
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.albums.return_value.list.return_value.execute.return_value = {
            "albums": [{
                "id": "album123",
                "title": "Test Album"
            }]
        }

        mock_service.mediaItems.return_value.search.return_value.execute.return_value = {
            "mediaItems": [
                {"id": "photo1", "filename": "receipt.jpg", "mimeType": "image/jpeg", "baseUrl": "http://example.com/receipt.jpg"}
            ]
        }

        mock_response = MagicMock()
        mock_response.content = b"dummy_image_content"
        mock_requests_get.return_value = mock_response

        fetcher = PhotosFetcher(self.config)
        documents = fetcher.fetch_documents()
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0]["original_filename"], "receipt.jpg")
        self.assertTrue(os.path.exists(documents[0]["local_path"]))
        os.remove(documents[0]["local_path"])

    def tearDown(self):
        # Clean up dummy files and directories
        for key in ["gmail", "google_drive", "google_photos"]:
            if os.path.exists(self.config[f"{key}_credentials_file"]):
                os.remove(self.config[f"{key}_credentials_file"])
            if os.path.exists(self.config[f"{key}_token_file"]):
                os.remove(self.config[f"{key}_token_file"])
        
        for key in ["gmail", "google_drive", "freshdesk", "google_photos"]:
            if os.path.exists(self.config[f"{key}_download_dir"]):
                shutil.rmtree(self.config[f"{key}_download_dir}"])

if __name__ == "__main__":
    unittest.main()


