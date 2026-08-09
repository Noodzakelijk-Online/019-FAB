# Security

## Trust boundary

FAB is local-first, but it processes high-risk financial and health-related evidence. Local execution is not a reason to bypass authentication, review, least privilege, or provider policy.

## Controls

- API exposure defaults to loopback. Non-loopback access without a token is a readiness blocker.
- Google connectors require owner OAuth consent and read only configured sources.
- Wave tokens are stored through the local encrypted secret store; environment values may override local storage.
- Readiness and support APIs return configuration state, never secret values.
- External operations distinguish prepared, approved, executed, verified, ambiguous, and failed state.
- Runtime leases prevent overlapping autonomous cycles; idempotency keys prevent duplicate provider operations.
- The persistent emergency stop is audited and checked between workflow steps. HAI may engage it but cannot clear it.
- Drive archival requires downstream record and attachment readback evidence.
- Audit events redact sensitive details before persistence.

## Support bundle privacy contract

`python -m src.run_fab_doctor --support-bundle` creates an ignored ZIP under `output/support`. It excludes documents, OCR text, ledger rows, filenames, amounts, local paths, configuration values, and credentials. Review the ZIP before sharing it anyway.

## Operator duties

- Keep `config/config.ini`, `.encryption_key`, `credentials/`, `tokens/`, `data/`, `downloads/`, `logs/`, and `output/` out of Git.
- Revoke and rotate credentials after suspected disclosure.
- Use provider MFA where available; FAB does not replace provider MFA.
- Do not enable external execution or Drive archival until the live acceptance checks pass.
- Treat Dutch VAT, retention, PGB, and tax output as provisional until reviewed by a qualified professional.

## Not claimed

The repository is not independently penetration-tested, certified by the Dutch DPA, or proven compliant merely because controls exist. Direct SVB submissions, direct PSD2 feeds, and direct MijnGeldzaken account mutation are not implemented.
