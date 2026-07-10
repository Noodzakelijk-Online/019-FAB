# Posting Retries and Dead-Letter Handling

FAB now treats approved posting execution as a controlled external operation.

## Provider throttling and daily quotas

FAB treats a configured provider throttle differently from a failed posting.
Immediately before a Waveapps API request, the handler reserves a slot from the
shared API quota guard. In the authoritative operations ledger, an unavailable
slot changes the export attempt to `deferred` and stores `attemptCount`,
`retryAfterSeconds`, and `nextRetryAt` in redacted export metadata. The worker
does not claim the attempt again before that time. This does not consume a
failure count or create avoidable manual review. The compatibility executor
uses its older `posting_deferred` retry-queue state.

```ini
outbound_rate_limit_max_wait_seconds = 0
rate_limit_retry_delay_seconds = 60
quota_exhausted_retry_delay_seconds = 3600
```

The default is non-blocking so the worker stays responsive. `outbound_rate_limit_max_wait_seconds`
can be set to a small positive number when waiting briefly is acceptable.

## Why this exists

Bookkeeping postings must not be duplicated and must not disappear silently. External systems can fail, credentials can expire, browser automation can break, and network issues can happen. FAB therefore uses:

- atomic claim before execution;
- retry queue for temporary failures;
- dead-letter queue for repeated failures;
- manual review item when intervention is required;
- audit log for each step.

## Atomic claim

Before an operations-ledger export is executed, FAB atomically changes
`approved` or due `deferred` to `execution_in_progress`. The compatibility
executor similarly uses `posting_in_progress`. This prevents two workers from
executing the same approved attempt at the same time.

## Retry queue

Failed posting attempts are added to `retry_queue` with operation `execute_posting`.

Config knobs:

```ini
retry_max_attempts = 3
retry_base_delay_seconds = 300
worker_process_due_retries = true
```

The retry delay uses exponential backoff:

- 1st retry: base delay;
- 2nd retry: base delay × 2;
- 3rd retry: base delay × 4.

## Dead-letter queue

When the retry limit is reached, FAB moves the item to `dead_letter_queue`. That means a person must inspect and resolve it.

## Worker behavior

The compatibility worker cycle does this only when
`worker_process_legacy_postings = true`:

1. Run the normal FAB workflow.
2. Process due retries.
3. Process newly approved posting attempts.
4. Write all activity to the audit log.

## Safety default

The authoritative operations-ledger executor remains disabled unless
`fab_autonomy_execute_approved_exports = true` is set in local config. The
SQL retry/dead-letter queue documented below belongs to the compatibility
`posting_attempts` executor; operations-ledger quota deferral stays on the
authoritative `export_attempts` row and is visible in `/api/health`.

## Operational rule

Do not enable execution until credentials, target-account mapping, and at least several dry-runs have been manually verified.
