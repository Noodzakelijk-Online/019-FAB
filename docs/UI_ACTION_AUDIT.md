# UI Action Audit

Audit date: 2026-08-09

The operator dashboard is a functional control surface, not a mock dashboard. Its server-side gateway keeps the local API token out of browser responses and rejects insecure non-loopback HTTP endpoints.

| Surface | User action | Wired result | Safety behavior |
| --- | --- | --- | --- |
| Overview | Refresh | Refetches authoritative local resources | Stale/unavailable state remains labeled. |
| Intake | Upload files | `/api/intake/upload`, then imported-document processing | Type/size validation; no provider mutation. |
| Automation | Run eligible work | `/api/autonomy/run` | Disabled when plan is blocked, cycle active, or emergency stop engaged. |
| Automation | Stop automation | `/api/autonomy/emergency-stop` | Persistent and audited; blocks every next step. |
| Automation | Resume automation | `DELETE /api/autonomy/emergency-stop` | Exact phrase required; HAI cannot invoke it; active lease blocks clearing. |
| Reviews | Approve/reject/correct | `/api/review/<id>/resolve` | Corrections and learned rules are audited; posting remains separately gated. |
| Recovery | Create verified backup | `/api/backups` | Incomplete source evidence prevents a complete status. |
| Recovery | Create support bundle | `/api/support-bundles` | Generated ZIP is sanitized and ignored by Git. |
| Recovery | Open advanced recovery | Local maintenance console | Standard mode is restore-locked. Maintenance suppresses worker/HAI/cloud/normal mutations; exact confirmation and verified package evidence are required. |
| Delivery | Open work order/document | Local delivery/document endpoints | Shows missing attachment evidence; cannot imply archive completion. |
| Connections | Gmail/Drive setup | Credential install and OAuth authorization endpoints | Owner consent required; state is explicit. |
| Connections | Wave setup | Encrypted settings and validation endpoints | Business identity and account mapping must validate. |
| Connections | Receipt executor setup | Pairing manifest/status | Supervised browser bridge; no unbounded browser authority. |
| Advanced ledger and evidence links | Open ledger sections, work orders, report artifacts, recovery evidence, or connector contracts | Same-origin `/api/fab/operator-session` handoff followed by the protected Flask target | Operator/admin authorization; 45-second HMAC ticket; server-only API token; relative targets only; one-time nonce; redacted audit. Machine-facing HAI/executor URLs are unchanged. |
| Command drawer | Run bounded commands | Server allowlist in `fabLocalGateway.ts` | No arbitrary endpoint, path, or HTTP method from the browser. |

## Visual and accessibility checks

- Buttons use text plus Lucide icons where the operation is unfamiliar or high risk.
- Emergency state uses `role="alert"`; loading and data-state components expose status text.
- Tables use bounded wrappers and responsive layouts; the support/emergency controls collapse to one column on narrow viewports.
- Final browser geometry and interaction evidence is recorded in `FINAL_VERIFICATION_REPORT.md`.

## Remaining UI limitations

- Full WCAG conformance has not been independently audited.
- Provider-owned OAuth, Wave, MijnGeldzaken, and SVB pages are outside FAB's UI authority.
- Public pricing/account surfaces belong to the web shell and should not be treated as evidence of a deployed commercial service.
