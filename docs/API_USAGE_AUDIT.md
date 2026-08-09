# API Usage Audit

## Local API

The Flask API is the source of operational truth. Major endpoint groups are:

| Group | Representative endpoints | Mutation policy |
| --- | --- | --- |
| Liveness/health/readiness | `/api/live`, `/api/health`, `/api/settings`, `/api/doctor` | `/api/live` is constant-time; deeper reports are read-only and secret-redacted. Health detail is prioritized and bounded while exact totals remain available. |
| Intake/documents | `/api/intake/upload`, `/api/intake/rescan`, `/api/documents/*` | Local evidence writes only. |
| Reviews/categories | `/api/review`, `/api/review/<id>/resolve`, `/api/categories/*` | Operator decisions are audited. |
| Autonomy/workflows | `/api/autonomy/plan`, `/api/autonomy/run`, `/api/workflows/*` | Lease, safety, recovery, and emergency-stop gated. |
| Emergency control | `/api/autonomy/emergency-stop` | Any operator/HAI may stop; only operator DELETE with exact phrase may resume. |
| Routing/exports | `/api/routing/*`, `/api/exports/*` | Preparation, approval, execution, and verification remain distinct states. |
| Wave | `/api/wave/*`, `/api/drive-wave/*` | Capability and business mapping gated; attachment verification required before archival. Work-order lists accept `view=summary` for queue rendering while the default and per-document endpoints retain complete executor/evidence payloads. |
| Reconciliation/reporting | `/api/reconciliation/*`, `/api/report-runs/*`, `/api/compliance/*`, `/api/master-ledger` | Local computation; provisional findings are labeled. `summaryOnly=true` returns the exact checksum and aggregate projection without serializing rows to the caller. |
| Recovery/support | `/api/backups`, `/api/support-bundles` | Restore is confirmation-gated; support output is sanitized. |
| HAI | `/api/hai/status`, `/api/hai/manifest`, `/api/hai/commands/execute` | Fixed command allowlist, normalized payloads, no external approval or emergency-stop clear. |

## Web gateway

The Express/tRPC gateway calls fixed local paths from `web/server/fabLocalGateway.ts`. The browser supplies a typed command ID, never an arbitrary URL. The gateway:

- validates endpoint scheme/origin;
- adds the local API bearer token server-side;
- applies timeouts, a four-read concurrency bound, and a bounded projection before returning data;
- caches only read resources for degraded/stale display;
- coalesces identical control-center reads for two seconds and invalidates that snapshot after every successful mutation;
- compresses responses larger than 1 KiB for browser/ngrok clients;
- does not convert an API error into success;
- uses role-gated `fabOperatorProcedure` for financial operations.

## Provider APIs

- Google connectors use owner OAuth and scoped read operations against configured sources.
- Wave GraphQL coverage is capability-based. Receipt attachment work can require a supervised executor when the API cannot provide the necessary action/readback.
- MijnGeldzaken is an artifact export with supervised completion tracking.
- Direct PSD2 and SVB mutation APIs are absent and are not advertised as live.

## Error contract

Every JSON error below `/api/` has the same transport envelope: `success=false`, `status`, `errorCode`, `message`, and `requestId`. Route-specific fields such as `error`, validation details, or provider state are preserved. FAB accepts a caller-provided `X-Request-ID` only when it is a bounded safe identifier; otherwise it creates one and always returns the effective value in the response header and body. Unexpected exceptions return a generic message and create a sanitized correlated ledger audit event plus local log entry without exposing financial or provider details.

`GET /api/health` computes the complete issue set before deriving status, severity counts, metrics, type counts, and next actions. It returns the highest-priority issue-detail window only: 50 by default and 1-500 through `issueLimit`. `issueCount`, `issueTypeCounts`, `issuesReturned`, and `issuesTruncated` distinguish complete aggregate evidence from the bounded detail array. Identical read-only projections are coalesced in an eight-entry, two-second server cache; `X-FAB-Health-Cache` reports `hit`, `miss`, or `disabled`, while browser/proxy caching remains `no-store`. Internal autonomy, notifications, close readiness, exception materialization, and every external-execution gate continue to read the ledger directly and never use this cache.
