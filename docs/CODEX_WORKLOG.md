# Codex Worklog

## 2026-08-09 - Control-center data path and dependency hardening

- Added compact Drive-to-Wave queue projections that preserve exact stage, review, retention, archive, and external-submission decisions while leaving complete evidence available from the default and per-document work-order endpoints.
- Added an exact-checksum master-ledger summary response for dashboard reads; complete JSON and CSV projections remain unchanged.
- Added two-second control-center request coalescing with generation-safe invalidation after writes, kept stale-resource fallback behavior, and scheduled the heaviest reads first within the four-request ceiling.
- Enabled compression for JSON/static responses above 1 KiB.
- On the live 150-document ledger, Drive/Wave list traffic fell from 988,287 to 141,040 bytes and master-ledger traffic from 202,949 to 918 bytes with the same checksum.
- Cold control-center refresh fell from 2.04-2.64 seconds to 1.35-1.65 seconds across the complete optimization and dependency-upgrade runs; an immediate repeat completed in 36-54 ms. Gzip reduced the roughly 508 KB browser response to 78,294 bytes.
- Upgraded the web dependency graph and removed the obsolete JSX-location plugin. The package audit fell from 86 findings to zero, with no peer-dependency errors and a reproducible frozen-lockfile install.
- Migrated the chart wrapper to current Recharts contracts and fixed its formatter payload so consumers receive the complete tooltip payload array.
- Fixed Express 5 SPA fallback routing after a production restart exposed the old bare-wildcard incompatibility; a real TCP test now protects nested dashboard routes.
- Vite 8 reduced transformed client modules from 6,221 to 2,426, reduced the Operations chunk to 192.70 KB, and eliminated the greater-than-500-KB public chunk warning.
- Verification passed 780 backend tests, 155 web tests, TypeScript checking, production builds, native and container runtime checks, dependency/peer audits, and desktop/mobile browser geometry and console inspection.
- No provider record was changed, no Drive file was archived, and no external submission was performed.

## 2026-08-09 - Reliability, migration, and API contract follow-up

- Normalized every JSON error below `/api/` to a correlated machine-readable envelope while preserving route-specific details.
- Added bounded request IDs, generic unexpected-error responses, and sanitized persistent failure audit events without exception messages or provider data.
- Hardened HAI request identifiers and executor failures so command responses and ledger audit events cannot leak executor exception details.
- Added ordered checksum-bound SQLite migration history with future/unknown/incomplete/tampered-history refusal.
- Added an automatic SQLite backup, integrity check, atomic SHA-256 manifest, and private file permissions before any populated legacy ledger is upgraded.
- Exposed persisted schema/backup status consistently through API health, doctor, and support diagnostics, including from a separate process.
- Replaced the failed-workflow health N+1 lookup with one bounded bulk query.
- Bounded serialized health/support issue details while retaining complete status, metrics, severity/type totals, next actions, notification materialization, exception queues, and autonomy/close safety decisions.
- Added a bounded two-second single-flight cache for identical read-only health projections; browser/proxy caching stays disabled and all financial safety paths remain uncached.
- Added configurable API/support diagnostic windows and fixed a mojibake separator in the legacy Wave operation table.
- Verified the real 180,838,400-byte pre-upgrade ledger snapshot independently: manifest hash matched and both integrity checks returned `ok`.
- Final verification passed 779 backend tests, 143 affected-path tests, 153 web tests, TypeScript checking, production web build, API image build, non-root Compose acceptance, and the native Windows runtime.
- Live native measurements: liveness 45 ms, five deep-health calls 259-412 ms, dashboard 310 ms, all with 441 real backlog issues retained as blockers rather than hidden.
- Real-ledger payload verification reduced default health JSON from 118,102 to about 18,505 bytes (84.3%) and doctor JSON from 77,448 to 24,544 bytes (68.3%) while preserving all 441 issue totals and on-demand full detail.
- Four-worker/20-request health acceptance improved from 3.14 to 26.11 requests/second; median latency improved from 1,006.6 to 8.1 ms and p95 from 2,226.5 to 703.5 ms, with one cache miss, 19 hits, and exact counts in every response.
- Fixed the Python container runtime baseline so the reviewed fail-closed defaults are loaded even without a mounted host config; Docker acceptance confirmed that optional Freshdesk intake and the legacy workflow stay disabled and produced no error log matches.
- No Wave/Google/provider record was changed, no Drive file was archived, and no external submission was performed.

## 2026-08-08 - Giant goal implementation audit

- Recorded `main` at starting commit `8a2b43d`; `origin/HEAD` also targets `main`.
- Inventoried the Python, React/Express, SQLite, worker, provider, CI, script, test, and documentation surfaces.
- Parsed the 116-phase implementation brief and mapped it against existing product behavior.
- Added a persistent `runtime_controls` ledger model and audited autonomy emergency-stop service.
- Checked the stop before each autonomous step, exposed API/dashboard controls, and allowed HAI to stop but never resume.
- Added sanitized doctor and support-bundle services, CLI, API, dashboard action, privacy contract, and tests.
- Removed fabricated testimonials, numeric outcomes, and unsupported direct-provider/security claims from English and Dutch public copy.
- Added required technical audit, critical path, acceptance, completion, verification, API/UI, security, operator, task graph, worklog, and checkpoint artifacts.
- Added production Waitress serving, authenticated constant-time liveness, SQLite WAL/busy waiting, bounded gateway concurrency, reduced read payloads, and review pagination after browser QA exposed lock contention and excessive mobile DOM height.
- Removed the N+1 trusted-category plan scan and reused one master-ledger/health evidence snapshot across autonomy, exception, and close decisions.
- Added non-root API/worker/web containers, Compose isolation, and a fail-closed ngrok verifier that does not disturb unrelated tunnels.
- Verification commands and final results are maintained in `FINAL_VERIFICATION_REPORT.md`.
- Final local verification passed 768 backend tests, 153 web tests, TypeScript checking, the production build, production Start/Stop, and a 26-resource API profile without SQLite lock errors.
- Built and executed both production containers. Compose passed authenticated API liveness, dashboard HTML, tRPC local-operator authorization, health checks, and non-root execution on configurable loopback ports.
- Removed the fixed Compose subnet after acceptance exposed a collision with an unrelated Docker network; added narrowly scoped Docker bridge-gateway trust and regression tests.
- Fixed a production-only bundled-server crash (`Dynamic require of "fs" is not supported`) with an ESM `createRequire` bridge and re-ran container acceptance.
- Verified implementation commit `c5e42aa` from a separate clean clone: source compilation, Compose parsing, clean status, and 123 focused tests passed.
- Scanned the staged implementation snapshot for runtime paths and high-confidence credential patterns; none were present.

## Explicitly not performed

- No live provider record was created, modified, or deleted during the code audit.
- No Drive source was archived.
- No credentials, OAuth tokens, financial files, or runtime database were added to Git.
- No direct MijnGeldzaken, PSD2, or SVB automation was invented to satisfy a checklist.
