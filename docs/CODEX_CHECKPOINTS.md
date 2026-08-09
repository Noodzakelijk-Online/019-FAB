# Codex Checkpoints

| Checkpoint | State | Resume evidence |
| --- | --- | --- |
| C0 Baseline | Complete | `main`, start `8a2b43d`, origin default `main`; audit in `TECHNICAL_AUDIT.md`. |
| C1 Requirements map | Complete | 116 phase rows in `GOAL_COMPLETION_MATRIX.md`. |
| C2 Critical safety gaps | Complete | Persistent emergency stop and sanitized support bundle implemented and tested. |
| C3 Product truthfulness | Complete | Unsupported public claims and invented testimonials removed in English and Dutch. |
| C4 Focused verification | Complete | 91 ledger/processing/autonomy tests prove compact duplicate snapshots, selected-review ordering, unchanged reassessment decisions, and no full-history N+1 fallback; Python compilation passed. |
| C5 Full verification | Complete | 797 backend tests passed with 4 optional-runtime skips; 165 web tests, type check, production build budgets, dependency/peer audits, five PowerShell parsers, and both Compose modes passed. Full ledger/source recovery, worker ownership, safety gates, shared readiness, and compact duplicate planning are included. |
| C6 Browser acceptance | Complete for latest UI-changing baseline | The unchanged dashboard's prior desktop and narrow responsive checks passed without horizontal overflow or console errors. The latest backend-only source passed 165 web tests, production build, and live HTTP identity; a repeat in-app Browser DOM capture was unavailable because its control bridge returned a stale tab identifier. Broad cross-browser certification remains external. |
| C7 Source hygiene | Complete | Temporary extraction/build probes removed; staged snapshot has no runtime paths or high-confidence credential patterns. |
| C8 Delivery | Complete | Compact duplicate-reassessment implementation `a6ce7c4` is on `origin/main`; GitHub Actions run `31329640244` passed the frontend, Linux backend, and all four Windows backend jobs. The documentation-only evidence commit is recorded by the delivery response. |

On context loss, resume at the first non-complete checkpoint and re-run `git status --short` before editing.
