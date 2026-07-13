import os
import tempfile
import unittest
from datetime import date

from src.operations.local_compliance import LocalComplianceService
from src.operations.local_ledger import LocalOperationsLedger


class TestLocalComplianceService(unittest.TestCase):
    def _ledger(self, temp_dir):
        ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
        good_path = os.path.join(temp_dir, "good-receipt.txt")
        with open(good_path, "w", encoding="utf-8") as handle:
            handle.write("Office Shop total 121.00 VAT 21.00")
        good_document_id = ledger.register_document({
            "source": "scanner",
            "sourceDocumentId": "compliance-good",
            "originalFilename": "good-receipt.txt",
            "storagePath": good_path,
            "processingStatus": "reviewed",
        })
        bad_document_id = ledger.register_document({
            "source": "scanner",
            "sourceDocumentId": "compliance-bad",
            "originalFilename": "missing-receipt.pdf",
            "storagePath": os.path.join(temp_dir, "missing-receipt.pdf"),
            "processingStatus": "reviewed",
        })
        good_record_id = ledger.upsert_bookkeeping_record({
            "documentId": good_document_id,
            "recordType": "expense",
            "status": "ready_to_route",
            "targetSystem": "waveapps_business",
            "targetAccount": "Office expenses",
            "vendorName": "Office Shop",
            "category": "Office",
            "recordDate": "2026-07-02",
            "amount": 121,
            "vatAmount": 21,
            "currency": "EUR",
            "reviewRequired": False,
            "reconciliationStatus": "reconciled",
        })
        ledger.replace_bookkeeping_record_line_items(good_record_id, [{
            "lineIndex": 0,
            "itemName": "Office supplies",
            "amount": 121,
            "taxAmount": 21,
            "taxRate": 21,
            "taxCode": "BTW 21%",
            "accountName": "Office expenses",
        }])
        bad_record_id = ledger.upsert_bookkeeping_record({
            "documentId": bad_document_id,
            "recordType": "expense",
            "status": "ready_to_route",
            "targetSystem": "waveapps_business",
            "targetAccount": "Travel",
            "vendorName": "Foreign Vendor",
            "category": "Travel",
            "recordDate": "2026-07-03",
            "amount": 109,
            "vatAmount": 10,
            "currency": "USD",
            "reviewRequired": False,
            "reconciliationStatus": "reconciled",
        })
        ledger.replace_bookkeeping_record_line_items(bad_record_id, [{
            "lineIndex": 0,
            "itemName": "Travel",
            "amount": 109,
            "taxAmount": 10,
            "taxRate": 10.1,
            "accountName": "Travel",
        }])
        missing_vat_record_id = ledger.upsert_bookkeeping_record({
            "bankTransactionId": 99,
            "sourceType": "bank_transaction",
            "recordType": "expense",
            "status": "draft",
            "targetSystem": "waveapps_business",
            "targetAccount": "Professional fees",
            "vendorName": "Advisor",
            "category": "Professional fees",
            "recordDate": "2026-07-04",
            "amount": -75,
            "currency": "EUR",
            "reviewRequired": False,
            "reconciliationStatus": "reconciled",
        })
        return ledger, good_record_id, bad_record_id, missing_vat_record_id

    def test_assessment_persists_vat_findings_and_retention_evidence_idempotently(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger, good_record_id, bad_record_id, _ = self._ledger(temp_dir)
            service = LocalComplianceService(ledger)

            first = service.assess(
                from_date="2026-07-01",
                to_date="2026-07-31",
                actor="test",
                today=date(2026, 7, 13),
            )
            second = service.assess(
                from_date="2026-07-01",
                to_date="2026-07-31",
                actor="test",
                today=date(2026, 7, 13),
            )

            self.assertTrue(first["created"])
            self.assertEqual(second["status"], "already_current")
            self.assertEqual(len(ledger.list_compliance_assessments()), 1)
            self.assertEqual(first["statutoryStatus"], "provisional")
            self.assertEqual(first["filingStatus"], "not_filed")
            self.assertEqual(first["externalFiling"], "not_executed")
            codes = {finding["code"] for finding in first["findings"]}
            self.assertIn("vat_rate_unrecognized", codes)
            self.assertIn("vat_tax_code_missing", codes)
            self.assertIn("line_tax_rate_unrecognized", codes)
            self.assertIn("vat_currency_conversion_required", codes)
            self.assertIn("source_document_missing", codes)
            self.assertIn("vat_classification_missing", codes)
            good_codes = {
                finding["code"]
                for finding in first["findings"]
                if finding.get("bookkeeping_record_id") == good_record_id
            }
            self.assertEqual(good_codes, set())
            bad_findings = [
                finding for finding in first["findings"]
                if finding.get("bookkeeping_record_id") == bad_record_id
            ]
            self.assertTrue(any(finding["severity"] == "high" for finding in bad_findings))
            self.assertEqual(len(first["retentionRecords"]), 2)
            self.assertTrue(all(item["retain_until"] == "2033-07-02" or item["retain_until"] == "2033-07-03" for item in first["retentionRecords"]))
            self.assertEqual(ledger.dashboard_metrics()["compliance_assessments"], 1)
            self.assertGreater(ledger.dashboard_metrics()["open_compliance_findings"], 0)

            with open(os.path.join(temp_dir, "missing-receipt.pdf"), "w", encoding="utf-8") as handle:
                handle.write("restored source evidence")
            refreshed = service.assess(
                from_date="2026-07-01",
                to_date="2026-07-31",
                actor="test",
                today=date(2026, 7, 13),
            )
            self.assertTrue(refreshed["created"])
            self.assertEqual(len(ledger.list_compliance_assessments()), 2)
            self.assertNotIn("source_document_missing", {item["code"] for item in refreshed["findings"]})
            old_source_finding = next(
                item for item in ledger.list_compliance_findings(limit=500)
                if item["code"] == "source_document_missing"
            )
            self.assertEqual(old_source_finding["status"], "superseded")

    def test_finding_resolution_requires_reason_and_is_audited(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger, _, _, _ = self._ledger(temp_dir)
            service = LocalComplianceService(ledger)
            assessment = service.assess(
                from_date="2026-07-01",
                to_date="2026-07-31",
                today=date(2026, 7, 13),
            )
            finding_id = assessment["findings"][0]["id"]

            with self.assertRaisesRegex(ValueError, "resolution is required"):
                service.update_finding(finding_id, "resolved", actor="tester")
            result = service.update_finding(
                finding_id,
                "accepted_exception",
                resolution="Verified zero-risk historical exception.",
                actor="tester",
            )

            self.assertTrue(result["success"])
            self.assertEqual(result["finding"]["status"], "accepted_exception")
            self.assertEqual(result["externalFiling"], "not_executed")
            refreshed_assessment = ledger.get_compliance_assessment(assessment["assessment"]["id"])
            self.assertEqual(refreshed_assessment["status"], "needs_review")
            self.assertEqual(refreshed_assessment["blocking_count"], 0)
            audit = ledger.list_audit_events(limit=1)[0]
            self.assertEqual(audit["action"], "local_compliance.finding_status_changed")
            self.assertEqual(audit["details"]["actor"], "tester")

    def test_retention_record_never_authorizes_automatic_deletion(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            document_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "old-retention-doc",
                "originalFilename": "old.pdf",
                "processingStatus": "reviewed",
            })
            ledger.upsert_bookkeeping_record({
                "documentId": document_id,
                "recordType": "expense",
                "status": "ready_to_route",
                "targetSystem": "waveapps_business",
                "targetAccount": "Archive",
                "category": "Archive",
                "recordDate": "2010-01-01",
                "amount": 0,
                "vatAmount": 0,
                "currency": "EUR",
                "reconciliationStatus": "reconciled",
            })

            result = LocalComplianceService(ledger).assess(
                from_date="2010-01-01",
                to_date="2010-12-31",
                today=date(2026, 7, 13),
            )

            retention = result["retentionRecords"][0]
            self.assertEqual(retention["status"], "retention_review_eligible")
            self.assertFalse(retention["metadata"]["deletionAuthorized"])

    def test_assessment_does_not_supersede_findings_from_an_unrelated_period(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger, _, _, _ = self._ledger(temp_dir)
            service = LocalComplianceService(ledger)
            july = service.assess(
                from_date="2026-07-01",
                to_date="2026-07-31",
                today=date(2026, 7, 13),
            )
            july_finding_ids = {finding["id"] for finding in july["findings"]}

            service.assess(
                from_date="2026-06-01",
                to_date="2026-06-30",
                today=date(2026, 7, 13),
            )

            july_findings = [
                finding for finding in ledger.list_compliance_findings(limit=500)
                if finding["id"] in july_finding_ids
            ]
            self.assertTrue(july_findings)
            self.assertTrue(all(finding["status"] == "open" for finding in july_findings))


if __name__ == "__main__":
    unittest.main()
