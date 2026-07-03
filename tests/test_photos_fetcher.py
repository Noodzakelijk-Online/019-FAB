import unittest
from unittest.mock import MagicMock, patch
import os
import shutil
import tempfile

from src.document_fetchers.photos_fetcher import PhotosFetcher

class TestPhotosFetcher(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.config = {
            "google_photos_credentials_file": os.path.join(self.temp_dir.name, "photos_credentials.json"),
            "google_photos_token_file": os.path.join(self.temp_dir.name, "photos_token.json"),
            "google_photos_album_name": "Bookkeeping Receipts",
            "google_photos_download_dir": os.path.join(self.temp_dir.name, "photos_downloads")
        }
        # Create dummy credential and token files for testing
        with open(self.config["google_photos_credentials_file"], "w") as f:
            f.write("{}")
        with open(self.config["google_photos_token_file"], "w") as f:
            f.write("{}")
        os.makedirs(self.config["google_photos_download_dir"], exist_ok=True)

    @patch("src.document_fetchers.photos_fetcher.InstalledAppFlow")
    @patch("src.document_fetchers.photos_fetcher.build")
    @patch("src.document_fetchers.photos_fetcher.Request")
    @patch("src.document_fetchers.photos_fetcher.os.path.exists")
    @patch("src.document_fetchers.photos_fetcher.pickle")
    def test_fetch_documents(self, mock_pickle, mock_exists, mock_Request, mock_build, mock_InstalledAppFlow):
        mock_exists.return_value = True
        mock_pickle.load.return_value = MagicMock()
        
        # Mock the Google Photos API service
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock albums.list to return a specific album
        mock_service.albums.return_value.list.return_value.execute.return_value = {
            "albums": [{
                "id": "album123",
                "title": "Bookkeeping Receipts"
            }]
        }

        # Mock mediaItems.search to return some media items
        mock_service.mediaItems.return_value.search.return_value.execute.return_value = {
            "mediaItems": [
                {"id": "photo1", "filename": "receipt1.jpg", "mimeType": "image/jpeg", "baseUrl": "http://example.com/photo1"},
                {"id": "photo2", "filename": "invoice.png", "mimeType": "image/png", "baseUrl": "http://example.com/photo2"}
            ]
        }

        # Mock requests.get for downloading files
        with patch("src.document_fetchers.photos_fetcher.requests.get") as mock_requests_get:
            mock_response = MagicMock()
            mock_response.content = b"dummy_image_content"
            mock_response.raise_for_status.return_value = None
            mock_response.iter_content.return_value = [b"dummy_image_content"]
            mock_requests_get.return_value = mock_response

            fetcher = PhotosFetcher(self.config)
            documents = fetcher.fetch_documents()

            self.assertEqual(len(documents), 2)
            self.assertEqual(documents[0]["original_filename"], "receipt1.jpg")
            self.assertTrue(os.path.exists(documents[0]["local_path"]))
            self.assertEqual(documents[1]["original_filename"], "invoice.png")
            self.assertTrue(os.path.exists(documents[1]["local_path"]))

            # Clean up downloaded files
            for doc in documents:
                os.remove(doc["local_path"])

    def tearDown(self):
        # Clean up dummy files and directories
        if os.path.exists(self.config["google_photos_credentials_file"]):
            os.remove(self.config["google_photos_credentials_file"])
        if os.path.exists(self.config["google_photos_token_file"]):
            os.remove(self.config["google_photos_token_file"])
        if os.path.exists(self.config["google_photos_download_dir"]):
            shutil.rmtree(self.config["google_photos_download_dir"])

if __name__ == "__main__":
    unittest.main()


