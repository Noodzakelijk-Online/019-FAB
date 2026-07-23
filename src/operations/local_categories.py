"""Canonical FAB bookkeeping categories and their local usage."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional

from src.document_processors.document_type_classifier import is_non_posting_document_type
from src.operations.local_targets import resolve_document_target_system


DEFAULT_FAB_CATEGORIES = (
    "Advertising & Marketing",
    "Bank Fees",
    "Business Insurance",
    "Cleaning Supplies",
    "Computer Equipment",
    "Construction Materials & Tools",
    "Contractors & Freelancers",
    "Cost of Goods Sold",
    "Education & Training",
    "Fuel",
    "Government Fees & Permits",
    "Hosting & Cloud Services",
    "Legal & Professional Fees",
    "Meals & Entertainment",
    "Office Supplies",
    "Postage & Delivery",
    "Rent & Workspace",
    "Repairs & Maintenance",
    "Software & Subscriptions",
    "Telecommunications",
    "Travel & Transport",
    "Utilities",
    "Vehicle Expenses",
    "Other Business Expense",
)

NON_POSTING_CATEGORIES = {
    "",
    "manual review",
    "uncategorized",
    "supporting evidence",
}


def fab_category_options(
    ledger: Any,
    config: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """Return stable FAB category intents plus categories already present locally."""
    categories = set(DEFAULT_FAB_CATEGORIES)
    categories.update(_configured_catalog(config or {}))
    categories.update(_configured_mapping_categories(config or {}))
    for rule in ledger.list_vendor_category_rules(limit=5000):
        _add_category(categories, rule.get("category"))
    for document in ledger.list_documents(limit=5000):
        if is_non_posting_document_type(document.get("document_type")):
            continue
        _add_category(categories, document.get("category"))
    return sorted(categories, key=str.casefold)


def fab_category_intents(
    ledger: Any,
    config: Optional[Dict[str, Any]] = None,
    *,
    target_system: str,
) -> List[Dict[str, Any]]:
    """Describe category options and the posting evidence that currently uses them."""
    document_counts: Counter[str] = Counter()
    approved_rule_counts: Counter[str] = Counter()
    suggested_rule_counts: Counter[str] = Counter()

    for document in ledger.list_documents(limit=5000):
        if is_non_posting_document_type(document.get("document_type")):
            continue
        category = _category(document.get("category"))
        if not category:
            continue
        target = resolve_document_target_system(
            document,
            default="waveapps_business",
        )
        if target == target_system:
            document_counts[category] += 1

    for rule in ledger.list_vendor_category_rules(limit=5000):
        category = _category(rule.get("category"))
        if not category:
            continue
        rule_target = str(rule.get("target_system") or "none").strip()
        if rule_target not in {"", "none", target_system}:
            continue
        if str(rule.get("status") or "") == "approved":
            approved_rule_counts[category] += 1
        elif str(rule.get("status") or "") == "suggested":
            suggested_rule_counts[category] += 1

    return [
        {
            "category": category,
            "inUse": bool(document_counts[category] or approved_rule_counts[category]),
            "documentCount": document_counts[category],
            "approvedRuleCount": approved_rule_counts[category],
            "suggestedRuleCount": suggested_rule_counts[category],
        }
        for category in fab_category_options(ledger, config)
    ]


def _configured_catalog(config: Dict[str, Any]) -> Iterable[str]:
    value = (
        config.get("fab_category_catalog")
        or config.get("operations_fab_category_catalog")
        or config.get("category_catalog")
    )
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("["):
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError:
                value = stripped.split(",")
        else:
            value = stripped.split(",")
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if _category(item)]
    return []


def _configured_mapping_categories(config: Dict[str, Any]) -> Iterable[str]:
    categories = []
    for key in (
        "waveapps_business_category_mapping",
        "waveapps_business_category_account_ids",
        "waveapps_personal_category_mapping",
        "waveapps_personal_category_account_ids",
    ):
        value = config.get(key)
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                value = {}
        if isinstance(value, dict):
            categories.extend(str(category).strip() for category in value if _category(category))
    return categories


def _add_category(categories: set[str], value: Any) -> None:
    category = _category(value)
    if category:
        categories.add(category)


def _category(value: Any) -> str:
    category = str(value or "").strip()
    return "" if category.casefold() in NON_POSTING_CATEGORIES else category
