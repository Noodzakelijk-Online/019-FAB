# FAB Comprehensive Automated Bookkeeping Scope

FAB is intended to be a complete automated bookkeeping platform: it ingests financial documents, extracts and validates structured data, manages vendors and categories, prevents duplicates, routes entries to the right bookkeeping platform, reconciles bank activity, exposes review and reporting workflows, and preserves an auditable record of every action.

The current repository already contains many module-level foundations for this vision. The main enhancement work is to stabilize the automation core, add durable data persistence, connect the Python workflow to the React/Node web app, and turn the admin interface into a real bookkeeping operations dashboard.

## 1. Data Extraction and Upload

### Target Capability

- Automatically transfer receipts and financial documents from the Google Drive `sort out` folder into FAB.
- Support Gmail, Google Drive, Google Photos, Freshdesk, and later additional sources such as Outlook, OneDrive, Dropbox, scanner uploads, and mobile capture.
- Use OCR for diverse document layouts, image quality levels, handwritten text, and multiple languages.
- Extract vendor name, transaction date, total amount, VAT/tax amount, invoice or receipt number, and purchase line items.
- Validate extracted data before any bookkeeping entry is created.

### Current Code Anchors

- `src/document_fetchers/drive_fetcher.py`
- `src/document_fetchers/gmail_fetcher.py`
- `src/document_fetchers/photos_fetcher.py`
- `src/document_fetchers/freshdesk_fetcher.py`
- `src/document_processors/processor_pipeline.py`
- `src/document_processors/tesseract_processor.py`
- `src/document_processors/vision_processor.py`
- `src/document_processors/dutch_ocr_processor.py`
- `src/document_processors/bilingual_processor.py`
- `src/document_processors/line_item_extractor.py`
- `src/validation/receipt_validator.py`

### Enhancement Gaps

- Fetchers need production-grade idempotency, durable imported-document tracking, source folder state management, and retry metadata.
- OCR and extraction should emit confidence scores per field, not just document-level results.
- Extracted fields need a database-backed record so corrections, review decisions, and model feedback are preserved.
- Validation output should consistently include machine-readable errors, warnings, and blocking/non-blocking status.

## 2. Vendor and Category Management

### Target Capability

- Identify vendors from OCR, extracted fields, aliases, bank transactions, and historical entries.
- Cross-reference vendors with existing records and create new vendor profiles when appropriate.
- Suggest vendors from partial matches, aliases, fuzzy matches, and previous corrections.
- Categorize using vendor history, purchase patterns, rules, and learned feedback.
- Support nested category hierarchies and user-defined categorization rules.

### Current Code Anchors

- `src/vendor_management/vendor_manager.py`
- `src/categorizers/vendor_aware_categorizer.py`
- `src/categorizers/hybrid_categorizer.py`
- `src/categorizers/rule_based_categorizer.py`
- `src/categorizers/ml_categorizer.py`
- `src/learning/learning_manager.py`
- `src/learning/feedback_learner.py`

### Enhancement Gaps

- Vendor profiles, aliases, category history, and user rules should move from config/file structures into durable tables.
- Category decisions should include explanation data: rule matched, vendor match score, ML confidence, fallback reason, and review requirement.
- Manual corrections should feed back into vendor aliases, rules, and model training data.

## 3. Duplicate and Document Handling

### Target Capability

- Detect duplicates with exact fingerprints and fuzzy matching, even when filenames, OCR text, or amounts differ slightly.
- Handle multiple documents from the same order.
- Prioritize invoices over order confirmations while treating receipts as legally valid documents.
- Maintain version history for uploaded documents, extracted data, corrections, and routing decisions.

### Current Code Anchors

- `src/document_handling/duplicate_detector.py`
- `src/document_handling/document_priority.py`
- `src/document_handling/version_control.py`

### Enhancement Gaps

- Duplicate fingerprints and match decisions need persistent storage.
- The workflow should decide whether to skip, merge, supersede, or manually review duplicate-like documents.
- Version control should cover document metadata, extracted fields, category decisions, and user corrections, not only file manifests.

## 4. Integration and Multi-Account Support

### Target Capability

- Route Category A entries to MijnGeldzaken.nl.
- Route Categories B and C to separate Waveapps accounts.
- Connect to bank accounts for transaction import and reconciliation.
- Provide an API for integrations with business tools and later Slack, Zapier, and similar automation platforms.
- Keep a centralized processing layer so documents are routed consistently across all target systems.

### Current Code Anchors

- `src/routing/bookkeeping_router.py`
- `src/data_entry/mijngeldzaken_handler.py`
- `src/data_entry/waveapps_business_handler.py`
- `src/data_entry/waveapps_personal_handler.py`
- `src/banking/banking_api.py`
- `src/reconciliation/automated_reconciliation.py`
- `web/server/routers.ts`

### Enhancement Gaps

- Several integration handlers still contain placeholder or dummy behavior and need real API/session flows.
- Routing rules should be configurable and auditable.
- Platform entry attempts need durable status records, retry handling, and external IDs from Waveapps/MijnGeldzaken.
- The web app should expose operational APIs for workflow runs, review actions, and integration status.

## 5. User Interface and Experience

### Target Capability

- Provide an intuitive dashboard with real-time processing status, recent activity, backlog counts, errors, and key metrics.
- Allow customizable views, including layout preferences, visible columns, filters, and potentially theme preferences.
- Provide a dedicated manual-review backlog where users can inspect a document, correct extracted fields, choose vendor/category, resolve duplicates, and approve routing.

### Current Code Anchors

- `web/client/src/pages/admin/Overview.tsx`
- `web/client/src/pages/admin/Waitlist.tsx`
- `web/client/src/pages/admin/Messages.tsx`
- `web/client/src/pages/admin/Blog.tsx`
- `web/drizzle/schema.ts`
- `src/manual_review/manual_review_interface.py`
- `src/error_handling/manual_review.py`

### Enhancement Gaps

- The current web admin mostly manages waitlist, messages, blog, and Stripe information.
- The web database currently lacks bookkeeping documents, review items, vendors, categories, workflow runs, and audit events.
- Manual review exists as a file-backed Python concept, not as a first-class web workflow.

## 6. Reporting and Analytics

### Target Capability

- Generate expense, revenue, cash-flow, VAT/tax, budget, vendor, and category reports.
- Provide charts, graphs, drilldowns, and trend views.
- Schedule recurring reports and deliver them by email or notification.

### Current Code Anchors

- `src/financial_analysis/financial_analyzer.py`
- `src/budget/budget_manager.py`
- `src/operations/local_reporting.py`
- `src/operations/local_ledger.py`
- `src/operations/local_api.py`
- `web/client/src/pages/admin/Overview.tsx`

### Enhancement Gaps

- The local operations app now exposes provisional P&L, VAT, cash movement, and vendor/category spending from durable normalized records, with reconciliation-aware duplicate suppression, currency separation, CSV output, and completeness gates.
- Local scheduled report generation now uses durable worker-driven schedule slots, retry state, checksum-bound JSON/CSV artifacts, and report-run health tracking.
- The operations ledger now has a local notification inbox, per-event preferences, severity thresholds, idempotent health-event fingerprints, lifecycle actions, and worker refresh. It includes upcoming and overdue Wave invoice signals; outbound delivery remains disabled.
- External report or alert delivery still needs recipient preferences, approval policy, and delivery-attempt tracking; statutory filing remains out of scope until Dutch tax mappings are complete.
- Reports still need balance-sheet account semantics, statutory Dutch VAT filing rules, comparative periods, and time-series views by account/source/status.

## 7. Security and Compliance

### Target Capability

- Encrypt financial data in transit and at rest.
- Use role-based access control for users, reviewers, admins, and service accounts.
- Support VAT, tax, document retention, and financial reporting compliance checks.
- Maintain a comprehensive audit trail.

### Current Code Anchors

- `src/security/security_manager.py`
- `src/compliance/regulatory_compliance.py`
- `web/server/_core/trpc.ts`
- `web/server/lib/sanitize.ts`
- `web/server/lib/rateLimiter.ts`
- `web/server/lib/logger.ts`
- `web/drizzle/schema.ts`

### Enhancement Gaps

- Financial operations need audit logging beyond application logs.
- Secrets should be integrated with a production secrets manager for deployment.
- RBAC should be expanded from basic admin/user web roles into bookkeeping-specific permissions.
- The local operations layer now produces idempotent, provisional Dutch VAT assessments, reviewable structured findings, source-file evidence, and seven-year document-retention records. Filing and deletion remain explicitly unauthorized.
- Compliance still needs full Dutch return-box mappings, ICP/private-use/small-business rules, exchange-rate policy, accountant approval, and a separately approved filing connector.

## 8. Workflow Automation and Notifications

### Target Capability

- Automate invoice approvals, payment scheduling, receipt matching, categorization, and routing where confidence is high.
- Notify users about duplicates, missing receipts, discrepancies, failed integrations, review backlog changes, and upcoming deadlines.
- Support reminder systems for tax filings, invoice due dates, and unresolved review items.

### Current Code Anchors

- `src/workflow/controller.py`
- `src/error_handling/enhanced_error_recovery.py`
- `web/server/_core/notification.ts`
- `web/server/routers.ts`

### Enhancement Gaps

- Workflow runs need persistent state and step-level status.
- Local event definitions, user preferences, inbox lifecycle, and audit tracking are implemented in the operations layer. Approved recipient/channel delivery and delivery-attempt evidence remain open.
- Automation needs confidence thresholds and safe fallback to review.

## 9. Error Handling and Support

### Target Capability

- Detect and correct common bookkeeping errors where safe.
- Maintain detailed audit logs for every action, data change, and integration attempt.
- Route uncertain, risky, or failed cases to manual review.
- Provide support channels such as chat, email, and phone as the commercial product matures.

### Current Code Anchors

- `src/error_handling/enhanced_error_recovery.py`
- `src/error_handling/manual_review.py`
- `src/manual_review/manual_review_interface.py`
- `web/client/src/components/AIChatBox.tsx`

### Enhancement Gaps

- Error recovery decisions need structured result types.
- Support/chat should be connected to real user/account/document context before it becomes operationally useful.
- Audit logs should be queryable from the admin dashboard.

## 10. Scalability, Performance, Backup, and Recovery

### Target Capability

- Scale document processing without blocking the UI.
- Monitor system performance and identify processing bottlenecks.
- Use cloud infrastructure for reliable uptime, redundancy, and remote access.
- Run automated backups.
- Provide disaster recovery procedures and user-initiated restores.

### Current Code Anchors

- `src/performance/batch_processor.py`
- `src/performance/cache_manager.py`
- `src/performance/performance_optimizer.py`
- `src/backup/backup_manager.py`
- `cloud_functions.py`
- `src/cloud_functions.py`
- `Dockerfile`

### Enhancement Gaps

- Processing should move toward queued jobs and workers.
- Backups need to cover database state, original documents, generated artifacts, and configuration.
- Restore operations need safety checks, audit logging, and user-facing status.
- Performance metrics should be captured by workflow step and source.

## Recommended Delivery Sequence

### Phase 0: Stabilize the Current Codebase

- Fix failing syntax and contract issues in Python tests.
- Remove tracked `__pycache__` artifacts and add appropriate ignore rules.
- Make `python -m unittest discover tests` reliable in a clean environment.
- Make `web` install, typecheck, and test commands reproducible.

### Phase 1: Core Data Model

- Add database tables for documents, extracted fields, vendors, categories, review items, workflow runs, routing attempts, reconciliation matches, and audit events.
- Define shared status enums for processing, review, routing, reconciliation, and backup states.
- Add migration and seed data for local development.

### Phase 2: Manual Review Dashboard

- Build admin pages for review backlog, document detail, field correction, vendor/category selection, duplicate resolution, and approval.
- Connect review actions to persistent records.
- Feed approved corrections back into vendor/category learning.

### Phase 3: Workflow Orchestration

- Persist each workflow run and step result.
- Add resumable processing and retries.
- Add integration status and error visibility to the dashboard.
- Connect the Python workflow to the web API or move orchestration behind a worker/job boundary.

### Phase 4: Platform Integrations and Reconciliation

- Harden Google Drive ingestion from the `sort out` folder.
- Replace Waveapps and MijnGeldzaken placeholders with real entry flows.
- Implement bank transaction import and reconciliation status views.

### Phase 5: Reporting, Notifications, and Compliance

- Add financial reports and charts from persisted bookkeeping data.
- Add scheduled report generation.
- Add notification preferences and event-driven alerts.
- Add structured VAT/tax/compliance findings and audit views.

### Phase 6: Production Readiness

- Add queue-based processing, monitoring, backups, restore flows, secrets management, and deployment runbooks.
- Expand RBAC and audit logging.
- Add support workflows tied to user/account/document context.

## Immediate Next Build Target

The best first product increment is:

1. Stabilize the Python test suite enough to trust the core workflow.
2. Add persistent tables for documents, review queue items, vendors, categories, and workflow runs.
3. Build the first manual-review admin page in the web app.
4. Wire the existing Python manual-review queue into the database-backed review model.

This creates the backbone for nearly every other FAB capability: validation, categorization feedback, duplicate resolution, audit logs, notifications, reporting, and integration retry handling.
