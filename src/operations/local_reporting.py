import csv
import io
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, Optional

from src.operations.local_ledger import LocalOperationsLedger


REPORT_VERSION = "fab-local-financial-report-v1"
REPORT_TYPES = {"overview", "profit_and_loss", "vat", "cash_flow", "expenses"}
REPORT_BASES = {"accrual", "cash"}
EXCLUDED_RECORD_STATUSES = {"duplicate", "failed", "ignored", "rejected"}
FINAL_RECONCILIATION_STATUSES = {"approved", "reconciled"}
LINKED_BANK_RECONCILIATION_STATUSES = FINAL_RECONCILIATION_STATUSES | {"candidate", "needs_review"}
REPORT_RECORD_LIMIT = 500
CENT = Decimal("0.01")


class LocalFinancialReportingService:
    """Build provisional, reconciliation-aware reports from FAB's normalized ledger."""

    def __init__(self, ledger: LocalOperationsLedger, config: Optional[Dict[str, Any]] = None):
        self.ledger = ledger
        self.config = config or {}

    def generate(
        self,
        report_type: str = "overview",
        basis: str = "accrual",
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        target_system: Optional[str] = None,
        include_rows: bool = False,
    ) -> Dict[str, Any]:
        report_type = _report_type(report_type)
        basis = _basis(basis)
        from_date, to_date = _period(from_date, to_date)
        target_system = str(target_system or "").strip() or None

        records = self.ledger.list_bookkeeping_records(
            target_system=target_system,
            from_date=from_date,
            to_date=to_date,
            limit=REPORT_RECORD_LIMIT,
        )
        scoped_count = self.ledger.count_bookkeeping_records(
            target_system=target_system,
            from_date=from_date,
            to_date=to_date,
        )
        undated_count = self.ledger.count_undated_bookkeeping_records(
            target_system=target_system,
            source_type="bank_transaction" if basis == "cash" else None,
            excluded_statuses=sorted(EXCLUDED_RECORD_STATUSES),
        )
        evaluated = [_evaluate_record(record, basis) for record in records]
        included = [item for item in evaluated if item["included"]]
        excluded = [item for item in evaluated if not item["included"]]
        reporting_rows = [item["row"] for item in included]
        bank_rows = [
            _normalized_row(record)
            for record in records
            if str(record.get("source_type") or "") == "bank_transaction"
            and str(record.get("status") or "") not in EXCLUDED_RECORD_STATUSES
            and record.get("amount") is not None
        ]

        reports = {
            "profitAndLoss": _profit_and_loss(reporting_rows),
            "vat": _vat_report(reporting_rows),
            "cashFlow": _cash_flow(bank_rows),
            "expenses": _expense_breakdowns(reporting_rows),
        }
        blockers = _quality_blockers(
            reporting_rows,
            scoped_count=scoped_count,
            loaded_count=len(records),
            undated_count=undated_count,
        )
        selected = _selected_report(report_type, reports)
        payload: Dict[str, Any] = {
            "success": True,
            "reportVersion": REPORT_VERSION,
            "reportType": report_type,
            "generatedAt": _now(),
            "period": {"fromDate": from_date, "toDate": to_date},
            "basis": basis,
            "targetSystem": target_system,
            "currencyPolicy": "separate_totals_per_currency",
            "statutoryStatus": "provisional",
            "externalSubmission": "not_executed",
            "summary": {
                "scopedRecordCount": scoped_count,
                "loadedRecordCount": len(records),
                "includedRecordCount": len(reporting_rows),
                "excludedRecordCount": len(excluded),
                "undatedRecordCount": undated_count,
                "truncated": scoped_count > len(records),
                "readiness": "ready" if not blockers else "needs_review",
                "blockers": blockers,
                "excludedReasons": _reason_counts(excluded),
            },
            "report": selected,
        }
        if report_type == "overview":
            payload["reports"] = reports
        if include_rows:
            payload["rows"] = reporting_rows
            payload["excludedRows"] = [
                {**item["row"], "exclusionReason": item["reason"]}
                for item in excluded
            ]
        return payload

    def csv_artifact(
        self,
        report_type: str = "overview",
        basis: str = "accrual",
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        target_system: Optional[str] = None,
    ) -> Dict[str, Any]:
        report = self.generate(
            report_type=report_type,
            basis=basis,
            from_date=from_date,
            to_date=to_date,
            target_system=target_system,
            include_rows=True,
        )
        columns = [
            "recordId",
            "recordDate",
            "sourceType",
            "recordType",
            "vendorName",
            "category",
            "targetSystem",
            "targetAccount",
            "currency",
            "grossAmount",
            "vatAmount",
            "netAmount",
            "status",
            "reconciliationStatus",
            "reviewRequired",
        ]
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(report.get("rows") or [])
        return {
            "success": True,
            "status": "prepared",
            "filename": f"fab-{report['reportType']}-{report['period']['fromDate']}-{report['period']['toDate']}.csv",
            "contentType": "text/csv",
            "content": output.getvalue(),
            "rowCount": len(report.get("rows") or []),
            "report": report,
            "externalSubmission": "not_executed",
        }

    def record_generation_audit(self, report: Dict[str, Any], actor: str = "fab_local_reporting") -> int:
        return self.ledger.record_audit_event({
            "action": "local_reporting.report_generated",
            "entityType": "financial_report",
            "details": {
                "actor": actor,
                "reportVersion": report.get("reportVersion"),
                "reportType": report.get("reportType"),
                "basis": report.get("basis"),
                "period": report.get("period"),
                "targetSystem": report.get("targetSystem"),
                "includedRecordCount": (report.get("summary") or {}).get("includedRecordCount"),
                "readiness": (report.get("summary") or {}).get("readiness"),
                "externalSubmission": "not_executed",
            },
        })


def _evaluate_record(record: Dict[str, Any], basis: str) -> Dict[str, Any]:
    row = _normalized_row(record)
    status = str(record.get("status") or "")
    source_type = str(record.get("source_type") or "")
    reconciliation_status = str(record.get("reconciliation_status") or "")
    reason = None
    if status in EXCLUDED_RECORD_STATUSES:
        reason = f"record_status_{status}"
    elif record.get("amount") is None:
        reason = "missing_amount"
    elif basis == "cash" and source_type != "bank_transaction":
        reason = "not_cash_evidence"
    elif basis == "accrual" and source_type == "bank_transaction" and reconciliation_status in LINKED_BANK_RECONCILIATION_STATUSES:
        reason = (
            "reconciled_bank_evidence"
            if reconciliation_status in FINAL_RECONCILIATION_STATUSES
            else "pending_reconciliation_bank_evidence"
        )
    return {"included": reason is None, "reason": reason, "row": row}


def _normalized_row(record: Dict[str, Any]) -> Dict[str, Any]:
    gross = _money(record.get("amount"))
    vat = abs(_money(record.get("vat_amount")))
    record_type = str(record.get("record_type") or "expense").lower()
    is_income = record_type in {"income", "revenue", "sales_invoice"}
    absolute_gross = abs(gross)
    net = max(Decimal("0"), absolute_gross - vat)
    return {
        "recordId": record.get("id"),
        "recordDate": record.get("record_date"),
        "sourceType": record.get("source_type"),
        "recordType": "income" if is_income else "expense",
        "vendorName": record.get("vendor_name") or "Unknown",
        "category": record.get("category") or "Unassigned",
        "targetSystem": record.get("target_system"),
        "targetAccount": record.get("target_account"),
        "currency": str(record.get("currency") or "EUR").upper(),
        "grossAmount": _number(absolute_gross),
        "signedAmount": _number(gross),
        "vatAmount": _number(vat),
        "netAmount": _number(net),
        "status": record.get("status"),
        "reconciliationStatus": record.get("reconciliation_status"),
        "reviewRequired": bool(record.get("review_required")),
    }


def _profit_and_loss(rows: list[Dict[str, Any]]) -> Dict[str, Any]:
    totals: Dict[str, Dict[str, Decimal]] = {}
    for row in rows:
        currency = row["currency"]
        bucket = totals.setdefault(currency, {
            "revenueGross": Decimal("0"),
            "revenueVat": Decimal("0"),
            "revenueNet": Decimal("0"),
            "expensesGross": Decimal("0"),
            "expensesVat": Decimal("0"),
            "expensesNet": Decimal("0"),
        })
        prefix = "revenue" if row["recordType"] == "income" else "expenses"
        bucket[f"{prefix}Gross"] += _money(row["grossAmount"])
        bucket[f"{prefix}Vat"] += _money(row["vatAmount"])
        bucket[f"{prefix}Net"] += _money(row["netAmount"])
    by_currency = []
    for currency in sorted(totals):
        bucket = totals[currency]
        by_currency.append({
            "currency": currency,
            **{key: _number(value) for key, value in bucket.items()},
            "netResult": _number(bucket["revenueNet"] - bucket["expensesNet"]),
        })
    return {"byCurrency": by_currency}


def _vat_report(rows: list[Dict[str, Any]]) -> Dict[str, Any]:
    totals: Dict[str, Dict[str, Decimal]] = {}
    for row in rows:
        bucket = totals.setdefault(row["currency"], {"outputVat": Decimal("0"), "inputVat": Decimal("0")})
        key = "outputVat" if row["recordType"] == "income" else "inputVat"
        bucket[key] += _money(row["vatAmount"])
    return {
        "byCurrency": [
            {
                "currency": currency,
                "outputVat": _number(values["outputVat"]),
                "inputVat": _number(values["inputVat"]),
                "netVatPayable": _number(values["outputVat"] - values["inputVat"]),
            }
            for currency, values in sorted(totals.items())
        ],
        "filingStatus": "not_filed",
    }


def _cash_flow(rows: list[Dict[str, Any]]) -> Dict[str, Any]:
    totals: Dict[str, Dict[str, Decimal]] = {}
    for row in rows:
        signed = _money(row["signedAmount"])
        bucket = totals.setdefault(row["currency"], {"inflow": Decimal("0"), "outflow": Decimal("0"), "netMovement": Decimal("0")})
        if signed >= 0:
            bucket["inflow"] += signed
        else:
            bucket["outflow"] += abs(signed)
        bucket["netMovement"] += signed
    return {
        "byCurrency": [
            {"currency": currency, **{key: _number(value) for key, value in values.items()}}
            for currency, values in sorted(totals.items())
        ],
        "source": "bank_transaction_records",
    }


def _expense_breakdowns(rows: list[Dict[str, Any]]) -> Dict[str, Any]:
    expense_rows = [row for row in rows if row["recordType"] == "expense"]
    return {
        "byCategory": _group_expenses(expense_rows, "category", "category"),
        "byVendor": _group_expenses(expense_rows, "vendorName", "vendorName"),
    }


def _group_expenses(rows: list[Dict[str, Any]], source_key: str, output_key: str) -> list[Dict[str, Any]]:
    totals: Dict[tuple[str, str], Dict[str, Decimal]] = {}
    counts: Dict[tuple[str, str], int] = {}
    for row in rows:
        key = (str(row.get(source_key) or "Unknown"), row["currency"])
        bucket = totals.setdefault(key, {"grossAmount": Decimal("0"), "vatAmount": Decimal("0"), "netAmount": Decimal("0")})
        for amount_key in bucket:
            bucket[amount_key] += _money(row[amount_key])
        counts[key] = counts.get(key, 0) + 1
    result = [
        {
            output_key: label,
            "currency": currency,
            "recordCount": counts[(label, currency)],
            **{key: _number(value) for key, value in values.items()},
        }
        for (label, currency), values in totals.items()
    ]
    return sorted(result, key=lambda item: (-float(item["grossAmount"]), item[output_key], item["currency"]))


def _quality_blockers(
    rows: list[Dict[str, Any]],
    scoped_count: int,
    loaded_count: int,
    undated_count: int,
) -> list[Dict[str, Any]]:
    blockers = []
    if scoped_count > loaded_count:
        blockers.append({"code": "record_limit_reached", "count": scoped_count - loaded_count})
    if undated_count:
        blockers.append({"code": "undated_records_outside_period", "count": undated_count})
    checks = {
        "review_required": lambda row: row["reviewRequired"],
        "unassigned_category": lambda row: row["category"] == "Unassigned",
        "unmapped_target_account": lambda row: not row.get("targetAccount"),
        "unreconciled_record": lambda row: str(row.get("reconciliationStatus") or "") not in FINAL_RECONCILIATION_STATUSES,
        "vat_exceeds_gross": lambda row: _money(row["vatAmount"]) > _money(row["grossAmount"]),
    }
    for code, predicate in checks.items():
        count = sum(1 for row in rows if predicate(row))
        if count:
            blockers.append({"code": code, "count": count})
    return blockers


def _reason_counts(excluded: list[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for item in excluded:
        reason = str(item.get("reason") or "unknown")
        counts[reason] = counts.get(reason, 0) + 1
    return counts


def _selected_report(report_type: str, reports: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "overview": reports,
        "profit_and_loss": reports["profitAndLoss"],
        "vat": reports["vat"],
        "cash_flow": reports["cashFlow"],
        "expenses": reports["expenses"],
    }[report_type]


def _report_type(value: Any) -> str:
    normalized = str(value or "overview").strip().lower().replace("-", "_")
    if normalized not in REPORT_TYPES:
        raise ValueError(f"Unsupported report type: {normalized}")
    return normalized


def _basis(value: Any) -> str:
    normalized = str(value or "accrual").strip().lower()
    if normalized not in REPORT_BASES:
        raise ValueError(f"Unsupported reporting basis: {normalized}")
    return normalized


def _period(from_date: Optional[str], to_date: Optional[str]) -> tuple[str, str]:
    today = datetime.now(timezone.utc).date()
    start = _date(from_date, date(today.year, 1, 1))
    end = _date(to_date, today)
    if start > end:
        raise ValueError("fromDate cannot be later than toDate")
    return start.isoformat(), end.isoformat()


def _date(value: Optional[str], default: date) -> date:
    if value in (None, ""):
        return default
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"Invalid ISO date: {value}") from exc


def _money(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def _number(value: Decimal) -> float:
    return float(value.quantize(CENT, rounding=ROUND_HALF_UP))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
