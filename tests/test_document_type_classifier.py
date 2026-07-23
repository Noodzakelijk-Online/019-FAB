import unittest

from src.document_processors.document_type_classifier import (
    DocumentTypeClassifier,
    is_non_posting_document_type,
)
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

    def test_credit_note_is_posting_eligible_but_requires_review(self):
        result = self.classifier.classify(
            "CREDITNOTA\nLeverancier BV\nTotaal EUR 42,50",
            {"credit_note_number": "CN-0042"},
        )

        self.assertEqual(result["documentType"], "credit_note")
        self.assertTrue(result["postingEligible"])
        self.assertTrue(result["reviewRequired"])
        self.assertFalse(is_non_posting_document_type(result["documentType"]))
        self.assertEqual(
            resolve_wave_action_for_document({"document_type": result["documentType"]}),
            "transaction_add",
        )

    def test_dutch_refund_receipt_is_a_review_gated_credit_note(self):
        result = self.classifier.classify(
            "Praxis\nTERUGBETALING\nTerug (Vpay) 25,00",
            {},
        )

        self.assertEqual(result["documentType"], "credit_note")
        self.assertTrue(result["postingEligible"])
        self.assertTrue(result["reviewRequired"])
        self.assertFalse(is_non_posting_document_type(result["documentType"]))

    def test_unrecognized_document_remains_unknown(self):
        result = self.classifier.classify("General correspondence", {})

        self.assertEqual(result["documentType"], "unknown")
        self.assertEqual(result["confidenceScore"], 0.0)

    def test_insurance_policy_is_non_posting_supporting_evidence(self):
        result = self.classifier.classify(
            "Polisblad motorrijtuigenverzekering\nPolisnummer 12345",
            {},
        )

        self.assertEqual(result["documentType"], "insurance_policy")
        self.assertFalse(result["postingEligible"])
        self.assertTrue(result["reviewRequired"])
        self.assertTrue(is_non_posting_document_type(result["documentType"]))
        self.assertEqual(result["classifier"], "deterministic_financial_document_type_v6")

    def test_government_benefits_letter_is_non_posting_supporting_evidence(self):
        result = self.classifier.classify(
            "Besluit op grond van de Participatiewet\nDe bijstandsnorm wordt aangepast.",
            {},
        )

        self.assertEqual(result["documentType"], "government_correspondence")
        self.assertFalse(result["postingEligible"])
        self.assertTrue(result["reviewRequired"])

    def test_specific_dutch_government_evidence_is_non_posting(self):
        examples = (
            "uwv Betaalspecificatie\nWajong Uitkering 01-06-2023 t/m 30-06-2023",
            "Melding aan IND: Vragenlijst",
            "Verwerking opgaaf/wijziging rekeningnummer voor uitbetalingen toeslagen",
            "Alle raadsvergaderingen zijn openbaar. Volg de Arnhemse gemeenteraad.",
            "Uw bezwaarschrift tegen het besluit inzake toekenning bijstand is ontvangen.",
            "Belastingdienst Aanslag inkomstenbelasting\nTe betalen EUR 0,00",
        )

        for text in examples:
            with self.subTest(text=text):
                result = self.classifier.classify(text, {})
                self.assertEqual(result["documentType"], "government_correspondence")
                self.assertFalse(result["postingEligible"])
                self.assertTrue(result["reviewRequired"])

    def test_payable_tax_assessment_is_not_silently_made_non_posting(self):
        result = self.classifier.classify(
            "Belastingdienst Aanslag inkomstenbelasting\nTe betalen EUR 125,00",
            {},
        )

        self.assertEqual(result["documentType"], "unknown")
        self.assertFalse(result["postingEligible"])
        self.assertFalse(result["reviewRequired"])

    def test_municipal_invoice_remains_a_vendor_invoice(self):
        result = self.classifier.classify(
            "Gemeente Arnhem\nFactuur afvalstoffen\nTe betalen EUR 125,00",
            {"invoice_number": "GEM-42"},
        )

        self.assertEqual(result["documentType"], "vendor_invoice")
        self.assertTrue(result["postingEligible"])

    def test_invoice_with_policy_number_remains_an_invoice(self):
        result = self.classifier.classify(
            "Factuur verzekeringspremie\nPolisnummer 12345\nTe betalen EUR 125,40",
            {"invoice_number": "INV-42"},
        )

        self.assertEqual(result["documentType"], "vendor_invoice")
        self.assertTrue(result["postingEligible"])

    def test_negative_receivable_total_is_a_credit_note(self):
        result = self.classifier.classify(
            "Factuur\nUw verzekering is beëindigd\nTotaal te ontvangen EUR\n-7,20",
            {"total_amount": -7.2},
        )

        self.assertEqual(result["documentType"], "credit_note")
        self.assertGreaterEqual(result["confidenceScore"], 0.98)
        self.assertIn("field:negative_total_amount", result["evidence"])

    def test_negative_amount_without_refund_semantics_is_not_a_credit_note(self):
        result = self.classifier.classify(
            "Factuur\nCorrectieboekingsregel -7,20",
            {"total_amount": -7.2},
        )

        self.assertEqual(result["documentType"], "vendor_invoice")


if __name__ == "__main__":
    unittest.main()
