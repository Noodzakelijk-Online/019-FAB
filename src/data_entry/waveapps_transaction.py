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
    resolved_description = str(description or extracted.get("description") or "Automated expense").strip()
    amount = _amount(extracted.get("total_amount"))
    transaction_date = _date(extracted.get("transaction_date"))
    raw_line_items = extracted.get("line_items") if isinstance(extracted.get("line_items"), list) else []
    line_items, line_item_missing = _expense_line_items(
        raw_line_items,
        fallback_category=category,
        fallback_mapped_category=mapped_category,
        category_mapping=category_mapping,
        category_account_ids=account_ids,
        default_category_account_id=default_category_account_id,
        total_amount=amount,
    )
    missing = list(line_item_missing) + [
        name
        for name, value in (
            ("businessId", business_id),
            ("anchorAccountId", anchor_account_id),
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
            "lineItems": line_items,
        },
    }


def _expense_line_items(
    raw_items: list,
    *,
    fallback_category: str,
    fallback_mapped_category: str,
    category_mapping: Any,
    category_account_ids: Dict[str, Any],
    default_category_account_id: Any,
    total_amount: Optional[float],
) -> tuple[list[Dict[str, Any]], list[str]]:
    mappings = _as_mapping(category_mapping)
    if not raw_items:
        account_id = (
            category_account_ids.get(fallback_mapped_category)
            or category_account_ids.get(fallback_category)
        )
        if not account_id:
            return [], ["categoryAccountId"]
        return [{
            "accountId": str(account_id),
            "amount": total_amount,
            "balance": "INCREASE",
        }], []

    line_items = []
    missing = []
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            missing.append(f"lineItems[{index}]")
            continue
        line_category = str(item.get("category") or fallback_category).strip()
        mapped_category = str(mappings.get(line_category) or line_category or fallback_mapped_category).strip()
        account_label = str(item.get("account") or item.get("account_name") or "").strip()
        account_id = (
            category_account_ids.get(mapped_category)
            or category_account_ids.get(line_category)
            or category_account_ids.get(account_label)
        )
        line_amount = _amount(item.get("amount"))
        if not account_id:
            missing.append(f"lineItems[{index}].accountId")
        if line_amount is None:
            missing.append(f"lineItems[{index}].amount")
        if account_id and line_amount is not None:
            line_items.append({
                "accountId": str(account_id),
                "amount": line_amount,
                "balance": "INCREASE",
            })

    if not missing and total_amount is not None:
        item_total = sum((Decimal(str(item["amount"])) for item in line_items), Decimal("0"))
        expected_total = Decimal(str(total_amount))
        if item_total.quantize(Decimal("0.01")) != expected_total.quantize(Decimal("0.01")):
            missing.append("lineItemTotal")
    return line_items, missing


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
