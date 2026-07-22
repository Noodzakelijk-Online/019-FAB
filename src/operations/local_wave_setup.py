from __future__ import annotations

import os
from typing import Any, Dict, Optional

from src.data_entry.waveapps_account_discovery import (
    WaveappsAccountDiscoveryService,
    resolve_wave_target_config,
)
from src.operations.local_ledger import LocalOperationsLedger
from src.security.local_secret_store import (
    LocalSecretStore,
    LocalSecretStoreError,
    apply_local_wave_settings,
)


class LocalWaveSetupService:
    """Manage local Wave credentials and verified account mappings without exposing tokens."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def status(
        self,
        ledger: LocalOperationsLedger,
        target_system: str = "waveapps_business",
    ) -> Dict[str, Any]:
        effective = apply_local_wave_settings(self.config)
        target = resolve_wave_target_config(effective, target_system)
        if not target:
            return {
                "success": False,
                "status": "unsupported_target",
                "targetSystem": target_system,
            }
        storage = self._storage_status(target_system)
        discovery = _latest_discovery(ledger, target_system, str(target.get("business_id") or ""))
        accounts = discovery.get("accounts") or []
        mapping = WaveappsAccountDiscoveryService(effective).mapping_status(
            target_system,
            accounts=accounts or None,
        )["targets"][0]
        anchor_accounts = [account for account in accounts if _is_anchor_account(account)]
        expense_accounts = [account for account in accounts if _is_expense_account(account)]
        mapped_expense_ids = {
            str(row.get("accountId") or "")
            for row in mapping.get("categoryAccounts") or []
            if row.get("verified") is True
        }
        available_expense_ids = {
            str(account.get("id") or "")
            for account in expense_accounts
            if account.get("id")
        }
        mapped_expense_count = len(mapped_expense_ids & available_expense_ids)
        available_expense_count = len(available_expense_ids)
        token_configured = bool(target.get("access_token"))
        business_id = str(target.get("business_id") or "")
        ready = token_configured and bool(business_id) and bool(mapping.get("verified"))
        if ready:
            status = "ready"
        elif not token_configured:
            status = "needs_token"
        elif not business_id:
            status = "needs_business_id"
        elif not accounts:
            status = "needs_validation"
        else:
            status = "needs_mapping"
        return {
            "success": True,
            "status": status,
            "ready": ready,
            "targetSystem": target_system,
            "businessId": business_id or None,
            "accessTokenConfigured": token_configured,
            "environmentOverrides": _environment_overrides(target_system),
            "storage": storage,
            "mapping": mapping,
            "mappingCoverage": {
                "mappedExpenseAccounts": mapped_expense_count,
                "availableExpenseAccounts": available_expense_count,
                "percentage": round((mapped_expense_count / available_expense_count) * 100, 1)
                if available_expense_count else 0.0,
                "complete": bool(available_expense_count)
                and mapped_expense_count == available_expense_count,
            },
            "accounts": accounts,
            "accountOptions": {
                "anchor": anchor_accounts,
                "expense": expense_accounts,
            },
            "lastValidatedAt": discovery.get("validatedAt"),
            "validatedBusiness": discovery.get("business"),
            "externalSubmission": "not_executed",
        }

    def save(
        self,
        ledger: LocalOperationsLedger,
        payload: Dict[str, Any],
        *,
        actor: str,
    ) -> Dict[str, Any]:
        target_system = str(payload.get("targetSystem") or "waveapps_business")
        updates: Dict[str, Any] = {}
        aliases = {
            "accessToken": "access_token",
            "businessId": "business_id",
            "anchorAccountId": "anchor_account_id",
            "defaultCategoryAccountId": "default_category_account_id",
            "categoryAccountIds": "category_account_ids",
        }
        for public_key, store_key in aliases.items():
            if public_key in payload:
                updates[store_key] = payload[public_key]
        clear_token = payload.get("clearAccessToken") is True
        if "accessToken" in payload and not str(payload.get("accessToken") or "").strip():
            raise ValueError("accessToken must not be empty; use clearAccessToken to disconnect.")
        if not updates and not clear_token:
            raise ValueError("At least one Wave setup field is required.")
        self._validate_mapping_selection(ledger, target_system, updates)
        store = LocalSecretStore(self.config)
        store.update_wave_target(
            target_system,
            updates,
            clear_access_token=clear_token,
        )
        if clear_token and not _environment_overrides(target_system)["accessToken"]:
            self.config.pop(f"{target_system}_access_token", None)
            nested = self.config.get(target_system)
            if isinstance(nested, dict):
                nested.pop("access_token", None)
        apply_local_wave_settings(self.config, mutate=True)
        ledger.record_audit_event({
            "action": "local_wave.settings_updated",
            "entityType": "wave_connection",
            "entityId": target_system,
            "details": {
                "actor": str(actor or "local_operator")[:200],
                "updatedFields": sorted(key for key in updates if key != "access_token"),
                "accessTokenUpdated": "access_token" in updates,
                "accessTokenCleared": clear_token,
                "externalSubmission": "not_executed",
            },
        })
        return self.status(ledger, target_system)

    def _storage_status(self, target_system: str) -> Dict[str, Any]:
        try:
            return LocalSecretStore(self.config).public_wave_status(target_system)
        except LocalSecretStoreError as exc:
            return {
                "storePresent": False,
                "keyPresent": False,
                "encryptedAtRest": True,
                "keyProtector": "unavailable",
                "accessTokenStored": False,
                "storedFields": [],
                "error": str(exc),
            }

    def _validate_mapping_selection(
        self,
        ledger: LocalOperationsLedger,
        target_system: str,
        updates: Dict[str, Any],
    ) -> None:
        requested_ids = {
            str(updates.get("anchor_account_id") or "").strip(),
            str(updates.get("default_category_account_id") or "").strip(),
        }
        category_accounts = updates.get("category_account_ids") or {}
        if not isinstance(category_accounts, dict):
            raise ValueError("categoryAccountIds must be an object.")
        requested_ids.update(str(value or "").strip() for value in category_accounts.values())
        requested_ids.discard("")
        if not requested_ids:
            return
        effective = apply_local_wave_settings(self.config)
        target = resolve_wave_target_config(effective, target_system) or {}
        business_id = str(updates.get("business_id") or target.get("business_id") or "")
        discovery = _latest_discovery(ledger, target_system, business_id)
        known_ids = {str(account.get("id") or "") for account in discovery.get("accounts") or []}
        if not known_ids:
            raise ValueError("Validate the Wave business and load its accounts before saving account mappings.")
        unknown = sorted(requested_ids - known_ids)
        if unknown:
            raise ValueError("One or more selected Wave accounts are not present in the latest validated account list.")


def _latest_discovery(
    ledger: LocalOperationsLedger,
    target_system: str,
    business_id: str,
) -> Dict[str, Any]:
    snapshots = ledger.list_wave_operation_snapshots(
        action_id="chart_account_list_read",
        status="read_result_captured",
        limit=25,
    )
    for snapshot in snapshots:
        metadata = snapshot.get("metadata") if isinstance(snapshot.get("metadata"), dict) else {}
        discovery = metadata.get("accountDiscovery") if isinstance(metadata.get("accountDiscovery"), dict) else {}
        business = discovery.get("business") if isinstance(discovery.get("business"), dict) else {}
        if str(discovery.get("targetSystem") or "") != target_system:
            continue
        if business_id and str(business.get("id") or "") != business_id:
            continue
        accounts = discovery.get("accounts") if isinstance(discovery.get("accounts"), list) else []
        return {
            "accounts": [account for account in accounts if isinstance(account, dict)],
            "business": business,
            "validatedAt": snapshot.get("updated_at"),
        }
    return {"accounts": [], "business": None, "validatedAt": None}


def _environment_overrides(target_system: str) -> Dict[str, bool]:
    prefix = "FAB_WAVEAPPS_BUSINESS_" if target_system == "waveapps_business" else "FAB_WAVEAPPS_PERSONAL_"
    return {
        "accessToken": bool(os.environ.get(f"{prefix}ACCESS_TOKEN")),
        "businessId": bool(os.environ.get(f"{prefix}ID")),
        "anchorAccountId": bool(os.environ.get(f"{prefix}ANCHOR_ACCOUNT_ID")),
        "defaultCategoryAccountId": bool(os.environ.get(f"{prefix}DEFAULT_CATEGORY_ACCOUNT_ID")),
        "categoryAccountIds": bool(os.environ.get(f"{prefix}CATEGORY_ACCOUNT_IDS")),
    }


def _is_anchor_account(account: Dict[str, Any]) -> bool:
    subtype = account.get("subtype") if isinstance(account.get("subtype"), dict) else {}
    value = str(subtype.get("value") or "").upper()
    name = str(subtype.get("name") or "").casefold()
    return any(token in value for token in ("BANK", "CASH", "CREDIT_CARD", "LOAN")) or any(
        token in name for token in ("bank", "cash", "credit card", "loan")
    )


def _is_expense_account(account: Dict[str, Any]) -> bool:
    subtype = account.get("subtype") if isinstance(account.get("subtype"), dict) else {}
    value = str(subtype.get("value") or "").upper()
    name = str(subtype.get("name") or "").casefold()
    return "EXPENSE" in value or "expense" in name or "kosten" in name
