import hashlib
import io
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from src.operations.drive_wave_delivery import DriveWaveDeliveryService
from src.operations.local_api import create_app
from src.operations.local_ledger import LocalOperationsLedger


SOURCE_FOLDER = "drive-source"
ARCHIVE_FOLDER = "drive-archive"
BUSINESS_ID = "wave-business"


class FakeDriveArchiver:
    def __init__(self, source_sha256: str, size: int = 17, post_move_sha256: str = None):
        self.source_sha256 = source_sha256
        self.post_move_sha256 = post_move_sha256 or source_sha256
        self.size = size
        self.moves = []
        self.restores = []
        self.archived = False

    def inspect_file(self, file_id):
        return {
            "id": file_id,
            "name": "invoice.pdf",
            "mimeType": "application/pdf",
            "parents": [ARCHIVE_FOLDER if self.archived else SOURCE_FOLDER],
            "size": str(self.size),
            "md5Checksum": "provider-md5",
            "trashed": False,
        }

    def download_sha256(self, file_id):
        return self.post_move_sha256 if self.archived else self.source_sha256

    def move_file(self, file_id, source_folder_id, archive_folder_id):
        self.moves.append((file_id, source_folder_id, archive_folder_id))
        self.archived = True
        return {
            "status": "archived",
            "before": {"parents": [source_folder_id]},
            "after": {"parents": [archive_folder_id]},
        }

    def restore_file(self, file_id, source_folder_id, archive_folder_id):
        self.restores.append((file_id, source_folder_id, archive_folder_id))
        self.archived = False
        return {"status": "restored"}


class TestDriveWaveDeliveryService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ledger = LocalOperationsLedger(os.path.join(self.temp_dir.name, "fab.sqlite3"))
        self.source_bytes = b"synthetic invoice"
        self.source_size = len(self.source_bytes)
        self.source_hash = hashlib.sha256(self.source_bytes).hexdigest()
        source_path = os.path.join(self.temp_dir.name, "invoice.pdf")
        with open(source_path, "wb") as handle:
            handle.write(self.source_bytes)
        self.document_id = self.ledger.register_document({
            "source": "google_drive",
            "sourceDocumentId": "drive-file-1",
            "originalFilename": "invoice.pdf",
            "mimeType": "application/pdf",
            "storagePath": source_path,
            "documentType": "pdf",
            "processingStatus": "routed",
            "duplicateFingerprint": self.source_hash,
            "vendorName": "Example Vendor",
            "category": "Office Supplies",
            "transactionDate": "2026-07-22",
            "totalAmount": 121.0,
            "vatAmount": 21.0,
            "extractedData": {"invoice_number": "INV-1", "currency": "EUR"},
            "metadata": {
                "contentSha256": self.source_hash,
                "sizeBytes": self.source_size,
                "providerMetadata": {
                    "folder_id": SOURCE_FOLDER,
                    "size": str(self.source_size),
                    "md5_checksum": "provider-md5",
                },
            },
        })
        self.config = {
            "google_drive_archive_verified_files": True,
            "google_drive_folder_id": SOURCE_FOLDER,
            "google_drive_wave_archive_folder_id": ARCHIVE_FOLDER,
            "waveapps_business_id": BUSINESS_ID,
        }
        self.record_id = self.ledger.upsert_bookkeeping_record({
            "documentId": self.document_id,
            "sourceType": "document",
            "recordType": "expense",
            "status": "routed",
            "targetSystem": "waveapps_business",
            "targetAccount": "Office expenses",
            "vendorName": "Example Vendor",
            "category": "Office Supplies",
            "recordDate": "2026-07-22",
            "amount": 121.0,
            "vatAmount": 21.0,
            "currency": "EUR",
            "description": "invoice.pdf",
            "reviewRequired": False,
            "exportStatus": "executed",
        })

    def tearDown(self):
        self.temp_dir.cleanup()

    def _evidence(self, **updates):
        evidence = {
            "externalTransactionId": "wave-transaction-1",
            "businessId": BUSINESS_ID,
            "sourceSha256": self.source_hash,
            "uploadSourceSha256": self.source_hash,
            "attachmentObjectId": "wave-attachment-1",
            "attachmentMimeType": "application/pdf",
            "attachmentFilename": "invoice.pdf",
            "attachmentSizeBytes": self.source_size,
            "attachmentPresent": True,
            "attachmentOpened": True,
            "attachmentDownloaded": True,
            "attachmentTransactionId": "wave-transaction-1",
            "transactionExists": True,
            "transactionStatus": "reviewed",
            "transactionMatchCount": 1,
            "matchingTransactionIds": ["wave-transaction-1"],
            "transactionPageUrl": f"https://next.waveapps.com/{BUSINESS_ID}/transactions",
            "transactionReviewed": True,
            "waveObservedAt": datetime.now(timezone.utc).isoformat(),
            "observedFields": {
                "vendor": "Example Vendor",
                "date": "2026-07-22",
                "amount": 121.0,
                "currency": "EUR",
                "category": "Office Supplies",
                "description": "invoice.pdf",
                "invoiceNumber": "INV-1",
                "taxAmount": 21.0,
            },
            "fieldMatches": {
                "vendor": True,
                "date": True,
                "amount": True,
                "currency": True,
                "category": True,
                "description": True,
                "invoiceNumber": True,
                "taxAmount": True,
            },
        }
        evidence.update(updates)
        return evidence

    def _register_gmail_scanner_document(
        self,
        *,
        sender="eprintcenter@hp8.us",
        outside_download_root=False,
    ):
        download_root = os.path.join(self.temp_dir.name, "gmail-downloads")
        os.makedirs(download_root, exist_ok=True)
        storage_root = self.temp_dir.name if outside_download_root else download_root
        is_default = sender == "eprintcenter@hp8.us" and not outside_download_root
        source_bytes = (
            b"trusted scanner invoice"
            if is_default
            else f"scanner invoice:{sender}:{outside_download_root}".encode("utf-8")
        )
        source_hash = hashlib.sha256(source_bytes).hexdigest()
        filename = "scanner-invoice.pdf" if is_default else f"scanner-{source_hash[:8]}.pdf"
        source_path = os.path.join(storage_root, filename)
        with open(source_path, "wb") as handle:
            handle.write(source_bytes)
        document_id = self.ledger.register_document({
            "source": "gmail",
            "sourceDocumentId": f"sha256:{source_hash}",
            "originalFilename": filename,
            "mimeType": "application/pdf",
            "storagePath": source_path,
            "documentType": "pdf",
            "processingStatus": "routed",
            "duplicateFingerprint": source_hash,
            "vendorName": "Example Vendor",
            "category": "Office Supplies",
            "transactionDate": "2026-07-22",
            "totalAmount": 121.0,
            "vatAmount": 21.0,
            "extractedData": {"invoice_number": "INV-1", "currency": "EUR"},
            "metadata": {
                "contentSha256": source_hash,
                "sizeBytes": len(source_bytes),
                "providerMetadata": {
                    "sender_address": sender,
                    "message_id": "gmail-message-1",
                    "attachment_id": "gmail-attachment-1",
                    "scanner_profile": "hp_eprint",
                    "scanner_policy_verified": True,
                    "delivery_path": "gmail_to_fab_direct",
                },
            },
        })
        self.ledger.upsert_bookkeeping_record({
            "documentId": document_id,
            "sourceType": "document",
            "recordType": "expense",
            "status": "routed",
            "targetSystem": "waveapps_business",
            "targetAccount": "Office expenses",
            "vendorName": "Example Vendor",
            "category": "Office Supplies",
            "recordDate": "2026-07-22",
            "amount": 121.0,
            "vatAmount": 21.0,
            "currency": "EUR",
            "description": "invoice.pdf",
            "reviewRequired": False,
        })
        config = {
            **self.config,
            "gmail_scanner_mode": True,
            "gmail_trusted_senders": "eprintcenter@hp8.us",
            "gmail_attachment_download_dir": download_root,
        }
        return document_id, source_path, source_bytes, source_hash, config

    def test_drive_credential_rotation_blocks_archive_until_fresh_consent(self):
        token_path = os.path.join(self.temp_dir.name, "drive-token.pickle")
        for path in (token_path, f"{token_path}.reauthorize"):
            with open(path, "wb") as handle:
                handle.write(b"configured")
        config = {**self.config, "google_drive_token_file": token_path}
        service = DriveWaveDeliveryService(self.ledger, config)

        status = service.status()
        plan = service.plan_archive(self.document_id)

        self.assertEqual(status["status"], "needs_authorization")
        self.assertTrue(status["driveReauthorizationRequired"])
        self.assertFalse(plan["canArchive"])
        self.assertIn("drive_reauthorization_required", plan["reasons"])

    def test_transaction_presence_without_attachment_proof_never_archives(self):
        archiver = FakeDriveArchiver(self.source_hash, self.source_size)
        service = DriveWaveDeliveryService(self.ledger, self.config, drive_archiver=archiver)

        plan = service.plan_archive(self.document_id)
        result = service.archive_document(self.document_id)

        self.assertFalse(plan["canArchive"])
        self.assertIn("wave_attachment_evidence_missing", plan["reasons"])
        self.assertFalse(result["success"])
        self.assertEqual(archiver.moves, [])
        document = self.ledger.get_document(self.document_id)
        self.assertEqual(document["review_items"][0]["reason"], "drive_wave_archive_blocked")

    def test_archive_folder_must_not_equal_intake_folder(self):
        config = {
            **self.config,
            "google_drive_wave_archive_folder_id": SOURCE_FOLDER,
        }
        service = DriveWaveDeliveryService(self.ledger, config)

        status = service.status()
        plan = service.plan_archive(self.document_id)

        self.assertEqual(status["status"], "needs_configuration")
        self.assertFalse(status["foldersDistinct"])
        self.assertFalse(plan["canArchive"])
        self.assertIn("archive_folder_matches_source_folder", plan["reasons"])

    def test_work_order_binds_source_wave_fields_and_evidence_contract(self):
        record_id = self.ledger.upsert_bookkeeping_record({
            "documentId": self.document_id,
            "sourceType": "document",
            "recordType": "expense",
            "status": "routed",
            "targetSystem": "waveapps_business",
            "targetAccount": "Office expenses",
            "vendorName": "Example Vendor",
            "category": "Office Supplies",
            "recordDate": "2026-07-22",
            "amount": 121.0,
            "vatAmount": 21.0,
            "currency": "EUR",
            "description": "Printer paper",
            "reviewRequired": False,
            "exportStatus": "executed",
        })
        self.ledger.replace_bookkeeping_record_line_items(record_id, [{
            "itemName": "Printer paper",
            "quantity": 1,
            "amount": 100.0,
            "taxAmount": 21.0,
            "taxRate": 21.0,
            "accountName": "Office expenses",
        }])
        self.ledger.upsert_export_attempt({
            "bookkeepingRecordId": record_id,
            "documentId": self.document_id,
            "targetSystem": "waveapps_business",
            "actionId": "transaction_add",
            "operationId": "wave-operation-1",
            "status": "executed",
            "externalSubmission": "executed",
            "externalId": "wave-transaction-1",
        })
        service = DriveWaveDeliveryService(self.ledger, self.config)

        result = service.list_work_orders(limit=10)
        order = result["workOrders"][0]

        self.assertEqual(result["workOrderVersion"], "fab-source-wave-work-order-v3")
        self.assertEqual(result["summary"]["needsAttachmentVerification"], 1)
        self.assertEqual(order["stage"], "upload_and_verify_attachment")
        self.assertEqual(order["source"]["fileId"], "drive-file-1")
        self.assertEqual(order["source"]["sha256"], self.source_hash)
        self.assertEqual(order["wave"]["businessId"], BUSINESS_ID)
        self.assertEqual(order["wave"]["externalTransactionId"], "wave-transaction-1")
        self.assertEqual(order["wave"]["expectedFields"]["amount"], 121.0)
        self.assertEqual(order["wave"]["lineItems"][0]["item_name"], "Printer paper")
        self.assertEqual(
            order["evidence"]["submission"]["path"],
            f"/api/drive-wave/documents/{self.document_id}/attachment-evidence",
        )
        self.assertEqual(order["evidence"]["template"]["sourceSha256"], self.source_hash)
        self.assertFalse(order["evidence"]["template"]["attachmentPresent"])
        self.assertIn("observedFields", order["evidence"]["template"])
        self.assertTrue(result["evidencePolicy"]["serverComputedFieldMatches"])
        self.assertTrue(result["evidencePolicy"]["uniqueWaveTransactionRequired"])
        self.assertTrue(result["evidencePolicy"]["attachmentTransactionBindingRequired"])
        self.assertTrue(result["evidencePolicy"]["postMoveHashVerificationRequired"])
        self.assertTrue(order["browserExecution"]["requiredReadback"]["serverComputedSha256MustMatchSource"])
        self.assertEqual(
            order["evidence"]["binaryReadbackSubmission"]["path"],
            f"/api/drive-wave/documents/{self.document_id}/attachment-readback",
        )
        self.assertNotIn("ocr_text", str(order))

    def test_list_work_orders_uses_batched_delivery_context(self):
        service = DriveWaveDeliveryService(self.ledger, self.config)

        with (
            patch.object(
                self.ledger,
                "get_document",
                side_effect=AssertionError("per-document detail lookup"),
            ),
            patch.object(
                self.ledger,
                "get_bookkeeping_record_by_document",
                side_effect=AssertionError("per-document record lookup"),
            ),
            patch.object(
                self.ledger,
                "list_export_attempts",
                side_effect=AssertionError("per-document export lookup"),
            ),
            patch.object(
                self.ledger,
                "find_audit_event",
                side_effect=AssertionError("per-document evidence lookup"),
            ),
        ):
            result = service.list_work_orders(limit=10)

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["workOrders"][0]["documentId"], self.document_id)
        self.assertEqual(
            result["workOrders"][0]["wave"]["expectedFields"]["amount"],
            121.0,
        )

    def test_trusted_gmail_scanner_source_gets_evidence_bound_wave_work_order(self):
        document_id, source_path, source_bytes, source_hash, config = (
            self._register_gmail_scanner_document()
        )
        service = DriveWaveDeliveryService(self.ledger, config)

        result = service.list_work_orders(limit=10)
        order = next(
            item for item in result["workOrders"]
            if item["documentId"] == document_id
        )

        self.assertEqual(order["source"]["provider"], "gmail")
        self.assertEqual(order["source"]["messageId"], "gmail-message-1")
        self.assertEqual(order["source"]["attachmentId"], "gmail-attachment-1")
        self.assertEqual(order["source"]["scannerProfile"], "hp_eprint")
        self.assertEqual(order["source"]["sha256"], source_hash)
        self.assertTrue(os.path.isfile(source_path))
        self.assertFalse(order["evidence"]["binaryReadbackSubmission"]["requiredForArchive"])
        self.assertTrue(order["evidence"]["binaryReadbackSubmission"]["requiredForCompletion"])
        self.assertEqual(
            order["source"]["retention"]["policy"],
            "email_unchanged_local_evidence_retained",
        )
        self.assertEqual(order["archivePlan"]["status"], "not_applicable")
        self.assertFalse(order["archivePlan"]["evidenceVerified"])
        self.assertEqual(order["stage"], "locate_or_create_transaction")

    def test_gmail_scanner_completes_only_after_exact_wave_attachment_readback(self):
        document_id, source_path, source_bytes, source_hash, config = (
            self._register_gmail_scanner_document()
        )
        service = DriveWaveDeliveryService(self.ledger, config)
        evidence = self._evidence(
            sourceSha256=source_hash,
            uploadSourceSha256=source_hash,
            attachmentFilename="scanner-invoice.pdf",
            attachmentSizeBytes=len(source_bytes),
        )

        verification = service.record_attachment_readback(
            document_id,
            source_bytes,
            filename="scanner-invoice.pdf",
            mime_type="application/pdf",
            evidence=evidence,
            actor="hai-browser",
        )
        order = service.work_order(document_id)
        archive_attempt = service.archive_document(document_id)

        self.assertTrue(verification["success"])
        self.assertEqual(order["stage"], "completed")
        self.assertTrue(order["archivePlan"]["evidenceVerified"])
        self.assertEqual(order["archivePlan"]["retentionStatus"], "verified")
        self.assertEqual(archive_attempt["status"], "not_applicable")
        self.assertFalse(archive_attempt["success"])
        self.assertEqual(archive_attempt["reasons"], [])
        self.assertTrue(os.path.isfile(source_path))
        with open(source_path, "rb") as handle:
            self.assertEqual(handle.read(), source_bytes)
        document = self.ledger.get_document(document_id)
        self.assertEqual(document["review_items"], [])
        self.assertEqual(
            document["metadata"]["waveDeliveryLifecycle"]["status"],
            "attachment_verified",
        )

    def test_gmail_scanner_work_orders_reject_untrusted_sender_and_escaped_path(self):
        untrusted_id, _, _, _, config = self._register_gmail_scanner_document(
            sender="attacker@example.com",
        )
        escaped_id, _, _, _, _ = self._register_gmail_scanner_document(
            outside_download_root=True,
        )
        service = DriveWaveDeliveryService(self.ledger, config)

        result = service.list_work_orders(limit=10)

        listed_ids = {item["documentId"] for item in result["workOrders"]}
        self.assertNotIn(untrusted_id, listed_ids)
        self.assertNotIn(escaped_id, listed_ids)
        self.assertEqual(
            service.work_order(untrusted_id)["status"],
            "outside_configured_source",
        )
        self.assertEqual(
            service.record_attachment_readback(
                escaped_id,
                b"trusted scanner invoice",
                filename="scanner-invoice.pdf",
                mime_type="application/pdf",
                evidence={},
            )["status"],
            "outside_configured_source",
        )

    def test_work_order_never_queues_a_missing_local_source_for_upload(self):
        self.ledger.upsert_bookkeeping_record({
            "documentId": self.document_id,
            "status": "routed",
            "targetSystem": "waveapps_business",
            "reviewRequired": False,
        })
        document = self.ledger.get_document(self.document_id)
        os.remove(document["storage_path"])

        result = DriveWaveDeliveryService(self.ledger, self.config).work_order(self.document_id)

        self.assertEqual(result["stage"], "source_file_unavailable")
        self.assertFalse(result["source"]["localAvailable"])
        self.assertIn("Restore or re-download", result["actionRequired"])

    def test_mismatched_attachment_hash_is_rejected(self):
        service = DriveWaveDeliveryService(self.ledger, self.config)
        result = service.record_attachment_evidence(
            self.document_id,
            self._evidence(attachmentSha256="0" * 64),
        )

        self.assertFalse(result["success"])
        self.assertIn("wave_attachment_hash_mismatch", result["reasons"])
        self.assertIn("wave_attachment_readback_bytes_missing", result["reasons"])
        self.assertIsNone(
            self.ledger.find_audit_event(
                "drive_wave.attachment_verified",
                "bookkeeping_document",
                str(self.document_id),
            )
        )

    def test_verified_upload_chain_moves_same_provider_file_id_without_delete(self):
        archiver = FakeDriveArchiver(self.source_hash, self.source_size)
        service = DriveWaveDeliveryService(self.ledger, self.config, drive_archiver=archiver)

        verification = service.record_attachment_readback(
            self.document_id,
            self.source_bytes,
            filename="invoice.pdf",
            mime_type="application/pdf",
            evidence=self._evidence(),
            actor="hai-browser",
        )
        archived = service.archive_document(self.document_id, actor="local-worker")

        self.assertTrue(verification["success"])
        self.assertEqual(verification["verificationMethod"], "hash_round_trip")
        self.assertTrue(archived["success"])
        self.assertEqual(archived["deletion"], "not_performed")
        self.assertTrue(archived["postMoveVerified"])
        self.assertEqual(archived["postMoveSha256"], self.source_hash)
        self.assertEqual(archiver.moves, [("drive-file-1", SOURCE_FOLDER, ARCHIVE_FOLDER)])
        document = self.ledger.get_document(self.document_id)
        lifecycle = document["metadata"]["driveWaveLifecycle"]
        self.assertEqual(lifecycle["status"], "archived")
        self.assertEqual(lifecycle["attachmentObjectId"], "wave-attachment-1")

    def test_current_drive_bytes_must_still_match_intake_hash(self):
        archiver = FakeDriveArchiver("f" * 64, self.source_size)
        service = DriveWaveDeliveryService(self.ledger, self.config, drive_archiver=archiver)
        service.record_attachment_readback(
            self.document_id,
            self.source_bytes,
            filename="invoice.pdf",
            mime_type="application/pdf",
            evidence=self._evidence(),
        )

        archived = service.archive_document(self.document_id)

        self.assertFalse(archived["success"])
        self.assertIn("Drive source content changed", archived["reasons"][0])
        self.assertEqual(archiver.moves, [])

    def test_fresh_evidence_resolves_a_prior_archive_block(self):
        archiver = FakeDriveArchiver(self.source_hash, self.source_size)
        service = DriveWaveDeliveryService(self.ledger, self.config, drive_archiver=archiver)
        service.archive_document(self.document_id)

        recorded = service.record_attachment_readback(
            self.document_id,
            self.source_bytes,
            filename="invoice.pdf",
            mime_type="application/pdf",
            evidence=self._evidence(),
        )
        reviews = self.ledger.list_review_items(document_id=self.document_id)

        self.assertTrue(recorded["success"])
        self.assertTrue(recorded["archivePlan"]["canArchive"])
        self.assertEqual(reviews[0]["reason"], "drive_wave_archive_blocked")
        self.assertEqual(reviews[0]["status"], "resolved")

    def test_stale_wave_readback_never_authorizes_a_drive_move(self):
        archiver = FakeDriveArchiver(self.source_hash, self.source_size)
        service = DriveWaveDeliveryService(self.ledger, self.config, drive_archiver=archiver)
        service.record_attachment_readback(
            self.document_id,
            self.source_bytes,
            filename="invoice.pdf",
            mime_type="application/pdf",
            evidence=self._evidence(),
        )
        with self.ledger._connection() as connection:
            connection.execute(
                "UPDATE audit_events SET created_at = ? WHERE action = ? AND entity_id = ?",
                ("2000-01-01T00:00:00Z", "drive_wave.attachment_verified", str(self.document_id)),
            )

        plan = service.plan_archive(self.document_id)
        archived = service.archive_document(self.document_id)

        self.assertFalse(plan["canArchive"])
        self.assertIn("wave_attachment_verification_stale", plan["reasons"])
        self.assertFalse(archived["success"])
        self.assertEqual(archiver.moves, [])

    def test_metadata_attestation_cannot_replace_binary_readback(self):
        config = {
            **self.config,
            "fab_local_ledger_path": self.ledger.path,
            "fab_hai_connector_enabled": True,
            "fab_hai_allowed_commands": "record_wave_attachment_verification,archive_verified_drive_sources",
        }
        client = create_app(config).test_client()

        recorded = client.post("/api/hai/commands/execute", json={
            "requestId": "drive-wave-evidence-1",
            "commandId": "record_wave_attachment_verification",
            "actor": "hai-browser",
            "payload": {
                "documentId": self.document_id,
                "evidence": self._evidence(),
            },
        })
        planned = client.post("/api/hai/commands/execute", json={
            "requestId": "drive-wave-archive-plan-1",
            "commandId": "archive_verified_drive_sources",
            "actor": "hai-browser",
            "payload": {"limit": 10, "dryRun": True},
        })

        self.assertEqual(recorded.status_code, 200)
        self.assertEqual(recorded.get_json()["result"]["status"], "blocked")
        self.assertIn(
            "wave_attachment_readback_bytes_missing",
            recorded.get_json()["result"]["reasons"],
        )
        self.assertEqual(planned.status_code, 200)
        self.assertEqual(planned.get_json()["result"]["status"], "planned")
        self.assertEqual(planned.get_json()["result"]["ready"], 0)

    def test_multipart_readback_computes_hash_inside_fab(self):
        client = create_app({**self.config, "fab_local_ledger_path": self.ledger.path}).test_client()
        response = client.post(
            f"/api/drive-wave/documents/{self.document_id}/attachment-readback",
            data={
                "evidence": json.dumps(self._evidence(attachmentSha256="0" * 64)),
                "actor": "hai-wave-browser",
                "attachment": (io.BytesIO(self.source_bytes), "invoice.pdf"),
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        result = response.get_json()
        self.assertTrue(result["success"])
        self.assertEqual(result["verificationMethod"], "hash_round_trip")
        event = self.ledger.find_audit_event(
            "drive_wave.attachment_verified",
            "bookkeeping_document",
            str(self.document_id),
        )
        self.assertTrue(event["details"]["attachmentReadbackVerified"])
        self.assertEqual(event["details"]["attachmentSha256"], self.source_hash)

    def test_readback_filename_and_size_must_match_source(self):
        service = DriveWaveDeliveryService(self.ledger, self.config)

        wrong_name = service.record_attachment_readback(
            self.document_id,
            self.source_bytes,
            filename="another.pdf",
            mime_type="application/pdf",
            evidence=self._evidence(),
        )
        wrong_bytes = service.record_attachment_readback(
            self.document_id,
            self.source_bytes + b"changed",
            filename="invoice.pdf",
            mime_type="application/pdf",
            evidence=self._evidence(),
        )

        self.assertIn("wave_attachment_filename_mismatch", wrong_name["reasons"])
        self.assertIn("wave_attachment_hash_mismatch", wrong_bytes["reasons"])
        self.assertIn("wave_attachment_size_mismatch", wrong_bytes["reasons"])

    def test_readback_computes_field_matches_from_observed_values(self):
        service = DriveWaveDeliveryService(self.ledger, self.config)
        evidence = self._evidence()
        evidence["observedFields"]["amount"] = 120.0
        evidence["fieldMatches"] = {
            field: True
            for field in (
                "vendor", "date", "amount", "currency", "category",
                "description", "invoiceNumber", "taxAmount",
            )
        }

        result = service.record_attachment_readback(
            self.document_id,
            self.source_bytes,
            filename="invoice.pdf",
            mime_type="application/pdf",
            evidence=evidence,
        )

        self.assertFalse(result["success"])
        self.assertIn("wave_field_mismatch:amount", result["reasons"])

    def test_bookkeeping_field_change_invalidates_prior_readback(self):
        service = DriveWaveDeliveryService(self.ledger, self.config)
        recorded = service.record_attachment_readback(
            self.document_id,
            self.source_bytes,
            filename="invoice.pdf",
            mime_type="application/pdf",
            evidence=self._evidence(),
        )
        self.ledger.update_bookkeeping_record(
            self.record_id,
            {"category": "Computer equipment"},
        )

        plan = service.plan_archive(self.document_id)

        self.assertTrue(recorded["success"])
        self.assertFalse(plan["canArchive"])
        self.assertIn("wave_expected_fields_changed_or_unbound", plan["reasons"])
        self.assertIn("wave_field_mismatch:category", plan["reasons"])

    def test_wave_entry_must_be_unique_finished_and_bound_to_attachment(self):
        service = DriveWaveDeliveryService(self.ledger, self.config)
        cases = (
            ({"transactionExists": False}, "wave_transaction_missing"),
            ({"transactionMatchCount": 2, "matchingTransactionIds": ["wave-transaction-1", "wave-transaction-2"]}, "wave_transaction_match_not_unique"),
            ({"transactionStatus": "pending"}, "wave_transaction_not_finished"),
            ({"attachmentTransactionId": "wave-transaction-2"}, "wave_attachment_transaction_mismatch"),
            ({"waveObservedAt": "2000-01-01T00:00:00Z"}, "wave_observation_stale_or_missing"),
            ({"uploadSourceSha256": "0" * 64}, "wave_upload_source_hash_mismatch"),
        )

        for updates, expected_reason in cases:
            with self.subTest(expected_reason=expected_reason):
                result = service.record_attachment_readback(
                    self.document_id,
                    self.source_bytes,
                    filename="invoice.pdf",
                    mime_type="application/pdf",
                    evidence=self._evidence(**updates),
                )
                self.assertFalse(result["success"])
                self.assertIn(expected_reason, result["reasons"])

    def test_incomplete_source_identity_never_authorizes_archive(self):
        document = self.ledger.get_document(self.document_id)
        metadata = dict(document["metadata"])
        metadata.pop("sizeBytes", None)
        metadata["providerMetadata"] = {
            "folder_id": SOURCE_FOLDER,
            "md5_checksum": "provider-md5",
        }
        self.ledger.update_document(self.document_id, {"metadata": metadata})
        service = DriveWaveDeliveryService(self.ledger, self.config)

        verification = service.record_attachment_readback(
            self.document_id,
            self.source_bytes,
            filename="invoice.pdf",
            mime_type="application/pdf",
            evidence=self._evidence(),
        )
        plan = service.plan_archive(self.document_id)

        self.assertTrue(verification["success"])
        self.assertFalse(plan["canArchive"])
        self.assertIn("source_size_missing", plan["reasons"])

    def test_post_move_hash_failure_restores_source_and_never_marks_archived(self):
        archiver = FakeDriveArchiver(
            self.source_hash,
            self.source_size,
            post_move_sha256="f" * 64,
        )
        service = DriveWaveDeliveryService(self.ledger, self.config, drive_archiver=archiver)
        service.record_attachment_readback(
            self.document_id,
            self.source_bytes,
            filename="invoice.pdf",
            mime_type="application/pdf",
            evidence=self._evidence(),
        )

        result = service.archive_document(self.document_id)

        self.assertFalse(result["success"])
        self.assertIn("content hash verification failed", result["reasons"][0])
        self.assertEqual(archiver.restores, [("drive-file-1", SOURCE_FOLDER, ARCHIVE_FOLDER)])
        self.assertFalse(archiver.archived)
        lifecycle = self.ledger.get_document(self.document_id)["metadata"]["driveWaveLifecycle"]
        self.assertEqual(lifecycle["status"], "attachment_verified")

    def test_archive_lease_prevents_concurrent_moves(self):
        archiver = FakeDriveArchiver(self.source_hash, self.source_size)
        service = DriveWaveDeliveryService(self.ledger, self.config, drive_archiver=archiver)
        service.record_attachment_readback(
            self.document_id,
            self.source_bytes,
            filename="invoice.pdf",
            mime_type="application/pdf",
            evidence=self._evidence(),
        )
        lease_name = f"drive-wave-archive:{self.document_id}"
        self.ledger.acquire_runtime_lease(lease_name, "other-worker", ttl_seconds=60)

        try:
            result = service.archive_document(self.document_id)
        finally:
            self.ledger.release_runtime_lease(lease_name, "other-worker")

        self.assertFalse(result["success"])
        self.assertIn("archive_operation_already_in_progress", result["reasons"])
        self.assertEqual(archiver.moves, [])

    def test_review_in_progress_blocks_archive(self):
        review_id = self.ledger.create_review_item({
            "documentId": self.document_id,
            "reason": "operator_check",
            "details": "Operator is actively reviewing this record.",
        })
        self.ledger.resolve_review_item(review_id, status="in_review")
        service = DriveWaveDeliveryService(self.ledger, self.config)
        service.record_attachment_readback(
            self.document_id,
            self.source_bytes,
            filename="invoice.pdf",
            mime_type="application/pdf",
            evidence=self._evidence(),
        )

        plan = service.plan_archive(self.document_id)

        self.assertFalse(plan["canArchive"])
        self.assertIn("open_review_item", plan["reasons"])

    def test_api_and_hai_manifest_expose_read_only_attachment_work_orders(self):
        self.ledger.upsert_bookkeeping_record({
            "documentId": self.document_id,
            "status": "routed",
            "targetSystem": "waveapps_business",
            "reviewRequired": False,
        })
        config = {
            **self.config,
            "fab_local_ledger_path": self.ledger.path,
            "fab_hai_connector_enabled": True,
        }
        client = create_app(config).test_client()

        listed = client.get("/api/drive-wave/work-orders?limit=10")
        document_order = client.get(
            f"/api/drive-wave/documents/{self.document_id}/work-order"
        )
        manifest = client.get("/api/hai/manifest")

        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.get_json()["count"], 1)
        self.assertEqual(document_order.status_code, 200)
        self.assertEqual(document_order.get_json()["documentId"], self.document_id)
        self.assertEqual(manifest.status_code, 200)
        resources = {
            item["resourceId"]: item for item in manifest.get_json()["resources"]
        }
        resource = resources["wave_attachment_work_orders"]
        self.assertEqual(resource["resourceId"], "wave_attachment_work_orders")
        self.assertEqual(resource["path"], "/api/drive-wave/work-orders")
        self.assertEqual(resource["externalSubmission"], "not_executed")
        self.assertEqual(
            resources["wave_attachment_binary_readback"]["pathTemplate"],
            "/api/drive-wave/documents/{documentId}/attachment-readback",
        )


if __name__ == "__main__":
    unittest.main()
