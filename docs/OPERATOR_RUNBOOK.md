# Operator Runbook

## Start and inspect

```powershell
.\Start-FAB.ps1 -NoBrowser
python -m src.run_fab_doctor
```

Open the dashboard URL printed by the launcher, normally `http://127.0.0.1:3000/admin/operations`. The local API normally uses `http://127.0.0.1:5001`.

The local API uses Waitress and an SQLite WAL ledger. `GET /api/live` is the fast authenticated process check; `GET /api/health` performs the deeper bookkeeping assessment. Use the dashboard Retry action if a cold backup-integrity scan causes one resource to be temporarily stale.

## Daily operation

1. Check source and provider readiness.
2. Sync configured read-only sources or upload documents.
3. Run eligible local work.
4. Resolve the exception and review queues.
5. Inspect routing/export drafts before approving external changes.
6. Run reconciliation and review discrepancies.
7. Generate due reports and compliance findings.
8. Confirm a current, source-complete recovery package exists.

## Emergency stop

Use **Stop automation** when provider behavior, duplicate risk, unexpected data, or a security concern needs investigation. An active step may finish, but no next step starts. HAI can stop FAB but cannot resume it.

To resume, wait until the active cycle lease is released, inspect audit/workflow evidence, enter `RESUME FAB AUTONOMY`, state why resumption is safe, and review the new autonomy plan.

## Provider activation

- Google: install the owner-approved desktop OAuth client, complete consent, and confirm the configured Gmail/Drive sources report ready.
- Wave: save the correct business ID and token, validate identity, choose the anchor/default category mappings, and pair the supervised receipt executor where attachment API coverage is unavailable.
- MijnGeldzaken: generate and inspect the supervised master-ledger export. Record completion manually; do not claim direct account mutation.

## Receipt archival rule

Never archive a Drive source merely because a Wave record exists. FAB must verify the target business, expected bookkeeping fields, the actual downstream attachment, and its evidence digest. Any ambiguity keeps the source in place.

## Diagnostics and recovery

```powershell
python -m src.run_fab_doctor --json
python -m src.run_fab_doctor --support-bundle
.\Stop-FAB.ps1
.\Test-FAB-Ngrok.ps1
```

Create a verified recovery package from the dashboard. Restore remains confirmation-gated in the local recovery console. Preserve the current database before repair and verify the restored checksum and source-evidence coverage.

### Schema upgrades and rollback

FAB records ordered, checksum-bound SQLite schema migrations. Before an existing ledger is upgraded, startup creates a private SQLite snapshot and JSON manifest in the ledger's sibling `schema_backups` directory. The snapshot must pass SQLite integrity verification, and its SHA-256 must match the manifest, before FAB changes the live schema. `/api/health`, the doctor report, and support diagnostics expose the current and supported schema versions without exposing ledger contents.

For rollback, stop FAB first. Preserve the failed live database and its WAL/SHM sidecars as incident evidence; do not overwrite or delete them. Verify the selected pre-upgrade snapshot against its JSON manifest and run `PRAGMA integrity_check` on a copy. Restore that verified copy atomically to the configured ledger path, then start the prior FAB release that supports the snapshot's source schema. Starting the newer release will intentionally upgrade it again. Keep both copies until the prior release starts, health is green, and document/audit counts have been reconciled.

## Verification

```powershell
python -m pytest -q -p no:cacheprovider -p no:stepwise
pnpm.cmd --dir web check
pnpm.cmd --dir web test
pnpm.cmd --dir web build
```
