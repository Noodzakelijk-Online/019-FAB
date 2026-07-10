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

Add these keys to the `[app]` section in `config/config.ini` when the operator is ready:

```ini
execute_approved_postings = false
worker_process_approved_postings = true
workflow_execute_external_posting = false
```

Meaning:

- `execute_approved_postings = false` means approved posting attempts are not executed automatically.
- `worker_process_approved_postings = true` means the worker will check the approved queue, but execution still respects `execute_approved_postings`.
- `workflow_execute_external_posting = false` keeps the legacy pipeline from bypassing FAB's draft/approval process.

To enable real execution after careful testing:

```ini
execute_approved_postings = true
```

## Manual Runner

Approved posting execution can be run manually with:

```powershell
python src\run_approved_postings.py
```

This runner respects the same config safety flag.

## MijnGeldzaken supervised submission

MijnGeldzaken does not use the Wave API execution path. Once an approved
posting attempt reaches the handler, FAB writes a durable CSV package to
`mijngeldzaken_export_dir`, records its SHA-256 checksum, changes the attempt to
`supervision_required`, and opens a review item. No stored MijnGeldzaken
username, password, or DigiD credential is used.

After the operator imports the package in a user-owned MijnGeldzaken session,
record completion through the token-protected dashboard API:

```text
POST /posting-attempts/{attempt_id}/complete-supervised
```

The JSON body must include `confirmation` with the exact value
`CONFIRM EXTERNAL SUBMISSION`. Optional evidence is restricted to
`submitted_at`, `receipt_reference`, `note`, and `artifact_sha256`. FAB then
marks the attempt and document as posted, resolves the supervision review item,
and writes an audit event. This endpoint records the observed result; it does
not log in to MijnGeldzaken or bypass DigiD.

## Worker Execution

The background worker also calls the approved-posting executor after each workflow cycle. The executor only processes records with status `approved`.

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

MijnGeldzaken browser execution remains supervised and is still dependent on
an explicitly approved export attempt and a verified current browser surface.
