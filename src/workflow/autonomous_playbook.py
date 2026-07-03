from __future__ import annotations

from typing import Any, Dict, List, Optional, Set


AUTONOMOUS_BOOKKEEPER_PLAYBOOK: Dict[str, Any] = {
    "source": "competitor_research",
    "captured_from": "Booke AI, Outmin, Bookeeping.ai, and LayerNext public product pages reviewed on 2026-06-28",
    "stages": {
        "collect": "Collect bank activity, receipts, invoices, emails, and Drive files.",
        "extract_validate": "Extract multilingual document fields and validate totals, VAT, dates, and vendors.",
        "classify_post": "Classify vendors, categories, taxes, and target Wave surfaces.",
        "match_reconcile": "Match receipts, bills, invoices, and bank transactions.",
        "exception_chase": "Draft requests and reminders for missing evidence or ambiguous context.",
        "close_report": "Run close checks, discrepancy detection, exports, and audit packs.",
        "learn_optimize": "Learn from human corrections and tighten future automation.",
        "system_execute": "Execute approved actions through APIs, browser, or desktop automation.",
    },
    "sources": {
        "booke_ai": ["daily bank feed work", "document matching", "client query tasks", "month-end detection"],
        "outmin": ["continuous reconciliation", "practice control centre", "collect/process/reconcile/close"],
        "bookeeping_ai": ["chat task execution", "health monitoring", "bank statement import", "audit score"],
        "layernext": ["AP automation", "application-layer execution", "approval gates", "custom workflows"],
    },
    "capabilities": {
        "daily_bank_feed_triage": {
            "stage": "collect",
            "autonomy": "prepare",
            "required_signals": ["bank_feed", "account_mapping"],
            "optional_signals": ["prior_reconciliation", "vendor_history"],
            "wave_actions": ["connected_account_refresh", "transaction_categorize"],
            "review_gates": ["provider re-authentication", "new bank account connection"],
        },
        "document_capture_and_ocr": {
            "stage": "extract_validate",
            "autonomy": "safe_draft",
            "required_signals": ["source_document", "ocr_text"],
            "optional_signals": ["line_items", "language", "vat_number"],
            "wave_actions": ["transaction_attach_receipt", "bill_create"],
            "review_gates": ["low OCR confidence", "unbalanced subtotal/tax/total"],
        },
        "vendor_category_learning": {
            "stage": "classify_post",
            "autonomy": "safe_draft",
            "required_signals": ["vendor_identity", "category_candidates"],
            "optional_signals": ["purchase_pattern", "user_rule", "tax_profile"],
            "wave_actions": ["vendor_create", "chart_account_map", "transaction_categorize"],
            "review_gates": ["new chart-of-account creation", "ambiguous vendor match", "first-seen tax treatment"],
        },
        "ap_invoice_workflow": {
            "stage": "classify_post",
            "autonomy": "review_required",
            "required_signals": ["vendor_invoice", "vendor_identity", "line_items"],
            "optional_signals": ["purchase_order", "approval_rule", "due_date"],
            "wave_actions": ["bill_create", "bill_mark_paid"],
            "review_gates": ["payment marking", "approval threshold", "missing PO or contract"],
        },
        "receipt_to_bank_match": {
            "stage": "match_reconcile",
            "autonomy": "safe_draft",
            "required_signals": ["source_document", "bank_transaction", "duplicate_fingerprint"],
            "optional_signals": ["vendor_history", "currency", "card_last_four"],
            "wave_actions": ["transaction_attach_receipt", "transaction_categorize"],
            "review_gates": ["partial amount match", "duplicate candidate", "multi-document order"],
        },
        "ledger_report_reconciliation": {
            "stage": "match_reconcile",
            "autonomy": "prepare",
            "required_signals": ["ledger_period", "account_scope", "reconciliation_status"],
            "optional_signals": ["contact_scope", "cash_mode", "bank_feed", "review_queue"],
            "wave_actions": [
                "report_open",
                "report_account_filter_select",
                "report_contact_filter_select",
                "report_date_range_set",
                "report_basis_select",
                "report_update",
                "report_table_read",
                "report_empty_state_read",
                "report_export",
            ],
            "review_gates": ["empty ledger scope", "unmatched bank activity", "material discrepancy"],
        },
        "missing_document_chase": {
            "stage": "exception_chase",
            "autonomy": "review_required",
            "required_signals": ["bank_transaction", "document_policy"],
            "optional_signals": ["contact_email", "last_request_at", "owner"],
            "wave_actions": [],
            "review_gates": ["external email send", "client-facing message", "sensitive financial details"],
        },
        "anomaly_and_health_monitoring": {
            "stage": "close_report",
            "autonomy": "observe",
            "required_signals": ["ledger_snapshot", "bank_feed"],
            "optional_signals": ["budget", "historical_average", "cash_forecast"],
            "wave_actions": ["report_open"],
            "review_gates": ["advisory recommendation", "tax-sensitive decision"],
        },
        "month_end_close_pack": {
            "stage": "close_report",
            "autonomy": "prepare",
            "required_signals": ["ledger_snapshot", "reconciliation_status"],
            "optional_signals": ["period_lock_date", "vat_working", "review_queue"],
            "wave_actions": ["report_export", "customer_statement_create"],
            "review_gates": ["period lock", "tax filing", "material unresolved exception"],
        },
        "chat_task_orchestrator": {
            "stage": "system_execute",
            "autonomy": "prepare",
            "required_signals": ["user_intent", "policy_context"],
            "optional_signals": ["target_customer", "target_vendor", "amount", "due_date"],
            "wave_actions": ["invoice_create", "estimate_create", "report_open"],
            "review_gates": ["send invoice", "record payment", "create recurring billing"],
        },
        "app_layer_executor": {
            "stage": "system_execute",
            "autonomy": "confirmed_execute",
            "required_signals": ["approved_operation", "idempotency_key", "target_surface"],
            "optional_signals": ["browser_route", "api_endpoint", "rollback_plan"],
            "wave_actions": ["transaction_add", "bill_create", "invoice_create", "report_export"],
            "review_gates": ["credential prompt", "external communication", "payment or account access change"],
        },
    },
    "service_offerings": {
        "booke_qbo_xero_bank_feed_ai": {
            "source": "booke_ai",
            "category": "bookkeeping",
            "status": "partial",
            "required_capabilities": [
                "daily_bank_feed_triage",
                "vendor_category_learning",
                "receipt_to_bank_match",
                "app_layer_executor",
            ],
            "netherlands_adaptation": "Dutch bank feeds, SEPA descriptions, IBAN matching, BTW category mapping, and evidence retention.",
        },
        "booke_document_ocr_matching": {
            "source": "booke_ai",
            "category": "capture",
            "status": "partial",
            "required_capabilities": ["document_capture_and_ocr", "receipt_to_bank_match"],
            "netherlands_adaptation": "Dutch receipt fields, BTW rates, KvK/BTW IDs, UBL attachments, EUR totals, and Dutch date formats.",
        },
        "booke_client_query_tasks": {
            "source": "booke_ai",
            "category": "client_workflow",
            "status": "partial",
            "required_capabilities": ["missing_document_chase", "chat_task_orchestrator"],
            "netherlands_adaptation": "Dutch/English request templates with approval before sensitive outbound messages.",
        },
        "booke_ap_workflow": {
            "source": "booke_ai",
            "category": "accounts_payable",
            "status": "partial",
            "required_capabilities": ["document_capture_and_ocr", "ap_invoice_workflow", "app_layer_executor"],
            "netherlands_adaptation": "UBL invoices, Dutch suppliers, payment terms, and SEPA payment evidence.",
        },
        "booke_error_detection_journal_dashboard": {
            "source": "booke_ai",
            "category": "reporting",
            "status": "modeled",
            "required_capabilities": ["anomaly_and_health_monitoring", "month_end_close_pack"],
            "netherlands_adaptation": "BTW mismatches, duplicate invoices, missing legal receipts, stale feeds, and close exceptions.",
        },
        "outmin_activeledger_rex_loop": {
            "source": "outmin",
            "category": "reconciliation",
            "status": "partial",
            "required_capabilities": [
                "daily_bank_feed_triage",
                "document_capture_and_ocr",
                "receipt_to_bank_match",
                "ledger_report_reconciliation",
                "month_end_close_pack",
            ],
            "netherlands_adaptation": "CAMT/MT940 imports, BTW controls, and monthly/quarterly close packs.",
        },
        "outmin_practice_control_centre": {
            "source": "outmin",
            "category": "platform",
            "status": "modeled",
            "required_capabilities": ["daily_bank_feed_triage", "missing_document_chase", "month_end_close_pack"],
            "netherlands_adaptation": "BTW, ICP, annual-accounting, and filing readiness by client.",
        },
        "outmin_no_chase_no_upload_no_coding": {
            "source": "outmin",
            "category": "client_workflow",
            "status": "partial",
            "required_capabilities": ["missing_document_chase", "vendor_category_learning", "receipt_to_bank_match"],
            "netherlands_adaptation": "Legal-document retention and BTW deductibility review gates.",
        },
        "outmin_partnership_embedded_models": {
            "source": "outmin",
            "category": "platform",
            "status": "planned",
            "required_capabilities": ["app_layer_executor", "month_end_close_pack"],
            "netherlands_adaptation": "Administratiekantoor workspaces, client consent, role access, and Dutch filing calendars.",
        },
        "bookeeping_paula_chat_accountant": {
            "source": "bookeeping_ai",
            "category": "bookkeeping",
            "status": "planned",
            "required_capabilities": ["chat_task_orchestrator", "app_layer_executor"],
            "netherlands_adaptation": "Dutch bookkeeping context with final postings, filings, and messages review-gated.",
        },
        "bookeeping_health_monitoring_audit_score": {
            "source": "bookeeping_ai",
            "category": "reporting",
            "status": "partial",
            "required_capabilities": ["anomaly_and_health_monitoring", "month_end_close_pack"],
            "netherlands_adaptation": "BTW risk, missing purchase invoices, unreconciled age, liquidity, tax reserve, and filing readiness.",
        },
        "bookeeping_import_converter_suite": {
            "source": "bookeeping_ai",
            "category": "platform",
            "status": "planned",
            "required_capabilities": ["daily_bank_feed_triage", "month_end_close_pack"],
            "netherlands_adaptation": "MT940, CAMT.053, CSV, UBL, ICP exports, and Dutch accountant handoff packs.",
        },
        "bookeeping_vertical_templates": {
            "source": "bookeeping_ai",
            "category": "compliance",
            "status": "planned",
            "required_capabilities": [
                "vendor_category_learning",
                "anomaly_and_health_monitoring",
                "month_end_close_pack",
            ],
            "netherlands_adaptation": "Profiles for ZZP, BV, stichting/vereniging, horeca, e-commerce, Airbnb, and OSS/IOSS VAT.",
        },
        "bookeeping_security_ai_ethics": {
            "source": "bookeeping_ai",
            "category": "security",
            "status": "partial",
            "required_capabilities": ["app_layer_executor", "chat_task_orchestrator"],
            "netherlands_adaptation": "GDPR, financial-data retention, least-privilege roles, and no customer data model training.",
        },
        "layernext_finance_agents": {
            "source": "layernext",
            "category": "bookkeeping",
            "status": "partial",
            "required_capabilities": ["app_layer_executor", "chat_task_orchestrator", "month_end_close_pack"],
            "netherlands_adaptation": "Wave, Mijngeldzaken, bank imports, spreadsheets, and Dutch accountant handoff workflows.",
        },
        "layernext_ap_exception_handling": {
            "source": "layernext",
            "category": "accounts_payable",
            "status": "partial",
            "required_capabilities": ["document_capture_and_ocr", "ap_invoice_workflow"],
            "netherlands_adaptation": "BTW, supplier BTW/KvK IDs, IBAN, payment terms, and UBL evidence.",
        },
        "layernext_reconciliation_bookkeeping": {
            "source": "layernext",
            "category": "reconciliation",
            "status": "partial",
            "required_capabilities": [
                "daily_bank_feed_triage",
                "receipt_to_bank_match",
                "ledger_report_reconciliation",
                "vendor_category_learning",
            ],
            "netherlands_adaptation": "CAMT/MT940/CSV statements and tax-ready BTW evidence for quarterly returns.",
        },
        "layernext_custom_erp_desktop": {
            "source": "layernext",
            "category": "platform",
            "status": "partial",
            "required_capabilities": ["app_layer_executor", "vendor_category_learning"],
            "netherlands_adaptation": "Dutch chart mapping, RGS-compatible categories where possible, and rule versioning.",
        },
        "layernext_cfo_mobile_insights": {
            "source": "layernext",
            "category": "reporting",
            "status": "partial",
            "required_capabilities": [
                "anomaly_and_health_monitoring",
                "month_end_close_pack",
                "missing_document_chase",
            ],
            "netherlands_adaptation": "Cash/BTW reserve views, tax deadlines, BTW/ICP readiness, and accountant review packs.",
        },
        "layernext_trust_metalake": {
            "source": "layernext",
            "category": "security",
            "status": "partial",
            "required_capabilities": ["app_layer_executor", "month_end_close_pack"],
            "netherlands_adaptation": "GDPR, Dutch retention, source-document lineage, and accountant/client role separation.",
        },
    },
    "benchmark_areas": {
        "inside_accounting_platform_execution": {
            "label": "Inside-accounting-platform execution",
            "competitor_pattern": "Agents work directly inside the bookkeeping system and fall back to app-layer automation when APIs stop short.",
            "source_ids": ["booke_ai", "layernext"],
            "capability_ids": ["app_layer_executor", "chat_task_orchestrator"],
            "fab_status": "partial",
            "priority": "high",
            "next_milestone": "Expand Wave action manifests with idempotent browser/API execution recipes for every high-volume surface.",
            "risk_control": "Require confirmed execution, idempotency keys, screenshots or API receipts, and rollback notes for write actions.",
        },
        "continuous_reconciliation": {
            "label": "Continuous reconciliation",
            "competitor_pattern": "Bank feeds, documents, and ledger state are reconciled continuously instead of waiting for month-end cleanup.",
            "source_ids": ["booke_ai", "outmin", "layernext"],
            "capability_ids": [
                "daily_bank_feed_triage",
                "receipt_to_bank_match",
                "ledger_report_reconciliation",
                "month_end_close_pack",
            ],
            "fab_status": "partial",
            "priority": "high",
            "next_milestone": "Schedule daily reconciliation planning and publish unresolved match reasons to the review backlog.",
            "risk_control": "Auto-reconcile only exact high-confidence matches; partial matches stay review-gated with source evidence.",
        },
        "missing_document_chase": {
            "label": "Missing-document chase",
            "competitor_pattern": "The system detects missing receipts or context and drafts targeted requests with reminders.",
            "source_ids": ["booke_ai", "outmin", "bookeeping_ai"],
            "capability_ids": ["missing_document_chase"],
            "fab_status": "partial",
            "priority": "high",
            "next_milestone": "Connect missing-document tasks to owner contacts, reminder schedules, and safe outbound-message approval.",
            "risk_control": "Never send external messages without approval when sensitive financial details or client-facing text are present.",
        },
        "ap_approval_workflow": {
            "label": "AP approval workflow",
            "competitor_pattern": "Vendor invoices flow through capture, validation, payable drafting, approval, and payment-state controls.",
            "source_ids": ["outmin", "layernext"],
            "capability_ids": ["ap_invoice_workflow", "document_capture_and_ocr", "vendor_category_learning"],
            "fab_status": "partial",
            "priority": "high",
            "next_milestone": "Add approval-policy rules for vendor, amount, due date, PO/contract match, and payment marking.",
            "risk_control": "Block payment marking and high-value payable changes until an approval policy has explicitly cleared them.",
        },
        "operator_control_center": {
            "label": "Operator control center",
            "competitor_pattern": "Operators get one control surface for every client, reconciliation, exception, source document, and close state.",
            "source_ids": ["outmin", "booke_ai"],
            "capability_ids": [
                "daily_bank_feed_triage",
                "receipt_to_bank_match",
                "ledger_report_reconciliation",
                "missing_document_chase",
                "month_end_close_pack",
            ],
            "fab_status": "covered",
            "priority": "medium",
            "next_milestone": "Add drill-down links from benchmark gaps to the exact review queue, Wave surface, and audit events.",
            "risk_control": "Keep all autonomous decisions traceable from dashboard cards back to source documents and audit events.",
        },
        "deterministic_audit_trail": {
            "label": "Deterministic audit trail",
            "competitor_pattern": "AI suggestions are bounded by accounting logic, human review, validation gates, and a full action trail.",
            "source_ids": ["booke_ai", "bookeeping_ai", "layernext"],
            "capability_ids": ["document_capture_and_ocr", "vendor_category_learning", "receipt_to_bank_match", "app_layer_executor"],
            "fab_status": "covered",
            "priority": "high",
            "next_milestone": "Attach benchmark area IDs to audit events so every autonomous decision names the risk model it used.",
            "risk_control": "Log planned, blocked, reviewed, and completed states with confidence and required signal evidence.",
        },
        "chat_task_execution": {
            "label": "Chat task execution",
            "competitor_pattern": "Owners can ask for bookkeeping actions in natural language and receive validated execution plans.",
            "source_ids": ["bookeeping_ai", "layernext"],
            "capability_ids": ["chat_task_orchestrator", "app_layer_executor"],
            "fab_status": "planned",
            "priority": "medium",
            "next_milestone": "Expose a chat-to-plan endpoint that maps user intent to Wave action plans and review gates.",
            "risk_control": "Treat chat requests as planning input only until target records, required fields, and confirmations are resolved.",
        },
        "bank_statement_import_formats": {
            "label": "Bank statement import formats",
            "competitor_pattern": "CSV, MT940, CAMT, PDF, and payment-provider exports can be imported when direct feeds are unavailable.",
            "source_ids": ["bookeeping_ai"],
            "capability_ids": ["daily_bank_feed_triage", "receipt_to_bank_match"],
            "fab_status": "planned",
            "priority": "medium",
            "next_milestone": "Add parser adapters for common bank export formats and normalize them into the reconciliation queue.",
            "risk_control": "Require account mapping, opening/closing balance validation, and duplicate import fingerprints before posting.",
        },
        "business_health_monitoring": {
            "label": "Business health monitoring",
            "competitor_pattern": "The bookkeeper watches for anomalies, cash-flow drift, stale feeds, and unusual expense behavior.",
            "source_ids": ["bookeeping_ai", "layernext"],
            "capability_ids": ["anomaly_and_health_monitoring", "month_end_close_pack"],
            "fab_status": "partial",
            "priority": "medium",
            "next_milestone": "Turn health signals into actionable review tasks with owner-visible severity and recommended evidence.",
            "risk_control": "Keep recommendations advisory unless a human confirms tax-sensitive or cash-management decisions.",
        },
        "custom_workflow_rules": {
            "label": "Custom workflow rules",
            "competitor_pattern": "Agents learn client-specific business rules and route exceptions through configurable workflows.",
            "source_ids": ["booke_ai", "layernext"],
            "capability_ids": ["vendor_category_learning", "app_layer_executor"],
            "fab_status": "partial",
            "priority": "medium",
            "next_milestone": "Persist user-defined rules for vendors, categories, Wave actions, approval thresholds, and exception routing.",
            "risk_control": "Version every rule change and replay it in dry-run mode before it is allowed to affect live write actions.",
        },
    },
}


AUTONOMOUS_LEVELS = {"observe", "prepare", "safe_draft"}


def list_automation_capabilities(stage: Optional[str] = None) -> List[Dict[str, Any]]:
    capabilities: List[Dict[str, Any]] = []
    for capability_id, capability in AUTONOMOUS_BOOKKEEPER_PLAYBOOK["capabilities"].items():
        if stage and capability["stage"] != stage:
            continue
        capabilities.append({"id": capability_id, **capability})
    return capabilities


def list_automation_benchmarks(status: Optional[str] = None) -> List[Dict[str, Any]]:
    benchmarks: List[Dict[str, Any]] = []
    for benchmark_id, benchmark in AUTONOMOUS_BOOKKEEPER_PLAYBOOK["benchmark_areas"].items():
        if status and benchmark["fab_status"] != status:
            continue
        benchmarks.append({"id": benchmark_id, **benchmark})
    return benchmarks


def list_automation_services(
    source: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    services: List[Dict[str, Any]] = []
    for service_id, service in AUTONOMOUS_BOOKKEEPER_PLAYBOOK["service_offerings"].items():
        if source and service["source"] != source:
            continue
        if category and service["category"] != category:
            continue
        if status and service["status"] != status:
            continue
        services.append({"id": service_id, **service})
    return services


def summarize_automation_services() -> Dict[str, Any]:
    services = list_automation_services()
    by_status = {"modeled": 0, "partial": 0, "planned": 0}
    by_source = {source: 0 for source in AUTONOMOUS_BOOKKEEPER_PLAYBOOK["sources"]}
    by_category: Dict[str, int] = {}
    for service in services:
        by_status[service["status"]] += 1
        by_source[service["source"]] += 1
        by_category[service["category"]] = by_category.get(service["category"], 0) + 1

    return {
        "service_offerings": len(services),
        "services_by_status": by_status,
        "services_by_source": by_source,
        "services_by_category": by_category,
    }


def summarize_automation_benchmarks() -> Dict[str, Any]:
    benchmarks = list_automation_benchmarks()
    by_status = {"covered": 0, "partial": 0, "planned": 0}
    for benchmark in benchmarks:
        by_status[benchmark["fab_status"]] += 1

    return {
        "benchmark_areas": len(benchmarks),
        "benchmark_by_status": by_status,
        "high_priority_benchmark_gaps": len(
            [
                benchmark
                for benchmark in benchmarks
                if benchmark["priority"] == "high" and benchmark["fab_status"] != "covered"
            ]
        ),
    }


def summarize_automation_playbook() -> Dict[str, Any]:
    capabilities = list_automation_capabilities()
    by_stage: Dict[str, int] = {stage: 0 for stage in AUTONOMOUS_BOOKKEEPER_PLAYBOOK["stages"]}
    by_autonomy: Dict[str, int] = {
        "observe": 0,
        "prepare": 0,
        "safe_draft": 0,
        "review_required": 0,
        "confirmed_execute": 0,
    }
    for capability in capabilities:
        by_stage[capability["stage"]] += 1
        by_autonomy[capability["autonomy"]] += 1

    return {
        "sources": len(AUTONOMOUS_BOOKKEEPER_PLAYBOOK["sources"]),
        "stages": len(AUTONOMOUS_BOOKKEEPER_PLAYBOOK["stages"]),
        "capabilities": len(capabilities),
        **summarize_automation_services(),
        **summarize_automation_benchmarks(),
        "wave_linked_capabilities": len([capability for capability in capabilities if capability["wave_actions"]]),
        "capabilities_by_stage": by_stage,
        "capabilities_by_autonomy": by_autonomy,
    }


def plan_autonomous_capability(
    capability_id: str,
    available_signals: Optional[List[str]] = None,
    confidence: Optional[float] = None,
    approvals: Optional[List[str]] = None,
) -> Dict[str, Any]:
    capability = AUTONOMOUS_BOOKKEEPER_PLAYBOOK["capabilities"].get(capability_id)
    if not capability:
        return {
            "status": "blocked_by_review",
            "capability": None,
            "missing_signals": [],
            "review_gates": ["unknown capability"],
            "can_run_autonomously": False,
            "recommended_mode": "review_required",
            "next_action": "Route to manual review because the requested automation capability is not modeled.",
        }

    available: Set[str] = set(available_signals or [])
    approved: Set[str] = set(approvals or [])
    missing = [signal for signal in capability["required_signals"] if signal not in available]
    unresolved_gates = [gate for gate in capability["review_gates"] if gate not in approved]
    effective_confidence = 1.0 if confidence is None else confidence
    low_confidence = effective_confidence < 0.85
    can_run = (
        not missing
        and not low_confidence
        and capability["autonomy"] in AUTONOMOUS_LEVELS
        and capability["autonomy"] != "review_required"
    )

    if missing:
        return {
            "status": "needs_signals",
            "capability": {"id": capability_id, **capability},
            "missing_signals": missing,
            "review_gates": unresolved_gates,
            "can_run_autonomously": False,
            "recommended_mode": "prepare",
            "next_action": f"Collect missing signals: {', '.join(missing)}.",
        }

    if not can_run:
        review_gates = ["confidence below 85%", *unresolved_gates] if low_confidence else unresolved_gates
        return {
            "status": "blocked_by_review",
            "capability": {"id": capability_id, **capability},
            "missing_signals": [],
            "review_gates": review_gates,
            "can_run_autonomously": False,
            "recommended_mode": capability["autonomy"],
            "next_action": "Prepare the work item and route it through the review gate before posting or sending.",
        }

    return {
        "status": "ready",
        "capability": {"id": capability_id, **capability},
        "missing_signals": [],
        "review_gates": unresolved_gates,
        "can_run_autonomously": True,
        "recommended_mode": capability["autonomy"],
        "next_action": "Run the capability through the policy-gated autonomous operator.",
    }


def _unique(values: List[str]) -> List[str]:
    return list(dict.fromkeys([value for value in values if value]))


def _report_payload(
    workflow_input: Dict[str, Any],
    report_type: str,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload = {
        "reportType": report_type,
        "fromDate": workflow_input["from_date"],
        "toDate": workflow_input["to_date"],
        "asOfDate": workflow_input.get("as_of_date") or workflow_input["to_date"],
        "basis": workflow_input.get("cash_mode") or "accrual",
        "accountOption": workflow_input.get("account_option") or "-1",
        "accountName": workflow_input.get("account_name") or "All Accounts",
        "contactOption": workflow_input.get("contact_option") or "0",
        "contactName": workflow_input.get("contact_name") or "All Contacts",
        "cashMode": workflow_input.get("cash_mode") or "1",
    }
    if extra:
        payload.update(extra)
    return payload


def _daily_reconciliation_steps(workflow_input: Dict[str, Any]) -> List[Dict[str, Any]]:
    payload = _report_payload(workflow_input, "account-transactions")
    steps = [
        ("open_account_transactions_report", "Open Account Transactions report", "report_open"),
        ("scope_account_transactions_by_account", "Scope ledger by account", "report_account_filter_select"),
        ("scope_account_transactions_by_contact", "Scope ledger by contact", "report_contact_filter_select"),
        ("set_ledger_report_period", "Set ledger report period", "report_date_range_set"),
        ("select_ledger_report_basis", "Select ledger report basis", "report_basis_select"),
        ("refresh_ledger_report", "Update ledger report", "report_update"),
        ("read_ledger_rows", "Read ledger rows", "report_table_read"),
        ("detect_empty_ledger_scope", "Detect empty ledger scope", "report_empty_state_read"),
    ]
    planned_steps = [
        {
            "id": step_id,
            "label": label,
            "capability_id": "ledger_report_reconciliation",
            "surface": "reports",
            "action": action,
            "payload": payload,
            "safety": "read_only",
        }
        for step_id, label, action in steps
    ]
    if workflow_input.get("include_exports", True):
        planned_steps.append(
            {
                "id": "export_ledger_evidence",
                "label": "Export ledger evidence",
                "capability_id": "ledger_report_reconciliation",
                "surface": "reports",
                "action": "report_export",
                "payload": _report_payload(workflow_input, "account-transactions", {"format": "csv"}),
                "safety": "read_only",
            }
        )
    return planned_steps


def _period_close_steps(workflow_input: Dict[str, Any]) -> List[Dict[str, Any]]:
    report_types = [
        "profit-and-loss",
        "balance-sheet",
        "cash-flow",
        "sales-tax",
        "aged-receivables",
        "aged-payables",
        "account-balances",
        "trial-balance",
    ]
    steps = _daily_reconciliation_steps({**workflow_input, "include_exports": True})
    for report_type in report_types:
        steps.extend(
            [
                {
                    "id": f"open_{report_type}_report",
                    "label": f"Open {report_type} report",
                    "capability_id": "month_end_close_pack",
                    "surface": "reports",
                    "action": "report_open",
                    "payload": _report_payload(workflow_input, report_type),
                    "safety": "read_only",
                },
                {
                    "id": f"export_{report_type}_report",
                    "label": f"Export {report_type} report",
                    "capability_id": "month_end_close_pack",
                    "surface": "reports",
                    "action": "report_export",
                    "payload": _report_payload(workflow_input, report_type, {"format": "pdf"}),
                    "safety": "read_only",
                },
            ]
        )
    return steps


def plan_autonomous_workflow(
    workflow_id: str,
    from_date: str,
    to_date: str,
    available_signals: Optional[List[str]] = None,
    confidence: Optional[float] = None,
    approvals: Optional[List[str]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    workflow_input = {
        "workflow_id": workflow_id,
        "from_date": from_date,
        "to_date": to_date,
        **kwargs,
    }
    if workflow_id == "period_close_pack":
        capability_ids = ["ledger_report_reconciliation", "month_end_close_pack", "anomaly_and_health_monitoring"]
        steps = _period_close_steps(workflow_input)
    else:
        capability_ids = ["ledger_report_reconciliation", "receipt_to_bank_match"]
        steps = _daily_reconciliation_steps(workflow_input)

    capability_plans = [
        plan_autonomous_capability(capability_id, available_signals, confidence, approvals)
        for capability_id in capability_ids
    ]
    required_signals = _unique(
        [
            signal
            for plan in capability_plans
            for signal in (plan.get("capability") or {}).get("required_signals", [])
        ]
    )
    missing_signals = _unique([signal for plan in capability_plans for signal in plan["missing_signals"]])
    review_gates = _unique([gate for plan in capability_plans for gate in plan["review_gates"]])
    if any(plan["status"] == "blocked_by_review" for plan in capability_plans):
        status = "blocked_by_review"
    elif any(plan["status"] == "needs_signals" for plan in capability_plans):
        status = "needs_signals"
    else:
        status = "ready"

    return {
        "workflow_id": workflow_id,
        "status": status,
        "can_run_autonomously": status == "ready" and all(step["safety"] in {"read_only", "safe_draft"} for step in steps),
        "required_signals": required_signals,
        "missing_signals": missing_signals,
        "review_gates": review_gates,
        "capability_plans": capability_plans,
        "steps": steps,
        "next_action": (
            "Queue this workflow through the policy-gated autonomous Wave executor."
            if status == "ready"
            else f"Collect missing signals: {', '.join(missing_signals)}."
            if missing_signals
            else "Prepare the workflow and route unresolved review gates before execution."
        ),
    }


class AutonomousBookkeeperPlaybook:
    """Deterministic orchestration policy for the autonomous bookkeeping loop."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def summarize(self) -> Dict[str, Any]:
        return summarize_automation_playbook()

    def benchmark(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        return list_automation_benchmarks(status)

    def services(
        self,
        source: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return list_automation_services(source, category, status)

    def plan(
        self,
        capability_id: str,
        available_signals: Optional[List[str]] = None,
        confidence: Optional[float] = None,
        approvals: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return plan_autonomous_capability(capability_id, available_signals, confidence, approvals)

    def plan_workflow(
        self,
        workflow_id: str,
        from_date: str,
        to_date: str,
        available_signals: Optional[List[str]] = None,
        confidence: Optional[float] = None,
        approvals: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        return plan_autonomous_workflow(
            workflow_id,
            from_date,
            to_date,
            available_signals,
            confidence,
            approvals,
            **kwargs,
        )

    def infer_document_capabilities(self, document: Dict[str, Any]) -> List[str]:
        capabilities = ["document_capture_and_ocr", "vendor_category_learning"]
        document_type = str(document.get("document_type") or document.get("type") or "").lower()
        if document_type in {"invoice", "vendor_invoice", "bill"}:
            capabilities.append("ap_invoice_workflow")
        if document.get("bank_transaction") or document.get("bank_transaction_id"):
            capabilities.append("receipt_to_bank_match")
        if document.get("missing_receipt") or document.get("needs_context"):
            capabilities.append("missing_document_chase")
        return capabilities

    def plan_document(
        self,
        document: Dict[str, Any],
        available_signals: Optional[List[str]] = None,
        confidence: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        signals = list(available_signals or [])
        if document.get("ocr_text"):
            signals.append("ocr_text")
        if document.get("source_document") or document.get("sourceDocumentId") or document.get("original_filename"):
            signals.append("source_document")
        if document.get("vendor_name") or document.get("vendor_identity"):
            signals.append("vendor_identity")
        if document.get("category") or document.get("category_candidates"):
            signals.append("category_candidates")
        if document.get("line_items") or document.get("extracted_data", {}).get("line_items"):
            signals.append("line_items")
        if document.get("duplicate_fingerprint"):
            signals.append("duplicate_fingerprint")
        if document.get("bank_transaction") or document.get("bank_transaction_id"):
            signals.append("bank_transaction")

        return [
            self.plan(capability_id, sorted(set(signals)), confidence)
            for capability_id in self.infer_document_capabilities(document)
        ]
