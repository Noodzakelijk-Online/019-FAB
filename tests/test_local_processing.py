import os
import tempfile
import unittest

from src.operations.local_ledger import LocalOperationsLedger
from src.operations.local_processing import LocalDocumentProcessor


class StaticCategorizer:
    def __init__(self, category="Office Supplies", confidence_score=0.91):
        self.category = category
        self.confidence_score = confidence_score

    def categorize(self, processed_data):
        return {"category": self.category, "confidence_score": self.confidence_score}


class StaticValidator:
    def __init__(self, valid=True, reason=""):
        self.valid = valid
        self.reason = reason

    def validate_receipt(self, processed_data):
        return {
            "is_valid": self.valid,
            "errors": [self.reason] if self.reason else [],
            "warnings": [],
            "reason": self.reason,
            "blocking": not self.valid,
        }


class RaisingPipeline:
    def process_document(self, path):
        raise RuntimeError("OCR engine unavailable")


class StaticPipeline:
    def process_document(self, path):
        return {
            "document_path": path,
            "ocr_text": "Vendor: Retry Vendor\nDate: 2026-06-28\nTotal: EUR 42.50\n",
            "language": "en",
            "extracted_data": {
                "vendor_name": "Retry Vendor",
                "transaction_date": "2026-06-28",
                "total_amount": 42.5,
                "currency": "EUR",
            },
        }


class TestLocalDocumentProcessor(unittest.TestCase):
    def test_process_text_document_updates_ledger_fields_and_audit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            receipt_path = os.path.join(temp_dir, "receipt.txt")
            with open(receipt_path, "w", encoding="utf-8") as handle:
                handle.write("Vendor: Test Vendor\nDate: 2026-06-28\nTotal: EUR 42.50\nVAT: EUR 7.38\n")
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            document_id = ledger.register_document({
                "source": "local_folder",
                "sourceDocumentId": "text-1",
                "originalFilename": "receipt.txt",
                "mimeType": "text/plain",
                "storagePath": receipt_path,
                "documentType": "text",
                "processingStatus": "imported",
            })

            result = LocalDocumentProcessor(
                ledger,
                categorizer=StaticCategorizer(),
                validator=StaticValidator(),
            ).process_document(document_id)

            self.assertEqual(result["status"], "processed")
            self.assertIsNotNone(result["bookkeepingRecordId"])
            document = ledger.get_document(document_id)
            self.assertEqual(document["processing_status"], "processed")
            self.assertEqual(document["vendor_name"], "Test Vendor")
            self.assertEqual(document["category"], "Office Supplies")
            self.assertEqual(document["total_amount"], 42.5)
            self.assertIn("Vendor: Test Vendor", document["ocr_text"])
            fields = {field["field_name"]: field for field in document["extracted_fields"]}
            self.assertEqual(fields["vendor_name"]["field_value"], "Test Vendor")
            self.assertEqual(fields["total_amount"]["field_value"], 42.5)
            self.assertEqual(fields["vat_amount"]["field_value"], 7.38)
            self.assertEqual(fields["category"]["field_value"], "Office Supplies")
            self.assertEqual(fields["vendor_name"]["provenance"]["extractionSource"], "local_text_regex")
            self.assertEqual(document["bookkeeping_record"]["status"], "ready_to_route")
            self.assertEqual(document["bookkeeping_record"]["export_status"], "ready")
            self.assertEqual(ledger.list_audit_events()[0]["action"], "local_processing.document_processed")

    def test_process_text_document_queues_review_for_validation_and_sensitive_terms(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            letter_path = os.path.join(temp_dir, "belastingdienst.txt")
            with open(letter_path, "w", encoding="utf-8") as handle:
                handle.write("Belastingdienst\nVendor: Government\nTotal: EUR 0.00\n")
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            document_id = ledger.register_document({
                "source": "local_folder",
                "sourceDocumentId": "letter-1",
                "originalFilename": "belastingdienst.txt",
                "mimeType": "text/plain",
                "storagePath": letter_path,
                "documentType": "text",
                "processingStatus": "imported",
            })

            result = LocalDocumentProcessor(
                ledger,
                categorizer=StaticCategorizer(category="Manual Review", confidence_score=0.1),
                validator=StaticValidator(valid=False, reason="Missing transaction date"),
            ).process_document(document_id)

            self.assertEqual(result["status"], "needs_review")
            self.assertIsNotNone(result["bookkeepingRecordId"])
            self.assertIn("validation_failed", result["reviewReasons"])
            self.assertIn("low_confidence_categorization", result["reviewReasons"])
            self.assertIn("manual_review_category", result["reviewReasons"])
            self.assertIn("sensitive_government_document", result["reviewReasons"])
            review_reasons = {item["reason"] for item in ledger.list_review_items(status="pending")}
            self.assertIn("sensitive_government_document", review_reasons)
            document = ledger.get_document(document_id)
            self.assertEqual(document["processing_status"], "needs_review")
            self.assertEqual(document["bookkeeping_record"]["status"], "needs_review")
            self.assertEqual(document["bookkeeping_record"]["review_required"], 1)

    def test_reprocessing_resolves_machine_review_reasons_that_are_no_longer_active(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            receipt_path = os.path.join(temp_dir, "receipt.txt")
            with open(receipt_path, "w", encoding="utf-8") as handle:
                handle.write("Vendor: Test Vendor\nDate: 2026-06-28\nTotal: EUR 42.50\n")
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            document_id = ledger.register_document({
                "source": "local_folder",
                "sourceDocumentId": "reprocess-1",
                "originalFilename": "receipt.txt",
                "mimeType": "text/plain",
                "storagePath": receipt_path,
                "documentType": "text",
                "processingStatus": "imported",
            })

            first = LocalDocumentProcessor(
                ledger,
                categorizer=StaticCategorizer(category="Manual Review", confidence_score=0.1),
                validator=StaticValidator(valid=False, reason="Missing required field"),
            ).process_document(document_id)
            second = LocalDocumentProcessor(
                ledger,
                categorizer=StaticCategorizer(),
                validator=StaticValidator(),
            ).process_document(document_id)

            self.assertEqual(first["status"], "needs_review")
            self.assertEqual(second["status"], "processed")
            self.assertEqual(len(second["resolvedReviewItemIds"]), 3)
            self.assertEqual(
                ledger.list_review_items(status=("pending", "in_review"), document_id=document_id),
                [],
            )
            resolved_reasons = {
                item["reason"]
                for item in ledger.list_review_items(status="resolved", document_id=document_id)
            }
            self.assertEqual(
                resolved_reasons,
                {"validation_failed", "low_confidence_categorization", "manual_review_category"},
            )

    def test_approved_vendor_rule_overrides_low_confidence_category(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            receipt_path = os.path.join(temp_dir, "receipt.txt")
            with open(receipt_path, "w", encoding="utf-8") as handle:
                handle.write("Vendor: Office Shop\nDate: 2026-06-28\nTotal: EUR 42.50\n")
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            document_id = ledger.register_document({
                "source": "local_folder",
                "sourceDocumentId": "rule-approved",
                "originalFilename": "receipt.txt",
                "mimeType": "text/plain",
                "storagePath": receipt_path,
                "documentType": "text",
                "processingStatus": "imported",
            })
            rule_id = ledger.upsert_vendor_category_rule({
                "vendorName": "Office Shop",
                "category": "Office Supplies",
                "targetSystem": "none",
                "confidenceScore": 0.98,
                "status": "approved",
            })

            result = LocalDocumentProcessor(
                ledger,
                categorizer=StaticCategorizer(category="Manual Review", confidence_score=0.1),
                validator=StaticValidator(),
            ).process_document(document_id)

            self.assertEqual(result["status"], "processed")
            self.assertEqual(result["category"], "Office Supplies")
            self.assertEqual(result["appliedVendorCategoryRule"]["ruleId"], rule_id)
            self.assertEqual(result["reviewReasons"], [])
            document = ledger.get_document(document_id)
            self.assertEqual(document["category"], "Office Supplies")
            self.assertEqual(document["metadata"]["processing"]["appliedVendorCategoryRule"]["ruleId"], rule_id)
            fields = {field["field_name"]: field for field in document["extracted_fields"]}
            self.assertEqual(fields["category"]["provenance"]["fieldSource"], "approved_vendor_rule")
            self.assertEqual(fields["category"]["provenance"]["ruleId"], rule_id)
            self.assertEqual(document["bookkeeping_record"]["status"], "ready_to_route")
            audit = ledger.list_audit_events()[0]
            self.assertEqual(audit["action"], "local_processing.document_processed")
            self.assertEqual(audit["details"]["appliedVendorCategoryRule"]["ruleId"], rule_id)

    def test_suggested_vendor_rule_does_not_override_processing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            receipt_path = os.path.join(temp_dir, "receipt.txt")
            with open(receipt_path, "w", encoding="utf-8") as handle:
                handle.write("Vendor: Office Shop\nDate: 2026-06-28\nTotal: EUR 42.50\n")
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            document_id = ledger.register_document({
                "source": "local_folder",
                "sourceDocumentId": "rule-suggested",
                "originalFilename": "receipt.txt",
                "mimeType": "text/plain",
                "storagePath": receipt_path,
                "documentType": "text",
                "processingStatus": "imported",
            })
            ledger.upsert_vendor_category_rule({
                "vendorName": "Office Shop",
                "category": "Office Supplies",
                "targetSystem": "none",
                "status": "suggested",
            })

            result = LocalDocumentProcessor(
                ledger,
                categorizer=StaticCategorizer(category="Manual Review", confidence_score=0.1),
                validator=StaticValidator(),
            ).process_document(document_id)

            self.assertEqual(result["status"], "needs_review")
            self.assertIsNone(result["appliedVendorCategoryRule"])
            self.assertIn("low_confidence_categorization", result["reviewReasons"])
            self.assertIn("manual_review_category", result["reviewReasons"])
            document = ledger.get_document(document_id)
            self.assertEqual(document["category"], "Manual Review")
            fields = {field["field_name"]: field for field in document["extracted_fields"]}
            self.assertEqual(fields["category"]["provenance"]["fieldSource"], "categorizer")

    def test_process_imported_batches_only_imported_documents(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            receipt_path = os.path.join(temp_dir, "receipt.txt")
            with open(receipt_path, "w", encoding="utf-8") as handle:
                handle.write("Vendor: Test Vendor\nDate: 2026-06-28\nTotal: 42.50\n")
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            ledger.register_document({
                "source": "local_folder",
                "sourceDocumentId": "text-1",
                "originalFilename": "receipt.txt",
                "mimeType": "text/plain",
                "storagePath": receipt_path,
                "documentType": "text",
                "processingStatus": "imported",
            })
            ledger.register_document({
                "source": "local_folder",
                "sourceDocumentId": "done-1",
                "originalFilename": "done.txt",
                "processingStatus": "processed",
            })

            summary = LocalDocumentProcessor(
                ledger,
                categorizer=StaticCategorizer(),
                validator=StaticValidator(),
            ).process_imported()

            self.assertEqual(summary["requested"], 1)
            self.assertEqual(summary["processed"], 1)
            self.assertEqual(summary["needsReview"], 0)
            self.assertEqual(ledger.dashboard_metrics()["documents"], 2)

    def test_process_text_document_flags_fuzzy_duplicate_candidate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            first_path = os.path.join(temp_dir, "first.txt")
            second_path = os.path.join(temp_dir, "second.txt")
            with open(first_path, "w", encoding="utf-8") as handle:
                handle.write("Vendor: Office Shop\nDate: 2026-06-28\nTotal: EUR 42.50\n")
            with open(second_path, "w", encoding="utf-8") as handle:
                handle.write("Supplier: Office Shop\nDate: 2026-06-28\nAmount: EUR 42.50\nDifferent scan bytes\n")
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            original_id = ledger.register_document({
                "source": "local_folder",
                "sourceDocumentId": "first",
                "originalFilename": "first.txt",
                "mimeType": "text/plain",
                "storagePath": first_path,
                "documentType": "text",
                "processingStatus": "processed",
                "vendorName": "Office Shop",
                "transactionDate": "2026-06-28",
                "totalAmount": 42.5,
                "extractedData": {
                    "vendor_name": "Office Shop",
                    "transaction_date": "2026-06-28",
                    "total_amount": 42.5,
                },
            })
            duplicate_id = ledger.register_document({
                "source": "local_folder",
                "sourceDocumentId": "second",
                "originalFilename": "second.txt",
                "mimeType": "text/plain",
                "storagePath": second_path,
                "documentType": "text",
                "processingStatus": "imported",
            })

            result = LocalDocumentProcessor(
                ledger,
                categorizer=StaticCategorizer(),
                validator=StaticValidator(),
            ).process_document(duplicate_id)

            self.assertEqual(result["status"], "needs_review")
            self.assertIn("duplicate_candidate", result["reviewReasons"])
            document = ledger.get_document(duplicate_id)
            self.assertEqual(document["duplicate_of_document_id"], original_id)
            self.assertEqual(document["processing_status"], "needs_review")
            candidates = ledger.list_duplicate_candidates(status="pending", document_id=duplicate_id)
            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0]["candidate_document_id"], original_id)
            self.assertGreaterEqual(candidates[0]["confidence_score"], 0.9)
            self.assertEqual(ledger.list_review_items(status="pending")[0]["reason"], "duplicate_candidate")

    def test_retry_failed_reprocesses_document_and_resolves_failure_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            receipt_path = os.path.join(temp_dir, "receipt.pdf")
            with open(receipt_path, "wb") as handle:
                handle.write(b"receipt bytes")
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            document_id = ledger.register_document({
                "source": "local_folder",
                "sourceDocumentId": "retry-failed",
                "originalFilename": "receipt.pdf",
                "mimeType": "application/pdf",
                "storagePath": receipt_path,
                "documentType": "receipt",
                "processingStatus": "imported",
            })

            failed = LocalDocumentProcessor(
                ledger,
                processor_pipeline=RaisingPipeline(),
                categorizer=StaticCategorizer(),
                validator=StaticValidator(),
            ).process_document(document_id)
            retried = LocalDocumentProcessor(
                ledger,
                processor_pipeline=StaticPipeline(),
                categorizer=StaticCategorizer(),
                validator=StaticValidator(),
            ).retry_failed(actor="tester")

            self.assertEqual(failed["status"], "failed")
            self.assertEqual(retried["requested"], 1)
            self.assertEqual(retried["retried"], 1)
            self.assertEqual(retried["processed"], 1)
            self.assertEqual(retried["documents"][0]["retryCount"], 1)
            document = ledger.get_document(document_id)
            self.assertEqual(document["processing_status"], "processed")
            self.assertEqual(document["vendor_name"], "Retry Vendor")
            self.assertEqual(document["metadata"]["processing"]["retryCount"], 1)
            self.assertEqual(document["metadata"]["processing"]["retryHistory"][0]["previousError"], "OCR engine unavailable")
            failure_reviews = [
                item for item in document["review_items"]
                if item["reason"] == "processing_failed"
            ]
            self.assertEqual(failure_reviews[0]["status"], "resolved")
            audit_actions = [event["action"] for event in ledger.list_audit_events(limit=20)]
            self.assertIn("local_processing.retry_started", audit_actions)
            self.assertIn("local_processing.processing_failed_review_resolved", audit_actions)
            self.assertIn("local_processing.retry_failed_completed", audit_actions)


if __name__ == "__main__":
    unittest.main()
