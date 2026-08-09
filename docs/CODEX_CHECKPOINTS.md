# Codex Checkpoints

| Checkpoint | State | Resume evidence |
| --- | --- | --- |
| C0 Baseline | Complete | `main`, start `8a2b43d`, origin default `main`; audit in `TECHNICAL_AUDIT.md`. |
| C1 Requirements map | Complete | 116 phase rows in `GOAL_COMPLETION_MATRIX.md`. |
| C2 Critical safety gaps | Complete | Persistent emergency stop and sanitized support bundle implemented and tested. |
| C3 Product truthfulness | Complete | Unsupported public claims and invented testimonials removed in English and Dutch. |
| C4 Focused verification | Complete | Emergency-stop and support-bundle tests plus Python compilation. |
| C5 Full verification | Complete | 768 backend tests, 153 web tests, type check, build, focused safety tests, live 26-resource profile, both images, and the Compose service acceptance passed. |
| C6 Browser acceptance | Partial | Desktop/mobile DOM and geometry passed without overflow or overlays. The in-app Browser runtime could not capture screenshots or dispatch clicks despite finding enabled controls. |
| C7 Source hygiene | Pending final run | Remove temporary PDF extraction and confirm no ignored/runtime data is tracked. |
| C8 Delivery | Pending final run | Commit, push `main`, and record final commit and remote state. |

On context loss, resume at the first non-complete checkpoint and re-run `git status --short` before editing.
