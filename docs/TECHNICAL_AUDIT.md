# Technical Audit

Audit date: 2026-08-09

## Baseline

- Branch and default branch: `main`.
- Starting commit: `8a2b43d`.
- Runtime: Python local API/worker plus a React/Express operator dashboard.
- Persistence: SQLite operational ledger with ordered checksum-bound schema history and verified pre-upgrade snapshots; optional MySQL/Drizzle storage for the web application.
- Delivery: Windows launch scripts, CI on Linux and Windows, and explicit API/worker/dashboard container services.
- Local financial data, credentials, tokens, logs, uploads, databases, and generated support bundles are ignored by Git.

## Confirmed strengths

- The critical path is implemented across intake, OCR/extraction, validation, categorization, duplicate handling, manual review, routing, approval-gated exports, reconciliation, reporting, backup, retention, and audit history.
- Google and Wave readiness is capability-based. OAuth `invalid_grant` is an authorization blocker, not a retry loop.
- Drive source archival is gated on Wave record and attachment readback evidence.
- External submissions are represented separately from local preparation and require supported capabilities and approvals.
- Worker leases, idempotency keys, rate limits, recovery candidates, and dead-letter-style export deferral are present.

## Remediated in this audit

- Added a persistent, audited autonomy emergency stop. It is checked before every workflow step and only an operator can clear it with an exact confirmation phrase.
- Added sanitized doctor output and support ZIP generation that excludes financial documents, OCR, ledger rows, filenames, amounts, paths, configuration values, and credentials.
- Wired support bundle creation and emergency controls through the local API and operator dashboard.
- Removed invented testimonials, numeric outcome claims, and public claims of unsupported direct MijnGeldzaken, PSD2, SVB, biometric, and unrestricted Wave automation.
- Added traceability, acceptance, security, API/UI audit, operator, checkpoint, and verification documents.
- Replaced the Flask development runtime with bounded Waitress threads, enabled SQLite WAL plus bounded lock waiting, limited dashboard fan-out, and paginated the document-review workspace.
- Added three-service Docker/Compose definitions with non-root containers, health checks, durable runtime volumes, read-only intake, configurable loopback-published ports, and opt-in Docker bridge-gateway trust restricted to private `.1` gateways and loopback hostnames.
- Self-bundled the production web server so its runtime image needs no dependency tree, added the Node ESM compatibility bridge required by bundled CommonJS packages, and removed fixed Docker subnet assumptions that could collide with existing projects.
- Added stable correlated JSON error envelopes across the local API, sanitized unexpected-error handling, and bounded HAI request identifiers without provider-detail leakage.
- Added versioned SQLite migration history, fail-closed history validation, automatic integrity-checked pre-upgrade snapshots, restore-based rollback guidance, and schema status in health/doctor output.
- Replaced per-failed-workflow recovery lookups in deep health with one bounded bulk query.
- Bounded API and support health-detail serialization without weakening full-set status, metrics, counts, next actions, notifications, exception queues, close readiness, or autonomy gates.
- Coalesced identical deep-health HTTP reads through a short bounded in-process cache while retaining `no-store` responses and uncached internal safety decisions.
- On the real 441-issue ledger, bounded serialization reduced health payload bytes by 84.3% and doctor bytes by 68.3%; short concurrent acceptance improved health throughput 8.3x with exact counts in every response.

## Remaining risks

- Live Google and Wave acceptance depends on owner authorization and current provider state.
- MijnGeldzaken remains a supervised master-ledger export, not an authenticated write connector.
- Direct PSD2 bank feeds and SVB submissions are not implemented.
- Compose configuration, both images, authenticated service health, dashboard access, local-operator authorization, and non-root execution are locally verified. Live cloud-host acceptance remains environment-specific.
- SQLite rollback is restore-based by design. Operational recovery still requires a rehearsed restore using the prior compatible FAB release.
- Formal penetration testing, DPIA approval, accountant validation, and production disaster-recovery exercises remain external work.

## Technical debt register

| Priority | Item | Required action |
| --- | --- | --- |
| High | Live provider acceptance | Reauthorize Google, validate the Wave business/token/mapping, and run a synthetic receipt through attachment readback before enabling archival. |
| Medium | Image optimization | The OCR/PDF-capable API image is 1.52 GB; consider a separate lightweight API image and an OCR worker image if registry transfer or cold-start cost becomes material. |
| Medium | Performance baseline | Run sustained idle-host and concurrent-refresh tests, and track cold backup-integrity scan time separately from warm bounded-health latency and payload size. |
| Medium | Recovery rehearsal | Exercise the documented schema rollback and full source-evidence recovery process on a production-sized copy before unattended upgrades. |
| Medium | Privacy governance | Complete a signed DPIA and data-processing inventory before multi-user production use. |
| Low | Public product shell | Remove or hide pricing and roadmap surfaces that are not part of the local operator product before public release. |
