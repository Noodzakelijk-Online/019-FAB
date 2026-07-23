import unittest

from src.document_handling.duplicate_detector import DuplicateDetector


class TestDuplicateDetector(unittest.TestCase):
    def setUp(self):
        self.detector = DuplicateDetector({})

    def test_localized_amounts_produce_same_fingerprint(self):
        european = {
            "extracted_data": {
                "vendor_name": "Vendor BV",
                "transaction_date": "2026-06-01",
                "total_amount": "EUR 1.234,56",
            }
        }
        decimal = {
            "extracted_data": {
                "vendor_name": "Vendor BV",
                "transaction_date": "2026-06-01",
                "total_amount": "1234.56",
            }
        }

        self.assertEqual(
            self.detector.build_fingerprint(european),
            self.detector.build_fingerprint(decimal),
        )

    def test_sparse_documents_with_same_filename_are_not_duplicates(self):
        result = self.detector.is_duplicate(
            {"original_filename": "receipt.pdf"},
            [{"id": "existing", "original_filename": "receipt.pdf"}],
        )

        self.assertFalse(result["is_duplicate"])

    def test_exact_accounting_fields_match_across_different_filenames(self):
        result = self.detector.is_duplicate(
            {
                "original_filename": "scan-2026.pdf",
                "extracted_data": {
                    "vendor_name": "Vendor BV",
                    "transaction_date": "2026-06-01",
                    "total_amount": "123,45",
                },
            },
            [
                {
                    "id": "existing",
                    "original_filename": "invoice.pdf",
                    "extracted_data": {
                        "vendor_name": "Vendor BV",
                        "transaction_date": "2026-06-01",
                        "total_amount": 123.45,
                    },
                }
            ],
        )

        self.assertTrue(result["is_duplicate"])
        self.assertEqual(result["reason"], "exact_fingerprint_match")

    def test_credit_note_is_not_a_duplicate_of_the_original_invoice(self):
        common = {
            "vendor_name": "Vendor BV",
            "transaction_date": "2026-06-01",
            "total_amount": 123.45,
        }
        result = self.detector.is_duplicate(
            {
                "document_type": "credit_note",
                "extracted_data": {**common, "document_type": "credit_note"},
            },
            [{
                "id": "invoice-1",
                "document_type": "vendor_invoice",
                "extracted_data": {**common, "document_type": "vendor_invoice"},
            }],
        )

        self.assertFalse(result["is_duplicate"])

    def test_invoice_number_requires_corroborating_accounting_fields(self):
        result = self.detector.is_duplicate(
            {
                "extracted_data": {
                    "vendor_name": "Vendor A",
                    "invoice_number": "123",
                    "transaction_date": "2026-06-01",
                    "total_amount": 10,
                }
            },
            [
                {
                    "id": "existing",
                    "extracted_data": {
                        "vendor_name": "Vendor B",
                        "invoice_number": "123",
                        "transaction_date": "2026-06-02",
                        "total_amount": 20,
                    },
                }
            ],
        )

        self.assertFalse(result["is_duplicate"])

    def test_common_word_invoice_reference_does_not_merge_recurring_charges(self):
        result = self.detector.is_duplicate(
            {
                "extracted_data": {
                    "vendor_name": "T-Mobile",
                    "invoice_number": "staat",
                    "transaction_date": "2023-05-19",
                    "total_amount": 37.68,
                }
            },
            [
                {
                    "id": "previous-month",
                    "extracted_data": {
                        "vendor_name": "T-Mobile",
                        "invoice_number": "staat",
                        "transaction_date": "2023-04-21",
                        "total_amount": 37.68,
                    },
                }
            ],
        )

        self.assertFalse(result["is_duplicate"])

    def test_valid_invoice_reference_can_corroborate_recurring_amount(self):
        result = self.detector.is_duplicate(
            {
                "extracted_data": {
                    "vendor_name": "Vendor BV",
                    "invoice_number": "INV-2026-0042",
                    "transaction_date": "2026-06-02",
                    "total_amount": 37.68,
                }
            },
            [
                {
                    "id": "same-invoice",
                    "extracted_data": {
                        "vendor_name": "Vendor BV",
                        "invoice_number": "INV-2026-0042",
                        "transaction_date": "2026-06-01",
                        "total_amount": 37.68,
                    },
                }
            ],
        )

        self.assertTrue(result["is_duplicate"])
        self.assertEqual(result["reason"], "exact_fingerprint_match")

    def test_missing_dates_do_not_receive_similarity_credit(self):
        score = self.detector.similarity_score(
            {"extracted_data": {"vendor_name": "Vendor A", "total_amount": 10}},
            {"extracted_data": {"vendor_name": "Vendor B", "total_amount": 20}},
        )

        self.assertLess(score, 0.5)

    def test_fuzzy_match_requires_three_comparable_fields(self):
        result = self.detector.is_duplicate(
            {
                "ocr_text": "Invoice from Acme office supplies",
                "extracted_data": {
                    "vendor_name": "Acme Supplies",
                    "transaction_date": "2026-06-01",
                    "total_amount": "100,00",
                },
            },
            [
                {
                    "id": "existing",
                    "ocr_text": "Invoice from Acme office supply",
                    "extracted_data": {
                        "vendor_name": "Acme Supply",
                        "transaction_date": "2026-06-01",
                        "total_amount": 100,
                    },
                }
            ],
        )

        self.assertTrue(result["is_duplicate"])
        self.assertEqual(result["reason"], "fuzzy_document_match")

    def test_invalid_configuration_falls_back_to_safe_defaults(self):
        detector = DuplicateDetector(
            {
                "duplicate_similarity_threshold": "invalid",
                "duplicate_amount_tolerance": -1,
            }
        )

        self.assertEqual(detector.similarity_threshold, 0.9)
        self.assertEqual(str(detector.amount_tolerance), "0.02")


if __name__ == "__main__":
    unittest.main()
