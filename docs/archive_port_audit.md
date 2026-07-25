# FAB archive port audit

Audit date: 2026-07-26

## Archives reviewed

- `fab-website.zip`
- `019 _ Unified Financial Document Management Automation platform (FAB).zip`
- `019 - FAB V2.zip`

## Ported

### Ledger-native anomaly detection

The V2 archives contained early anomaly and discrepancy detectors. Their useful
idea has been rewritten as `src/operations/local_anomalies.py` and connected to
FAB's authoritative exception queue.

The implementation:

- reads normalized bookkeeping records from the local operations ledger;
- detects future-dated records;
- detects unusually high vendor or category amounts only when enough comparable
  history exists;
- uses median and median absolute deviation instead of an average-only outlier
  test;
- uses a conservative ratio fallback when historical values have zero variance;
- emits versioned evidence, sample counts, baselines, ratios, and scores;
- never changes a record or submits data externally;
- links each anomaly to the existing record and master-ledger review actions;
- can be disabled or tuned through local configuration.

## Already present in newer form

The following V2 ideas were not copied because the canonical repository already
contains stronger, tested implementations:

- per-service rate limits and daily quotas;
- fuzzy vendor identification and category history;
- OCR pipelines and fallbacks;
- document identity, duplicate prevention, and version evidence;
- governed autonomy, retries, recovery, and audit logs;
- progress and workflow-step evidence;
- reporting, backups, reconciliation, and close readiness;
- Google Drive, Gmail, Wave, and MijnGeldzaken control surfaces;
- the React operator dashboard and local API.

## Not ported

- The website archive is an older generic marketing/dashboard scaffold already
  superseded by `web/`.
- The unified-platform archive primarily contains plans, research, screenshots,
  and generated marketing assets rather than compatible runtime code.
- Plaintext `credentials.ini`, browser-login automation, and code that performs
  direct downstream mutations were excluded.
- Simulated, placeholder, or incomplete learning modules were excluded.
- Malformed files, archive placeholders such as `Inherited file content will not
  be shown`, and modules that fail Python compilation were excluded.
- Duplicate HTML dashboards and setup wizards were excluded.
- Nested generated release archives, logs, and environment-specific paths were
  excluded.
- Heuristics such as flagging all round amounts or weekend expenses were
  excluded because they create weak, non-accounting-specific alerts.
- Receipt splitting rules that guessed VAT rates or tax deductibility from
  keywords were excluded because those decisions require evidence and explicit
  policy, not a generic heuristic.

The source archives remain external reference material. They are not runtime
dependencies of FAB.
