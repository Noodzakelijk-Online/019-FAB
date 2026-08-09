# Codex Checkpoints

| Checkpoint | State | Resume evidence |
| --- | --- | --- |
| C0 Baseline | Complete | `main`, start `8a2b43d`, origin default `main`; audit in `TECHNICAL_AUDIT.md`. |
| C1 Requirements map | Complete | 116 phase rows in `GOAL_COMPLETION_MATRIX.md`. |
| C2 Critical safety gaps | Complete | Persistent emergency stop and sanitized support bundle implemented and tested. |
| C3 Product truthfulness | Complete | Unsupported public claims and invented testimonials removed in English and Dutch. |
| C4 Focused verification | Complete | Operator handoff tests cover local/admin authorization, HMAC contents, target/origin bounds, token absence, expiry, secure cookies, authenticated continuation, audit redaction, tampering, and one-time replay rejection. Prior bank-import coverage remains green. |
| C5 Full verification | Complete | All four CI-equivalent backend shards passed: 808 tests with 4 optional-runtime skips. All 182 web tests, TypeScript, production build budgets, peer checks, and the production dependency audit passed. Prior recovery, worker, provider-boundary, Windows, Compose, HAI, and data-path evidence remains unchanged. |
| C6 Browser acceptance | Complete for current source | The live production dashboard opened the protected ledger through the same-origin one-time handoff, reached `http://127.0.0.1:5001/#audit` without a token prompt, and produced no console warnings/errors in fresh dashboard or ledger tabs. Desktop/narrow page width equaled viewport width. No real financial file, provider record, review decision, attachment, or Drive archive was changed. Broad cross-browser certification remains external. |
| C7 Source hygiene | Complete | Temporary extraction/build probes removed; staged snapshot has no runtime paths or high-confidence credential patterns. |
| C8 Delivery | Complete | Authenticated operator-ledger handoff implementation `6e9dad0` is on `origin/main`; GitHub Actions run `31337125650` passed the frontend, Linux backend, and all four Windows backend jobs. Final clean-source release packages are recorded by the delivery response. |

On context loss, resume at the first non-complete checkpoint and re-run `git status --short` before editing.
