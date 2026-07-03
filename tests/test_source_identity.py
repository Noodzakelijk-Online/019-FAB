import unittest

from src.document_handling.source_identity import source_document_id


class TestSourceDocumentIdentity(unittest.TestCase):
    def test_uses_alternate_explicit_source_identifier(self):
        self.assertEqual(source_document_id({"file_id": "drive-file-1"}), "drive-file-1")

    def test_generates_stable_identity_from_file_metadata(self):
        document = {
            "local_path": "/tmp/receipt.pdf",
            "original_filename": "receipt.pdf",
            "mime_type": "application/pdf",
            "size": 1234,
        }

        first = source_document_id(document)
        second = source_document_id(dict(reversed(list(document.items()))))

        self.assertIsNotNone(first)
        self.assertTrue(first.startswith("generated:"))
        self.assertEqual(first, second)

    def test_different_file_metadata_produces_different_identity(self):
        first = source_document_id({"local_path": "/tmp/receipt-1.pdf"})
        second = source_document_id({"local_path": "/tmp/receipt-2.pdf"})

        self.assertNotEqual(first, second)

    def test_long_explicit_identity_is_bounded_for_database_storage(self):
        identity = source_document_id({"id": "x" * 300})

        self.assertTrue(identity.startswith("sha256:"))
        self.assertLessEqual(len(identity), 255)

    def test_returns_none_without_identity_fields(self):
        self.assertIsNone(source_document_id({}))


if __name__ == "__main__":
    unittest.main()
