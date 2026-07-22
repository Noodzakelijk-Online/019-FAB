from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.document_fetchers.drive_archiver import DriveArchiveClient
from src.operations.local_ledger import LocalOperationsLedger


EVIDENCE_ACTION = "drive_wave.attachment_verified"
ARCHIVE_ACTION = "drive_wave.source_archived"
REQUIRED_FIELD_MATCHES = ("vendor", "date", "amount", "currency", "category", "description")
TERMINAL_EXPORT_STATUSES = {"executed", "submitted"}
OPEN_REVIEW_STATUSES = {"pending", "open", "needs_review", "in_progress"}


class DriveWaveDeliveryService:
    """Close the Drive-to-Wave loop without treating transaction presence as file proof."""

    def __init__(
        self,
        ledger: LocalOperationsLedger,
        config: Optional[Dict[str, Any]] = None,
        drive_archiver: Optional[DriveArchiveClient] = None,
    ):
        self.ledger = ledger
        self.config = config or {}
        self.drive_archiver = drive_archiver

    def status(self) -> Dict[str, Any]:
        source_folder_id = self._source_folder_id()
        archive_folder_id = self._archive_folder_id()
        business_id = self._business_id()
        enabled = self._archive_enabled()
        token_path = str(
            _first(self.config, "google_drive_token_file", "drive_token_path")
            or "tokens/drive_token.pickle"
        )
        credentials_path = str(
            _first(self.config, "google_drive_credentials_file", "drive_credentials_path")
            or "credentials/drive_credentials.json"
        )
        token_present = os.path.isfile(os.path.abspath(os.path.expanduser(token_path)))
        credentials_present = os.path.isfile(os.path.abspath(os.path.expanduser(credentials_path)))
        configured = enabled and bool(source_folder_id) and bool(archive_folder_id) and bool(business_id)
        return {
            "status": "ready" if configured and token_present else "needs_authorization" if configured else "needs_configuration",
            "archiveEnabled": enabled,
            "sourceFolderConfigured": bool(source_folder_id),
            "archiveFolderConfigured": bool(archive_folder_id),
            "waveBusinessConfigured": bool(business_id),
            "driveTokenPresent": token_present,
            "driveCredentialsPresent": credentials_present,
            "driveScopeVerification": "checked_on_archive",
            "verificationPolicy": "source_hash_and_provider_readback",
            "deletionPolicy": "never_delete_move_only",
            "externalSubmission": "policy_gated",
        }

    def list_candidates(self, limit: int = 100) -> Dict[str, Any]:
        documents = [
            document
            for document in self.ledger.list_documents(limit=limit)
            if self._is_configured_source(document)
        ]
        candidates = []
        for document in documents:
            plan = self.plan_archive(int(document["id"]))
            candidates.append({
                "documentId": document["id"],
                "sourceDocumentId": document.get("source_document_id"),
                "filename": document.get("original_filename"),
                "storagePath": document.get("storage_path"),
                "sourceSha256": _source_sha256(document),
                "processingStatus": document.get("processing_status"),
                "archivePlan": plan,
            })
        return {
            "status": "ready",
            "count": len(candidates),
            "candidates": candidates,
            "externalSubmission": "not_executed",
        }

    def record_attachment_evidence(
        self,
        document_id: int,
        evidence: Dict[str, Any],
        actor: str = "hai",
    ) -> Dict[str, Any]:
        document = self.ledger.get_document(int(document_id))
        if not document:
            return {"success": False, "status": "not_found", "reasons": ["document_not_found"]}
        normalized = _normalize_evidence(evidence)
        reasons = self._evidence_reasons(document, normalized)
        evidence_digest = _digest(normalized)
        if reasons:
            audit_event_id = self.ledger.record_audit_event({
                "action": "drive_wave.attachment_verification_rejected",
                "entityType": "bookkeeping_document",
                "entityId": str(document_id),
                "details": {
                    "actor": actor,
                    "reasons": reasons,
                    "evidenceDigest": evidence_digest,
                    "externalTransactionId": normalized.get("externalTransactionId"),
                    "externalSubmission": "not_executed",
                },
            })
            return {
                "success": False,
                "status": "blocked",
                "reasons": reasons,
                "auditEventId": audit_event_id,
                "externalSubmission": "not_executed",
            }

        verification_method = (
            "hash_round_trip"
            if normalized.get("attachmentSha256")
            else "source_hash_and_provider_readback"
        )
        normalized.update({
            "actor": str(actor or "hai")[:200],
            "evidenceDigest": evidence_digest,
            "verificationMethod": verification_method,
            "verifiedAt": _now(),
        })
        audit_event_id = self.ledger.record_audit_event({
            "action": EVIDENCE_ACTION,
            "entityType": "bookkeeping_document",
            "entityId": str(document_id),
            "details": normalized,
        })
        metadata = dict(document.get("metadata") or {})
        lifecycle = dict(metadata.get("driveWaveLifecycle") or {})
        lifecycle.update({
            "status": "attachment_verified",
            "verifiedAt": normalized["verifiedAt"],
            "verificationMethod": verification_method,
            "evidenceDigest": evidence_digest,
            "externalTransactionId": normalized["externalTransactionId"],
            "attachmentObjectId": normalized["attachmentObjectId"],
        })
        metadata["driveWaveLifecycle"] = lifecycle
        self.ledger.update_document(int(document_id), {"metadata": metadata})
        self._resolve_archive_review_items(int(document_id), actor, evidence_digest)
        return {
            "success": True,
            "status": "verified",
            "verificationMethod": verification_method,
            "auditEventId": audit_event_id,
            "archivePlan": self.plan_archive(int(document_id)),
            "externalSubmission": "verified_readback",
        }

    def plan_archive(self, document_id: int) -> Dict[str, Any]:
        document = self.ledger.get_document(int(document_id))
        if not document:
            return {"status": "blocked", "canArchive": False, "reasons": ["document_not_found"]}
        metadata = document.get("metadata") or {}
        lifecycle = metadata.get("driveWaveLifecycle") if isinstance(metadata.get("driveWaveLifecycle"), dict) else {}
        if lifecycle.get("status") == "archived":
            return {
                "status": "already_archived",
                "canArchive": False,
                "reasons": [],
                "archiveFolderId": lifecycle.get("archiveFolderId"),
                "externalTransactionId": lifecycle.get("externalTransactionId"),
            }

        reasons = self._document_reasons(document)
        evidence_event = self.ledger.find_audit_event(
            EVIDENCE_ACTION,
            "bookkeeping_document",
            str(document_id),
        )
        evidence = (evidence_event or {}).get("details") or {}
        if not evidence:
            reasons.append("wave_attachment_evidence_missing")
        else:
            reasons.extend(self._evidence_reasons(document, evidence))
            if not _timestamp_is_fresh(
                evidence_event.get("created_at"),
                self._evidence_max_age_seconds(),
            ):
                reasons.append("wave_attachment_verification_stale")
            exports = self.ledger.list_export_attempts(document_id=int(document_id), limit=5)
            terminal_exports = [item for item in exports if str(item.get("status") or "").lower() in TERMINAL_EXPORT_STATUSES]
            if terminal_exports:
                external_id = str(terminal_exports[0].get("external_id") or "")
                if external_id and external_id != str(evidence.get("externalTransactionId") or ""):
                    reasons.append("wave_transaction_id_mismatch")
                target = str(terminal_exports[0].get("target_system") or "")
                if target and target != "waveapps_business":
                    reasons.append("wave_target_is_not_business")

        reasons = sorted(set(reasons))
        return {
            "status": "ready" if not reasons else "blocked",
            "canArchive": not reasons,
            "reasons": reasons,
            "sourceFolderId": self._source_folder_id(),
            "archiveFolderId": self._archive_folder_id(),
            "externalTransactionId": evidence.get("externalTransactionId"),
            "attachmentObjectId": evidence.get("attachmentObjectId"),
            "verificationMethod": evidence.get("verificationMethod"),
            "moveOnly": True,
            "deleteSource": False,
        }

    def archive_document(self, document_id: int, actor: str = "local_worker") -> Dict[str, Any]:
        plan = self.plan_archive(int(document_id))
        if plan.get("status") == "already_archived":
            return {"success": True, **plan, "externalSubmission": "already_executed"}
        if not plan.get("canArchive"):
            self._ensure_review_item(int(document_id), plan.get("reasons") or [])
            return {"success": False, **plan, "externalSubmission": "not_executed"}

        document = self.ledger.get_document(int(document_id)) or {}
        provider_id = str(document.get("source_document_id") or "")
        source_sha256 = _source_sha256(document)
        archiver = self.drive_archiver or DriveArchiveClient(self.config)
        try:
            current = archiver.inspect_file(provider_id)
            current_sha256 = archiver.download_sha256(provider_id)
            if current_sha256 != source_sha256:
                raise RuntimeError("Drive source content changed after FAB intake.")
            self._assert_provider_identity(document, current)
            move_result = archiver.move_file(
                provider_id,
                str(plan["sourceFolderId"]),
                str(plan["archiveFolderId"]),
            )
        except Exception as exc:
            reason = _safe_reason(exc)
            self._ensure_review_item(int(document_id), [reason])
            audit_event_id = self.ledger.record_audit_event({
                "action": "drive_wave.archive_failed",
                "entityType": "bookkeeping_document",
                "entityId": str(document_id),
                "details": {"actor": actor, "reason": reason, "externalSubmission": "not_executed"},
            })
            return {
                "success": False,
                "status": "blocked",
                "reasons": [reason],
                "auditEventId": audit_event_id,
                "externalSubmission": "not_executed",
            }

        evidence = (
            self.ledger.find_audit_event(EVIDENCE_ACTION, "bookkeeping_document", str(document_id)) or {}
        ).get("details") or {}
        metadata = dict(document.get("metadata") or {})
        lifecycle = dict(metadata.get("driveWaveLifecycle") or {})
        lifecycle.update({
            "status": "archived",
            "archivedAt": _now(),
            "archivedBy": str(actor or "local_worker")[:200],
            "sourceFolderId": plan["sourceFolderId"],
            "archiveFolderId": plan["archiveFolderId"],
            "sourceSha256": source_sha256,
            "externalTransactionId": evidence.get("externalTransactionId"),
            "attachmentObjectId": evidence.get("attachmentObjectId"),
            "verificationMethod": evidence.get("verificationMethod"),
            "providerMoveStatus": move_result.get("status"),
        })
        metadata["driveWaveLifecycle"] = lifecycle
        self.ledger.update_document(int(document_id), {"metadata": metadata})
        audit_event_id = self.ledger.record_audit_event({
            "action": ARCHIVE_ACTION,
            "entityType": "bookkeeping_document",
            "entityId": str(document_id),
            "details": {
                "actor": actor,
                **lifecycle,
                "externalSubmission": "executed",
                "deletion": "not_performed",
            },
        })
        return {
            "success": True,
            "status": move_result.get("status") or "archived",
            "documentId": int(document_id),
            "archiveFolderId": plan["archiveFolderId"],
            "auditEventId": audit_event_id,
            "externalSubmission": "executed",
            "deletion": "not_performed",
        }

    def archive_ready(self, limit: int = 25, actor: str = "local_worker", dry_run: bool = False) -> Dict[str, Any]:
        candidates = self.list_candidates(limit=limit)["candidates"]
        ready = [item for item in candidates if item["archivePlan"].get("canArchive")]
        if dry_run:
            return {
                "success": True,
                "status": "planned",
                "ready": len(ready),
                "blocked": len(candidates) - len(ready),
                "candidates": candidates,
                "externalSubmission": "not_executed",
            }
        results = [self.archive_document(int(item["documentId"]), actor=actor) for item in ready]
        return {
            "success": all(item.get("success") for item in results),
            "status": "completed" if all(item.get("success") for item in results) else "completed_with_errors",
            "ready": len(ready),
            "archived": sum(1 for item in results if item.get("success")),
            "blocked": len(candidates) - len(ready),
            "results": results,
            "externalSubmission": "executed" if results else "not_executed",
        }

    def _document_reasons(self, document: Dict[str, Any]) -> list[str]:
        reasons = []
        if not self._archive_enabled():
            reasons.append("drive_archive_disabled")
        if document.get("source") != "google_drive":
            reasons.append("source_is_not_google_drive")
        if not self._source_folder_id():
            reasons.append("source_folder_not_configured")
        if not self._archive_folder_id():
            reasons.append("archive_folder_not_configured")
        if not self._business_id():
            reasons.append("wave_business_not_configured")
        if not self._is_configured_source(document):
            reasons.append("document_outside_configured_source_folder")
        if document.get("duplicate_of_document_id"):
            reasons.append("duplicate_review_unresolved")
        for review in document.get("review_items") or []:
            if str(review.get("status") or "pending").lower() in OPEN_REVIEW_STATUSES:
                reasons.append("open_review_item")
                break
        if not re.fullmatch(r"[0-9a-f]{64}", _source_sha256(document)):
            reasons.append("source_sha256_missing")
        return reasons

    def _evidence_reasons(self, document: Dict[str, Any], evidence: Dict[str, Any]) -> list[str]:
        reasons = []
        source_hash = _source_sha256(document)
        if str(evidence.get("sourceSha256") or "").lower() != source_hash:
            reasons.append("evidence_source_hash_mismatch")
        attachment_hash = str(evidence.get("attachmentSha256") or "").lower()
        upload_hash = str(evidence.get("uploadSourceSha256") or "").lower()
        if attachment_hash:
            if attachment_hash != source_hash:
                reasons.append("wave_attachment_hash_mismatch")
        elif upload_hash != source_hash:
            reasons.append("wave_upload_chain_missing")
        if not evidence.get("attachmentPresent"):
            reasons.append("wave_attachment_missing")
        if not evidence.get("attachmentOpened"):
            reasons.append("wave_attachment_not_opened")
        if not str(evidence.get("attachmentObjectId") or "").strip():
            reasons.append("wave_attachment_object_id_missing")
        if not str(evidence.get("externalTransactionId") or "").strip():
            reasons.append("wave_transaction_id_missing")
        if not evidence.get("transactionReviewed"):
            reasons.append("wave_transaction_not_reviewed")
        business_id = self._business_id()
        if business_id and str(evidence.get("businessId") or "") != business_id:
            reasons.append("wave_business_mismatch")
        mime_type = str(evidence.get("attachmentMimeType") or "").lower()
        document_mime = str(document.get("mime_type") or "").lower()
        if document_mime and mime_type != document_mime:
            reasons.append("wave_attachment_mime_mismatch")

        field_matches = evidence.get("fieldMatches") if isinstance(evidence.get("fieldMatches"), dict) else {}
        required_fields = list(REQUIRED_FIELD_MATCHES)
        extracted = document.get("extracted_data") if isinstance(document.get("extracted_data"), dict) else {}
        if any(extracted.get(key) not in (None, "") for key in ("invoice_number", "invoiceNumber", "document_number")):
            required_fields.append("invoiceNumber")
        if document.get("vat_amount") is not None:
            required_fields.append("taxAmount")
        for field in required_fields:
            if field_matches.get(field) is not True:
                reasons.append(f"wave_field_mismatch:{field}")
        return reasons

    def _assert_provider_identity(self, document: Dict[str, Any], current: Dict[str, Any]) -> None:
        metadata = document.get("metadata") or {}
        provider = metadata.get("providerMetadata") if isinstance(metadata.get("providerMetadata"), dict) else {}
        expected_md5 = str(provider.get("md5_checksum") or provider.get("md5Checksum") or "")
        current_md5 = str(current.get("md5Checksum") or "")
        if expected_md5 and current_md5 and expected_md5 != current_md5:
            raise RuntimeError("Drive provider checksum changed after FAB intake.")
        expected_size = provider.get("size") or metadata.get("sizeBytes")
        current_size = current.get("size")
        if expected_size not in (None, "") and current_size not in (None, ""):
            if int(expected_size) != int(current_size):
                raise RuntimeError("Drive provider size changed after FAB intake.")
        if current.get("trashed"):
            raise RuntimeError("Drive source file is in trash.")

    def _ensure_review_item(self, document_id: int, reasons: list[str]) -> None:
        document = self.ledger.get_document(document_id) or {}
        if any(
            item.get("reason") == "drive_wave_archive_blocked"
            and str(item.get("status") or "pending").lower() in OPEN_REVIEW_STATUSES
            for item in document.get("review_items") or []
        ):
            return
        self.ledger.create_review_item({
            "documentId": document_id,
            "reason": "drive_wave_archive_blocked",
            "details": "Drive source retained because Wave attachment proof did not meet policy: " + ", ".join(reasons),
            "correctedData": {"reasons": reasons, "sourceAction": "retain_in_drive"},
        })

    def _resolve_archive_review_items(self, document_id: int, actor: str, evidence_digest: str) -> None:
        resolved_ids = []
        for item in self.ledger.list_review_items(
            status=sorted(OPEN_REVIEW_STATUSES),
            limit=100,
            document_id=document_id,
        ):
            if item.get("reason") != "drive_wave_archive_blocked":
                continue
            self.ledger.resolve_review_item(
                int(item["id"]),
                status="resolved",
                resolution="Fresh Wave transaction and attachment evidence now satisfies the archive policy.",
                corrected_data={
                    "actor": str(actor or "hai")[:200],
                    "evidenceDigest": evidence_digest,
                    "sourceAction": "recheck_before_move",
                },
            )
            resolved_ids.append(int(item["id"]))
        if resolved_ids:
            self.ledger.record_audit_event({
                "action": "drive_wave.archive_reviews_resolved",
                "entityType": "bookkeeping_document",
                "entityId": str(document_id),
                "details": {
                    "actor": str(actor or "hai")[:200],
                    "reviewItemIds": resolved_ids,
                    "evidenceDigest": evidence_digest,
                },
            })

    def _is_configured_source(self, document: Dict[str, Any]) -> bool:
        if document.get("source") != "google_drive":
            return False
        metadata = document.get("metadata") or {}
        provider = metadata.get("providerMetadata") if isinstance(metadata.get("providerMetadata"), dict) else {}
        folder_id = provider.get("folder_id") or provider.get("folderId") or metadata.get("sourceIdentifier")
        return bool(self._source_folder_id()) and str(folder_id or "") == self._source_folder_id()

    def _archive_enabled(self) -> bool:
        return _as_bool(_first(self.config, "google_drive_archive_verified_files", "drive_archive_verified_files"), False)

    def _source_folder_id(self) -> str:
        return str(_first(self.config, "google_drive_wave_source_folder_id", "google_drive_folder_id", "drive_folder_id") or "").strip()

    def _archive_folder_id(self) -> str:
        return str(_first(self.config, "google_drive_wave_archive_folder_id", "google_drive_archive_folder_id") or "").strip()

    def _business_id(self) -> str:
        return str(_first(self.config, "waveapps_business_id", "wave_business_id") or "").strip()

    def _evidence_max_age_seconds(self) -> int:
        value = _first(
            self.config,
            "google_drive_wave_attachment_evidence_max_age_seconds",
            "drive_wave_attachment_evidence_max_age_seconds",
            "wave_attachment_evidence_max_age_seconds",
        )
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = 900
        return max(60, min(parsed, 3600))


def _normalize_evidence(evidence: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(evidence, dict):
        return {}
    allowed = {
        "externalTransactionId", "businessId", "sourceSha256", "uploadSourceSha256",
        "attachmentSha256", "attachmentObjectId", "attachmentMimeType", "attachmentFilename",
        "attachmentPresent", "attachmentOpened", "transactionReviewed", "fieldMatches",
        "verifiedAt", "verifier", "verificationMethod", "evidenceDigest", "actor",
    }
    normalized = {key: value for key, value in evidence.items() if key in allowed}
    for key in ("sourceSha256", "uploadSourceSha256", "attachmentSha256"):
        if normalized.get(key):
            normalized[key] = str(normalized[key]).lower().strip()
    return normalized


def _source_sha256(document: Dict[str, Any]) -> str:
    metadata = document.get("metadata") or {}
    return str(metadata.get("contentSha256") or document.get("duplicate_fingerprint") or "").lower().strip()


def _digest(payload: Dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _first(config: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = config.get(key)
        if value not in (None, ""):
            return value
    nested_drive = config.get("google_drive") if isinstance(config.get("google_drive"), dict) else {}
    nested_wave = config.get("waveapps_business") if isinstance(config.get("waveapps_business"), dict) else {}
    nested = {**nested_drive, **nested_wave}
    for key in keys:
        short = key.replace("google_drive_", "").replace("waveapps_business_", "")
        if nested.get(short) not in (None, ""):
            return nested[short]
    return None


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "enabled"}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _timestamp_is_fresh(value: Any, max_age_seconds: int) -> bool:
    try:
        observed_at = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return False
    age_seconds = (datetime.now(timezone.utc) - observed_at.astimezone(timezone.utc)).total_seconds()
    return -60 <= age_seconds <= max_age_seconds


def _safe_reason(error: Exception) -> str:
    text = re.sub(r"\s+", " ", str(error or type(error).__name__)).strip()
    return text[:300] or type(error).__name__
