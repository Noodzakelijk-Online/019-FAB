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

    def test_exact_vendor_batch_applies_only_category_and_target_with_audit_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))

            def register(source_id, vendor, target="waveapps_business", duplicate_of=None):
                document_id = ledger.register_document({
                    "source": "google_drive",
                    "sourceDocumentId": source_id,
                    "originalFilename": f"{source_id}.pdf",
                    "processingStatus": "needs_review",
                    "vendorName": vendor,
                    "category": "Manual Review",
                    "transactionDate": "2026-06-28",
                    "totalAmount": 25.0,
                    "duplicateOfDocumentId": duplicate_of,
                    "metadata": {"targetSystem": target},
                })
                review_id = ledger.create_review_item({
                    "documentId": document_id,
                    "reason": "manual_review_category",
                    "details": "Choose a category.",
                })
                ledger.create_review_item({
                    "documentId": document_id,
                    "reason": "low_confidence_categorization",
                    "details": "Confirm category.",
                })
                return document_id, review_id

            primary_id, primary_review_id = register("primary", "T-Mobile")
            matching_id, _ = register("matching", "  t-mobile  ")
            approximate_id, _ = register("approximate", "T Mobile")
            personal_id, _ = register("personal", "T-Mobile", target="waveapps_personal")
            duplicate_id, _ = register("duplicate", "T-Mobile", duplicate_of=primary_id)
            validation_only_id = ledger.register_document({
                "source": "google_drive",
                "sourceDocumentId": "validation-only",
                "originalFilename": "validation-only.pdf",
                "processingStatus": "needs_review",
                "vendorName": "T-Mobile",
                "category": "Manual Review",
                "metadata": {"targetSystem": "waveapps_business"},
            })
            validation_review_id = ledger.create_review_item({
                "documentId": validation_only_id,
                "reason": "validation_failed",
                "details": "Date and amount are missing.",
            })
            duplicate_review_id = ledger.create_review_item({
                "documentId": matching_id,
                "reason": "duplicate_candidate",
                "details": "Compare source documents.",
            })

            result = LocalReviewService(ledger).resolve_review_item(
                primary_review_id,
                status="approved",
                resolution="Verified recurring telecom expense.",
                corrections={
                    "vendorName": "T-Mobile",
                    "category": "Operations | Telecommunications",
                    "transactionDate": "2026-06-28",
                    "totalAmount": 25.0,
                    "targetSystem": "waveapps_business",
                },
                apply_to_matching_vendor=True,
            )

            self.assertTrue(result["success"])
            batch = result["batchPropagation"]
            self.assertEqual(batch["status"], "applied")
            self.assertEqual(batch["matchedDocuments"], 1)
            self.assertEqual(batch["appliedDocuments"], 1)
            self.assertEqual(len(batch["appliedReviewItemIds"]), 1)
            self.assertIn(
                {"documentId": duplicate_id, "reason": "document_marked_duplicate"},
                batch["skipped"],
            )

            matching = ledger.get_document(matching_id)
            self.assertEqual(matching["vendor_name"], "  t-mobile  ")
            self.assertEqual(matching["category"], "Operations | Telecommunications")
            self.assertEqual(matching["transaction_date"], "2026-06-28")
            self.assertEqual(matching["total_amount"], 25.0)
            self.assertEqual(matching["processing_status"], "needs_review")
            self.assertEqual(
                [item["id"] for item in ledger.list_review_items(
                    status=("pending", "in_review"),
                    document_id=matching_id,
                )],
                [duplicate_review_id],
            )
            self.assertEqual(ledger.get_document(approximate_id)["category"], "Manual Review")
            self.assertEqual(ledger.get_document(personal_id)["category"], "Manual Review")
            self.assertEqual(ledger.get_document(duplicate_id)["category"], "Manual Review")
            self.assertEqual(ledger.get_document(validation_only_id)["category"], "Manual Review")
            self.assertEqual(ledger.get_review_item(validation_review_id)["status"], "pending")
            self.assertEqual(len(ledger.list_vendor_category_rules()), 1)
            batch_events = [
                event for event in ledger.list_audit_events()
                if event["action"] == "local_review.vendor_category_batch.resolve"
            ]
            self.assertEqual(batch_events[0]["details"]["appliedDocuments"], 1)

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
