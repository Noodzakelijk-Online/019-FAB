"""Read-only Wave account discovery and FAB mapping verification."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

import requests

from src.data_entry.waveapps_transaction import WAVE_GRAPHQL_URL
from src.utils.rate_limiter import get_rate_limiter


WAVE_ACCOUNTS_QUERY = """
query ($businessId: ID!) {
  business(id: $businessId) {
    id
    name
    accounts {
      edges {
        node {
          id
          name
          subtype {
            name
            value
          }
        }
      }
    }
  }
}
"""


class WaveappsAccountDiscoveryService:
    """Reads Wave chart-of-accounts state needed by FAB's export adapter."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.api_url = str(self.config.get("waveapps_api_url") or WAVE_GRAPHQL_URL)
        self.timeout_seconds = _timeout_seconds(self.config.get("waveapps_request_timeout_seconds"))

    def mapping_status(
        self,
        target_system: Optional[str] = None,
        accounts: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        targets = _targets(self.config, target_system)
        return {
            "externalSubmission": "not_executed",
            "targets": [
                self._mapping_status_for_target(
                    target,
                    accounts if target_system and target["id"] == target_system else None,
                )
                for target in targets
            ],
        }

    def discover(self, target_system: str) -> Dict[str, Any]:
        target = _target_config(self.config, target_system)
        if not target:
            return {"success": False, "status": "unsupported_target", "externalSubmission": "not_executed"}
        missing = [
            label
            for label, value in (("accessToken", target["access_token"]), ("businessId", target["business_id"]))
            if value in (None, "")
        ]
        if missing:
            result = _discovery_failure(
                "not_configured",
                "Wave account validation requires a stored access token and business ID.",
            )
            result["missingFields"] = missing
            result["mapping"] = self._mapping_status_for_target(target)
            return result

        limiter = get_rate_limiter("waveapps")
        if not limiter.acquire(block=False):
            rate = limiter.get_current_rate()
            status = "quota_exhausted" if rate.get("quotaExhausted") else "rate_limited"
            result = _discovery_failure(
                status,
                "FAB deferred Wave account validation because the configured provider quota is unavailable.",
            )
            result["rateLimit"] = rate
            return result

        try:
            response = requests.post(
                self.api_url,
                headers={"Authorization": f"Bearer {target['access_token']}", "Content-Type": "application/json"},
                json={"query": WAVE_ACCOUNTS_QUERY, "variables": {"businessId": target["business_id"]}},
                timeout=self.timeout_seconds,
            )
            response_status = getattr(response, "status_code", None)
            if response_status == 401:
                return _discovery_failure(
                    "authentication_failed",
                    "Wave rejected the access token. Replace it with a current user-owned token and validate again.",
                )
            if response_status == 403:
                return _discovery_failure(
                    "authorization_failed",
                    "Wave accepted the token but denied access to this business or the required account data. Confirm the business, subscription, and token permissions.",
                )
            if response_status == 429:
                return _discovery_failure(
                    "rate_limited",
                    "Wave rate-limited account validation. Wait briefly and validate again.",
                )
            response.raise_for_status()
            payload = response.json()
        except requests.exceptions.RequestException as exc:
            return _discovery_failure(
                "provider_error",
                f"Wave account validation could not reach a healthy API response ({type(exc).__name__}).",
            )
        except ValueError:
            return _discovery_failure(
                "provider_error",
                "Wave account validation returned an invalid response.",
            )

        business = ((payload.get("data") or {}).get("business") or {}) if isinstance(payload, dict) else {}
        if not business:
            provider_message = _graph_errors(payload) or "Wave returned no business account data."
            status = _graph_error_status(provider_message)
            return _discovery_failure(status, _graph_failure_message(status))
        accounts = _accounts(business)
        mapping = self._mapping_status_for_target(target, accounts)
        operation_id = _operation_id(target["id"], business.get("id") or target["business_id"], accounts)
        return {
            "success": True,
            "status": "read_result_captured",
            "targetSystem": target["id"],
            "business": {"id": business.get("id"), "name": business.get("name")},
            "accounts": accounts,
            "mapping": mapping,
            "operation": {
                "operation_id": operation_id,
                "action_id": "chart_account_list_read",
                "surface": "chart_of_accounts",
                "mode": "read_only",
                "safety": "read_only",
                "payload": {"targetSystem": target["id"], "businessId": business.get("id"), "accountCount": len(accounts)},
                "plan": {"status": "planned", "requires_confirmation": False, "requires_credentials": True},
            },
            "externalSubmission": "not_executed",
        }

    def _mapping_status_for_target(self, target: Dict[str, Any], accounts: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        account_ids = {account["id"] for account in accounts or [] if account.get("id")}
        configured_anchor = target.get("anchor_account_id")
        category_accounts = _mapping(target.get("category_account_ids"))
        default_category_account_id = target.get("default_category_account_id")
        mapping_rows = []
        for category, account_id in sorted(category_accounts.items()):
            mapping_rows.append({
                "category": str(category),
                "accountId": str(account_id),
                "verified": None if accounts is None else str(account_id) in account_ids,
            })
        required_missing = []
        if not target.get("access_token"):
            required_missing.append("accessToken")
        if not target.get("business_id"):
            required_missing.append("businessId")
        if not configured_anchor:
            required_missing.append("anchorAccountId")
        # A catch-all account is not a substitute for an explicit category map.
        # Treating it as complete can silently collapse unrelated expenses into
        # one ledger account.
        if not category_accounts:
            required_missing.append("categoryAccountIds")
        default_verified = None if accounts is None else (
            default_category_account_id in account_ids if default_category_account_id else True
        )
        verified = (
            accounts is not None
            and not required_missing
            and configured_anchor in account_ids
            and all(row["verified"] for row in mapping_rows)
            and bool(default_verified)
        )
        return {
            "targetSystem": target["id"],
            "configured": not required_missing,
            "requiredMissing": required_missing,
            "anchorAccount": {
                "accountId": configured_anchor,
                "verified": None if accounts is None else configured_anchor in account_ids,
            },
            "categoryAccounts": mapping_rows,
            "defaultCategoryAccount": {
                "accountId": default_category_account_id,
                "verified": default_verified,
            },
            "verified": verified,
            "accountsDiscovered": len(accounts) if accounts is not None else None,
        }


def _targets(config: Dict[str, Any], target_system: Optional[str] = None) -> List[Dict[str, Any]]:
    targets = [_target_config(config, "waveapps_business"), _target_config(config, "waveapps_personal")]
    targets = [target for target in targets if target]
    if target_system:
        return [target for target in targets if target["id"] == target_system]
    return targets


def _target_config(config: Dict[str, Any], target_system: str) -> Optional[Dict[str, Any]]:
    if target_system not in {"waveapps_business", "waveapps_personal"}:
        return None
    prefix = target_system
    flat_id_key = "waveapps_business_id" if target_system == "waveapps_business" else "waveapps_personal_id"
    nested_id_key = "business_id" if target_system == "waveapps_business" else "personal_id"
    return {
        "id": target_system,
        "access_token": _config_value(config, f"{prefix}_access_token", f"{prefix}.access_token"),
        "business_id": _config_value(config, flat_id_key, f"{prefix}.{nested_id_key}", f"{prefix}.id"),
        "anchor_account_id": _config_value(config, f"{prefix}_anchor_account_id", f"{prefix}.anchor_account_id"),
        "category_account_ids": _config_value(config, f"{prefix}_category_account_ids", f"{prefix}.category_account_ids"),
        "default_category_account_id": _config_value(config, f"{prefix}_default_category_account_id", f"{prefix}.default_category_account_id"),
    }


def resolve_wave_target_config(config: Dict[str, Any], target_system: str) -> Optional[Dict[str, Any]]:
    """Return the private target descriptor used by Wave API services."""
    return _target_config(config, target_system)


def wave_graph_errors(payload: Any) -> str:
    return _graph_errors(payload)


def wave_timeout_seconds(value: Any) -> float:
    return _timeout_seconds(value)


def _config_value(config: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = config.get(key)
        if value not in (None, ""):
            return value
        if "." in key:
            section, option = key.split(".", 1)
            nested = config.get(section)
            if isinstance(nested, dict) and nested.get(option) not in (None, ""):
                return nested[option]
    return None


def _accounts(business: Dict[str, Any]) -> List[Dict[str, Any]]:
    edges = ((business.get("accounts") or {}).get("edges") or [])
    accounts = []
    for edge in edges:
        node = edge.get("node") if isinstance(edge, dict) else None
        if not isinstance(node, dict) or not node.get("id"):
            continue
        subtype = node.get("subtype") if isinstance(node.get("subtype"), dict) else {}
        accounts.append({
            "id": str(node["id"]),
            "name": str(node.get("name") or ""),
            "subtype": {"name": subtype.get("name"), "value": subtype.get("value")},
        })
    return sorted(accounts, key=lambda account: (account["name"].lower(), account["id"]))


def _mapping(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _operation_id(target_system: str, business_id: Any, accounts: List[Dict[str, Any]]) -> str:
    body = json.dumps({"target": target_system, "businessId": business_id, "accounts": accounts}, sort_keys=True)
    return "wave-account-discovery:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


def _graph_errors(payload: Any) -> str:
    errors = payload.get("errors") if isinstance(payload, dict) else None
    if not isinstance(errors, list):
        return ""
    return "; ".join(str(error.get("message") or error) for error in errors if error)


def _timeout_seconds(value: Any) -> float:
    try:
        return max(float(value), 1.0)
    except (TypeError, ValueError):
        return 30.0


def _discovery_failure(status: str, message: str) -> Dict[str, Any]:
    return {
        "success": False,
        "status": status,
        "message": str(message or "Wave account validation failed.")[:1000],
        "nextAction": _next_action(status),
        "externalSubmission": "not_executed",
    }


def _graph_error_status(message: str) -> str:
    normalized = str(message or "").casefold()
    if any(token in normalized for token in ("unauthenticated", "invalid token", "access token")):
        return "authentication_failed"
    if any(token in normalized for token in ("unauthorized", "not authorized", "forbidden", "permission", "scope", "access denied")):
        return "authorization_failed"
    if "not found" in normalized:
        return "business_not_found"
    return "provider_error"


def _next_action(status: str) -> str:
    return {
        "not_configured": "Store the user-owned Wave access token and confirm the Wave business ID before validating.",
        "authentication_failed": "Replace the locally stored Wave token with a current token from the official Wave Developer Portal.",
        "authorization_failed": "Confirm the token can access this Wave business and, for OAuth tokens, includes business:read and account:read.",
        "business_not_found": "Confirm the Wave business ID belongs to the account authorized by this token.",
        "rate_limited": "Wait for the provider limit to reset, then validate again.",
        "quota_exhausted": "Wait for the configured daily quota to reset, then validate again.",
        "provider_error": "Check Wave service availability and validate again without changing any bookkeeping records.",
    }.get(status, "Review the Wave connection and validate again.")


def _graph_failure_message(status: str) -> str:
    return {
        "authentication_failed": "Wave did not authenticate the stored access token.",
        "authorization_failed": "Wave denied access to the selected business or its account data.",
        "business_not_found": "Wave could not find the selected business for this authorized user.",
        "provider_error": "Wave rejected account validation without returning usable business data.",
    }.get(status, "Wave account validation failed.")
