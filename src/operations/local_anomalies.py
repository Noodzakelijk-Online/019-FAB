import re
import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from src.operations.local_ledger import LocalOperationsLedger


ANOMALY_DETECTION_VERSION = "fab-ledger-anomaly-v1"


class LocalLedgerAnomalyService:
    """Detect conservative, evidence-backed anomalies in normalized ledger rows."""

    def __init__(self, ledger: LocalOperationsLedger, config: Optional[Dict[str, Any]] = None):
        self.ledger = ledger
        self.config = config or {}

    def list_issues(self, limit: int = 50) -> List[Dict[str, Any]]:
        if not _bool(self.config.get("anomaly_detection_enabled"), True):
            return []

        scan_limit = _bounded_int(
            self.config.get("anomaly_scan_limit"),
            default=500,
            minimum=25,
            maximum=500,
        )
        records = [
            record
            for record in self.ledger.list_bookkeeping_records(limit=scan_limit)
            if _eligible_record(record)
        ]
        vendor_groups = _group_records(records, "vendor_name")
        category_groups = _group_records(records, "category")
        issues: List[Dict[str, Any]] = []

        for record in records:
            future_issue = self._future_date_issue(record)
            if future_issue:
                issues.append(future_issue)

            amount_issue = self._amount_issue(record, vendor_groups, "vendor")
            if not amount_issue:
                amount_issue = self._amount_issue(record, category_groups, "category")
            if amount_issue:
                issues.append(amount_issue)

        issues.sort(
            key=lambda issue: (
                {"high": 0, "medium": 1, "low": 2}.get(str(issue.get("severity")), 3),
                -float((issue.get("details") or {}).get("anomalyScore") or 0),
                -_integer(issue.get("entityId")),
            )
        )
        return issues[:_bounded_int(limit, default=50, minimum=1, maximum=500)]

    def _amount_issue(
        self,
        record: Dict[str, Any],
        groups: Dict[Tuple[str, str], List[Dict[str, Any]]],
        dimension: str,
    ) -> Optional[Dict[str, Any]]:
        field = "vendor_name" if dimension == "vendor" else "category"
        label = _normalized_label(record.get(field))
        currency = str(record.get("currency") or "EUR").upper()
        if not label:
            return None

        minimum_samples = _bounded_int(
            self.config.get(f"anomaly_minimum_{dimension}_samples"),
            default=5 if dimension == "vendor" else 8,
            minimum=3,
            maximum=100,
        )
        history = [
            _absolute_amount(item.get("amount"))
            for item in groups.get((label, currency), [])
            if item.get("id") != record.get("id")
        ]
        history = [amount for amount in history if amount is not None and amount > 0]
        if len(history) < minimum_samples:
            return None

        amount = _absolute_amount(record.get("amount"))
        minimum_amount = _float(self.config.get("anomaly_minimum_amount"), 100.0)
        if amount is None or amount < minimum_amount:
            return None

        baseline = statistics.median(history)
        if baseline <= 0 or amount <= baseline:
            return None

        deviations = [abs(value - baseline) for value in history]
        median_absolute_deviation = statistics.median(deviations)
        ratio = amount / baseline
        score: Optional[float]
        threshold = _float(self.config.get("anomaly_modified_zscore_threshold"), 3.5)
        ratio_threshold = _float(self.config.get("anomaly_zero_variance_ratio_threshold"), 3.0)
        minimum_difference = _float(self.config.get("anomaly_minimum_difference"), 75.0)

        if median_absolute_deviation > 0:
            score = 0.6745 * (amount - baseline) / median_absolute_deviation
            if score < threshold:
                return None
        else:
            score = None
            if ratio < ratio_threshold or amount - baseline < minimum_difference:
                return None

        high_amount = _float(self.config.get("anomaly_high_amount"), 2500.0)
        high = amount >= high_amount or ratio >= 10 or (score is not None and score >= threshold * 2)
        dimension_value = str(record.get(field) or "").strip()
        issue_type = f"{dimension}_amount_anomaly"
        score_value = round(score if score is not None else ratio, 4)
        comparison = "modified_z_score" if score is not None else "zero_variance_ratio"
        return {
            "severity": "high" if high else "medium",
            "type": issue_type,
            "entityType": "bookkeeping_record",
            "entityId": record.get("id"),
            "message": (
                f"Bookkeeping record #{record.get('id')} has an unusual {currency} "
                f"amount for {dimension} '{dimension_value}'."
            ),
            "ageHours": None,
            "details": {
                "detectionVersion": ANOMALY_DETECTION_VERSION,
                "dimension": dimension,
                "dimensionValue": dimension_value,
                "amount": round(amount, 2),
                "currency": currency,
                "historicalMedian": round(baseline, 2),
                "historicalSampleCount": len(history),
                "medianAbsoluteDeviation": round(median_absolute_deviation, 4),
                "amountToMedianRatio": round(ratio, 4),
                "modifiedZScore": round(score, 4) if score is not None else None,
                "comparison": comparison,
                "anomalyScore": score_value,
                "externalSubmission": "not_executed",
            },
        }

    def _future_date_issue(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        record_date = _parse_date(record.get("record_date"))
        tolerance_days = _bounded_int(
            self.config.get("anomaly_future_date_tolerance_days"),
            default=1,
            minimum=0,
            maximum=31,
        )
        if record_date is None or record_date <= date.today() + timedelta(days=tolerance_days):
            return None
        days_ahead = (record_date - date.today()).days
        return {
            "severity": "high" if days_ahead > 31 else "medium",
            "type": "future_dated_record",
            "entityType": "bookkeeping_record",
            "entityId": record.get("id"),
            "message": (
                f"Bookkeeping record #{record.get('id')} is dated {record_date.isoformat()}, "
                f"{days_ahead} days in the future."
            ),
            "ageHours": None,
            "details": {
                "detectionVersion": ANOMALY_DETECTION_VERSION,
                "recordDate": record_date.isoformat(),
                "daysAhead": days_ahead,
                "anomalyScore": float(days_ahead),
                "externalSubmission": "not_executed",
            },
        }


def _group_records(
    records: List[Dict[str, Any]],
    field: str,
) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        label = _normalized_label(record.get(field))
        if label:
            groups[(label, str(record.get("currency") or "EUR").upper())].append(record)
    return groups


def _eligible_record(record: Dict[str, Any]) -> bool:
    return str(record.get("status") or "") not in {"failed", "duplicate", "deleted"}


def _normalized_label(value: Any) -> str:
    normalized = str(value or "").casefold().strip()
    normalized = re.sub(r"\b(b\.?v\.?|n\.?v\.?|v\.?o\.?f\.?|ltd|llc|inc)\b", " ", normalized)
    normalized = re.sub(r"[^\w]+", " ", normalized, flags=re.UNICODE)
    return re.sub(r"\s+", " ", normalized).strip()


def _absolute_amount(value: Any) -> Optional[float]:
    try:
        if value in (None, ""):
            return None
        return abs(float(value))
    except (TypeError, ValueError):
        return None


def _parse_date(value: Any) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(parsed, maximum))


def _integer(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
