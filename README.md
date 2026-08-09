# Automated Bookkeeping Solution

## Overview
This project aims to develop a fully automated system to fetch financial documents from various sources, extract relevant data, categorize them based on predefined rules, and enter the data into mijngeldzaken.nl and Waveapps accounts.

The governed cutover from repository 025's Apps Script is documented in [docs/scanner_mailbox_migration.md](docs/scanner_mailbox_migration.md).

## Features
- **Document Fetching**: Runs paginated, durable Gmail, Google Drive, and Freshdesk intake into the local source/document ledger, with duplicate and provider-revision evidence. Gmail can run as a strict scanner mailbox: exact trusted sender, PDF filename/MIME/signature validation, immutable local evidence, and no deletion or mutation of the source email. Freshdesk can run the consolidated repository-025 financial-ticket profile: keyword-scoped read-only ticket intake, non-posting description evidence, streamed and signature-verified PDF attachments, and no ticket closing or redundant Drive copy. Google Photos uses user-owned Picker sessions whose selected receipt images enter the same durable ledger and review gates.
- **Advanced Document Processing**: Utilizes OCR (Tesseract, Google Cloud Vision), including Dutch OCR, handwritten recognition, template matching, and line item extraction.
- **Intelligent Categorization**: Employs rule-based, machine learning, and hybrid categorization approaches.
- **Governed Downstream Delivery**: Prepares approval-gated Wave operations and checksum-bound MijnGeldzaken artifacts. Receipt attachment work remains supervised until exact Wave readback succeeds.
- **Review-Based Learning**: Approved corrections can create explainable exact-vendor rules. FAB does not fabricate training text or promise unsupervised accuracy gains.
- **Validation**: Validates extracted data against predefined rules and patterns.
- **Error Handling & Recovery**: Records stage failures, governed retries, exceptions, and authenticated review decisions in the operations ledger.
- **Workflow Evidence**: Persists ordered autonomous actions and connector-source steps with attempts, timestamps, duration, result metadata, failures, and aborted downstream work.
- **Governed Workflow Recovery**: Plans and executes linked attempt-2+ retries for failed read-only connector sources or the exact failed low-risk autonomous step, without replaying approved exports or other external actions. The worker applies bounded exponential backoff, stops at a configurable retry depth, and safely finalizes abandoned runs only after their runtime lease has expired.
- **Performance Optimization**: Uses bounded worker batches, lazy OCR/ML imports, SQLite WAL/indexes, compact cached projections, compressed responses, and enforced web build budgets.
- **Security**: Manages credentials securely using encryption.
- **Compliance**: Checks documents against regulatory compliance rules.
- **Browser Upload**: The authenticated operator dashboard accepts bounded receipt uploads from supported desktop or mobile browsers into the same local evidence ledger.
- **Automated Reconciliation**: Reconciles processed transactions with banking data.
- **Historical Import**: Routes authenticated document uploads, connector intake, and bank statements through the same identity, duplicate, review, and ledger contracts.
- **Budget Management**: Helps in tracking and managing budgets.
- **Bank Statement Import**: Imports and reconciles supported statement data locally. Direct PSD2 bank feeds are not implemented.
- **Financial Analysis**: Generates financial reports and insights.
- **Backup & Restore**: Manages backup and restoration of application data.

## Selected Project Structure
```
019-FAB/
├── config/
│   └── config_template.ini
├── docs/
│   ├── additional_improvements_requirements.md
│   ├── deployment_guide.md
│   ├── dependencies.md
│   ├── gap_analysis.md
│   ├── module_interfaces.md
│   ├── requirements_analysis.md
│   ├── security_approach.md
│   ├── technical_reference.md
│   └── user_guide.md
├── src/
│   ├── __init__.py
│   ├── banking/
│   │   └── banking_api.py
│   ├── backup/
│   │   └── backup_manager.py
│   ├── budget/
│   │   └── budget_manager.py
│   ├── categorizers/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── fallback_categorizer.py
│   │   ├── hybrid_categorizer.py
│   │   ├── ml_categorizer.py
│   │   └── rule_based_categorizer.py
│   ├── compliance/
│   │   └── regulatory_compliance.py
│   ├── config_loader.py
│   ├── data_entry/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── mijngeldzaken_handler.py
│   │   ├── waveapps_business_handler.py
│   │   └── waveapps_personal_handler.py
│   ├── document_fetchers/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── drive_fetcher.py
│   │   ├── freshdesk_fetcher.py
│   │   ├── gmail_fetcher.py
│   │   └── photos_fetcher.py
│   ├── document_processors/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── bilingual_processor.py
│   │   ├── dutch_ocr_processor.py
│   │   ├── enhanced_processor.py
│   │   ├── handwritten_recognition_processor.py
│   │   ├── line_item_extractor.py
│   │   ├── processor_factory.py
│   │   ├── processor_pipeline.py
│   │   ├── template_matching_processor.py
│   │   ├── tesseract_processor.py
│   │   └── vision_processor.py
│   ├── financial_analysis/
│   │   └── financial_analyzer.py
│   ├── integration.py
│   ├── learning/
│   │   ├── __init__.py
│   │   └── correction_learning.py
│   ├── main.py
│   ├── reconciliation/
│   │   └── automated_reconciliation.py
│   ├── security/
│   │   ├── __init__.py
│   │   └── security_manager.py
│   ├── validation/
│   │   ├── receipt_validator.py
│   │   └── validation_manager.py
│   └── workflow/
│       ├── __init__.py
│       ├── autonomous_playbook.py
│       ├── logger.py
│       ├── safety_engine.py
│       └── state_machine.py
├── tests/
│   └── test_*.py (backend regression and safety suite)
├── Dockerfile
├── package.py
└── requirements.txt
```

## Setup and Installation

### Prerequisites
- Python 3.13
- pip (Python package installer)
- Docker (optional, for containerized deployment)
- Git, which is used to bind release archives to an exact committed revision

### Local Installation
1.  **Clone the repository (or extract the zip file):**
    ```bash
    git clone https://github.com/Robert-Velhorst/019-FAB.git
    cd 019-FAB
    ```
    (If you received a release ZIP, extract it and navigate into its FAB directory.)

2.  **Create a virtual environment (recommended):**
    ```bash
    python3.13 -m venv .venv
    source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure the application:**
    Copy `config/config_template.ini` to `config/config.ini` and fill in your credentials and settings.
    ```bash
    cp config/config_template.ini config/config.ini
    # Open config/config.ini and edit with your details
    ```
    **Security Note**: For sensitive credentials, it is highly recommended to use environment variables instead of directly editing `config.ini`. The `ConfigLoader` is designed to prioritize environment variables prefixed with `APP_` (e.g., `APP_GMAIL_CLIENT_ID` will override `gmail.client_id` in `config.ini`).

### Docker Installation

Use `docker-compose.yml` so the API, authoritative worker, and dashboard share the same ledger and service identity. Set strong `FAB_LOCAL_API_TOKEN` and `FAB_WEB_JWT_SECRET` environment values, then run `docker compose up --build`. The Compose definition binds dashboard/API ports to loopback, separates the internal API address from browser-facing operator links, and refuses to render when either required secret is absent. See `docs/deployment_guide.md` for volumes, health checks, recovery mode, and managed-cloud requirements.

## Usage

### FAB Operator Dashboard

The React operator dashboard is a local-first control surface backed by the
authoritative SQLite operations ledger. It shows health, review and
reconciliation backlogs, autonomous pipeline gates, exceptions, recovery,
audit activity, source readiness, and close evidence. Its command drawer only
exposes local safe-cycle actions; approvals, exports, and external submissions
remain outside this command boundary.

On Windows, double-click `Start-FAB.cmd` for the normal local setup. It creates
the ignored local configuration files when needed, installs missing dashboard
and Python runtime dependencies, provisions Tesseract plus Dutch/English OCR
data and Poppler PDF tools when `winget` is available, starts the ledger API,
autonomous worker, and a current production build of the dashboard on loopback,
then opens the control room. Use `.\Start-FAB.ps1 -Development` only when
actively changing dashboard source code.
Use `Start-FAB-Maintenance.cmd` only for local recovery. It switches the same
checkout into a quiescent mode with no autonomous worker, locks normal API and
HAI mutations, disables ngrok, and exposes the confirmation-gated advanced
recovery console. Stop maintenance with `Stop-FAB.cmd`, then run
`Start-FAB.cmd` to resume standard operation.
Double-click `Stop-FAB.cmd` to stop only processes whose service identity and
project root match this FAB checkout. Runtime logs are written under `logs/`.

The launcher verifies FAB-specific service identity instead of trusting an
occupied port. If another application uses `3000` or `5001`, FAB selects a
free loopback port, records the actual URLs in `data/fab-runtime.json`, and
opens the correct dashboard. It also repairs stale PID metadata by
rediscovering the matching API, dashboard listener and singleton worker. The
dashboard process tree is adopted only after its runtime identity, checkout and
local API endpoint match, so repeated starts do not create duplicate
bookkeeping loops or move the dashboard to another port. `Stop-FAB.cmd`
performs the same discovery when runtime metadata is stale or missing. The
launcher records a secret-safe source fingerprint and restarts its own API,
worker, and dashboard when code or local configuration has changed. Ledger,
credential, token, and other runtime data are excluded from that fingerprint.

Complete Gmail and Google Drive consent from **Finish activation** in the
operator dashboard. An installed desktop OAuth client can be reused for fresh
consent; upload another JSON only for an intentional client rotation. The
supervised flows open Google in your default browser, store tokens only under
`tokens/`, verify the configured mailbox or intake folder, and never print or
store the tokens in the ledger. `Authorize-FAB-GoogleDrive.cmd` remains
available as a command-line alternative.

Configure Wave from the **Connections** section of the operator dashboard.
Open **Wave - Noodzakelijk Online**, store the user-owned API token and business
ID, run the read-only business validation, then map each in-use FAB category
intent to an expense account returned by Wave. Reviewers can classify and teach
FAB before Wave is connected because the intent is local; posting remains
blocked until the intent has an explicit, live-verified Wave account ID. A
default expense account can be retained for supervised drafts, but autonomous
posting never uses it to hide a missing mapping. FAB encrypts these local
settings and, on Windows, protects the encryption key with DPAPI for the current
user. The token is never returned to the browser, ledger, audit log, or API
status response. Environment variables remain supported and take precedence
over dashboard settings.

The review workspace prefills explainable category intents only for exact
normalized matches to FAB's conservative vendor taxonomy. The suggestion is
never applied until the source-backed decision is approved. When **Teach FAB**
is checked, that explicit approval becomes an approved exact-vendor rule for
future documents instead of requiring a second approval. **Reassess review
queue** creates a ledger backup, reruns current extraction and validation
against retained OCR once per algorithm version, preserves manual corrections
and duplicate gates, and never reruns OCR or submits externally.

For manual startup or development:

1. Start the Python ledger API from the repository root:

    ```powershell
    python -m src.operations.local_api
    ```

2. Configure and start the web application:

    ```powershell
    Copy-Item web/.env.example web/.env
    pnpm.cmd --dir web install
    pnpm.cmd --dir web dev
    ```

3. Open `http://127.0.0.1:3000/admin/operations`. The server selects the next
   available port when `3000` is already in use.

4. Use **Add receipts** to upload one or more PDF/image/CSV files of up to 6 MB
   each. FAB stores them in the configured local intake folder, registers them
   in the authoritative ledger, and starts local processing. Use **Run safe
   cycle** to collect and process anything later added to the intake folder.
   **Detailed ledger** opens the complete local document, review,
   reconciliation, reporting, backup, and approval interface.

`Start-FAB.cmd` passes `operations.api_token` to both authenticated dashboard
server bridges without printing it. Compose wires the same server-only trust
boundary. For manual startup, set `FAB_LOCAL_API_TOKEN` and
`FAB_OPERATIONS_SERVICE_TOKEN` in `web/.env` to the same long random value. The
token is used only by the web server and is never sent to the browser. Advanced
ledger, evidence, report-artifact, delivery, recovery, and connector-contract
links use a 45-second one-time signed handoff, so an authenticated operator is
not asked to paste the hidden API token. Only bounded relative FAB targets are
accepted; the Flask session is rotated and the handoff is redacted in audit
history. Local operator access accepts direct loopback requests in development;
deployed environments require an authenticated administrator unless
`FAB_OPERATOR_LOCAL_MODE=true` is explicitly set and the request remains local.

The HAI connector publishes discovery at `/api/hai/manifest` and status at
`/api/hai/status`. The default local configuration enables the bounded
governed-command allowlist used by the dashboard. HAI cannot approve, export,
restore, change access controls, or submit downstream bookkeeping changes.

Wave receipt upload uses a separate supervised executor boundary because the
public Wave transaction API does not provide FAB's required receipt upload and
binary readback flow. A user-owned browser or HAI executor registers non-secret
session metadata at `POST /api/wave/receipt-executor/session`, keeps a fresh
heartbeat there, and claims one eligible work order at a time from
`POST /api/wave/receipt-executor/claim`. FAB rejects passwords, tokens,
cookies, credentials, and browser storage state. The executor must advertise
transaction location, receipt upload/download, transaction review, and
observed-field capabilities for the exact configured Wave business. Status is
available at `GET /api/wave/receipt-executor/status`; leases are released at
`POST /api/wave/receipt-executor/release` or automatically after a bound binary
readback submission containing the executor and session IDs. Token/account
mapping alone therefore no longer reports the source-to-Wave pipeline as ready.

Source-to-Wave executor handoff is available at
`GET /api/drive-wave/work-orders` and is advertised by the HAI manifest as the
read-only resource `wave_attachment_work_orders`. Authenticated connectors can
submit exact configured-folder bytes through `google_drive_binary_relay`; after
Wave upload they must submit the attachment downloaded back from Wave through
`wave_attachment_binary_readback`. Each work order binds one Drive file or
trusted Gmail scanner attachment and SHA-256 to FAB's expected Wave fields,
line items, transaction reference, server-computed attachment readback
evidence, and source retention policy. Metadata attestation or a visible
receipt icon cannot complete delivery or unlock archival. FAB compares the
observed Wave values itself; executor-supplied match booleans are ignored, and
later field changes invalidate older evidence. Gmail source messages and local
evidence are never mutated or deleted. The dashboard exposes the same state in
**Source to Wave delivery**.

### Running the Workflow Locally
To run exactly one governed cycle through the same authoritative ledger worker
used by the Windows launcher and containers:
```bash
python -m src.main
```

The command acquires this checkout's worker ownership lock and exits without
starting a second cycle when the recurring worker is already running. Normal
Windows operation should use `Start-FAB.cmd`; use `python -m src.run_worker`
only when deliberately running the recurring worker outside the launcher.

### Running Tests
To run all unit and integration tests:
```bash
python -m unittest discover tests
```

### Building Deployment Packages
Use `package.py` from a clean committed checkout to create verified source
archives for the supported Windows 11 or Docker Compose runtimes:
```bash
python package.py --target windows
python package.py --target compose
```

Each ZIP is built only from tracked non-runtime files, contains a
`RELEASE-MANIFEST.json` with per-file SHA-256 checksums, and has a matching
`.zip.sha256` sidecar. Packaging refuses modified tracked files, secret paths,
credential-like files, runtime data, tests, and CI-only files. The old
unauthenticated Cloud Function and standalone mobile-upload packages are not
supported.

## Deployment

Use `Start-FAB.ps1` for the supported Windows runtime or the repository's three-service Docker Compose stack for container deployment. Optional supervised Windows cloud access uses `Start-FAB-Ngrok.cmd` and `Stop-FAB-Ngrok.cmd`; it exposes only the authenticated API/HAI surface, keeps the dashboard local, and refuses to reuse or stop another project's endpoint. FAB must remain on loopback or behind private networking, TLS, an authenticated reverse proxy, and a managed secret store. Unauthenticated Cloud Function deployment is not supported for financial data. See `docs/deployment_guide.md` and `docs/local_windows_ngrok_setup.md` for the verified procedures and acceptance boundaries.

## Contributing

Contributions are welcome! Please follow these steps:
1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/your-feature-name`).
3.  Make your changes.
4.  Write and run tests.
5.  Commit your changes (`git commit -m 'Add new feature'`).
6.  Push to the branch (`git push origin feature/your-feature-name`).
7.  Create a new Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details (if applicable).

## Contact

For operational support, use the sanitized support bundle from the FAB dashboard and the repository's configured support channel.


