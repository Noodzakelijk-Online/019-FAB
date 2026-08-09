# FAB Comprehensive Automated Bookkeeping Scope

FAB is intended to be a complete automated bookkeeping platform: it ingests financial documents, extracts and validates structured data, manages vendors and categories, prevents duplicates, routes entries to the right bookkeeping platform, reconciles bank activity, exposes review and reporting workflows, and preserves an auditable record of every action.

The repository now has a locally operational SQLite-backed worker, authenticated API, React/Node operations dashboard, governed HAI connector, Windows launcher, and Compose deployment. Remaining work is dominated by live provider/accountant acceptance and hosted multi-user governance, not by a missing local bookkeeping backbone.

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

- Gmail, Google Drive, and Freshdesk now have bounded pagination, content-addressed downloads, durable source/document provenance, exact-content idempotency, provider-revision review, isolated failures, and source health/readiness visibility. Production credential provisioning and connector-specific retry scheduling still need operational deployment work.
- Google Photos whole-library background reads are no longer available. FAB now provides a durable user-owned Picker session, paginated selected-photo retrieval, bounded authenticated download, duplicate/revision registration, provider cleanup, and session health/audit visibility. Production OAuth-client approval and a live account acceptance run remain deployment tasks.
- OCR, financial extraction, and vendor templates emit per-field confidence and attributable evidence. Derived preprocessing files are private and removed after OCR.
- Extracted fields, source identity, revisions, corrections, review decisions, and workflow evidence persist in the operations ledger.
- Validation findings are machine-readable and distinguish warnings from blockers; live OCR/provider acceptance across the user's full document population remains an operational gate.

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
- `src/learning/correction_learning.py`
- `src/operations/local_corrections.py`

### Enhancement Gaps

- Category intents, suggestions, applied rules, correction evidence, and Wave account mappings persist in the ledger or encrypted local setup according to their sensitivity.
- Decisions expose method, confidence, evidence, fallback/review state, and exact-vendor rule attribution. User-owned extraction templates are deterministic and malformed definitions fail independently.
- Approved corrections can create attributable exact-vendor category rules. Broader alias management, nested-category editing, and model training remain review-gated product work.

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

- Exact content identities, provider revisions, fuzzy duplicate candidates, grouping decisions, and review outcomes persist in the ledger.
- Autonomous policy skips exact duplicates and routes ambiguous or superseding evidence to review instead of silently merging it.
- Document revisions, extracted fields, correction history, duplicate links, source evidence, and export/readback state remain queryable. Provider-side document version semantics still require connector-specific acceptance.

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

- Supported Wave execution, MijnGeldzaken artifact supervision, routing rules, export attempts, retries, external IDs, workflow runs, reviews, and integration status use durable ledger/API/dashboard paths. Provider acceptance and additional Wave mutation coverage remain gated rather than represented as successful.

## 5. User Interface and Experience

### Target Capability

- Provide an intuitive dashboard with real-time processing status, recent activity, backlog counts, errors, and key metrics.
- Allow customizable views, including layout preferences, visible columns, filters, and potentially theme preferences.
- Provide a dedicated manual-review backlog where users can inspect a document, correct extracted fields, choose vendor/category, resolve duplicates, and approve routing.

### Current Code Anchors

- `web/client/src/pages/admin/Operations.tsx`
- `web/server/routers.ts`
- `src/operations/local_api.py`
- `src/operations/local_ledger.py`
- `src/operations/local_review.py`
- `src/operations/local_exceptions.py`
- `src/learning/correction_learning.py`

### Enhancement Gaps

- The Operations dashboard is the first-class bookkeeping workspace for live health, documents, review, exceptions, workflow runs, exports, reports, connectors, backup, and audit evidence.
- Review changes persist in the authoritative SQLite ledger and can create attributable category-rule suggestions through the correction-learning service.
- Durable per-user layout/column presets and fine-grained bookkeeping roles remain future product work; they are not represented as active controls.

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

- Financial operations use durable audit events in addition to application logs; sensitive local connector values use the encrypted secret store and are redacted from API/support output.
- Hosted deployment still needs a deployment-owned secrets manager and identity provider.
- RBAC should be expanded from the authenticated local operator boundary and basic web roles into bookkeeping-specific permissions before multi-user hosting.
- The local operations layer now produces idempotent, provisional Dutch VAT assessments, reviewable structured findings, source-file evidence, and seven-year document-retention records. Filing and deletion remain explicitly unauthorized.
- Compliance still needs full Dutch return-box mappings, ICP/private-use/small-business rules, exchange-rate policy, accountant approval, and a separately approved filing connector.

## 8. Workflow Automation and Notifications

### Target Capability

- Automate invoice approvals, payment scheduling, receipt matching, categorization, and routing where confidence is high.
- Notify users about duplicates, missing receipts, discrepancies, failed integrations, review backlog changes, and upcoming deadlines.
- Support reminder systems for tax filings, invoice due dates, and unresolved review items.

### Current Code Anchors

- `src/worker/scheduler.py`
- `src/operations/local_autonomy.py`
- `src/operations/local_workflow_recovery.py`
- `src/operations/local_notifications.py`
- `src/operations/local_exceptions.py`
- `web/server/_core/notification.ts`
- `web/server/routers.ts`

### Enhancement Gaps

- Workflow runs and step-level status are persisted in the operations ledger with governed retry evidence.
- Local event definitions, user preferences, inbox lifecycle, and audit tracking are implemented in the operations layer. Approved recipient/channel delivery and delivery-attempt evidence remain open.
- Confidence thresholds and review fallback are implemented; live provider acceptance remains the boundary for unattended external execution.

## 9. Error Handling and Support

### Target Capability

- Detect and correct common bookkeeping errors where safe.
- Maintain detailed audit logs for every action, data change, and integration attempt.
- Route uncertain, risky, or failed cases to manual review.
- Provide support channels such as chat, email, and phone as the commercial product matures.

### Current Code Anchors

- `src/worker/scheduler.py`
- `src/operations/local_workflow_recovery.py`
- `src/operations/local_exceptions.py`
- `src/operations/local_review.py`
- `src/operations/local_ledger.py`
- `web/client/src/pages/admin/Operations.tsx`
- `web/client/src/components/AIChatBox.tsx`

### Enhancement Gaps

- Stage failures, recovery eligibility, retry attempts, exceptions, review decisions, and audit events are structured ledger records and queryable from the dashboard.
- Support/chat still needs approved identity, retention, and document-context policy before it can perform bookkeeping actions.
- Outbound notification delivery remains disabled until recipient approval and delivery-attempt evidence are implemented.

## 10. Scalability, Performance, Backup, and Recovery

### Target Capability

- Scale document processing without blocking the UI.
- Monitor system performance and identify processing bottlenecks.
- Use cloud infrastructure for reliable uptime, redundancy, and remote access.
- Run automated backups.
- Provide disaster recovery procedures and user-initiated restores.

### Current Code Anchors

- `src/worker/scheduler.py`
- `src/operations/local_ledger.py`
- `src/operations/local_health.py`
- `src/backup/backup_manager.py`
- `package.py`
- `docker-compose.yml`
- `Dockerfile`

### Enhancement Gaps

- The API and worker now own queued stages through the durable SQLite workflow and runtime-lease model.
- Source-complete version 2 recovery packages now cover the operations ledger and every checksum-matching original document, fail closed on evidence gaps, run on a due-aware worker schedule, and expose redacted status plus strict creation in the operator dashboard.
- Generated report/export artifacts and a sanitized configuration snapshot still need explicit package coverage.
- Local maintenance now owns the same singleton lock as the autonomous worker. Ledger-only and full recovery both require exact confirmation and a verified pre-restore package; full recovery restores source bytes into an immutable content-addressed root, rewrites recovered ledger paths, rejects collisions or incomplete coverage, verifies every live row and byte, and restores the prior ledger snapshot if post-restore verification fails. Production-sized recovery rehearsal and operator sign-off remain acceptance work.
- Durable step evidence now covers autonomous actions and connector sources. Governed recovery creates linked attempts for failed read-only connector sources or the exact failed low-risk autonomous step. Bounded scheduling, stale-process finalization, and dependency-aware continuation are wired: only source-proven `not_run` descendants in the explicit local data-flow graph are selected, each continuation requires output from its recovered predecessor, and approved exports or other external actions are never replayed. Multi-host distributed execution remains a deployment concern.

## Recommended Delivery Sequence

### Phase 1: Provider Acceptance

- Provision and validate production Gmail, Google Drive `sort out`, and Freshdesk credentials against the durable connector-intake control plane.
- Validate the supervised Google Photos Picker flow with the production OAuth client and receipt-selection account, including token revocation and provider timeout recovery.
- Run a synthetic receipt through Wave creation, attachment upload, and independent attachment readback before enabling Drive archival. Expand only provider operations that can meet the same idempotency/readback bar.
- Keep MijnGeldzaken as an explicit supervised checksum-bound artifact flow unless an authenticated provider API is approved.

### Phase 2: Financial and Legal Acceptance

- Have a Dutch accountant validate chart-of-account mappings, opening balances, VAT box semantics, private-use/ICP/KOR rules, exchange-rate policy, and close packs.
- Keep VAT outputs provisional until mappings, approval responsibilities, and a filing connector pass separate acceptance.
- Rehearse ledger/source restore on a production-sized copy and sign off the DPIA, retention inventory, and disaster-recovery procedure.

### Phase 3: Hosted and Multi-User Operation

- Add deployment-owned identity, bookkeeping-specific RBAC, secrets management, monitoring, and a dedicated HTTPS endpoint before remote multi-user access.
- Add approved recipients/channels and delivery-attempt evidence before enabling outbound notifications or scheduled report delivery.
- Split the large OCR-capable image only if measured registry transfer, memory, or cold-start cost justifies the operational complexity.

## Immediate Next Build Target

Complete the live Google Drive to Wave acceptance loop with a synthetic non-financial test document: source identity, extraction/review, approved draft, provider record, attachment upload, independent attachment readback, and only then verified Drive archival. Until that succeeds, FAB must continue reporting the provider gate and leave every source file in place.
