from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Optional

from src.operations.local_ledger import LocalOperationsLedger


HAI_CONNECTOR_VERSION = "fab-hai-connector-v1"
DEFAULT_HAI_COMMAND_IDS = (
    "rescan_intake",
    "process_imported",
    "reprocess_incomplete",
    "sync_sources",
    "run_safe_cycle",
    "run_due_recovery",
    "run_reconciliation",
    "refresh_notifications",
    "run_due_reports",
    "assess_compliance",
    "record_wave_attachment_verification",
    "archive_verified_drive_sources",
)


@dataclass(frozen=True)
class HaiCommand:
    command_id: str
    label: str
    description: str
    input_schema: Dict[str, Any]
    mode: str = "safe_local_operation"
    risk: str = "low"
    requires_human_approval: bool = False
    external_submission: str = "not_executed"

    def as_dict(self, allowed: bool) -> Dict[str, Any]:
        return {
            "commandId": self.command_id,
            "label": self.label,
            "description": self.description,
            "mode": self.mode,
            "risk": self.risk,
            "requiresHumanApproval": self.requires_human_approval,
            "allowed": allowed,
            "inputSchema": self.input_schema,
            "externalSubmission": self.external_submission,
        }


def _bounded_limit_schema(default: int, maximum: int) -> Dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": maximum,
                "default": default,
            }
        },
    }


HAI_COMMANDS = (
    HaiCommand(
        "rescan_intake",
        "Rescan intake folders",
        "Register new local documents without changing downstream bookkeeping systems.",
        {"type": "object", "additionalProperties": False, "properties": {}},
    ),
    HaiCommand(
        "process_imported",
        "Process imported documents",
        "Run OCR, validation, duplicate checks, and classification for imported documents.",
        _bounded_limit_schema(25, 100),
    ),
    HaiCommand(
        "reprocess_incomplete",
        "Recover incomplete OCR",
        "Retry only review-gated documents with blank OCR after creating a local ledger backup.",
        _bounded_limit_schema(25, 100),
    ),
    HaiCommand(
        "sync_sources",
        "Sync document sources",
        "Collect documents from configured read-only source connectors.",
        {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "sources": {
                    "type": "array",
                    "uniqueItems": True,
                    "items": {
                        "type": "string",
                        "enum": ["gmail", "google_drive", "freshdesk", "google_photos"],
                    },
                }
            },
        },
    ),
    HaiCommand(
        "run_safe_cycle",
        "Run safe autonomous cycle",
        "Run the local collect, process, classify, reconcile, and draft-planning cycle.",
        {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 25},
                "dryRun": {"type": "boolean", "default": False},
            },
        },
    ),
    HaiCommand(
        "run_due_recovery",
        "Run due recovery",
        "Retry only recovery steps already classified by FAB as safe and due.",
        _bounded_limit_schema(5, 50),
    ),
    HaiCommand(
        "run_reconciliation",
        "Run reconciliation",
        "Match imported bank transactions against document-backed bookkeeping records.",
        _bounded_limit_schema(100, 500),
    ),
    HaiCommand(
        "refresh_notifications",
        "Refresh notifications",
        "Rebuild the local in-app notification inbox from current bookkeeping state.",
        {"type": "object", "additionalProperties": False, "properties": {}},
    ),
    HaiCommand(
        "run_due_reports",
        "Run due reports",
        "Generate report artifacts that are due according to the configured local schedule.",
        {"type": "object", "additionalProperties": False, "properties": {}},
    ),
    HaiCommand(
        "assess_compliance",
        "Assess Dutch VAT compliance",
        "Prepare a provisional Dutch VAT and retention assessment for human review.",
        {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "fromDate": {"type": "string", "format": "date"},
                "toDate": {"type": "string", "format": "date"},
                "targetSystem": {"type": "string", "maxLength": 100},
            },
        },
    ),
    HaiCommand(
        "record_wave_attachment_verification",
        "Record Wave attachment attestation",
        "Record transaction metadata for one configured Drive source; binary readback is still required before archival.",
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["documentId", "evidence"],
            "properties": {
                "documentId": {"type": "integer", "minimum": 1},
                "evidence": {"type": "object"},
            },
        },
        mode="governed_evidence_recording",
        risk="medium",
    ),
    HaiCommand(
        "archive_verified_drive_sources",
        "Archive verified Drive sources",
        "Move only sources whose Wave transaction and exact attachment evidence pass every configured gate.",
        {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 25},
                "dryRun": {"type": "boolean", "default": True},
            },
        },
        mode="preauthorized_policy_gated_move",
        risk="medium",
        external_submission="policy_gated",
    ),
)


class LocalHaiConnector:
    """Expose a fail-closed, audited command contract for a future HAI controller."""

    def __init__(
        self,
        ledger: LocalOperationsLedger,
        config: Optional[Dict[str, Any]] = None,
        executors: Optional[Dict[str, Callable[[Dict[str, Any], str], Dict[str, Any]]]] = None,
    ):
        self.ledger = ledger
        self.config = config or {}
        self.executors = executors or {}
        self.enabled = _bool_config(self.config.get("fab_hai_connector_enabled"), default=False)
        self.api_token_configured = bool(
            self.config.get("fab_local_api_token")
            or self.config.get("fab_operations_api_token")
            or self.config.get("operations_api_token")
        )
        self.allowed_command_ids = _allowed_commands(self.config.get("fab_hai_allowed_commands"))
        self._commands = {command.command_id: command for command in HAI_COMMANDS}

    def manifest(self) -> Dict[str, Any]:
        return {
            "connector": "hai",
            "version": HAI_CONNECTOR_VERSION,
            "enabled": self.enabled,
            "status": "ready" if self.enabled else "prepared_disabled",
            "transport": "authenticated_local_http" if self.api_token_configured else "loopback_local_http",
            "authentication": "bearer_token" if self.api_token_configured else "loopback_origin_controls",
            "sourceOfTruth": "fab_local_ledger",
            "idempotencyField": "requestId",
            "executionPolicy": "explicit_allowlist",
            "commands": [
                command.as_dict(command.command_id in self.allowed_command_ids)
                for command in HAI_COMMANDS
            ],
            "resources": [
                {
                    "resourceId": "google_drive_binary_relay",
                    "label": "Google Drive binary relay",
                    "description": "Idempotently hand exact configured-folder Drive bytes into FAB with provider identity and hash checks.",
                    "method": "POST",
                    "path": "/api/connectors/google-drive/relay",
                    "contentType": "multipart/form-data",
                    "mode": "authenticated_source_intake",
                    "externalSubmission": "not_executed",
                },
                {
                    "resourceId": "wave_attachment_work_orders",
                    "label": "Wave attachment work orders",
                    "description": "Evidence-bound Drive source, Wave field, attachment readback, and archive-gate handoff.",
                    "method": "GET",
                    "path": "/api/drive-wave/work-orders",
                    "mode": "read_only_executor_handoff",
                    "externalSubmission": "not_executed",
                },
                {
                    "resourceId": "wave_attachment_binary_readback",
                    "label": "Wave attachment binary readback",
                    "description": "Submit the receipt downloaded from one uniquely matched, reviewed Wave transaction so FAB verifies its entry binding, hash, size, filename, and bookkeeping evidence.",
                    "method": "POST",
                    "pathTemplate": "/api/drive-wave/documents/{documentId}/attachment-readback",
                    "contentType": "multipart/form-data",
                    "mode": "governed_binary_evidence",
                    "externalSubmission": "verified_readback",
                }
            ],
            "excludedCapabilities": [
                "approve_review_items",
                "approve_exports",
                "submit_to_wave",
                "submit_to_mijngeldzaken",
                "restore_backups",
                "change_access_control",
                "delete_drive_sources",
            ],
            "externalSubmission": "not_executed",
        }

    def status(self) -> Dict[str, Any]:
        manifest = self.manifest()
        return {
            "connector": manifest["connector"],
            "version": manifest["version"],
            "enabled": manifest["enabled"],
            "status": manifest["status"],
            "allowedCommandIds": sorted(self.allowed_command_ids),
            "availableExecutors": sorted(self.executors),
            "commandCount": len(manifest["commands"]),
            "resourceCount": len(manifest["resources"]),
            "externalSubmission": "not_executed",
        }

    def plan(self, command_id: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        command = self._commands.get(str(command_id or "").strip())
        if command is None:
            return self._blocked_plan(command_id, "unsupported", "Command is not in the HAI manifest.")
        try:
            normalized_payload = _normalize_payload(command.command_id, payload or {})
        except ValueError as exc:
            return self._blocked_plan(command.command_id, "invalid", str(exc), command=command)
        if not self.enabled:
            return self._blocked_plan(
                command.command_id,
                "connector_disabled",
                "Enable fab_hai_connector_enabled before machine execution.",
                command=command,
                payload=normalized_payload,
            )
        if command.command_id not in self.allowed_command_ids:
            return self._blocked_plan(
                command.command_id,
                "not_allowed",
                "Command is not in fab_hai_allowed_commands.",
                command=command,
                payload=normalized_payload,
            )
        if command.command_id not in self.executors:
            return self._blocked_plan(
                command.command_id,
                "executor_unavailable",
                "The local executor for this command is unavailable.",
                command=command,
                payload=normalized_payload,
            )
        return {
            "success": True,
            "status": "ready",
            "command": command.as_dict(True),
            "payload": normalized_payload,
            "externalSubmission": "not_executed",
        }

    def execute(
        self,
        request_id: str,
        command_id: str,
        payload: Optional[Dict[str, Any]] = None,
        actor: str = "hai",
    ) -> Dict[str, Any]:
        request_id = str(request_id or "").strip()
        actor = str(actor or "hai").strip()[:200] or "hai"
        if not request_id or len(request_id) > 200:
            return self._execution_error("invalid_request", "requestId is required and must be at most 200 characters.")

        previous = self.ledger.find_audit_event(
            action="hai.command.completed",
            entity_type="hai_command_request",
            entity_id=request_id,
        )
        if previous:
            details = previous.get("details") or {}
            return {
                "success": True,
                "status": "already_executed",
                "requestId": request_id,
                "commandId": details.get("commandId") or command_id,
                "result": details.get("result") or {},
                "auditEventId": previous.get("id"),
                "externalSubmission": "not_executed",
            }

        plan = self.plan(command_id, payload)
        if plan.get("status") != "ready":
            return {
                **plan,
                "requestId": request_id,
            }

        normalized_payload = plan["payload"]
        self.ledger.record_audit_event({
            "action": "hai.command.requested",
            "entityType": "hai_command_request",
            "entityId": request_id,
            "details": {
                "requestId": request_id,
                "commandId": command_id,
                "actor": actor,
                "payload": normalized_payload,
                "externalSubmission": "not_executed",
            },
        })
        try:
            result = self.executors[command_id](normalized_payload, actor)
        except Exception as exc:
            audit_event_id = self.ledger.record_audit_event({
                "action": "hai.command.failed",
                "entityType": "hai_command_request",
                "entityId": request_id,
                "details": {
                    "requestId": request_id,
                    "commandId": command_id,
                    "actor": actor,
                    "error": str(exc),
                    "externalSubmission": "not_executed",
                },
            })
            return {
                "success": False,
                "status": "failed",
                "requestId": request_id,
                "commandId": command_id,
                "error": str(exc),
                "auditEventId": audit_event_id,
                "externalSubmission": "not_executed",
            }

        audit_event_id = self.ledger.record_audit_event({
            "action": "hai.command.completed",
            "entityType": "hai_command_request",
            "entityId": request_id,
            "details": {
                "requestId": request_id,
                "commandId": command_id,
                "actor": actor,
                "payload": normalized_payload,
                "result": result,
                "externalSubmission": "not_executed",
            },
        })
        return {
            "success": True,
            "status": "completed",
            "requestId": request_id,
            "commandId": command_id,
            "result": result,
            "auditEventId": audit_event_id,
            "externalSubmission": "not_executed",
        }

    @staticmethod
    def _execution_error(status: str, error: str) -> Dict[str, Any]:
        return {
            "success": False,
            "status": status,
            "error": error,
            "externalSubmission": "not_executed",
        }

    def _blocked_plan(
        self,
        command_id: str,
        status: str,
        error: str,
        command: Optional[HaiCommand] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "success": False,
            "status": status,
            "commandId": command_id,
            "command": command.as_dict(command.command_id in self.allowed_command_ids) if command else None,
            "payload": payload or {},
            "error": error,
            "externalSubmission": "not_executed",
        }


def _allowed_commands(value: Any) -> set:
    if value is None:
        return set()
    if isinstance(value, str):
        raw_values: Iterable[Any] = value.replace("\n", ",").split(",")
    elif isinstance(value, (list, tuple, set)):
        raw_values = value
    else:
        return set()
    known = set(DEFAULT_HAI_COMMAND_IDS)
    return {
        str(item).strip()
        for item in raw_values
        if str(item).strip() in known
    }


def _bool_config(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "enabled"}


def _normalize_payload(command_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object.")
    allowed_fields = {
        "rescan_intake": set(),
        "process_imported": {"limit"},
        "reprocess_incomplete": {"limit"},
        "sync_sources": {"sources"},
        "run_safe_cycle": {"limit", "dryRun"},
        "run_due_recovery": {"limit"},
        "run_reconciliation": {"limit"},
        "refresh_notifications": set(),
        "run_due_reports": set(),
        "assess_compliance": {"fromDate", "toDate", "targetSystem"},
        "record_wave_attachment_verification": {"documentId", "evidence"},
        "archive_verified_drive_sources": {"limit", "dryRun"},
    }[command_id]
    unexpected = sorted(set(payload) - allowed_fields)
    if unexpected:
        raise ValueError(f"Unsupported payload field(s): {', '.join(unexpected)}")

    normalized: Dict[str, Any] = {}
    if "limit" in payload:
        maximum = 500 if command_id == "run_reconciliation" else 50 if command_id == "run_due_recovery" else 100
        try:
            limit = int(payload["limit"])
        except (TypeError, ValueError):
            raise ValueError("limit must be an integer.")
        if limit < 1 or limit > maximum:
            raise ValueError(f"limit must be between 1 and {maximum}.")
        normalized["limit"] = limit
    if "dryRun" in payload:
        if not isinstance(payload["dryRun"], bool):
            raise ValueError("dryRun must be a boolean.")
        normalized["dryRun"] = payload["dryRun"]
    if "documentId" in payload:
        try:
            document_id = int(payload["documentId"])
        except (TypeError, ValueError):
            raise ValueError("documentId must be a positive integer.")
        if document_id < 1:
            raise ValueError("documentId must be a positive integer.")
        normalized["documentId"] = document_id
    if "evidence" in payload:
        evidence = payload["evidence"]
        if not isinstance(evidence, dict):
            raise ValueError("evidence must be an object.")
        allowed_evidence = {
            "externalTransactionId", "businessId", "sourceSha256", "uploadSourceSha256",
            "attachmentSha256", "attachmentObjectId", "attachmentMimeType", "attachmentFilename",
            "attachmentSizeBytes",
            "attachmentPresent", "attachmentOpened", "attachmentDownloaded", "attachmentTransactionId",
            "transactionExists", "transactionStatus", "transactionMatchCount", "matchingTransactionIds",
            "transactionPageUrl", "transactionReviewed", "waveObservedAt", "fieldMatches",
            "observedFields", "expectedFieldsDigest",
            "verifiedAt", "verifier",
        }
        unexpected_evidence = sorted(set(evidence) - allowed_evidence)
        if unexpected_evidence:
            raise ValueError(f"Unsupported evidence field(s): {', '.join(unexpected_evidence)}")
        if "observedFields" in evidence and not isinstance(evidence["observedFields"], dict):
            raise ValueError("evidence.observedFields must be an object.")
        if "matchingTransactionIds" in evidence and not isinstance(evidence["matchingTransactionIds"], list):
            raise ValueError("evidence.matchingTransactionIds must be a list.")
        normalized["evidence"] = dict(evidence)
    if "sources" in payload:
        sources = payload["sources"]
        if not isinstance(sources, list) or not all(isinstance(item, str) for item in sources):
            raise ValueError("sources must be a list of connector identifiers.")
        known_sources = {"gmail", "google_drive", "freshdesk", "google_photos"}
        normalized_sources = sorted({item.strip() for item in sources})
        unknown = sorted(set(normalized_sources) - known_sources)
        if unknown:
            raise ValueError(f"Unsupported connector source(s): {', '.join(unknown)}")
        normalized["sources"] = normalized_sources
    for field in ("fromDate", "toDate", "targetSystem"):
        if field in payload:
            value = str(payload[field] or "").strip()
            if not value:
                continue
            if len(value) > 100:
                raise ValueError(f"{field} must be at most 100 characters.")
            normalized[field] = value
    return normalized
