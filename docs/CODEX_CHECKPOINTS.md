# Codex Checkpoints

| Checkpoint | State | Resume evidence |
| --- | --- | --- |
| C0 Baseline | Complete | `main`, start `8a2b43d`, origin default `main`; audit in `TECHNICAL_AUDIT.md`. |
| C1 Requirements map | Complete | 116 phase rows in `GOAL_COMPLETION_MATRIX.md`. |
| C2 Critical safety gaps | Complete | Persistent emergency stop and sanitized support bundle implemented and tested. |
| C3 Product truthfulness | Complete | Unsupported public claims and invented testimonials removed in English and Dutch. |
| C4 Focused verification | Complete | Emergency-stop and support-bundle tests plus Python compilation. |
| C5 Full verification | Complete | 788 backend tests passed with 4 optional-runtime skips; 164 web tests, type check, build budgets, dependency gates, Python compilation, PowerShell parsing, and Compose configuration passed. Full ledger/source recovery, tamper/collision/rollback behavior, worker ownership, maintenance-mode mutation blocking, and dependency-safe workflow recovery are included. Live Windows/HAI maintenance and standard-mode acceptance passed. |
| C6 Browser acceptance | Complete for local release | Current-source in-app Browser desktop and narrow responsive checks passed with no horizontal overflow or console warnings/errors. The maintenance recovery view disabled normal mutations and exposed the corrected host-reachable advanced-recovery link. Connections and a complete document Review action were exercised in the broader release. Broad cross-browser certification remains external. |
| C7 Source hygiene | Complete | Temporary extraction/build probes removed; staged snapshot has no runtime paths or high-confidence credential patterns. |
| C8 Delivery | In progress | Quiescent recovery is locally verified. Publish the clean implementation, wait for the frontend, Linux backend, and four Windows backend jobs, then record the final commit and run here. |

On context loss, resume at the first non-complete checkpoint and re-run `git status --short` before editing.
