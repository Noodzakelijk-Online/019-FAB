# Codex Checkpoints

| Checkpoint | State | Resume evidence |
| --- | --- | --- |
| C0 Baseline | Complete | `main`, start `8a2b43d`, origin default `main`; audit in `TECHNICAL_AUDIT.md`. |
| C1 Requirements map | Complete | 116 phase rows in `GOAL_COMPLETION_MATRIX.md`. |
| C2 Critical safety gaps | Complete | Persistent emergency stop and sanitized support bundle implemented and tested. |
| C3 Product truthfulness | Complete | Unsupported public claims and invented testimonials removed in English and Dutch. |
| C4 Focused verification | Complete | Emergency-stop and support-bundle tests plus Python compilation. |
| C5 Full verification | Complete | 777 backend tests passed with 3 optional-runtime skips; 163 web tests, type check, build budgets, dependency gates, PowerShell parsing, and Compose configuration passed. Dependency-safe recovery, exact continuation failure, scheduler, output-bound, and direct-executor misuse cases are included. Live Windows/HAI acceptance is recorded by the final release evidence. |
| C6 Browser acceptance | Complete for local release | Current-source in-app Browser desktop and narrow responsive checks passed with no horizontal overflow or console warnings/errors. The live recovery candidate exposed its exact safe path without clipping. Connections and a complete document Review action were exercised in the broader release. Broad cross-browser certification remains external. |
| C7 Source hygiene | Complete | Temporary extraction/build probes removed; staged snapshot has no runtime paths or high-confidence credential patterns. |
| C8 Delivery | Complete | Dependency-safe implementation `3f2d5c6` is on `origin/main`; GitHub Actions run `31319135326` passed the frontend, Linux backend, and all four Windows backend jobs. The documentation-only evidence commit is recorded by the delivery response. |

On context loss, resume at the first non-complete checkpoint and re-run `git status --short` before editing.
