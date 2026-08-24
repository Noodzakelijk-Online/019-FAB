# FAB - Financial Automation Bookkeeper

FAB is a local-first bookkeeping automation system for collecting financial
documents, extracting bookkeeping facts, routing them through review and
approval, preparing downstream accounting actions, reconciling evidence, and
keeping an auditable local ledger.

The intended operating model is:

```text
End user / operator <-> FAB <-> supervised or API-backed bookkeeping providers
```

FAB is built to become the primary source of truth for the operator's financial
document workflow. It does not treat external systems as a place to blindly push
data. Every meaningful action is tracked locally first, and high-risk provider
changes remain gated by capability checks, explicit approval, idempotency,
readback evidence, and recoverable audit trails.

## Current Status

The repository contains a working local application, not only a prototype:

- Python 3.13 bookkeeping engine, local operations API, recurring worker, OCR
  pipeline, connector intake, SQLite operations ledger, backup and recovery
  services.
- React/Node operator dashboard for health, activation, intake, review,
  automation, reconciliation, reporting, recovery, exports, Wave setup, Google
  setup, and HAI control.
- Windows 11 launcher scripts, Docker Compose runtime, managed ngrok helpers,
  packaging, GitHub Actions CI, and broad Python/web regression tests.
- Guarded HAI connector surfaces for bounded control and status, without
  granting HAI authority to approve exports, clear emergency stops, restore
  backups, change permissions, or submit downstream bookkeeping changes.

Important live-provider limits are intentional and must not be hidden:

- Google Gmail and Drive require owner OAuth consent before FAB can read real
  mailbox/folder sources.
- Wave requires a valid user-owned Wave token, business ID, verified account
  mappings, and in some cases a supervised receipt executor because Wave's
  public API does not cover every receipt attachment/readback action FAB needs.
- MijnGeldzaken is handled as supervised export artifacts. FAB does not store
  DigiD credentials and does not claim direct MijnGeldzaken account mutation.
- Direct PSD2 bank feeds, SVB submissions, tax filings, and legal/accountant
  sign-off are not implemented. Bank statement import and provisional VAT
  evidence are local bookkeeping aids, not official filings.
- Google Drive source archival is disabled until FAB verifies the exact
  downstream Wave record and the actual stored attachment through binary
  readback. A matching record or visible icon is not enough.

See [docs/GOAL_COMPLETION_MATRIX.md](docs/GOAL_COMPLETION_MATRIX.md) for the
full implemented/partial/blocked matrix.

## Who This Is For

For non-technical operators, FAB is the control room for a bookkeeping process:

- Put receipts, invoices, scans, bank statements, and supporting files into the
  configured sources.
- Let FAB collect, OCR, classify, validate, group, deduplicate, and prepare the
  bookkeeping work.
- Review only the exceptions, uncertain fields, duplicate candidates, and
  high-risk provider actions.
- Approve or reject drafts with visible evidence.
- Keep source files, local records, external operations, Wave readback evidence,
  reports, and recovery packages traceable.

For developers, FAB is a Python + SQLite + Flask/Waitress backend, a React +
Express/tRPC frontend, and a set of local automation services organized around
an operations ledger. The codebase is intentionally conservative about external
automation: local computations can run autonomously, while provider mutations
must pass explicit safety gates.

## Core Workflow

FAB's protected path is:

```text
source intake
-> immutable evidence
-> OCR and field extraction
-> validation
-> categorization
-> duplicate and document-group handling
-> manual review where needed
-> local bookkeeping record
-> routing draft
-> explicit approval
-> supported provider execution
-> provider readback and attachment verification
-> reconciliation
-> reports
-> verified backup or export
```

The key invariants are documented in
[docs/CRITICAL_PATH.md](docs/CRITICAL_PATH.md). In short: source bytes are
hashed before processing, uncertain data pauses for review, duplicates cannot
post twice, preparing an external operation is not the same as executing it,
and archival requires proof that the external attachment and bookkeeping fields
match the retained source evidence.

## Main Capabilities

### Intake and Source Evidence

- Local folder intake from configured folders such as `downloads/sort-out`.
- Authenticated browser uploads through the operator dashboard.
- Gmail connector with an optional strict scanner-mailbox profile. This ports
  the useful behavior from `Noodzakelijk-Online/025-Scan-to-folder-automation`
  into FAB directly: trusted sender, PDF filename/MIME/signature validation,
  content-addressed local evidence, provider checkpointing, and no source email
  mutation.
- Google Drive connector for configured folders, including source provenance,
  duplicate/revision evidence, and optional move-only archival after Wave
  verification.
- Freshdesk financial-ticket intake profile for read-only ticket and PDF
  attachment evidence. FAB never closes tickets or copies evidence to Drive as
  a side effect.
- Supervised Google Photos Picker intake. The worker does not scan whole Google
  Photos libraries.

### Document Understanding

- Tesseract OCR with Dutch and English language support.
- Optional Google Cloud Vision OCR provider when configured.
- Image preprocessing through private temporary copies: grayscale, denoising,
  deskew, and binarization.
- PDF-to-image conversion through Poppler for OCR.
- Dutch/English language-aware processing.
- Financial field extraction for vendor, date, amount, VAT/BTW, currency,
  references, line items, category evidence, and confidence/provenance.
- Vendor templates and deterministic extraction rules.
- Duplicate detection using content, provider identity, validated references,
  and document grouping.

### Categorization and Learning

- Fixed conservative vendor taxonomy for trusted exact-vendor suggestions.
- Rule-based, ML, fallback, and hybrid categorizer modules.
- Review-based learning: explicit approved corrections can create explainable
  vendor/category rules.
- FAB does not fabricate training data and does not treat model confidence as
  permission to bypass validation, duplicate review, external approval, or
  archival gates.

### Review, Routing, and Export Control

- Review queue with source-backed correction handling.
- Draft routing into target systems such as Wave Business, Wave Personal, or
  MijnGeldzaken.
- Approval-gated export attempts with operation IDs, idempotency keys, approval
  status, execution state, redacted results, and audit history.
- Pre-execution backups for approved batches.
- Quota/throttle deferral instead of silent failure.
- Supervised completion tracking for artifact-based flows.

### Wave Support

FAB models Wave as a downstream bookkeeping surface, with local FAB records as
the decision source:

- Store Wave business/account setup locally through encrypted settings or
  environment variables.
- Validate Wave identity and read account/category data.
- Map FAB category intents to Wave chart-of-account IDs.
- Mirror customers, products/services, and invoices read-only for routing and
  drift detection.
- Prepare Wave operations only when required fields and account mappings are
  present.
- Execute supported Wave money-transaction actions only after approval and
  capability checks.
- Coordinate a supervised receipt executor for attachment upload/readback when
  the public Wave API cannot provide the required receipt workflow.
- Require binary readback evidence before Drive archival.

The Drive-to-Wave contract is documented in
[docs/drive_wave_delivery.md](docs/drive_wave_delivery.md).

### MijnGeldzaken Support

FAB prepares checksum-bound CSV/JSON artifacts for supervised MijnGeldzaken
handling. The operator completes the account-side action in a user-owned
session and records the result back in FAB.

FAB intentionally does not store MijnGeldzaken passwords, DigiD details, or
unattended browser credentials.

### Banking, Reconciliation, Reports, and Compliance

- Local bank statement import for supported CSV/JSON/CAMT/MT940-like data.
- Reconciliation between imported bank rows and bookkeeping documents.
- Missing receipt and unmatched transaction review handling.
- Provisional financial reports with checksum-bound JSON/CSV artifacts.
- Scheduled local report generation.
- Provisional Dutch VAT and seven-year source-retention evidence.
- Notification center for health, due work, compliance findings, and Wave
  invoice deadlines.

These features support bookkeeping control and review. They do not file tax
returns, submit to authorities, or replace professional advice.

### Backup, Recovery, and Auditability

- SQLite operations ledger with WAL, migrations, integrity checks, and
  migration snapshots.
- Source-complete recovery packages with manifest-bound SHA-256 checksums.
- Local maintenance mode for restore operations. The worker, normal mutations,
  ngrok, and HAI command execution are locked during maintenance.
- Pre-restore package creation, source-byte verification, immutable source
  recovery tree, ledger path rewriting, and rollback after failed final checks.
- Sanitized support bundles that exclude credentials, raw documents, OCR text,
  filenames, local paths, and amounts.
- Audit events with sensitive fields redacted before persistence.

### HAI Connector

The HAI connector exposes bounded discovery, status, resources, and governed
commands under `/api/hai/*`.

HAI can help inspect status and trigger low-risk local work such as intake,
processing, reconciliation, due reports, compliance assessment, notification
refresh, and emergency stop. It cannot:

- approve export drafts;
- execute provider submissions by itself;
- clear emergency stop;
- restore backups;
- change access controls or secrets;
- bypass review, duplicate, attachment, or archive gates.

## Architecture

### Backend

The backend is Python 3.13. Major areas:

```text
src/operations/          Local API, ledger, readiness, autonomy, exports,
                         review, recovery, HAI, Wave/Drive delivery
src/worker/              Recurring authoritative worker
src/document_fetchers/   Gmail, Drive, Freshdesk, Photos Picker, local folder
src/document_processors/ OCR, preprocessing, extraction, templates, line items
src/categorizers/        Rule, ML, hybrid, fallback categorization
src/data_entry/          Wave, MijnGeldzaken, safe posting, provider surfaces
src/reconciliation/      Transaction/document matching
src/backup/              Backup and restore support
src/security/            Encryption, OAuth token storage, local secret store
src/workflow/            State, safety, logging, autonomous playbook
tests/                   Python regression and safety suite
```

The authoritative local API is `python -m src.operations.local_api`. It serves
authenticated JSON endpoints under `/api/*`, uses Waitress in supported local
runtime, and stores operational truth in `data/fab_operations.sqlite3` by
default.

The recurring worker is `python -m src.run_worker`. It runs connector intake,
local autonomy, scheduled backups, reports, compliance checks, notifications,
export execution gates, Drive archival checks, and recovery handling as
isolated audited stages.

### Frontend and Gateway

The web app lives in `web/`:

```text
web/client/              React operator dashboard
web/server/              Express/tRPC gateway and standalone server
web/shared/              Shared types and provider surface definitions
web/drizzle/             Web database schema/migrations
web/server/lib/          Logging, loopback checks, rate limiting, sanitization
```

The browser never receives the hidden local API token. The Express gateway
adds it server-side, calls fixed local endpoints, validates origins, applies
timeouts and bounded projections, compresses large responses, and keeps
operator links protected through short-lived one-time handoff tickets.

The main operator page is:

```text
http://127.0.0.1:<dashboard-port>/admin/operations
```

The launcher records the actual ports in `data/fab-runtime.json` after proving
that the API, worker, and dashboard belong to this checkout.

### Storage

Runtime data is intentionally local and ignored by Git:

```text
config/config.ini
credentials/
tokens/
data/
downloads/
logs/
output/
web/node_modules/
.venv/
```

Do not commit real financial files, ledgers, tokens, support bundles, or
provider credentials.

## Quick Start for Operators on Windows 11

1. Install Git. Install Python 3.13 if the launcher cannot provision it through
   the Windows Python launcher or `uv`.
2. Clone the repository:

   ```powershell
   git clone https://github.com/Robert-Velhorst/019-FAB.git
   cd 019-FAB
   ```

3. Start FAB:

   ```powershell
   .\Start-FAB.cmd
   ```

   The launcher creates the project-local `.venv`, installs missing Python and
   dashboard dependencies, builds or starts the dashboard, checks Tesseract and
   Poppler, starts the local API and worker, selects safe loopback ports, and
   opens the dashboard.

4. In the dashboard, use **Finish activation** and **Connections** to configure
   Gmail, Google Drive, Wave, OCR, intake folders, and review settings.

5. Add files through:

   - the configured local intake folder;
   - Google Drive folder sync;
   - Gmail scanner/source sync;
   - Freshdesk source sync;
   - dashboard **Add receipts** upload.

6. Resolve review items and only approve external drafts after checking the
   evidence shown by FAB.

To stop only this checkout's FAB services:

```powershell
.\Stop-FAB.cmd
```

For maintenance/recovery:

```powershell
.\Start-FAB-Maintenance.cmd
```

See [docs/OPERATOR_RUNBOOK.md](docs/OPERATOR_RUNBOOK.md) and
[docs/user_guide.md](docs/user_guide.md).

## Developer Setup

### Prerequisites

- Python 3.13.
- Node.js 22.
- pnpm 11.20.0.
- Tesseract OCR with `eng` and `nld` language data.
- Poppler PDF tools for PDF OCR.
- Docker Desktop or Docker Engine if using Compose.

### Python backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --disable-pip-version-check -r requirements.txt pytest
python -m src.operations.local_api
```

The local API defaults to:

```text
http://127.0.0.1:5001
```

Set a strong `operations.api_token` in `config/config.ini` or set
`FAB_LOCAL_API_TOKEN` before exposing anything beyond loopback.

### Web dashboard

```powershell
Copy-Item web\.env.example web\.env
pnpm.cmd --dir web install --frozen-lockfile
pnpm.cmd --dir web dev
```

For manual development, set these in `web/.env`:

```text
FAB_LOCAL_API_URL=http://127.0.0.1:5001
FAB_LOCAL_API_PUBLIC_URL=http://127.0.0.1:5001
FAB_LOCAL_API_TOKEN=<same long token as the Python API>
FAB_OPERATIONS_SERVICE_TOKEN=<same long token as the Python API>
JWT_SECRET=<long random secret>
FAB_OPERATOR_LOCAL_MODE=true
```

Use `pnpm.cmd` on Windows when PowerShell cannot resolve the `pnpm` shim.

### One-shot workflow cycle

Run exactly one governed local cycle:

```powershell
python -m src.main
```

If the recurring worker already owns the runtime lease, the command exits
without starting a duplicate cycle.

## Configuration

Start from:

```powershell
Copy-Item config\config_template.ini config\config.ini
```

The template documents all major sections:

- `[operations]`: local ledger, API host/port/token, HAI allowlist, intake
  paths, backup/report directories, autonomy, worker schedule, health limits,
  reports, notifications, VAT/retention settings.
- `[document_processing]`: OCR method, Tesseract, Poppler, preprocessing,
  template matching, line items, VAT extraction safety.
- `[gmail]`: Gmail source, scanner mode, trusted senders, limits, OAuth paths.
- `[google_drive]`: Drive intake folder, archive folder, relay size, OAuth
  paths, archival gates.
- `[freshdesk]`: read-only financial-ticket profile and attachment policy.
- `[google_photos]`: supervised Picker settings.
- `[waveapps]`, `[waveapps_business]`, `[waveapps_personal]`: Wave GraphQL URL,
  business IDs, category mappings, account IDs, and token settings.
- `[wave_receipt_executor]`: supervised receipt upload/readback coordination.
- `[mijngeldzaken]`: supervised export artifact settings.

Environment variables override config values. Keep credentials out of Git and
prefer the dashboard's encrypted local setup or environment variables for
secrets.

## Testing and Verification

Run the backend suite:

```powershell
python -m pytest -q -p no:cacheprovider -p no:stepwise
```

Run the web checks:

```powershell
pnpm.cmd --dir web check
pnpm.cmd --dir web test
pnpm.cmd --dir web build
```

Run dependency checks used by CI:

```powershell
pnpm.cmd --dir web audit --audit-level=high
pnpm.cmd --dir web peers check
```

GitHub Actions runs:

- backend on Linux;
- backend on Windows across four shards;
- web frozen install, high-severity audit, peer check, TypeScript check, Vitest,
  and production build.

The latest verification evidence is kept in
[docs/FINAL_VERIFICATION_REPORT.md](docs/FINAL_VERIFICATION_REPORT.md).

## Docker Compose

Set required secrets and start the three-service stack:

```powershell
$env:FAB_LOCAL_API_TOKEN = "<long random token>"
$env:FAB_WEB_JWT_SECRET = "<long random secret>"
docker compose up --build
```

Compose runs:

- `api`: Python local operations API;
- `worker`: Python recurring worker;
- `web`: production React/Express dashboard.

The stack binds published ports to loopback by default and stores persistent
state in Compose volumes plus the mounted local intake folder. Remote or cloud
deployment must add TLS, an authenticated reverse proxy, managed secrets, and
provider acceptance checks. Unauthenticated Cloud Function deployment is not
supported for financial data.

## Packaging

Create clean, checksum-bound release archives from a committed checkout:

```powershell
python package.py --target windows
python package.py --target compose
```

Packaging refuses dirty tracked files, tests, runtime data, credential-like
paths, unsupported old entrypoints, and oversized/unsafe archive contents. Each
ZIP includes a `RELEASE-MANIFEST.json` and a `.zip.sha256` sidecar.

## Local Cloud Access with ngrok

FAB can expose only the authenticated API/HAI surface through managed ngrok.
The operator dashboard stays local.

```powershell
.\Start-FAB-Ngrok.cmd
```

If another ngrok endpoint is already online, FAB refuses to pool, stop, or
reuse it. Reserve a dedicated FAB endpoint and pass it explicitly:

```powershell
.\Start-FAB-Ngrok.cmd -Url https://your-reserved-endpoint.example
```

See [docs/local_windows_ngrok_setup.md](docs/local_windows_ngrok_setup.md).

## Security and Privacy Model

FAB processes high-risk financial evidence. Its defaults are designed to fail
closed:

- API and dashboard bind to loopback by default.
- Non-loopback API access requires a strong bearer token.
- The browser never receives the hidden API token.
- Provider credentials are stored in ignored local files, encrypted local
  settings, or environment variables.
- Readiness, health, errors, logs, support bundles, and audit records redact
  secrets and bound provider diagnostics.
- Runtime leases prevent overlapping autonomous cycles and duplicate external
  actions.
- Export execution is separate from draft preparation and approval.
- Emergency stop blocks new autonomous work until an operator clears it with
  the exact confirmation flow.
- Drive archival requires Wave transaction, field, and attachment evidence.
- Maintenance mode disables normal mutations and HAI execution before restore.

See [docs/SECURITY.md](docs/SECURITY.md) and
[docs/security_approach.md](docs/security_approach.md).

## Documentation Map

- [docs/user_guide.md](docs/user_guide.md): operator guide.
- [docs/OPERATOR_RUNBOOK.md](docs/OPERATOR_RUNBOOK.md): daily operation,
  emergency stop, provider activation, diagnostics, recovery.
- [docs/technical_reference.md](docs/technical_reference.md): module and data
  flow reference.
- [docs/API_USAGE_AUDIT.md](docs/API_USAGE_AUDIT.md): local API, web gateway,
  provider API, and error-contract audit.
- [docs/UI_ACTION_AUDIT.md](docs/UI_ACTION_AUDIT.md): dashboard action
  inventory.
- [docs/ACCEPTANCE_TESTS.md](docs/ACCEPTANCE_TESTS.md): release acceptance
  contract.
- [docs/GOAL_COMPLETION_MATRIX.md](docs/GOAL_COMPLETION_MATRIX.md): implemented,
  partial, blocked, and intentionally absent capabilities.
- [docs/FINAL_VERIFICATION_REPORT.md](docs/FINAL_VERIFICATION_REPORT.md):
  current verification evidence and provider-live blockers.
- [docs/scanner_mailbox_migration.md](docs/scanner_mailbox_migration.md):
  consolidation of repository 025 scan-to-folder behavior.
- [docs/drive_wave_delivery.md](docs/drive_wave_delivery.md): high-assurance
  Drive/Gmail source to Wave attachment delivery.
- [docs/local_windows_ngrok_setup.md](docs/local_windows_ngrok_setup.md):
  Windows and managed ngrok setup.
- [docs/deployment_guide.md](docs/deployment_guide.md): deployment and
  operations notes.
- [docs/TECHNICAL_AUDIT.md](docs/TECHNICAL_AUDIT.md): technical audit and debt
  record.

## Repository Hygiene

Before publishing changes:

```powershell
git status --short
git diff --check
python -m pytest -q -p no:cacheprovider -p no:stepwise
pnpm.cmd --dir web check
pnpm.cmd --dir web test
pnpm.cmd --dir web build
```

Stage only intended files. Do not use broad staging commands when runtime data
or credentials may exist locally.

## Contributing

1. Create a feature branch.
2. Keep changes scoped to the affected runtime, module, or documentation area.
3. Add or update tests for behavior changes.
4. Preserve fail-closed provider behavior and truthful capability states.
5. Run the verification commands above.
6. Open a pull request with clear local, CI, browser, packaging, and provider
   acceptance evidence where relevant.

## License

`web/package.json` declares the web package as MIT, but this repository does
not currently contain a repository-level `LICENSE` file. Treat the repository
license as unset until a top-level license file is added.

## Support

For operational support, generate a sanitized support bundle from the FAB
dashboard or with:

```powershell
python -m src.run_fab_doctor --support-bundle
```

Review the bundle before sharing. It is designed to exclude source documents,
OCR text, financial identifiers, local paths, credential values, and tokens.
