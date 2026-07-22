import os
import tempfile
import unittest

from src.operations.local_bank_transactions import LocalBankTransactionImportService
from src.operations.local_ledger import LocalOperationsLedger
from src.operations.local_reconciliation import LocalReconciliationService
from src.operations.local_review import LocalReviewService


class TestLocalReviewService(unittest.TestCase):
    def test_resolve_review_applies_corrections_and_suggests_rule(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            document_id = ledger.register_document({
                "source": "local_folder",
                "sourceDocumentId": "doc-1",
                "originalFilename": "receipt.txt",
                "processingStatus": "needs_review",
                "vendorName": "Old Vendor",
                "category": "Manual Review",
                "totalAmount": 12.0,
                "extractedData": {"vendor_name": "Old Vendor", "total_amount": 12.0},
            })
            review_id = ledger.create_review_item({
                "documentId": document_id,
                "reason": "low_confidence_categorization",
                "details": "Confirm category.",
            })

            result = LocalReviewService(ledger).resolve_review_item(
                review_id,
                status="approved",
                resolution="Corrected category and amount.",
                corrections={
                    "vendorName": "Correct Vendor",
                    "category": "Office Supplies",
                    "totalAmount": "42.50",
                    "transactionDate": "2026-06-28",
                },
            )

            self.assertTrue(result["success"])
            self.assertIsNotNone(result["correctionId"])
            self.assertIsNotNone(result["ruleId"])
            self.assertIsNotNone(result["bookkeepingRecordId"])
            document = ledger.get_document(document_id)
            self.assertEqual(document["processing_status"], "reviewed")
            self.assertEqual(document["vendor_name"], "Correct Vendor")
            self.assertEqual(document["category"], "Office Supplies")
            self.assertEqual(document["total_amount"], 42.5)
            self.assertEqual(document["transaction_date"], "2026-06-28")
            self.assertEqual(document["bookkeeping_record"]["vendor_name"], "Correct Vendor")
            self.assertEqual(document["bookkeeping_record"]["category"], "Office Supplies")
            self.assertEqual(document["bookkeeping_record"]["amount"], 42.5)
            self.assertEqual(document["bookkeeping_record"]["status"], "ready_to_route")
            self.assertEqual(document["review_items"][0]["status"], "approved")
            self.assertEqual(document["review_corrections"][0]["corrected_data"]["vendorName"], "Correct Vendor")
            rule = ledger.list_vendor_category_rules()[0]
            self.assertEqual(rule["vendor_name"], "Correct Vendor")
            self.assertEqual(rule["category"], "Office Supplies")
            self.assertEqual(rule["status"], "suggested")
            audit_actions = [event["action"] for event in ledger.list_audit_events()]
            self.assertIn("local_review.correction_applied", audit_actions)
            self.assertIn("local_review.vendor_category_rule.suggested", audit_actions)

    def test_duplicate_review_rejects_duplicate_without_deleting_document(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            original_id = ledger.register_document({
                "source": "local_folder",
                "sourceDocumentId": "doc-original",
                "originalFilename": "original.pdf",
                "processingStatus": "processed",
                "duplicateFingerprint": "abc",
            })
            duplicate_id = ledger.register_document({
                "source": "local_folder",
                "sourceDocumentId": "doc-copy",
                "originalFilename": "copy.pdf",
                "processingStatus": "needs_review",
                "duplicateFingerprint": "abc",
                "duplicateOfDocumentId": original_id,
            })
            candidate_id = ledger.record_duplicate_candidate({
                "documentId": duplicate_id,
                "candidateDocumentId": original_id,
                "matchType": "exact_content_hash",
                "confidenceScore": 1.0,
                "status": "pending",
            })
            review_id = ledger.create_review_item({
                "documentId": duplicate_id,
                "reason": "duplicate_candidate",
                "details": "Possible duplicate.",
                "correctedData": {"duplicateCandidateId": candidate_id},
            })

            result = LocalReviewService(ledger).resolve_review_item(review_id, status="rejected")

            self.assertTrue(result["success"])
            self.assertEqual(result["duplicateCandidatesResolved"], 1)
            document = ledger.get_document(duplicate_id)
            self.assertIsNone(document["duplicate_of_document_id"])
            self.assertEqual(document["processing_status"], "reviewed")
            self.assertEqual(document["review_items"][0]["status"], "rejected")
            self.assertEqual(document["duplicate_candidates"][0]["status"], "rejected")
            self.assertEqual(ledger.dashboard_metrics()["documents"], 2)

    def test_category_correction_resolves_satisfied_gates_but_preserves_duplicate_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            document_id = ledger.register_document({
                "source": "local_folder",
                "sourceDocumentId": "doc-multi-gate",
                "originalFilename": "receipt.pdf",
                "processingStatus": "needs_review",
                "vendorName": "Office Shop",
                "category": "Manual Review",
                "transactionDate": "2026-06-28",
                "totalAmount": 42.5,
            })
            category_review_id = ledger.create_review_item({
                "documentId": document_id,
                "reason": "manual_review_category",
                "details": "Choose a category.",
            })
            low_confidence_id = ledger.create_review_item({
                "documentId": document_id,
                "reason": "low_confidence_categorization",
                "details": "Confirm category.",
            })
            validation_id = ledger.create_review_item({
                "documentId": document_id,
                "reason": "validation_failed",
                "details": "Confirm extracted values.",
            })
            duplicate_id = ledger.create_review_item({
                "documentId": document_id,
                "reason": "duplicate_candidate",
                "details": "Confirm duplicate decision.",
            })

            result = LocalReviewService(ledger).resolve_review_item(
                category_review_id,
                status="approved",
                resolution="Confirmed extracted details and category.",
                corrections={"category": "Operations | Office Supplies"},
            )

            self.assertTrue(result["success"])
            self.assertEqual(result["processingStatus"], "needs_review")
            self.assertCountEqual(result["supersededReviewItemIds"], [low_confidence_id, validation_id])
            open_reviews = ledger.list_review_items(
                status=("pending", "in_review"),
                document_id=document_id,
            )
            self.assertEqual([item["id"] for item in open_reviews], [duplicate_id])

    def test_reconciliation_candidate_review_approval_reconciles_linked_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            document_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "receipt-review-match",
                "originalFilename": "receipt.txt",
                "processingStatus": "processed",
                "vendorName": "Office Shop",
                "category": "Office Supplies",
                "transactionDate": "2026-06-28",
                "totalAmount": 42.5,
            })
            bank_service = LocalBankTransactionImportService(ledger, {})
            bank_service.import_transactions([{
                "id": "tx-review-match",
                "date": "2026-06-28",
                "amount": -42.5,
                "description": "Office Shop",
            }])
            LocalReconciliationService(ledger, {"reconciliation_match_threshold": 0.9}).run(
                bank_service.transactions_for_reconciliation()
            )
            review_id = ledger.list_review_items(status="pending")[0]["id"]
            bank_transaction_id = ledger.list_bank_transactions()[0]["id"]

            result = LocalReviewService(ledger).resolve_review_item(
                review_id,
                status="approved",
                resolution="Confirmed from manual review.",
            )

            self.assertTrue(result["success"])
            self.assertEqual(result["reconciliationResolution"]["appliedReconciliationStatus"], "approved")
            document = ledger.get_document(document_id)
            self.assertEqual(document["reconciliation_status"], "reconciled")
            self.assertEqual(document["bookkeeping_record"]["reconciliation_status"], "reconciled")
            self.assertEqual(ledger.list_reconciliation_matches()[0]["status"], "approved")
            self.assertEqual(ledger.get_bank_transaction(bank_transaction_id)["reconciliation_status"], "reconciled")

    def test_missing_receipt_review_ignore_closes_bank_exception(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            bank_service = LocalBankTransactionImportService(ledger, {})
            bank_service.import_transactions([{
                "id": "tx-no-receipt-needed",
                "date": "2026-06-28",
                "amount": -8.5,
                "description": "Bank service fee",
            }])
            LocalReconciliationService(ledger, {}).run(bank_service.transactions_for_reconciliation())
            review_id = ledger.list_review_items(status="pending")[0]["id"]
            bank_transaction_id = ledger.list_bank_transactions()[0]["id"]

            result = LocalReviewService(ledger).resolve_review_item(
                review_id,
                status="ignored",
                resolution="Bank fee does not require a receipt.",
            )

            self.assertTrue(result["success"])
            self.assertEqual(result["reconciliationResolution"]["appliedReconciliationStatus"], "ignored")
            self.assertEqual(ledger.list_review_items()[0]["status"], "ignored")
            self.assertEqual(ledger.list_reconciliation_matches()[0]["status"], "ignored")
            self.assertEqual(ledger.get_bank_transaction(bank_transaction_id)["reconciliation_status"], "ignored")
            record = ledger.get_bookkeeping_record_by_bank_transaction(bank_transaction_id)
            self.assertEqual(record["reconciliation_status"], "ignored")


if __name__ == "__main__":
    unittest.main()
