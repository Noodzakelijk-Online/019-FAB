# Acceptance Tests

The final verification report records actual results. This file defines the release acceptance contract.

| ID | Test | Expected result |
| --- | --- | --- |
| A01 | Start with `Start-FAB.ps1 -NoBrowser` | API, worker, and dashboard bind to loopback and publish runtime identity. |
| A02 | Open `/admin/operations` | Live resource states appear; unavailable services are labeled and no fake data substitutes for them. |
| A03 | Upload a supported synthetic receipt | Source hash and provenance are recorded; processing creates extracted evidence or a reviewable failure. |
| A04 | Process low-confidence or incomplete evidence | Record enters review and cannot be posted externally. |
| A05 | Resolve a review | Corrections are audited and downstream work remains a draft until approved. |
| A06 | Prepare and approve an export | Approval is separate from execution and uses idempotent operation identity. |
| A07 | Engage emergency stop | Autonomy plan becomes blocked and no new workflow step starts. |
| A08 | Attempt HAI resume | Resume is unavailable to HAI; only the operator confirmation endpoint can clear the stop. |
| A09 | Create support bundle | ZIP contains only manifest, doctor, audit index, and README; known secrets and source identifiers are absent. |
| A10 | Create recovery package with missing source evidence | Package is not reported as complete. |
| A11 | Run reconciliation and reports | Discrepancies and provisional compliance state remain visible. |
| A12 | Attempt Drive archive without Wave attachment verification | Archive is blocked and the exact missing evidence is shown. |
| A13 | Verify desktop and mobile dashboard geometry | No horizontal page overflow, inaccessible controls, or clipped emergency/support actions. |
| A14 | Run Python and web verification suites | Tests, type check, and production build pass. |
| A15 | Inspect Git status and tracked files | No credentials, tokens, uploaded files, runtime databases, logs, or generated support ZIPs are tracked. |

## Live provider acceptance

These are blocked until real authorization is available:

- Google Drive: consent, approved folder listing, read-only import, source hash verification, and non-destructive archive dry run.
- Wave: business identity, chart mapping, synthetic record creation, receipt upload, attachment readback/hash evidence, and rollback guidance.
- MijnGeldzaken: operator review of the generated master-ledger artifact; no direct mutation is claimed.
