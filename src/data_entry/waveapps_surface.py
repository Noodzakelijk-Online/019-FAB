from typing import Any, Dict, List, Optional


WAVE_SURFACE_CATALOG: Dict[str, Any] = {
    "modules": {
        "dashboard": ["dashboard"],
        "sales_payments": [
            "estimates",
            "invoices",
            "recurring_invoices",
            "customer_statements",
            "customers",
            "selling_products_services",
        ],
        "purchases": ["bills", "vendors", "buying_products_services"],
        "accounting": ["transactions", "chart_of_accounts"],
        "banking": ["connected_accounts"],
        "reports": ["reports"],
        "settings": [
            "business_settings",
            "invoice_estimate_settings",
            "financial_settings",
            "sales_tax_settings",
            "subscription_management",
            "data_export",
        ],
        "integrations": ["integrations", "wave_payments", "business_checking", "zoho_migration_offer"],
    },
    "menu_inventory": {
        "quick_create": {
            "label": "Create new",
            "items": [
                {"label": "Transaction", "surface": "transactions", "safety": "safe_draft", "action": "transaction_add"},
                {"label": "Estimate", "surface": "estimates", "safety": "safe_draft", "action": "estimate_create"},
                {"label": "Invoice", "surface": "invoices", "safety": "safe_draft", "action": "invoice_create"},
                {"label": "Recurring Invoice", "surface": "recurring_invoices", "safety": "requires_confirmation", "action": "recurring_invoice_create"},
                {"label": "Bill", "surface": "bills", "safety": "safe_draft", "action": "bill_create"},
                {"label": "Customer", "surface": "customers", "safety": "safe_draft", "action": "customer_create"},
                {"label": "Vendor", "surface": "vendors", "safety": "safe_draft", "action": "vendor_create"},
                {"label": "Product or Service", "surface": "selling_products_services", "safety": "safe_draft", "action": "selling_product_service_upsert"},
            ],
        },
        "sales_payments_menu": {
            "label": "Sales & Payments",
            "items": [
                {"label": "Estimates", "surface": "estimates", "safety": "read_only", "action": "estimate_filter"},
                {"label": "Invoices", "surface": "invoices", "safety": "read_only", "action": "invoice_filter"},
                {"label": "Recurring Invoices", "surface": "recurring_invoices", "safety": "requires_confirmation", "action": "recurring_invoice_create"},
                {"label": "Customer Statements", "surface": "customer_statements", "safety": "read_only", "action": "customer_statement_create"},
                {"label": "Customers", "surface": "customers", "safety": "safe_draft", "action": "customer_create"},
                {"label": "Products & Services", "surface": "selling_products_services", "safety": "safe_draft", "action": "selling_product_service_upsert"},
            ],
        },
        "purchases_menu": {
            "label": "Purchases",
            "items": [
                {"label": "Bills", "surface": "bills", "safety": "safe_draft", "action": "bill_create"},
                {"label": "Vendors", "surface": "vendors", "safety": "safe_draft", "action": "vendor_create"},
                {"label": "Products & Services", "surface": "buying_products_services", "safety": "safe_draft", "action": "buying_product_service_upsert"},
            ],
        },
        "accounting_menu": {
            "label": "Accounting",
            "items": [
                {"label": "Transactions", "surface": "transactions", "safety": "safe_draft", "action": "transaction_add"},
                {"label": "Chart of Accounts", "surface": "chart_of_accounts", "safety": "requires_confirmation", "action": "chart_account_create"},
            ],
        },
        "banking_menu": {
            "label": "Banking",
            "items": [
                {"label": "Connected Accounts", "surface": "connected_accounts", "safety": "requires_credentials", "action": "connected_account_connect"},
            ],
        },
        "standalone_menu": {
            "label": "Standalone",
            "items": [
                {"label": "Dashboard", "surface": "dashboard", "safety": "read_only"},
                {"label": "Payroll", "surface": "payroll", "safety": "unsupported", "action": "payroll_open"},
                {"label": "Reports", "surface": "reports", "safety": "read_only", "action": "report_open"},
                {"label": "Perks", "surface": "perks", "safety": "read_only", "action": "perks_open"},
            ],
        },
    },
    "sync_contracts": {
        "documents_to_wave_ledger": {
            "domain": "Document intake and ledger posting",
            "fab_owns": ["source document identity", "OCR/extraction result", "duplicate decision", "review state"],
            "wave_owns": ["posted transaction", "bill", "invoice", "estimate", "Wave attachment id"],
            "confirmation_required_for": ["delete", "merge", "mark paid", "send invoice", "record payment"],
        },
        "master_data": {
            "domain": "Customers, vendors, products, services, and accounts",
            "fab_owns": ["canonical identity", "fuzzy match history", "category-to-account rules"],
            "wave_owns": ["Wave customer id", "Wave vendor id", "Wave product/service id", "Chart of Accounts id"],
            "confirmation_required_for": ["bulk import", "edit existing record", "delete/archive", "create chart account"],
        },
        "banking_reconciliation": {
            "domain": "Banking and reconciliation",
            "fab_owns": ["matching decisions", "receipt-to-bank evidence", "exception queue"],
            "wave_owns": ["connected account status", "bank feed credentials", "account balances"],
            "confirmation_required_for": ["connect account", "upload statement", "merge transactions", "delete transaction"],
        },
        "reporting_close": {
            "domain": "Reporting, VAT, and close pack",
            "fab_owns": ["scheduled report requests", "variance diagnostics", "close checklist"],
            "wave_owns": ["official report calculations", "general ledger export", "tax report balances"],
            "confirmation_required_for": ["send reports externally", "change report-affecting account mappings"],
        },
        "settings_access_integrations": {
            "domain": "Settings, access, integrations, and external offers",
            "fab_owns": ["desired integration plan", "role/access request", "business-context guardrail"],
            "wave_owns": ["user permissions", "profile/security state", "subscription state", "OAuth tokens"],
            "confirmation_required_for": ["invite/remove user", "switch business", "profile/security change", "connect integration"],
        },
    },
    "report_catalog": {
        "financial_statements": {
            "label": "Financial statements",
            "description": "Profit, balance, and cash movement reports used for close review.",
            "reports": [
                {
                    "type": "profit-and-loss",
                    "label": "Profit & Loss (Income Statement)",
                    "date_mode": "date_range",
                    "default_export": "pdf",
                    "close_pack": True,
                    "reconciliation_pack": False,
                },
                {
                    "type": "balance-sheet",
                    "label": "Balance Sheet",
                    "date_mode": "as_of",
                    "default_export": "pdf",
                    "close_pack": True,
                    "reconciliation_pack": False,
                },
                {
                    "type": "cash-flow",
                    "label": "Cash Flow",
                    "date_mode": "date_range",
                    "default_export": "pdf",
                    "close_pack": True,
                    "reconciliation_pack": False,
                },
            ],
        },
        "taxes": {
            "label": "Taxes",
            "description": "Sales tax collected and paid; used as VAT/BTW control evidence in FAB.",
            "reports": [
                {
                    "type": "sales-tax",
                    "label": "Sales Tax Report",
                    "date_mode": "date_range",
                    "default_export": "pdf",
                    "close_pack": True,
                    "reconciliation_pack": False,
                },
            ],
        },
        "customers": {
            "label": "Customers",
            "description": "Customer income, receivables aging, and customer credit balances.",
            "reports": [
                {
                    "type": "income-by-customer",
                    "label": "Income by Customer",
                    "date_mode": "date_range",
                    "default_export": "csv",
                    "close_pack": False,
                    "reconciliation_pack": False,
                },
                {
                    "type": "aged-receivables",
                    "label": "Aged Receivables",
                    "date_mode": "as_of",
                    "default_export": "pdf",
                    "close_pack": True,
                    "reconciliation_pack": False,
                },
                {
                    "type": "customer-credits",
                    "label": "Customer Credits",
                    "date_mode": "as_of",
                    "default_export": "csv",
                    "close_pack": False,
                    "reconciliation_pack": False,
                },
            ],
        },
        "vendors": {
            "label": "Vendors",
            "description": "Vendor spending, payable aging, and supplier evidence for exception review.",
            "reports": [
                {
                    "type": "purchases-by-vendor",
                    "label": "Purchases by Vendor",
                    "date_mode": "date_range",
                    "default_export": "csv",
                    "close_pack": False,
                    "reconciliation_pack": True,
                },
                {
                    "type": "aged-payables",
                    "label": "Aged Payables",
                    "date_mode": "as_of",
                    "default_export": "pdf",
                    "close_pack": True,
                    "reconciliation_pack": False,
                },
            ],
        },
        "detailed_reporting": {
            "label": "Detailed reporting",
            "description": "Account balances, trial balance, and general-ledger rows for reconciliation.",
            "reports": [
                {
                    "type": "account-balances",
                    "label": "Account Balances",
                    "date_mode": "as_of",
                    "default_export": "csv",
                    "close_pack": True,
                    "reconciliation_pack": True,
                },
                {
                    "type": "trial-balance",
                    "label": "Trial Balance",
                    "date_mode": "as_of",
                    "default_export": "pdf",
                    "close_pack": True,
                    "reconciliation_pack": True,
                },
                {
                    "type": "account-transactions",
                    "label": "Account Transactions (General Ledger)",
                    "date_mode": "date_range",
                    "default_export": "csv",
                    "close_pack": True,
                    "reconciliation_pack": True,
                },
            ],
        },
    },
    "feature_inventory": {
        "dashboard_live_overview": {
            "surface": "dashboard",
            "module": "dashboard",
            "automation_mode": "observe",
            "controls": [
                {"label": "Create estimate", "kind": "link", "safety": "safe_draft", "action": "estimate_create"},
                {"label": "Create invoice", "kind": "link", "safety": "safe_draft", "action": "invoice_create"},
                {"label": "Add transaction", "kind": "link", "safety": "safe_draft", "action": "transaction_add"},
                {"label": "Add bill", "kind": "link", "safety": "safe_draft", "action": "bill_create"},
                {"label": "Customize", "kind": "button", "safety": "safe_draft", "action": "dashboard_customize"},
            ],
            "review_gate": "FAB may observe dashboard state and prepare drafts; account prompts remain user-owned.",
        },
        "wave_drawer_navigation": {
            "surface": "dashboard",
            "module": "dashboard",
            "automation_mode": "observe",
            "controls": [
                {"label": "Sales & Payments", "kind": "menu", "safety": "read_only"},
                {"label": "Purchases", "kind": "menu", "safety": "read_only"},
                {"label": "Accounting", "kind": "menu", "safety": "read_only"},
                {"label": "Banking", "kind": "menu", "safety": "read_only"},
                {"label": "Reports", "kind": "link", "safety": "read_only", "action": "report_open"},
                {"label": "Payroll", "kind": "external", "safety": "unsupported", "action": "payroll_open"},
                {"label": "Perks", "kind": "link", "safety": "read_only", "action": "perks_open"},
            ],
            "review_gate": "Navigation is read-only; execution follows the target action safety.",
        },
        "dashboard_widgets_and_offers": {
            "surface": "dashboard",
            "module": "dashboard",
            "automation_mode": "observe",
            "controls": [
                {"label": "Explore Zoho Books and unlock your offer", "kind": "external", "safety": "requires_confirmation", "action": "zoho_offer_open"},
                {"label": "Profile settings", "kind": "external", "safety": "requires_confirmation", "action": "profile_settings_update"},
                {"label": "Make changes", "kind": "button", "safety": "requires_confirmation", "action": "profile_settings_update"},
                {"label": "Everything looks good", "kind": "button", "safety": "safe_draft", "action": "dashboard_account_prompt_acknowledge"},
                {"label": "View all invoices", "kind": "link", "safety": "read_only", "action": "invoice_filter"},
                {"label": "View report", "kind": "link", "safety": "read_only", "action": "dashboard_widget_report_open"},
                {"label": "Last 12 months", "kind": "filter", "safety": "read_only", "action": "dashboard_widget_filter"},
                {"label": "Current fiscal year", "kind": "filter", "safety": "read_only", "action": "dashboard_widget_filter"},
                {"label": "Set up Payments now", "kind": "link", "safety": "requires_confirmation", "action": "wave_payments_get_started"},
                {"label": "Learn more", "kind": "external", "safety": "read_only", "action": "business_checking_open"},
            ],
            "review_gate": "Report and filter controls are read-only; profile, payment, banking, and external-offer actions require approval.",
        },
        "sales_payments_pages": {
            "surface": "invoices",
            "module": "sales_payments",
            "automation_mode": "safe_draft",
            "controls": [
                {"label": "Estimates", "kind": "page", "safety": "read_only", "action": "estimate_filter"},
                {"label": "Invoices", "kind": "page", "safety": "read_only", "action": "invoice_filter"},
                {"label": "Recurring Invoices", "kind": "page", "safety": "requires_confirmation", "action": "recurring_invoice_create"},
                {"label": "Customer Statements", "kind": "page", "safety": "read_only", "action": "customer_statement_create"},
                {"label": "Customers", "kind": "page", "safety": "safe_draft", "action": "customer_create"},
                {"label": "Products & Services", "kind": "page", "safety": "safe_draft", "action": "selling_product_service_upsert"},
            ],
            "review_gate": "Sending, payment recording, recurring billing, and overwrites require confirmation.",
        },
        "estimates_workspace": {
            "surface": "estimates",
            "module": "sales_payments",
            "automation_mode": "safe_draft",
            "controls": [
                {"label": "Create estimate", "kind": "button", "safety": "safe_draft", "action": "estimate_create"},
                {"label": "Active filters count", "kind": "page", "safety": "read_only", "action": "estimate_filter"},
                {"label": "All customers", "kind": "filter", "safety": "read_only", "action": "estimate_customer_filter"},
                {"label": "All statuses", "kind": "filter", "safety": "read_only", "action": "estimate_status_filter"},
                {"label": "From date filter", "kind": "input", "safety": "read_only", "action": "estimate_date_filter"},
                {"label": "To date filter", "kind": "input", "safety": "read_only", "action": "estimate_date_filter"},
                {"label": "Open date picker", "kind": "button", "safety": "read_only", "action": "estimate_date_picker_open"},
                {"label": "Close date picker", "kind": "button", "safety": "read_only", "action": "estimate_date_picker_close"},
                {"label": "Estimate number filter", "kind": "input", "safety": "read_only", "action": "estimate_number_search"},
                {"label": "Clear", "kind": "button", "safety": "read_only", "action": "estimate_clear_filters"},
                {"label": "Search", "kind": "button", "safety": "read_only", "action": "estimate_number_search"},
                {"label": "Active tab", "kind": "tab", "safety": "read_only", "action": "estimate_tab_view"},
                {"label": "Draft tab", "kind": "tab", "safety": "read_only", "action": "estimate_tab_view"},
                {"label": "All tab", "kind": "tab", "safety": "read_only", "action": "estimate_tab_view"},
                {"label": "Empty-state Create estimate", "kind": "button", "safety": "safe_draft", "action": "estimate_create"},
                {"label": "Export to PDF dialog", "kind": "dialog", "safety": "read_only", "action": "estimate_download_pdf"},
                {"label": "Close dialog", "kind": "button", "safety": "read_only", "action": "estimate_pdf_dialog_close"},
                {"label": "Download PDF", "kind": "button", "safety": "read_only", "action": "estimate_download_pdf"},
                {"label": "Convert", "kind": "button", "safety": "requires_confirmation", "action": "estimate_convert_to_invoice"},
            ],
            "review_gate": "List filters, tabs, date pickers, and PDF download are read-only; drafts are allowed; conversion requires confirmation.",
        },
        "estimate_editor_lifecycle": {
            "surface": "estimates",
            "module": "sales_payments",
            "automation_mode": "confirmed_execute",
            "controls": [
                {"label": "Save estimate", "kind": "button", "safety": "safe_draft", "action": "estimate_update"},
                {"label": "Send estimate", "kind": "button", "safety": "requires_confirmation", "action": "estimate_send"},
                {"label": "Download PDF", "kind": "button", "safety": "read_only", "action": "estimate_download_pdf"},
                {"label": "Duplicate", "kind": "button", "safety": "safe_draft", "action": "estimate_duplicate"},
                {"label": "Convert to invoice", "kind": "button", "safety": "requires_confirmation", "action": "estimate_convert_to_invoice"},
                {"label": "Delete estimate", "kind": "button", "safety": "requires_confirmation", "action": "estimate_delete"},
            ],
            "review_gate": "FAB may save its own draft; send, convert, and delete require confirmation.",
        },
        "invoices_workspace": {
            "surface": "invoices",
            "module": "sales_payments",
            "automation_mode": "safe_draft",
            "controls": [
                {"label": "Create an invoice", "kind": "button", "safety": "safe_draft", "action": "invoice_create"},
                {"label": "Overdue", "kind": "report", "safety": "read_only", "action": "invoice_summary_metrics_read"},
                {"label": "Due within next 30 days", "kind": "report", "safety": "read_only", "action": "invoice_summary_metrics_read"},
                {"label": "Average time to get paid", "kind": "report", "safety": "read_only", "action": "invoice_summary_metrics_read"},
                {"label": "Refresh", "kind": "button", "safety": "read_only", "action": "invoice_summary_refresh"},
                {"label": "Active filters count", "kind": "page", "safety": "read_only", "action": "invoice_filter"},
                {"label": "All customers", "kind": "filter", "safety": "read_only", "action": "invoice_customer_filter"},
                {"label": "Create a new invoice", "kind": "button", "safety": "safe_draft", "action": "invoice_create"},
                {"label": "All statuses", "kind": "filter", "safety": "read_only", "action": "invoice_status_filter"},
                {"label": "From date filter", "kind": "input", "safety": "read_only", "action": "invoice_date_filter"},
                {"label": "To date filter", "kind": "input", "safety": "read_only", "action": "invoice_date_filter"},
                {"label": "Open date picker", "kind": "button", "safety": "read_only", "action": "invoice_date_picker_open"},
                {"label": "Close date picker", "kind": "button", "safety": "read_only", "action": "invoice_date_picker_close"},
                {"label": "Invoice number filter", "kind": "input", "safety": "read_only", "action": "invoice_number_search"},
                {"label": "Clear", "kind": "button", "safety": "read_only", "action": "invoice_clear_filters"},
                {"label": "Search", "kind": "button", "safety": "read_only", "action": "invoice_number_search"},
                {"label": "Unpaid tab", "kind": "tab", "safety": "read_only", "action": "invoice_tab_view"},
                {"label": "Draft tab", "kind": "tab", "safety": "read_only", "action": "invoice_tab_view"},
                {"label": "All invoices tab", "kind": "tab", "safety": "read_only", "action": "invoice_tab_view"},
                {"label": "View all invoices", "kind": "button", "safety": "read_only", "action": "invoice_view_all"},
            ],
            "review_gate": "List filters, tabs, summary refresh, and metrics are read-only; sending, payment recording, and reminders require confirmation.",
        },
        "invoice_editor_lifecycle": {
            "surface": "invoices",
            "module": "sales_payments",
            "automation_mode": "confirmed_execute",
            "controls": [
                {"label": "Save invoice", "kind": "button", "safety": "safe_draft", "action": "invoice_update"},
                {"label": "Approve invoice", "kind": "button", "safety": "requires_confirmation", "action": "invoice_approve"},
                {"label": "Send invoice", "kind": "button", "safety": "requires_confirmation", "action": "invoice_send"},
                {"label": "Record payment", "kind": "button", "safety": "requires_confirmation", "action": "invoice_record_payment"},
                {"label": "Send reminder", "kind": "button", "safety": "requires_confirmation", "action": "invoice_send_reminder"},
                {"label": "Download PDF", "kind": "button", "safety": "read_only", "action": "invoice_download_pdf"},
                {"label": "Duplicate", "kind": "button", "safety": "safe_draft", "action": "invoice_duplicate"},
                {"label": "Delete invoice", "kind": "button", "safety": "requires_confirmation", "action": "invoice_delete"},
            ],
            "review_gate": "FAB may draft/save invoices; approval, send, reminders, payment, and delete require confirmation.",
        },
        "recurring_invoices_workspace": {
            "surface": "recurring_invoices",
            "module": "sales_payments",
            "automation_mode": "confirmed_execute",
            "controls": [
                {"label": "Create a recurring invoice", "kind": "button", "safety": "requires_confirmation", "action": "recurring_invoice_create"},
                {"label": "All customers", "kind": "filter", "safety": "read_only", "action": "recurring_invoice_customer_filter"},
                {"label": "Active tab", "kind": "tab", "safety": "read_only", "action": "recurring_invoice_tab_view"},
                {"label": "Draft tab", "kind": "tab", "safety": "read_only", "action": "recurring_invoice_tab_view"},
                {"label": "All recurring invoices tab", "kind": "tab", "safety": "read_only", "action": "recurring_invoice_tab_view"},
                {"label": "Status column", "kind": "report", "safety": "read_only", "action": "recurring_invoice_table_read"},
                {"label": "Customer column", "kind": "report", "safety": "read_only", "action": "recurring_invoice_table_read"},
                {"label": "Schedule column", "kind": "report", "safety": "read_only", "action": "recurring_invoice_table_read"},
                {"label": "Previous invoice column", "kind": "report", "safety": "read_only", "action": "recurring_invoice_table_read"},
                {"label": "Next invoice column", "kind": "report", "safety": "read_only", "action": "recurring_invoice_table_read"},
                {"label": "Invoice amount column", "kind": "report", "safety": "read_only", "action": "recurring_invoice_table_read"},
                {"label": "View drafts", "kind": "button", "safety": "read_only", "action": "recurring_invoice_view_drafts"},
                {"label": "Create new recurring invoice", "kind": "button", "safety": "requires_confirmation", "action": "recurring_invoice_create"},
            ],
            "review_gate": "List filters, tabs, and schedule table reads are read-only; creating or changing recurring schedules requires confirmation.",
        },
        "recurring_invoice_lifecycle": {
            "surface": "recurring_invoices",
            "module": "sales_payments",
            "automation_mode": "confirmed_execute",
            "controls": [
                {"label": "Save recurring invoice", "kind": "button", "safety": "requires_confirmation", "action": "recurring_invoice_update"},
                {"label": "Activate schedule", "kind": "button", "safety": "requires_confirmation", "action": "recurring_invoice_activate"},
                {"label": "Pause schedule", "kind": "button", "safety": "requires_confirmation", "action": "recurring_invoice_pause"},
                {"label": "Delete schedule", "kind": "button", "safety": "requires_confirmation", "action": "recurring_invoice_delete"},
            ],
            "review_gate": "All recurring schedule mutations require explicit approval.",
        },
        "customer_statement_generator": {
            "surface": "customer_statements",
            "module": "sales_payments",
            "automation_mode": "observe",
            "controls": [
                {"label": "How does this work?", "kind": "external", "safety": "read_only", "action": "customer_statement_help_open"},
                {"label": "Customer selector", "kind": "filter", "safety": "read_only", "action": "customer_statement_customer_select"},
                {"label": "Select report type", "kind": "filter", "safety": "read_only", "action": "customer_statement_type_select"},
                {"label": "Outstanding invoices", "kind": "filter", "safety": "read_only", "action": "customer_statement_type_select"},
                {"label": "Account activity", "kind": "filter", "safety": "read_only", "action": "customer_statement_type_select"},
                {"label": "Create statement", "kind": "button", "safety": "read_only", "action": "customer_statement_create"},
                {"label": "Export statement", "kind": "button", "safety": "read_only", "action": "customer_statement_export"},
                {"label": "Send statement", "kind": "button", "safety": "requires_confirmation", "action": "customer_statement_send"},
            ],
            "review_gate": "Statement creation/export is read-only; sending externally requires confirmation.",
        },
        "customers_list_and_form": {
            "surface": "customers",
            "module": "sales_payments",
            "automation_mode": "safe_draft",
            "controls": [
                {"label": "Import from CSV", "kind": "button", "safety": "requires_confirmation", "action": "customer_import_csv"},
                {"label": "Add a customer", "kind": "button", "safety": "safe_draft", "action": "customer_create"},
                {"label": "Search by name", "kind": "input", "safety": "read_only", "action": "customer_search"},
                {"label": "Customer count", "kind": "report", "safety": "read_only", "action": "customer_list_read"},
                {"label": "Name column", "kind": "report", "safety": "read_only", "action": "customer_list_read"},
                {"label": "Contact column", "kind": "report", "safety": "read_only", "action": "customer_list_read"},
                {"label": "Saved cards column", "kind": "report", "safety": "read_only", "action": "customer_list_read"},
                {"label": "Balance | Overdue column", "kind": "report", "safety": "read_only", "action": "customer_list_read"},
                {"label": "More actions", "kind": "button", "safety": "read_only", "action": "customer_row_actions_open"},
                {"label": "View", "kind": "menu", "safety": "read_only", "action": "customer_view"},
                {"label": "Edit", "kind": "menu", "safety": "requires_confirmation", "action": "customer_update"},
                {"label": "Create invoice", "kind": "menu", "safety": "safe_draft", "action": "customer_create_invoice"},
                {"label": "Send statement", "kind": "menu", "safety": "requires_confirmation", "action": "customer_statement_send"},
                {"label": "Delete", "kind": "menu", "safety": "requires_confirmation", "action": "customer_delete"},
            ],
            "review_gate": "Bulk import and existing customer edits need confirmation.",
        },
        "customer_form_fields": {
            "surface": "customers",
            "module": "sales_payments",
            "automation_mode": "safe_draft",
            "controls": [
                {"label": "Customer *", "kind": "input", "safety": "safe_draft", "action": "customer_form_fill"},
                {"label": "Primary contact First name", "kind": "input", "safety": "safe_draft", "action": "customer_form_fill"},
                {"label": "Last name", "kind": "input", "safety": "safe_draft", "action": "customer_form_fill"},
                {"label": "Email", "kind": "input", "safety": "safe_draft", "action": "customer_form_fill"},
                {"label": "Phone", "kind": "input", "safety": "safe_draft", "action": "customer_form_fill"},
                {"label": "Add phone", "kind": "button", "safety": "safe_draft", "action": "customer_add_phone"},
                {"label": "Add contact", "kind": "button", "safety": "safe_draft", "action": "customer_add_contact"},
                {"label": "Account number", "kind": "input", "safety": "safe_draft", "action": "customer_form_fill"},
                {"label": "Website", "kind": "input", "safety": "safe_draft", "action": "customer_form_fill"},
                {"label": "Notes", "kind": "input", "safety": "safe_draft", "action": "customer_form_fill"},
                {"label": "Currency", "kind": "filter", "safety": "safe_draft", "action": "customer_form_fill"},
                {"label": "Billing address", "kind": "input", "safety": "safe_draft", "action": "customer_form_fill"},
                {"label": "Billing country", "kind": "filter", "safety": "safe_draft", "action": "customer_form_fill"},
                {"label": "Billing province, state, or region", "kind": "filter", "safety": "safe_draft", "action": "customer_form_fill"},
                {"label": "Billing city", "kind": "input", "safety": "safe_draft", "action": "customer_form_fill"},
                {"label": "Billing postal", "kind": "input", "safety": "safe_draft", "action": "customer_form_fill"},
                {"label": "Clear billing address", "kind": "button", "safety": "safe_draft", "action": "customer_clear_address"},
                {"label": "Ship to", "kind": "input", "safety": "safe_draft", "action": "customer_form_fill"},
                {"label": "Shipping address", "kind": "input", "safety": "safe_draft", "action": "customer_form_fill"},
                {"label": "Shipping country", "kind": "filter", "safety": "safe_draft", "action": "customer_form_fill"},
                {"label": "Shipping province, state, or region", "kind": "filter", "safety": "safe_draft", "action": "customer_form_fill"},
                {"label": "Shipping city", "kind": "input", "safety": "safe_draft", "action": "customer_form_fill"},
                {"label": "Shipping postal", "kind": "input", "safety": "safe_draft", "action": "customer_form_fill"},
                {"label": "Shipping phone", "kind": "input", "safety": "safe_draft", "action": "customer_form_fill"},
                {"label": "Delivery instructions", "kind": "input", "safety": "safe_draft", "action": "customer_form_fill"},
                {"label": "Clear shipping address", "kind": "button", "safety": "safe_draft", "action": "customer_clear_address"},
                {"label": "Cancel", "kind": "button", "safety": "read_only", "action": "customer_cancel_form"},
                {"label": "Save", "kind": "button", "safety": "safe_draft", "action": "customer_create"},
            ],
            "review_gate": "FAB may prepare and save new customer drafts; overwriting existing customer records requires confirmation.",
        },
        "customer_csv_import_page": {
            "surface": "customers",
            "module": "sales_payments",
            "automation_mode": "confirmed_execute",
            "controls": [
                {"label": "Choose File", "kind": "button", "safety": "requires_confirmation", "action": "customer_import_csv_choose_file"},
                {"label": "Upload and preview customers", "kind": "button", "safety": "requires_confirmation", "action": "customer_import_csv_preview"},
                {"label": "Maximum 10MB file size. CSV file type only.", "kind": "report", "safety": "read_only", "action": "customer_import_csv_instructions"},
                {"label": "View instructions", "kind": "link", "safety": "read_only", "action": "customer_import_csv_instructions"},
                {"label": "Download and view our customer CSV template.", "kind": "external", "safety": "read_only", "action": "customer_import_csv_template_download"},
                {"label": "CSV headers: Company Name, First Name, Last Name, Email, Phone, Address 1, Address 2, City, Postal Code, Country, Currency", "kind": "report", "safety": "read_only", "action": "customer_import_csv_instructions"},
                {"label": "UTF-8 CSV format", "kind": "report", "safety": "read_only", "action": "customer_import_csv_instructions"},
            ],
            "review_gate": "Choosing, uploading, previewing, and importing customer CSV files require confirmation.",
        },
        "purchases_pages": {
            "surface": "bills",
            "module": "purchases",
            "automation_mode": "safe_draft",
            "controls": [
                {"label": "Bills", "kind": "page", "safety": "read_only", "action": "bill_workspace_read"},
                {"label": "Vendors", "kind": "page", "safety": "safe_draft", "action": "vendor_create"},
                {"label": "Products & Services", "kind": "page", "safety": "safe_draft", "action": "buying_product_service_upsert"},
                {"label": "Create a bill", "kind": "button", "safety": "safe_draft", "action": "bill_create"},
                {"label": "Create your first bill", "kind": "button", "safety": "safe_draft", "action": "bill_create"},
                {"label": "From/To date filters", "kind": "filter", "safety": "read_only", "action": "bill_filter"},
                {"label": "Vendor filter", "kind": "filter", "safety": "read_only", "action": "bill_filter"},
                {"label": "Bill date filter", "kind": "filter", "safety": "read_only", "action": "bill_filter"},
            ],
            "review_gate": "Marking bills paid and changing vendor data requires confirmation.",
        },
        "bills_workspace": {
            "surface": "bills",
            "module": "purchases",
            "automation_mode": "safe_draft",
            "controls": [
                {"label": "BILLS", "kind": "page", "safety": "read_only", "action": "bill_workspace_read"},
                {"label": "Follow the money", "kind": "report", "safety": "read_only", "action": "bill_workspace_read"},
                {"label": "Monitor your cash flow. Create bills from vendors and mark them as paid to track your expenses.", "kind": "report", "safety": "read_only", "action": "bill_workspace_read"},
                {"label": "Create your first bill", "kind": "button", "safety": "safe_draft", "action": "bill_create"},
                {"label": "Exclusive offer: Invoice better with Zoho", "kind": "report", "safety": "read_only", "action": "zoho_offer_open"},
                {"label": "Explore Zoho Books and unlock your offer", "kind": "external", "safety": "read_only", "action": "zoho_offer_open"},
            ],
            "review_gate": "FAB may read the bills workspace and open a draft bill form; external offers remain read-only unless explicitly requested.",
        },
        "bill_add_form_fields": {
            "surface": "bills",
            "module": "purchases",
            "automation_mode": "safe_draft",
            "controls": [
                {"label": "Bill form", "kind": "page", "safety": "read_only", "action": "bill_form_read"},
                {"label": "Vendor *", "kind": "filter", "safety": "safe_draft", "action": "bill_form_fill"},
                {"label": "Currency", "kind": "filter", "safety": "safe_draft", "action": "bill_form_fill"},
                {"label": "Bill Date", "kind": "input", "safety": "safe_draft", "action": "bill_form_fill"},
                {"label": "Due Date", "kind": "input", "safety": "safe_draft", "action": "bill_form_fill"},
                {"label": "P.O./S.O.", "kind": "input", "safety": "safe_draft", "action": "bill_form_fill"},
                {"label": "Bill #", "kind": "input", "safety": "safe_draft", "action": "bill_form_fill"},
                {"label": "Notes", "kind": "input", "safety": "safe_draft", "action": "bill_form_fill"},
                {"label": "Item", "kind": "filter", "safety": "safe_draft", "action": "bill_line_item_fill"},
                {"label": "Expense Category", "kind": "filter", "safety": "safe_draft", "action": "bill_line_item_fill"},
                {"label": "Description", "kind": "input", "safety": "safe_draft", "action": "bill_line_item_fill"},
                {"label": "Qty", "kind": "input", "safety": "safe_draft", "action": "bill_line_item_fill"},
                {"label": "Price", "kind": "input", "safety": "safe_draft", "action": "bill_line_item_fill"},
                {"label": "Tax", "kind": "filter", "safety": "safe_draft", "action": "bill_line_item_fill"},
                {"label": "Amount", "kind": "report", "safety": "read_only", "action": "bill_form_read"},
                {"label": "Delete this row", "kind": "button", "safety": "safe_draft", "action": "bill_line_item_delete"},
                {"label": "Add a line", "kind": "button", "safety": "safe_draft", "action": "bill_update"},
                {"label": "Cancel", "kind": "button", "safety": "read_only", "action": "bill_cancel_form"},
                {"label": "Save", "kind": "button", "safety": "safe_draft", "action": "bill_create"},
            ],
            "review_gate": "FAB may draft and save source-backed bills; paying, deleting, or overwriting existing bills requires confirmation.",
        },
        "bill_editor_lifecycle": {
            "surface": "bills",
            "module": "purchases",
            "automation_mode": "confirmed_execute",
            "controls": [
                {"label": "Save bill", "kind": "button", "safety": "safe_draft", "action": "bill_update"},
                {"label": "Add line item", "kind": "button", "safety": "safe_draft", "action": "bill_update"},
                {"label": "Delete line item", "kind": "button", "safety": "safe_draft", "action": "bill_line_item_delete"},
                {"label": "Attach receipt", "kind": "button", "safety": "safe_draft", "action": "bill_attach_receipt"},
                {"label": "Mark paid", "kind": "button", "safety": "requires_confirmation", "action": "bill_mark_paid"},
                {"label": "Delete bill", "kind": "button", "safety": "requires_confirmation", "action": "bill_delete"},
            ],
            "review_gate": "FAB may save source-backed drafts; paid-state and delete actions require confirmation.",
        },
        "vendors_legacy_workspace": {
            "surface": "vendors",
            "module": "purchases",
            "automation_mode": "safe_draft",
            "controls": [
                {"label": "Vendors", "kind": "page", "safety": "read_only", "action": "vendor_list_read"},
                {"label": "Import from...", "kind": "button", "safety": "read_only", "action": "vendor_import_menu_open"},
                {"label": "CSV", "kind": "link", "safety": "requires_confirmation", "action": "vendor_import_csv"},
                {"label": "Google Contacts", "kind": "link", "safety": "requires_confirmation", "action": "vendor_import_google_contacts"},
                {"label": "Import from CSV", "kind": "button", "safety": "requires_confirmation", "action": "vendor_import_csv"},
                {"label": "Import from Google Contacts", "kind": "button", "safety": "requires_confirmation", "action": "vendor_import_google_contacts"},
                {"label": "Add a vendor", "kind": "link", "safety": "safe_draft", "action": "vendor_create"},
                {"label": "Create bill", "kind": "link", "safety": "safe_draft", "action": "vendor_create_bill"},
                {"label": "Name column", "kind": "report", "safety": "read_only", "action": "vendor_list_read"},
                {"label": "Email column", "kind": "report", "safety": "read_only", "action": "vendor_list_read"},
                {"label": "Phone column", "kind": "report", "safety": "read_only", "action": "vendor_list_read"},
                {"label": "Actions column", "kind": "report", "safety": "read_only", "action": "vendor_list_read"},
                {"label": "Edit", "kind": "link", "safety": "requires_confirmation", "action": "vendor_update"},
                {"label": "Delete", "kind": "link", "safety": "requires_confirmation", "action": "vendor_delete"},
            ],
            "review_gate": "Imports, edits, and deletes require explicit approval.",
        },
        "vendor_form_fields": {
            "surface": "vendors",
            "module": "purchases",
            "automation_mode": "safe_draft",
            "controls": [
                {"label": "Add a vendor", "kind": "page", "safety": "read_only", "action": "vendor_form_read"},
                {"label": "Vendor Name", "kind": "input", "safety": "safe_draft", "action": "vendor_form_fill"},
                {"label": "Email", "kind": "input", "safety": "safe_draft", "action": "vendor_form_fill"},
                {"label": "First name", "kind": "input", "safety": "safe_draft", "action": "vendor_form_fill"},
                {"label": "Last name", "kind": "input", "safety": "safe_draft", "action": "vendor_form_fill"},
                {"label": "Currency", "kind": "filter", "safety": "safe_draft", "action": "vendor_form_fill"},
                {"label": "Country", "kind": "filter", "safety": "safe_draft", "action": "vendor_form_fill"},
                {"label": "Province/State", "kind": "input", "safety": "safe_draft", "action": "vendor_form_fill"},
                {"label": "Address line 1", "kind": "input", "safety": "safe_draft", "action": "vendor_form_fill"},
                {"label": "Address line 2", "kind": "input", "safety": "safe_draft", "action": "vendor_form_fill"},
                {"label": "City", "kind": "input", "safety": "safe_draft", "action": "vendor_form_fill"},
                {"label": "Postal/Zip code", "kind": "input", "safety": "safe_draft", "action": "vendor_form_fill"},
                {"label": "Enter additional information (optional)", "kind": "button", "safety": "safe_draft", "action": "vendor_form_fill"},
                {"label": "Save", "kind": "button", "safety": "safe_draft", "action": "vendor_create"},
            ],
            "review_gate": "FAB may save new vendor drafts after duplicate checks; existing vendor edits require confirmation.",
        },
        "buying_products_services_legacy": {
            "surface": "buying_products_services",
            "module": "purchases",
            "automation_mode": "safe_draft",
            "controls": [
                {"label": "Products & Services (Purchases)", "kind": "page", "safety": "read_only", "action": "buying_product_service_list_read"},
                {"label": "Add a product or service", "kind": "link", "safety": "safe_draft", "action": "buying_product_service_upsert"},
                {"label": "You haven't added any products yet.", "kind": "report", "safety": "read_only", "action": "buying_product_service_list_read"},
                {"label": "Name column", "kind": "report", "safety": "read_only", "action": "buying_product_service_list_read"},
                {"label": "Price column", "kind": "report", "safety": "read_only", "action": "buying_product_service_list_read"},
                {"label": "Actions column", "kind": "report", "safety": "read_only", "action": "buying_product_service_list_read"},
                {"label": "Edit", "kind": "link", "safety": "requires_confirmation", "action": "buying_product_service_update"},
                {"label": "Delete", "kind": "link", "safety": "requires_confirmation", "action": "buying_product_service_delete"},
            ],
            "review_gate": "New purchase item drafts are safe; edits/deletes require confirmation.",
        },
        "buying_product_service_form_fields": {
            "surface": "buying_products_services",
            "module": "purchases",
            "automation_mode": "safe_draft",
            "controls": [
                {"label": "Add a Product or Service", "kind": "page", "safety": "read_only", "action": "buying_product_service_form_read"},
                {"label": "Name *", "kind": "input", "safety": "safe_draft", "action": "buying_product_service_form_fill"},
                {"label": "Description", "kind": "input", "safety": "safe_draft", "action": "buying_product_service_form_fill"},
                {"label": "Price", "kind": "input", "safety": "safe_draft", "action": "buying_product_service_form_fill"},
                {"label": "Price default 0.00", "kind": "report", "safety": "read_only", "action": "buying_product_service_default_state_read"},
                {"label": "Sell this", "kind": "input", "safety": "safe_draft", "action": "buying_product_service_sell_toggle"},
                {"label": "Income account", "kind": "filter", "safety": "safe_draft", "action": "buying_product_service_income_account_select"},
                {"label": "Buy this", "kind": "input", "safety": "safe_draft", "action": "buying_product_service_buy_toggle"},
                {"label": "Expense account", "kind": "filter", "safety": "safe_draft", "action": "buying_product_service_expense_account_select"},
                {"label": "Create a new account", "kind": "button", "safety": "requires_confirmation", "action": "buying_product_service_account_create"},
                {"label": "Sales tax", "kind": "filter", "safety": "safe_draft", "action": "buying_product_service_tax_select"},
                {"label": "Income Tax", "kind": "report", "safety": "read_only", "action": "buying_product_service_default_state_read"},
                {"label": "Save", "kind": "button", "safety": "safe_draft", "action": "buying_product_service_upsert"},
            ],
            "review_gate": "FAB may prepare and save new buying item drafts; edits, deletes, and tax master-data changes require confirmation.",
        },
        "products_services_legacy": {
            "surface": "selling_products_services",
            "module": "sales_payments",
            "automation_mode": "safe_draft",
            "controls": [
                {"label": "Products & Services (Sales)", "kind": "page", "safety": "read_only", "action": "product_service_list_read"},
                {"label": "Add a product or service", "kind": "link", "safety": "safe_draft", "action": "selling_product_service_upsert"},
                {"label": "Name column", "kind": "report", "safety": "read_only", "action": "product_service_list_read"},
                {"label": "Price column", "kind": "report", "safety": "read_only", "action": "product_service_list_read"},
                {"label": "Actions column", "kind": "report", "safety": "read_only", "action": "product_service_list_read"},
                {"label": "Edit", "kind": "link", "safety": "requires_confirmation", "action": "product_service_update"},
                {"label": "Delete", "kind": "link", "safety": "requires_confirmation", "action": "product_service_delete"},
            ],
            "review_gate": "New drafts are safe; edits/deletes require confirmation.",
        },
        "product_service_form_fields": {
            "surface": "selling_products_services",
            "module": "sales_payments",
            "automation_mode": "safe_draft",
            "controls": [
                {"label": "Add a Product or Service", "kind": "page", "safety": "read_only", "action": "product_service_form_read"},
                {"label": "Name *", "kind": "input", "safety": "safe_draft", "action": "product_service_form_fill"},
                {"label": "Description", "kind": "input", "safety": "safe_draft", "action": "product_service_form_fill"},
                {"label": "Price", "kind": "input", "safety": "safe_draft", "action": "product_service_form_fill"},
                {"label": "Sell this", "kind": "input", "safety": "safe_draft", "action": "product_service_sell_toggle"},
                {"label": "Income account", "kind": "filter", "safety": "safe_draft", "action": "product_service_income_account_select"},
                {"label": "Buy this", "kind": "input", "safety": "safe_draft", "action": "product_service_buy_toggle"},
                {"label": "Expense account", "kind": "filter", "safety": "safe_draft", "action": "product_service_expense_account_select"},
                {"label": "Sales tax", "kind": "filter", "safety": "safe_draft", "action": "product_service_tax_select"},
                {"label": "Add new item", "kind": "button", "safety": "requires_confirmation", "action": "sales_tax_create"},
                {"label": "Save", "kind": "button", "safety": "safe_draft", "action": "selling_product_service_upsert"},
            ],
            "review_gate": "FAB may prepare and save new product/service drafts; edits, deletes, and new tax master data require confirmation.",
        },
        "transactions_workspace": {
            "surface": "transactions",
            "module": "accounting",
            "automation_mode": "safe_draft",
            "controls": [
                {"label": "Transactions", "kind": "page", "safety": "read_only", "action": "transaction_workspace_read"},
                {"label": "All accounts", "kind": "filter", "safety": "read_only", "action": "transaction_filter"},
                {"label": "Add transaction", "kind": "button", "safety": "safe_draft", "action": "transaction_add"},
                {"label": "Add deposit", "kind": "menu", "safety": "safe_draft", "action": "transaction_add_deposit"},
                {"label": "Add withdrawal", "kind": "menu", "safety": "safe_draft", "action": "transaction_add_withdrawal"},
                {"label": "Add journal entry", "kind": "menu", "safety": "requires_confirmation", "action": "transaction_add_journal_entry"},
                {"label": "More", "kind": "button", "safety": "read_only", "action": "transaction_more_menu_open"},
                {"label": "Upload transactions", "kind": "link", "safety": "requires_confirmation", "action": "statement_upload"},
                {"label": "Account balance menu item", "kind": "menu", "safety": "read_only", "action": "transaction_account_filter_select"},
                {"label": "Upload bank statement", "kind": "menu", "safety": "requires_confirmation", "action": "transaction_account_upload_statement"},
                {"label": "Add a new account", "kind": "menu", "safety": "requires_confirmation", "action": "transaction_account_create"},
                {"label": "Reconciliation toggle", "kind": "input", "safety": "read_only", "action": "transaction_reconciliation_toggle_read"},
                {"label": "filter icon", "kind": "button", "safety": "read_only", "action": "transaction_filter"},
                {"label": "sort icon", "kind": "button", "safety": "read_only", "action": "transaction_sort"},
                {"label": "Newest to oldest", "kind": "menu", "safety": "read_only", "action": "transaction_sort_newest_to_oldest"},
                {"label": "Oldest to newest", "kind": "menu", "safety": "read_only", "action": "transaction_sort_oldest_to_newest"},
                {"label": "search icon", "kind": "button", "safety": "read_only", "action": "transaction_search"},
                {"label": "Search transactions", "kind": "input", "safety": "read_only", "action": "transaction_search"},
                {"label": "Search", "kind": "button", "safety": "read_only", "action": "transaction_search_submit"},
                {"label": "Select all", "kind": "input", "safety": "read_only", "action": "transaction_bulk_select"},
                {"label": "Select for bulk actions", "kind": "input", "safety": "read_only", "action": "transaction_bulk_select"},
                {"label": "Date", "kind": "report", "safety": "read_only", "action": "transaction_row_read"},
                {"label": "Description & Account", "kind": "report", "safety": "read_only", "action": "transaction_row_read"},
                {"label": "Category", "kind": "report", "safety": "read_only", "action": "transaction_row_read"},
                {"label": "Amount", "kind": "report", "safety": "read_only", "action": "transaction_row_read"},
                {"label": "Status", "kind": "report", "safety": "read_only", "action": "transaction_row_read"},
                {"label": "Load More Transactions", "kind": "button", "safety": "read_only", "action": "transaction_load_more"},
                {"label": "Your feedback helped us improve reconciliation", "kind": "report", "safety": "read_only", "action": "transaction_reconciliation_notice_read"},
                {"label": "Close", "kind": "button", "safety": "read_only", "action": "transaction_notice_close"},
                {"label": "Merge", "kind": "button", "safety": "requires_confirmation", "action": "transaction_merge"},
                {"label": "Delete", "kind": "button", "safety": "requires_confirmation", "action": "transaction_delete"},
                {"label": "Upload", "kind": "button", "safety": "requires_confirmation", "action": "statement_upload"},
            ],
            "review_gate": "High-confidence categorization can run; merge/delete/upload require approval.",
        },
        "transaction_add_form_fields": {
            "surface": "transactions",
            "module": "accounting",
            "automation_mode": "safe_draft",
            "controls": [
                {"label": "Date", "kind": "input", "safety": "safe_draft", "action": "transaction_form_fill"},
                {"label": "Open date picker", "kind": "button", "safety": "safe_draft", "action": "transaction_date_picker_open"},
                {"label": "Description", "kind": "input", "safety": "safe_draft", "action": "transaction_form_fill"},
                {"label": "Write a Description", "kind": "input", "safety": "safe_draft", "action": "transaction_form_fill"},
                {"label": "Account", "kind": "filter", "safety": "safe_draft", "action": "transaction_account_select"},
                {"label": "Type", "kind": "filter", "safety": "safe_draft", "action": "transaction_type_select"},
                {"label": "Withdrawal Deposit", "kind": "filter", "safety": "safe_draft", "action": "transaction_type_select"},
                {"label": "Amount", "kind": "input", "safety": "safe_draft", "action": "transaction_form_fill"},
                {"label": "Category", "kind": "filter", "safety": "safe_draft", "action": "transaction_category_select"},
                {"label": "Include sales tax", "kind": "input", "safety": "safe_draft", "action": "transaction_sales_tax_toggle"},
                {"label": "Add customer", "kind": "button", "safety": "safe_draft", "action": "transaction_customer_select"},
                {"label": "Add vendor", "kind": "button", "safety": "safe_draft", "action": "transaction_vendor_select"},
                {"label": "Split transaction", "kind": "button", "safety": "requires_confirmation", "action": "transaction_split"},
                {"label": "Notes", "kind": "page", "safety": "safe_draft", "action": "transaction_note_fill"},
                {"label": "Write a note here...", "kind": "input", "safety": "safe_draft", "action": "transaction_note_fill"},
                {"label": "Receipt", "kind": "page", "safety": "safe_draft", "action": "transaction_attach_receipt"},
                {"label": "Upload receipt...", "kind": "button", "safety": "safe_draft", "action": "transaction_attach_receipt"},
                {"label": "Cancel", "kind": "button", "safety": "read_only", "action": "transaction_cancel_form"},
                {"label": "Save", "kind": "button", "safety": "safe_draft", "action": "transaction_add"},
            ],
            "review_gate": "FAB may draft simple deposits/withdrawals; splits, uploads, and journal entries require confirmation.",
        },
        "transaction_statement_upload_page": {
            "surface": "transactions",
            "module": "accounting",
            "automation_mode": "confirmed_execute",
            "controls": [
                {"label": "1. Download your electronic statement", "kind": "page", "safety": "read_only", "action": "statement_upload_instructions_read"},
                {"label": "2. Upload your statement to Wave", "kind": "page", "safety": "read_only", "action": "statement_upload_instructions_read"},
                {"label": "3. Manage your transactions", "kind": "page", "safety": "read_only", "action": "statement_upload_instructions_read"},
                {"label": "Statement", "kind": "input", "safety": "requires_confirmation", "action": "statement_file_choose"},
                {"label": "Payment account", "kind": "filter", "safety": "requires_confirmation", "action": "statement_payment_account_select"},
                {"label": "Create a new account", "kind": "button", "safety": "requires_confirmation", "action": "statement_account_create"},
                {"label": "Upload", "kind": "button", "safety": "requires_confirmation", "action": "statement_upload"},
                {"label": "upload a statement in CSV format", "kind": "link", "safety": "read_only", "action": "statement_upload_instructions_read"},
                {"label": "what to do if Wave can't read your CSV", "kind": "link", "safety": "read_only", "action": "statement_upload_help_open"},
                {"label": "CSV template", "kind": "link", "safety": "read_only", "action": "statement_csv_template_download"},
                {"label": "Learn more.", "kind": "link", "safety": "read_only", "action": "statement_upload_help_open"},
            ],
            "review_gate": "Choosing files, creating accounts, and uploading statements require confirmation.",
        },
        "transaction_row_controls": {
            "surface": "transactions",
            "module": "accounting",
            "automation_mode": "safe_draft",
            "controls": [
                {"label": "Edit transaction", "kind": "button", "safety": "safe_draft", "action": "transaction_update"},
                {"label": "Categorize", "kind": "button", "safety": "safe_draft", "action": "transaction_categorize"},
                {"label": "Split", "kind": "button", "safety": "requires_confirmation", "action": "transaction_split"},
                {"label": "Attach receipt", "kind": "button", "safety": "safe_draft", "action": "transaction_attach_receipt"},
                {"label": "Check/mark reviewed", "kind": "button", "safety": "safe_draft", "action": "transaction_mark_reviewed"},
                {"label": "Reconcile", "kind": "button", "safety": "requires_confirmation", "action": "transaction_reconcile"},
                {"label": "Merge", "kind": "button", "safety": "requires_confirmation", "action": "transaction_merge"},
                {"label": "Delete", "kind": "button", "safety": "requires_confirmation", "action": "transaction_delete"},
            ],
            "review_gate": "Routine edits and receipt attachments can be drafted; split, reconcile, merge, and delete require confirmation.",
        },
        "chart_accounts_workspace": {
            "surface": "chart_of_accounts",
            "module": "accounting",
            "automation_mode": "confirmed_execute",
            "controls": [
                {"label": "Chart of Accounts", "kind": "page", "safety": "read_only", "action": "chart_account_list_read"},
                {"label": "help icon", "kind": "button", "safety": "read_only", "action": "chart_account_help_open"},
                {"label": "Add a New Account", "kind": "button", "safety": "requires_confirmation", "action": "chart_account_create"},
                {"label": "Add account", "kind": "button", "safety": "requires_confirmation", "action": "chart_account_create"},
                {"label": "Add a new account", "kind": "button", "safety": "requires_confirmation", "action": "chart_account_create"},
                {"label": "Assets 3", "kind": "tab", "safety": "read_only", "action": "chart_account_tab_view"},
                {"label": "Liabilities & Credit Cards 4", "kind": "tab", "safety": "read_only", "action": "chart_account_tab_view"},
                {"label": "Income 14", "kind": "tab", "safety": "read_only", "action": "chart_account_tab_view"},
                {"label": "Expenses 31", "kind": "tab", "safety": "read_only", "action": "chart_account_tab_view"},
                {"label": "Equity 2", "kind": "tab", "safety": "read_only", "action": "chart_account_tab_view"},
                {"label": "Cash and Bank", "kind": "report", "safety": "read_only", "action": "chart_account_section_read"},
                {"label": "Money in Transit", "kind": "report", "safety": "read_only", "action": "chart_account_section_read"},
                {"label": "Credit Card", "kind": "report", "safety": "read_only", "action": "chart_account_section_read"},
                {"label": "Operating Expense", "kind": "report", "safety": "read_only", "action": "chart_account_section_read"},
                {"label": "Business Owner Contribution and Drawing", "kind": "report", "safety": "read_only", "action": "chart_account_section_read"},
                {"label": "Last transaction on", "kind": "report", "safety": "read_only", "action": "chart_account_activity_read"},
                {"label": "No transactions for this account", "kind": "report", "safety": "read_only", "action": "chart_account_activity_read"},
                {"label": "Account description", "kind": "report", "safety": "read_only", "action": "chart_account_activity_read"},
                {"label": "Archived", "kind": "report", "safety": "read_only", "action": "chart_account_list_read"},
                {"label": "Archive account", "kind": "button", "safety": "requires_confirmation", "action": "chart_account_archive"},
                {"label": "Account search/type filters", "kind": "filter", "safety": "read_only", "action": "chart_account_map"},
            ],
            "review_gate": "Chart changes affect reporting taxonomy and require approval.",
        },
        "chart_account_editor_controls": {
            "surface": "chart_of_accounts",
            "module": "accounting",
            "automation_mode": "confirmed_execute",
            "controls": [
                {"label": "Add an Account", "kind": "page", "safety": "read_only", "action": "chart_account_form_read"},
                {"label": "close dialog", "kind": "button", "safety": "read_only", "action": "chart_account_cancel_form"},
                {"label": "Account Type", "kind": "filter", "safety": "requires_confirmation", "action": "chart_account_type_select"},
                {"label": "Select one...", "kind": "filter", "safety": "read_only", "action": "chart_account_type_picker_open"},
                {"label": "Search", "kind": "input", "safety": "read_only", "action": "chart_account_type_search"},
                {"label": "Assets Cash and Bank Money in Transit", "kind": "menu", "safety": "requires_confirmation", "action": "chart_account_type_select"},
                {"label": "Liabilities & Credit Cards Credit Card Loan and Line of Credit", "kind": "menu", "safety": "requires_confirmation", "action": "chart_account_type_select"},
                {"label": "Income Income Discount Other Income", "kind": "menu", "safety": "requires_confirmation", "action": "chart_account_type_select"},
                {"label": "Expenses Operating Expense Cost of Goods Sold Payment Processing Fee Payroll Expense", "kind": "menu", "safety": "requires_confirmation", "action": "chart_account_type_select"},
                {"label": "Equity Business Owner Contribution and Drawing Retained Earnings: Profit", "kind": "menu", "safety": "requires_confirmation", "action": "chart_account_type_select"},
                {"label": "Account Name", "kind": "input", "safety": "requires_confirmation", "action": "chart_account_form_fill"},
                {"label": "Account Currency", "kind": "filter", "safety": "requires_confirmation", "action": "chart_account_currency_select"},
                {"label": "EUR (€) - Euro", "kind": "filter", "safety": "requires_confirmation", "action": "chart_account_currency_select"},
                {"label": "Account ID", "kind": "input", "safety": "requires_confirmation", "action": "chart_account_form_fill"},
                {"label": "Description", "kind": "input", "safety": "requires_confirmation", "action": "chart_account_form_fill"},
                {"label": "Edit account", "kind": "button", "safety": "requires_confirmation", "action": "chart_account_update"},
                {"label": "Save", "kind": "button", "safety": "requires_confirmation", "action": "chart_account_update"},
                {"label": "Cancel", "kind": "button", "safety": "read_only", "action": "chart_account_cancel_form"},
                {"label": "Archive", "kind": "button", "safety": "requires_confirmation", "action": "chart_account_archive"},
            ],
            "review_gate": "FAB treats chart changes as admin accounting changes and requires approval.",
        },
        "banking_connected_accounts": {
            "surface": "connected_accounts",
            "module": "banking",
            "automation_mode": "credential_owner",
            "controls": [
                {"label": "Bank connections are unavailable", "kind": "page", "safety": "read_only", "action": "connected_account_unavailable_read"},
                {"label": "Access to transaction auto-import feature is limited for personal businesses.", "kind": "report", "safety": "read_only", "action": "connected_account_unavailable_read"},
                {"label": "enter them manually", "kind": "report", "safety": "safe_draft", "action": "connected_account_manual_entry_plan"},
                {"label": "how to upload your bank and credit card statements", "kind": "external", "safety": "read_only", "action": "connected_account_statement_help_open"},
                {"label": "Connect account", "kind": "button", "safety": "requires_credentials", "action": "connected_account_connect"},
                {"label": "Upload bank/credit card statements", "kind": "link", "safety": "requires_confirmation", "action": "statement_upload"},
            ],
            "review_gate": "FAB must not handle bank credentials or bypass provider login.",
        },
        "connected_account_statement_help_page": {
            "surface": "connected_accounts",
            "module": "banking",
            "automation_mode": "observe",
            "controls": [
                {"label": "Upload bank and credit card statements", "kind": "page", "safety": "read_only", "action": "connected_account_statement_help_open"},
                {"label": "Download your statement from your bank", "kind": "report", "safety": "read_only", "action": "connected_account_statement_upload_steps_read"},
                {"label": "Microsoft Money (.Ofx)", "kind": "report", "safety": "read_only", "action": "connected_account_statement_format_read"},
                {"label": "QuickBooks (.Qbo)", "kind": "report", "safety": "read_only", "action": "connected_account_statement_format_read"},
                {"label": "Quicken (.Qfx)", "kind": "report", "safety": "read_only", "action": "connected_account_statement_format_read"},
                {"label": "Simply Accounting (.Aso)", "kind": "report", "safety": "read_only", "action": "connected_account_statement_format_read"},
                {"label": "Comma-Separated Variable (.CSV)", "kind": "report", "safety": "read_only", "action": "connected_account_statement_format_read"},
                {"label": "add a payment account", "kind": "link", "safety": "requires_confirmation", "action": "connected_account_payment_account_help_open"},
                {"label": "Accounting > Transactions", "kind": "report", "safety": "read_only", "action": "connected_account_statement_upload_steps_read"},
                {"label": "More", "kind": "button", "safety": "read_only", "action": "transaction_more_menu_open"},
                {"label": "Upload transactions", "kind": "menu", "safety": "requires_confirmation", "action": "statement_upload"},
                {"label": "Choose File", "kind": "input", "safety": "requires_confirmation", "action": "statement_file_choose"},
                {"label": "Payment account", "kind": "filter", "safety": "requires_confirmation", "action": "statement_payment_account_select"},
                {"label": "Confirm date", "kind": "button", "safety": "requires_confirmation", "action": "connected_account_statement_mapping_confirm"},
                {"label": "Confirm amounts", "kind": "button", "safety": "requires_confirmation", "action": "connected_account_statement_mapping_confirm"},
                {"label": "Select description", "kind": "button", "safety": "requires_confirmation", "action": "connected_account_statement_mapping_confirm"},
                {"label": "Upload my statement", "kind": "button", "safety": "requires_confirmation", "action": "connected_account_statement_upload_complete"},
                {"label": "Upload a bank or credit card statement in .csv format", "kind": "link", "safety": "read_only", "action": "connected_account_csv_help_open"},
                {"label": "What to do if Wave can't read your statement in CSV format", "kind": "link", "safety": "read_only", "action": "connected_account_csv_help_open"},
                {"label": "What is a payment account?", "kind": "link", "safety": "read_only", "action": "connected_account_payment_account_help_open"},
                {"label": "Upload and download data with Wave Connect", "kind": "link", "safety": "read_only", "action": "connected_account_wave_connect_help_open"},
                {"label": "Automated bookkeeping with auto-updates", "kind": "link", "safety": "read_only", "action": "connected_account_auto_updates_help_open"},
                {"label": "Get support with Wave", "kind": "link", "safety": "requires_confirmation", "action": "connected_account_support_open"},
                {"label": "Was this article helpful?", "kind": "report", "safety": "read_only", "action": "connected_account_statement_help_open"},
                {"label": "Yes", "kind": "button", "safety": "requires_confirmation", "action": "connected_account_help_feedback"},
                {"label": "No", "kind": "button", "safety": "requires_confirmation", "action": "connected_account_help_feedback"},
                {"label": "Facebook", "kind": "external", "safety": "requires_confirmation", "action": "connected_account_help_share"},
                {"label": "LinkedIn", "kind": "external", "safety": "requires_confirmation", "action": "connected_account_help_share"},
            ],
            "review_gate": "Help reading is safe; uploads, payment-account setup, support feedback, support escalation, and social sharing require approval.",
        },
        "reports_catalog": {
            "surface": "reports",
            "module": "reports",
            "automation_mode": "observe",
            "controls": [
                {"label": "Explore Zoho Books and unlock your offer", "kind": "external", "safety": "requires_confirmation", "action": "zoho_offer_open"},
                {"label": "Financial statements", "kind": "page", "safety": "read_only", "action": "report_catalog_section_read"},
                {"label": "Profit & Loss (Income Statement)", "kind": "report", "safety": "read_only", "action": "report_open"},
                {"label": "Balance Sheet", "kind": "report", "safety": "read_only", "action": "report_open"},
                {"label": "Cash Flow", "kind": "report", "safety": "read_only", "action": "report_open"},
                {"label": "Taxes", "kind": "page", "safety": "read_only", "action": "report_catalog_section_read"},
                {"label": "Sales Tax Report", "kind": "report", "safety": "read_only", "action": "report_open"},
                {"label": "Customers", "kind": "page", "safety": "read_only", "action": "report_catalog_section_read"},
                {"label": "Income by Customer", "kind": "report", "safety": "read_only", "action": "report_open"},
                {"label": "Aged Receivables", "kind": "report", "safety": "read_only", "action": "report_open"},
                {"label": "Customer Credits", "kind": "report", "safety": "read_only", "action": "report_open"},
                {"label": "Vendors", "kind": "page", "safety": "read_only", "action": "report_catalog_section_read"},
                {"label": "Purchases by Vendor", "kind": "report", "safety": "read_only", "action": "report_open"},
                {"label": "Aged Payables", "kind": "report", "safety": "read_only", "action": "report_open"},
                {"label": "Detailed reporting", "kind": "page", "safety": "read_only", "action": "report_catalog_section_read"},
                {"label": "Account Balances", "kind": "report", "safety": "read_only", "action": "report_open"},
                {"label": "Trial Balance", "kind": "report", "safety": "read_only", "action": "report_open"},
                {"label": "Account Transactions (General Ledger)", "kind": "report", "safety": "read_only", "action": "report_open"},
            ],
            "review_gate": "Opening/exporting reports is read-only; external sending requires confirmation.",
        },
        "report_detail_controls": {
            "surface": "reports",
            "module": "reports",
            "automation_mode": "observe",
            "controls": [
                {"label": "Export", "kind": "button", "safety": "read_only", "action": "report_export_menu_open"},
                {"label": "Account", "kind": "filter", "safety": "read_only", "action": "report_account_filter_select"},
                {"label": "All Accounts", "kind": "filter", "safety": "read_only", "action": "report_account_filter_select"},
                {"label": "Date Range", "kind": "filter", "safety": "read_only", "action": "report_date_range_set"},
                {"label": "As of", "kind": "filter", "safety": "read_only", "action": "report_as_of_date_set"},
                {"label": "From", "kind": "input", "safety": "read_only", "action": "report_date_range_set"},
                {"label": "To", "kind": "input", "safety": "read_only", "action": "report_date_range_set"},
                {"label": "Open date picker", "kind": "button", "safety": "read_only", "action": "report_date_picker_open"},
                {"label": "Report Type", "kind": "filter", "safety": "read_only", "action": "report_basis_select"},
                {"label": "Show report type details", "kind": "button", "safety": "read_only", "action": "report_type_help_read"},
                {"label": "Accrual (Paid & Unpaid)", "kind": "filter", "safety": "read_only", "action": "report_basis_select"},
                {"label": "Cash Basis (Paid)", "kind": "filter", "safety": "read_only", "action": "report_basis_select"},
                {"label": "Cash Only", "kind": "filter", "safety": "read_only", "action": "report_basis_select"},
                {"label": "Contact", "kind": "filter", "safety": "read_only", "action": "report_contact_filter_select"},
                {"label": "All Contacts", "kind": "filter", "safety": "read_only", "action": "report_contact_filter_select"},
                {"label": "Compare periods", "kind": "filter", "safety": "read_only", "action": "report_filter"},
                {"label": "Update Report", "kind": "button", "safety": "read_only", "action": "report_update"},
                {"label": "Summary", "kind": "button", "safety": "read_only", "action": "report_view_toggle"},
                {"label": "Details", "kind": "button", "safety": "read_only", "action": "report_view_toggle"},
                {"label": "Show Details", "kind": "button", "safety": "read_only", "action": "report_view_toggle"},
                {"label": "Export PDF", "kind": "button", "safety": "read_only", "action": "report_export"},
                {"label": "Export CSV", "kind": "button", "safety": "read_only", "action": "report_export"},
                {"label": "Report table", "kind": "report", "safety": "read_only", "action": "report_table_read"},
                {"label": "Account drilldown link", "kind": "link", "safety": "read_only", "action": "report_drilldown"},
                {"label": "No results were found.", "kind": "report", "safety": "read_only", "action": "report_empty_state_read"},
                {"label": "Try choosing a different date range or account.", "kind": "report", "safety": "read_only", "action": "report_empty_state_read"},
            ],
            "review_gate": "Report filtering, export, and drilldown are read-only inside Wave.",
        },
        "business_settings_invoice_estimates": {
            "surface": "business_settings",
            "module": "settings",
            "automation_mode": "confirmed_execute",
            "controls": [
                {"label": "Save all changes", "kind": "button", "safety": "requires_confirmation", "action": "business_invoice_estimate_settings_update"},
                {"label": "Due upon receipt", "kind": "button", "safety": "requires_confirmation", "action": "business_invoice_estimate_settings_update"},
                {"label": "Estimate validity period", "kind": "button", "safety": "requires_confirmation", "action": "business_invoice_estimate_settings_update"},
            ],
            "review_gate": "Business settings are admin changes and always require approval.",
        },
        "financial_settings_page": {
            "surface": "financial_settings",
            "module": "settings",
            "automation_mode": "confirmed_execute",
            "controls": [
                {"label": "Fiscal year month", "kind": "filter", "safety": "requires_confirmation", "action": "financial_settings_update"},
                {"label": "Fiscal year day", "kind": "filter", "safety": "requires_confirmation", "action": "financial_settings_update"},
                {"label": "Business Currency", "kind": "input", "safety": "requires_confirmation", "action": "financial_settings_update"},
                {"label": "Save", "kind": "button", "safety": "requires_confirmation", "action": "financial_settings_update"},
            ],
            "review_gate": "Financial settings affect reporting periods and currency assumptions, so they require approval.",
        },
        "sales_tax_settings_page": {
            "surface": "sales_tax_settings",
            "module": "settings",
            "automation_mode": "confirmed_execute",
            "controls": [
                {"label": "Create a sales tax", "kind": "button", "safety": "requires_confirmation", "action": "sales_tax_create"},
                {"label": "Edit tax", "kind": "button", "safety": "requires_confirmation", "action": "sales_tax_update"},
                {"label": "Delete tax", "kind": "button", "safety": "requires_confirmation", "action": "sales_tax_delete"},
                {"label": "Cancel", "kind": "button", "safety": "read_only"},
            ],
            "review_gate": "Tax creates, updates, and deletes require explicit approval.",
        },
        "subscription_management_page": {
            "surface": "subscription_management",
            "module": "settings",
            "automation_mode": "confirmed_execute",
            "controls": [
                {"label": "Go to payroll billing", "kind": "external", "safety": "requires_confirmation", "action": "payroll_billing_open"},
                {"label": "Wave Advisors Portal", "kind": "external", "safety": "requires_confirmation", "action": "wave_advisors_portal_open"},
                {"label": "Current plan", "kind": "page", "safety": "read_only", "action": "subscription_status_read"},
            ],
            "review_gate": "Billing portals and subscription changes require explicit account-owner approval.",
        },
        "data_export_page": {
            "surface": "data_export",
            "module": "settings",
            "automation_mode": "confirmed_execute",
            "controls": [
                {"label": "Data Export", "kind": "link", "safety": "requires_confirmation", "action": "data_export_start"},
            ],
            "review_gate": "Data export can expose financial data and requires approval.",
        },
        "settings_account_menu": {
            "surface": "business_settings",
            "module": "settings",
            "automation_mode": "confirmed_execute",
            "controls": [
                {"label": "Business settings", "kind": "link", "safety": "read_only"},
                {"label": "Integrations", "kind": "link", "safety": "read_only"},
                {"label": "Switch businesses", "kind": "button", "safety": "requires_confirmation", "action": "business_switch"},
                {"label": "Profile settings", "kind": "external", "safety": "requires_confirmation", "action": "profile_settings_update"},
                {"label": "Back to Wave", "kind": "button", "safety": "read_only", "action": "back_to_wave"},
                {"label": "Sign out", "kind": "external", "safety": "unsupported", "action": "sign_out"},
                {"label": "Share suggestion", "kind": "button", "safety": "requires_confirmation", "action": "feedback_send"},
            ],
            "review_gate": "Profile, switch-business, sign-out, and feedback actions are not autonomous bookkeeping steps.",
        },
        "user_management_controls": {
            "surface": "business_settings",
            "module": "settings",
            "automation_mode": "confirmed_execute",
            "controls": [
                {"label": "Invite user", "kind": "button", "safety": "requires_confirmation", "action": "business_user_invite"},
                {"label": "Manage your profile", "kind": "external", "safety": "requires_confirmation", "action": "profile_settings_update"},
                {"label": "Learn more about all user types", "kind": "external", "safety": "read_only", "action": "wave_help_open"},
                {"label": "Change role", "kind": "button", "safety": "requires_confirmation", "action": "business_user_role_update"},
                {"label": "Remove user", "kind": "button", "safety": "requires_confirmation", "action": "business_user_delete"},
            ],
            "review_gate": "Access control changes always require account-owner approval.",
        },
        "integrations_catalog": {
            "surface": "integrations",
            "module": "integrations",
            "automation_mode": "confirmed_execute",
            "controls": [
                {"label": "Add to Sheets", "kind": "link", "safety": "requires_confirmation", "action": "google_sheets_add"},
                {"label": "Connect", "kind": "link", "safety": "requires_confirmation", "action": "integration_connect"},
                {"label": "Use workflow", "kind": "link", "safety": "requires_confirmation", "action": "make_workflow_use"},
                {"label": "Upgrade now", "kind": "button", "safety": "requires_confirmation", "action": "subscription_upgrade"},
            ],
            "review_gate": "External OAuth, data sharing, and subscription changes require confirmation.",
        },
        "wave_payments_page": {
            "surface": "wave_payments",
            "module": "integrations",
            "automation_mode": "confirmed_execute",
            "controls": [
                {"label": "Get Started", "kind": "button", "safety": "requires_confirmation", "action": "wave_payments_get_started"},
                {"label": "Try it now", "kind": "button", "safety": "requires_confirmation", "action": "wave_payments_get_started"},
                {"label": "Terms of Service", "kind": "external", "safety": "read_only", "action": "wave_terms_open"},
                {"label": "Contact Support", "kind": "button", "safety": "requires_confirmation", "action": "wave_support_contact"},
                {"label": "Book a free consultation", "kind": "external", "safety": "requires_confirmation", "action": "wave_advisors_consultation_open"},
            ],
            "review_gate": "Payment onboarding, support contact, and consultation booking require approval.",
        },
        "business_checking_page": {
            "surface": "business_checking",
            "module": "integrations",
            "automation_mode": "confirmed_execute",
            "controls": [
                {"label": "BUSINESS CHECKING", "kind": "page", "safety": "read_only", "action": "business_checking_offer_read"},
                {"label": "The largest small business banking platform in the U.S.", "kind": "page", "safety": "read_only", "action": "business_checking_offer_read"},
                {"label": "Open account", "kind": "button", "safety": "requires_confirmation", "action": "business_checking_open_account"},
                {"label": "Get started", "kind": "button", "safety": "requires_confirmation", "action": "business_checking_open_account"},
                {"label": "Get 6 months of Wave's Pro Plan free", "kind": "report", "safety": "read_only", "action": "business_checking_offer_read"},
                {"label": "No monthly fees", "kind": "report", "safety": "read_only", "action": "business_checking_feature_read"},
                {"label": "High-APY business checking", "kind": "report", "safety": "read_only", "action": "business_checking_feature_read"},
                {"label": "Sub-accounts for easier budgeting", "kind": "report", "safety": "read_only", "action": "business_checking_feature_read"},
                {"label": "Debit cards for you and your team", "kind": "report", "safety": "read_only", "action": "business_checking_feature_read"},
                {"label": "Free Bill Pay software and ACH payments", "kind": "report", "safety": "read_only", "action": "business_checking_feature_read"},
                {"label": "3 months free of a Plus or Premier plan", "kind": "report", "safety": "read_only", "action": "business_checking_offer_read"},
                {"label": "Use the code", "kind": "report", "safety": "read_only", "action": "business_checking_claim_steps_read"},
                {"label": "Add funds", "kind": "report", "safety": "read_only", "action": "business_checking_claim_steps_read"},
                {"label": "Use your card", "kind": "report", "safety": "read_only", "action": "business_checking_claim_steps_read"},
                {"label": "Promotional Terms and Conditions", "kind": "report", "safety": "read_only", "action": "business_checking_promo_terms_read"},
                {"label": "Business Checking Account Agreement", "kind": "external", "safety": "read_only", "action": "business_checking_terms_open"},
                {"label": "Terms of Interest Accrual", "kind": "external", "safety": "read_only", "action": "business_checking_terms_open"},
                {"label": "Bluevine Business Checking Account Agreement", "kind": "external", "safety": "read_only", "action": "business_checking_terms_open"},
            ],
            "review_gate": "Opening a bank account or external banking flow requires explicit approval.",
        },
        "zoho_migration_offer": {
            "surface": "zoho_migration_offer",
            "module": "integrations",
            "automation_mode": "confirmed_execute",
            "controls": [
                {"label": "Explore Zoho Books and unlock your offer", "kind": "external", "safety": "requires_confirmation", "action": "zoho_offer_open"},
            ],
            "review_gate": "Opening external commercial offers requires explicit user intent.",
        },
        "payroll_unsupported_page": {
            "surface": "payroll",
            "module": "settings",
            "automation_mode": "blocked",
            "controls": [
                {"label": "Exclusive offer: Invoice better with Zoho", "kind": "external", "safety": "requires_confirmation", "action": "zoho_offer_open"},
                {"label": "Wave Payroll is available to US and Canadian businesses", "kind": "report", "safety": "read_only", "action": "payroll_availability_read"},
                {"label": "Payroll is not available in Quebec at this time.", "kind": "report", "safety": "read_only", "action": "payroll_availability_read"},
                {"label": "To access Wave Payroll", "kind": "report", "safety": "read_only", "action": "payroll_eligibility_rules_read"},
                {"label": "Business country, employee country, and business currency must align", "kind": "report", "safety": "read_only", "action": "payroll_eligibility_rules_read"},
                {"label": "Adjust business settings", "kind": "button", "safety": "read_only", "action": "payroll_business_settings_open"},
            ],
            "review_gate": "Payroll is blocked for this business region/currency context.",
        },
        "payroll_business_eligibility_settings": {
            "surface": "business_settings",
            "module": "settings",
            "automation_mode": "confirmed_execute",
            "controls": [
                {"label": "Businesses", "kind": "page", "safety": "read_only", "action": "business_list_read"},
                {"label": "Create a Business", "kind": "link", "safety": "requires_confirmation", "action": "business_create"},
                {"label": "Set default business", "kind": "link", "safety": "requires_confirmation", "action": "business_set_default"},
                {"label": "Edit business", "kind": "link", "safety": "read_only", "action": "business_profile_read"},
                {"label": "Company Name", "kind": "input", "safety": "requires_confirmation", "action": "business_profile_update"},
                {"label": "Country", "kind": "input", "safety": "requires_confirmation", "action": "business_profile_update"},
                {"label": "Province/State", "kind": "input", "safety": "requires_confirmation", "action": "business_profile_update"},
                {"label": "Time Zone", "kind": "input", "safety": "requires_confirmation", "action": "business_profile_update"},
                {"label": "Business Currency", "kind": "report", "safety": "read_only", "action": "payroll_currency_read"},
                {"label": "Save", "kind": "button", "safety": "requires_confirmation", "action": "business_profile_update"},
                {"label": "Archive This Business", "kind": "button", "safety": "requires_confirmation", "action": "business_archive"},
            ],
            "review_gate": "Business identity, default-business, and archive changes require explicit admin approval.",
        },
        "perks_page": {
            "surface": "perks",
            "module": "integrations",
            "automation_mode": "observe",
            "controls": [
                {"label": "Go to previous slide", "kind": "button", "safety": "read_only"},
                {"label": "Go to next slide", "kind": "button", "safety": "read_only"},
                {"label": "Get started", "kind": "external", "safety": "requires_confirmation", "action": "perk_external_open"},
                {"label": "Learn more", "kind": "external", "safety": "read_only", "action": "perks_open"},
            ],
            "review_gate": "External partner pages require explicit user intent before opening.",
        },
    },
    "account_families": {
        "asset": ["Cash and Bank", "Accounts Receivable", "Payment Clearing"],
        "liability": ["Accounts Payable", "Credit Card", "Sales Tax / VAT Payable", "Loans"],
        "equity": ["Owner Investment", "Owner Drawings", "Retained Earnings"],
        "income": ["Sales", "Services", "Discounts"],
        "expense": ["Office Supplies", "Software", "Meals", "Travel", "Professional Fees", "Bank Fees"],
    },
    "document_routing": {
        "receipt": {"target": "transactions", "fallback": "bills"},
        "card_receipt": {"target": "transactions", "fallback": "bills"},
        "bank_transaction": {"target": "transactions", "fallback": "bills"},
        "credit_note": {"target": "transactions", "fallback": "bills"},
        "vendor_invoice": {"target": "bills", "fallback": "transactions"},
        "bill": {"target": "bills", "fallback": "transactions"},
        "unpaid_purchase": {"target": "bills", "fallback": "transactions"},
        "sales_invoice": {"target": "invoices", "fallback": "transactions"},
        "estimate": {"target": "estimates", "fallback": "invoices"},
        "quote": {"target": "estimates", "fallback": "invoices"},
    },
    "actions": {
        "dashboard_account_prompt_acknowledge": {
            "surface": "dashboard",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["promptId"],
        },
        "dashboard_widget_filter": {"surface": "dashboard", "mode": "read", "safety": "read_only", "required": []},
        "dashboard_widget_report_open": {
            "surface": "reports",
            "mode": "read",
            "safety": "read_only",
            "required": ["widgetId"],
        },
        "dashboard_customize": {
            "surface": "dashboard",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["layoutPreset"],
        },
        "estimate_create": {
            "surface": "estimates",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["customer", "lineItems"],
        },
        "estimate_filter": {"surface": "estimates", "mode": "read", "safety": "read_only", "required": []},
        "estimate_customer_filter": {
            "surface": "estimates",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "estimate_status_filter": {
            "surface": "estimates",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "estimate_date_filter": {
            "surface": "estimates",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "estimate_date_picker_open": {
            "surface": "estimates",
            "mode": "read",
            "safety": "read_only",
            "required": ["rangeSide"],
        },
        "estimate_date_picker_close": {
            "surface": "estimates",
            "mode": "read",
            "safety": "read_only",
            "required": ["rangeSide"],
        },
        "estimate_number_search": {
            "surface": "estimates",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "estimate_clear_filters": {
            "surface": "estimates",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "estimate_tab_view": {
            "surface": "estimates",
            "mode": "read",
            "safety": "read_only",
            "required": ["tab"],
        },
        "estimate_update": {
            "surface": "estimates",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["estimateId", "changes"],
        },
        "estimate_send": {
            "surface": "estimates",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["estimateId", "recipientEmail"],
        },
        "estimate_download_pdf": {
            "surface": "estimates",
            "mode": "export",
            "safety": "read_only",
            "required": ["estimateId"],
        },
        "estimate_pdf_dialog_close": {
            "surface": "estimates",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "estimate_duplicate": {
            "surface": "estimates",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["estimateId"],
        },
        "estimate_convert_to_invoice": {
            "surface": "estimates",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["estimateId"],
        },
        "estimate_delete": {
            "surface": "estimates",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["estimateId"],
        },
        "invoice_create": {
            "surface": "invoices",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["customer", "lineItems"],
        },
        "invoice_send": {
            "surface": "invoices",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["invoiceId", "recipientEmail"],
        },
        "invoice_update": {
            "surface": "invoices",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["invoiceId", "changes"],
        },
        "invoice_approve": {
            "surface": "invoices",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["invoiceId"],
        },
        "invoice_send_reminder": {
            "surface": "invoices",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["invoiceId", "recipientEmail"],
        },
        "invoice_record_payment": {
            "surface": "invoices",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["invoiceId", "amount", "paymentDate", "account"],
        },
        "invoice_download_pdf": {
            "surface": "invoices",
            "mode": "export",
            "safety": "read_only",
            "required": ["invoiceId"],
        },
        "invoice_filter": {"surface": "invoices", "mode": "read", "safety": "read_only", "required": []},
        "invoice_summary_metrics_read": {
            "surface": "invoices",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "invoice_summary_refresh": {
            "surface": "invoices",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "invoice_customer_filter": {
            "surface": "invoices",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "invoice_status_filter": {
            "surface": "invoices",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "invoice_date_filter": {
            "surface": "invoices",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "invoice_date_picker_open": {
            "surface": "invoices",
            "mode": "read",
            "safety": "read_only",
            "required": ["rangeSide"],
        },
        "invoice_date_picker_close": {
            "surface": "invoices",
            "mode": "read",
            "safety": "read_only",
            "required": ["rangeSide"],
        },
        "invoice_number_search": {
            "surface": "invoices",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "invoice_clear_filters": {
            "surface": "invoices",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "invoice_tab_view": {
            "surface": "invoices",
            "mode": "read",
            "safety": "read_only",
            "required": ["tab"],
        },
        "invoice_view_all": {
            "surface": "invoices",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "invoice_duplicate": {
            "surface": "invoices",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["invoiceId"],
        },
        "invoice_delete": {
            "surface": "invoices",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["invoiceId"],
        },
        "recurring_invoice_create": {
            "surface": "recurring_invoices",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["customer", "lineItems", "schedule"],
        },
        "recurring_invoice_filter": {
            "surface": "recurring_invoices",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "recurring_invoice_customer_filter": {
            "surface": "recurring_invoices",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "recurring_invoice_tab_view": {
            "surface": "recurring_invoices",
            "mode": "read",
            "safety": "read_only",
            "required": ["tab"],
        },
        "recurring_invoice_table_read": {
            "surface": "recurring_invoices",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "recurring_invoice_view_drafts": {
            "surface": "recurring_invoices",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "recurring_invoice_update": {
            "surface": "recurring_invoices",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["recurringInvoiceId", "changes"],
        },
        "recurring_invoice_activate": {
            "surface": "recurring_invoices",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["recurringInvoiceId"],
        },
        "recurring_invoice_pause": {
            "surface": "recurring_invoices",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["recurringInvoiceId"],
        },
        "recurring_invoice_delete": {
            "surface": "recurring_invoices",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["recurringInvoiceId"],
        },
        "customer_statement_help_open": {
            "surface": "customer_statements",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "customer_statement_customer_select": {
            "surface": "customer_statements",
            "mode": "read",
            "safety": "read_only",
            "required": ["customer"],
        },
        "customer_statement_type_select": {
            "surface": "customer_statements",
            "mode": "read",
            "safety": "read_only",
            "required": ["statementType"],
        },
        "customer_statement_create": {
            "surface": "customer_statements",
            "mode": "export",
            "safety": "read_only",
            "required": ["customer", "statementType"],
        },
        "customer_statement_export": {
            "surface": "customer_statements",
            "mode": "export",
            "safety": "read_only",
            "required": ["statementId", "format"],
        },
        "customer_statement_send": {
            "surface": "customer_statements",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["statementId", "recipientEmail"],
        },
        "customer_list_read": {"surface": "customers", "mode": "read", "safety": "read_only", "required": []},
        "customer_row_actions_open": {
            "surface": "customers",
            "mode": "read",
            "safety": "read_only",
            "required": ["customerId"],
        },
        "customer_view": {
            "surface": "customers",
            "mode": "read",
            "safety": "read_only",
            "required": ["customerId"],
        },
        "customer_create": {"surface": "customers", "mode": "write", "safety": "safe_draft", "required": ["name"]},
        "customer_form_fill": {"surface": "customers", "mode": "write", "safety": "safe_draft", "required": ["name"]},
        "customer_add_phone": {
            "surface": "customers",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["customerDraftId"],
        },
        "customer_add_contact": {
            "surface": "customers",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["customerDraftId"],
        },
        "customer_clear_address": {
            "surface": "customers",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["addressType"],
        },
        "customer_cancel_form": {"surface": "customers", "mode": "read", "safety": "read_only", "required": []},
        "customer_update": {
            "surface": "customers",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["customerId"],
        },
        "customer_create_invoice": {
            "surface": "customers",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["customerId"],
        },
        "customer_delete": {
            "surface": "customers",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["customerId"],
        },
        "customer_search": {"surface": "customers", "mode": "read", "safety": "read_only", "required": []},
        "customer_import_csv_choose_file": {
            "surface": "customers",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["csvPath"],
        },
        "customer_import_csv_preview": {
            "surface": "customers",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["csvPath"],
        },
        "customer_import_csv_instructions": {
            "surface": "customers",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "customer_import_csv_template_download": {
            "surface": "customers",
            "mode": "export",
            "safety": "read_only",
            "required": [],
        },
        "customer_import_csv": {
            "surface": "customers",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["csvPath"],
        },
        "product_service_list_read": {
            "surface": "selling_products_services",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "product_service_form_read": {
            "surface": "selling_products_services",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "product_service_form_fill": {
            "surface": "selling_products_services",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["name"],
        },
        "product_service_sell_toggle": {
            "surface": "selling_products_services",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["sellThis"],
        },
        "product_service_buy_toggle": {
            "surface": "selling_products_services",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["buyThis"],
        },
        "product_service_income_account_select": {
            "surface": "selling_products_services",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["incomeAccount"],
        },
        "product_service_expense_account_select": {
            "surface": "selling_products_services",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["expenseAccount"],
        },
        "product_service_tax_select": {
            "surface": "selling_products_services",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["taxId"],
        },
        "selling_product_service_upsert": {
            "surface": "selling_products_services",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["name"],
        },
        "bill_workspace_read": {"surface": "bills", "mode": "read", "safety": "read_only", "required": []},
        "bill_form_read": {"surface": "bills", "mode": "read", "safety": "read_only", "required": []},
        "bill_form_fill": {
            "surface": "bills",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["vendor", "billDate"],
        },
        "bill_line_item_fill": {
            "surface": "bills",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["expenseCategory", "description", "quantity", "price"],
        },
        "bill_line_item_delete": {
            "surface": "bills",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["lineItemIndex"],
        },
        "bill_cancel_form": {"surface": "bills", "mode": "read", "safety": "read_only", "required": []},
        "bill_create": {
            "surface": "bills",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["vendor", "billDate", "lineItems"],
        },
        "bill_update": {
            "surface": "bills",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["billId", "changes"],
        },
        "bill_attach_receipt": {
            "surface": "bills",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["billId", "attachmentPath"],
        },
        "bill_mark_paid": {
            "surface": "bills",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["billId", "paymentDate", "account", "amount"],
        },
        "bill_filter": {"surface": "bills", "mode": "read", "safety": "read_only", "required": []},
        "bill_delete": {
            "surface": "bills",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["billId"],
        },
        "vendor_list_read": {"surface": "vendors", "mode": "read", "safety": "read_only", "required": []},
        "vendor_form_read": {"surface": "vendors", "mode": "read", "safety": "read_only", "required": []},
        "vendor_form_fill": {
            "surface": "vendors",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["name"],
        },
        "vendor_import_menu_open": {"surface": "vendors", "mode": "read", "safety": "read_only", "required": []},
        "vendor_create": {"surface": "vendors", "mode": "write", "safety": "safe_draft", "required": ["name"]},
        "vendor_create_bill": {
            "surface": "vendors",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["vendorId"],
        },
        "vendor_update": {
            "surface": "vendors",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["vendorId"],
        },
        "vendor_import_csv": {
            "surface": "vendors",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["csvPath"],
        },
        "vendor_import_google_contacts": {
            "surface": "vendors",
            "mode": "connect",
            "safety": "requires_confirmation",
            "required": ["googleAccount"],
        },
        "vendor_delete": {
            "surface": "vendors",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["vendorId"],
        },
        "buying_product_service_list_read": {
            "surface": "buying_products_services",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "buying_product_service_form_read": {
            "surface": "buying_products_services",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "buying_product_service_default_state_read": {
            "surface": "buying_products_services",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "buying_product_service_form_fill": {
            "surface": "buying_products_services",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["name"],
        },
        "buying_product_service_sell_toggle": {
            "surface": "buying_products_services",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["sellThis"],
        },
        "buying_product_service_buy_toggle": {
            "surface": "buying_products_services",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["buyThis"],
        },
        "buying_product_service_income_account_select": {
            "surface": "buying_products_services",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["incomeAccount"],
        },
        "buying_product_service_expense_account_select": {
            "surface": "buying_products_services",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["expenseAccount"],
        },
        "buying_product_service_account_create": {
            "surface": "buying_products_services",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["accountName", "accountType"],
        },
        "buying_product_service_tax_select": {
            "surface": "buying_products_services",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["taxId"],
        },
        "buying_product_service_upsert": {
            "surface": "buying_products_services",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["name"],
        },
        "buying_product_service_update": {
            "surface": "buying_products_services",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["productServiceId"],
        },
        "buying_product_service_delete": {
            "surface": "buying_products_services",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["productServiceId"],
        },
        "product_service_update": {
            "surface": "selling_products_services",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["productServiceId"],
        },
        "product_service_delete": {
            "surface": "selling_products_services",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["productServiceId"],
        },
        "transaction_add": {
            "surface": "transactions",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["date", "amount", "account", "category"],
        },
        "transaction_workspace_read": {"surface": "transactions", "mode": "read", "safety": "read_only", "required": []},
        "transaction_more_menu_open": {"surface": "transactions", "mode": "read", "safety": "read_only", "required": []},
        "transaction_account_filter_select": {
            "surface": "transactions",
            "mode": "read",
            "safety": "read_only",
            "required": ["account"],
        },
        "transaction_account_upload_statement": {
            "surface": "transactions",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["account"],
        },
        "transaction_account_create": {
            "surface": "transactions",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["accountName", "accountType"],
        },
        "transaction_add_deposit": {
            "surface": "transactions",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["date", "amount", "account", "category"],
        },
        "transaction_add_withdrawal": {
            "surface": "transactions",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["date", "amount", "account", "category"],
        },
        "transaction_add_journal_entry": {
            "surface": "transactions",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["date", "lines"],
        },
        "transaction_form_fill": {
            "surface": "transactions",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["date", "description", "amount"],
        },
        "transaction_date_picker_open": {
            "surface": "transactions",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["date"],
        },
        "transaction_account_select": {
            "surface": "transactions",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["account"],
        },
        "transaction_type_select": {
            "surface": "transactions",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["type"],
        },
        "transaction_category_select": {
            "surface": "transactions",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["category"],
        },
        "transaction_sales_tax_toggle": {
            "surface": "transactions",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["includeSalesTax"],
        },
        "transaction_customer_select": {
            "surface": "transactions",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["customer"],
        },
        "transaction_vendor_select": {
            "surface": "transactions",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["vendor"],
        },
        "transaction_note_fill": {
            "surface": "transactions",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["note"],
        },
        "transaction_cancel_form": {"surface": "transactions", "mode": "read", "safety": "read_only", "required": []},
        "transaction_row_read": {"surface": "transactions", "mode": "read", "safety": "read_only", "required": []},
        "transaction_sort": {"surface": "transactions", "mode": "read", "safety": "read_only", "required": []},
        "transaction_sort_newest_to_oldest": {"surface": "transactions", "mode": "read", "safety": "read_only", "required": []},
        "transaction_sort_oldest_to_newest": {"surface": "transactions", "mode": "read", "safety": "read_only", "required": []},
        "transaction_search": {"surface": "transactions", "mode": "read", "safety": "read_only", "required": ["query"]},
        "transaction_search_submit": {"surface": "transactions", "mode": "read", "safety": "read_only", "required": ["query"]},
        "transaction_bulk_select": {
            "surface": "transactions",
            "mode": "read",
            "safety": "read_only",
            "required": ["transactionIds"],
        },
        "transaction_load_more": {"surface": "transactions", "mode": "read", "safety": "read_only", "required": []},
        "transaction_reconciliation_toggle_read": {
            "surface": "transactions",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "transaction_reconciliation_notice_read": {
            "surface": "transactions",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "transaction_notice_close": {"surface": "transactions", "mode": "read", "safety": "read_only", "required": []},
        "transaction_filter": {"surface": "transactions", "mode": "read", "safety": "read_only", "required": []},
        "transaction_update": {
            "surface": "transactions",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["transactionId", "changes"],
        },
        "transaction_categorize": {
            "surface": "transactions",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["transactionId", "category"],
        },
        "transaction_split": {
            "surface": "transactions",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["transactionId", "splits"],
        },
        "transaction_attach_receipt": {
            "surface": "transactions",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["transactionId", "attachmentPath"],
        },
        "transaction_mark_reviewed": {
            "surface": "transactions",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["transactionId"],
        },
        "transaction_reconcile": {
            "surface": "transactions",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["transactionId", "statementId"],
        },
        "transaction_merge": {
            "surface": "transactions",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["transactionIds"],
        },
        "transaction_delete": {
            "surface": "transactions",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["transactionId"],
        },
        "statement_upload": {
            "surface": "transactions",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["filePath", "account"],
        },
        "statement_upload_instructions_read": {
            "surface": "transactions",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "statement_file_choose": {
            "surface": "transactions",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["filePath"],
        },
        "statement_payment_account_select": {
            "surface": "transactions",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["account"],
        },
        "statement_account_create": {
            "surface": "transactions",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["accountName", "accountType"],
        },
        "statement_upload_help_open": {
            "surface": "transactions",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "statement_csv_template_download": {
            "surface": "transactions",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "chart_account_list_read": {
            "surface": "chart_of_accounts",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "chart_account_help_open": {
            "surface": "chart_of_accounts",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "chart_account_tab_view": {
            "surface": "chart_of_accounts",
            "mode": "read",
            "safety": "read_only",
            "required": ["tab"],
        },
        "chart_account_section_read": {
            "surface": "chart_of_accounts",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "chart_account_activity_read": {
            "surface": "chart_of_accounts",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "chart_account_form_read": {
            "surface": "chart_of_accounts",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "chart_account_type_picker_open": {
            "surface": "chart_of_accounts",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "chart_account_type_search": {
            "surface": "chart_of_accounts",
            "mode": "read",
            "safety": "read_only",
            "required": ["query"],
        },
        "chart_account_type_select": {
            "surface": "chart_of_accounts",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["type"],
        },
        "chart_account_currency_select": {
            "surface": "chart_of_accounts",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["currency"],
        },
        "chart_account_form_fill": {
            "surface": "chart_of_accounts",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["name", "type"],
        },
        "chart_account_cancel_form": {
            "surface": "chart_of_accounts",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "chart_account_create": {
            "surface": "chart_of_accounts",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["name", "type"],
        },
        "chart_account_update": {
            "surface": "chart_of_accounts",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["accountId", "changes"],
        },
        "chart_account_archive": {
            "surface": "chart_of_accounts",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["accountId"],
        },
        "chart_account_map": {
            "surface": "chart_of_accounts",
            "mode": "write",
            "safety": "safe_draft",
            "required": ["fabCategory", "waveAccount"],
        },
        "connected_account_connect": {
            "surface": "connected_accounts",
            "mode": "connect",
            "safety": "requires_confirmation",
            "required": ["institution"],
        },
        "connected_account_unavailable_read": {
            "surface": "connected_accounts",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "connected_account_manual_entry_plan": {
            "surface": "connected_accounts",
            "mode": "write",
            "safety": "safe_draft",
            "required": [],
        },
        "connected_account_statement_help_open": {
            "surface": "connected_accounts",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "connected_account_statement_format_read": {
            "surface": "connected_accounts",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "connected_account_statement_upload_steps_read": {
            "surface": "connected_accounts",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "connected_account_statement_mapping_confirm": {
            "surface": "connected_accounts",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["mappingType"],
        },
        "connected_account_statement_upload_complete": {
            "surface": "connected_accounts",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["filePath", "paymentAccount", "mapping"],
        },
        "connected_account_csv_help_open": {
            "surface": "connected_accounts",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "connected_account_payment_account_help_open": {
            "surface": "connected_accounts",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "connected_account_wave_connect_help_open": {
            "surface": "connected_accounts",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "connected_account_auto_updates_help_open": {
            "surface": "connected_accounts",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "connected_account_support_open": {
            "surface": "connected_accounts",
            "mode": "connect",
            "safety": "requires_confirmation",
            "required": [],
        },
        "connected_account_help_feedback": {
            "surface": "connected_accounts",
            "mode": "write",
            "safety": "requires_confirmation",
            "required": ["feedback"],
        },
        "connected_account_help_share": {
            "surface": "connected_accounts",
            "mode": "connect",
            "safety": "requires_confirmation",
            "required": ["network"],
        },
        "connected_account_refresh": {
            "surface": "connected_accounts",
            "mode": "connect",
            "safety": "requires_credentials",
            "required": ["connectedAccountId"],
        },
        "report_open": {"surface": "reports", "mode": "read", "safety": "read_only", "required": ["reportType"]},
        "report_catalog_section_read": {
            "surface": "reports",
            "mode": "read",
            "safety": "read_only",
            "required": ["section"],
        },
        "report_filter": {
            "surface": "reports",
            "mode": "read",
            "safety": "read_only",
            "required": ["reportType"],
        },
        "report_date_range_set": {
            "surface": "reports",
            "mode": "read",
            "safety": "read_only",
            "required": ["reportType", "fromDate", "toDate"],
        },
        "report_as_of_date_set": {
            "surface": "reports",
            "mode": "read",
            "safety": "read_only",
            "required": ["reportType", "asOfDate"],
        },
        "report_date_picker_open": {
            "surface": "reports",
            "mode": "read",
            "safety": "read_only",
            "required": ["reportType", "field"],
        },
        "report_basis_select": {
            "surface": "reports",
            "mode": "read",
            "safety": "read_only",
            "required": ["reportType", "basis"],
        },
        "report_account_filter_select": {
            "surface": "reports",
            "mode": "read",
            "safety": "read_only",
            "required": ["reportType", "accountOption"],
        },
        "report_contact_filter_select": {
            "surface": "reports",
            "mode": "read",
            "safety": "read_only",
            "required": ["reportType", "contactOption"],
        },
        "report_type_help_read": {
            "surface": "reports",
            "mode": "read",
            "safety": "read_only",
            "required": ["reportType"],
        },
        "report_update": {
            "surface": "reports",
            "mode": "read",
            "safety": "read_only",
            "required": ["reportType"],
        },
        "report_view_toggle": {
            "surface": "reports",
            "mode": "read",
            "safety": "read_only",
            "required": ["reportType", "view"],
        },
        "report_table_read": {
            "surface": "reports",
            "mode": "read",
            "safety": "read_only",
            "required": ["reportType"],
        },
        "report_empty_state_read": {
            "surface": "reports",
            "mode": "read",
            "safety": "read_only",
            "required": ["reportType"],
        },
        "report_export_menu_open": {
            "surface": "reports",
            "mode": "export",
            "safety": "read_only",
            "required": ["reportType"],
        },
        "report_export": {
            "surface": "reports",
            "mode": "export",
            "safety": "read_only",
            "required": ["reportType", "format"],
        },
        "report_drilldown": {
            "surface": "reports",
            "mode": "read",
            "safety": "read_only",
            "required": ["reportType", "lineItem"],
        },
        "business_user_invite": {
            "surface": "business_settings",
            "mode": "admin",
            "safety": "requires_confirmation",
            "required": ["email", "role"],
        },
        "business_user_delete": {
            "surface": "business_settings",
            "mode": "admin",
            "safety": "requires_confirmation",
            "required": ["userId"],
        },
        "business_user_role_update": {
            "surface": "business_settings",
            "mode": "admin",
            "safety": "requires_confirmation",
            "required": ["userId", "role"],
        },
        "business_invoice_estimate_settings_update": {
            "surface": "business_settings",
            "mode": "admin",
            "safety": "requires_confirmation",
            "required": ["settingChanges"],
        },
        "financial_settings_update": {
            "surface": "financial_settings",
            "mode": "admin",
            "safety": "requires_confirmation",
            "required": ["settingChanges"],
        },
        "sales_tax_create": {
            "surface": "sales_tax_settings",
            "mode": "admin",
            "safety": "requires_confirmation",
            "required": ["name", "rate"],
        },
        "sales_tax_update": {
            "surface": "sales_tax_settings",
            "mode": "admin",
            "safety": "requires_confirmation",
            "required": ["taxId", "changes"],
        },
        "sales_tax_delete": {
            "surface": "sales_tax_settings",
            "mode": "admin",
            "safety": "requires_confirmation",
            "required": ["taxId"],
        },
        "subscription_status_read": {
            "surface": "subscription_management",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "payroll_billing_open": {
            "surface": "subscription_management",
            "mode": "admin",
            "safety": "requires_confirmation",
            "required": [],
        },
        "wave_advisors_portal_open": {
            "surface": "subscription_management",
            "mode": "admin",
            "safety": "requires_confirmation",
            "required": [],
        },
        "data_export_start": {
            "surface": "data_export",
            "mode": "export",
            "safety": "requires_confirmation",
            "required": ["exportScope"],
        },
        "business_switch": {
            "surface": "business_settings",
            "mode": "admin",
            "safety": "requires_confirmation",
            "required": ["businessId"],
        },
        "profile_settings_update": {
            "surface": "business_settings",
            "mode": "admin",
            "safety": "requires_confirmation",
            "required": ["profileChanges"],
        },
        "feedback_send": {
            "surface": "business_settings",
            "mode": "admin",
            "safety": "requires_confirmation",
            "required": ["message"],
        },
        "sign_out": {
            "surface": "business_settings",
            "mode": "admin",
            "safety": "unsupported",
            "required": [],
        },
        "back_to_wave": {
            "surface": "business_settings",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "wave_help_open": {
            "surface": "business_settings",
            "mode": "read",
            "safety": "read_only",
            "required": ["article"],
        },
        "business_list_read": {
            "surface": "business_settings",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "business_profile_read": {
            "surface": "business_settings",
            "mode": "read",
            "safety": "read_only",
            "required": ["businessId"],
        },
        "business_profile_update": {
            "surface": "business_settings",
            "mode": "admin",
            "safety": "requires_confirmation",
            "required": ["businessId", "profileChanges"],
        },
        "business_create": {
            "surface": "business_settings",
            "mode": "admin",
            "safety": "requires_confirmation",
            "required": ["businessName", "country", "currency"],
        },
        "business_set_default": {
            "surface": "business_settings",
            "mode": "admin",
            "safety": "requires_confirmation",
            "required": ["businessId"],
        },
        "business_archive": {
            "surface": "business_settings",
            "mode": "admin",
            "safety": "requires_confirmation",
            "required": ["businessId"],
        },
        "integration_connect": {
            "surface": "integrations",
            "mode": "connect",
            "safety": "requires_confirmation",
            "required": ["provider"],
        },
        "google_sheets_add": {
            "surface": "integrations",
            "mode": "connect",
            "safety": "requires_confirmation",
            "required": ["googleAccount"],
        },
        "make_workflow_use": {
            "surface": "integrations",
            "mode": "connect",
            "safety": "requires_confirmation",
            "required": ["workflowTemplate"],
        },
        "subscription_upgrade": {
            "surface": "integrations",
            "mode": "admin",
            "safety": "requires_confirmation",
            "required": ["plan"],
        },
        "zoho_offer_open": {
            "surface": "zoho_migration_offer",
            "mode": "connect",
            "safety": "requires_confirmation",
            "required": ["offerUrl"],
        },
        "wave_payments_get_started": {
            "surface": "wave_payments",
            "mode": "connect",
            "safety": "requires_confirmation",
            "required": ["businessId"],
        },
        "wave_terms_open": {
            "surface": "wave_payments",
            "mode": "read",
            "safety": "read_only",
            "required": ["termsType"],
        },
        "wave_support_contact": {
            "surface": "wave_payments",
            "mode": "connect",
            "safety": "requires_confirmation",
            "required": ["topic"],
        },
        "wave_advisors_consultation_open": {
            "surface": "wave_payments",
            "mode": "connect",
            "safety": "requires_confirmation",
            "required": ["consultationUrl"],
        },
        "business_checking_open": {
            "surface": "business_checking",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "business_checking_open_account": {
            "surface": "business_checking",
            "mode": "connect",
            "safety": "requires_confirmation",
            "required": ["provider"],
        },
        "business_checking_terms_open": {
            "surface": "business_checking",
            "mode": "read",
            "safety": "read_only",
            "required": ["termsUrl"],
        },
        "business_checking_offer_read": {
            "surface": "business_checking",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "business_checking_feature_read": {
            "surface": "business_checking",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "business_checking_claim_steps_read": {
            "surface": "business_checking",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "business_checking_promo_terms_read": {
            "surface": "business_checking",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "payroll_open": {
            "surface": "payroll",
            "mode": "read",
            "safety": "unsupported",
            "required": [],
        },
        "payroll_availability_read": {
            "surface": "payroll",
            "mode": "read",
            "safety": "read_only",
            "required": ["businessId"],
        },
        "payroll_eligibility_rules_read": {
            "surface": "payroll",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "payroll_business_settings_open": {
            "surface": "business_settings",
            "mode": "read",
            "safety": "read_only",
            "required": ["businessId"],
        },
        "payroll_currency_read": {
            "surface": "business_settings",
            "mode": "read",
            "safety": "read_only",
            "required": ["businessId"],
        },
        "payroll_adjust_business_settings": {
            "surface": "business_settings",
            "mode": "admin",
            "safety": "requires_confirmation",
            "required": ["businessSettingChanges"],
        },
        "perks_open": {
            "surface": "integrations",
            "mode": "read",
            "safety": "read_only",
            "required": [],
        },
        "perk_external_open": {
            "surface": "integrations",
            "mode": "connect",
            "safety": "requires_confirmation",
            "required": ["partner"],
        },
    },
}


def normalize_wave_document_type(value: Any) -> str:
    if not value:
        return "receipt"
    normalized = str(value).strip().lower().replace(" ", "_").replace("-", "_")
    if normalized in {"invoice", "purchase_invoice"}:
        return "vendor_invoice"
    return normalized


def classify_wave_destination(data: Dict[str, Any]) -> Dict[str, str]:
    document_type = normalize_wave_document_type(
        data.get("document_type")
        or data.get("type")
        or data.get("extracted_data", {}).get("document_type")
        or data.get("extracted_data", {}).get("type")
    )
    route = WAVE_SURFACE_CATALOG["document_routing"].get(
        document_type,
        WAVE_SURFACE_CATALOG["document_routing"]["receipt"],
    )
    return {
        "document_type": document_type,
        "target_surface": route["target"],
        "fallback_surface": route["fallback"],
    }


def resolve_wave_action_for_document(data: Dict[str, Any]) -> str:
    destination = classify_wave_destination(data)
    surface = destination["target_surface"]
    if surface == "bills":
        return "bill_create"
    if surface == "invoices":
        return "invoice_create"
    if surface == "estimates":
        return "estimate_create"
    return "transaction_add"


def build_wave_action_payload(
    data: Dict[str, Any],
    wave_category: str,
    default_account: str = "Uncategorized",
) -> Dict[str, Any]:
    extracted = data.get("extracted_data", {})
    vendor = extracted.get("vendor_name") or data.get("vendor_name") or ""
    date = extracted.get("transaction_date") or extracted.get("date") or ""
    raw_amount = (
        extracted.get("total_amount")
        if extracted.get("total_amount") not in (None, "")
        else extracted.get("amount")
        if extracted.get("amount") not in (None, "")
        else data.get("total_amount")
    )
    destination = classify_wave_destination(data)
    document_type = destination["document_type"]
    amount = _wave_posting_amount(raw_amount, document_type)
    description = extracted.get("description") or data.get("description") or ""
    action_id = resolve_wave_action_for_document(data)
    line_items = _normalize_wave_line_items(
        data.get("line_items") or extracted.get("line_items") or extracted.get("lineItems") or [],
        fallback_description=description or vendor or "Imported document",
        fallback_amount=amount,
        fallback_category=wave_category,
        default_account=default_account,
    )

    if action_id == "bill_create":
        return {
            "vendor": vendor,
            "billDate": date,
            "lineItems": line_items,
        }
    if action_id == "invoice_create":
        return {
            "customer": extracted.get("customer_name") or data.get("customer_name") or vendor,
            "lineItems": line_items,
        }
    if action_id == "estimate_create":
        return {
            "customer": extracted.get("customer_name") or data.get("customer_name") or vendor,
            "lineItems": line_items,
        }
    first_line = line_items[0] if line_items else {}
    return {
        "date": date,
        "amount": amount,
        "documentType": document_type,
        "transactionDirection": "deposit" if document_type == "credit_note" else "withdrawal",
        "account": first_line.get("account") or default_account,
        "category": first_line.get("category") or wave_category,
        "description": description,
        "vendor": vendor,
        "lineItems": line_items,
    }


def _normalize_wave_line_items(
    raw_items: Any,
    fallback_description: str,
    fallback_amount: Any,
    fallback_category: str,
    default_account: str,
) -> List[Dict[str, Any]]:
    if not isinstance(raw_items, list):
        raw_items = []
    line_items: List[Dict[str, Any]] = []
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        amount = _wave_number(
            raw_item.get("amount")
            if raw_item.get("amount") not in (None, "")
            else raw_item.get("total")
            if raw_item.get("total") not in (None, "")
            else raw_item.get("total_amount")
            if raw_item.get("total_amount") not in (None, "")
            else raw_item.get("totalAmount")
        )
        if amount is None:
            continue
        item = {
            "description": raw_item.get("description") or raw_item.get("item_name") or raw_item.get("itemName") or fallback_description,
            "amount": amount,
            "category": raw_item.get("category") or fallback_category,
            "account": (
                raw_item.get("account")
                or raw_item.get("account_name")
                or raw_item.get("accountName")
                or default_account
            ),
        }
        if raw_item.get("quantity") not in (None, ""):
            item["quantity"] = raw_item.get("quantity")
        if raw_item.get("unit_price") not in (None, ""):
            item["unitPrice"] = raw_item.get("unit_price")
        if raw_item.get("unitPrice") not in (None, ""):
            item["unitPrice"] = raw_item.get("unitPrice")
        tax_code = raw_item.get("tax_code") or raw_item.get("taxCode") or raw_item.get("tax")
        if tax_code not in (None, ""):
            item["tax"] = tax_code
        tax_amount = raw_item.get("tax_amount") if raw_item.get("tax_amount") not in (None, "") else raw_item.get("taxAmount")
        if tax_amount not in (None, ""):
            item["taxAmount"] = tax_amount
        line_items.append(item)
    document_total = _wave_number(fallback_amount)
    line_total = round(sum(float(item["amount"]) for item in line_items), 2)
    tolerance = max(0.02, abs(document_total or 0.0) * 0.01)
    if line_items:
        if document_total is None or abs(line_total - document_total) <= tolerance:
            return line_items
        if abs(abs(line_total) - abs(document_total)) <= tolerance:
            direction = -1.0 if document_total < 0 else 1.0
            return [
                {
                    **item,
                    "amount": round(abs(float(item["amount"])) * direction, 2),
                }
                for item in line_items
            ]
    return [{
        "description": fallback_description,
        "amount": document_total if document_total is not None else fallback_amount,
        "category": fallback_category,
        "account": default_account,
    }]


def _wave_number(value: Any) -> Optional[float]:
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        return float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None


def _wave_posting_amount(value: Any, document_type: str) -> Any:
    amount = _wave_number(value)
    if amount is None:
        return value if value not in (None, "") else 0.0
    if document_type == "credit_note":
        return -abs(amount)
    return amount


def build_wave_expense_import_row(
    data: Dict[str, Any],
    wave_category: str,
    description_suffix: str = "",
) -> Dict[str, Any]:
    extracted = data.get("extracted_data", {})
    description = extracted.get("description") or data.get("description") or "Automated Expense"
    if description_suffix:
        description = f"{description} {description_suffix}".strip()

    destination = classify_wave_destination(data)
    raw_amount = (
        extracted.get("total_amount")
        if extracted.get("total_amount") not in (None, "")
        else extracted.get("amount")
    )
    return {
        "Date": extracted.get("transaction_date") or extracted.get("date") or "",
        "Amount": _wave_posting_amount(raw_amount, destination["document_type"]),
        "Description": description,
        "Category": wave_category,
        "Vendor": extracted.get("vendor_name") or data.get("vendor_name") or "",
        "Wave Surface": destination["target_surface"],
        "Wave Action": resolve_wave_action_for_document(data),
        "Wave Fallback": destination["fallback_surface"],
    }


def list_wave_report_sections() -> List[Dict[str, Any]]:
    return [
        {
            "id": section_id,
            "label": section["label"],
            "description": section["description"],
            "report_count": len(section["reports"]),
        }
        for section_id, section in WAVE_SURFACE_CATALOG["report_catalog"].items()
    ]


def list_wave_reports(section: Optional[str] = None) -> List[Dict[str, Any]]:
    reports: List[Dict[str, Any]] = []
    for section_id, section_data in WAVE_SURFACE_CATALOG["report_catalog"].items():
        if section and section_id != section:
            continue
        for report in section_data["reports"]:
            reports.append({
                "section": section_id,
                "section_label": section_data["label"],
                **report,
            })
    return reports


def get_wave_report(report_type: str) -> Optional[Dict[str, Any]]:
    for report in list_wave_reports():
        if report["type"] == report_type:
            return report
    return None


def build_wave_report_payload(
    report_type: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    as_of_date: Optional[str] = None,
    basis: str = "accrual",
    account_option: str = "-1",
    contact_option: str = "0",
    export_format: Optional[str] = None,
) -> Dict[str, Any]:
    report = get_wave_report(report_type) or {
        "type": report_type,
        "date_mode": "date_range",
        "default_export": "csv",
    }
    payload = {
        "reportType": report["type"],
        "basis": basis,
        "accountOption": account_option,
        "contactOption": contact_option,
    }
    if report.get("date_mode") == "as_of":
        payload["asOfDate"] = as_of_date or to_date or from_date or ""
    else:
        payload["fromDate"] = from_date or ""
        payload["toDate"] = to_date or as_of_date or from_date or ""
    if export_format:
        payload["format"] = export_format
    return payload


def list_wave_surfaces() -> List[str]:
    surfaces: List[str] = []
    for module_surfaces in WAVE_SURFACE_CATALOG["modules"].values():
        surfaces.extend(module_surfaces)
    return surfaces


def list_wave_actions(surface: Optional[str] = None) -> List[Dict[str, Any]]:
    actions: List[Dict[str, Any]] = []
    for action_id, action in WAVE_SURFACE_CATALOG["actions"].items():
        if surface and action["surface"] != surface:
            continue
        actions.append({"id": action_id, **action})
    return actions


def plan_wave_action(
    surface: str,
    action_id: str,
    payload: Optional[Dict[str, Any]] = None,
    allow_write: bool = False,
) -> Dict[str, Any]:
    payload = payload or {}
    action = WAVE_SURFACE_CATALOG["actions"].get(action_id)
    if not action or action.get("surface") != surface:
        return {
            "status": "unsupported",
            "surface": surface,
            "action_id": action_id,
            "missing_fields": [],
            "can_run_autonomously": False,
            "requires_confirmation": True,
            "message": "Wave action is not in the FAB action catalog.",
        }

    missing_fields = [field for field in action["required"] if payload.get(field) is None]
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
            f"FAB can plan {action_id} against Wave {surface}."
            if can_run_autonomously
            else f"FAB can prepare {action_id}, but execution requires review or confirmation."
        ),
    }


def summarize_wave_parity() -> Dict[str, Any]:
    surfaces = list_wave_surfaces()
    actions = list_wave_actions()
    reports = list_wave_reports()
    feature_inventory = WAVE_SURFACE_CATALOG["feature_inventory"]
    menu_inventory = WAVE_SURFACE_CATALOG["menu_inventory"]
    controls = [
        control
        for feature in feature_inventory.values()
        for control in feature.get("controls", [])
    ]
    menu_items = [
        item
        for group in menu_inventory.values()
        for item in group.get("items", [])
    ]
    safety_counts: Dict[str, int] = {}
    for action in actions:
        safety = action["safety"]
        safety_counts[safety] = safety_counts.get(safety, 0) + 1
    mode_counts: Dict[str, int] = {}
    for feature in feature_inventory.values():
        mode = feature["automation_mode"]
        mode_counts[mode] = mode_counts.get(mode, 0) + 1
    return {
        "modules": len(WAVE_SURFACE_CATALOG["modules"]),
        "surfaces": len(surfaces),
        "menu_groups": len(menu_inventory),
        "menu_items": len(menu_items),
        "sync_contracts": len(WAVE_SURFACE_CATALOG["sync_contracts"]),
        "feature_pages": len(feature_inventory),
        "observed_controls": len(controls),
        "actions": len(actions),
        "report_sections": len(WAVE_SURFACE_CATALOG["report_catalog"]),
        "reports": len(reports),
        "actions_by_safety": safety_counts,
        "pages_by_automation_mode": mode_counts,
    }
