# User Guide for Automated Bookkeeping Solution

## 1. Introduction

Welcome to the Automated Bookkeeping Solution! This guide will walk you through how to set up, configure, and use the system to automate your financial document processing and data entry.

## 2. System Overview

The Automated Bookkeeping Solution is designed to streamline your bookkeeping process by:

*   **Fetching Documents**: Automatically retrieves financial documents (receipts, invoices, statements) from various sources like Gmail, Google Drive, Google Photos, and Freshdesk.
*   **Processing Documents**: Extracts key information from these documents using advanced OCR (Optical Character Recognition) and data extraction techniques.
*   **Categorizing Transactions**: Categorizes transactions into predefined accounts (e.g., Personal, Business, Handicap-related) using a combination of rule-based and machine learning models.
*   **Automated Data Entry**: Enters the processed and categorized data into your chosen bookkeeping platforms, currently supporting mijngeldzaken.nl and Waveapps.
*   **Learning and Improvement**: Continuously learns from your data and feedback to improve categorization accuracy over time.

## 3. Getting Started

Before you can use the system, you need to complete the initial setup steps.

### 3.1. Prerequisites

Ensure you have the following installed on your system:

*   **Python 3.9 or higher**: Download from [python.org](https://www.python.org/downloads/).
*   **`pip`**: Python's package installer, usually comes with Python.
*   **`git`** (optional, if cloning from a repository): Download from [git-scm.com](https://git-scm.com/downloads).
*   **Docker** (optional, for containerized deployment): Download from [docker.com](https://www.docker.com/products/docker-desktop).
*   **Google Cloud SDK** (optional, if deploying to Google Cloud Functions): Follow instructions on [cloud.google.com](https://cloud.google.com/sdk/docs/install).

### 3.2. Installation

1.  **Download the Project:**

    If you received a zip archive, extract its contents to your desired directory. For example, `C:\bookkeeping_app` on Windows or `/home/user/bookkeeping_app` on Linux/macOS.

    If you are cloning from a Git repository:
    ```bash
    git clone <repository_url>
    cd automated_bookkeeping
    ```

2.  **Create a Python Virtual Environment (Recommended):**

    A virtual environment isolates your project's dependencies from other Python projects.
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install Dependencies:**

    Navigate to the project's root directory (where `requirements.txt` is located) and install the necessary Python packages:
    ```bash
    pip install -r requirements.txt
    ```

## 4. Configuration

The system's behavior is controlled by the `config/config.ini` file. A template `config_template.ini` is provided. You **must** copy this template and rename it to `config.ini`.

```bash
cp config/config_template.ini config/config.ini
```

Now, open `config/config.ini` in a text editor and fill in the required details for each section. Below is a breakdown of the key sections and parameters.

**Security Note**: For sensitive credentials (like API keys, passwords), it is highly recommended to use **environment variables** instead of directly writing them into `config.ini`. The system's `ConfigLoader` is designed to automatically override `config.ini` values with environment variables that are prefixed with `APP_` (e.g., `APP_GMAIL_CLIENT_ID` will override `gmail.client_id` in `config.ini`). Local operations settings also accept direct `FAB_LOCAL_*` flat variables such as `FAB_LOCAL_LEDGER_PATH` and `FAB_LOCAL_API_PORT`.

### 4.1. `[app]` Section

General application settings.

*   `log_file`: Path to the application log file. (e.g., `logs/app.log`)

### 4.1.1. `[operations]` Section

Local operating ledger and optional web operations API settings.

*   `local_ledger_enabled`: Set to `true` to persist workflow runs, document status, normalized bookkeeping records and line items, review items, routing attempts, export attempts, bank statement imports, bank transactions, reconciliation matches, and audit events to local SQLite.
*   `ledger_path`: Path to the SQLite ledger file. On Windows, prefer a private folder such as `C:\Users\<you>\AppData\Local\FAB\fab_operations.sqlite3`.
*   `api_host`: Host for the optional local operations API. Use `127.0.0.1` unless you intentionally expose FAB through a protected tunnel.
*   `api_port`: Port for the optional local operations API. Default: `5001`.
*   `api_token`: Bearer token required by the optional local operations API and optional web operations API. Configure this before using ngrok or any non-loopback host.
*   `local_intake_paths`: Comma- or semicolon-separated local folders to scan from the dashboard, such as a Google Drive-synced `sort out` folder.
*   `local_intake_extensions`: File extensions accepted by local intake. Default document types include PDF, image, text, and CSV files.
*   `backup_dir`: Folder where the local dashboard/API stores SQLite ledger backups. Keep this outside Git-tracked folders for real financial metadata.
*   `categorization_review_confidence_threshold`: Minimum category confidence before FAB can keep a processed document out of manual review.
*   `waveapps_default_account`: Default Wave account name used when preparing local transaction draft payloads.
*   `review_stale_hours`: Age at which open review items are flagged in Operations Health. Default: `48`.
*   `document_stale_hours`: Age at which imported, processing, or review documents are flagged as stuck. Default: `24`.
*   `routing_stale_hours`: Age at which prepared routing drafts are flagged as waiting too long for approval/export. Default: `24`.
*   `workflow_stale_hours`: Age at which a running workflow is treated as stale. Default: `6`.
*   Local reconciliation uses the `[reconciliation]` matching thresholds and stores imported bank transactions, candidate matches, missing-receipt alerts, unmatched documents, and approval decisions in the local ledger.
*   `enabled`: Set to `true` only when the local web operations API is running and protected by a token.
*   `api_url`: Base URL for the optional web operations API, such as `http://127.0.0.1:3000`.
*   `timeout_seconds`: Request timeout for the optional web operations API.

The local ledger does not store API tokens or passwords. It can store financial document metadata and OCR text, so keep the file out of Git and protect it like bookkeeping records.
Run the local API with:

```bash
python -m src.operations.local_api
```

Open `http://127.0.0.1:5001/` for the local dashboard. Use the Operations Health panel to see stale review items, stuck documents, failed records, routing blocks, prepared drafts waiting for approval, and stale workflow runs. Use the Autonomous Cycle panel to plan or run the safe local loop: folder intake, imported-document processing, Wave draft preparation, reconciliation candidate creation from persisted or supplied bank transactions, and read-only Wave reconciliation planning. It never submits data to Wave, resolves reviews, changes credentials, restores backups, deletes files, or sends external messages. Use the Folder Intake panel to rescan configured folders into the ledger, then process imported documents through OCR/text extraction, categorization, validation, and review gates. The Bookkeeping Records panel shows FAB's normalized financial records across document and bank sources, including review-required state, export readiness, reconciliation status, target system, vendor, date, category, amount, line-item count, account mapping, and tax mapping. The Extracted Fields panel shows field-level vendor/date/amount/VAT/category evidence, confidence, and provenance for processed documents. Manual Review cards can approve, reject, resolve, and correct vendor/category/date/amount fields; approved corrections update the normalized bookkeeping record and create suggested vendor/category rules for future learning. Reconciliation-related review cards also show linked bank transaction evidence: approving a candidate marks the document, normalized record, and bank transaction reconciled, while resolving or choosing "No receipt needed" closes missing-receipt exceptions without posting to Wave. The Routing & Export Drafts panel prepares Wave draft operation plans for reviewed documents and records them as routing attempts without submitting anything to Wave. The Export Attempts panel turns those routing drafts into approval records, requires `APPROVE FAB EXPORT DRAFT` before local approval, and requires `RECORD FAB EXPORT RESULT` before recording a separate executor result; approval does not submit to Wave by itself. The Wave Control Center models Wave menus, reports, report packs, and operation safety gates so FAB can plan account-transactions, trial balance, sales tax, customer/vendor, and close-pack workflows before a separate approved executor touches Wave. Planned report work is persisted as Wave report snapshots with report type, period/as-of date, cash/accrual basis, account/contact scope, export format, operation id, and workflow provenance so FAB can audit what evidence should be read or exported later. The Bank Transactions panel persists Wave account-transactions exports and bank statements from JSON, CSV, CAMT XML, or MT940-style text, normalizes localized amounts/dates, detects duplicate transaction identities, and exposes unreconciled rows to the autonomous loop. The Reconciliation panel can use imported bank transactions automatically or accept a temporary JSON override batch; it matches them to processed documents, records candidate matches, opens missing-receipt or unmatched-document review items, and requires an audited decision before a document and linked bank transaction are marked reconciled. The Backups panel creates manifest-based SQLite ledger backups, lists backup checksums, and only restores when the exact phrase `RESTORE FAB LOCAL LEDGER` is supplied. The Settings panel and `/api/settings` show source readiness, dependency status, storage paths, credential presence, and remote exposure safety without returning API tokens, passwords, or other secret values. The API also exposes `/api/health`, `/api/settings`, `/api/autonomy/plan`, `/api/autonomy/run`, `/api/dashboard`, `/api/sources`, `/api/extracted-fields`, `/api/bookkeeping-records`, `/api/bookkeeping-records/{id}`, `/api/bookkeeping-records/{id}/line-items`, `/api/bookkeeping-records/refresh`, `/api/wave`, `/api/wave/actions`, `/api/wave/reports`, `/api/wave/reports/plan`, `/api/wave/report-snapshots`, `/api/wave/plan`, `/api/wave/workflows/plan`, `/api/bank-transactions`, `/api/bank-transactions/import`, `/api/intake/rescan`, `/api/documents`, `/api/documents/{id}/process`, `/api/documents/process-imported`, `/api/documents/{id}/route`, `/api/routing`, `/api/routing/prepare-ready`, `/api/routing/{id}/export-attempt`, `/api/export-attempts`, `/api/export-attempts/prepare-ready`, `/api/export-attempts/{id}/approve`, `/api/export-attempts/{id}/result`, `/api/reconciliation`, `/api/reconciliation/run`, `/api/reconciliation/{id}/resolve`, `/api/backups`, `/api/backups/inspect`, `/api/backups/restore`, `/api/review`, `/api/rules`, `/api/corrections`, and `/api/audit`. `/api/health` returns the same operational health summary used by the dashboard plus a compact readiness summary.

The Sources panel and `/api/sources` show observed folder or connector sources, their latest status, last scan time, seen/imported/duplicate counters, and source identifiers. Connector metadata that looks like tokens, passwords, secrets, credentials, authorization headers, or API keys is redacted before it is stored.

### 4.2. `[gmail]` Section

Configuration for fetching documents from Gmail.

*   `credentials_file`: Path to your Google API credentials JSON file (downloaded from Google Cloud Console). (e.g., `credentials/gmail_credentials.json`)
*   `token_file`: Path where the OAuth 2.0 token will be stored after first authentication. (e.g., `tokens/gmail_token.json`)
*   `attachment_download_dir`: Directory to save downloaded Gmail attachments. (e.g., `downloads/gmail`)
*   `search_query`: Gmail search query to filter emails. Examples:
    *   `has:attachment from:"example@vendor.com" subject:"Invoice"`
    *   `label:receipts after:2025/01/01`

### 4.3. `[google_drive]` Section

Configuration for fetching documents from Google Drive.

*   `credentials_file`: Path to your Google API credentials JSON file. (e.g., `credentials/drive_credentials.json`)
*   `token_file`: Path where the OAuth 2.0 token will be stored. (e.g., `tokens/drive_token.json`)
*   `download_dir`: Directory to save downloaded Drive files. (e.g., `downloads/drive`)
*   `folder_id`: The ID of the specific Google Drive folder to monitor. You can find this in the URL when viewing the folder in Google Drive.
*   `file_types`: Comma-separated list of file extensions to download (e.g., `pdf,jpg,png`).

### 4.4. `[freshdesk]` Section

Configuration for fetching documents from Freshdesk.

*   `api_key`: Your Freshdesk API key.
*   `domain`: Your Freshdesk domain (e.g., `yourcompany.freshdesk.com`).
*   `download_dir`: Directory to save downloaded Freshdesk attachments. (e.g., `downloads/freshdesk`)
*   `ticket_status`: Comma-separated list of ticket statuses to fetch attachments from (e.g., `2,3` for Open, Pending).

### 4.5. `[google_photos]` Section

Configuration for fetching documents from Google Photos.

*   `credentials_file`: Path to your Google API credentials JSON file. (e.g., `credentials/photos_credentials.json`)
*   `token_file`: Path where the OAuth 2.0 token will be stored. (e.g., `tokens/photos_token.json`)
*   `album_name`: The name of the Google Photos album to monitor for receipts/documents.
*   `download_dir`: Directory to save downloaded Google Photos media. (e.g., `downloads/photos`)

### 4.6. `[processor]` Section

Settings for document processing.

*   `ocr_processor`: The primary OCR engine to use. Options: `vision` (Google Cloud Vision), `tesseract`, `dutch_ocr`, `handwritten_recognition`, `bilingual`.
*   `line_item_extraction_enabled`: `true` or `false`. Enable/disable line item extraction.
*   `template_matching_templates_dir`: Directory containing JSON templates for structured data extraction. (e.g., `templates/document_templates`)
*   `vendor_templates_file`: Path to a JSON file defining vendor-specific extraction rules. (e.g., `config/vendor_templates.json`)
*   `tesseract_cmd`: Path to the Tesseract executable (if not in system PATH). (e.g., `/usr/local/bin/tesseract`)
*   `tesseract_lang`: Default Tesseract language (e.g., `eng`, `nld`).
*   `dutch_ocr_lang`: Language for Dutch OCR processor (e.g., `nld`).
*   `handwritten_model_path`: Path to the trained model for handwritten recognition.

### 4.7. `[categorizer]` Section

Settings for document categorization.

*   `categorization_rules`: Path to a JSON file defining rule-based categorization rules. (e.g., `config/categorization_rules.json`)
*   `default_fallback_category`: The category to assign if no other categorization method yields a confident result. (e.g., `Manual Review`)
*   `ml_confidence_threshold`: Minimum confidence score for ML categorizer to accept a prediction (0.0 to 1.0).
*   `ml_model_path`: Path to the trained ML categorization model. (e.g., `models/ml_categorizer_model.joblib`)
*   `ml_vectorizer_path`: Path to the TF-IDF vectorizer used by the ML model. (e.g., `models/tfidf_vectorizer.joblib`)

### 4.8. `[mijngeldzaken]` Section

Settings for data entry into mijngeldzaken.nl.

*   `username`: Your mijngeldzaken.nl username.
*   `password`: Your mijngeldzaken.nl password.
*   `login_url`: The login page URL for mijngeldzaken.nl.
*   `import_url`: The URL for the CSV import page on mijngeldzaken.nl.
*   `csv_template`: JSON string defining the CSV structure and mapping from extracted data. Example: `{"columns": ["Date", "Description", "Amount", "Category"], "mapping": {"Date": "extracted_data.transaction_date", "Description": "extracted_data.description", "Amount": "extracted_data.total_amount", "Category": "category"}, "delimiter": ";"}`
*   `category_mapping`: JSON string mapping internal categories to mijngeldzaken.nl categories. Example: `{"Personal": "Huishouden", "Business": "Zakelijk"}`

### 4.9. `[waveapps_business]` Section

Settings for data entry into Waveapps Business account.

*   `access_token`: Your Waveapps Business API access token.
*   `business_id`: Your Waveapps Business ID.
*   `category_mapping`: JSON string mapping internal categories to Waveapps Business categories. Example: `{"Business": "Office Supplies", "Travel": "Travel Expenses"}`

### 4.10. `[waveapps_personal]` Section

Settings for data entry into Waveapps Personal account.

*   `access_token`: Your Waveapps Personal API access token.
*   `personal_id`: Your Waveapps Personal ID.
*   `category_mapping`: JSON string mapping internal categories to Waveapps Personal categories. Example: `{"Handicaps": "Medical Expenses", "Personal": "Household"}`
*   `handicap_tag`: A tag to append to descriptions for handicap-related expenses. (e.g., `#handicap`)

### 4.11. `[validation]` Section

Settings for data validation.

*   `receipt_validation_required_fields`: Comma-separated list of fields that must be present in extracted data for a receipt to be considered valid. (e.g., `vendor_name,total_amount,transaction_date`)
*   `btw_number_pattern`: Regular expression pattern for validating BTW (VAT) numbers. (e.g., `NL\d{9}B\d{2}`)

### 4.12. `[budget]` Section

Settings for budget management.

*   `budget_file`: Path to the JSON file storing budget definitions. (e.g., `data/budgets.json`)

### 4.13. `[banking]` Section

Settings for banking API integration.

*   `banking_api_endpoint`: URL of the banking API endpoint.
*   `banking_api_credentials`: JSON string with banking API credentials. Example: `{"client_id": "your_client_id", "client_secret": "your_client_secret"}`

### 4.14. `[reconciliation]` Section

Settings for automated reconciliation.

*   `reconciliation_threshold`: The maximum allowable difference between transaction amounts for them to be considered a match. (e.g., `0.05` for 5 cents)
*   `reconciliation_match_threshold`: Minimum combined amount, date, and vendor confidence required for an automatic match. Defaults to `0.9`.
*   `reconciliation_date_tolerance_days`: Maximum number of days between the bank transaction and document date. Defaults to `0`.
*   `reconciliation_use_absolute_amounts`: Match negative bank expenses with positive receipt totals. Defaults to `true`.

### 4.15. `[manual_review]` Section

Settings for manual review interface.

*   `manual_review_queue_file`: Path to the JSON file storing documents awaiting manual review. (e.g., `data/manual_review_queue.json`)

### 4.16. `[backup]` Section

Settings for backup and restore.

*   `backup_base_dir`: Base directory where backups will be stored. (e.g., `backups`)
*   `backup_paths`: Comma-separated list of files/directories to include in backups. (e.g., `data,config/config.ini`)
*   `backup_config`: JSON string defining backup type. Example: `{"type": "zip"}`

The local operations dashboard has a ledger-specific backup flow under `[operations] backup_dir`. It snapshots the SQLite ledger with a manifest and checksum, records audit events, creates a pre-restore backup, and requires the exact restore phrase before replacing the active ledger.

### 4.17. `[error_handling]` Section

Settings for error handling and recovery.

*   `error_recovery_max_retries`: Maximum number of retries for failed operations.
*   `error_recovery_retry_delay_seconds`: Delay between retries in seconds.
*   `email_notifications_enabled`: `true` or `false`. Enable/disable email notifications for critical errors.

### 4.18. `[workflow]` Section

Settings for autonomous progress tracking and restart safety.

*   `workflow_state_enabled`: Enable persistent source-document checkpoints. Defaults to `true`.
*   `workflow_state_file`: Path to the atomic JSON checkpoint file. Defaults to `data/workflow_state.json`.
*   `workflow_checkpoint_autosave`: Persist every terminal document transition immediately. Defaults to `true`. Disable only when batched disk writes are preferable and replay risk after a process crash is acceptable.
*   `workflow_checkpoint_fail_closed`: Block processing when existing checkpoint JSON is unreadable or structurally invalid. Defaults to `true`. Disable only for a deliberate checkpoint reset after preserving the damaged file.
*   `workflow_checkpoint_skip_statuses`: Optional comma-separated override for statuses skipped on later runs.
*   `workflow_known_documents_limit`: Maximum duplicate fingerprints retained in checkpoint state. Defaults to `1000`.
*   `workflow_run_lock_enabled`: Prevent overlapping workflow runs on the same host. Defaults to `true`.
*   `workflow_run_lock_file`: Optional lock-file path. Defaults to `<workflow_state_file>.lock`.
*   `workflow_run_lock_stale_seconds`: Recover abandoned locks older than this duration. Defaults to `21600` (six hours).
*   `duplicate_similarity_threshold`: Minimum evidence-weighted fuzzy duplicate score. Defaults to `0.9`.
*   `duplicate_amount_tolerance`: Maximum amount difference for duplicate comparison. Defaults to `0.02`.

Duplicate detection only suppresses documents with sufficient populated accounting evidence. Reused filenames or missing dates alone are not treated as duplicate proof.

## 5. Running the Application

### 5.1. Running the Workflow Locally

To execute the main automated bookkeeping workflow, navigate to the project's root directory and run:

```bash
python src/main.py
```

This will initiate the document fetching, processing, categorization, and data entry pipeline based on your `config.ini` settings.

### 5.2. Running Tests

It's highly recommended to run the tests to ensure everything is set up correctly and functioning as expected. From the project's root directory:

```bash
python -m unittest discover tests
```

### 5.3. Building Deployment Packages

The `package.py` script can be used to create deployable zip archives for local or cloud environments.

To build packages:

```bash
python package.py
```

This will create `automated_bookkeeping_local_YYYYMMDD_HHMMSS.zip` and `automated_bookkeeping_cloud_YYYYMMDD_HHMMSS.zip` files in the `dist/` directory.

## 6. Advanced Usage and Customization

### 6.1. Customizing Categorization Rules

Edit the JSON file specified in `[categorizer] categorization_rules` to define or modify your rule-based categorization logic. This file typically contains rules based on keywords, vendors, or other extracted data points.

### 6.2. Training ML Categorizer

If you intend to use the ML Categorizer, you will need to train the model with your own historical data. The `LearningManager` module provides functionalities for this. Refer to the `technical_reference.md` for details on how to prepare your data and trigger model training.

### 6.3. Extending Document Fetchers/Processors/Data Entry Handlers

The system is designed with a modular architecture. You can extend its capabilities by creating new modules that adhere to the `base.py` interfaces in `src/document_fetchers`, `src/document_processors`, and `src/data_entry`. Refer to `module_interfaces.md` for detailed API specifications.

### 6.4. Manual Review Interface

Documents that cannot be automatically processed or categorized with high confidence are flagged for manual review. The `ManualReviewInterface` (though currently a placeholder in this version) is intended to provide a web-based interface to review these documents, correct errors, and provide feedback to the learning system.

## 7. Troubleshooting

*   **Check Logs**: Always start by examining the `app.log` file (or the path specified in `config.ini`) for error messages and warnings.
*   **Configuration Errors**: Double-check your `config.ini` file for typos, incorrect paths, or missing credentials. Ensure sensitive information is correctly set via environment variables if you choose that method.
*   **Dependency Issues**: If you encounter `ModuleNotFoundError` or similar, ensure all dependencies are installed (`pip install -r requirements.txt`) and your virtual environment is activated.
*   **Google API Authentication**: For Gmail, Drive, and Photos fetchers, the first run will typically open a browser window for OAuth 2.0 authentication. Ensure you complete this process. If issues persist, delete the `token.json` files and try again.
*   **Playwright Issues**: If mijngeldzaken.nl automation fails, ensure Playwright browsers are installed (`playwright install --with-deps chromium`) and that your internet connection is stable.

## 8. Support

For further assistance, please refer to the `technical_reference.md` and `deployment_guide.md` documents, or contact the development team.


