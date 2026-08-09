# Final Verification Report

Status: locally and container verified; provider acceptance remains blocked

This report separates local software verification from provider, account, infrastructure, and human acceptance. A green suite does not by itself authorize live financial mutations.

## Baseline

- Working/default branch: `main` / `main`.
- Starting commit: `8a2b43d`.
- Prior implementation commit: `98dbd51`.
- Reliability hardening commit: `182373f`.
- Health and deployment efficiency commit: `8b3d1a7`.
- Control-center hardening commit: `d563d95`.
- Production-runtime implementation commit: `2f70668`.
- Managed-cloud and runtime-efficiency implementation commit: `76e5fff`.
- Worker, OCR, and local-session hardening implementation commit: `b228fdc`.
- Dependency-safe workflow continuation commit: `3f2d5c6`.
- Quiescent maintenance and full recovery implementation commit: `312ec34`.
- Authoritative review-readiness implementation commit: `53d8e21`.
- Final evidence commit: recorded by the final Git push and delivery response.

## Results

| Check | Result | Evidence |
| --- | --- | --- |
| Python compile | Pass | Changed operations modules compile and run in the isolated Python 3.13 runtime used by Windows and containers. |
| Focused changed-path tests | Pass | The recovery and scheduler suites passed `17`; autonomy passed `26`; focused API rendering passed. This covers exact dependency continuation, output-bound no-op behavior, high-risk exclusion, direct-executor misuse, attempts and roles, continuation failure, next-point recovery, scheduling, and API/dashboard projection. |
| Full backend tests | Pass | Final CI-equivalent source rerun: `793 passed`, `4 skipped`. This includes quiescent ledger/source recovery, tamper/collision/rollback handling, maintenance mutation guards, dependency-safe workflow continuation, authoritative worker ownership, governed vendor templates, private OCR preprocessing/cleanup, encrypted runtime secrets, managed cloud ownership/status, document-group review pagination, authoritative queue-wide safety totals, bounded caches/projections, and release packaging safety. |
| Web type check | Pass | `pnpm check`. |
| Web tests | Pass | 17 files, `165 passed`; this includes public/private API address separation, browser-origin validation, recovery-policy redaction, bounded review-page projection, local-operator authentication isolation, real TCP tests for nested SPA routing, production security headers, static caching, operations auth/error envelopes, and disabled-by-default billing. |
| Web dependency audit | Pass | `pnpm audit` reports no known vulnerabilities, down from 86 findings before upgrades; `pnpm peers check` reports no peer issues and the frozen lockfile install succeeds. |
| Web production build | Pass | Vite 8 client and bundled Express 5 server built. The HTML shell is 2,031 bytes, the largest JavaScript asset is 480,764 bytes, and the enforced budgets reject developer instrumentation, HTML above 32 KiB, or JavaScript above 512 KiB. |
| Docker build/config | Pass | The exact current sources rebuilt in isolated maintenance Compose on loopback ports 5511/3511. Only non-root API/web services ran; liveness reported maintenance, HAI allowed zero commands, cloud access was disabled, normal mutation returned `423`, dashboard/runtime identity used the host-reachable API origin, and both services were healthy. Synthetic containers, volumes, and network were removed afterward. Standard three-service Compose acceptance passed in the preceding implementation run. |
| Local API/worker/dashboard start | Pass | Final production restart launched Waitress, worker, and the built dashboard on ports 5001/3005 using project-local Python 3.13. The launcher correctly left ports 3001-3004 untouched after ownership inspection showed they belong to another checkout. A stopped-state authoritative one-shot cycle previously completed in 23 seconds; the recurring worker then rejected a second one-shot owner with a concise nonzero result. Dashboard/API identity and DPAPI-backed signing-secret checks passed. |
| Runtime access identity | Pass | Windows readiness now promotes the React operator URL only after a bounded no-proxy/no-redirect loopback identity probe proves the FAB service, checkout, and exact API origin. Doctor and authenticated settings agreed on dashboard port 3005 and ledger API port 5001; invalid runtime metadata falls back safely. Compose supplies explicit host-reachable access metadata. A two-second signature-bound cache kept 20 final-runtime settings reads at 40.45 ms median and 51.83 ms maximum. |
| HAI contract | Pass locally | Standard Windows mode exposes 14 governed commands and eight bounded resources. Maintenance mode exposes zero commands while retaining recovery status as a read-only resource; restore is never a HAI command. A read-only command plan succeeded with `externalSubmission=not_executed`; no provider mutation was attempted. |
| Managed cloud contract | Pass locally | Start/stop scripts parse, static safety tests pass, `/api/cloud/status` is secret-safe, and exact checkout/instance/tunnel/target identity is required. With an unrelated ngrok endpoint already active, startup refused without creating, pooling, or stopping a tunnel. A dedicated FAB HTTPS endpoint remains an external activation requirement. |
| Release archive contract | Pass locally | Unsupported Cloud Function/mobile/root entrypoints and their unused dependencies are removed. Windows/Compose packages require clean committed Git source, refuse secret/runtime/retired paths, bind every file and the ZIP to SHA-256, enforce archive topology and size limits, clean partial output, and verify before success. Eight dedicated package tests plus the full backend suite passed; actual clean-commit Windows and Compose archives were verified before publish. |
| Production HTTP contract | Pass | Native and container checks proved no-cache HTML, one-year immutable hashed assets, restrictive CSP, no HSTS on loopback HTTP, HSTS only when a trusted proxy reports HTTPS, gzip, and a 2,031-byte shell. |
| Health payload and concurrency | Pass | Real 441-issue health JSON fell from 118,102 to about 18,505 bytes (84.3%); doctor JSON fell from 77,448 to 24,544 bytes (68.3%). A 20-request/four-worker run improved from 3.14 to 26.11 requests/second, p50 from 1,006.6 to 8.1 ms, and p95 from 2,226.5 to 703.5 ms; one miss and 19 hits retained exact totals. |
| Control-center data path | Pass | Real 150-work-order traffic fell from 988,287 to 141,040 bytes; master-ledger traffic fell from 202,949 to 918 bytes with the same checksum. Cold control-center refresh improved from 2.04-2.64 seconds to 1.35-1.65 seconds across the complete optimization and dependency-upgrade runs, immediate refresh to 36-54 ms, and gzip reduced about 508 KB to 78,294 bytes. |
| Review queue correctness and paging | Pass | Queue-wide readiness is no longer derived from the first 200 raw review rows. The API pages complete document groups, keeps every decision for a document together, returns queue-wide posting/evidence/duplicate/suggestion totals, and exposes oldest/newest review timestamps. Continuation reads request only the next compact page and total count. Live browser acceptance loaded `50 -> 100 -> 119`, ended on a 19-document page, and retained 253 authoritative open decisions without exposing the API token. |
| Reporting and compliance operator path | Pass locally | The dashboard now reads compact scheduled-report and compliance-assessment projections from the SQLite-backed API, preserves checksum and artifact evidence, exposes governed local commands, and explicitly keeps filing/external submission disabled. Live acceptance found two report runs and five assessments; TypeScript, all 163 web tests, the production build, and desktop/mobile browser inspection passed without console errors or horizontal overflow. |
| Runtime efficiency follow-up | Pass | Ordinary API import wall time fell from roughly 7 seconds to 1.1 seconds without loading OCR/ML dependencies. After a real dashboard load, the API used about 97 MB, the worker about 120 MB, and the dashboard about 124 MB. Warm unchanged backup manifest reads fell from roughly 1.4-1.6 seconds to 26-30 ms; the dashboard review source payload fell from 434,794 to 234,340 bytes. |
| Recovery and maintenance contract | Pass locally | Full recovery verifies archive limits/topology, source-evidence coverage and checksums, immutable targets, rewritten ledger paths, final live bytes, database integrity, and audited outcome. It requires local maintenance, the shared worker lock, exact confirmation, and a source-complete pre-restore package; failures preserve or roll back the live ledger. Native Windows and isolated Compose transitions passed without executing a restore. |
| Live schema upgrade evidence | Pass | The real v0-to-v1 pre-upgrade ledger snapshot was 180,838,400 bytes. Its SHA-256 matched the atomic manifest and both recorded and independent SQLite integrity checks returned `ok`. Health/doctor report schema v1, complete history, and persisted backup evidence. |
| Desktop/narrow browser QA | Pass | The rebuilt standard dashboard rendered in the in-app Browser with the live 119-document queue, exact `50 -> 100 -> 119` incremental loading, no horizontal or control-text overflow at desktop/responsive breakpoints, and no new warning/error logs after the final reload and page fetch. The responsive screenshot capture returned a blank frame, so DOM geometry and interaction evidence are authoritative for that breakpoint. Prior maintenance QA also verified disabled backup/support actions and the public recovery link. |
| Product-path truthfulness search | Pass locally | Supported API, dashboard, and authoritative worker paths expose explicit local, review, execution, and provider states. Fake-success external entrypoints, duplicate checkpoint/review/error orchestration, synthetic learning, placeholder performance/migration wrappers, duplicate vendor-template processing, and dummy tax output are removed. Test-only mocks remain confined to tests. |
| Tracked-secret/runtime scan | Pass | The staged implementation snapshot contained no runtime-data paths and no high-confidence private-key, Google, GitHub, Slack, Stripe-live, or OAuth-secret patterns. |
| Remote CI | Pass | GitHub Actions run `31324705111` on authoritative review-readiness implementation commit `53d8e21` passed the frontend, Linux backend, and all four Windows backend jobs. |
| Fresh-clone verification | Pass on prior baseline | The immediately preceding published commit passed an independent clean-clone source, frozen dependency, test, build, and Compose verification. Current-source verification above ran from the complete tracked tree before publish. |

## Provider state

Live Google and Wave acceptance is not implied by local verification. No provider record or Drive source was changed during this audit. The Wave receipt executor still needs a fresh user-owned session, Google authorization must remain current, and a synthetic receipt must pass Wave attachment readback before archival is enabled. MijnGeldzaken remains supervised, and direct PSD2/SVB mutations remain unavailable.

## Cloud and infrastructure blockers

- The isolated verifier failed closed with `ERR_NGROK_334`, and the managed launcher independently refused to pool the unrelated endpoint already online. FAB did not stop or modify that endpoint. Reserve a separate FAB HTTPS endpoint before running `Start-FAB-Ngrok.cmd`.
- Formal penetration testing, accountant acceptance, DPIA sign-off, and disaster-recovery exercises remain owner or specialist activities.
