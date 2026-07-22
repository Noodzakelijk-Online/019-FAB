import unittest

from src.document_processors.document_type_classifier import DocumentTypeClassifier
from src.data_entry.waveapps_surface import resolve_wave_action_for_document


class TestDocumentTypeClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = DocumentTypeClassifier()

    def test_invoice_reference_routes_as_vendor_invoice(self):
        result = self.classifier.classify(
            "FACTUUR\nTe betalen EUR 42,50",
            {"invoice_number": "INV-2026-0042"},
        )

        self.assertEqual(result["documentType"], "vendor_invoice")
        self.assertTrue(result["postingEligible"])
        self.assertFalse(result["reviewRequired"])
        self.assertEqual(result["evidencePriority"], 100)
        self.assertEqual(
            resolve_wave_action_for_document({"document_type": result["documentType"]}),
            "bill_create",
        )

    def test_order_confirmation_is_review_only_even_when_it_mentions_invoice(self):
        result = self.classifier.classify(
            "Order confirmation. Your invoice will be sent separately.",
            {},
        )

        self.assertEqual(result["documentType"], "order_confirmation")
        self.assertFalse(result["postingEligible"])
        self.assertTrue(result["reviewRequired"])

    def test_legacy_scanner_receipt_term_is_supported(self):
        result = self.classifier.classify("Ontvangstbewijs\nTotaal EUR 12,00", {})

        self.assertEqual(result["documentType"], "receipt")
        self.assertTrue(result["postingEligible"])

    def test_unrecognized_document_remains_unknown(self):
        result = self.classifier.classify("General correspondence", {})

        self.assertEqual(result["documentType"], "unknown")
        self.assertEqual(result["confidenceScore"], 0.0)


if __name__ == "__main__":
    unittest.main()
