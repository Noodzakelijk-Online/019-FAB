# Critical Path

FAB's protected path is:

`source intake -> immutable evidence -> OCR/extraction -> validation -> categorization -> duplicate/group handling -> manual review -> local bookkeeping record -> routing draft -> explicit approval -> supported provider execution -> readback/attachment verification -> reconciliation -> reports -> verified backup/export`

## Invariants

1. Source bytes receive a content hash and provenance before processing.
2. OCR and extracted fields are evidence, not authority. Confidence and missing fields can block progression.
3. Suspected duplicates and related document groups do not post twice.
4. Uncertain, inconsistent, or high-risk records enter review.
5. Preparing an external operation is not the same as executing it.
6. External execution requires a supported capability, explicit authority, idempotency, audit evidence, and a recoverable result.
7. A Google Drive source cannot be archived until the Wave record and actual attachment have been read back and verified.
8. The operator emergency stop prevents any new autonomous step from starting.
9. Reports and close packs disclose incomplete, provisional, and unreconciled state.
10. A complete recovery package requires checksum-matching source evidence; otherwise the backup remains incomplete.

## Smoke-test evidence

- Backend workflow coverage: `tests/test_local_intake.py`, `tests/test_local_processing.py`, `tests/test_local_reviews.py`, `tests/test_local_exports.py`, `tests/test_local_reconciliation.py`, `tests/test_local_reporting.py`, and `tests/test_local_backup.py`.
- Cross-stage autonomy coverage: `tests/test_local_autonomy.py`.
- Drive-to-Wave evidence and archival coverage: `tests/test_drive_wave_delivery.py`.
- Operator gateway and control-center coverage: `web/server/fabLocalGateway.test.ts`.

## Live acceptance boundary

Unit and integration tests prove local behavior. They do not prove that the current Google consent, Wave account, Wave attachment surface, or provider policy is valid. Live archival must remain disabled until the operator runbook's provider acceptance test passes.
