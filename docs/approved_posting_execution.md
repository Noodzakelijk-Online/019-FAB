# Approved Posting Execution

FAB now separates posting into three stages:

1. Dry-run creation.
2. Human approval or rejection.
3. Execution of approved posting attempts.

## Safety Defaults

Approved posting execution is disabled unless the local config explicitly enables it.

The legacy `WorkflowController` also defaults to draft-only operation. It will
create an approval-required review item and an audited routing attempt instead
of calling a Waveapps or MijnGeldzaken handler directly. Do not enable direct
workflow dispatch in normal operation; use the export-attempt workflow so
approval, retries, and results remain in the local ledger.

Add these keys to the `[operations]` section in `config/config.ini` when the operator is ready:

```ini
fab_autonomy_execute_approved_exports = false
worker_process_approved_postings = true
worker_process_legacy_postings = false
workflow_execute_external_posting = false
```

Meaning:

- `fab_autonomy_execute_approved_exports = false` means approved operations-ledger export attempts are not executed automatically.
- `worker_process_approved_postings = true` means the worker checks the authoritative `export_attempts` queue, but execution still respects `fab_autonomy_execute_approved_exports`.
- `worker_process_legacy_postings = false` prevents the worker from polling deprecated `posting_attempts` in parallel.
- `workflow_execute_external_posting = false` keeps the legacy pipeline from bypassing FAB's draft/approval process.

To enable real execution after careful testing:

```ini
fab_autonomy_execute_approved_exports = true
```

## Manual Runner

Approved posting execution can be run manually with:

```powershell
python src\run_approved_postings.py
```

This runner prepares ready routes and processes approved attempts from
`LocalOperationsLedger`. It respects the same config safety flag and creates a
pre-execution ledger backup. It only falls back to legacy `posting_attempts`
when the operations ledger is not configured.

## MijnGeldzaken supervised submission

MijnGeldzaken does not use the Wave API execution path. Once an approved
operations-ledger export attempt reaches execution, FAB writes a durable CSV package to
`mijngeldzaken_export_dir`, records its SHA-256 checksum, changes the attempt to
`supervision_required`, and opens a review item. No stored MijnGeldzaken
username, password, or DigiD credential is used.

After the operator imports the package in a user-owned MijnGeldzaken session,
record completion through the token-protected dashboard API:

```text
POST /api/export-attempts/{export_attempt_id}/result
```

The JSON body must include `confirmation` with the exact value
`RECORD FAB EXPORT RESULT`, plus `status` (`executed`, `submitted`, or
`failed`) and optional `externalId`/`result` evidence. FAB then updates the
master ledger, resolves the supervision review item for a successful
submission, and writes an audit event. This endpoint records the observed
result; it does not log in to MijnGeldzaken or bypass DigiD.

The older `/posting-attempts/{attempt_id}/complete-supervised` endpoint remains
available only for compatibility with legacy databases. New operations use the
export-attempt endpoint above.

## Worker Execution

After each workflow cycle, the worker prepares export attempts from ready
routes and checks approved operations-ledger exports. Execution remains disabled
until `fab_autonomy_execute_approved_exports` is enabled. A backup is created
before any approved batch is processed; a failed backup blocks the entire batch.

## Audit Trail

Each execution attempt is written to the audit log:

- execution started
- posted
- posting failed
- manual review item created when posting fails

## Current Limitation

Wave expense execution uses the documented `moneyTransactionCreate` API contract.
Before FAB can submit, each Wave target needs a verified anchor account ID and
a category-to-account-ID mapping. FAB refuses to send a request when any of
those are absent and sends the item to review instead. The configuration
template shows the required fields under `[waveapps_business]` and
`[waveapps_personal]`; keep OAuth tokens out of `config.ini`.

Use the dashboard's **Refresh accounts** action or `POST /api/wave/accounts/discover`
to read the current chart of accounts. FAB records the read as an audited Wave
operation snapshot and shows whether each configured anchor/category ID still
exists before an approved export is dispatched.

MijnGeldzaken execution remains supervised. FAB prepares the artifact and
review state locally; the user-owned session performs the external import.
