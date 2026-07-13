import hashlib
import json
import os
from calendar import monthrange
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional

from src.operations.local_ledger import LocalOperationsLedger
from src.operations.local_reporting import EXCLUDED_RECORD_STATUSES, LocalFinancialReportingService


COMPLIANCE_VERSION = "fab-dutch-vat-compliance-v1"
OPEN_FINDING_STATUSES = ("open", "acknowledged")
DEFAULT_VAT_RATES = (0.0, 9.0, 21.0)


class LocalComplianceService:
    """Create provisional Dutch VAT and document-retention evidence from FAB records."""

    def __init__(self, ledger: LocalOperationsLedger, config: Optional[Dict[str, Any]] = None):
        self.ledger = ledger
        self.config = config or {}
        self.retention_years = _bounded_int(
            self.config.get("document_retention_years")
            or self.config.get("operations_document_retention_years"),
            default=7,
            minimum=1,
            maximum=20,
        )
        self.vat_rate_tolerance = _bounded_float(
            self.config.get("vat_rate_tolerance_percentage_points")
            or self.config.get("operations_vat_rate_tolerance_percentage_points"),
            default=0.75,
            minimum=0.01,
            maximum=5.0,
        )
        self.allowed_vat_rates = _vat_rates(self.config)

    def assess(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        basis: str = "accrual",
        target_system: Optional[str] = None,
        actor: str = "local_compliance",
        today: Optional[date] = None,
    ) -> Dict[str, Any]:
        from_date, to_date = _period(from_date, to_date, today=today)
        basis = str(basis or "accrual").strip().lower()
        if basis != "accrual":
            raise ValueError("Dutch VAT compliance assessment currently requires accrual basis")
        target_system = str(target_system or "").strip() or None
        records = self.ledger.list_bookkeeping_records(
            target_system=target_system,
            from_date=from_date,
            to_date=to_date,
            limit=500,
        )
        scoped_count = self.ledger.count_bookkeeping_records(
            target_system=target_system,
            from_date=from_date,
            to_date=to_date,
        )
        report = LocalFinancialReportingService(self.ledger, self.config).generate(
            report_type="vat",
            basis="accrual",
            from_date=from_date,
            to_date=to_date,
            target_system=target_system,
            include_rows=True,
        )
        source_checksum = self._source_checksum(records, report, scoped_count)
        assessment_key = hashlib.sha256(
            f"{COMPLIANCE_VERSION}|{from_date}|{to_date}|{basis}|{target_system or '*'}|{source_checksum}".encode("utf-8")
        ).hexdigest()
        findings = self._findings(records, report, scoped_count)
        retention_records = self._retention_records(records, today=today)
        blocking_count = sum(1 for finding in findings if finding["severity"] == "high")
        attention_count = sum(1 for finding in findings if finding["severity"] in {"medium", "low"})
        status = "blocked" if blocking_count else "needs_review" if findings else "ready"
        vat_summary = (report.get("report") or {}).get("byCurrency") or []
        stored = self.ledger.create_compliance_assessment(
            {
                "assessmentKey": assessment_key,
                "periodFrom": from_date,
                "periodTo": to_date,
                "basis": basis,
                "targetSystem": target_system,
                "status": status,
                "recordCount": scoped_count,
                "findingCount": len(findings),
                "blockingCount": blocking_count,
                "attentionCount": attention_count,
                "vatSummary": vat_summary,
                "sourceChecksum": source_checksum,
                "metadata": {
                    "complianceVersion": COMPLIANCE_VERSION,
                    "loadedRecordCount": len(records),
                    "truncated": scoped_count > len(records),
                    "allowedVatRates": list(self.allowed_vat_rates),
                    "vatRateTolerancePercentagePoints": self.vat_rate_tolerance,
                    "retentionYears": self.retention_years,
                    "filingStatus": "not_filed",
                    "externalFiling": "not_executed",
                },
            },
            findings=findings,
            retention_records=retention_records,
        )
        assessment = stored["assessment"]
        assessment_findings = self.ledger.list_compliance_findings(
            assessment_id=assessment["id"],
            limit=500,
        )
        if stored["created"]:
            self.ledger.record_audit_event({
                "action": "local_compliance.assessment_created",
                "entityType": "compliance_assessment",
                "entityId": str(assessment["id"]),
                "details": {
                    "actor": actor,
                    "period": {"fromDate": from_date, "toDate": to_date},
                    "status": status,
                    "recordCount": scoped_count,
                    "findingCount": len(findings),
                    "blockingCount": blocking_count,
                    "sourceChecksum": source_checksum,
                    "statutoryStatus": "provisional",
                    "externalFiling": "not_executed",
                },
            })
        return {
            "success": True,
            "status": "assessed" if stored["created"] else "already_current",
            "created": stored["created"],
            "assessment": assessment,
            "findings": assessment_findings,
            "retentionRecords": [
                record for record in self.ledger.list_retention_records(limit=500)
                if record.get("assessment_id") == assessment["id"]
            ],
            "statutoryStatus": "provisional",
            "filingStatus": "not_filed",
            "externalFiling": "not_executed",
        }

    def update_finding(
        self,
        finding_id: int,
        status: str,
        resolution: Optional[str] = None,
        actor: str = "local_user",
    ) -> Dict[str, Any]:
        previous = self.ledger.get_compliance_finding(finding_id)
        if not previous:
            return {"success": False, "status": "not_found", "finding": None}
        finding = self.ledger.update_compliance_finding_status(finding_id, status, resolution=resolution)
        self.ledger.record_audit_event({
            "action": "local_compliance.finding_status_changed",
            "entityType": "compliance_finding",
            "entityId": str(finding_id),
            "details": {
                "actor": actor,
                "fromStatus": previous.get("status"),
                "toStatus": status,
                "resolution": resolution,
                "code": previous.get("code"),
                "externalFiling": "not_executed",
            },
        })
        return {
            "success": True,
            "status": "updated",
            "finding": finding,
            "externalFiling": "not_executed",
        }

    def summary(self) -> Dict[str, Any]:
        assessments = self.ledger.list_compliance_assessments(limit=1)
        latest = assessments[0] if assessments else None
        open_findings = self.ledger.list_compliance_findings(
            assessment_id=latest.get("id") if latest else None,
            status=OPEN_FINDING_STATUSES,
            limit=500,
        ) if latest else []
        return {
            "latestAssessment": latest,
            "assessmentCount": self.ledger.dashboard_metrics().get("compliance_assessments", 0),
            "openFindings": len(open_findings),
            "blockingFindings": sum(1 for finding in open_findings if finding.get("severity") == "high"),
            "attentionFindings": sum(1 for finding in open_findings if finding.get("severity") in {"medium", "low"}),
            "retentionRecords": self.ledger.dashboard_metrics().get("retention_records", 0),
            "statutoryStatus": "provisional",
            "filingStatus": "not_filed",
            "externalFiling": "not_executed",
        }

    def _findings(self, records: list, report: Dict[str, Any], scoped_count: int) -> list:
        findings = []
        if scoped_count > len(records):
            findings.append(_finding(
                "record_limit_reached",
                "high",
                "Assessment record limit reached",
                f"{scoped_count - len(records)} record(s) were not loaded into this assessment.",
                evidence={"scopedRecordCount": scoped_count, "loadedRecordCount": len(records)},
            ))
        for blocker in (report.get("summary") or {}).get("blockers") or []:
            code = str(blocker.get("code") or "report_completeness_gate")
            if code == "record_limit_reached":
                continue
            severity = "high" if code == "vat_exceeds_gross" else "medium"
            findings.append(_finding(
                f"report_{code}",
                severity,
                "VAT report completeness gate",
                f"VAT report gate {code} affects {blocker.get('count', 0)} record(s).",
                evidence=blocker,
            ))

        for record in records:
            if str(record.get("status") or "") in EXCLUDED_RECORD_STATUSES:
                continue
            record_id = int(record["id"])
            document_id = record.get("document_id")
            gross = abs(_decimal(record.get("amount")))
            vat_value = record.get("vat_amount")
            vat = abs(_decimal(vat_value)) if vat_value is not None else None
            if vat is not None and vat > gross:
                findings.append(_finding(
                    "vat_exceeds_gross",
                    "high",
                    "VAT exceeds gross amount",
                    f"Record #{record_id} has VAT greater than its gross amount.",
                    record_id=record_id,
                    document_id=document_id,
                    evidence={"grossAmount": float(gross), "vatAmount": float(vat)},
                ))
                continue
            if vat is None and _business_target(record.get("target_system")) and gross > 0:
                findings.append(_finding(
                    "vat_classification_missing",
                    "low",
                    "VAT classification is missing",
                    f"Business record #{record_id} has no explicit VAT amount or exemption evidence.",
                    record_id=record_id,
                    document_id=document_id,
                    evidence={"targetSystem": record.get("target_system"), "category": record.get("category")},
                ))
            if vat is not None and vat > 0:
                net = gross - vat
                effective_rate = (vat / net * Decimal("100")) if net > 0 else None
                if effective_rate is not None and not _rate_matches(
                    float(effective_rate),
                    self.allowed_vat_rates,
                    self.vat_rate_tolerance,
                ):
                    findings.append(_finding(
                        "vat_rate_unrecognized",
                        "medium",
                        "VAT rate needs review",
                        f"Record #{record_id} implies a VAT rate of {float(effective_rate):.2f}%.",
                        record_id=record_id,
                        document_id=document_id,
                        evidence={
                            "grossAmount": float(gross),
                            "vatAmount": float(vat),
                            "netAmount": float(net),
                            "effectiveRate": round(float(effective_rate), 4),
                            "allowedRates": list(self.allowed_vat_rates),
                        },
                    ))
                line_items = record.get("line_items") or []
                taxed_lines = [line for line in line_items if abs(_decimal(line.get("tax_amount"))) > 0]
                missing_codes = [line.get("id") for line in taxed_lines if not str(line.get("tax_code") or "").strip()]
                if not line_items or missing_codes:
                    findings.append(_finding(
                        "vat_tax_code_missing",
                        "medium",
                        "VAT tax code is missing",
                        f"Record #{record_id} has VAT evidence without complete line-level tax codes.",
                        record_id=record_id,
                        document_id=document_id,
                        evidence={"missingLineItemIds": missing_codes, "lineItemCount": len(line_items)},
                    ))
                unsupported_rates = sorted({
                    float(line["tax_rate"])
                    for line in line_items
                    if line.get("tax_rate") is not None
                    and not _rate_matches(
                        float(line["tax_rate"]),
                        self.allowed_vat_rates,
                        self.vat_rate_tolerance,
                    )
                })
                if unsupported_rates:
                    findings.append(_finding(
                        "line_tax_rate_unrecognized",
                        "medium",
                        "Line VAT rate needs review",
                        f"Record #{record_id} contains unsupported line VAT rates.",
                        record_id=record_id,
                        document_id=document_id,
                        evidence={"unsupportedRates": unsupported_rates, "allowedRates": list(self.allowed_vat_rates)},
                    ))
                if str(record.get("currency") or "EUR").upper() != "EUR":
                    findings.append(_finding(
                        "vat_currency_conversion_required",
                        "medium",
                        "EUR conversion evidence required",
                        f"Record #{record_id} contains VAT in {record.get('currency')} and needs EUR conversion evidence.",
                        record_id=record_id,
                        document_id=document_id,
                        evidence={"currency": record.get("currency"), "vatAmount": float(vat)},
                    ))
            if document_id:
                document = self.ledger.get_document(int(document_id))
                storage_path = (document or {}).get("storage_path")
                if storage_path and not os.path.isfile(storage_path):
                    findings.append(_finding(
                        "source_document_missing",
                        "high",
                        "Source document is unavailable",
                        f"The source file linked to record #{record_id} is not present at its recorded path.",
                        record_id=record_id,
                        document_id=document_id,
                        evidence={"filename": (document or {}).get("original_filename"), "storagePath": storage_path},
                    ))
        return _deduplicate_findings(findings)

    def _retention_records(self, records: list, today: Optional[date] = None) -> list:
        today = today or datetime.now(timezone.utc).date()
        retention = []
        seen_documents = set()
        for record in records:
            document_id = record.get("document_id")
            if not document_id or document_id in seen_documents:
                continue
            seen_documents.add(document_id)
            document = self.ledger.get_document(int(document_id)) or {}
            source_date = _parse_date(record.get("record_date"))
            retain_until = _add_years(source_date, self.retention_years) if source_date else None
            storage_path = document.get("storage_path")
            source_file_present = os.path.isfile(storage_path) if storage_path else None
            if not source_date:
                status = "missing_source_date"
            elif retain_until and today > retain_until:
                status = "retention_review_eligible"
            else:
                status = "retain_required"
            retention.append({
                "documentId": int(document_id),
                "sourceDate": source_date.isoformat() if source_date else None,
                "retentionYears": self.retention_years,
                "retainUntil": retain_until.isoformat() if retain_until else None,
                "status": status,
                "sourceFilePresent": source_file_present,
                "metadata": {
                    "filename": document.get("original_filename"),
                    "deletionAuthorized": False,
                    "externalFiling": "not_executed",
                },
            })
        return retention

    def _source_checksum(self, records: list, report: Dict[str, Any], scoped_count: int) -> str:
        document_evidence = {}
        for record in records:
            document_id = record.get("document_id")
            if not document_id or document_id in document_evidence:
                continue
            document = self.ledger.get_document(int(document_id)) or {}
            storage_path = document.get("storage_path")
            present = bool(storage_path and os.path.isfile(storage_path))
            document_evidence[document_id] = {
                "updatedAt": document.get("updated_at"),
                "storagePath": storage_path,
                "sourceFilePresent": present if storage_path else None,
                "sourceFileSize": os.path.getsize(storage_path) if present else None,
                "sourceFileModifiedAt": os.path.getmtime(storage_path) if present else None,
            }
        payload = {
            "scopedRecordCount": scoped_count,
            "reportSummary": report.get("summary"),
            "documents": document_evidence,
            "records": [
                {
                    "id": record.get("id"),
                    "updatedAt": record.get("updated_at"),
                    "status": record.get("status"),
                    "amount": record.get("amount"),
                    "vatAmount": record.get("vat_amount"),
                    "currency": record.get("currency"),
                    "category": record.get("category"),
                    "targetAccount": record.get("target_account"),
                    "reconciliationStatus": record.get("reconciliation_status"),
                    "lineItems": [
                        {
                            "id": line.get("id"),
                            "amount": line.get("amount"),
                            "taxAmount": line.get("tax_amount"),
                            "taxRate": line.get("tax_rate"),
                            "taxCode": line.get("tax_code"),
                            "updatedAt": line.get("updated_at"),
                        }
                        for line in record.get("line_items") or []
                    ],
                }
                for record in records
            ],
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _finding(
    code: str,
    severity: str,
    title: str,
    message: str,
    record_id: Optional[int] = None,
    document_id: Optional[int] = None,
    evidence: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    fingerprint_source = f"{code}|{record_id or '*'}|{document_id or '*'}|{json.dumps(evidence or {}, sort_keys=True, default=str)}"
    return {
        "fingerprint": hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest(),
        "code": code,
        "severity": severity,
        "status": "open",
        "title": title,
        "message": message,
        "bookkeepingRecordId": record_id,
        "documentId": document_id,
        "evidence": evidence or {},
    }


def _deduplicate_findings(findings: list) -> list:
    unique = {}
    for finding in findings:
        unique[finding["fingerprint"]] = finding
    return list(unique.values())


def _period(from_date: Optional[str], to_date: Optional[str], today: Optional[date] = None) -> tuple[str, str]:
    today = today or datetime.now(timezone.utc).date()
    if from_date:
        start = _parse_date(from_date)
        if not start:
            raise ValueError("fromDate must be YYYY-MM-DD")
    else:
        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        start = date(today.year, quarter_start_month, 1)
    if to_date:
        end = _parse_date(to_date)
        if not end:
            raise ValueError("toDate must be YYYY-MM-DD")
    else:
        end = today
    if start > end:
        raise ValueError("fromDate cannot be later than toDate")
    return start.isoformat(), end.isoformat()


def _parse_date(value: Any) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _add_years(value: date, years: int) -> date:
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        return value.replace(year=value.year + years, day=monthrange(value.year + years, value.month)[1])


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def _vat_rates(config: Dict[str, Any]) -> tuple[float, ...]:
    value = (
        config.get("allowed_vat_rates")
        or config.get("operations_allowed_vat_rates")
        or DEFAULT_VAT_RATES
    )
    if isinstance(value, str):
        value = value.replace(";", ",").split(",")
    try:
        rates = sorted({float(item) for item in value})
    except (TypeError, ValueError):
        rates = list(DEFAULT_VAT_RATES)
    return tuple(rates or DEFAULT_VAT_RATES)


def _rate_matches(rate: float, allowed_rates: tuple[float, ...], tolerance: float) -> bool:
    return any(abs(rate - allowed) <= tolerance for allowed in allowed_rates)


def _business_target(value: Any) -> bool:
    return str(value or "").strip().lower() in {"waveapps", "waveapps_business", "wave_business"}


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(parsed, maximum))


def _bounded_float(value: Any, default: float, minimum: float, maximum: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(parsed, maximum))
