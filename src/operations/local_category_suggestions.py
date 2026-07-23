"""Explainable FAB category suggestions for exact, well-known vendors."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Optional


_VENDOR_RULES = (
    {
        "category": "Telecommunications",
        "rationale": "Exact vendor match to a telecommunications provider.",
        "aliases": ("T-Mobile", "Odido", "KPN", "Vodafone", "Ziggo"),
    },
    {
        "category": "Construction Materials & Tools",
        "rationale": "Exact vendor match to a building materials and tools retailer.",
        "aliases": (
            "Praxis",
            "Hornbach",
            "Hornbach Bouwmarkt",
            "Hornbach Bouwmarkt B.V.",
            "Gamma",
            "Karwei",
        ),
    },
    {
        "category": "Software & Subscriptions",
        "rationale": "Exact vendor match to a software subscription provider.",
        "aliases": (
            "Slack",
            "getimg.ai",
            "BrainForce Co.",
            "Microsoft 365",
            "Adobe",
            "Dropbox",
            "GitHub",
            "OpenAI",
        ),
    },
    {
        "category": "Hosting & Cloud Services",
        "rationale": "Exact vendor match to a cloud hosting provider.",
        "aliases": (
            "Amazon Web Services",
            "AWS",
            "Google Cloud",
            "DigitalOcean",
            "Vercel",
            "Heroku",
        ),
    },
    {
        "category": "Postage & Delivery",
        "rationale": "Exact vendor match to a parcel or postal carrier.",
        "aliases": ("PostNL", "DHL", "UPS", "FedEx"),
    },
    {
        "category": "Utilities",
        "rationale": "Exact vendor match to an energy utility.",
        "aliases": ("Vattenfall", "Eneco", "Essent"),
    },
)


def suggest_category_intent(document: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Suggest an intent without applying it or bypassing review."""
    current = str(document.get("category") or "").strip().casefold()
    if current not in {"", "manual review", "uncategorized"}:
        return None

    extracted = document.get("extracted_data")
    if not isinstance(extracted, dict):
        extracted = {}
    vendor_name = str(
        document.get("vendor_name")
        or document.get("vendorName")
        or extracted.get("vendor_name")
        or ""
    ).strip()
    vendor_key = normalize_vendor_name(vendor_name)
    if not vendor_key:
        return None

    matched = _VENDOR_INDEX.get(vendor_key)
    if not matched:
        return None
    return {
        "category": matched["category"],
        "confidenceScore": 0.97,
        "source": "fab_builtin_vendor_taxonomy_v1",
        "rationale": matched["rationale"],
        "matchPolicy": "exact_normalized_vendor",
        "matchedVendor": vendor_name,
        "requiresApproval": True,
    }


def normalize_vendor_name(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_value = "".join(character for character in normalized if not unicodedata.combining(character))
    vendor_key = re.sub(r"[^a-z0-9]+", " ", ascii_value.casefold()).strip()
    vendor_key = re.sub(r"\bb\s+v\b", "bv", vendor_key)
    vendor_key = re.sub(r"\bn\s+v\b", "nv", vendor_key)
    return re.sub(r"\s+", " ", vendor_key).strip()


_VENDOR_INDEX = {
    normalize_vendor_name(alias): rule
    for rule in _VENDOR_RULES
    for alias in rule["aliases"]
}
