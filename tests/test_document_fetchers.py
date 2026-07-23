import unittest
from unittest.mock import MagicMock, patch
import base64
import os
import shutil
import tempfile

from src.document_fetchers.gmail_fetcher import GmailFetcher
from src.document_fetchers.drive_fetcher import DriveFetcher
from src.document_fetchers.freshdesk_fetcher import FreshdeskFetcher
from src.document_fetchers.photos_fetcher import PhotosFetcher

class TestDocumentFetchers(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.config = {
            "gmail_credentials_file": os.path.join(self.temp_dir.name, "gmail_credentials.json"),
            "gmail_token_file": os.path.join(self.temp_dir.name, "gmail_token.json"),
            "gmail_attachment_download_dir": os.path.join(self.temp_dir.name, "gmail_downloads"),
            "google_drive_credentials_file": os.path.join(self.temp_dir.name, "drive_credentials.json"),
            "google_drive_token_file": os.path.join(self.temp_dir.name, "drive_token.json"),
            "google_drive_download_dir": os.path.join(self.temp_dir.name, "drive_downloads"),
            "google_drive_folder_id": "sort-out-folder",
            "freshdesk_api_key": "test_api_key",
            "freshdesk_domain": "test_domain",
            "freshdesk_download_dir": os.path.join(self.temp_dir.name, "freshdesk_downloads"),
            "google_photos_credentials_file": os.path.join(self.temp_dir.name, "photos_credentials.json"),
            "google_photos_token_file": os.path.join(self.temp_dir.name, "photos_token.json"),
            "google_photos_album_name": "Test Album",
            "google_photos_download_dir": os.path.join(self.temp_dir.name, "photos_downloads")
        }
        # Create dummy credential and token files for all fetchers
        for key in ["gmail", "google_drive", "google_photos"]:
            with open(self.config[f"{key}_credentials_file"], "w") as f:
                f.write("{}")
            with open(self.config[f"{key}_token_file"], "w") as f:
                f.write("{}")
        
        # Create download directories
        for key in [
            "gmail_attachment_download_dir",
            "google_drive_download_dir",
            "freshdesk_download_dir",
            "google_photos_download_dir",
        ]:
            os.makedirs(self.config[key], exist_ok=True)

    @patch("src.document_fetchers.gmail_fetcher.build")
    @patch("src.document_fetchers.gmail_fetcher.InstalledAppFlow")
    @patch("src.document_fetchers.gmail_fetcher.Request")
    @patch("src.document_fetchers.gmail_fetcher.os.path.exists")
    @patch("src.document_fetchers.gmail_fetcher.pickle")
    def test_gmail_fetcher(self, mock_pickle, mock_exists, mock_Request, mock_InstalledAppFlow, mock_build):
        mock_exists.return_value = True
        mock_pickle.load.return_value = MagicMock()
        
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        # Mock Gmail API calls
        mock_service.users.return_value.messages.return_value.list.return_value.execute.return_value = {"messages": [{"id": "msg1"}]}
        mock_service.users.return_value.messages.return_value.get.return_value.execute.return_value = {
            "internalDate": "1735689600000",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Receipt"},
                    {"name": "From", "value": "vendor@example.com"},
                ],
                "parts": [
                    {"filename": "test.pdf", "body": {"attachmentId": "att1"}, "mimeType": "application/pdf"}
                ]
            }
        }
        mock_service.users.return_value.messages.return_value.attachments.return_value.get.return_value.execute.return_value = {"data": "JVBERi0xLjQK"}

        fetcher = GmailFetcher(self.config)
        documents = fetcher.fetch_documents()
        self.assertEqual(len(documents), 1)
        self.assertTrue(documents[0]["original_filename"].endswith(".pdf"))
        self.assertTrue(os.path.exists(documents[0]["local_path"]))
        os.remove(documents[0]["local_path"])

    @patch("src.document_fetchers.gmail_fetcher.build")
    @patch("src.document_fetchers.gmail_fetcher.InstalledAppFlow")
    @patch("src.document_fetchers.gmail_fetcher.Request")
    @patch("src.document_fetchers.gmail_fetcher.os.path.exists")
    @patch("src.document_fetchers.gmail_fetcher.pickle")
    def test_gmail_fetcher_follows_next_page_token(
        self,
        mock_pickle,
        mock_exists,
        mock_Request,
        mock_InstalledAppFlow,
        mock_build,
    ):
        mock_exists.return_value = True
        mock_pickle.load.return_value = MagicMock()
        service = MagicMock()
        mock_build.return_value = service
        service.users.return_value.messages.return_value.list.return_value.execute.side_effect = [
            {"messages": [{"id": "msg1"}], "nextPageToken": "page-2"},
            {"messages": [{"id": "msg2"}]},
        ]
        service.users.return_value.messages.return_value.get.return_value.execute.side_effect = [
            _gmail_message("att1", "one.pdf"),
            _gmail_message("att2", "two.pdf"),
        ]
        service.users.return_value.messages.return_value.attachments.return_value.get.return_value.execute.side_effect = [
            {"data": "JVBERi0xLjQK"},
            {"data": "JVBERi0xLjUK"},
        ]

        fetcher = GmailFetcher(self.config)
        documents = fetcher.fetch_documents()

        self.assertEqual(len(documents), 2)
        self.assertEqual(fetcher.last_run["pages"], 2)
        self.assertEqual(service.users.return_value.messages.return_value.list.call_count, 2)
        for document in documents:
            os.remove(document["local_path"])

    @patch("src.document_fetchers.gmail_fetcher.build")
    @patch("src.document_fetchers.gmail_fetcher.InstalledAppFlow")
    @patch("src.document_fetchers.gmail_fetcher.Request")
    @patch("src.document_fetchers.gmail_fetcher.os.path.exists")
    @patch("src.document_fetchers.gmail_fetcher.pickle")
    def test_gmail_scanner_profile_rejects_untrusted_and_invalid_pdf_attachments(
        self,
        mock_pickle,
        mock_exists,
        mock_Request,
        mock_InstalledAppFlow,
        mock_build,
    ):
        mock_exists.return_value = True
        mock_pickle.load.return_value = MagicMock()
        service = MagicMock()
        mock_build.return_value = service
        service.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": [{"id": "valid"}, {"id": "spoofed"}, {"id": "fake-pdf"}],
        }
        service.users.return_value.messages.return_value.get.return_value.execute.side_effect = [
            _gmail_message("att-valid", "scan.pdf", sender="HP ePrint <eprintcenter@hp8.us>"),
            _gmail_message("att-spoofed", "scan.pdf", sender="Attacker <other@example.com>"),
            _gmail_message("att-fake", "scan.pdf", sender="eprintcenter@hp8.us"),
        ]
        service.users.return_value.messages.return_value.attachments.return_value.get.return_value.execute.side_effect = [
            {"data": base64.urlsafe_b64encode(b"%PDF-1.7\nscanner").decode("ascii")},
            {"data": base64.urlsafe_b64encode(b"not actually a pdf").decode("ascii")},
        ]
        config = {
            **self.config,
            "gmail_scanner_mode": True,
            "gmail_trusted_senders": "eprintcenter@hp8.us",
            "gmail_query": "label:all from:eprintcenter@hp8.us has:attachment filename:pdf",
        }

        fetcher = GmailFetcher(config)
        documents = fetcher.fetch_documents()

        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0]["metadata"]["sender_address"], "eprintcenter@hp8.us")
        self.assertTrue(documents[0]["metadata"]["scanner_policy_verified"])
        self.assertEqual(documents[0]["metadata"]["scanner_profile"], "hp_eprint_v1")
        self.assertEqual(
            documents[0]["metadata"]["delivery_path"],
            "gmail_to_fab_direct",
        )
        self.assertEqual(documents[0]["mime_type"], "application/pdf")
        self.assertEqual(fetcher.last_run["rejected"]["untrusted_sender"], 1)
        self.assertEqual(fetcher.last_run["rejected"]["invalid_pdf"], 1)
        list_kwargs = service.users.return_value.messages.return_value.list.call_args.kwargs
        self.assertEqual(list_kwargs["q"], config["gmail_query"])
        os.remove(documents[0]["local_path"])

    @patch("src.document_fetchers.gmail_fetcher.build")
    @patch("src.document_fetchers.gmail_fetcher.InstalledAppFlow")
    @patch("src.document_fetchers.gmail_fetcher.Request")
    @patch("src.document_fetchers.gmail_fetcher.os.path.exists")
    @patch("src.document_fetchers.gmail_fetcher.pickle")
    def test_gmail_fetcher_marks_capped_history_partial_and_uses_incremental_checkpoint(
        self,
        mock_pickle,
        mock_exists,
        mock_Request,
        mock_InstalledAppFlow,
        mock_build,
    ):
        mock_exists.return_value = True
        mock_pickle.load.return_value = MagicMock()
        service = MagicMock()
        mock_build.return_value = service
        service.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": [{"id": "msg1"}],
            "nextPageToken": "more-history",
        }
        service.users.return_value.messages.return_value.get.return_value.execute.return_value = _gmail_message(
            "att1", "scan.pdf"
        )
        service.users.return_value.messages.return_value.attachments.return_value.get.return_value.execute.return_value = {
            "data": base64.urlsafe_b64encode(b"%PDF-1.7\nscanner").decode("ascii"),
        }
        config = {
            **self.config,
            "gmail_max_messages": 1,
            "gmail_incremental_after_epoch": 1_700_000_000,
        }

        fetcher = GmailFetcher(config)
        documents = fetcher.fetch_documents()

        self.assertEqual(len(documents), 1)
        self.assertEqual(fetcher.last_run["status"], "partial")
        self.assertTrue(fetcher.last_run["truncated"])
        query = service.users.return_value.messages.return_value.list.call_args.kwargs["q"]
        self.assertEqual(query, "has:attachment after:1700000000")
        os.remove(documents[0]["local_path"])

    @patch("src.document_fetchers.drive_fetcher.build")
    @patch("src.document_fetchers.drive_fetcher.InstalledAppFlow")
    @patch("src.document_fetchers.drive_fetcher.MediaIoBaseDownload")
    @patch("src.document_fetchers.drive_fetcher.Request")
    @patch("src.document_fetchers.drive_fetcher.os.path.exists")
    @patch("src.document_fetchers.drive_fetcher.pickle")
    def test_drive_fetcher(self, mock_pickle, mock_exists, mock_Request, mock_MediaIoBaseDownload, mock_InstalledAppFlow, mock_build):
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
        downloader = MagicMock()
        downloader.next_chunk.return_value = (None, True)
        mock_MediaIoBaseDownload.return_value = downloader

        fetcher = DriveFetcher(self.config)
        documents = fetcher.fetch_documents()
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0]["original_filename"], "document.jpg")
        self.assertTrue(os.path.exists(documents[0]["local_path"]))
        os.remove(documents[0]["local_path"])

    @patch("src.document_fetchers.drive_fetcher.build")
    @patch("src.document_fetchers.drive_fetcher.InstalledAppFlow")
    @patch("src.document_fetchers.drive_fetcher.MediaIoBaseDownload")
    @patch("src.document_fetchers.drive_fetcher.Request")
    @patch("src.document_fetchers.drive_fetcher.os.path.exists")
    @patch("src.document_fetchers.drive_fetcher.pickle")
    def test_drive_fetcher_follows_next_page_token(
        self,
        mock_pickle,
        mock_exists,
        mock_Request,
        mock_MediaIoBaseDownload,
        mock_InstalledAppFlow,
        mock_build,
    ):
        mock_exists.return_value = True
        mock_pickle.load.return_value = MagicMock()
        service = MagicMock()
        mock_build.return_value = service
        service.files.return_value.list.return_value.execute.side_effect = [
            {
                "files": [{"id": "file1", "name": "one.pdf", "mimeType": "application/pdf"}],
                "nextPageToken": "page-2",
            },
            {"files": [{"id": "file2", "name": "two.pdf", "mimeType": "application/pdf"}]},
        ]
        downloader = MagicMock()
        downloader.next_chunk.return_value = (None, True)
        mock_MediaIoBaseDownload.return_value = downloader

        fetcher = DriveFetcher(self.config)
        documents = fetcher.fetch_documents()

        self.assertEqual(len(documents), 2)
        self.assertEqual(fetcher.last_run["pages"], 2)
        self.assertEqual(service.files.return_value.list.call_count, 2)
        for document in documents:
            os.remove(document["local_path"])

    @patch("src.document_fetchers.freshdesk_fetcher.requests.get")
    def test_freshdesk_fetcher(self, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tickets": [
                {"id": 1, "attachments": [{"id": 101, "name": "report.pdf", "attachment_url": "http://example.com/report.pdf"}]}
            ]
        }
        conversations_response = MagicMock()
        conversations_response.json.return_value = []
        attachment_response = MagicMock(content=b"dummy_pdf_content")
        mock_requests_get.side_effect = [mock_response, conversations_response, attachment_response]

        fetcher = FreshdeskFetcher(self.config)
        documents = fetcher.fetch_documents()
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0]["original_filename"], "report.pdf")
        self.assertTrue(os.path.exists(documents[0]["local_path"]))
        os.remove(documents[0]["local_path"])

    @patch("src.document_fetchers.photos_fetcher.build")
    @patch("src.document_fetchers.photos_fetcher.InstalledAppFlow")
    @patch("src.document_fetchers.photos_fetcher.Request")
    @patch("src.document_fetchers.photos_fetcher.os.path.exists")
    @patch("src.document_fetchers.photos_fetcher.pickle")
    @patch("src.document_fetchers.photos_fetcher.requests.get")
    def test_photos_fetcher(self, mock_requests_get, mock_pickle, mock_exists, mock_Request, mock_InstalledAppFlow, mock_build):
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
        mock_response.raise_for_status.return_value = None
        mock_response.iter_content.return_value = [b"dummy_image_content"]
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
        
        for key in [
            "gmail_attachment_download_dir",
            "google_drive_download_dir",
            "freshdesk_download_dir",
            "google_photos_download_dir",
        ]:
            if os.path.exists(self.config[key]):
                shutil.rmtree(self.config[key])

def _gmail_message(attachment_id, filename, sender="vendor@example.com"):
    return {
        "internalDate": "1735689600000",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Scanner document"},
                {"name": "From", "value": sender},
            ],
            "parts": [{
                "filename": filename,
                "body": {"attachmentId": attachment_id},
                "mimeType": "application/pdf",
            }],
        },
    }


if __name__ == "__main__":
    unittest.main()


