import csv
import io
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.data_entry.mijngeldzaken_autonomous_operator import MijngeldzakenAutonomousOperator
from src.data_entry.mijngeldzaken_surface import (
    build_mijngeldzaken_action_payload,
    build_mijngeldzaken_master_ledger_draft,
    classify_mijngeldzaken_destination,
    resolve_mijngeldzaken_action_for_document,
)
from src.data_entry.waveapps_autonomous_operator import WaveappsAutonomousOperator
from src.operations.local_bookkeeping_records import LocalBookkeepingRecordService
from src.operations.local_ledger import LocalOperationsLedger
from src.operations.local_routing import PREPARED_ROUTING_STATUSES


EXPORT_APPROVAL_PHRASE = "APPROVE FAB EXPORT DRAFT"
EXPORT_REJECTION_PHRASE = "REJECT FAB EXPORT DRAFT"
EXPORT_RESULT_CONFIRMATION_PHRASE = "RECORD FAB EXPORT RESULT"
OPEN_REVIEW_STATUSES = {"pending", "in_review"}
APPROVABLE_EXPORT_STATUSES = {"approval_required", "prepared"}
REJECTABLE_EXPORT_STATUSES = {"approval_required", "prepared", "approved"}
RESULT_STATUSES = {"executed", "submitted", "queued", "failed"}
TERMINAL_EXECUTION_STATUSES = {"executed", "submitted", "queued"}
PRESERVED_EXPORT_STATUSES = {"approved", "queued", "executed", "submitted", "failed", "rejected"}


class LocalExportAttemptService:
    """Persist approval-gated export attempts from prepared external routes.

    Routing creates a Wave operation plan. This service records FAB's local
    decision state around that plan so the dashboard/API can approve or record
    results without silently submitting data to Wave.
    """

    def __init__(self, ledger: LocalOperationsLedger, config: Optional[Dict[str, Any]] = None):
        self.ledger = ledger
        self.config = config or {}

    def prepare_from_routing_attempt(
        self,
        routing_attempt_id: int,
        actor: str = "fab_local_exports",
    ) -> Dict[str, Any]:
        routing_attempt = self.ledger.get_routing_attempt(routing_attempt_id)
        if not routing_attempt:
            return {"success": False, "status": "not_found", "error": "Routing attempt not found"}

        metadata = routing_attempt.get("metadata") or {}
        document = self.ledger.get_document(int(routing_attempt["document_id"])) if routing_attempt.get("document_id") else None
        record = (document or {}).get("bookkeeping_record") or _record_from_routing_metadata(self.ledger, metadata)
        operation = metadata.get("operation") if isinstance(metadata.get("operation"), dict) else {}
        operation_payload = operation.get("payload") if isinstance(operation.get("payload"), dict) else {}
        destination = metadata.get("destination") if isinstance(metadata.get("destination"), dict) else {}
        route_status = str(routing_attempt.get("status") or "")
        target_system = metadata.get("targetSystem") or _target_system_from_target(routing_attempt.get("target"))
        existing_attempt = _existing_export_attempt_for_route(self.ledger, routing_attempt, operation)
        if existing_attempt and str(existing_attempt.get("status") or "") in PRESERVED_EXPORT_STATUSES:
            self.ledger.record_audit_event({
                "action": "local_export_attempt.prepare_preserved",
                "entityType": "export_attempt",
                "entityId": str(existing_attempt.get("id")),
                "details": {
                    "actor": actor,
                    "routingAttemptId": routing_attempt.get("id"),
                    "documentId": routing_attempt.get("document_id"),
                    "bookkeepingRecordId": existing_attempt.get("bookkeeping_record_id"),
                    "operationId": operation.get("operation_id"),
                    "status": existing_attempt.get("status"),
                    "externalSubmission": existing_attempt.get("external_submission"),
                },
            })
            return {
                "success": True,
                "status": "already_prepared",
                "exportAttemptId": existing_attempt.get("id"),
                "routingAttemptId": routing_attempt.get("id"),
                "documentId": routing_attempt.get("document_id"),
                "bookkeepingRecordId": existing_attempt.get("bookkeeping_record_id"),
                "operationId": operation.get("operation_id"),
                "message": f"Existing export attempt #{existing_attempt.get('id')} is {existing_attempt.get('status')} and was not overwritten.",
                "exportAttempt": existing_attempt,
            }
        master_ledger_draft = _master_ledger_draft(
            target_system,
            operation,
            operation_payload,
            routing_attempt,
            document,
            record,
        )
        block = self._export_block_for_routing(routing_attempt, document, record, operation)

        if block:
            export_status = block["status"]
            approval_required = False
            external_submission = "not_executed"
            message = block["message"]
        else:
            export_status = "approval_required"
            approval_required = True
            external_submission = "not_executed"
            target_label = _target_label(target_system)
            message = f"{target_label} export attempt prepared; approval is required before any external submission."

        export_id = self.ledger.upsert_export_attempt({
            "bookkeepingRecordId": record.get("id"),
            "documentId": routing_attempt.get("document_id"),
            "routingAttemptId": routing_attempt.get("id"),
            "workflowRunId": routing_attempt.get("workflow_run_id"),
            "targetSystem": target_system,
            "targetAccount": _first_present(
                operation_payload.get("account"),
                operation_payload.get("incomeAccount"),
                operation_payload.get("expenseAccount"),
                record.get("target_account"),
            ),
            "actionId": operation.get("action_id"),
            "surface": operation.get("surface") or destination.get("target_surface"),
            "operationId": operation.get("operation_id"),
            "status": export_status,
            "safety": operation.get("safety") or "requires_confirmation",
            "approvalRequired": approval_required,
            "externalSubmission": external_submission,
            "message": message,
            "payload": operation_payload,
            "metadata": {
                "actor": actor,
                "routingStatus": route_status,
                "routingTarget": routing_attempt.get("target"),
                "routingMessage": routing_attempt.get("message"),
                "operationPlan": operation.get("plan"),
                "approvalRequiredForSubmit": metadata.get("approvalRequiredForSubmit", True),
                "documentSnapshot": metadata.get("documentSnapshot"),
                "bookkeepingRecordSnapshot": metadata.get("bookkeepingRecordSnapshot"),
                "masterLedgerDraft": master_ledger_draft,
                "masterLedgerChecksum": (master_ledger_draft or {}).get("checksum"),
                "blockedReason": block.get("status") if block else None,
            },
        })

        if document and routing_attempt.get("document_id"):
            LocalBookkeepingRecordService(self.ledger, self.config).record_export_state(
                int(routing_attempt["document_id"]),
                "awaiting_approval" if export_status == "approval_required" else export_status,
                status="export_approval_pending" if export_status == "approval_required" else None,
                routing_attempt_id=int(routing_attempt["id"]),
                details={
                    "exportAttemptId": export_id,
                    "operationId": operation.get("operation_id"),
                    "externalSubmission": external_submission,
                },
            )
        elif record.get("id"):
            _update_record_export_state(
                self.ledger,
                record,
                "awaiting_approval" if export_status == "approval_required" else export_status,
                status="export_approval_pending" if export_status == "approval_required" else None,
                routing_attempt_id=int(routing_attempt["id"]),
                details={
                    "exportAttemptId": export_id,
                    "operationId": operation.get("operation_id"),
                    "externalSubmission": external_submission,
                },
            )

        self.ledger.record_audit_event({
            "action": "local_export_attempt.prepared",
            "entityType": "export_attempt",
            "entityId": str(export_id),
            "details": {
                "routingAttemptId": routing_attempt.get("id"),
                "documentId": routing_attempt.get("document_id"),
                "bookkeepingRecordId": record.get("id"),
                "status": export_status,
                "externalSubmission": external_submission,
                "approvalRequired": approval_required,
                "targetSystem": target_system,
                "masterLedgerChecksum": (master_ledger_draft or {}).get("checksum"),
            },
        })
        return {
            "success": export_status == "approval_required",
            "status": export_status,
            "exportAttemptId": export_id,
            "routingAttemptId": routing_attempt.get("id"),
            "documentId": routing_attempt.get("document_id"),
            "bookkeepingRecordId": record.get("id"),
            "operationId": operation.get("operation_id"),
            "message": message,
            "exportAttempt": self.ledger.get_export_attempt(export_id),
        }

    def prepare_ready_exports(self, limit: int = 25) -> Dict[str, Any]:
        routing_attempts = self.ledger.list_routing_attempts(
            status=tuple(PREPARED_ROUTING_STATUSES),
            limit=limit,
        )
        summary = {
            "requested": len(routing_attempts),
            "prepared": 0,
            "blocked": 0,
            "exportAttempts": [],
            "externalSubmission": "not_executed",
        }
        for routing_attempt in routing_attempts:
            result = self.prepare_from_routing_attempt(int(routing_attempt["id"]))
            if result.get("success"):
                summary["prepared"] += 1
            else:
                summary["blocked"] += 1
            summary["exportAttempts"].append(result)
        self.ledger.record_audit_event({
            "action": "local_export_attempt.batch_prepare_completed",
            "entityType": "export_attempt",
            "details": {
                "requested": summary["requested"],
                "prepared": summary["prepared"],
                "blocked": summary["blocked"],
                "externalSubmission": "not_executed",
            },
        })
        return summary

    def artifact_for_attempt(
        self,
        export_attempt_id: int,
        export_format: str = "json",
        actor: str = "fab_local_exports",
    ) -> Dict[str, Any]:
        attempt = self.ledger.get_export_attempt(export_attempt_id)
        if not attempt:
            return {"success": False, "status": "not_found", "error": "Export attempt not found"}
        metadata = attempt.get("metadata") if isinstance(attempt.get("metadata"), dict) else {}
        draft = metadata.get("masterLedgerDraft") if isinstance(metadata.get("masterLedgerDraft"), dict) else None
        if not draft:
            return {
                "success": False,
                "status": "no_artifact",
                "message": "Export attempt does not have a master-ledger draft artifact.",
            }

        export_format = str(export_format or "json").strip().lower()
        filename_base = f"fab-{attempt.get('target_system') or 'export'}-{export_attempt_id}"
        if export_format == "json":
            content = json.dumps(draft, sort_keys=True, indent=2, default=str)
            result = {
                "success": True,
                "status": "prepared",
                "artifact": {
                    "format": "json",
                    "contentType": "application/json",
                    "filename": f"{filename_base}.json",
                    "content": content,
                    "checksum": draft.get("checksum"),
                    "externalSubmission": "not_executed",
                    "draftType": draft.get("draftType"),
                },
            }
            self._record_artifact_audit(export_attempt_id, attempt, result["artifact"], actor)
            return result
        if export_format == "csv" and draft.get("draftType") == "transaction_import":
            content = _csv_artifact_content(draft)
            result = {
                "success": True,
                "status": "prepared",
                "artifact": {
                    "format": "csv",
                    "contentType": "text/csv",
                    "filename": f"{filename_base}.csv",
                    "content": content,
                    "checksum": draft.get("checksum"),
                    "externalSubmission": "not_executed",
                    "draftType": draft.get("draftType"),
                },
            }
            self._record_artifact_audit(export_attempt_id, attempt, result["artifact"], actor)
            return result
        return {
            "success": False,
            "status": "unsupported_format",
            "message": f"Master-ledger draft cannot be exported as {export_format!r}.",
            "supportedFormats": ["json"] + (["csv"] if draft.get("draftType") == "transaction_import" else []),
        }

    def regenerate_attempt(
        self,
        export_attempt_id: int,
        actor: str = "fab_local_exports",
    ) -> Dict[str, Any]:
        attempt = self.ledger.get_export_attempt(export_attempt_id)
        if not attempt:
            return {"success": False, "status": "not_found", "error": "Export attempt not found"}
        if attempt.get("external_submission") in {"queued", "submitted", "executed"}:
            return {
                "success": False,
                "status": "already_submitted",
                "message": "Submitted or queued export attempts cannot be regenerated locally.",
                "externalSubmission": attempt.get("external_submission"),
            }
        target_system = _target_system_for_attempt(attempt)
        if not _is_mijngeldzaken_target(target_system):
            return {
                "success": False,
                "status": "not_supported",
                "message": "Only MijnGeldzaken master-ledger drafts can be regenerated from current FAB state.",
                "externalSubmission": "not_executed",
            }

        current_package = _current_mijngeldzaken_master_ledger_package(self.ledger, self.config, attempt)
        if not current_package:
            return {
                "success": False,
                "status": "source_missing",
                "message": "The source document or bookkeeping record for this export attempt no longer exists.",
                "externalSubmission": "not_executed",
            }
        draft = current_package["draft"]
        metadata = dict(attempt.get("metadata") or {})
        history = list(metadata.get("regenerationHistory") or [])
        history.append({
            "actor": actor,
            "regeneratedAt": _now(),
            "fromChecksum": _master_ledger_checksum(metadata),
            "toChecksum": draft.get("checksum"),
            "fromStatus": attempt.get("status"),
            "fromExternalSubmission": attempt.get("external_submission"),
        })
        metadata.update({
            "masterLedgerDraft": draft,
            "masterLedgerChecksum": draft.get("checksum"),
            "regenerationHistory": history,
            "lastRegeneration": history[-1],
            "sourceRegeneratedFromCurrentFabState": True,
        })
        self.ledger.update_export_attempt(export_attempt_id, {
            "targetAccount": current_package["payload"].get("account"),
            "actionId": current_package["actionId"],
            "surface": current_package["surface"],
            "status": "approval_required",
            "approvalRequired": True,
            "externalSubmission": "not_executed",
            "message": "MijnGeldzaken master-ledger draft regenerated from current FAB source state; approval is required before external submission.",
            "payload": current_package["payload"],
            "result": {},
            "metadata": metadata,
        })
        details = {
            "exportAttemptId": export_attempt_id,
            "actor": actor,
            "targetSystem": target_system,
            "externalSubmission": "not_executed",
            "masterLedgerChecksum": draft.get("checksum"),
            "previousMasterLedgerChecksum": history[-1].get("fromChecksum"),
        }
        if attempt.get("document_id"):
            LocalBookkeepingRecordService(self.ledger, self.config).record_export_state(
                int(attempt["document_id"]),
                "awaiting_approval",
                status="export_approval_pending",
                routing_attempt_id=attempt.get("routing_attempt_id"),
                details=details,
            )
        elif attempt.get("bookkeeping_record_id"):
            record = self.ledger.get_bookkeeping_record(int(attempt["bookkeeping_record_id"])) or {}
            if record:
                _update_record_export_state(
                    self.ledger,
                    record,
                    "awaiting_approval",
                    status="export_approval_pending",
                    routing_attempt_id=attempt.get("routing_attempt_id"),
                    details=details,
                )
        self.ledger.record_audit_event({
            "action": "local_export_attempt.regenerated",
            "entityType": "export_attempt",
            "entityId": str(export_attempt_id),
            "details": details,
        })
        return {
            "success": True,
            "status": "regenerated",
            "externalSubmission": "not_executed",
            "masterLedgerChecksum": draft.get("checksum"),
            "exportAttempt": self.ledger.get_export_attempt(export_attempt_id),
        }

    def _record_artifact_audit(
        self,
        export_attempt_id: int,
        attempt: Dict[str, Any],
        artifact: Dict[str, Any],
        actor: str,
    ) -> None:
        self.ledger.record_audit_event({
            "action": "local_export_attempt.artifact_prepared",
            "entityType": "export_attempt",
            "entityId": str(export_attempt_id),
            "details": {
                "actor": actor,
                "format": artifact.get("format"),
                "filename": artifact.get("filename"),
                "checksum": artifact.get("checksum"),
                "draftType": artifact.get("draftType"),
                "targetSystem": attempt.get("target_system"),
                "externalSubmission": "not_executed",
            },
        })

    def approve_attempt(
        self,
        export_attempt_id: int,
        actor: str = "local_user",
        confirmation: Optional[str] = None,
        resolution: Optional[str] = None,
    ) -> Dict[str, Any]:
        attempt = self.ledger.get_export_attempt(export_attempt_id)
        if not attempt:
            return {"success": False, "status": "not_found", "error": "Export attempt not found"}
        if confirmation != EXPORT_APPROVAL_PHRASE:
            return {
                "success": False,
                "status": "requires_confirmation",
                "confirmationPhrase": EXPORT_APPROVAL_PHRASE,
                "message": "Type the exact approval phrase before marking this export as approved.",
            }
        if attempt.get("status") == "approved":
            return {"success": True, "status": "already_approved", "exportAttempt": attempt}
        if attempt.get("status") not in APPROVABLE_EXPORT_STATUSES:
            return {
                "success": False,
                "status": "not_approvable",
                "message": f"Export attempt status {attempt.get('status')} cannot be approved.",
            }
        stale = self._master_ledger_staleness(attempt, "approval", actor)
        if stale:
            return stale

        now = _now()
        metadata = dict(attempt.get("metadata") or {})
        master_ledger_checksum = _master_ledger_checksum(metadata)
        metadata["approval"] = {
            "actor": actor,
            "approvedAt": now,
            "resolution": resolution,
            "masterLedgerChecksum": master_ledger_checksum,
        }
        self.ledger.update_export_attempt(export_attempt_id, {
            "status": "approved",
            "approvalRequired": False,
            "approvedAt": now,
            "approvedBy": actor,
            "externalSubmission": "approved_not_executed",
            "message": "Export approved locally; external submission is still not executed.",
            "metadata": metadata,
        })
        if attempt.get("document_id"):
            LocalBookkeepingRecordService(self.ledger, self.config).record_export_state(
                int(attempt["document_id"]),
                "approved_not_submitted",
                status="export_approved",
                routing_attempt_id=attempt.get("routing_attempt_id"),
                details={
                    "exportAttemptId": export_attempt_id,
                    "approvedBy": actor,
                    "externalSubmission": "approved_not_executed",
                    "masterLedgerChecksum": master_ledger_checksum,
                },
            )
        elif attempt.get("bookkeeping_record_id"):
            record = self.ledger.get_bookkeeping_record(int(attempt["bookkeeping_record_id"])) or {}
            if record:
                _update_record_export_state(
                    self.ledger,
                    record,
                    "approved_not_submitted",
                    status="export_approved",
                    routing_attempt_id=attempt.get("routing_attempt_id"),
                    details={
                        "exportAttemptId": export_attempt_id,
                        "approvedBy": actor,
                        "externalSubmission": "approved_not_executed",
                        "masterLedgerChecksum": master_ledger_checksum,
                    },
                )
        self.ledger.record_audit_event({
            "action": "local_export_attempt.approved",
            "entityType": "export_attempt",
            "entityId": str(export_attempt_id),
            "details": {
                "actor": actor,
                "documentId": attempt.get("document_id"),
                "bookkeepingRecordId": attempt.get("bookkeeping_record_id"),
                "routingAttemptId": attempt.get("routing_attempt_id"),
                "externalSubmission": "approved_not_executed",
                "masterLedgerChecksum": master_ledger_checksum,
            },
        })
        return {
            "success": True,
            "status": "approved",
            "exportAttempt": self.ledger.get_export_attempt(export_attempt_id),
        }

    def reject_attempt(
        self,
        export_attempt_id: int,
        actor: str = "local_user",
        confirmation: Optional[str] = None,
        resolution: Optional[str] = None,
    ) -> Dict[str, Any]:
        attempt = self.ledger.get_export_attempt(export_attempt_id)
        if not attempt:
            return {"success": False, "status": "not_found", "error": "Export attempt not found"}
        if confirmation != EXPORT_REJECTION_PHRASE:
            return {
                "success": False,
                "status": "requires_confirmation",
                "confirmationPhrase": EXPORT_REJECTION_PHRASE,
                "message": "Type the exact rejection phrase before rejecting this export attempt.",
            }
        if attempt.get("status") == "rejected":
            return {"success": True, "status": "already_rejected", "exportAttempt": attempt}
        if attempt.get("status") not in REJECTABLE_EXPORT_STATUSES:
            return {
                "success": False,
                "status": "not_rejectable",
                "message": f"Export attempt status {attempt.get('status')} cannot be rejected.",
            }
        if attempt.get("external_submission") in {"queued", "submitted", "executed"}:
            return {
                "success": False,
                "status": "already_submitted",
                "message": "Submitted or queued export attempts cannot be rejected locally; record the actual external result instead.",
            }

        now = _now()
        metadata = dict(attempt.get("metadata") or {})
        master_ledger_checksum = _master_ledger_checksum(metadata)
        metadata["rejection"] = {
            "actor": actor,
            "rejectedAt": now,
            "resolution": resolution,
            "masterLedgerChecksum": master_ledger_checksum,
        }
        self.ledger.update_export_attempt(export_attempt_id, {
            "status": "rejected",
            "approvalRequired": False,
            "externalSubmission": "rejected_not_executed",
            "message": "Export rejected locally; no external submission was executed.",
            "metadata": metadata,
        })
        details = {
            "exportAttemptId": export_attempt_id,
            "rejectedBy": actor,
            "resolution": resolution,
            "externalSubmission": "rejected_not_executed",
            "masterLedgerChecksum": master_ledger_checksum,
        }
        if attempt.get("document_id"):
            LocalBookkeepingRecordService(self.ledger, self.config).record_export_state(
                int(attempt["document_id"]),
                "rejected_not_executed",
                status="export_rejected",
                routing_attempt_id=attempt.get("routing_attempt_id"),
                details=details,
            )
        elif attempt.get("bookkeeping_record_id"):
            record = self.ledger.get_bookkeeping_record(int(attempt["bookkeeping_record_id"])) or {}
            if record:
                _update_record_export_state(
                    self.ledger,
                    record,
                    "rejected_not_executed",
                    status="export_rejected",
                    routing_attempt_id=attempt.get("routing_attempt_id"),
                    details=details,
                )
        self.ledger.record_audit_event({
            "action": "local_export_attempt.rejected",
            "entityType": "export_attempt",
            "entityId": str(export_attempt_id),
            "details": {
                "actor": actor,
                "documentId": attempt.get("document_id"),
                "bookkeepingRecordId": attempt.get("bookkeeping_record_id"),
                "routingAttemptId": attempt.get("routing_attempt_id"),
                "externalSubmission": "rejected_not_executed",
                "resolution": resolution,
                "masterLedgerChecksum": master_ledger_checksum,
            },
        })
        return {
            "success": True,
            "status": "rejected",
            "externalSubmission": "rejected_not_executed",
            "exportAttempt": self.ledger.get_export_attempt(export_attempt_id),
        }

    def record_result(
        self,
        export_attempt_id: int,
        status: str,
        external_id: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        actor: str = "fab_local_exports",
        confirmation: Optional[str] = None,
    ) -> Dict[str, Any]:
        attempt = self.ledger.get_export_attempt(export_attempt_id)
        if not attempt:
            return {"success": False, "status": "not_found", "error": "Export attempt not found"}
        status = str(status or "").strip().lower()
        if status not in RESULT_STATUSES:
            return {"success": False, "status": "invalid_result_status", "error": f"Unsupported result status {status!r}"}
        if confirmation != EXPORT_RESULT_CONFIRMATION_PHRASE:
            return {
                "success": False,
                "status": "requires_confirmation",
                "confirmationPhrase": EXPORT_RESULT_CONFIRMATION_PHRASE,
                "message": "Type the exact result phrase before recording an external export result.",
            }
        if attempt.get("status") != "approved" and status in {"executed", "submitted", "queued"}:
            return {
                "success": False,
                "status": "blocked_unapproved",
                "message": "Only approved export attempts can receive submitted/executed results.",
            }
        if status in {"executed", "submitted", "queued"}:
            stale = self._master_ledger_staleness(attempt, "result", actor)
            if stale:
                return stale

        now = _now()
        external_submission = _external_submission_for_result(status)
        metadata = dict(attempt.get("metadata") or {})
        master_ledger_checksum = _master_ledger_checksum(metadata)
        metadata["lastResult"] = {
            "actor": actor,
            "recordedAt": now,
            "status": status,
            "externalSubmission": external_submission,
            "masterLedgerChecksum": master_ledger_checksum,
        }
        result_payload = dict(result or {})
        if master_ledger_checksum and "masterLedgerChecksum" not in result_payload:
            result_payload["masterLedgerChecksum"] = master_ledger_checksum
        self.ledger.update_export_attempt(export_attempt_id, {
            "status": status,
            "externalSubmission": external_submission,
            "submittedAt": now if status in {"executed", "submitted"} else None,
            "externalId": external_id,
            "message": _message_for_result(status),
            "result": result_payload,
            "metadata": metadata,
        })
        if attempt.get("document_id"):
            LocalBookkeepingRecordService(self.ledger, self.config).record_export_state(
                int(attempt["document_id"]),
                external_submission,
                status="routed" if status in {"executed", "submitted"} else None,
                routing_attempt_id=attempt.get("routing_attempt_id"),
                details={
                    "exportAttemptId": export_attempt_id,
                    "externalId": external_id,
                    "resultStatus": status,
                    "externalSubmission": external_submission,
                    "masterLedgerChecksum": master_ledger_checksum,
                },
            )
        elif attempt.get("bookkeeping_record_id"):
            record = self.ledger.get_bookkeeping_record(int(attempt["bookkeeping_record_id"])) or {}
            if record:
                _update_record_export_state(
                    self.ledger,
                    record,
                    external_submission,
                    status="routed" if status in {"executed", "submitted"} else None,
                    routing_attempt_id=attempt.get("routing_attempt_id"),
                    details={
                        "exportAttemptId": export_attempt_id,
                        "externalId": external_id,
                        "resultStatus": status,
                        "externalSubmission": external_submission,
                        "masterLedgerChecksum": master_ledger_checksum,
                    },
                )
        self.ledger.record_audit_event({
            "action": "local_export_attempt.result_recorded",
            "entityType": "export_attempt",
            "entityId": str(export_attempt_id),
            "details": {
                "actor": actor,
                "status": status,
                "externalSubmission": external_submission,
                "externalId": external_id,
                "masterLedgerChecksum": master_ledger_checksum,
            },
        })
        return {
            "success": True,
            "status": status,
            "externalSubmission": external_submission,
            "exportAttempt": self.ledger.get_export_attempt(export_attempt_id),
        }

    def execute_attempt(
        self,
        export_attempt_id: int,
        actor: str = "fab_local_exports",
    ) -> Dict[str, Any]:
        attempt = self.ledger.get_export_attempt(export_attempt_id)
        if not attempt:
            return {"success": False, "status": "not_found", "error": "Export attempt not found"}

        status = str(attempt.get("status") or "").strip().lower()
        if status == "approved":
            metadata = dict(attempt.get("metadata") or {})
            master_ledger_checksum = _master_ledger_checksum(metadata)
            stale = self._master_ledger_staleness(attempt, "execution", actor)
            if stale:
                return stale
            action_id = attempt.get("action_id")
            operation = dict(metadata.get("operation") or {})
            if not action_id:
                return {
                    "success": False,
                    "status": "invalid_plan",
                    "error": "No executable action id found for this export attempt.",
                }
            payload = dict(attempt.get("payload") or {})
            if not isinstance(payload, dict):
                payload = {}
            capability_id = metadata.get("capabilityId") or metadata.get("capability_id")
            available_signals = _list_optional_strs(metadata.get("availableSignals") or metadata.get("available_signals"))
            confidence = metadata.get("confidence")
            operation_mode = metadata.get("mode") or operation.get("mode") or operation.get("plan", {}).get("mode")
            target_system = _target_system_for_attempt(attempt)
            try:
                if _is_mijngeldzaken_target(target_system):
                    operator = MijngeldzakenAutonomousOperator(self.config)
                    execution = operator.execute(
                        action_id,
                        payload,
                        surface=attempt.get("surface") or operation.get("surface"),
                        actor=actor,
                        confirmed=True,
                        idempotency_key=str(attempt.get("operation_id") or attempt.get("id")),
                        mode=operation_mode,
                    )
                else:
                    operator = WaveappsAutonomousOperator(self.config)
                    execution = operator.execute(
                        action_id,
                        payload,
                        surface=attempt.get("surface") or operation.get("surface"),
                        actor=actor,
                        confirmed=True,
                        idempotency_key=str(attempt.get("operation_id") or attempt.get("id")),
                        mode=operation_mode,
                        capability_id=capability_id,
                        available_signals=available_signals,
                        confidence=confidence,
                    )
            except Exception as exc:
                execution_status = "failed"
                message = f"Execution failed before dispatch: {exc}"
                execution = {"status": "failed", "message": message, "operation": operation}
                execution["status"] = execution_status

            execution_status = str(execution.get("status") or "").strip().lower()
            external_id = execution.get("external_id")
            operation = execution.get("operation") or attempt
            external_submission, mapped_status, mapped_message = _map_execution_status(execution_status, target_system)

            now = _now()
            execution_metadata = dict(metadata.get("lastExecution") or {})
            execution_metadata["actor"] = actor
            execution_metadata["executedAt"] = now
            execution_metadata["rawStatus"] = execution_status
            execution_metadata["mappedStatus"] = mapped_status
            execution_metadata["operation"] = operation
            execution_metadata["masterLedgerChecksum"] = master_ledger_checksum

            update_payload = {
                "status": mapped_status,
                "externalSubmission": external_submission,
                "message": mapped_message,
                "result": {
                    "status": execution_status,
                    "message": execution.get("message"),
                    "externalId": external_id,
                    "operation": operation,
                    "masterLedgerChecksum": master_ledger_checksum,
                },
                "metadata": {
                    **dict(metadata),
                    "lastExecution": execution_metadata,
                },
            }
            if mapped_status in TERMINAL_EXECUTION_STATUSES:
                if mapped_status in {"executed", "submitted"}:
                    update_payload["submittedAt"] = now
                update_payload["externalId"] = external_id
            elif mapped_status == "failed":
                update_payload["message"] = execution.get("message") or mapped_message

            self.ledger.update_export_attempt(export_attempt_id, update_payload)

            if attempt.get("document_id") and mapped_status in TERMINAL_EXECUTION_STATUSES:
                LocalBookkeepingRecordService(self.ledger, self.config).record_export_state(
                    int(attempt["document_id"]),
                    _record_status_for_execution(mapped_status),
                    status="routed",
                    routing_attempt_id=attempt.get("routing_attempt_id"),
                    details={
                        "exportAttemptId": export_attempt_id,
                        "externalId": external_id,
                        "resultStatus": mapped_status,
                        "executionStatus": execution_status,
                        "externalSubmission": external_submission,
                        "masterLedgerChecksum": master_ledger_checksum,
                    },
                )
            elif attempt.get("bookkeeping_record_id") and mapped_status in TERMINAL_EXECUTION_STATUSES:
                record = self.ledger.get_bookkeeping_record(int(attempt["bookkeeping_record_id"])) or {}
                if record:
                    _update_record_export_state(
                        self.ledger,
                        record,
                        _record_status_for_execution(mapped_status),
                        status="routed",
                        routing_attempt_id=attempt.get("routing_attempt_id"),
                        details={
                            "exportAttemptId": export_attempt_id,
                            "externalId": external_id,
                            "resultStatus": mapped_status,
                            "executionStatus": execution_status,
                            "externalSubmission": external_submission,
                            "masterLedgerChecksum": master_ledger_checksum,
                        },
                    )

            self.ledger.record_audit_event({
                "action": "local_export_attempt.executed",
                "entityType": "export_attempt",
                "entityId": str(export_attempt_id),
                "details": {
                    "actor": actor,
                    "status": mapped_status,
                    "externalSubmission": external_submission,
                    "executionStatus": execution_status,
                    "externalId": external_id,
                    "targetSystem": target_system,
                    "masterLedgerChecksum": master_ledger_checksum,
                },
            })
            return {
                "success": True,
                "status": mapped_status,
                "externalSubmission": external_submission,
                "executionStatus": execution_status,
                "exportAttempt": self.ledger.get_export_attempt(export_attempt_id),
            }

        if status in TERMINAL_EXECUTION_STATUSES:
            return {
                "success": True,
                "status": f"already_{status}",
                "externalSubmission": attempt.get("external_submission"),
                "exportAttempt": attempt,
            }

        if status == "failed":
            return {
                "success": False,
                "status": "not_executable",
                "message": "A failed attempt must be corrected before resubmitting.",
            }

        return {
            "success": False,
            "status": "not_approved",
            "message": f"Export attempt status {attempt.get('status')} cannot be executed without approval.",
        }

    def _master_ledger_staleness(
        self,
        attempt: Dict[str, Any],
        stage: str,
        actor: str,
    ) -> Optional[Dict[str, Any]]:
        check = _master_ledger_freshness(self.ledger, self.config, attempt)
        if check.get("status") in {"not_applicable", "fresh"}:
            return None
        self.ledger.record_audit_event({
            "action": "local_export_attempt.master_ledger_stale",
            "entityType": "export_attempt",
            "entityId": str(attempt.get("id")),
            "details": {
                "actor": actor,
                "stage": stage,
                "targetSystem": attempt.get("target_system"),
                "storedChecksum": check.get("storedChecksum"),
                "currentChecksum": check.get("currentChecksum"),
                "reason": check.get("status"),
                "externalSubmission": "not_executed",
            },
        })
        return {
            "success": False,
            "status": "stale_master_ledger_draft",
            "message": "Master-ledger draft no longer matches the current FAB source record. Regenerate the route/export attempt before approval or external result recording.",
            "storedChecksum": check.get("storedChecksum"),
            "currentChecksum": check.get("currentChecksum"),
            "currentDraft": check.get("currentDraft"),
            "externalSubmission": "not_executed",
        }

    def _export_block_for_routing(
        self,
        routing_attempt: Dict[str, Any],
        document: Optional[Dict[str, Any]],
        record: Optional[Dict[str, Any]],
        operation: Dict[str, Any],
    ) -> Optional[Dict[str, str]]:
        if str(routing_attempt.get("status") or "") not in PREPARED_ROUTING_STATUSES:
            return {
                "status": "blocked_routing",
                "message": f"Routing attempt status {routing_attempt.get('status')} is not ready for export approval.",
            }
        if not document and not record:
            return {"status": "blocked_source_missing", "message": "Source document or bookkeeping record is missing for this route."}
        open_reviews = [
            item for item in document.get("review_items") or []
            if item.get("status") in OPEN_REVIEW_STATUSES
        ] if document else []
        if open_reviews:
            return {"status": "blocked_by_review", "message": "Document still has open review items."}
        if record and record.get("review_required"):
            return {"status": "blocked_by_review", "message": "Bookkeeping record still requires manual review."}
        plan = operation.get("plan") if isinstance(operation.get("plan"), dict) else {}
        if not operation or plan.get("status") != "planned":
            return {"status": "blocked_invalid_plan", "message": "Wave operation plan is incomplete."}
        return None


def _target_system_from_target(value: Any) -> str:
    text = str(value or "waveapps").strip()
    if ":" in text:
        return text.split(":", 1)[0] or "waveapps"
    return text or "waveapps"


def _target_system_for_attempt(attempt: Dict[str, Any]) -> str:
    metadata = attempt.get("metadata") if isinstance(attempt.get("metadata"), dict) else {}
    return str(
        _first_present(
            attempt.get("target_system"),
            attempt.get("targetSystem"),
            metadata.get("targetSystem"),
            metadata.get("target_system"),
            _target_system_from_target(metadata.get("routingTarget")),
            "waveapps",
        )
    ).strip().lower()


def _is_mijngeldzaken_target(target_system: Any) -> bool:
    normalized = str(target_system or "").strip().lower().replace("_", "-")
    return normalized in {"mijngeldzaken", "mijngeldzaken-nl", "mijngeldzaken.nl"} or normalized.startswith("mijngeldzaken:")


def _csv_artifact_content(draft: Dict[str, Any]) -> str:
    row = draft.get("importRow") if isinstance(draft.get("importRow"), dict) else {}
    columns = draft.get("columns") if isinstance(draft.get("columns"), list) else list(row.keys())
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=[str(column) for column in columns], extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerow({str(key): value for key, value in row.items()})
    return buffer.getvalue()


def _master_ledger_draft(
    target_system: Any,
    operation: Dict[str, Any],
    operation_payload: Dict[str, Any],
    routing_attempt: Dict[str, Any],
    document: Optional[Dict[str, Any]],
    record: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not _is_mijngeldzaken_target(target_system):
        return None
    source_proof = {
        "routingAttemptId": routing_attempt.get("id"),
        "documentId": routing_attempt.get("document_id"),
        "bookkeepingRecordId": (record or {}).get("id"),
        "sourceDocumentId": (document or {}).get("source_document_id"),
        "bankTransactionId": (record or {}).get("bank_transaction_id"),
        "duplicateFingerprint": (document or {}).get("duplicate_fingerprint"),
        "reconciliationStatus": (record or document or {}).get("reconciliation_status"),
    }
    source_proof = {key: value for key, value in source_proof.items() if value not in (None, "")}
    return build_mijngeldzaken_master_ledger_draft(
        str(operation.get("action_id") or ""),
        str(operation.get("surface") or ""),
        operation_payload,
        source_proof=source_proof,
    )


def _target_label(target_system: Any) -> str:
    if _is_mijngeldzaken_target(target_system):
        return "MijnGeldzaken"
    return "Wave"


def _record_from_routing_metadata(
    ledger: LocalOperationsLedger,
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    record_id = metadata.get("bookkeepingRecordId") or metadata.get("bookkeeping_record_id")
    if not record_id:
        return {}
    try:
        return ledger.get_bookkeeping_record(int(record_id)) or {}
    except (TypeError, ValueError):
        return {}


def _existing_export_attempt_for_route(
    ledger: LocalOperationsLedger,
    routing_attempt: Dict[str, Any],
    operation: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    routing_attempt_id = routing_attempt.get("id")
    operation_id = operation.get("operation_id")
    candidates = ledger.list_export_attempts(limit=500)
    for attempt in candidates:
        if routing_attempt_id is not None and attempt.get("routing_attempt_id") == routing_attempt_id:
            return attempt
        if operation_id and attempt.get("operation_id") == operation_id:
            return attempt
    return None


def _master_ledger_checksum(metadata: Dict[str, Any]) -> Optional[str]:
    checksum = metadata.get("masterLedgerChecksum")
    if checksum:
        return str(checksum)
    draft = metadata.get("masterLedgerDraft") if isinstance(metadata.get("masterLedgerDraft"), dict) else {}
    checksum = draft.get("checksum")
    return str(checksum) if checksum else None


def master_ledger_freshness(
    ledger: LocalOperationsLedger,
    config: Dict[str, Any],
    attempt: Dict[str, Any],
) -> Dict[str, Any]:
    """Return whether an approval-gated master-ledger draft still matches FAB state."""
    return _master_ledger_freshness(ledger, config, attempt)


def _master_ledger_freshness(
    ledger: LocalOperationsLedger,
    config: Dict[str, Any],
    attempt: Dict[str, Any],
) -> Dict[str, Any]:
    target_system = _target_system_for_attempt(attempt)
    metadata = attempt.get("metadata") if isinstance(attempt.get("metadata"), dict) else {}
    stored_checksum = _master_ledger_checksum(metadata)
    if not _is_mijngeldzaken_target(target_system) or not stored_checksum:
        return {"status": "not_applicable"}

    current_draft = _current_mijngeldzaken_master_ledger_draft(ledger, config, attempt)
    current_checksum = current_draft.get("checksum") if isinstance(current_draft, dict) else None
    if not current_checksum:
        return {
            "status": "source_missing",
            "storedChecksum": stored_checksum,
            "currentChecksum": None,
            "currentDraft": current_draft,
        }
    if str(current_checksum) != str(stored_checksum):
        return {
            "status": "checksum_mismatch",
            "storedChecksum": stored_checksum,
            "currentChecksum": str(current_checksum),
            "currentDraft": current_draft,
        }
    return {
        "status": "fresh",
        "storedChecksum": stored_checksum,
        "currentChecksum": str(current_checksum),
        "currentDraft": current_draft,
    }


def _current_mijngeldzaken_master_ledger_draft(
    ledger: LocalOperationsLedger,
    config: Dict[str, Any],
    attempt: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    package = _current_mijngeldzaken_master_ledger_package(ledger, config, attempt)
    return package.get("draft") if package else None


def _current_mijngeldzaken_master_ledger_package(
    ledger: LocalOperationsLedger,
    config: Dict[str, Any],
    attempt: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    document = ledger.get_document(int(attempt["document_id"])) if attempt.get("document_id") else None
    record = (document or {}).get("bookkeeping_record")
    if not record and attempt.get("bookkeeping_record_id"):
        record = ledger.get_bookkeeping_record(int(attempt["bookkeeping_record_id"]))
    if not document and not record:
        return None

    source = _document_data_for_mijngeldzaken(document) if document else _record_data_for_mijngeldzaken(record or {})
    metadata = attempt.get("metadata") if isinstance(attempt.get("metadata"), dict) else {}
    attempt_payload = attempt.get("payload") if isinstance(attempt.get("payload"), dict) else {}
    mgz_category = _mijngeldzaken_category(source, config)
    default_account = _config_value(
        config,
        "fab_mijngeldzaken_default_account",
        "operations_mijngeldzaken_default_account",
        "mijngeldzaken_default_account",
        default="Huishouden",
    )
    if _source_category_unchanged(source, metadata):
        if attempt_payload.get("category") not in (None, ""):
            mgz_category = str(attempt_payload.get("category"))
        if attempt_payload.get("account") not in (None, ""):
            default_account = str(attempt_payload.get("account"))
    action_id = resolve_mijngeldzaken_action_for_document(source)
    destination = classify_mijngeldzaken_destination(source)
    payload = build_mijngeldzaken_action_payload(
        source,
        mgz_category,
        default_account=default_account,
    )
    routing_attempt = (
        ledger.get_routing_attempt(int(attempt["routing_attempt_id"]))
        if attempt.get("routing_attempt_id")
        else {}
    ) or {}
    source_proof = {
        "routingAttemptId": attempt.get("routing_attempt_id") or routing_attempt.get("id"),
        "documentId": attempt.get("document_id"),
        "bookkeepingRecordId": (record or {}).get("id") or attempt.get("bookkeeping_record_id"),
        "sourceDocumentId": (document or {}).get("source_document_id"),
        "bankTransactionId": (record or {}).get("bank_transaction_id"),
        "duplicateFingerprint": (document or {}).get("duplicate_fingerprint"),
        "reconciliationStatus": (record or document or {}).get("reconciliation_status"),
    }
    source_proof = {key: value for key, value in source_proof.items() if value not in (None, "")}
    surface = str(destination.get("target_surface") or attempt.get("surface") or "")
    draft = build_mijngeldzaken_master_ledger_draft(
        action_id,
        surface,
        payload,
        source_proof=source_proof,
    )
    return {
        "actionId": action_id,
        "surface": surface or draft.get("surface"),
        "payload": payload,
        "draft": draft,
        "sourceProof": source_proof,
        "destination": destination,
    }


def _source_category_unchanged(source: Dict[str, Any], metadata: Dict[str, Any]) -> bool:
    snapshot = metadata.get("documentSnapshot") if isinstance(metadata.get("documentSnapshot"), dict) else None
    if snapshot is None:
        snapshot = metadata.get("bookkeepingRecordSnapshot") if isinstance(metadata.get("bookkeepingRecordSnapshot"), dict) else None
    if not snapshot:
        return False
    snapshot_category = snapshot.get("category")
    if snapshot_category in (None, ""):
        return False
    return str(source.get("category") or "").strip() == str(snapshot_category).strip()


def _document_data_for_mijngeldzaken(document: Dict[str, Any]) -> Dict[str, Any]:
    extracted = dict(document.get("extracted_data") or {})
    record = document.get("bookkeeping_record") or {}
    record_line_items = record.get("line_items") or []
    if record_line_items:
        extracted["line_items"] = [_line_item_from_record_line(item) for item in record_line_items]
    extracted.setdefault("vendor_name", document.get("vendor_name"))
    extracted.setdefault("transaction_date", document.get("transaction_date"))
    extracted.setdefault("total_amount", document.get("total_amount"))
    extracted.setdefault("vat_amount", document.get("vat_amount"))
    extracted.setdefault("document_type", document.get("document_type"))
    return {
        "id": document.get("id"),
        "document_type": document.get("document_type"),
        "vendor_name": document.get("vendor_name"),
        "category": document.get("category"),
        "transaction_date": document.get("transaction_date"),
        "total_amount": document.get("total_amount"),
        "vat_amount": document.get("vat_amount"),
        "description": document.get("original_filename"),
        "line_items": extracted.get("line_items") or extracted.get("lineItems") or [],
        "extracted_data": extracted,
    }


def _record_data_for_mijngeldzaken(record: Dict[str, Any]) -> Dict[str, Any]:
    amount = _positive_amount(record.get("amount"))
    extracted = {
        "vendor_name": record.get("vendor_name"),
        "transaction_date": record.get("record_date"),
        "total_amount": amount,
        "currency": record.get("currency"),
        "description": record.get("description"),
        "document_type": "receipt",
        "line_items": [_line_item_from_record_line(item) for item in record.get("line_items") or []],
    }
    return {
        "id": record.get("id"),
        "document_type": "receipt",
        "vendor_name": record.get("vendor_name"),
        "category": record.get("category"),
        "transaction_date": record.get("record_date"),
        "total_amount": amount,
        "vat_amount": record.get("vat_amount"),
        "description": record.get("description"),
        "line_items": extracted["line_items"],
        "extracted_data": extracted,
    }


def _line_item_from_record_line(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "description": item.get("description") or item.get("item_name"),
        "amount": item.get("amount"),
        "category": item.get("category"),
        "accountName": item.get("account_name"),
        "quantity": item.get("quantity"),
        "unitPrice": item.get("unit_price"),
        "taxCode": item.get("tax_code"),
        "taxAmount": item.get("tax_amount"),
    }


def _mijngeldzaken_category(source: Dict[str, Any], config: Dict[str, Any]) -> str:
    category = str(source.get("category") or "").strip()
    mapping = config.get("mijngeldzaken_category_mapping") or config.get("fab_mijngeldzaken_category_mapping") or {}
    if isinstance(mapping, dict):
        return str(mapping.get(category) or category or "Overig")
    return category or "Overig"


def _config_value(config: Dict[str, Any], *keys: str, default: str) -> str:
    for key in keys:
        value = config.get(key)
        if value not in (None, ""):
            return str(value)
    return default


def _positive_amount(value: Any) -> Any:
    if value is None:
        return None
    try:
        return abs(float(value))
    except (TypeError, ValueError):
        return value


def _update_record_export_state(
    ledger: LocalOperationsLedger,
    record: Dict[str, Any],
    export_status: str,
    status: Optional[str] = None,
    routing_attempt_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    metadata = dict(record.get("metadata") or {})
    metadata["latestExport"] = {
        "status": export_status,
        "routingAttemptId": routing_attempt_id,
        "details": details or {},
    }
    update: Dict[str, Any] = {
        "exportStatus": export_status,
        "metadata": metadata,
    }
    if status:
        update["status"] = status
    ledger.update_bookkeeping_record(int(record["id"]), update)


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def _external_submission_for_result(status: str) -> str:
    if status in {"executed", "submitted"}:
        return "executed"
    if status == "queued":
        return "queued"
    return "failed"


def _message_for_result(status: str) -> str:
    if status in {"executed", "submitted"}:
        return "External export result recorded."
    if status == "queued":
        return "External export queued by a separate executor."
    return "External export failure recorded."


def _map_execution_status(status: str, target_system: Any = "waveapps") -> tuple[str, str, str]:
    target_label = _target_label(target_system)
    if status in {"success", "executed"}:
        return "executed", "executed", f"{target_label} execution completed successfully."
    if status == "submitted":
        return "submitted", "submitted", f"{target_label} external execution submitted."
    if status == "queued":
        return "queued", "queued", f"{target_label} execution queued for external processing."
    if status == "blocked_requires_confirmation":
        return "not_executed", "approved", "Execution is waiting for explicit confirmed action settings."
    if status == "blocked_requires_credentials":
        return "not_executed", "approved", "Execution is waiting for external credentials."
    if status == "needs_review":
        return "not_executed", "approved", "Execution needs additional review before it can run."
    return "failed", "failed", f"{target_label} execution could not run: {status!r}."


def _record_status_for_execution(status: str) -> str:
    if status == "queued":
        return "queued"
    if status in {"executed", "submitted"}:
        return "executed"
    return "failed"


def _list_optional_strs(value: Any) -> Optional[list[str]]:
    if value is None:
        return None
    if isinstance(value, (list, tuple, set)):
        result = [str(item) for item in value if str(item)]
        return result or None
    text = str(value).strip()
    if not text:
        return None
    if "," in text:
        return [item.strip() for item in text.split(",") if item.strip()]
    if ";" in text:
        return [item.strip() for item in text.split(";") if item.strip()]
    return [text]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
