# Codex Checkpoints

| Checkpoint | State | Resume evidence |
| --- | --- | --- |
| C0 Baseline | Complete | `main`, start `8a2b43d`, origin default `main`; audit in `TECHNICAL_AUDIT.md`. |
| C1 Requirements map | Complete | 116 phase rows in `GOAL_COMPLETION_MATRIX.md`. |
| C2 Critical safety gaps | Complete | Persistent emergency stop and sanitized support bundle implemented and tested. |
| C3 Product truthfulness | Complete | Unsupported public claims and invented testimonials removed in English and Dutch. |
| C4 Focused verification | Complete | 18 readiness/support tests prove shared app-owned caching, independent snapshots, redaction, runtime identity, and diagnostic behavior; Python compilation passed. |
| C5 Full verification | Complete | 795 backend tests passed with 4 optional-runtime skips; 165 web tests, type check, and production build budgets passed. Full ledger/source recovery, tamper/collision/rollback behavior, worker ownership, maintenance-mode mutation blocking, dependency-safe workflow recovery, authoritative runtime access identity, and shared readiness lifecycle are included. Final PowerShell, Compose, HAI, and Windows checks are recorded before delivery. |
| C6 Browser acceptance | Complete for local release | Current-source in-app Browser desktop and narrow responsive checks passed with no horizontal overflow or console warnings/errors. The maintenance recovery view disabled normal mutations and exposed the corrected host-reachable advanced-recovery link. Connections and a complete document Review action were exercised in the broader release. Broad cross-browser certification remains external. |
| C7 Source hygiene | Complete | Temporary extraction/build probes removed; staged snapshot has no runtime paths or high-confidence credential patterns. |
| C8 Delivery | Complete | Readiness-lifecycle implementation `04a2ad4` is on `origin/main`; GitHub Actions run `31328111774` passed the frontend, Linux backend, and all four Windows backend jobs. The documentation-only evidence commit is recorded by the delivery response. |

On context loss, resume at the first non-complete checkpoint and re-run `git status --short` before editing.
