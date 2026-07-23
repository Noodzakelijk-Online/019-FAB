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

    def test_vendor_fallback_still_scans_beyond_the_strong_header_window(self):
        text = "\n".join([
            "Invoice",
            "Factuur",
            "Receipt",
            "Kassabon",
            "Totaal 12,00",
            "12-07-2023",
            "Readable Vendor BV",
        ])

        result = FinancialFieldExtractor().extract(text)

        self.assertEqual(result["extracted_data"]["vendor_name"], "Readable Vendor BV")
        self.assertEqual(result["field_confidences"]["vendor_name"], 0.65)
        self.assertEqual(
            result["field_evidence"]["vendor_name"]["source"],
            "first_non_noise_header_line",
        )

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

    def test_btw_registration_number_is_not_a_vat_amount(self):
        result = FinancialFieldExtractor().extract(
            "Hornbach\nBTW-nummer: NL8075.08.093.B.01\nTotaal EUR 59,60"
        )

        self.assertEqual(result["extracted_data"]["total_amount"], 59.6)
        self.assertIsNone(result["extracted_data"]["vat_amount"])
        self.assertEqual(result["field_confidences"]["vat_amount"], 0.0)

    def test_vat_table_uses_plausible_tax_not_percentage_or_gross_total(self):
        result = FinancialFieldExtractor().extract(
            "Shop\nBTW 21,00 %: 1,12, totaal BTW: 5,36\nTotaal EUR 6,48"
        )

        self.assertEqual(result["extracted_data"]["vat_amount"], 1.12)

    def test_impossible_vat_is_not_extracted(self):
        result = FinancialFieldExtractor().extract(
            "Shop\nBTW EUR 50,00\nTotaal EUR 50,00"
        )

        self.assertIsNone(result["extracted_data"]["vat_amount"])

    def test_total_savings_never_outranks_payable_total(self):
        result = FinancialFieldExtractor().extract(
            "Lidl Arnhem\nTotaal: 12,02 EUR\nTotaal prijsvoordeel 1,03"
        )

        self.assertEqual(result["extracted_data"]["total_amount"], 12.02)
        self.assertGreaterEqual(result["field_confidences"]["total_amount"], 0.9)

    def test_recovers_observed_ocr_total_label_variants(self):
        cases = (
            ("Lidl\ntaal: 16,54 EUR\ntotaal prijsvoordeel 6,65", 16.54),
            ("Lidl\nfotaal 7,36\nfotaa) pri javoordeel 9,75", 7.36),
            ("Lidl\nTotaa] 14,29", 14.29),
            ("Lidl\nMota: 27,85 ER", 27.85),
            ("Lidl\n/Totaa}: 6,48 Eup", 6.48),
            ("Lidl\nfotaal 3,81\njotaal: 3,87 EUR", 3.87),
        )

        for text, expected in cases:
            with self.subTest(text=text):
                result = FinancialFieldExtractor().extract(text)
                self.assertEqual(result["extracted_data"]["total_amount"], expected)
                self.assertGreaterEqual(result["field_confidences"]["total_amount"], 0.9)

    def test_repairs_corrupted_total_only_with_payment_and_vat_consensus(self):
        result = FinancialFieldExtractor().extract(
            "Lidl\nfotaal 1,36\nbankpas 736\n"
            "Bedr.Excl BW Bedr Incl\n89 6,75 0,61 1,6"
        )

        self.assertEqual(result["extracted_data"]["total_amount"], 7.36)
        self.assertEqual(result["field_confidences"]["total_amount"], 1.0)

    def test_payment_label_does_not_promote_timestamp_or_auth_code_to_total(self):
        result = FinancialFieldExtractor().extract(
            "Shop\nBETALING\n26/05/2023,17::31 Auth. code: B30014\n"
            "Product 9,59"
        )

        self.assertIsNone(result["extracted_data"]["total_amount"])
        self.assertEqual(result["field_confidences"]["total_amount"], 0.0)

    def test_insurance_coverage_limits_are_not_transaction_totals(self):
        result = FinancialFieldExtractor().extract(
            "Polisblad\nCataloguswaarde EUR 4.300,00\n"
            "WA verzekerd bedrag EUR 2.500.000,00\n"
            "Dekking EUR 6.100.000,00\nEigen risico EUR 75,00"
        )

        self.assertIsNone(result["extracted_data"]["total_amount"])
        self.assertEqual(result["field_confidences"]["total_amount"], 0.0)

    def test_payable_premium_outranks_insurance_coverage_limit(self):
        result = FinancialFieldExtractor().extract(
            "Factuur verzekeringspremie\n"
            "Verzekerd bedrag EUR 6.100.000,00\nTe betalen EUR 125,40"
        )

        self.assertEqual(result["extracted_data"]["total_amount"], 125.4)
        self.assertGreaterEqual(result["field_confidences"]["total_amount"], 0.9)

    def test_government_thresholds_are_not_transaction_totals(self):
        result = FinancialFieldExtractor().extract(
            "Participatiewet\nBijstandsnorm EUR 1.243,03\n"
            "Vrij te laten vermogen EUR 15.210,00"
        )

        self.assertIsNone(result["extracted_data"]["total_amount"])

    def test_gross_total_wins_when_tax_table_shares_the_final_total_row(self):
        result = FinancialFieldExtractor().extract(
            "ACTION\n12-07-2023\nTOTAAL 1.98\n"
            "BTW-SPECIFICATIE BTW Excl. Incl.\nTOTAAL 0.16 1.82 1.98"
        )

        self.assertEqual(result["extracted_data"]["vendor_name"], "Action")
        self.assertEqual(result["extracted_data"]["total_amount"], 1.98)
        self.assertGreaterEqual(result["field_confidences"]["vendor_name"], 0.9)
        self.assertGreaterEqual(result["field_confidences"]["transaction_date"], 0.8)

    def test_recovers_strong_vendor_names_from_ocr_receipt_headers(self):
        cases = (
            ("AAGTION\n1385 Arnhem\nTotaal 12,00", "Action", 0.85),
            ("Albert Heijn Oosterbeek\nTotaal 12,00", "Albert Heijn Oosterbeek", 0.9),
            ("Sun Wah Supermarket\nVan Wesenbekestraat\nTotaal 12,00", "Sun Wah Supermarket", 0.9),
            ("Solow Arnie\nJansstraat 28\nTotaal 12,00", "SoLow", 0.9),
            ("GWITCH\n2Switch Arnhem\nTotaal 12,00", "2Switch", 0.9),
            ("mantel A\\\nDatum: 8-7-2023\nTotaal 12,00", "Mantel", 0.9),
        )

        for text, vendor, minimum_confidence in cases:
            with self.subTest(vendor=vendor):
                result = FinancialFieldExtractor().extract(text)
                self.assertEqual(result["extracted_data"]["vendor_name"], vendor)
                self.assertGreaterEqual(
                    result["field_confidences"]["vendor_name"],
                    minimum_confidence,
                )
                self.assertEqual(
                    result["field_evidence"]["vendor_name"]["source"],
                    "receipt_header_vendor_pattern",
                )

    def test_recovers_lidl_from_stable_terminal_merchant_identifier(self):
        result = FinancialFieldExtractor().extract(
            "Unreadable receipt header\n"
            "Terminal: 2PR901 Herchant: 1770001\n"
            "Totaal EUR 12,02"
        )

        self.assertEqual(result["extracted_data"]["vendor_name"], "Lidl")
        self.assertEqual(result["field_confidences"]["vendor_name"], 0.9)
        self.assertEqual(
            result["field_evidence"]["vendor_name"]["source"],
            "known_vendor_pattern",
        )

    def test_payable_total_wins_over_discount_amount(self):
        result = FinancialFieldExtractor().extract(
            "T-Mobile\nKorting -9,99\n"
            "Totaal maandelijkse kosten na activatie Klantvoordeel korting EUR 25,00"
        )

        self.assertEqual(result["extracted_data"]["total_amount"], 25.0)
        self.assertGreaterEqual(result["field_confidences"]["total_amount"], 0.9)

    def test_payment_line_wins_over_vat_amount(self):
        result = FinancialFieldExtractor().extract(
            "Praxis\nBTW 21% 4,33\nPin 24,95"
        )

        self.assertEqual(result["extracted_data"]["total_amount"], 24.95)
        self.assertGreaterEqual(result["field_confidences"]["total_amount"], 0.9)

    def test_bank_card_payment_wins_over_vat_summary(self):
        result = FinancialFieldExtractor().extract(
            "Lidl\nBankpas 5 _ 9,59\n"
            "Bedr.Excl BTW Bedr Incl\nA 0 -5,25 0,00 -5,25"
        )

        self.assertEqual(result["extracted_data"]["total_amount"], 9.59)
        self.assertGreaterEqual(result["field_confidences"]["total_amount"], 0.9)

    def test_corrupted_gross_vat_value_is_recomputed_from_valid_parts(self):
        result = FinancialFieldExtractor().extract(
            "Shop\nBTW 21% 5,40 25,72 934,12"
        )

        self.assertEqual(result["extracted_data"]["total_amount"], 31.12)
        self.assertEqual(result["field_confidences"]["total_amount"], 0.94)

    def test_ambiguous_descending_vat_row_does_not_become_total(self):
        result = FinancialFieldExtractor().extract(
            "Shop\nBTW 21% 31,12 25,72 5,40"
        )

        self.assertIsNone(result["extracted_data"]["total_amount"])
        self.assertEqual(result["field_confidences"]["total_amount"], 0.0)

    def test_explicit_total_outranks_vat_summary_rows(self):
        result = FinancialFieldExtractor().extract(
            "Shop\nTotaal 14,82\n"
            "BTW 9% 0,86 9,50 10,36\n"
            "BTW 21% 0,77 3,69 4,46"
        )

        self.assertEqual(result["extracted_data"]["total_amount"], 14.82)
        self.assertEqual(result["field_confidences"]["total_amount"], 0.999)

    def test_total_context_does_not_leak_to_unrelated_next_line(self):
        result = FinancialFieldExtractor().extract(
            "Shop\nBTW DETAIL BTW Excl. Incl.\n"
            "21% 1,59 unreadable\nTOTAAL 1,59 1,51 16\n"
            "Wij zijn geopend van 10.00 tot 17.00 uur"
        )

        self.assertIsNone(result["extracted_data"]["total_amount"])

    def test_two_column_vat_row_uses_header_evidence_for_gross(self):
        result = FinancialFieldExtractor().extract(
            "Shop\nBTW-BEDRAG BRUTO\n0,49 5,89"
        )

        self.assertEqual(result["extracted_data"]["total_amount"], 5.89)

    def test_refund_payment_is_negative(self):
        result = FinancialFieldExtractor().extract(
            "Praxis\nTERUGBETALING\nTerug (Vpay) 25,00"
        )

        self.assertEqual(result["extracted_data"]["total_amount"], -25.0)

    def test_cash_given_does_not_outrank_receipt_total(self):
        result = FinancialFieldExtractor().extract(
            "Hornbach\nTotaal EUR 125,40\n"
            "GEGEVEN Contant EUR 150,00\nWisselgeld EUR -24,60"
        )

        self.assertEqual(result["extracted_data"]["total_amount"], 125.4)

    def test_total_discount_does_not_become_payable_total(self):
        result = FinancialFieldExtractor().extract(
            "Praxis\nTOTALE KORTING: 7,00 EUR\n"
            "BTW DETAIL BTW Excl. Incl.\n21% 4,86 23,13 27,99"
        )

        self.assertEqual(result["extracted_data"]["total_amount"], 27.99)

    def test_explicit_total_outranks_partial_refund_tender(self):
        result = FinancialFieldExtractor().extract(
            "Praxis\nTOTAAL 6,39\nRetourcheque 8,91\nTerug (Vpay) 2,82"
        )

        self.assertEqual(result["extracted_data"]["total_amount"], 6.39)

    def test_vat_column_separators_are_not_refund_signs(self):
        result = FinancialFieldExtractor().extract(
            "Praxis\nBTW DETAIL BTW Excl. Incl.\n"
            "TOTAAL - 5,40 - 25,72 934,12"
        )

        self.assertEqual(result["extracted_data"]["total_amount"], 31.12)

    def test_extracts_dutch_dotted_and_year_month_dates(self):
        dotted = FinancialFieldExtractor().extract(
            "Hornbach\nDatum: 10.07.2023\nTotaal EUR 25,00"
        )
        year_month = FinancialFieldExtractor().extract(
            "Praxis\n2023-jul-07 17:52\nTotaal EUR 25,00"
        )

        self.assertEqual(dotted["extracted_data"]["transaction_date"], "2023-07-10")
        self.assertEqual(year_month["extracted_data"]["transaction_date"], "2023-07-07")

    def test_recovers_observed_ocr_month_separator_variants(self):
        cases = (
            ("Lidl\n2023- jul 08\nTotaal 12,00", "2023-07-08"),
            ("Lidl\n2023-jun- 02\nTotaal 12,00", "2023-06-02"),
            ("Lidl\n2023--jur- 08\nTotaal 12,00", "2023-06-08"),
            ("Lidl\nzondag 16 jul} 2023\nTotaal 12,00", "2023-07-16"),
        )

        for text, expected in cases:
            with self.subTest(text=text):
                result = FinancialFieldExtractor().extract(text)
                self.assertEqual(result["extracted_data"]["transaction_date"], expected)
                self.assertGreaterEqual(result["field_confidences"]["transaction_date"], 0.8)

    def test_unique_unlabelled_valid_date_has_review_threshold_confidence(self):
        result = FinancialFieldExtractor().extract(
            "Praxis\nAmsterdamseweg 127\n07-07-2023\nTotaal EUR 25,00"
        )

        self.assertEqual(result["extracted_data"]["transaction_date"], "2023-07-07")
        self.assertEqual(result["field_confidences"]["transaction_date"], 0.8)

    def test_explicit_ocr_datum_line_outranks_conflicting_unlabelled_date(self):
        result = FinancialFieldExtractor().extract(
            "ACTION\n13-07-2023 15:54:20\n"
            "Totaal EUR 14,82\nDatum 23/07/2023"
        )

        self.assertEqual(result["extracted_data"]["transaction_date"], "2023-07-23")
        self.assertEqual(result["field_confidences"]["transaction_date"], 0.95)

    def test_implausible_labeled_date_falls_back_to_valid_receipt_date(self):
        result = FinancialFieldExtractor().extract(
            "ACTION\n10-06-2023 12:49:47\n"
            "Totaal EUR 13,98\nDatum: 10/06/3038"
        )

        self.assertEqual(result["extracted_data"]["transaction_date"], "2023-06-10")
        self.assertEqual(result["field_confidences"]["transaction_date"], 0.8)

    def test_only_implausible_date_is_not_extracted(self):
        result = FinancialFieldExtractor().extract(
            "Kopie kaarthouder\nDatum: 16/07/2823\nTotaal EUR 7,46"
        )

        self.assertIsNone(result["extracted_data"]["transaction_date"])
        self.assertEqual(result["field_confidences"]["transaction_date"], 0.0)

    def test_reference_requires_identifier_digits(self):
        false_reference = FinancialFieldExtractor().extract(
            "T-Mobile\nInvoice staat open\nTotaal EUR 27,68"
        )
        valid_reference = FinancialFieldExtractor().extract(
            "BrainForce\nInvoice BD4462AC-0002\nTotaal EUR 29,00"
        )

        self.assertIsNone(false_reference["extracted_data"]["invoice_number"])
        self.assertEqual(false_reference["field_confidences"]["invoice_number"], 0.0)
        self.assertEqual(
            valid_reference["extracted_data"]["invoice_number"],
            "BD4462AC-0002",
        )
        self.assertEqual(valid_reference["field_confidences"]["invoice_number"], 0.8)


if __name__ == "__main__":
    unittest.main()
