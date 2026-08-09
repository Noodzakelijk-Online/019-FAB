# Codex Checkpoints

| Checkpoint | State | Resume evidence |
| --- | --- | --- |
| C0 Baseline | Complete | `main`, start `8a2b43d`, origin default `main`; audit in `TECHNICAL_AUDIT.md`. |
| C1 Requirements map | Complete | 116 phase rows in `GOAL_COMPLETION_MATRIX.md`. |
| C2 Critical safety gaps | Complete | Persistent emergency stop and sanitized support bundle implemented and tested. |
| C3 Product truthfulness | Complete | Unsupported public claims and invented testimonials removed in English and Dutch. |
| C4 Focused verification | Complete | Four activation and five review-draft tests cover ordered progress, reauthorization, unavailable queue evidence, exact-identity recovery, expiry, malformed/oversized state, change detection, and discard. |
| C5 Full verification | Complete | All four CI-equivalent backend shards passed: 801 tests with 4 optional-runtime skips. All 174 web tests, TypeScript, production build budgets, and the production dependency audit passed. Prior recovery, worker, provider-boundary, Windows, Compose, HAI, and data-path evidence remains unchanged. |
| C6 Browser acceptance | Complete for current source | The live production dashboard selected receipt-executor setup as step 4 of 5, opened the matching drawer, restored a review draft after close/reopen and full reload, and discarded it without submission. Desktop and narrow activation geometry had no page or component overflow; console warnings/errors remained empty. Broad cross-browser certification remains external. |
| C7 Source hygiene | Complete | Temporary extraction/build probes removed; staged snapshot has no runtime paths or high-confidence credential patterns. |
| C8 Delivery | Complete | Guided activation and review-draft implementation `cc718f3` is on `origin/main`; GitHub Actions run `31333616656` passed the frontend, Linux backend, and all four Windows backend jobs. Final clean-source release packages are recorded by the delivery response. |

On context loss, resume at the first non-complete checkpoint and re-run `git status --short` before editing.
