# Codex Checkpoints

| Checkpoint | State | Resume evidence |
| --- | --- | --- |
| C0 Baseline | Complete | `main`, start `8a2b43d`, origin default `main`; audit in `TECHNICAL_AUDIT.md`. |
| C1 Requirements map | Complete | 116 phase rows in `GOAL_COMPLETION_MATRIX.md`. |
| C2 Critical safety gaps | Complete | Persistent emergency stop and sanitized support bundle implemented and tested. |
| C3 Product truthfulness | Complete | Unsupported public claims and invented testimonials removed in English and Dutch. |
| C4 Focused verification | Complete | Emergency-stop and support-bundle tests plus Python compilation. |
| C5 Full verification | Complete | 771 backend tests passed with 3 optional-runtime skips; 163 web tests, type check, build budgets, dependency gates, PowerShell parsing, and Compose configuration passed. Live Windows/HAI acceptance is recorded by the final release evidence. |
| C6 Browser acceptance | Complete for local release | Current-source in-app Browser desktop and 480-pixel-effective responsive checks passed with no horizontal overflow or console warnings/errors. Connections and a complete document Review action were exercised. Broad cross-browser certification remains external. |
| C7 Source hygiene | Complete | Temporary extraction/build probes removed; staged snapshot has no runtime paths or high-confidence credential patterns. |
| C8 Delivery | Pending | Publish the authoritative-worker/template/Compose-identity slice to `origin/main`, wait for the frontend, Linux backend, and all four Windows backend jobs, then record the commit and run in the release evidence. |

On context loss, resume at the first non-complete checkpoint and re-run `git status --short` before editing.
