export type MijngeldzakenModuleId =
  | "access"
  | "overview"
  | "master_ledger"
  | "documents"
  | "planning"
  | "reports"
  | "settings";

export type MijngeldzakenActionSafety =
  | "read_only"
  | "safe_draft"
  | "requires_confirmation"
  | "requires_credentials";

export type MijngeldzakenAutomationMode =
  | "observe"
  | "read_only"
  | "safe_draft"
  | "requires_user_auth";

export type MijngeldzakenModule = {
  id: MijngeldzakenModuleId;
  label: string;
  surfaces: string[];
};

export type MijngeldzakenControl = {
  label: string;
  kind: "page" | "link" | "button" | "input" | "table" | "import" | "form" | "status" | "summary" | "report" | "download" | "upload" | "mapping" | "period";
  safety: MijngeldzakenActionSafety;
  actionId: string;
};

export type MijngeldzakenFeaturePage = {
  id: string;
  surfaceId: string;
  moduleId: MijngeldzakenModuleId;
  label: string;
  observedFrom?: string;
  automationMode: MijngeldzakenAutomationMode;
  controls: MijngeldzakenControl[];
  reviewGate: string;
  fabCoverage: string[];
};

export type MijngeldzakenAction = {
  id: string;
  surfaceId: string;
  label: string;
  mode: "auth" | "read" | "import" | "write" | "sync" | "map" | "upload" | "export";
  safety: MijngeldzakenActionSafety;
  requiredFields: string[];
  result: string;
  workflowNotes: string;
};

export type MijngeldzakenSyncContract = {
  id: string;
  domain: string;
  fabOwns: string[];
  mijngeldzakenOwns: string[];
  pullFromMijngeldzaken: string[];
  pushToMijngeldzaken: string[];
  conflictResolution: string;
  confirmationRequiredFor: string[];
};

export type MijngeldzakenSurfaceCatalog = {
  source: "mijngeldzaken_ui_inspection";
  capturedFrom: string;
  modules: MijngeldzakenModule[];
  syncContracts: MijngeldzakenSyncContract[];
  featureInventory: MijngeldzakenFeaturePage[];
  actions: MijngeldzakenAction[];
};

export const mijngeldzakenImportColumns = [
  "Datum",
  "Omschrijving",
  "Tegenpartij",
  "Bedrag",
  "Categorie",
  "Rekening",
  "Valuta",
  "FAB Document ID",
] as const;

export type MijngeldzakenMasterLedgerDraft =
  | {
      draftType: "transaction_import";
      targetSystem: "mijngeldzaken";
      surfaceId: string;
      actionId: string;
      exportFormat: "csv";
      columns: typeof mijngeldzakenImportColumns;
      importRow: Record<string, unknown>;
      sourceProof: Record<string, unknown>;
      checksum: string;
      externalSubmission: "not_executed";
    }
  | {
      draftType: "document_upload";
      targetSystem: "mijngeldzaken";
      surfaceId: string;
      actionId: string;
      uploadDraft: Record<string, unknown>;
      sourceProof: Record<string, unknown>;
      checksum: string;
      externalSubmission: "not_executed";
    }
  | {
      draftType: "mapping";
      targetSystem: "mijngeldzaken";
      surfaceId: string;
      actionId: string;
      mappingDraft: Record<string, unknown>;
      sourceProof: Record<string, unknown>;
      checksum: string;
      externalSubmission: "not_executed";
    };

export const mijngeldzakenSurfaceCatalog: MijngeldzakenSurfaceCatalog = {
  source: "mijngeldzaken_ui_inspection",
  capturedFrom:
    "MijnGeldzaken login and authenticated household-bookkeeping sidebar/current-month surfaces inspected read-only on 2026-06-30",
  modules: [
    {
      id: "access",
      label: "Access",
      surfaces: ["login", "profile_security"],
    },
    {
      id: "overview",
      label: "Overview",
      surfaces: ["dashboard", "current_month", "trends", "income", "expenses", "net_worth", "alerts"],
    },
    {
      id: "master_ledger",
      label: "Master Ledger",
      surfaces: ["transactions", "accounts", "categories", "budgets"],
    },
    {
      id: "documents",
      label: "Documents",
      surfaces: ["document_vault", "receipts", "payslips", "contracts"],
    },
    {
      id: "planning",
      label: "Planning",
      surfaces: ["goals", "scenarios", "mortgage_planning", "pension_planning"],
    },
    {
      id: "reports",
      label: "Reports",
      surfaces: ["reports", "exports"],
    },
    {
      id: "settings",
      label: "Settings",
      surfaces: ["settings", "imports"],
    },
  ],
  syncContracts: [
    {
      id: "fab_master_ledger_to_mijngeldzaken",
      domain: "Household and Category A personal ledger",
      fabOwns: [
        "source document identity",
        "canonical transaction identity",
        "category decision",
        "duplicate and reconciliation evidence",
        "master-ledger export approval",
      ],
      mijngeldzakenOwns: [
        "household account balances",
        "budget views",
        "planning calculations",
        "document vault records",
      ],
      pullFromMijngeldzaken: [
        "historical household categories",
        "budget reports",
        "account-update prompts",
        "document-vault status",
      ],
      pushToMijngeldzaken: [
        "approved transaction import rows",
        "approved receipt/document upload drafts",
        "approved category mappings",
      ],
      conflictResolution:
        "FAB remains the canonical approval and audit ledger; MijnGeldzaken is a downstream household-planning and budget surface.",
      confirmationRequiredFor: [
        "submit import",
        "edit external transaction",
        "delete external transaction",
        "change account or security settings",
      ],
    },
    {
      id: "mijngeldzaken_to_fab_learning",
      domain: "Learning from historical household bookkeeping",
      fabOwns: ["learned vendor/category rules", "mapping history", "review queue"],
      mijngeldzakenOwns: ["historical household categories", "budget reports"],
      pullFromMijngeldzaken: ["category exports", "transaction exports", "budget trends"],
      pushToMijngeldzaken: ["approved learned-rule import drafts"],
      conflictResolution:
        "Imported history trains FAB suggestions only; automatic future use requires confidence and review-gate policy.",
      confirmationRequiredFor: ["use learned rule automatically", "overwrite existing rule"],
    },
  ],
  featureInventory: [
    {
      id: "login_page",
      surfaceId: "login",
      moduleId: "access",
      label: "Login",
      observedFrom: "https://www.mijngeldzaken.nl/account/login",
      automationMode: "requires_user_auth",
      controls: [
        { label: "E-mailadres", kind: "input", safety: "requires_credentials", actionId: "login_email_fill" },
        { label: "Wachtwoord", kind: "input", safety: "requires_credentials", actionId: "login_password_fill" },
        { label: "Inloggen", kind: "button", safety: "requires_credentials", actionId: "login_submit" },
        { label: "Wachtwoord vergeten", kind: "link", safety: "read_only", actionId: "password_reset_open" },
        { label: "Start nu gratis", kind: "link", safety: "read_only", actionId: "register_open" },
      ],
      reviewGate: "FAB never stores or types credentials from chat; user-owned sign-in is required.",
      fabCoverage: ["credential gate", "read-only authenticated inspection", "manual session handoff"],
    },
    {
      id: "authenticated_sidebar_navigation",
      surfaceId: "dashboard",
      moduleId: "overview",
      label: "Authenticated Sidebar Navigation",
      observedFrom: "https://mijnhuishoudboekje.mijngeldzaken.nl/",
      automationMode: "observe",
      controls: [
        { label: "Dashboard", kind: "link", safety: "read_only", actionId: "dashboard_open" },
        { label: "Deze maand", kind: "page", safety: "read_only", actionId: "current_month_read" },
        { label: "Trends", kind: "page", safety: "read_only", actionId: "trend_report_read" },
        { label: "Inkomsten", kind: "page", safety: "read_only", actionId: "income_overview_read" },
        { label: "Uitgaven", kind: "page", safety: "read_only", actionId: "expense_overview_read" },
        { label: "Transacties", kind: "page", safety: "read_only", actionId: "transaction_list_read" },
        { label: "Budgetten", kind: "page", safety: "read_only", actionId: "budget_list_read" },
        { label: "Contracten", kind: "page", safety: "read_only", actionId: "contract_list_read" },
        { label: "Bonnetjes", kind: "page", safety: "read_only", actionId: "receipt_list_read" },
        { label: "Loonstroken", kind: "page", safety: "read_only", actionId: "payslip_list_read" },
        { label: "Help", kind: "button", safety: "read_only", actionId: "help_open" },
      ],
      reviewGate: "Navigation and help are read-only; FAB models page contracts before external writes.",
      fabCoverage: ["sidebar model", "read-only page contracts", "operator route inventory"],
    },
    {
      id: "current_month_dashboard",
      surfaceId: "current_month",
      moduleId: "overview",
      label: "Current Month",
      observedFrom: "https://mijnhuishoudboekje.mijngeldzaken.nl/",
      automationMode: "observe",
      controls: [
        { label: "Financial month heading", kind: "period", safety: "read_only", actionId: "current_month_read" },
        { label: "Previous period", kind: "button", safety: "read_only", actionId: "period_previous" },
        { label: "Next period", kind: "button", safety: "read_only", actionId: "period_next" },
        { label: "Inkomsten panel", kind: "summary", safety: "read_only", actionId: "income_overview_read" },
        { label: "Uitgaven panel", kind: "summary", safety: "read_only", actionId: "expense_overview_read" },
        { label: "Rekeningen bijwerken prompt", kind: "status", safety: "read_only", actionId: "account_update_prompt_read" },
      ],
      reviewGate: "FAB may read monthly status and account-update prompts; account refresh requires explicit user action.",
      fabCoverage: ["monthly status read", "income/expense read contracts", "account-refresh warning"],
    },
    {
      id: "household_bookkeeping",
      surfaceId: "transactions",
      moduleId: "master_ledger",
      label: "Household Transactions",
      automationMode: "safe_draft",
      controls: [
        { label: "Transaction list", kind: "table", safety: "read_only", actionId: "transaction_list_read" },
        { label: "Transaction import preview", kind: "import", safety: "safe_draft", actionId: "transaction_import_prepare" },
        { label: "Submit transaction import", kind: "button", safety: "requires_confirmation", actionId: "transaction_import_submit" },
        { label: "Edit transaction", kind: "form", safety: "requires_confirmation", actionId: "transaction_update" },
        { label: "Delete transaction", kind: "button", safety: "requires_confirmation", actionId: "transaction_delete" },
      ],
      reviewGate: "FAB can prepare import rows locally; external submission requires approval.",
      fabCoverage: ["master-ledger transaction import", "category mapping", "approval-gated external writes"],
    },
    {
      id: "document_vault",
      surfaceId: "document_vault",
      moduleId: "documents",
      label: "Documents, Receipts, Payslips, Contracts",
      automationMode: "safe_draft",
      controls: [
        { label: "Document list", kind: "table", safety: "read_only", actionId: "document_list_read" },
        { label: "Contract list", kind: "table", safety: "read_only", actionId: "contract_list_read" },
        { label: "Receipt list", kind: "table", safety: "read_only", actionId: "receipt_list_read" },
        { label: "Payslip list", kind: "table", safety: "read_only", actionId: "payslip_list_read" },
        { label: "Document upload draft", kind: "upload", safety: "safe_draft", actionId: "document_upload_prepare" },
        { label: "Receipt upload draft", kind: "upload", safety: "safe_draft", actionId: "receipt_upload_prepare" },
        { label: "Payslip upload draft", kind: "upload", safety: "safe_draft", actionId: "payslip_upload_prepare" },
        { label: "Submit document upload", kind: "button", safety: "requires_confirmation", actionId: "document_upload_submit" },
        { label: "Submit receipt upload", kind: "button", safety: "requires_confirmation", actionId: "receipt_upload_submit" },
        { label: "Submit payslip upload", kind: "button", safety: "requires_confirmation", actionId: "payslip_upload_submit" },
      ],
      reviewGate: "Document uploads may transmit personal files and require explicit approval.",
      fabCoverage: ["document-vault inventory", "safe upload drafts", "personal document approval gates"],
    },
    {
      id: "budgets_reports_and_exports",
      surfaceId: "reports",
      moduleId: "reports",
      label: "Budgets, Trends, Reports, Exports",
      automationMode: "read_only",
      controls: [
        { label: "Budget report", kind: "report", safety: "read_only", actionId: "budget_report_read" },
        { label: "Budget list", kind: "page", safety: "read_only", actionId: "budget_list_read" },
        { label: "Cashflow report", kind: "report", safety: "read_only", actionId: "cashflow_report_read" },
        { label: "Trend report", kind: "report", safety: "read_only", actionId: "trend_report_read" },
        { label: "Income overview", kind: "report", safety: "read_only", actionId: "income_overview_read" },
        { label: "Expense overview", kind: "report", safety: "read_only", actionId: "expense_overview_read" },
        { label: "Export transactions", kind: "download", safety: "read_only", actionId: "transaction_export_download" },
        { label: "Export categories", kind: "download", safety: "read_only", actionId: "category_export_download" },
      ],
      reviewGate: "Exports feed FAB learning and close controls without modifying MijnGeldzaken.",
      fabCoverage: ["budget/trend read model", "category export learning", "master-ledger evidence pulls"],
    },
  ],
  actions: [
    { id: "login_email_fill", surfaceId: "login", label: "Fill login email", mode: "auth", safety: "requires_credentials", requiredFields: ["email"], result: "Email staged for user-owned sign-in", workflowNotes: "Credentials are never typed autonomously." },
    { id: "login_password_fill", surfaceId: "login", label: "Fill login password", mode: "auth", safety: "requires_credentials", requiredFields: ["password"], result: "Password staged for user-owned sign-in", workflowNotes: "Credentials are never typed autonomously." },
    { id: "login_submit", surfaceId: "login", label: "Submit login", mode: "auth", safety: "requires_credentials", requiredFields: [], result: "Authenticated session", workflowNotes: "Requires user authorization." },
    { id: "password_reset_open", surfaceId: "login", label: "Open password reset", mode: "read", safety: "read_only", requiredFields: [], result: "Password reset page", workflowNotes: "Read-only account recovery navigation." },
    { id: "register_open", surfaceId: "login", label: "Open registration", mode: "read", safety: "read_only", requiredFields: [], result: "Registration page", workflowNotes: "Read-only registration navigation." },
    { id: "dashboard_open", surfaceId: "dashboard", label: "Open dashboard", mode: "read", safety: "read_only", requiredFields: [], result: "Dashboard visible", workflowNotes: "Read-only navigation." },
    { id: "help_open", surfaceId: "dashboard", label: "Open help", mode: "read", safety: "read_only", requiredFields: [], result: "Help panel", workflowNotes: "Read-only support navigation." },
    { id: "current_month_read", surfaceId: "current_month", label: "Read current month", mode: "read", safety: "read_only", requiredFields: [], result: "Monthly status", workflowNotes: "No private amounts are logged by default." },
    { id: "period_previous", surfaceId: "current_month", label: "Previous period", mode: "read", safety: "read_only", requiredFields: [], result: "Previous month selected", workflowNotes: "Read-only period navigation." },
    { id: "period_next", surfaceId: "current_month", label: "Next period", mode: "read", safety: "read_only", requiredFields: [], result: "Next month selected", workflowNotes: "Read-only period navigation." },
    { id: "account_update_prompt_read", surfaceId: "current_month", label: "Read account update prompt", mode: "read", safety: "read_only", requiredFields: [], result: "Account update status", workflowNotes: "Account refresh is not autonomous." },
    { id: "trend_report_read", surfaceId: "trends", label: "Read trends", mode: "read", safety: "read_only", requiredFields: [], result: "Trend report", workflowNotes: "Read-only reporting." },
    { id: "income_overview_read", surfaceId: "income", label: "Read income", mode: "read", safety: "read_only", requiredFields: [], result: "Income overview", workflowNotes: "Read-only reporting." },
    { id: "expense_overview_read", surfaceId: "expenses", label: "Read expenses", mode: "read", safety: "read_only", requiredFields: [], result: "Expense overview", workflowNotes: "Read-only reporting." },
    { id: "transaction_list_read", surfaceId: "transactions", label: "Read transactions", mode: "read", safety: "read_only", requiredFields: [], result: "Transaction list", workflowNotes: "Read-only master-ledger pull." },
    { id: "transaction_import_prepare", surfaceId: "transactions", label: "Prepare transaction import", mode: "import", safety: "safe_draft", requiredFields: ["date", "amount", "description", "category"], result: "Import row draft", workflowNotes: "FAB prepares import rows locally before approval." },
    { id: "transaction_import_submit", surfaceId: "transactions", label: "Submit transaction import", mode: "import", safety: "requires_confirmation", requiredFields: ["importBatchId"], result: "External import submitted", workflowNotes: "External state change requires approval." },
    { id: "transaction_update", surfaceId: "transactions", label: "Update transaction", mode: "write", safety: "requires_confirmation", requiredFields: ["transactionId", "changes"], result: "Transaction updated", workflowNotes: "External state change requires approval." },
    { id: "transaction_delete", surfaceId: "transactions", label: "Delete transaction", mode: "write", safety: "requires_confirmation", requiredFields: ["transactionId"], result: "Transaction deleted", workflowNotes: "Destructive action requires approval." },
    { id: "account_list_read", surfaceId: "accounts", label: "Read accounts", mode: "read", safety: "read_only", requiredFields: [], result: "Account list", workflowNotes: "Read-only account inventory." },
    { id: "account_balance_read", surfaceId: "accounts", label: "Read account balances", mode: "read", safety: "read_only", requiredFields: [], result: "Account balances", workflowNotes: "Read-only balance evidence." },
    { id: "account_update_start", surfaceId: "accounts", label: "Start account update", mode: "sync", safety: "requires_confirmation", requiredFields: ["accountId"], result: "Account refresh started", workflowNotes: "Bank/account sync requires user approval." },
    { id: "category_list_read", surfaceId: "categories", label: "Read categories", mode: "read", safety: "read_only", requiredFields: [], result: "Category list", workflowNotes: "Used for FAB mapping and learning." },
    { id: "category_mapping_prepare", surfaceId: "categories", label: "Prepare category mapping", mode: "map", safety: "safe_draft", requiredFields: ["sourceCategory", "targetCategory"], result: "Category mapping draft", workflowNotes: "Local mapping draft only." },
    { id: "category_update", surfaceId: "categories", label: "Update category", mode: "write", safety: "requires_confirmation", requiredFields: ["categoryId", "changes"], result: "Category updated", workflowNotes: "External state change requires approval." },
    { id: "budget_report_read", surfaceId: "reports", label: "Read budget report", mode: "read", safety: "read_only", requiredFields: [], result: "Budget report", workflowNotes: "Read-only report evidence." },
    { id: "budget_list_read", surfaceId: "budgets", label: "Read budgets", mode: "read", safety: "read_only", requiredFields: [], result: "Budget list", workflowNotes: "Read-only budget inventory." },
    { id: "cashflow_report_read", surfaceId: "reports", label: "Read cashflow", mode: "read", safety: "read_only", requiredFields: [], result: "Cashflow report", workflowNotes: "Read-only report evidence." },
    { id: "transaction_export_download", surfaceId: "exports", label: "Download transactions export", mode: "export", safety: "read_only", requiredFields: ["dateRange"], result: "Transaction export", workflowNotes: "Feeds FAB learning and audit evidence." },
    { id: "category_export_download", surfaceId: "exports", label: "Download categories export", mode: "export", safety: "read_only", requiredFields: [], result: "Category export", workflowNotes: "Feeds FAB category learning." },
    { id: "document_list_read", surfaceId: "document_vault", label: "Read documents", mode: "read", safety: "read_only", requiredFields: [], result: "Document list", workflowNotes: "Read-only document vault inventory." },
    { id: "contract_list_read", surfaceId: "contracts", label: "Read contracts", mode: "read", safety: "read_only", requiredFields: [], result: "Contract list", workflowNotes: "Read-only contract inventory." },
    { id: "receipt_list_read", surfaceId: "receipts", label: "Read receipts", mode: "read", safety: "read_only", requiredFields: [], result: "Receipt list", workflowNotes: "Read-only receipt inventory." },
    { id: "payslip_list_read", surfaceId: "payslips", label: "Read payslips", mode: "read", safety: "read_only", requiredFields: [], result: "Payslip list", workflowNotes: "Read-only payslip inventory." },
    { id: "document_upload_prepare", surfaceId: "document_vault", label: "Prepare document upload", mode: "upload", safety: "safe_draft", requiredFields: ["documentId", "filename"], result: "Document upload draft", workflowNotes: "Local upload draft before approval." },
    { id: "receipt_upload_prepare", surfaceId: "receipts", label: "Prepare receipt upload", mode: "upload", safety: "safe_draft", requiredFields: ["documentId", "filename"], result: "Receipt upload draft", workflowNotes: "Local upload draft before approval." },
    { id: "payslip_upload_prepare", surfaceId: "payslips", label: "Prepare payslip upload", mode: "upload", safety: "safe_draft", requiredFields: ["documentId", "filename"], result: "Payslip upload draft", workflowNotes: "Local upload draft before approval." },
    { id: "document_upload_submit", surfaceId: "document_vault", label: "Submit document upload", mode: "upload", safety: "requires_confirmation", requiredFields: ["uploadDraftId"], result: "Document uploaded", workflowNotes: "External file transfer requires approval." },
    { id: "receipt_upload_submit", surfaceId: "receipts", label: "Submit receipt upload", mode: "upload", safety: "requires_confirmation", requiredFields: ["uploadDraftId"], result: "Receipt uploaded", workflowNotes: "External file transfer requires approval." },
    { id: "payslip_upload_submit", surfaceId: "payslips", label: "Submit payslip upload", mode: "upload", safety: "requires_confirmation", requiredFields: ["uploadDraftId"], result: "Payslip uploaded", workflowNotes: "External file transfer requires approval." },
  ],
};

export function getMijngeldzakenSurfaceCatalog(): MijngeldzakenSurfaceCatalog {
  return mijngeldzakenSurfaceCatalog;
}

export function findMijngeldzakenAction(actionId: string): MijngeldzakenAction | undefined {
  return mijngeldzakenSurfaceCatalog.actions.find((action) => action.id === actionId);
}

export function getMijngeldzakenParitySummary() {
  const controls = mijngeldzakenSurfaceCatalog.featureInventory.flatMap((page) => page.controls);
  const actionsBySafety = mijngeldzakenSurfaceCatalog.actions.reduce<Record<MijngeldzakenActionSafety, number>>(
    (acc, action) => {
      acc[action.safety] += 1;
      return acc;
    },
    {
      read_only: 0,
      safe_draft: 0,
      requires_confirmation: 0,
      requires_credentials: 0,
    }
  );
  const pagesByAutomationMode = mijngeldzakenSurfaceCatalog.featureInventory.reduce<Record<MijngeldzakenAutomationMode, number>>(
    (acc, page) => {
      acc[page.automationMode] += 1;
      return acc;
    },
    {
      observe: 0,
      read_only: 0,
      safe_draft: 0,
      requires_user_auth: 0,
    }
  );

  return {
    modules: mijngeldzakenSurfaceCatalog.modules.length,
    surfaces: mijngeldzakenSurfaceCatalog.modules.reduce((count, module) => count + module.surfaces.length, 0),
    syncContracts: mijngeldzakenSurfaceCatalog.syncContracts.length,
    featurePages: mijngeldzakenSurfaceCatalog.featureInventory.length,
    observedControls: controls.length,
    actions: mijngeldzakenSurfaceCatalog.actions.length,
    actionsBySafety,
    pagesByAutomationMode,
  };
}

export function planMijngeldzakenAction(input: {
  surfaceId: string;
  actionId: string;
  payload?: Record<string, unknown>;
  allowWrite?: boolean;
}) {
  const payload = input.payload || {};
  const action = findMijngeldzakenAction(input.actionId);
  if (!action || action.surfaceId !== input.surfaceId) {
    return {
      status: "unsupported" as const,
      surfaceId: input.surfaceId,
      actionId: input.actionId,
      missingFields: [] as string[],
      canRunAutonomously: false,
      requiresConfirmation: true,
      message: "MijnGeldzaken action is not in the FAB action catalog.",
    };
  }

  const missingFields = action.requiredFields.filter((field) => payload[field] === undefined || payload[field] === "");
  const requiresConfirmation = action.safety === "requires_confirmation" || action.safety === "requires_credentials";
  const canRunAutonomously =
    missingFields.length === 0 &&
    (action.safety === "read_only" || action.safety === "safe_draft" || Boolean(input.allowWrite && !requiresConfirmation));

  return {
    status: missingFields.length ? "needs_fields" as const : "planned" as const,
    surfaceId: action.surfaceId,
    actionId: action.id,
    mode: action.mode,
    safety: action.safety,
    missingFields,
    canRunAutonomously,
    requiresConfirmation,
    message: canRunAutonomously
      ? `FAB can plan ${action.id} against MijnGeldzaken ${action.surfaceId}.`
      : `FAB can prepare ${action.id}, but execution requires review or confirmation.`,
  };
}

export function buildMijngeldzakenImportRow(payload: Record<string, unknown>) {
  return {
    Datum: payload.date ?? "",
    Omschrijving: payload.description ?? "",
    Tegenpartij: payload.counterparty ?? "",
    Bedrag: payload.amount ?? 0,
    Categorie: payload.category ?? "",
    Rekening: payload.account ?? "",
    Valuta: payload.currency ?? "EUR",
    "FAB Document ID": payload.sourceDocumentId ?? payload.documentId ?? "",
  };
}

export function buildMijngeldzakenMasterLedgerDraft(input: {
  actionId: string;
  surfaceId: string;
  payload?: Record<string, unknown>;
  sourceProof?: Record<string, unknown>;
}): MijngeldzakenMasterLedgerDraft | undefined {
  const payload = input.payload || {};
  const sourceProof = compactRecord(input.sourceProof || {});
  if (input.actionId === "transaction_import_prepare") {
    const importRow = buildMijngeldzakenImportRow(payload);
    const checksum = stableChecksum({
      actionId: input.actionId,
      surfaceId: input.surfaceId,
      importRow,
      sourceProof,
    });
    return {
      draftType: "transaction_import",
      targetSystem: "mijngeldzaken",
      surfaceId: input.surfaceId || "transactions",
      actionId: input.actionId,
      exportFormat: "csv",
      columns: mijngeldzakenImportColumns,
      importRow,
      sourceProof,
      checksum,
      externalSubmission: "not_executed",
    };
  }

  if (["document_upload_prepare", "receipt_upload_prepare", "payslip_upload_prepare"].includes(input.actionId)) {
    const uploadDraft = compactRecord({
      documentId: payload.documentId,
      filename: payload.filename,
      category: payload.category,
      description: payload.description,
    });
    const checksum = stableChecksum({
      actionId: input.actionId,
      surfaceId: input.surfaceId,
      uploadDraft,
      sourceProof,
    });
    return {
      draftType: "document_upload",
      targetSystem: "mijngeldzaken",
      surfaceId: input.surfaceId || "document_vault",
      actionId: input.actionId,
      uploadDraft,
      sourceProof,
      checksum,
      externalSubmission: "not_executed",
    };
  }

  if (input.actionId === "category_mapping_prepare") {
    const mappingDraft = compactRecord({
      sourceCategory: payload.sourceCategory,
      targetCategory: payload.targetCategory,
    });
    const checksum = stableChecksum({
      actionId: input.actionId,
      surfaceId: input.surfaceId,
      mappingDraft,
      sourceProof,
    });
    return {
      draftType: "mapping",
      targetSystem: "mijngeldzaken",
      surfaceId: input.surfaceId || "categories",
      actionId: input.actionId,
      mappingDraft,
      sourceProof,
      checksum,
      externalSubmission: "not_executed",
    };
  }

  return undefined;
}

function compactRecord(value: Record<string, unknown>) {
  return Object.fromEntries(Object.entries(value).filter(([, item]) => item !== undefined && item !== null && item !== ""));
}

function stableChecksum(value: unknown) {
  const body = stableStringify(value);
  return [0x811c9dc5, 0x9e3779b1, 0x85ebca77, 0xc2b2ae3d, 0x27d4eb2f, 0x165667b1, 0xd3a2646c, 0xfd7046c5]
    .map((seed) => fnv1aHex(body, seed))
    .join("");
}

function stableStringify(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map((item) => stableStringify(item)).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.entries(value as Record<string, unknown>)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, item]) => `${JSON.stringify(key)}:${stableStringify(item)}`)
      .join(",")}}`;
  }
  return JSON.stringify(value);
}

function fnv1aHex(value: string, seed: number) {
  let hash = seed >>> 0;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash.toString(16).padStart(8, "0");
}
