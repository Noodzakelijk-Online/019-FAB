# Codex Checkpoints

| Checkpoint | State | Resume evidence |
| --- | --- | --- |
| C0 Baseline | Complete | `main`, start `8a2b43d`, origin default `main`; audit in `TECHNICAL_AUDIT.md`. |
| C1 Requirements map | Complete | 116 phase rows in `GOAL_COMPLETION_MATRIX.md`. |
| C2 Critical safety gaps | Complete | Persistent emergency stop and sanitized support bundle implemented and tested. |
| C3 Product truthfulness | Complete | Unsupported public claims and invented testimonials removed in English and Dutch. |
| C4 Focused verification | Complete | Nine backend and 24 web bank-import tests cover Dutch/Windows CSV, bounds/formats, identity replay, malformed/binary input, authorization, audit actor binding, redaction, and dashboard projection. |
| C5 Full verification | Complete | All four CI-equivalent backend shards passed: 806 tests with 4 optional-runtime skips. All 179 web tests, TypeScript, production build budgets, peer checks, and the production dependency audit passed. Prior recovery, worker, provider-boundary, Windows, Compose, HAI, and data-path evidence remains unchanged. |
| C6 Browser acceptance | Complete for current source | The live production dashboard opened bank import from Overview and Connections, kept execution disabled without a valid file, restored invocation focus after Escape, had no desktop/narrow page or drawer overflow, and produced no console warnings/errors. No real financial file or provider mutation was used. Broad cross-browser certification remains external. |
| C7 Source hygiene | Complete | Temporary extraction/build probes removed; staged snapshot has no runtime paths or high-confidence credential patterns. |
| C8 Delivery | Complete | Safe bank-statement import implementation `2356177` is on `origin/main`; GitHub Actions run `31335374005` passed the frontend, Linux backend, and all four Windows backend jobs. Final clean-source release packages are recorded by the delivery response. |

On context loss, resume at the first non-complete checkpoint and re-run `git status --short` before editing.
