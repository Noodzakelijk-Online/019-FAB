# Approved Posting Execution

FAB now separates posting into three stages:

1. Dry-run creation.
2. Human approval or rejection.
3. Execution of approved posting attempts.

## Safety Defaults

Approved posting execution is disabled unless the local config explicitly enables it.

Add these keys to the `[app]` section in `config/config.ini` when the operator is ready:

```ini
execute_approved_postings = false
worker_process_approved_postings = true
```

Meaning:

- `execute_approved_postings = false` means approved posting attempts are not executed automatically.
- `worker_process_approved_postings = true` means the worker will check the approved queue, but execution still respects `execute_approved_postings`.

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

## Worker Execution

The background worker also calls the approved-posting executor after each workflow cycle. The executor only processes records with status `approved`.

## Audit Trail

Each execution attempt is written to the audit log:

- execution started
- posted
- posting failed
- manual review item created when posting fails

## Current Limitation

The executor calls the current configured handlers. If a handler is still a placeholder or credentials are missing, the attempt will fail safely, be audit logged, and be sent to manual review rather than silently ignored.
