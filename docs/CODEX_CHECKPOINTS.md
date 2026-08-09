# Codex Checkpoints

| Checkpoint | State | Resume evidence |
| --- | --- | --- |
| C0 Baseline | Complete | `main`, start `8a2b43d`, origin default `main`; audit in `TECHNICAL_AUDIT.md`. |
| C1 Requirements map | Complete | 116 phase rows in `GOAL_COMPLETION_MATRIX.md`. |
| C2 Critical safety gaps | Complete | Persistent emergency stop and sanitized support bundle implemented and tested. |
| C3 Product truthfulness | Complete | Unsupported public claims and invented testimonials removed in English and Dutch. |
| C4 Focused verification | Complete | 93 health/ledger/exception/delivery tests prove query-only compound snapshots, batched line-item and exception context loading, one current-snapshot source validation, unchanged queue decisions, and write rejection inside read snapshots; Python compilation passed. |
| C5 Full verification | Complete | 801 backend tests passed with 4 optional-runtime skips; 165 web tests, type check, production build budgets, dependency/peer audits, six PowerShell parsers, both Compose modes, live-ledger integrity/foreign-key checks, and an exact-source standard Compose build/run passed. Full ledger/source recovery, worker ownership, safety gates, shared readiness, and compact projections are included. |
| C6 Browser acceptance | Complete for current source | A fresh production restart and in-app Browser reload at the current source showed connected live data, no new console warnings/errors, and no horizontal or off-screen control overflow at desktop and the narrow responsive breakpoint. Broad cross-browser certification remains external. |
| C7 Source hygiene | Complete | Temporary extraction/build probes removed; staged snapshot has no runtime paths or high-confidence credential patterns. |
| C8 Delivery | Complete | Consistent ledger-read implementation `e55e7b2` is on `origin/main`; GitHub Actions run `31331321548` passed the frontend, Linux backend, and all four Windows backend jobs. The documentation-only evidence commit is recorded by the delivery response. |

On context loss, resume at the first non-complete checkpoint and re-run `git status --short` before editing.
