from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional


MIJNGELDZAKEN_IMPORT_COLUMNS = [
    "Datum",
    "Omschrijving",
    "Tegenpartij",
    "Bedrag",
    "Categorie",
    "Rekening",
    "Valuta",
    "FAB Document ID",
]


MIJNGELDZAKEN_SURFACE_CATALOG: Dict[str, Any] = {
    "modules": {
        "access": ["login", "profile_security"],
        "overview": ["dashboard", "current_month", "trends", "income", "expenses", "net_worth", "alerts"],
        "master_ledger": ["transactions", "accounts", "categories", "budgets"],
        "documents": ["document_vault", "receipts", "payslips", "contracts"],
        "planning": ["goals", "scenarios", "mortgage_planning", "pension_planning", "savings_planning"],
        "reports": ["reports", "exports"],
        "settings": ["settings", "imports", "security", "data_connections"],
    },
    "sync_contracts": {
        "fab_master_ledger_to_mijngeldzaken": {
            "domain": "Household and Category A personal ledger",
            "fab_owns": [
                "source document identity",
                "canonical transaction identity",
                "category decision",
                "duplicate and reconciliation evidence",
                "master-ledger export approval",
            ],
            "mijngeldzaken_owns": [
                "household account balances",
                "budget views",
                "planning calculations",
                "document vault records",
            ],
            "confirmation_required_for": [
                "submit import",
                "edit external transaction",
                "delete external transaction",
                "change account or security settings",
            ],
        },
        "mijngeldzaken_to_fab_learning": {
            "domain": "Learning from historical household bookkeeping",
            "fab_owns": ["learned vendor/category rules", "mapping history", "review queue"],
            "mijngeldzaken_owns": ["historical household categories", "budget reports"],
            "confirmation_required_for": ["use learned rule automatically", "overwrite existing rule"],
        },
    },
    "feature_inventory": {
        "login_page": {
            "surface": "login",
            "module": "access",
            "automation_mode": "requires_user_auth",
            "observed_from": "https://www.mijngeldzaken.nl/account/login",
            "controls": [
                {"label": "E-mailadres", "kind": "input", "safety": "requires_credentials", "action": "login_email_fill"},
                {"label": "Wachtwoord", "kind": "input", "safety": "requires_credentials", "action": "login_password_fill"},
                {"label": "Inloggen", "kind": "button", "safety": "requires_credentials", "action": "login_submit"},
                {"label": "Wachtwoord vergeten", "kind": "link", "safety": "read_only", "action": "password_reset_open"},
                {"label": "Start nu gratis", "kind": "link", "safety": "read_only", "action": "register_open"},
            ],
            "review_gate": "FAB never stores or types credentials from chat; user-owned sign-in is required.",
        },
        "household_bookkeeping": {
            "surface": "transactions",
            "module": "master_ledger",
            "automation_mode": "safe_draft",
            "controls": [
                {"label": "Transaction list", "kind": "table", "safety": "read_only", "action": "transaction_list_read"},
                {"label": "Transaction import preview", "kind": "import", "safety": "safe_draft", "action": "transaction_import_prepare"},
                {"label": "Submit transaction import", "kind": "button", "safety": "requires_confirmation", "action": "transaction_import_submit"},
                {"label": "Edit transaction", "kind": "form", "safety": "requires_confirmation", "action": "transaction_update"},
                {"label": "Delete transaction", "kind": "button", "safety": "requires_confirmation", "action": "transaction_delete"},
            ],
            "review_gate": "FAB can prepare import rows locally; external submission requires approval.",
        },
        "authenticated_sidebar_navigation": {
            "surface": "dashboard",
            "module": "overview",
            "automation_mode": "observe",
            "observed_from": "https://mijnhuishoudboekje.mijngeldzaken.nl/",
            "controls": [
                {"label": "Dashboard", "kind": "link", "safety": "read_only", "action": "dashboard_open"},
                {"label": "Deze maand", "kind": "page", "safety": "read_only", "action": "current_month_read"},
                {"label": "Trends", "kind": "page", "safety": "read_only", "action": "trend_report_read"},
                {"label": "Inkomsten", "kind": "page", "safety": "read_only", "action": "income_overview_read"},
                {"label": "Uitgaven", "kind": "page", "safety": "read_only", "action": "expense_overview_read"},
                {"label": "Transacties", "kind": "page", "safety": "read_only", "action": "transaction_list_read"},
                {"label": "Budgetten", "kind": "page", "safety": "read_only", "action": "budget_list_read"},
                {"label": "Contracten", "kind": "page", "safety": "read_only", "action": "contract_list_read"},
                {"label": "Bonnetjes", "kind": "page", "safety": "read_only", "action": "receipt_list_read"},
                {"label": "Loonstroken", "kind": "page", "safety": "read_only", "action": "payslip_list_read"},
                {"label": "Help", "kind": "button", "safety": "read_only", "action": "help_open"},
            ],
            "review_gate": "Navigation and help are read-only; FAB models page contracts before any external write.",
        },
        "current_month_dashboard": {
            "surface": "current_month",
            "module": "overview",
            "automation_mode": "observe",
            "observed_from": "https://mijnhuishoudboekje.mijngeldzaken.nl/",
            "controls": [
                {"label": "Financial month heading", "kind": "period", "safety": "read_only", "action": "current_month_read"},
                {"label": "Previous period", "kind": "button", "safety": "read_only", "action": "period_previous"},
                {"label": "Next period", "kind": "button", "safety": "read_only", "action": "period_next"},
                {"label": "Inkomsten panel", "kind": "summary", "safety": "read_only", "action": "income_overview_read"},
                {"label": "Uitgaven panel", "kind": "summary", "safety": "read_only", "action": "expense_overview_read"},
                {"label": "Rkeningen bijwerken prompt", "kind": "status", "safety": "read_only", "action": "account_update_prompt_read"},
            ],
            "review_gate": "FAB may read monthly status and account-update prompts; account refresh requires explicit user action.",
        },
        "import_center": {
            "surface": "imports",
            "module": "settings",
            "automation_mode": "safe_draft",
            "controls": [
                {"label": "Transaction import wizard", "kind": "import", "safety": "safe_draft", "action": "transaction_import_prepare"},
                {"label": "Upload transaction import", "kind": "upload", "safety": "requires_confirmation", "action": "transaction_import_submit"},
                {"label": "Import mapping preview", "kind": "mapping", "safety": "safe_draft", "action": "import_mapping_prepare"},
                {"label": "Apply import mapping", "kind": "button", "safety": "requires_confirmation", "action": "import_mapping_apply"},
                {"label": "Import history", "kind": "table", "safety": "read_only", "action": "import_history_read"},
            ],
            "review_gate": "FAB prepares deterministic import files and mappings; submitting them to MijnGeldzaken is approval-gated.",
        },
        "accounts_and_categories": {
            "surface": "accounts",
            "module": "master_ledger",
            "automation_mode": "observe",
            "controls": [
                {"label": "Account list", "kind": "table", "safety": "read_only", "action": "account_list_read"},
                {"label": "Account balances", "kind": "summary", "safety": "read_only", "action": "account_balance_read"},
                {"label": "Update accounts", "kind": "button", "safety": "requires_confirmation", "action": "account_update_start"},
                {"label": "Category list", "kind": "table", "safety": "read_only", "action": "category_list_read"},
                {"label": "Category mapping", "kind": "mapping", "safety": "safe_draft", "action": "category_mapping_prepare"},
                {"label": "Update category", "kind": "form", "safety": "requires_confirmation", "action": "category_update"},
            ],
            "review_gate": "Mapping suggestions are local; changes in MijnGeldzaken require confirmation.",
        },
        "budget_management": {
            "surface": "budgets",
            "module": "master_ledger",
            "automation_mode": "safe_draft",
            "controls": [
                {"label": "Budget list", "kind": "table", "safety": "read_only", "action": "budget_list_read"},
                {"label": "Budget detail", "kind": "detail", "safety": "read_only", "action": "budget_detail_read"},
                {"label": "Budget suggestion", "kind": "draft", "safety": "safe_draft", "action": "budget_suggestion_prepare"},
                {"label": "Create budget", "kind": "form", "safety": "requires_confirmation", "action": "budget_create"},
                {"label": "Update budget", "kind": "form", "safety": "requires_confirmation", "action": "budget_update"},
            ],
            "review_gate": "Budget recommendations are generated from FAB ledger trends; external budget changes require approval.",
        },
        "budgets_reports_and_exports": {
            "surface": "reports",
            "module": "reports",
            "automation_mode": "read_only",
            "controls": [
                {"label": "Budget report", "kind": "report", "safety": "read_only", "action": "budget_report_read"},
                {"label": "Budget list", "kind": "page", "safety": "read_only", "action": "budget_list_read"},
                {"label": "Cashflow report", "kind": "report", "safety": "read_only", "action": "cashflow_report_read"},
                {"label": "Trend report", "kind": "report", "safety": "read_only", "action": "trend_report_read"},
                {"label": "Income overview", "kind": "report", "safety": "read_only", "action": "income_overview_read"},
                {"label": "Expense overview", "kind": "report", "safety": "read_only", "action": "expense_overview_read"},
                {"label": "Export transactions", "kind": "download", "safety": "read_only", "action": "transaction_export_download"},
                {"label": "Export categories", "kind": "download", "safety": "read_only", "action": "category_export_download"},
            ],
            "review_gate": "Exports feed FAB learning and close controls without modifying MijnGeldzaken.",
        },
        "planning_and_advice": {
            "surface": "scenarios",
            "module": "planning",
            "automation_mode": "read_only",
            "controls": [
                {"label": "Goals", "kind": "page", "safety": "read_only", "action": "goal_list_read"},
                {"label": "Scenario list", "kind": "page", "safety": "read_only", "action": "scenario_list_read"},
                {"label": "Mortgage planning", "kind": "page", "safety": "read_only", "action": "mortgage_planning_read"},
                {"label": "Pension planning", "kind": "page", "safety": "read_only", "action": "pension_planning_read"},
                {"label": "Savings planning", "kind": "page", "safety": "read_only", "action": "savings_planning_read"},
                {"label": "Create scenario", "kind": "form", "safety": "requires_confirmation", "action": "scenario_create"},
            ],
            "review_gate": "Planning pages can inform FAB recommendations; creating or editing scenarios is never autonomous by default.",
        },
        "document_vault": {
            "surface": "document_vault",
            "module": "documents",
            "automation_mode": "safe_draft",
            "controls": [
                {"label": "Document list", "kind": "table", "safety": "read_only", "action": "document_list_read"},
                {"label": "Contract list", "kind": "table", "safety": "read_only", "action": "contract_list_read"},
                {"label": "Receipt list", "kind": "table", "safety": "read_only", "action": "receipt_list_read"},
                {"label": "Payslip list", "kind": "table", "safety": "read_only", "action": "payslip_list_read"},
                {"label": "Document upload draft", "kind": "upload", "safety": "safe_draft", "action": "document_upload_prepare"},
                {"label": "Receipt upload draft", "kind": "upload", "safety": "safe_draft", "action": "receipt_upload_prepare"},
                {"label": "Payslip upload draft", "kind": "upload", "safety": "safe_draft", "action": "payslip_upload_prepare"},
                {"label": "Submit document upload", "kind": "button", "safety": "requires_confirmation", "action": "document_upload_submit"},
                {"label": "Submit receipt upload", "kind": "button", "safety": "requires_confirmation", "action": "receipt_upload_submit"},
                {"label": "Submit payslip upload", "kind": "button", "safety": "requires_confirmation", "action": "payslip_upload_submit"},
            ],
            "review_gate": "Document uploads may transmit personal files and require explicit approval.",
        },
        "profile_security_and_connections": {
            "surface": "settings",
            "module": "settings",
            "automation_mode": "observe",
            "controls": [
                {"label": "Profile settings", "kind": "page", "safety": "read_only", "action": "profile_settings_read"},
                {"label": "Security settings", "kind": "page", "safety": "read_only", "action": "security_settings_read"},
                {"label": "Connected accounts", "kind": "page", "safety": "read_only", "action": "data_connections_read"},
                {"label": "Refresh connected account", "kind": "button", "safety": "requires_confirmation", "action": "connected_account_refresh"},
                {"label": "Change password", "kind": "form", "safety": "requires_credentials", "action": "password_change"},
            ],
            "review_gate": "FAB can report connection health; credential and security changes stay user-owned.",
        },
    },
    "actions": {
        "login_email_fill": {"surface": "login", "mode": "auth", "safety": "requires_credentials", "required": ["email"]},
        "login_password_fill": {"surface": "login", "mode": "auth", "safety": "requires_credentials", "required": ["password"]},
        "login_submit": {"surface": "login", "mode": "auth", "safety": "requires_credentials", "required": []},
        "password_reset_open": {"surface": "login", "mode": "read", "safety": "read_only", "required": []},
        "register_open": {"surface": "login", "mode": "read", "safety": "read_only", "required": []},
        "dashboard_open": {"surface": "dashboard", "mode": "read", "safety": "read_only", "required": []},
        "help_open": {"surface": "dashboard", "mode": "read", "safety": "read_only", "required": []},
        "current_month_read": {"surface": "current_month", "mode": "read", "safety": "read_only", "required": []},
        "period_previous": {"surface": "current_month", "mode": "read", "safety": "read_only", "required": []},
        "period_next": {"surface": "current_month", "mode": "read", "safety": "read_only", "required": []},
        "account_update_prompt_read": {"surface": "current_month", "mode": "read", "safety": "read_only", "required": []},
        "trend_report_read": {"surface": "trends", "mode": "read", "safety": "read_only", "required": []},
        "income_overview_read": {"surface": "income", "mode": "read", "safety": "read_only", "required": []},
        "expense_overview_read": {"surface": "expenses", "mode": "read", "safety": "read_only", "required": []},
        "transaction_list_read": {"surface": "transactions", "mode": "read", "safety": "read_only", "required": []},
        "transaction_import_prepare": {
            "surface": "transactions",
            "mode": "import",
            "safety": "safe_draft",
            "required": ["date", "amount", "description", "category"],
        },
        "transaction_import_submit": {
            "surface": "transactions",
            "mode": "import",
            "safety": "requires_confirmation",
            "required": ["importBatchId"],
        },
        "import_mapping_prepare": {
            "surface": "imports",
            "mode": "map",
            "safety": "safe_draft",
            "required": ["sourceColumns", "targetColumns"],
        },
        "import_mapping_apply": {
            "surface": "imports",
            "mode": "map",
            "safety": "requires_confirmation",
            "required": ["mappingId"],
        },
        "import_history_read": {"surface": "imports", "mode": "read", "safety": "read_only", "required": []},
        "transaction_update": {
            "surface": "transactions",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["transactionId", "changes"],
        },
        "transaction_delete": {
            "surface": "transactions",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["transactionId"],
        },
        "account_list_read": {"surface": "accounts", "mode": "read", "safety": "read_only", "required": []},
        "account_balance_read": {"surface": "accounts", "mode": "read", "safety": "read_only", "required": []},
        "account_update_start": {"surface": "accounts", "mode": "sync", "safety": "requires_confirmation", "required": ["accountId"]},
        "category_list_read": {"surface": "categories", "mode": "read", "safety": "read_only", "required": []},
        "category_mapping_prepare": {
            "surface": "categories",
            "mode": "map",
            "safety": "safe_draft",
            "required": ["sourceCategory", "targetCategory"],
        },
        "category_update": {
            "surface": "categories",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["categoryId", "changes"],
        },
        "budget_report_read": {"surface": "reports", "mode": "read", "safety": "read_only", "required": []},
        "budget_list_read": {"surface": "budgets", "mode": "read", "safety": "read_only", "required": []},
        "budget_detail_read": {"surface": "budgets", "mode": "read", "safety": "read_only", "required": ["budgetId"]},
        "budget_suggestion_prepare": {
            "surface": "budgets",
            "mode": "budget",
            "safety": "safe_draft",
            "required": ["category", "period", "suggestedAmount"],
        },
        "budget_create": {
            "surface": "budgets",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["category", "period", "amount"],
        },
        "budget_update": {
            "surface": "budgets",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["budgetId", "changes"],
        },
        "cashflow_report_read": {"surface": "reports", "mode": "read", "safety": "read_only", "required": []},
        "transaction_export_download": {"surface": "exports", "mode": "export", "safety": "read_only", "required": ["dateRange"]},
        "category_export_download": {"surface": "exports", "mode": "export", "safety": "read_only", "required": []},
        "goal_list_read": {"surface": "goals", "mode": "read", "safety": "read_only", "required": []},
        "scenario_list_read": {"surface": "scenarios", "mode": "read", "safety": "read_only", "required": []},
        "mortgage_planning_read": {"surface": "mortgage_planning", "mode": "read", "safety": "read_only", "required": []},
        "pension_planning_read": {"surface": "pension_planning", "mode": "read", "safety": "read_only", "required": []},
        "savings_planning_read": {"surface": "savings_planning", "mode": "read", "safety": "read_only", "required": []},
        "scenario_create": {
            "surface": "scenarios",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["name", "assumptions"],
        },
        "document_list_read": {"surface": "document_vault", "mode": "read", "safety": "read_only", "required": []},
        "contract_list_read": {"surface": "contracts", "mode": "read", "safety": "read_only", "required": []},
        "receipt_list_read": {"surface": "receipts", "mode": "read", "safety": "read_only", "required": []},
        "payslip_list_read": {"surface": "payslips", "mode": "read", "safety": "read_only", "required": []},
        "document_upload_prepare": {
            "surface": "document_vault",
            "mode": "upload",
            "safety": "safe_draft",
            "required": ["documentId", "filename"],
        },
        "receipt_upload_prepare": {
            "surface": "receipts",
            "mode": "upload",
            "safety": "safe_draft",
            "required": ["documentId", "filename"],
        },
        "payslip_upload_prepare": {
            "surface": "payslips",
            "mode": "upload",
            "safety": "safe_draft",
            "required": ["documentId", "filename"],
        },
        "document_upload_submit": {
            "surface": "document_vault",
            "mode": "upload",
            "safety": "requires_confirmation",
            "required": ["uploadDraftId"],
        },
        "receipt_upload_submit": {
            "surface": "receipts",
            "mode": "upload",
            "safety": "requires_confirmation",
            "required": ["uploadDraftId"],
        },
        "payslip_upload_submit": {
            "surface": "payslips",
            "mode": "upload",
            "safety": "requires_confirmation",
            "required": ["uploadDraftId"],
        },
        "profile_settings_read": {"surface": "settings", "mode": "read", "safety": "read_only", "required": []},
        "security_settings_read": {"surface": "security", "mode": "read", "safety": "read_only", "required": []},
        "data_connections_read": {"surface": "data_connections", "mode": "read", "safety": "read_only", "required": []},
        "connected_account_refresh": {
            "surface": "data_connections",
            "mode": "sync",
            "safety": "requires_confirmation",
            "required": ["connectionId"],
        },
        "password_change": {
            "surface": "security",
            "mode": "auth",
            "safety": "requires_credentials",
            "required": ["currentPassword", "newPassword"],
        },
    },
}


def normalize_mijngeldzaken_document_type(value: Any) -> str:
    if not value:
        return "receipt"
    return str(value).strip().lower().replace(" ", "_").replace("-", "_")


def classify_mijngeldzaken_destination(data: Dict[str, Any]) -> Dict[str, str]:
    document_type = normalize_mijngeldzaken_document_type(
        data.get("document_type")
        or data.get("type")
        or data.get("extracted_data", {}).get("document_type")
        or data.get("extracted_data", {}).get("type")
    )
    if document_type in {"document", "contract", "policy", "statement"}:
        return {"document_type": document_type, "target_surface": "document_vault", "fallback_surface": "transactions"}
    return {"document_type": document_type, "target_surface": "transactions", "fallback_surface": "document_vault"}


def resolve_mijngeldzaken_action_for_document(data: Dict[str, Any]) -> str:
    destination = classify_mijngeldzaken_destination(data)
    if destination["target_surface"] == "document_vault":
        return "document_upload_prepare"
    return "transaction_import_prepare"


def build_mijngeldzaken_action_payload(
    data: Dict[str, Any],
    mgz_category: str,
    default_account: str = "Huishouden",
) -> Dict[str, Any]:
    extracted = data.get("extracted_data", {})
    action_id = resolve_mijngeldzaken_action_for_document(data)
    if action_id == "document_upload_prepare":
        return {
            "documentId": data.get("id") or data.get("document_id"),
            "filename": data.get("original_filename") or data.get("filename") or data.get("description") or "document",
            "category": mgz_category,
            "description": extracted.get("description") or data.get("description") or "",
        }
    vendor = extracted.get("vendor_name") or data.get("vendor_name") or ""
    description = extracted.get("description") or data.get("description") or vendor or "FAB import"
    return {
        "date": extracted.get("transaction_date") or extracted.get("date") or data.get("transaction_date") or "",
        "amount": extracted.get("total_amount") or extracted.get("amount") or data.get("total_amount") or 0.0,
        "description": description,
        "counterparty": vendor,
        "category": mgz_category,
        "account": extracted.get("account") or data.get("target_account") or default_account,
        "currency": extracted.get("currency") or data.get("currency") or "EUR",
        "sourceDocumentId": data.get("id") or data.get("document_id"),
    }


def build_mijngeldzaken_import_row(data: Dict[str, Any], mgz_category: str, default_account: str = "Huishouden") -> Dict[str, Any]:
    payload = build_mijngeldzaken_action_payload(data, mgz_category, default_account=default_account)
    return build_mijngeldzaken_import_row_from_payload(payload)


def build_mijngeldzaken_import_row_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "Datum": payload.get("date", ""),
        "Omschrijving": payload.get("description", ""),
        "Tegenpartij": payload.get("counterparty", ""),
        "Bedrag": payload.get("amount", 0.0),
        "Categorie": payload.get("category", ""),
        "Rekening": payload.get("account", ""),
        "Valuta": payload.get("currency", "EUR"),
        "FAB Document ID": payload.get("sourceDocumentId"),
    }


def build_mijngeldzaken_master_ledger_draft(
    action_id: str,
    surface: str,
    payload: Dict[str, Any],
    source_proof: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    source_proof = source_proof or {}
    if action_id == "transaction_import_prepare":
        import_row = build_mijngeldzaken_import_row_from_payload(payload)
        checksum = _stable_checksum({
            "actionId": action_id,
            "surface": surface,
            "importRow": import_row,
            "sourceProof": source_proof,
        })
        return {
            "draftType": "transaction_import",
            "targetSystem": "mijngeldzaken",
            "surface": surface or "transactions",
            "actionId": action_id,
            "exportFormat": "csv",
            "columns": MIJNGELDZAKEN_IMPORT_COLUMNS,
            "importRow": import_row,
            "sourceProof": source_proof,
            "checksum": checksum,
            "externalSubmission": "not_executed",
        }
    if action_id in {"document_upload_prepare", "receipt_upload_prepare", "payslip_upload_prepare"}:
        upload_draft = {
            "documentId": payload.get("documentId"),
            "filename": payload.get("filename"),
            "category": payload.get("category"),
            "description": payload.get("description"),
        }
        checksum = _stable_checksum({
            "actionId": action_id,
            "surface": surface,
            "uploadDraft": upload_draft,
            "sourceProof": source_proof,
        })
        return {
            "draftType": "document_upload",
            "targetSystem": "mijngeldzaken",
            "surface": surface or "document_vault",
            "actionId": action_id,
            "uploadDraft": upload_draft,
            "sourceProof": source_proof,
            "checksum": checksum,
            "externalSubmission": "not_executed",
        }
    return {
        "draftType": "unsupported",
        "targetSystem": "mijngeldzaken",
        "surface": surface,
        "actionId": action_id,
        "payload": payload,
        "sourceProof": source_proof,
        "checksum": _stable_checksum({
            "actionId": action_id,
            "surface": surface,
            "payload": payload,
            "sourceProof": source_proof,
        }),
        "externalSubmission": "not_executed",
    }


def list_mijngeldzaken_surfaces() -> List[str]:
    surfaces: List[str] = []
    for module_surfaces in MIJNGELDZAKEN_SURFACE_CATALOG["modules"].values():
        surfaces.extend(module_surfaces)
    return surfaces


def list_mijngeldzaken_actions(surface: Optional[str] = None) -> List[Dict[str, Any]]:
    actions: List[Dict[str, Any]] = []
    for action_id, action in MIJNGELDZAKEN_SURFACE_CATALOG["actions"].items():
        if surface and action["surface"] != surface:
            continue
        actions.append({"id": action_id, **action})
    return actions


def plan_mijngeldzaken_action(
    surface: str,
    action_id: str,
    payload: Optional[Dict[str, Any]] = None,
    allow_write: bool = False,
) -> Dict[str, Any]:
    payload = payload or {}
    action = MIJNGELDZAKEN_SURFACE_CATALOG["actions"].get(action_id)
    if not action or action.get("surface") != surface:
        return {
            "status": "unsupported",
            "surface": surface,
            "action_id": action_id,
            "missing_fields": [],
            "can_run_autonomously": False,
            "requires_confirmation": True,
            "message": "MijnGeldzaken action is not in the FAB action catalog.",
        }
    missing_fields = [field for field in action["required"] if payload.get(field) in (None, "")]
    requires_confirmation = action["safety"] in {"requires_confirmation", "requires_credentials"}
    can_run_autonomously = (
        not missing_fields
        and action["safety"] in {"read_only", "safe_draft"}
    ) or (allow_write and not missing_fields and not requires_confirmation)
    return {
        "status": "needs_fields" if missing_fields else "planned",
        "surface": surface,
        "action_id": action_id,
        "mode": action["mode"],
        "safety": action["safety"],
        "missing_fields": missing_fields,
        "can_run_autonomously": can_run_autonomously,
        "requires_confirmation": requires_confirmation,
        "message": (
            f"FAB can plan {action_id} against MijnGeldzaken {surface}."
            if can_run_autonomously
            else f"FAB can prepare {action_id}, but execution requires review or confirmation."
        ),
    }


def summarize_mijngeldzaken_parity() -> Dict[str, Any]:
    surfaces = list_mijngeldzaken_surfaces()
    actions = list_mijngeldzaken_actions()
    controls = [
        control
        for feature in MIJNGELDZAKEN_SURFACE_CATALOG["feature_inventory"].values()
        for control in feature.get("controls", [])
    ]
    safety_counts: Dict[str, int] = {}
    for action in actions:
        safety = action["safety"]
        safety_counts[safety] = safety_counts.get(safety, 0) + 1
    return {
        "modules": len(MIJNGELDZAKEN_SURFACE_CATALOG["modules"]),
        "surfaces": len(surfaces),
        "sync_contracts": len(MIJNGELDZAKEN_SURFACE_CATALOG["sync_contracts"]),
        "feature_pages": len(MIJNGELDZAKEN_SURFACE_CATALOG["feature_inventory"]),
        "observed_controls": len(controls),
        "actions": len(actions),
        "actions_by_safety": safety_counts,
    }


def _stable_checksum(value: Dict[str, Any]) -> str:
    body = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()
