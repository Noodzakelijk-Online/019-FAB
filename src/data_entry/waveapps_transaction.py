"""Safe construction helpers for Wave money-transaction requests."""

from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
from typing import Any, Dict, Optional


WAVE_GRAPHQL_URL = "https://gql.waveapps.com/graphql/public"

MONEY_TRANSACTION_CREATE_MUTATION = """
mutation ($input: MoneyTransactionCreateInput!) {
  moneyTransactionCreate(input: $input) {
    didSucceed
    inputErrors {
      path
      message
      code
    }
    transaction {
      id
    }
  }
}
"""


def build_expense_transaction_input(
    data: Dict[str, Any],
    *,
    business_id: Any,
    anchor_account_id: Any,
    category_mapping: Any,
    category_account_ids: Any,
    default_category_account_id: Any = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a balanced Wave expense transaction from a normalized FAB record."""
    extracted = data.get("extracted_data") if isinstance(data.get("extracted_data"), dict) else {}
    category = str(data.get("category") or "").strip()
    mapped_category = str(_as_mapping(category_mapping).get(category) or category).strip()
    account_ids = _as_mapping(category_account_ids)
    category_account_id = (
        account_ids.get(mapped_category)
        or account_ids.get(category)
        or default_category_account_id
    )
    resolved_description = str(description or extracted.get("description") or "Automated expense").strip()
    amount = _amount(extracted.get("total_amount"))
    transaction_date = _date(extracted.get("transaction_date"))
    missing = [
        name
        for name, value in (
            ("businessId", business_id),
            ("anchorAccountId", anchor_account_id),
            ("categoryAccountId", category_account_id),
            ("transactionDate", transaction_date),
            ("totalAmount", amount),
        )
        if value in (None, "")
    ]
    if missing:
        return {
            "success": False,
            "missingFields": missing,
            "mappedCategory": mapped_category or None,
            "message": "Wave transaction requires verified account mapping and financial fields: " + ", ".join(missing) + ".",
        }

    external_id = _external_id(data)
    return {
        "success": True,
        "mappedCategory": mapped_category,
        "input": {
            "businessId": str(business_id),
            "externalId": external_id,
            "date": transaction_date,
            "description": resolved_description,
            "anchor": {
                "accountId": str(anchor_account_id),
                "amount": amount,
                "direction": "WITHDRAWAL",
            },
            "lineItems": [{
                "accountId": str(category_account_id),
                "amount": amount,
                "balance": "INCREASE",
            }],
        },
    }


def wave_error_messages(payload: Any) -> str:
    if not isinstance(payload, dict):
        return "Wave returned an invalid response."
    operation = ((payload.get("data") or {}).get("moneyTransactionCreate") or {})
    errors = operation.get("inputErrors") or payload.get("errors") or []
    messages = []
    for error in errors:
        if isinstance(error, dict):
            message = error.get("message") or error.get("code")
        else:
            message = error
        if message:
            messages.append(str(message))
    return "; ".join(messages) or "Wave rejected the money transaction without a detailed error."


def _as_mapping(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _amount(value: Any) -> Optional[float]:
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return None
    return float(amount) if amount > 0 else None


def _date(value: Any) -> Optional[str]:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)).isoformat()
    except ValueError:
        return None


def _external_id(data: Dict[str, Any]) -> str:
    for key in ("idempotency_key", "posting_attempt_id", "document_id"):
        value = data.get(key)
        if value not in (None, ""):
            return f"fab:{value}"
    return "fab:unidentified"
