export type AutomationStageId =
  | "collect"
  | "extract_validate"
  | "classify_post"
  | "match_reconcile"
  | "exception_chase"
  | "close_report"
  | "learn_optimize"
  | "system_execute";

export type AutomationAutonomyLevel =
  | "observe"
  | "prepare"
  | "safe_draft"
  | "review_required"
  | "confirmed_execute";

export type AutomationSourceId = "booke_ai" | "outmin" | "bookeeping_ai" | "layernext";

export type AutomationSource = {
  id: AutomationSourceId;
  label: string;
  url: string;
  patterns: string[];
};

export type AutomationBenchmarkStatus = "covered" | "partial" | "planned";
export type AutomationBenchmarkPriority = "high" | "medium" | "low";

export type AutomationBenchmarkArea = {
  id: string;
  label: string;
  competitorPattern: string;
  sourceIds: AutomationSourceId[];
  capabilityIds: string[];
  fabStatus: AutomationBenchmarkStatus;
  priority: AutomationBenchmarkPriority;
  nextMilestone: string;
  riskControl: string;
};

export type AutomationServiceStatus = "modeled" | "partial" | "planned";
export type AutomationServiceCategory =
  | "capture"
  | "bookkeeping"
  | "reconciliation"
  | "accounts_payable"
  | "client_workflow"
  | "reporting"
  | "compliance"
  | "security"
  | "platform";

export type AutomationServiceOffering = {
  id: string;
  sourceId: AutomationSourceId;
  category: AutomationServiceCategory;
  label: string;
  serviceSurface: string;
  extractedFrom: string[];
  fabImplementation: string;
  status: AutomationServiceStatus;
  requiredCapabilities: string[];
  netherlandsAdaptation: string;
};

export type AutomationStage = {
  id: AutomationStageId;
  label: string;
  purpose: string;
  targetOutcome: string;
};

export type AutomationCapability = {
  id: string;
  stageId: AutomationStageId;
  label: string;
  autonomyLevel: AutomationAutonomyLevel;
  description: string;
  requiredSignals: string[];
  optionalSignals: string[];
  waveActions: string[];
  reviewGates: string[];
  auditEvents: string[];
  inspiredBy: AutomationSourceId[];
};

export type AutonomousBookkeeperPlaybook = {
  source: "competitor_research";
  capturedFrom: string;
  sources: AutomationSource[];
  stages: AutomationStage[];
  capabilities: AutomationCapability[];
  serviceOfferings: AutomationServiceOffering[];
  benchmarkAreas: AutomationBenchmarkArea[];
};

export type AutomationCapabilityPlan = {
  status: "ready" | "needs_signals" | "blocked_by_review";
  capability?: AutomationCapability;
  missingSignals: string[];
  reviewGates: string[];
  canRunAutonomously: boolean;
  recommendedMode: AutomationAutonomyLevel;
  nextAction: string;
};

export const autonomousBookkeeperPlaybook = {
  source: "competitor_research",
  capturedFrom: "Booke AI, Outmin, Bookeeping.ai, and LayerNext public product pages reviewed on 2026-06-28",
  sources: [
    {
      id: "booke_ai",
      label: "Booke AI",
      url: "https://booke.ai/",
      patterns: [
        "Daily bank feed categorization inside the accounting platform",
        "Document matching against invoices, bills, and receipts",
        "Client query tasks for missing transaction context",
        "Month-end discrepancy detection and interactive reports",
      ],
    },
    {
      id: "outmin",
      label: "Outmin",
      url: "https://www.outmin.io/what-is-outmin",
      patterns: [
        "Continuous ActiveLedger-style reconciliation",
        "Practice control centre with client-facing simple uploads",
        "Rex Collect, Process, Reconcile, and Close workflow stages",
        "Traceable books with edge cases surfaced for verification",
      ],
    },
    {
      id: "bookeeping_ai",
      label: "Bookeeping.ai",
      url: "https://bookeeping.ai/",
      patterns: [
        "Chat-driven task completion for invoices and bookkeeping questions",
        "Business health monitoring and anomaly alerts",
        "Multi-format bank statement import",
        "Human review, deterministic accounting logic, and full audit trail",
      ],
    },
    {
      id: "layernext",
      label: "LayerNext",
      url: "https://www.layernext.ai/",
      patterns: [
        "AI agents for AP, reconciliation, bookkeeping, reporting, and custom workflows",
        "Approval gates before posting finance work",
        "ERP and desktop automation when APIs are unavailable",
        "Business rules, workflow audit trails, and customer data isolation",
      ],
    },
  ],
  stages: [
    {
      id: "collect",
      label: "Collect",
      purpose: "Pull bank activity, receipts, invoices, emails, and Drive files into one evidence queue.",
      targetOutcome: "Every transaction has a known source, expected document state, and ownership trail.",
    },
    {
      id: "extract_validate",
      label: "Extract & Validate",
      purpose: "Read documents, normalize multilingual fields, and validate totals, VAT, dates, and vendor identity.",
      targetOutcome: "Only complete, internally consistent document records move forward without review.",
    },
    {
      id: "classify_post",
      label: "Classify & Post",
      purpose: "Apply vendor history, category rules, and Wave surface routing to prepare draft accounting entries.",
      targetOutcome: "Safe draft entries are ready in the right Wave surface with category and tax metadata.",
    },
    {
      id: "match_reconcile",
      label: "Match & Reconcile",
      purpose: "Match documents to bank transactions, invoices, bills, payments, and supporting receipts.",
      targetOutcome: "Clean matches reconcile automatically; partial or risky matches land in review.",
    },
    {
      id: "exception_chase",
      label: "Exception Chase",
      purpose: "Turn missing receipts, unclear vendors, and anomalies into owner/client tasks or email requests.",
      targetOutcome: "The system asks for the exact missing evidence and waits with reminders.",
    },
    {
      id: "close_report",
      label: "Close & Report",
      purpose: "Run period checks, detect discrepancies, export reports, and package audit evidence.",
      targetOutcome: "Month-end starts from reconciled, traceable books instead of cleanup.",
    },
    {
      id: "learn_optimize",
      label: "Learn & Optimize",
      purpose: "Learn from corrections, category overrides, vendor merges, and exception outcomes.",
      targetOutcome: "Future automation gets stricter where risk is high and faster where history is stable.",
    },
    {
      id: "system_execute",
      label: "System Execute",
      purpose: "Use APIs first and controlled browser or desktop execution only for surfaces without APIs.",
      targetOutcome: "Human-equivalent platform actions are policy-gated, idempotent, and auditable.",
    },
  ],
  capabilities: [
    {
      id: "daily_bank_feed_triage",
      stageId: "collect",
      label: "Daily bank feed triage",
      autonomyLevel: "prepare",
      description: "Import new bank transactions, identify uncategorized activity, and plan matching work.",
      requiredSignals: ["bank_feed", "account_mapping"],
      optionalSignals: ["prior_reconciliation", "vendor_history"],
      waveActions: ["connected_account_refresh", "transaction_categorize"],
      reviewGates: ["provider re-authentication", "new bank account connection"],
      auditEvents: ["bank_feed.refresh_planned", "transaction.triage_completed"],
      inspiredBy: ["booke_ai", "outmin", "layernext"],
    },
    {
      id: "document_capture_and_ocr",
      stageId: "extract_validate",
      label: "Document capture and OCR",
      autonomyLevel: "safe_draft",
      description: "Collect receipts and invoices, run OCR, extract line items, and validate totals.",
      requiredSignals: ["source_document", "ocr_text"],
      optionalSignals: ["line_items", "language", "vat_number"],
      waveActions: ["transaction_attach_receipt", "bill_create"],
      reviewGates: ["low OCR confidence", "unbalanced subtotal/tax/total"],
      auditEvents: ["document.imported", "document.extracted", "document.validation_failed"],
      inspiredBy: ["booke_ai", "bookeeping_ai", "layernext"],
    },
    {
      id: "vendor_category_learning",
      stageId: "classify_post",
      label: "Vendor and category learning",
      autonomyLevel: "safe_draft",
      description: "Use vendor history and user rules to select categories, taxes, and Wave account mappings.",
      requiredSignals: ["vendor_identity", "category_candidates"],
      optionalSignals: ["purchase_pattern", "user_rule", "tax_profile"],
      waveActions: ["vendor_create", "chart_account_map", "transaction_categorize"],
      reviewGates: ["new chart-of-account creation", "ambiguous vendor match", "first-seen tax treatment"],
      auditEvents: ["vendor.match", "category.suggested", "category.applied"],
      inspiredBy: ["booke_ai", "bookeeping_ai", "layernext"],
    },
    {
      id: "ap_invoice_workflow",
      stageId: "classify_post",
      label: "AP invoice workflow",
      autonomyLevel: "review_required",
      description: "Create payable drafts from vendor invoices, match to POs when present, and route for approval.",
      requiredSignals: ["vendor_invoice", "vendor_identity", "line_items"],
      optionalSignals: ["purchase_order", "approval_rule", "due_date"],
      waveActions: ["bill_create", "bill_mark_paid"],
      reviewGates: ["payment marking", "approval threshold", "missing PO or contract"],
      auditEvents: ["ap.bill_drafted", "ap.approval_required", "ap.payment_blocked"],
      inspiredBy: ["outmin", "layernext"],
    },
    {
      id: "receipt_to_bank_match",
      stageId: "match_reconcile",
      label: "Receipt to bank matching",
      autonomyLevel: "safe_draft",
      description: "Match receipts to bank lines by amount, date, vendor, currency, and duplicate fingerprint.",
      requiredSignals: ["source_document", "bank_transaction", "duplicate_fingerprint"],
      optionalSignals: ["vendor_history", "currency", "card_last_four"],
      waveActions: ["transaction_attach_receipt", "transaction_categorize"],
      reviewGates: ["partial amount match", "duplicate candidate", "multi-document order"],
      auditEvents: ["reconciliation.match_found", "reconciliation.partial_match", "duplicate.detected"],
      inspiredBy: ["booke_ai", "outmin", "layernext"],
    },
    {
      id: "ledger_report_reconciliation",
      stageId: "match_reconcile",
      label: "Ledger report reconciliation",
      autonomyLevel: "prepare",
      description: "Use Wave Account Transactions as the source-of-truth ledger view for account/contact/date-scoped reconciliation evidence.",
      requiredSignals: ["ledger_period", "account_scope", "reconciliation_status"],
      optionalSignals: ["contact_scope", "cash_mode", "bank_feed", "review_queue"],
      waveActions: [
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
      reviewGates: ["empty ledger scope", "unmatched bank activity", "material discrepancy"],
      auditEvents: ["ledger.report_opened", "ledger.scope_verified", "ledger.empty_scope_detected", "ledger.evidence_exported"],
      inspiredBy: ["outmin", "bookeeping_ai", "layernext"],
    },
    {
      id: "missing_document_chase",
      stageId: "exception_chase",
      label: "Missing document chase",
      autonomyLevel: "review_required",
      description: "Detect transactions that should have receipts, draft requests, and schedule reminders.",
      requiredSignals: ["bank_transaction", "document_policy"],
      optionalSignals: ["contact_email", "last_request_at", "owner"],
      waveActions: [],
      reviewGates: ["external email send", "client-facing message", "sensitive financial details"],
      auditEvents: ["missing_document.detected", "missing_document.request_drafted", "reminder.scheduled"],
      inspiredBy: ["booke_ai", "outmin", "bookeeping_ai"],
    },
    {
      id: "anomaly_and_health_monitoring",
      stageId: "close_report",
      label: "Anomaly and health monitoring",
      autonomyLevel: "observe",
      description: "Watch for unusual expenses, cash-flow drift, stale bank feeds, and unreconciled balances.",
      requiredSignals: ["ledger_snapshot", "bank_feed"],
      optionalSignals: ["budget", "historical_average", "cash_forecast"],
      waveActions: ["report_open"],
      reviewGates: ["advisory recommendation", "tax-sensitive decision"],
      auditEvents: ["health.anomaly_detected", "cashflow.warning", "feed.stale"],
      inspiredBy: ["bookeeping_ai", "layernext"],
    },
    {
      id: "month_end_close_pack",
      stageId: "close_report",
      label: "Month-end close pack",
      autonomyLevel: "prepare",
      description: "Run close checks, export reports, summarize exceptions, and assemble evidence for review.",
      requiredSignals: ["ledger_snapshot", "reconciliation_status"],
      optionalSignals: ["period_lock_date", "vat_working", "review_queue"],
      waveActions: ["report_export", "customer_statement_create"],
      reviewGates: ["period lock", "tax filing", "material unresolved exception"],
      auditEvents: ["close.check_started", "close.report_exported", "close.exception_summary"],
      inspiredBy: ["booke_ai", "outmin", "layernext"],
    },
    {
      id: "chat_task_orchestrator",
      stageId: "system_execute",
      label: "Chat task orchestrator",
      autonomyLevel: "prepare",
      description: "Translate owner requests into validated bookkeeping actions and safe execution plans.",
      requiredSignals: ["user_intent", "policy_context"],
      optionalSignals: ["target_customer", "target_vendor", "amount", "due_date"],
      waveActions: ["invoice_create", "estimate_create", "report_open"],
      reviewGates: ["send invoice", "record payment", "create recurring billing"],
      auditEvents: ["chat.intent_classified", "chat.action_planned", "chat.confirmation_required"],
      inspiredBy: ["bookeeping_ai", "layernext"],
    },
    {
      id: "app_layer_executor",
      stageId: "system_execute",
      label: "App-layer executor",
      autonomyLevel: "confirmed_execute",
      description: "Execute approved Wave or legacy-app actions through API, browser, or desktop automation.",
      requiredSignals: ["approved_operation", "idempotency_key", "target_surface"],
      optionalSignals: ["browser_route", "api_endpoint", "rollback_plan"],
      waveActions: ["transaction_add", "bill_create", "invoice_create", "report_export"],
      reviewGates: ["credential prompt", "external communication", "payment or account access change"],
      auditEvents: ["executor.started", "executor.completed", "executor.blocked"],
      inspiredBy: ["booke_ai", "layernext"],
    },
  ],
  serviceOfferings: [
    {
      id: "booke_qbo_xero_bank_feed_ai",
      sourceId: "booke_ai",
      category: "bookkeeping",
      label: "QuickBooks and Xero AI bookkeeper",
      serviceSurface: "Daily bank-feed review, client-history categorization, document matching, and review trail inside accounting platforms.",
      extractedFrom: ["Booke AI homepage", "QuickBooks Online page", "Xero page", "Bookkeeping automation hub"],
      fabImplementation: "Run the same loop against Wave, Mijngeldzaken, and import-only ledgers through the Wave surface model and autonomous operator.",
      status: "partial",
      requiredCapabilities: ["daily_bank_feed_triage", "vendor_category_learning", "receipt_to_bank_match", "app_layer_executor"],
      netherlandsAdaptation: "Support Dutch bank feeds, SEPA descriptions, IBAN counterparty matching, BTW category mapping, and audit evidence retention.",
    },
    {
      id: "booke_document_ocr_matching",
      sourceId: "booke_ai",
      category: "capture",
      label: "Invoice and receipt OCR with matching",
      serviceSurface: "OCR, custom templates, tax auto-fill, confidence indicators, multilingual/currency handling, categorization, and matching.",
      extractedFrom: ["Invoice and Receipt OCR AI page"],
      fabImplementation: "Extend document extraction into validated line-item records and feed confidence-aware matching and review decisions.",
      status: "partial",
      requiredCapabilities: ["document_capture_and_ocr", "receipt_to_bank_match"],
      netherlandsAdaptation: "Extract Dutch receipt fields, BTW rates, KvK/BTW IDs, UBL attachments, EUR totals, and Dutch date/decimal formats.",
    },
    {
      id: "booke_client_query_tasks",
      sourceId: "booke_ai",
      category: "client_workflow",
      label: "Client query and task management",
      serviceSurface: "Client questions, internal/external tasks, transaction context requests, client visibility controls, and follow-up tracking.",
      extractedFrom: ["Client Query Tool page", "Tasks page", "AI client portal page"],
      fabImplementation: "Turn missing context into review tasks, draft outbound requests, schedule reminders, and keep responses attached to transactions.",
      status: "partial",
      requiredCapabilities: ["missing_document_chase", "chat_task_orchestrator"],
      netherlandsAdaptation: "Use Dutch/English message templates and avoid sending tax-sensitive details without explicit approval.",
    },
    {
      id: "booke_ap_workflow",
      sourceId: "booke_ai",
      category: "accounts_payable",
      label: "Accounts payable document workflow",
      serviceSurface: "Bulk upload, unique client email, selectable workflows, export with original document, Google Drive and Dropbox integrations.",
      extractedFrom: ["Accounts Payable workflow page"],
      fabImplementation: "Route vendor invoices from Drive/email into payable drafts with source documents and approval-state controls.",
      status: "partial",
      requiredCapabilities: ["document_capture_and_ocr", "ap_invoice_workflow", "app_layer_executor"],
      netherlandsAdaptation: "Support UBL invoices, Dutch supplier identities, due-date/payment-term extraction, and SEPA payment evidence.",
    },
    {
      id: "booke_error_detection_journal_dashboard",
      sourceId: "booke_ai",
      category: "reporting",
      label: "Error detection, activity journal, and performance dashboard",
      serviceSurface: "Automatic inconsistency rules, discrepancy correction flow, activity journal, and all-client performance overview.",
      extractedFrom: ["Inconsistencies and Error Detection page", "Activities Journal page", "Performance Dashboard page"],
      fabImplementation: "Expose anomaly, audit, and client/status views in Operations with traceable resolution states.",
      status: "modeled",
      requiredCapabilities: ["anomaly_and_health_monitoring", "month_end_close_pack"],
      netherlandsAdaptation: "Flag BTW mismatches, duplicate invoices, missing legal receipts, stale bank feeds, and period-close exceptions.",
    },
    {
      id: "outmin_activeledger_rex_loop",
      sourceId: "outmin",
      category: "reconciliation",
      label: "Continuous ActiveLedger and Rex loop",
      serviceSurface: "Rex Collect, Process, Reconcile, and Close with continuously reconciled, traceable books.",
      extractedFrom: ["What is Outmin page", "Small business bookkeeping automation page", "Pricing page"],
      fabImplementation: "Schedule a daily autonomous loop that ingests source documents, reconciles, creates exceptions, and produces close evidence.",
      status: "partial",
      requiredCapabilities: [
        "daily_bank_feed_triage",
        "document_capture_and_ocr",
        "receipt_to_bank_match",
        "ledger_report_reconciliation",
        "month_end_close_pack",
      ],
      netherlandsAdaptation: "Use Dutch bank exports, CAMT/MT940 imports, BTW controls, and monthly/quarterly close packs.",
    },
    {
      id: "outmin_practice_control_centre",
      sourceId: "outmin",
      category: "platform",
      label: "Practice control centre",
      serviceSurface: "One control centre for every client, reconciliation, exception, AP/AR/GL/trial balance/VAT/source document, and close state.",
      extractedFrom: ["What is Outmin page", "Accounting firm partnership page"],
      fabImplementation: "Make Operations the command centre for documents, Wave/Mijngeldzaken routing, reconciliation, review, and audit timelines.",
      status: "modeled",
      requiredCapabilities: ["daily_bank_feed_triage", "missing_document_chase", "month_end_close_pack"],
      netherlandsAdaptation: "Surface BTW, ICP, annual-accounting, and client-by-client filing readiness for Dutch administrations.",
    },
    {
      id: "outmin_no_chase_no_upload_no_coding",
      sourceId: "outmin",
      category: "client_workflow",
      label: "No supplier chasing, no manual upload, no transaction coding",
      serviceSurface: "Supplier/document chasing, simple uploads, automatic coding, and no month-end scrambles.",
      extractedFrom: ["Small business bookkeeping automation page", "Compare Outmin page"],
      fabImplementation: "Treat missing documents and uncoded transactions as autonomous tasks with owner assignment and escalation.",
      status: "partial",
      requiredCapabilities: ["missing_document_chase", "vendor_category_learning", "receipt_to_bank_match"],
      netherlandsAdaptation: "Keep Dutch legal-document retention and BTW deductibility checks in the review gate.",
    },
    {
      id: "outmin_partnership_embedded_models",
      sourceId: "outmin",
      category: "platform",
      label: "Referral and embedded accountant partnership models",
      serviceSurface: "Referral partners, embedded partners, scalable bookkeeping capacity, and modern service offering for firms.",
      extractedFrom: ["Accounting firm partnership page"],
      fabImplementation: "Model multi-client/multi-entity workspaces and account-firm operator roles in FAB's control model.",
      status: "planned",
      requiredCapabilities: ["app_layer_executor", "month_end_close_pack"],
      netherlandsAdaptation: "Support administratiekantoor workflows, client consent, role-based access, and Dutch filing calendars.",
    },
    {
      id: "bookeeping_paula_chat_accountant",
      sourceId: "bookeeping_ai",
      category: "bookkeeping",
      label: "Paula chat accountant",
      serviceSurface: "Chat-driven task completion, document analysis, financial questions, and zero-effort bookkeeping.",
      extractedFrom: ["Bookeeping.ai homepage", "Why us page", "Talk page"],
      fabImplementation: "Expose chat-to-plan orchestration where natural-language requests produce safe Wave/FAB execution plans.",
      status: "planned",
      requiredCapabilities: ["chat_task_orchestrator", "app_layer_executor"],
      netherlandsAdaptation: "Answer with Dutch bookkeeping context and block final postings, filings, or messages until review gates pass.",
    },
    {
      id: "bookeeping_health_monitoring_audit_score",
      sourceId: "bookeeping_ai",
      category: "reporting",
      label: "Business health monitoring and AI audit score",
      serviceSurface: "24/7 monitoring, anomaly detection, audit score, and advice on actions.",
      extractedFrom: ["Bookeeping.ai homepage", "Features page"],
      fabImplementation: "Convert ledger, bank-feed, and review signals into health events and close-readiness scores.",
      status: "partial",
      requiredCapabilities: ["anomaly_and_health_monitoring", "month_end_close_pack"],
      netherlandsAdaptation: "Track BTW risk, missing purchase invoices, bank unreconciled age, liquidity, tax reserve, and filing readiness.",
    },
    {
      id: "bookeeping_import_converter_suite",
      sourceId: "bookeeping_ai",
      category: "platform",
      label: "Imports, converters, and accountant utilities",
      serviceSurface: "QuickBooks import, Drake converter, tax document conversion, synced transactions, AI sheet/doc tools, and custom development.",
      extractedFrom: ["QuickBooks import page", "Accountants page", "Drake converter page", "AI Sheet page", "AI Doc page", "Custom Development page"],
      fabImplementation: "Add adapter registry for imports/exports and reusable conversion jobs for bank, ledger, document, and report formats.",
      status: "planned",
      requiredCapabilities: ["daily_bank_feed_triage", "month_end_close_pack"],
      netherlandsAdaptation: "Prioritize MT940, CAMT.053, CSV bank imports, UBL invoices, ICP exports, and Dutch accountant handoff packs.",
    },
    {
      id: "bookeeping_vertical_templates",
      sourceId: "bookeeping_ai",
      category: "compliance",
      label: "Vertical bookkeeping templates",
      serviceSurface: "Nonprofit fund/program tracking, nonprofit statements, Airbnb accounting, and tax-compliance MCP servers.",
      extractedFrom: ["Non-profit page", "Airbnb import page", "IRS Tax MCP page"],
      fabImplementation: "Represent vertical rule packs as configurable profiles that change categories, evidence, reporting, and review gates.",
      status: "planned",
      requiredCapabilities: ["vendor_category_learning", "anomaly_and_health_monitoring", "month_end_close_pack"],
      netherlandsAdaptation: "Add Dutch profiles for ZZP, BV, stichting/vereniging, horeca, e-commerce, Airbnb/verhuur, and OSS/IOSS VAT.",
    },
    {
      id: "bookeeping_security_ai_ethics",
      sourceId: "bookeeping_ai",
      category: "security",
      label: "Security, privacy, AI ethics, and accountant/client access",
      serviceSurface: "Plaid bank security, SOC2-grade infrastructure, data residency, 2FA/passkeys, RBAC, private prompts, and AI ethics.",
      extractedFrom: ["Why us page", "Security page", "Privacy policy", "AI ethics page"],
      fabImplementation: "Keep role-based controls, audit trails, isolated financial data, and explicit AI decision boundaries in the autonomy model.",
      status: "partial",
      requiredCapabilities: ["app_layer_executor", "chat_task_orchestrator"],
      netherlandsAdaptation: "Align to GDPR, Dutch financial-data retention, least-privilege accountant roles, and no customer data model training.",
    },
    {
      id: "layernext_finance_agents",
      sourceId: "layernext",
      category: "bookkeeping",
      label: "AI agents for finance operations",
      serviceSurface: "Agents process invoices, reconcile accounts, categorize transactions, generate CFO reports, and work across any ERP/accounting platform.",
      extractedFrom: ["LayerNext homepage", "Enterprise page"],
      fabImplementation: "Keep FAB's autonomous operator as a policy-gated agent layer that can plan, execute, verify, and audit finance workflows.",
      status: "partial",
      requiredCapabilities: ["app_layer_executor", "chat_task_orchestrator", "month_end_close_pack"],
      netherlandsAdaptation: "Route across Wave, Mijngeldzaken, bank imports, spreadsheets, and Dutch accountant handoff workflows.",
    },
    {
      id: "layernext_ap_exception_handling",
      sourceId: "layernext",
      category: "accounts_payable",
      label: "AP and invoice autopilot with exceptions",
      serviceSurface: "Invoice capture, extraction, validation, PO matching, approval routing, exception handling, and payment readiness.",
      extractedFrom: ["LayerNext homepage", "Enterprise page"],
      fabImplementation: "Add AP approval-policy rules and exception queues for payable drafts and payment-state changes.",
      status: "partial",
      requiredCapabilities: ["document_capture_and_ocr", "ap_invoice_workflow"],
      netherlandsAdaptation: "Validate BTW rates, supplier BTW/KvK IDs, IBAN, due dates, payment terms, and UBL source evidence.",
    },
    {
      id: "layernext_reconciliation_bookkeeping",
      sourceId: "layernext",
      category: "reconciliation",
      label: "Real-time reconciliation and autonomous bookkeeping",
      serviceSurface: "Connect banks or upload statements; match and reconcile in real time; capture, categorize, and make expenses tax-ready.",
      extractedFrom: ["LayerNext homepage", "Enterprise page"],
      fabImplementation: "Combine bank import, document matching, categorization, and tax-readiness into one daily reconciliation loop.",
      status: "partial",
      requiredCapabilities: [
        "daily_bank_feed_triage",
        "receipt_to_bank_match",
        "ledger_report_reconciliation",
        "vendor_category_learning",
      ],
      netherlandsAdaptation: "Support Dutch CAMT/MT940/CSV statements and tax-ready BTW evidence for quarterly returns.",
    },
    {
      id: "layernext_custom_erp_desktop",
      sourceId: "layernext",
      category: "platform",
      label: "Custom workflows plus ERP and desktop automation",
      serviceSurface: "Business-rule execution, approval chains, GL structures, application-layer automation, desktop apps, legacy ERPs, and no-API surfaces.",
      extractedFrom: ["LayerNext homepage", "Enterprise page", "FAQ"],
      fabImplementation: "Use Wave/API routes first and browser/desktop recipes only for approved, idempotent, replayable operations.",
      status: "partial",
      requiredCapabilities: ["app_layer_executor", "vendor_category_learning"],
      netherlandsAdaptation: "Keep Dutch chart-of-accounts mappings, RGS-compatible categories where possible, and rule versioning.",
    },
    {
      id: "layernext_cfo_mobile_insights",
      sourceId: "layernext",
      category: "reporting",
      label: "CFO intelligence, mobile approvals, and deep research",
      serviceSurface: "Cash flow, burn rate, runway, tax-saving tips, reports, mobile exception review, KPI analysis, and board-ready briefings.",
      extractedFrom: ["LayerNext homepage", "Deep Research page"],
      fabImplementation: "Generate close packs, owner dashboards, anomaly explanations, and approval-ready exception summaries.",
      status: "partial",
      requiredCapabilities: ["anomaly_and_health_monitoring", "month_end_close_pack", "missing_document_chase"],
      netherlandsAdaptation: "Include Dutch cash/VAT reserve views, tax deadline reminders, BTW/ICP readiness, and accountant review packs.",
    },
    {
      id: "layernext_trust_metalake",
      sourceId: "layernext",
      category: "security",
      label: "Trust center, governance, and AI-ready data layer",
      serviceSurface: "Customer data isolation, approval before posting, workflow audit trail, business-rule enforcement, data security, AI practices, and MetaLake data unification.",
      extractedFrom: ["LayerNext homepage", "Trust page", "MetaLake page"],
      fabImplementation: "Treat source identity, governance, retention, and auditability as first-class automation inputs rather than afterthoughts.",
      status: "partial",
      requiredCapabilities: ["app_layer_executor", "month_end_close_pack"],
      netherlandsAdaptation: "Apply GDPR controls, Dutch retention periods, source-document lineage, and accountant/client role separation.",
    },
  ],
  benchmarkAreas: [
    {
      id: "inside_accounting_platform_execution",
      label: "Inside-accounting-platform execution",
      competitorPattern: "Agents work directly inside the bookkeeping system and fall back to app-layer automation when APIs stop short.",
      sourceIds: ["booke_ai", "layernext"],
      capabilityIds: ["app_layer_executor", "chat_task_orchestrator"],
      fabStatus: "partial",
      priority: "high",
      nextMilestone: "Expand Wave action manifests with idempotent browser/API execution recipes for every high-volume surface.",
      riskControl: "Require confirmed execution, idempotency keys, screenshots or API receipts, and rollback notes for write actions.",
    },
    {
      id: "continuous_reconciliation",
      label: "Continuous reconciliation",
      competitorPattern: "Bank feeds, documents, and ledger state are reconciled continuously instead of waiting for month-end cleanup.",
      sourceIds: ["booke_ai", "outmin", "layernext"],
      capabilityIds: ["daily_bank_feed_triage", "receipt_to_bank_match", "ledger_report_reconciliation", "month_end_close_pack"],
      fabStatus: "partial",
      priority: "high",
      nextMilestone: "Schedule daily reconciliation planning and publish unresolved match reasons to the review backlog.",
      riskControl: "Auto-reconcile only exact high-confidence matches; partial matches stay review-gated with source evidence.",
    },
    {
      id: "missing_document_chase",
      label: "Missing-document chase",
      competitorPattern: "The system detects missing receipts or context and drafts targeted requests with reminders.",
      sourceIds: ["booke_ai", "outmin", "bookeeping_ai"],
      capabilityIds: ["missing_document_chase"],
      fabStatus: "partial",
      priority: "high",
      nextMilestone: "Connect missing-document tasks to owner contacts, reminder schedules, and safe outbound-message approval.",
      riskControl: "Never send external messages without approval when sensitive financial details or client-facing text are present.",
    },
    {
      id: "ap_approval_workflow",
      label: "AP approval workflow",
      competitorPattern: "Vendor invoices flow through capture, validation, payable drafting, approval, and payment-state controls.",
      sourceIds: ["outmin", "layernext"],
      capabilityIds: ["ap_invoice_workflow", "document_capture_and_ocr", "vendor_category_learning"],
      fabStatus: "partial",
      priority: "high",
      nextMilestone: "Add approval-policy rules for vendor, amount, due date, PO/contract match, and payment marking.",
      riskControl: "Block payment marking and high-value payable changes until an approval policy has explicitly cleared them.",
    },
    {
      id: "operator_control_center",
      label: "Operator control center",
      competitorPattern: "Operators get one control surface for every client, reconciliation, exception, source document, and close state.",
      sourceIds: ["outmin", "booke_ai"],
      capabilityIds: [
        "daily_bank_feed_triage",
        "receipt_to_bank_match",
        "ledger_report_reconciliation",
        "missing_document_chase",
        "month_end_close_pack",
      ],
      fabStatus: "covered",
      priority: "medium",
      nextMilestone: "Add drill-down links from benchmark gaps to the exact review queue, Wave surface, and audit events.",
      riskControl: "Keep all autonomous decisions traceable from dashboard cards back to source documents and audit events.",
    },
    {
      id: "deterministic_audit_trail",
      label: "Deterministic audit trail",
      competitorPattern: "AI suggestions are bounded by accounting logic, human review, validation gates, and a full action trail.",
      sourceIds: ["booke_ai", "bookeeping_ai", "layernext"],
      capabilityIds: ["document_capture_and_ocr", "vendor_category_learning", "receipt_to_bank_match", "app_layer_executor"],
      fabStatus: "covered",
      priority: "high",
      nextMilestone: "Attach benchmark area IDs to audit events so every autonomous decision names the risk model it used.",
      riskControl: "Log planned, blocked, reviewed, and completed states with confidence and required signal evidence.",
    },
    {
      id: "chat_task_execution",
      label: "Chat task execution",
      competitorPattern: "Owners can ask for bookkeeping actions in natural language and receive validated execution plans.",
      sourceIds: ["bookeeping_ai", "layernext"],
      capabilityIds: ["chat_task_orchestrator", "app_layer_executor"],
      fabStatus: "planned",
      priority: "medium",
      nextMilestone: "Expose a chat-to-plan endpoint that maps user intent to Wave action plans and review gates.",
      riskControl: "Treat chat requests as planning input only until target records, required fields, and confirmations are resolved.",
    },
    {
      id: "bank_statement_import_formats",
      label: "Bank statement import formats",
      competitorPattern: "CSV, MT940, CAMT, PDF, and payment-provider exports can be imported when direct feeds are unavailable.",
      sourceIds: ["bookeeping_ai"],
      capabilityIds: ["daily_bank_feed_triage", "receipt_to_bank_match"],
      fabStatus: "planned",
      priority: "medium",
      nextMilestone: "Add parser adapters for common bank export formats and normalize them into the reconciliation queue.",
      riskControl: "Require account mapping, opening/closing balance validation, and duplicate import fingerprints before posting.",
    },
    {
      id: "business_health_monitoring",
      label: "Business health monitoring",
      competitorPattern: "The bookkeeper watches for anomalies, cash-flow drift, stale feeds, and unusual expense behavior.",
      sourceIds: ["bookeeping_ai", "layernext"],
      capabilityIds: ["anomaly_and_health_monitoring", "month_end_close_pack"],
      fabStatus: "partial",
      priority: "medium",
      nextMilestone: "Turn health signals into actionable review tasks with owner-visible severity and recommended evidence.",
      riskControl: "Keep recommendations advisory unless a human confirms tax-sensitive or cash-management decisions.",
    },
    {
      id: "custom_workflow_rules",
      label: "Custom workflow rules",
      competitorPattern: "Agents learn client-specific business rules and route exceptions through configurable workflows.",
      sourceIds: ["booke_ai", "layernext"],
      capabilityIds: ["vendor_category_learning", "app_layer_executor"],
      fabStatus: "partial",
      priority: "medium",
      nextMilestone: "Persist user-defined rules for vendors, categories, Wave actions, approval thresholds, and exception routing.",
      riskControl: "Version every rule change and replay it in dry-run mode before it is allowed to affect live write actions.",
    },
  ],
} as const satisfies AutonomousBookkeeperPlaybook;

export function getAutonomousBookkeeperPlaybook(): AutonomousBookkeeperPlaybook {
  return autonomousBookkeeperPlaybook;
}

export function findAutomationCapability(capabilityId: string): AutomationCapability | undefined {
  return autonomousBookkeeperPlaybook.capabilities.find((capability) => capability.id === capabilityId);
}

export function getAutomationCapabilitiesForStage(stageId: AutomationStageId): AutomationCapability[] {
  return autonomousBookkeeperPlaybook.capabilities.filter((capability) => capability.stageId === stageId);
}

export function getAutomationPlaybookSummary() {
  const capabilitiesByStage = autonomousBookkeeperPlaybook.stages.reduce<Record<AutomationStageId, number>>(
    (acc, stage) => {
      acc[stage.id] = getAutomationCapabilitiesForStage(stage.id).length;
      return acc;
    },
    {
      collect: 0,
      extract_validate: 0,
      classify_post: 0,
      match_reconcile: 0,
      exception_chase: 0,
      close_report: 0,
      learn_optimize: 0,
      system_execute: 0,
    }
  );

  const capabilitiesByAutonomy = autonomousBookkeeperPlaybook.capabilities.reduce<Record<AutomationAutonomyLevel, number>>(
    (acc, capability) => {
      acc[capability.autonomyLevel] += 1;
      return acc;
    },
    {
      observe: 0,
      prepare: 0,
      safe_draft: 0,
      review_required: 0,
      confirmed_execute: 0,
    }
  );

  const benchmarkByStatus = autonomousBookkeeperPlaybook.benchmarkAreas.reduce<Record<AutomationBenchmarkStatus, number>>(
    (acc, area) => {
      acc[area.fabStatus] += 1;
      return acc;
    },
    {
      covered: 0,
      partial: 0,
      planned: 0,
    }
  );

  const servicesByStatus = autonomousBookkeeperPlaybook.serviceOfferings.reduce<Record<AutomationServiceStatus, number>>(
    (acc, service) => {
      acc[service.status] += 1;
      return acc;
    },
    {
      modeled: 0,
      partial: 0,
      planned: 0,
    }
  );

  const servicesByCategory = autonomousBookkeeperPlaybook.serviceOfferings.reduce<
    Record<AutomationServiceCategory, number>
  >(
    (acc, service) => {
      acc[service.category] += 1;
      return acc;
    },
    {
      capture: 0,
      bookkeeping: 0,
      reconciliation: 0,
      accounts_payable: 0,
      client_workflow: 0,
      reporting: 0,
      compliance: 0,
      security: 0,
      platform: 0,
    }
  );

  const servicesBySource = autonomousBookkeeperPlaybook.serviceOfferings.reduce<Record<AutomationSourceId, number>>(
    (acc, service) => {
      acc[service.sourceId] += 1;
      return acc;
    },
    {
      booke_ai: 0,
      outmin: 0,
      bookeeping_ai: 0,
      layernext: 0,
    }
  );

  return {
    sources: autonomousBookkeeperPlaybook.sources.length,
    stages: autonomousBookkeeperPlaybook.stages.length,
    capabilities: autonomousBookkeeperPlaybook.capabilities.length,
    serviceOfferings: autonomousBookkeeperPlaybook.serviceOfferings.length,
    servicesByStatus,
    servicesByCategory,
    servicesBySource,
    benchmarkAreas: autonomousBookkeeperPlaybook.benchmarkAreas.length,
    benchmarkByStatus,
    highPriorityBenchmarkGaps: autonomousBookkeeperPlaybook.benchmarkAreas.filter(
      (area) => area.priority === "high" && area.fabStatus !== "covered"
    ).length,
    waveLinkedCapabilities: autonomousBookkeeperPlaybook.capabilities.filter(
      (capability) => capability.waveActions.length > 0
    ).length,
    capabilitiesByStage,
    capabilitiesByAutonomy,
  };
}

export function planAutomationCapability(input: {
  capabilityId: string;
  availableSignals?: string[];
  confidence?: number;
  approvals?: string[];
}): AutomationCapabilityPlan {
  const capability = findAutomationCapability(input.capabilityId);
  if (!capability) {
    return {
      status: "blocked_by_review",
      missingSignals: [],
      reviewGates: ["unknown capability"],
      canRunAutonomously: false,
      recommendedMode: "review_required",
      nextAction: "Route to manual review because the requested automation capability is not modeled.",
    };
  }

  const availableSignals = new Set(input.availableSignals || []);
  const missingSignals = capability.requiredSignals.filter((signal) => !availableSignals.has(signal));
  const approvals = new Set(input.approvals || []);
  const unresolvedReviewGates = capability.reviewGates.filter((gate) => !approvals.has(gate));
  const confidence = input.confidence ?? 1;
  const lowConfidence = confidence < 0.85;
  const intrinsicallyAutonomous = ["observe", "prepare", "safe_draft"].includes(capability.autonomyLevel);
  const canRunAutonomously =
    missingSignals.length === 0 &&
    intrinsicallyAutonomous &&
    !lowConfidence &&
    capability.autonomyLevel !== "review_required";

  if (missingSignals.length > 0) {
    return {
      status: "needs_signals",
      capability,
      missingSignals,
      reviewGates: unresolvedReviewGates,
      canRunAutonomously: false,
      recommendedMode: "prepare",
      nextAction: `Collect missing signals: ${missingSignals.join(", ")}.`,
    };
  }

  if (!canRunAutonomously) {
    return {
      status: "blocked_by_review",
      capability,
      missingSignals: [],
      reviewGates: lowConfidence ? ["confidence below 85%", ...unresolvedReviewGates] : unresolvedReviewGates,
      canRunAutonomously: false,
      recommendedMode: capability.autonomyLevel,
      nextAction: "Prepare the work item and route it through the review gate before posting or sending.",
    };
  }

  return {
    status: "ready",
    capability,
    missingSignals: [],
    reviewGates: unresolvedReviewGates,
    canRunAutonomously: true,
    recommendedMode: capability.autonomyLevel,
    nextAction: "Run the capability through the policy-gated autonomous operator.",
  };
}

export type AutomationWorkflowId = "daily_reconciliation_run" | "period_close_pack" | "mijngeldzaken_master_ledger_sync";

export type AutomationWorkflowPlanStep = {
  id: string;
  label: string;
  targetSystem: "waveapps" | "mijngeldzaken";
  capabilityId: string;
  surfaceId: string;
  actionId: string;
  payload: Record<string, string | boolean>;
  purpose: string;
  safety: "read_only" | "safe_draft" | "requires_confirmation" | "requires_credentials" | "unsupported";
};

export type AutomationWorkflowPlan = {
  workflowId: AutomationWorkflowId;
  status: "ready" | "needs_signals" | "blocked_by_review";
  canRunAutonomously: boolean;
  requiredSignals: string[];
  missingSignals: string[];
  reviewGates: string[];
  capabilityPlans: AutomationCapabilityPlan[];
  steps: AutomationWorkflowPlanStep[];
  nextAction: string;
};

export type AutomationWorkflowPlanInput = {
  workflowId: AutomationWorkflowId;
  fromDate: string;
  toDate: string;
  asOfDate?: string;
  accountOption?: string;
  accountName?: string;
  contactOption?: string;
  contactName?: string;
  cashMode?: string;
  includeExports?: boolean;
  availableSignals?: string[];
  confidence?: number;
  approvals?: string[];
};

function uniqueStrings(values: string[]): string[] {
  return Array.from(new Set(values.filter(Boolean)));
}

function buildReportPayload(
  input: AutomationWorkflowPlanInput,
  reportType: string,
  extra: Record<string, string | boolean> = {}
): Record<string, string | boolean> {
  return {
    reportType,
    fromDate: input.fromDate,
    toDate: input.toDate,
    asOfDate: input.asOfDate || input.toDate,
    basis: input.cashMode || "accrual",
    accountOption: input.accountOption || "-1",
    accountName: input.accountName || "All Accounts",
    contactOption: input.contactOption || "0",
    contactName: input.contactName || "All Contacts",
    cashMode: input.cashMode || "1",
    ...extra,
  };
}

function buildDailyReconciliationSteps(input: AutomationWorkflowPlanInput): AutomationWorkflowPlanStep[] {
  const payload = buildReportPayload(input, "account-transactions");
  const steps: AutomationWorkflowPlanStep[] = [
    {
      id: "open_account_transactions_report",
      label: "Open Account Transactions report",
      targetSystem: "waveapps",
      capabilityId: "ledger_report_reconciliation",
      surfaceId: "reports",
      actionId: "report_open",
      payload,
      purpose: "Load Wave's source-of-truth general ledger detail for the target reconciliation period.",
      safety: "read_only",
    },
    {
      id: "scope_account_transactions_by_account",
      label: "Scope ledger by account",
      targetSystem: "waveapps",
      capabilityId: "ledger_report_reconciliation",
      surfaceId: "reports",
      actionId: "report_account_filter_select",
      payload,
      purpose: "Select the account scope that should reconcile to bank/source activity.",
      safety: "read_only",
    },
    {
      id: "scope_account_transactions_by_contact",
      label: "Scope ledger by contact",
      targetSystem: "waveapps",
      capabilityId: "ledger_report_reconciliation",
      surfaceId: "reports",
      actionId: "report_contact_filter_select",
      payload,
      purpose: "Limit ledger evidence to a customer/vendor/contact when the reconciliation task is contact-specific.",
      safety: "read_only",
    },
    {
      id: "set_ledger_report_period",
      label: "Set ledger report period",
      targetSystem: "waveapps",
      capabilityId: "ledger_report_reconciliation",
      surfaceId: "reports",
      actionId: "report_date_range_set",
      payload,
      purpose: "Apply the date window that defines the autonomous reconciliation run.",
      safety: "read_only",
    },
    {
      id: "select_ledger_report_basis",
      label: "Select ledger report basis",
      targetSystem: "waveapps",
      capabilityId: "ledger_report_reconciliation",
      surfaceId: "reports",
      actionId: "report_basis_select",
      payload,
      purpose: "Align Wave's report basis with the reconciliation policy.",
      safety: "read_only",
    },
    {
      id: "refresh_ledger_report",
      label: "Update ledger report",
      targetSystem: "waveapps",
      capabilityId: "ledger_report_reconciliation",
      surfaceId: "reports",
      actionId: "report_update",
      payload,
      purpose: "Refresh the Wave report after applying account, contact, period, and basis filters.",
      safety: "read_only",
    },
    {
      id: "read_ledger_rows",
      label: "Read ledger rows",
      targetSystem: "waveapps",
      capabilityId: "ledger_report_reconciliation",
      surfaceId: "reports",
      actionId: "report_table_read",
      payload,
      purpose: "Extract visible ledger rows/totals for match evidence and exception detection.",
      safety: "read_only",
    },
    {
      id: "detect_empty_ledger_scope",
      label: "Detect empty ledger scope",
      targetSystem: "waveapps",
      capabilityId: "ledger_report_reconciliation",
      surfaceId: "reports",
      actionId: "report_empty_state_read",
      payload,
      purpose: "Detect no-result report scopes so FAB can widen filters or create a review item.",
      safety: "read_only",
    },
  ];

  if (input.includeExports !== false) {
    steps.push({
      id: "export_ledger_evidence",
      label: "Export ledger evidence",
      targetSystem: "waveapps",
      capabilityId: "ledger_report_reconciliation",
      surfaceId: "reports",
      actionId: "report_export",
      payload: buildReportPayload(input, "account-transactions", { format: "csv" }),
      purpose: "Produce machine-readable evidence for the reconciliation audit trail.",
      safety: "read_only",
    });
  }

  return steps;
}

function buildPeriodCloseSteps(input: AutomationWorkflowPlanInput): AutomationWorkflowPlanStep[] {
  const closeReports = [
    "profit-and-loss",
    "balance-sheet",
    "cash-flow",
    "sales-tax",
    "aged-receivables",
    "aged-payables",
    "account-balances",
    "trial-balance",
  ];

  const reportSteps = closeReports.flatMap((reportType) => [
    {
      id: `open_${reportType}_report`,
      label: `Open ${reportType} report`,
      targetSystem: "waveapps" as const,
      capabilityId: "month_end_close_pack",
      surfaceId: "reports",
      actionId: "report_open",
      payload: buildReportPayload(input, reportType),
      purpose: "Load a Wave close-pack report for the target period.",
      safety: "read_only" as const,
    },
    {
      id: `export_${reportType}_report`,
      label: `Export ${reportType} report`,
      targetSystem: "waveapps" as const,
      capabilityId: "month_end_close_pack",
      surfaceId: "reports",
      actionId: "report_export",
      payload: buildReportPayload(input, reportType, { format: "pdf" }),
      purpose: "Capture close-pack evidence for accountant/owner review.",
      safety: "read_only" as const,
    },
  ]);

  return [...buildDailyReconciliationSteps({ ...input, includeExports: true }), ...reportSteps];
}

function buildMijngeldzakenMasterLedgerSteps(input: AutomationWorkflowPlanInput): AutomationWorkflowPlanStep[] {
  const dateRange = `${input.fromDate}:${input.toDate}`;
  const transactionPayload = {
    date: input.toDate,
    amount: "0",
    description: "FAB approved master-ledger import batch",
    category: "Huishouden",
    account: "Huishouden",
    dateRange,
  };

  return [
    {
      id: "read_mijngeldzaken_current_month",
      label: "Read MijnGeldzaken current month",
      targetSystem: "mijngeldzaken",
      capabilityId: "ledger_report_reconciliation",
      surfaceId: "current_month",
      actionId: "current_month_read",
      payload: {
        fromDate: input.fromDate,
        toDate: input.toDate,
      },
      purpose: "Read household ledger status before syncing approved FAB Category A entries.",
      safety: "read_only",
    },
    {
      id: "read_mijngeldzaken_categories",
      label: "Read MijnGeldzaken categories",
      targetSystem: "mijngeldzaken",
      capabilityId: "vendor_category_learning",
      surfaceId: "categories",
      actionId: "category_list_read",
      payload: {
        dateRange,
      },
      purpose: "Pull category names used by the downstream household ledger for mapping and learning.",
      safety: "read_only",
    },
    {
      id: "prepare_mijngeldzaken_category_mapping",
      label: "Prepare category mapping",
      targetSystem: "mijngeldzaken",
      capabilityId: "vendor_category_learning",
      surfaceId: "categories",
      actionId: "category_mapping_prepare",
      payload: {
        sourceCategory: "Personal",
        targetCategory: "Huishouden",
      },
      purpose: "Prepare a local mapping from FAB Category A/personal records to MijnGeldzaken household categories.",
      safety: "safe_draft",
    },
    {
      id: "prepare_mijngeldzaken_transaction_import",
      label: "Prepare transaction import",
      targetSystem: "mijngeldzaken",
      capabilityId: "app_layer_executor",
      surfaceId: "transactions",
      actionId: "transaction_import_prepare",
      payload: transactionPayload,
      purpose: "Prepare the approved FAB master-ledger batch for MijnGeldzaken import without submitting it externally.",
      safety: "safe_draft",
    },
    {
      id: "prepare_mijngeldzaken_receipt_upload",
      label: "Prepare receipt upload",
      targetSystem: "mijngeldzaken",
      capabilityId: "document_capture_and_ocr",
      surfaceId: "receipts",
      actionId: "receipt_upload_prepare",
      payload: {
        documentId: "fab-master-ledger-batch",
        filename: "fab-master-ledger-evidence.zip",
        dateRange,
      },
      purpose: "Prepare supporting receipt/evidence upload for the downstream household ledger.",
      safety: "safe_draft",
    },
  ];
}

export function planAutomationWorkflow(input: AutomationWorkflowPlanInput): AutomationWorkflowPlan {
  const capabilities =
    input.workflowId === "mijngeldzaken_master_ledger_sync"
      ? ["ledger_report_reconciliation", "vendor_category_learning", "document_capture_and_ocr"]
      : input.workflowId === "period_close_pack"
      ? ["ledger_report_reconciliation", "month_end_close_pack", "anomaly_and_health_monitoring"]
      : ["ledger_report_reconciliation", "receipt_to_bank_match"];
  const capabilityPlans = capabilities.map((capabilityId) =>
    planAutomationCapability({
      capabilityId,
      availableSignals: input.availableSignals,
      confidence: input.confidence,
      approvals: input.approvals,
    })
  );
  const requiredSignals = uniqueStrings(
    capabilityPlans.flatMap((plan) => plan.capability?.requiredSignals || [])
  );
  const missingSignals = uniqueStrings(capabilityPlans.flatMap((plan) => plan.missingSignals));
  const reviewGates = uniqueStrings(capabilityPlans.flatMap((plan) => plan.reviewGates));
  const blocked = capabilityPlans.some((plan) => plan.status === "blocked_by_review");
  const needsSignals = capabilityPlans.some((plan) => plan.status === "needs_signals");
  const status = blocked ? "blocked_by_review" : needsSignals ? "needs_signals" : "ready";
  const steps =
    input.workflowId === "mijngeldzaken_master_ledger_sync"
      ? buildMijngeldzakenMasterLedgerSteps(input)
      : input.workflowId === "period_close_pack"
        ? buildPeriodCloseSteps(input)
        : buildDailyReconciliationSteps(input);

  return {
    workflowId: input.workflowId,
    status,
    canRunAutonomously: status === "ready" && steps.every((step) => step.safety === "read_only" || step.safety === "safe_draft"),
    requiredSignals,
    missingSignals,
    reviewGates,
    capabilityPlans,
    steps,
    nextAction:
      status === "ready"
        ? "Queue this workflow through the policy-gated autonomous executor."
        : missingSignals.length
          ? `Collect missing signals: ${missingSignals.join(", ")}.`
          : "Prepare the workflow and route unresolved review gates before execution.",
  };
}
