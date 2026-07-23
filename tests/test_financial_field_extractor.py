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
        Totaal \u20ac 4,28
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

    def test_extracts_split_stripe_receipt_fields(self):
        text = """
        Receipt from BrainForce Co.
        US$29.00
        Paid on October 13, 2023
        Total
        Amount paid
        US$29.00
        US$29.00
        """

        result = FinancialFieldExtractor().extract(text)
        data = result["extracted_data"]

        self.assertEqual(data["vendor_name"], "BrainForce Co.")
        self.assertEqual(data["transaction_date"], "2023-10-13")
        self.assertEqual(data["total_amount"], 29.0)
        self.assertEqual(data["currency"], "USD")
        self.assertGreaterEqual(result["field_confidences"]["total_amount"], 0.85)

    def test_extracts_dutch_invoice_sentence(self):
        text = """
        T
        Je nieuwe factuur staat klaar in My T-Mobile
        Het factuurbedrag is \u20ac 25,01.
        Het bedrag van \u20ac 25,01 wordt rond 12 augustus 2023 van je rekening afgeschreven.
        Vriendelijke groeten,
        T-Mobile
        """

        result = FinancialFieldExtractor().extract(text)
        data = result["extracted_data"]

        self.assertEqual(data["vendor_name"], "T-Mobile")
        self.assertEqual(data["transaction_date"], "2023-08-12")
        self.assertEqual(data["total_amount"], 25.01)
        self.assertEqual(data["currency"], "EUR")

    def test_extracts_slack_paid_total_and_vat(self):
        text = """
        slack
        5/14/23 - 6/13/23
        \u20ac8.25 x 2 members x 1 month \u20ac16.50
        VAT (21.0%) \u20ac3.47
        Paid today \u20ac19.97
        """

        result = FinancialFieldExtractor().extract(text)
        data = result["extracted_data"]

        self.assertEqual(data["vendor_name"], "Slack")
        self.assertEqual(data["transaction_date"], "2023-05-14")
        self.assertEqual(data["total_amount"], 19.97)
        self.assertEqual(data["vat_amount"], 3.47)

    def test_total_savings_never_outranks_payable_total(self):
        result = FinancialFieldExtractor().extract(
            "Lidl Arnhem\nTotaal: 12,02 EUR\nTotaal prijsvoordeel 1,03"
        )

        self.assertEqual(result["extracted_data"]["total_amount"], 12.02)
        self.assertGreaterEqual(result["field_confidences"]["total_amount"], 0.9)


if __name__ == "__main__":
    unittest.main()
