from __future__ import annotations

import os
from typing import Any, Dict, Optional

from src.data_entry.waveapps_account_discovery import (
    WaveappsAccountDiscoveryService,
    resolve_wave_target_config,
)
from src.operations.local_ledger import LocalOperationsLedger
from src.operations.local_categories import fab_category_intents
from src.security.local_secret_store import (
    LocalSecretStore,
    LocalSecretStoreError,
    apply_local_wave_settings,
)

WAVE_DEVELOPER_TOKEN_GUIDE_URL = (
    "https://developer.waveapps.com/hc/en-us/articles/"
    "360020596571-Permitted-Use-Wave-Business-Owners"
)
WAVE_GRAPHQL_CLIENT_GUIDE_URL = (
    "https://developer.waveapps.com/hc/en-us/articles/360018856171-Clients"
)
WAVE_OAUTH_SCOPE_GUIDE_URL = (
    "https://developer.waveapps.com/hc/en-us/articles/360032818132-OAuth-Scopes"
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
        category_intents = fab_category_intents(
            ledger,
            effective,
            target_system=target_system,
        )
        configured_category_accounts = {
            str(row.get("category") or ""): str(row.get("accountId") or "")
            for row in mapping.get("categoryAccounts") or []
        }
        verified_category_accounts = {
            str(row.get("category") or ""): row.get("verified") is True
            for row in mapping.get("categoryAccounts") or []
        }
        for intent in category_intents:
            category = str(intent["category"])
            intent["accountId"] = configured_category_accounts.get(category) or None
            intent["mapped"] = verified_category_accounts.get(category, False)
        in_use_intents = [intent for intent in category_intents if intent["inUse"]]
        mapped_in_use_intents = [intent for intent in in_use_intents if intent["mapped"]]
        category_coverage_complete = (
            len(mapped_in_use_intents) == len(in_use_intents)
            and bool(mapping.get("categoryAccounts"))
        )
        token_configured = bool(target.get("access_token"))
        business_id = str(target.get("business_id") or "")
        ready = (
            token_configured
            and bool(business_id)
            and bool(mapping.get("verified"))
            and category_coverage_complete
        )
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
        activation = _activation_status(
            status=status,
            token_configured=token_configured,
            business_id=business_id,
            accounts=accounts,
            mapping=mapping,
            category_coverage_complete=category_coverage_complete,
            unmapped_categories=[
                intent["category"] for intent in in_use_intents if not intent["mapped"]
            ],
        )
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
                "requiredCategoryIntents": len(in_use_intents),
                "mappedCategoryIntents": len(mapped_in_use_intents),
                "unmappedInUseCategories": [
                    intent["category"] for intent in in_use_intents if not intent["mapped"]
                ],
                "percentage": round((len(mapped_in_use_intents) / len(in_use_intents)) * 100, 1)
                if in_use_intents else (100.0 if mapping.get("categoryAccounts") else 0.0),
                "complete": category_coverage_complete,
            },
            "categoryIntents": category_intents,
            "accounts": accounts,
            "accountOptions": {
                "anchor": anchor_accounts,
                "expense": expense_accounts,
            },
            "lastValidatedAt": discovery.get("validatedAt"),
            "validatedBusiness": discovery.get("business"),
            "activation": activation,
            "documentation": {
                "ownBusinessAccessToken": WAVE_DEVELOPER_TOKEN_GUIDE_URL,
                "graphqlClient": WAVE_GRAPHQL_CLIENT_GUIDE_URL,
                "oauthScopes": WAVE_OAUTH_SCOPE_GUIDE_URL,
            },
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


def _activation_status(
    *,
    status: str,
    token_configured: bool,
    business_id: str,
    accounts: list[Dict[str, Any]],
    mapping: Dict[str, Any],
    category_coverage_complete: bool,
    unmapped_categories: list[str],
) -> Dict[str, Any]:
    connection_complete = token_configured and bool(business_id)
    validation_complete = connection_complete and bool(accounts)
    anchor_complete = validation_complete and mapping.get("anchorAccount", {}).get("verified") is True
    mapping_complete = (
        anchor_complete
        and mapping.get("verified") is True
        and category_coverage_complete
    )
    step_specs = [
        {
            "id": "connection",
            "label": "Store Wave token and business ID",
            "complete": connection_complete,
        },
        {
            "id": "validation",
            "label": "Validate business and chart of accounts",
            "complete": validation_complete,
        },
        {
            "id": "anchor_mapping",
            "label": "Select the verified funding account",
            "complete": anchor_complete,
        },
        {
            "id": "category_mapping",
            "label": "Map every FAB category currently in use",
            "complete": mapping_complete,
        },
    ]
    current_index = next(
        (index for index, step in enumerate(step_specs) if not step["complete"]),
        len(step_specs),
    )
    steps = [
        {
            **step,
            "status": (
                "complete"
                if step["complete"]
                else "current"
                if index == current_index
                else "pending"
            ),
        }
        for index, step in enumerate(step_specs)
    ]
    next_action = _activation_next_action(
        status,
        business_id=business_id,
        anchor_complete=anchor_complete,
        unmapped_categories=unmapped_categories,
    )
    return {
        "currentStep": steps[current_index]["id"] if current_index < len(steps) else "complete",
        "nextAction": next_action,
        "steps": steps,
        "canValidate": connection_complete,
        "canSaveMapping": validation_complete,
        "canPrepareWaveDrafts": mapping_complete,
        "canSubmitExternally": False,
        "externalSubmission": "approval_gated",
    }


def _activation_next_action(
    status: str,
    *,
    business_id: str,
    anchor_complete: bool,
    unmapped_categories: list[str],
) -> str:
    if status == "needs_token":
        return "Create a user-owned Wave access token and store it in FAB."
    if status == "needs_business_id":
        return "Enter the Wave business ID that FAB is allowed to operate."
    if status == "needs_validation":
        return "Run read-only Wave validation to load the live chart of accounts."
    if status == "needs_mapping":
        if not anchor_complete:
            return "Select a verified Wave funding account."
        if unmapped_categories:
            preview = ", ".join(unmapped_categories[:3])
            suffix = "" if len(unmapped_categories) <= 3 else f" and {len(unmapped_categories) - 3} more"
            return f"Map the Wave expense account for: {preview}{suffix}."
        return "Repair the invalid Wave posting-account mapping and validate it again."
    if status == "ready":
        return "Review and approve one prepared Wave draft before enabling routine delivery."
    if business_id:
        return "Inspect the Wave setup status before continuing."
    return "Configure the Wave downstream target."
