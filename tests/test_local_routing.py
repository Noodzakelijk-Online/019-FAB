import os
import tempfile
import unittest

from src.operations.local_bookkeeping_records import LocalBookkeepingRecordService
from src.operations.local_ledger import LocalOperationsLedger
from src.operations.local_routing import LocalRoutingService


class TestLocalRoutingService(unittest.TestCase):
    def test_prepare_reviewed_document_creates_wave_draft_attempt(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            document_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "scan-route-1",
                "originalFilename": "receipt.txt",
                "documentType": "receipt",
                "processingStatus": "reviewed",
                "vendorName": "Office Shop",
                "category": "Office Supplies",
                "transactionDate": "2026-06-28",
                "totalAmount": 42.5,
                "extractedData": {
                    "vendor_name": "Office Shop",
                    "transaction_date": "2026-06-28",
                    "total_amount": 42.5,
                    "description": "Printer paper",
                    "line_items": [
                        {
                            "description": "Printer paper",
                            "amount": 42.5,
                            "category": "Office Supplies",
                            "account_name": "Office Supplies",
                            "tax_code": "BTW 21%",
                        }
                    ],
                },
                "metadata": {"targetAccount": "Office Supplies"},
            })

            result = LocalRoutingService(ledger).prepare_document_route(document_id)

            self.assertTrue(result["success"])
            self.assertEqual(result["status"], "draft_prepared")
            self.assertEqual(result["operation"]["action_id"], "transaction_add")
            self.assertEqual(result["operation"]["surface"], "transactions")
            document = ledger.get_document(document_id)
            self.assertEqual(document["processing_status"], "export_draft_prepared")
            self.assertEqual(document["routing_attempts"][0]["status"], "draft_prepared")
            self.assertEqual(document["bookkeeping_record"]["status"], "export_draft_prepared")
            self.assertEqual(document["bookkeeping_record"]["export_status"], "draft_prepared")
            self.assertEqual(
                document["routing_attempts"][0]["metadata"]["operation"]["payload"]["category"],
                "Office Supplies",
            )
            self.assertEqual(
                document["routing_attempts"][0]["metadata"]["operation"]["payload"]["lineItems"][0]["account"],
                "Office Supplies",
            )
            self.assertEqual(
                document["routing_attempts"][0]["metadata"]["operation"]["payload"]["lineItems"][0]["tax"],
                "BTW 21%",
            )
            self.assertEqual(ledger.list_audit_events()[0]["action"], "local_routing.wave_draft_prepared")

    def test_prepare_document_is_idempotent_for_existing_operation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            document_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "scan-route-2",
                "originalFilename": "receipt.txt",
                "processingStatus": "reviewed",
                "vendorName": "Office Shop",
                "category": "Office Supplies",
                "transactionDate": "2026-06-28",
                "totalAmount": 42.5,
            })
            service = LocalRoutingService(ledger)

            first = service.prepare_document_route(document_id)
            ledger.update_document(document_id, {"processingStatus": "reviewed"})
            second = service.prepare_document_route(document_id)

            self.assertEqual(first["status"], "draft_prepared")
            self.assertEqual(second["status"], "already_prepared")
            self.assertEqual(first["routingAttemptId"], second["routingAttemptId"])
            self.assertEqual(len(ledger.get_document(document_id)["routing_attempts"]), 1)

    def test_prepare_reviewed_category_a_document_creates_mijngeldzaken_master_ledger_draft(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            document_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "scan-route-mgz",
                "originalFilename": "groceries.txt",
                "documentType": "receipt",
                "processingStatus": "reviewed",
                "vendorName": "Local Supermarket",
                "category": "Personal",
                "transactionDate": "2026-06-28",
                "totalAmount": 42.5,
                "extractedData": {
                    "vendor_name": "Local Supermarket",
                    "transaction_date": "2026-06-28",
                    "total_amount": 42.5,
                    "description": "Weekly groceries",
                },
                "metadata": {"targetSystem": "mijngeldzaken"},
            })

            result = LocalRoutingService(
                ledger,
                {"mijngeldzaken_category_mapping": {"Personal": "Huishouden"}},
            ).prepare_document_route(document_id)

            self.assertTrue(result["success"])
            self.assertEqual(result["status"], "draft_prepared")
            self.assertEqual(result["target"], "mijngeldzaken:transactions")
            self.assertEqual(result["operation"]["action_id"], "transaction_import_prepare")
            self.assertEqual(result["operation"]["surface"], "transactions")
            self.assertEqual(result["operation"]["payload"]["category"], "Huishouden")
            document = ledger.get_document(document_id)
            self.assertEqual(document["processing_status"], "export_draft_prepared")
            self.assertEqual(document["routing_attempts"][0]["metadata"]["masterLedgerDownstream"], True)
            self.assertEqual(document["bookkeeping_record"]["export_status"], "draft_prepared")
            self.assertEqual(ledger.list_audit_events()[0]["action"], "local_routing.mijngeldzaken_draft_prepared")

    def test_missing_routing_fields_create_review_and_block_export(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            document_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "scan-route-3",
                "originalFilename": "receipt.txt",
                "processingStatus": "reviewed",
                "vendorName": "Office Shop",
                "category": "Office Supplies",
                "totalAmount": 42.5,
            })

            result = LocalRoutingService(ledger).prepare_document_route(document_id)

            self.assertFalse(result["success"])
            self.assertEqual(result["status"], "needs_review")
            document = ledger.get_document(document_id)
            self.assertEqual(document["processing_status"], "needs_review")
            self.assertEqual(document["review_items"][0]["reason"], "routing_fields_missing")
            self.assertIn("transactionDate", document["review_items"][0]["details"])
            self.assertEqual(document["routing_attempts"][0]["status"], "needs_review")
            self.assertEqual(document["bookkeeping_record"]["status"], "needs_review")
            self.assertEqual(document["bookkeeping_record"]["export_status"], "blocked_by_review")

    def test_open_review_blocks_route_preparation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            document_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "scan-route-4",
                "originalFilename": "receipt.txt",
                "processingStatus": "reviewed",
                "vendorName": "Office Shop",
                "category": "Office Supplies",
                "transactionDate": "2026-06-28",
                "totalAmount": 42.5,
            })
            ledger.create_review_item({
                "documentId": document_id,
                "reason": "human_check",
                "status": "pending",
            })

            result = LocalRoutingService(ledger).prepare_document_route(document_id)

            self.assertFalse(result["success"])
            self.assertEqual(result["status"], "blocked_review")
            self.assertEqual(ledger.get_document(document_id)["routing_attempts"][0]["status"], "blocked_review")

    def test_non_posting_document_is_blocked_even_after_review_is_closed(self):
        for target_system in ("waveapps", "mijngeldzaken"):
            with self.subTest(target_system=target_system), tempfile.TemporaryDirectory() as temp_dir:
                ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
                document_id = ledger.register_document({
                    "source": "scanner",
                    "sourceDocumentId": f"policy-{target_system}",
                    "originalFilename": "policy.pdf",
                    "documentType": "insurance_policy",
                    "processingStatus": "reviewed",
                    "vendorName": "Insurer",
                    "category": "Supporting Evidence",
                    "transactionDate": "2026-06-28",
                    "totalAmount": 6100000,
                    "metadata": {"targetSystem": target_system},
                })

                result = LocalRoutingService(ledger).prepare_document_route(document_id)
                document = ledger.get_document(document_id)

                self.assertFalse(result["success"])
                self.assertEqual(result["status"], "blocked_non_posting_document_type")
                self.assertEqual(document["routing_attempts"][0]["status"], result["status"])
                self.assertEqual(
                    document["routing_attempts"][0]["metadata"]["externalSubmission"],
                    "not_executed",
                )
                self.assertEqual(document["bookkeeping_record"]["export_status"], "not_applicable")

    def test_non_posting_classifier_conflict_requires_explicit_type_override(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            document_id = ledger.register_document({
                "source": "scanner",
                "sourceDocumentId": "policy-invoice-conflict",
                "originalFilename": "policy.pdf",
                "documentType": "vendor_invoice",
                "processingStatus": "reviewed",
                "vendorName": "Insurer",
                "category": "Insurance",
                "transactionDate": "2026-06-28",
                "totalAmount": 125.4,
                "metadata": {
                    "processing": {
                        "documentTypeClassification": {
                            "documentType": "insurance_policy",
                            "classifier": "deterministic_financial_document_type_v2",
                        },
                    },
                },
            })
            service = LocalRoutingService(ledger)

            blocked = service.prepare_document_route(document_id)
            self.assertEqual(blocked["status"], "blocked_document_type_conflict")

            document = ledger.get_document(document_id)
            metadata = dict(document["metadata"])
            metadata["review"] = {
                "documentTypeOverride": {
                    "documentType": "vendor_invoice",
                    "source": "manual_review_correction",
                },
            }
            ledger.update_document(document_id, {"metadata": metadata})
            prepared = service.prepare_document_route(document_id)

            self.assertTrue(prepared["success"])
            self.assertEqual(prepared["status"], "draft_prepared")

    def test_prepare_bank_transaction_record_creates_wave_draft_attempt(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            ledger.upsert_vendor_category_rule({
                "vendorName": "Office Shop",
                "category": "Office Supplies",
                "targetSystem": "waveapps",
                "status": "approved",
                "confidenceScore": 0.97,
            })
            transaction_id = ledger.upsert_bank_transaction({
                "accountIdentifier": "wave-checking",
                "transactionId": "tx-route-bank-record",
                "transactionDate": "2026-06-28",
                "amount": -42.5,
                "currency": "EUR",
                "description": "Printer paper",
                "counterparty": "Office Shop",
                "reconciliationStatus": "not_started",
            })
            record_result = LocalBookkeepingRecordService(ledger, {}).upsert_from_bank_transaction(transaction_id)

            result = LocalRoutingService(ledger).prepare_bookkeeping_record_route(record_result["recordId"])

            self.assertTrue(result["success"])
            self.assertEqual(result["status"], "draft_prepared")
            self.assertEqual(result["operation"]["action_id"], "transaction_add")
            self.assertEqual(result["operation"]["surface"], "transactions")
            payload = result["operation"]["payload"]
            self.assertEqual(payload["amount"], 42.5)
            self.assertEqual(payload["category"], "Office Supplies")
            self.assertEqual(payload["account"], "Office Supplies")
            self.assertEqual(payload["vendor"], "Office Shop")
            routing_attempt = ledger.get_routing_attempt(result["routingAttemptId"])
            self.assertIsNone(routing_attempt["document_id"])
            self.assertEqual(routing_attempt["bookkeeping_record_id"], record_result["recordId"])
            self.assertEqual(routing_attempt["metadata"]["bookkeepingRecordId"], record_result["recordId"])
            record = ledger.get_bookkeeping_record(record_result["recordId"])
            self.assertEqual(record["status"], "export_draft_prepared")
            self.assertEqual(record["export_status"], "draft_prepared")
            self.assertEqual(record["metadata"]["latestExport"]["routingAttemptId"], result["routingAttemptId"])
            audit_actions = [event["action"] for event in ledger.list_audit_events()]
            self.assertIn("local_routing.bank_record_wave_draft_prepared", audit_actions)

    def test_prepare_ready_bookkeeping_records_routes_bank_records(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            ledger.upsert_vendor_category_rule({
                "vendorName": "Office Shop",
                "category": "Office Supplies",
                "targetSystem": "waveapps",
                "status": "approved",
            })
            transaction_id = ledger.upsert_bank_transaction({
                "accountIdentifier": "wave-checking",
                "transactionId": "tx-ready-bank-record",
                "transactionDate": "2026-06-28",
                "amount": -42.5,
                "currency": "EUR",
                "description": "Printer paper",
                "counterparty": "Office Shop",
                "reconciliationStatus": "not_started",
            })
            LocalBookkeepingRecordService(ledger, {}).upsert_from_bank_transaction(transaction_id)

            summary = LocalRoutingService(ledger).prepare_ready_bookkeeping_records()

            self.assertEqual(summary["requested"], 1)
            self.assertEqual(summary["draftPrepared"], 1)
            self.assertEqual(len(ledger.list_routing_attempts(status="draft_prepared")), 1)


if __name__ == "__main__":
    unittest.main()
