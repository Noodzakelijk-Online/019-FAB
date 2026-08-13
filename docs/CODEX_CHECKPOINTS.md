# Codex Checkpoints

| Checkpoint | State | Resume evidence |
| --- | --- | --- |
| C0 Baseline | Complete | `main`, start `8a2b43d`, origin default `main`; audit in `TECHNICAL_AUDIT.md`. |
| C1 Requirements map | Complete | 116 phase rows in `GOAL_COMPLETION_MATRIX.md`. |
| C2 Critical safety gaps | Complete | Persistent emergency stop and sanitized support bundle implemented and tested. |
| C3 Product truthfulness | Complete | Unsupported public claims and invented testimonials removed in English and Dutch. |
| C4 Focused verification | Complete | Export idempotency, route due-state, projection/daily-plan scheduling, sparse recurring workflow persistence, audit coalescing, and canonical operator-ticket tests pass. Prior operator-handoff and bank-import coverage remains green. |
| C5 Full verification | Complete | All four CI-equivalent backend shards passed: 814 tests with 4 optional-runtime skips. All 182 web tests, TypeScript, production build budgets, peer checks, and the production dependency audit passed. Python, PowerShell, Compose, Windows-runtime, and copied-production steady-cycle checks also passed. |
| C6 Browser acceptance | Complete for current source | The live production dashboard rendered without horizontal overflow or console warnings/errors. The same-origin handoff reached the populated ledger at `http://127.0.0.1:5001/` without a token prompt. Prior narrow-layout evidence remains applicable because this increment changes backend/worker code only. No real financial file, provider record, review decision, attachment, or Drive archive was changed. Broad cross-browser certification remains external. |
| C7 Source hygiene | Complete | Temporary extraction/build probes removed; staged snapshot has no runtime paths or high-confidence credential patterns. |
| C8 Delivery | Complete | Recurring-autonomy implementation `c18b2ae` is on `origin/main`; GitHub Actions run `31678667271` passed the frontend, Linux backend, and all four Windows backend jobs. Final clean-source release packages are recorded by the delivery response. |

On context loss, resume at the first non-complete checkpoint and re-run `git status --short` before editing.
