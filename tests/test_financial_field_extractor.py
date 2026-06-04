import unittest

from src.document_processors.financial_field_extractor import FinancialFieldExtractor


class TestFinancialFieldExtractor(unittest.TestCase):
    def test_extracts_core_receipt_fields(self):
        text = """
        Albert Heijn XL
        Kassabon 12345
        Datum: 05-06-2026
        Melk 2.49
        Brood 1.79
        BTW 0.27
        Totaal € 4,28
        """
        result = FinancialFieldExtractor().extract(text)
        data = result["extracted_data"]
        confidences = result["field_confidences"]

        self.assertEqual(data["vendor_name"], "Albert Heijn XL")
        self.assertEqual(data["transaction_date"], "2026-06-05")
        self.assertEqual(data["total_amount"], 4.28)
        self.assertEqual(data["currency"], "EUR")
        self.assertEqual(data["vat_amount"], 0.27)
        self.assertGreaterEqual(confidences["total_amount"], 0.9)
        self.assertEqual(len(data["line_items"]), 2)

    def test_handles_missing_fields_with_low_confidence(self):
        result = FinancialFieldExtractor().extract("unreadable text")
        data = result["extracted_data"]
        confidences = result["field_confidences"]

        self.assertIsNone(data["transaction_date"])
        self.assertIsNone(data["total_amount"])
        self.assertEqual(confidences["transaction_date"], 0.0)
        self.assertEqual(confidences["total_amount"], 0.0)


if __name__ == "__main__":
    unittest.main()
