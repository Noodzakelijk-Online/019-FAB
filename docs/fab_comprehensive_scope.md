# FAB Comprehensive Automated Bookkeeping Scope

FAB is a comprehensive automated bookkeeping solution. It streamlines the bookkeeping process from document intake to extraction, categorization, duplicate handling, platform routing, validation, reporting, compliance, backup, and recovery.

## 1. Data Extraction and Upload

- Transfer receipts and financial documents from the Google Drive `sort out` folder to the bookkeeping workflow.
- Use OCR for diverse receipt formats and multiple languages.
- Extract vendor name, date, amount, taxes, and purchase items.
- Validate extracted data before data entry.

## 2. Vendor and Category Management

- Identify vendors from receipts.
- Cross-reference vendors with existing entries.
- Create new vendor profiles when appropriate.
- Suggest vendors from aliases, fuzzy matches, partial matches, and history.
- Categorize based on vendor history and purchase patterns.
- Support dynamic category hierarchies and user-defined categorization rules.

## 3. Duplicate and Document Handling

- Detect duplicate entries using exact fingerprints and fuzzy matching.
- Handle multiple documents from the same order.
- Prioritize invoices and receipts over order confirmations.
- Preserve version history for transparency.

## 4. Integration and Multi-Account Support

- Route Category A entries to Mijngeldzaken.
- Route Categories B and C to Waveapps accounts.
- Support bank-account transaction imports.
- Keep the architecture API-ready for future integrations.

## 5. User Interface and Experience

- Provide dashboard-oriented data structures for real-time insights.
- Support customizable views and a manual-review backlog.

## 6. Reporting and Analytics

- Generate expense, revenue, cash-flow, and other financial reports.
- Support data visualization and scheduled report generation.

## 7. Security and Compliance

- Encrypt financial data in transit and at rest.
- Support role-based access control.
- Support VAT, tax, and financial reporting compliance checks.

## 8. Workflow Automation and Notifications

- Automate invoice approvals, payment scheduling, and categorization.
- Notify users about duplicates, missing receipts, discrepancies, and deadlines.

## 9. Error Handling and Support

- Correct common bookkeeping errors where safe.
- Maintain audit logs.
- Route uncertain cases to manual review.

## 10. Scalability, Performance, Backup, and Recovery

- Keep the architecture scalable and cloud-ready.
- Monitor performance.
- Support automated backups, disaster recovery, and user-initiated restores.

## Implementation Mapping

- `src/vendor_management/vendor_manager.py`: vendor identification, creation, suggestions, history-based category assignment, dynamic hierarchy lookup.
- `src/categorizers/vendor_aware_categorizer.py`: categorization using vendor profiles, vendor history, purchase patterns, and configured rules.
- `src/document_handling/duplicate_detector.py`: exact and fuzzy duplicate detection.
- `src/document_handling/document_priority.py`: invoice/receipt/order-confirmation prioritization.
- `src/document_handling/version_control.py`: JSON-based document version manifest.
- `src/routing/bookkeeping_router.py`: category-based routing to Mijngeldzaken and Waveapps handlers.
- `src/fab_blueprint.py`: product-scope blueprint kept close to the implementation.
