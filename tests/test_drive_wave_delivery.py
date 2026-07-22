import hashlib
import os
import tempfile
import unittest

from src.operations.drive_wave_delivery import DriveWaveDeliveryService
from src.operations.local_api import create_app
from src.operations.local_ledger import LocalOperationsLedger


SOURCE_FOLDER = "drive-source"
ARCHIVE_FOLDER = "drive-archive"
BUSINESS_ID = "wave-business"


class FakeDriveArchiver:
    def __init__(self, source_sha256: str, size: int = 17):
        self.source_sha256 = source_sha256
        self.size = size
        self.moves = []

    def inspect_file(self, file_id):
        return {
            "id": file_id,
            "parents": [SOURCE_FOLDER],
            "size": str(self.size),
            "md5Checksum": "provider-md5",
            "trashed": False,
        }

    def download_sha256(self, file_id):
        return self.source_sha256

    def move_file(self, file_id, source_folder_id, archive_folder_id):
        self.moves.append((file_id, source_folder_id, archive_folder_id))
        return {
            "status": "archived",
            "before": {"parents": [source_folder_id]},
            "after": {"parents": [archive_folder_id]},
        }


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
            "attachmentPresent": True,
            "attachmentOpened": True,
            "transactionReviewed": True,
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

        self.assertEqual(result["workOrderVersion"], "fab-drive-wave-work-order-v1")
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
        self.assertNotIn("ocr_text", str(order))

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

        verification = service.record_attachment_evidence(
            self.document_id,
            self._evidence(),
            actor="hai-browser",
        )
        archived = service.archive_document(self.document_id, actor="local-worker")

        self.assertTrue(verification["success"])
        self.assertEqual(verification["verificationMethod"], "source_hash_and_provider_readback")
        self.assertTrue(archived["success"])
        self.assertEqual(archived["deletion"], "not_performed")
        self.assertEqual(archiver.moves, [("drive-file-1", SOURCE_FOLDER, ARCHIVE_FOLDER)])
        document = self.ledger.get_document(self.document_id)
        lifecycle = document["metadata"]["driveWaveLifecycle"]
        self.assertEqual(lifecycle["status"], "archived")
        self.assertEqual(lifecycle["attachmentObjectId"], "wave-attachment-1")

    def test_current_drive_bytes_must_still_match_intake_hash(self):
        archiver = FakeDriveArchiver("f" * 64, self.source_size)
        service = DriveWaveDeliveryService(self.ledger, self.config, drive_archiver=archiver)
        service.record_attachment_evidence(self.document_id, self._evidence())

        archived = service.archive_document(self.document_id)

        self.assertFalse(archived["success"])
        self.assertIn("Drive source content changed", archived["reasons"][0])
        self.assertEqual(archiver.moves, [])

    def test_fresh_evidence_resolves_a_prior_archive_block(self):
        archiver = FakeDriveArchiver(self.source_hash, self.source_size)
        service = DriveWaveDeliveryService(self.ledger, self.config, drive_archiver=archiver)
        service.archive_document(self.document_id)

        recorded = service.record_attachment_evidence(self.document_id, self._evidence())
        reviews = self.ledger.list_review_items(document_id=self.document_id)

        self.assertTrue(recorded["success"])
        self.assertTrue(recorded["archivePlan"]["canArchive"])
        self.assertEqual(reviews[0]["reason"], "drive_wave_archive_blocked")
        self.assertEqual(reviews[0]["status"], "resolved")

    def test_stale_wave_readback_never_authorizes_a_drive_move(self):
        archiver = FakeDriveArchiver(self.source_hash, self.source_size)
        service = DriveWaveDeliveryService(self.ledger, self.config, drive_archiver=archiver)
        service.record_attachment_evidence(self.document_id, self._evidence())
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

    def test_hai_can_record_evidence_but_archive_remains_policy_gated(self):
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
        self.assertEqual(recorded.get_json()["result"]["status"], "verified")
        self.assertEqual(planned.status_code, 200)
        self.assertEqual(planned.get_json()["result"]["status"], "planned")
        self.assertEqual(planned.get_json()["result"]["ready"], 1)

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
        resource = manifest.get_json()["resources"][0]
        self.assertEqual(resource["resourceId"], "wave_attachment_work_orders")
        self.assertEqual(resource["path"], "/api/drive-wave/work-orders")
        self.assertEqual(resource["externalSubmission"], "not_executed")


if __name__ == "__main__":
    unittest.main()
