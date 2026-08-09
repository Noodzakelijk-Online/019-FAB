# Codex Checkpoints

| Checkpoint | State | Resume evidence |
| --- | --- | --- |
| C0 Baseline | Complete | `main`, start `8a2b43d`, origin default `main`; audit in `TECHNICAL_AUDIT.md`. |
| C1 Requirements map | Complete | 116 phase rows in `GOAL_COMPLETION_MATRIX.md`. |
| C2 Critical safety gaps | Complete | Persistent emergency stop and sanitized support bundle implemented and tested. |
| C3 Product truthfulness | Complete | Unsupported public claims and invented testimonials removed in English and Dutch. |
| C4 Focused verification | Complete | Emergency-stop and support-bundle tests plus Python compilation. |
| C5 Full verification | Complete | 793 backend tests plus 38 subtests, 161 web tests, type check, build budgets, dependency gates, live Windows/HAI/cloud checks, both exact-source images, and the Compose service acceptance passed. |
| C6 Browser acceptance | Complete for local release | Prior connected Chrome desktop/narrow screenshots passed. Current-source in-app Browser desktop/narrow DOM, navigation, cloud state, and error checks passed; its screenshot function returned blank frames. Broad cross-browser certification remains external. |
| C7 Source hygiene | Complete | Temporary extraction/build probes removed; staged snapshot has no runtime paths or high-confidence credential patterns. |
| C8 Delivery | Complete | Implementation `2f70668` is on `origin/main`; GitHub Actions run `31301840108` and an independent clean-clone verification passed. The final evidence commit is recorded by the delivery response. |

On context loss, resume at the first non-complete checkpoint and re-run `git status --short` before editing.
