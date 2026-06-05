# Posting Retries and Dead-Letter Handling

FAB now treats approved posting execution as a controlled external operation.

## Why this exists

Bookkeeping postings must not be duplicated and must not disappear silently. External systems can fail, credentials can expire, browser automation can break, and network issues can happen. FAB therefore uses:

- atomic claim before execution;
- retry queue for temporary failures;
- dead-letter queue for repeated failures;
- manual review item when intervention is required;
- audit log for each step.

## Atomic claim

Before a posting attempt is executed, FAB changes the status from `approved` to `posting_in_progress` in one database update. This prevents two workers from executing the same approved attempt at the same time.

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

The worker cycle now does this:

1. Run the normal FAB workflow.
2. Process due retries.
3. Process newly approved posting attempts.
4. Write all activity to the audit log.

## Safety default

Execution remains disabled unless `execute_approved_postings = true` is set in local config.

## Operational rule

Do not enable execution until credentials, target-account mapping, and at least several dry-runs have been manually verified.
