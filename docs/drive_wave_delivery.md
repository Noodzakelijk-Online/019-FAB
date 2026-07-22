# Verified Google Drive to Wave delivery

FAB treats the Google Drive file as the source of record and Wave as the
downstream accounting surface. A matching transaction or receipt icon alone is
not enough to archive a source document.

## Lifecycle

1. The Google Drive connector downloads direct children of the configured
   intake folder, either through native OAuth or the authenticated binary relay
   at `POST /api/connectors/google-drive/relay`. FAB requires the configured
   folder ID and records the provider file ID, size, and a locally computed
   SHA-256 digest in the operations ledger. Repeating the same provider ID and
   bytes is idempotent; changed bytes create a revision and never overwrite the
   earlier local copy.
2. FAB processes and validates the document, resolves duplicates and review
   items, and prepares or finds the matching Wave transaction.
3. A browser or HAI executor uploads the exact local source file to Wave and
   then downloads the stored Wave attachment back.
4. The executor submits that downloaded file plus transaction evidence as
   multipart data to
   `POST /api/drive-wave/documents/<id>/attachment-readback`. FAB computes the
   readback hash and size itself. Metadata attestation through
   `attachment-evidence` or `record_wave_attachment_verification` can record
   progress but can never unlock archival.
5. The worker runs a move-only archive pass. It downloads the current Drive
   source again, requires recent Wave readback evidence, verifies its SHA-256
   and provider metadata, moves the same provider file ID, and verifies the
   destination parent.

Any failed gate leaves the source in the intake folder and creates a review
item. FAB never deletes a Drive source in this workflow.

## Required Wave evidence

- configured Wave business ID and external transaction ID;
- server-computed attachment SHA-256 exactly equal to the source SHA-256;
- exact attachment size, filename, and MIME type equality;
- a provider attachment object ID, attachment-present readback, and successful
  opening of the stored attachment;
- reviewed transaction state;
- observed Wave values for vendor, date, amount, currency, category, and
  description. FAB computes these matches server-side and binds them to a
  digest of the current expected fields; a later bookkeeping edit invalidates
  the evidence;
- invoice-number and VAT matches when those fields exist on the source.

The Wave receipt surface currently accepts PDF, JPG/JPEG, PNG, GIF, TIFF/TIF,
BMP, and HEIC files up to 6 MB. FAB marks incompatible work orders before an
executor attempts an upload.

## Configuration

Set the following values in the local ignored `config/config.ini` file:

```ini
[google_drive]
enabled = true
folder_id = <intake-folder-id>
relay_max_bytes = 26214400
archive_verified_files = true
wave_archive_folder_id = <archive-folder-id>
wave_attachment_evidence_max_age_seconds = 900
interactive_auth = false

[waveapps_business]
id = <wave-business-id>
```

The normal intake connector uses read-only Drive access. Moving existing Drive
files requires a separately authorized full-Drive token. Place the Google OAuth
desktop client JSON at `credentials/drive_credentials.json`, then run
`Authorize-FAB-GoogleDrive.cmd`. The supervised command opens Google in the
operator's browser, writes the configured token, verifies access to the intake
folder, and leaves unattended interactive authorization disabled.

## HAI contract

The HAI manifest advertises three bounded resources and two related commands:

- `google_drive_binary_relay` accepts exact Drive bytes and provider metadata
  from an authenticated connector without requiring the local process to own a
  Drive OAuth token.
- `wave_attachment_work_orders` returns the exact local source path,
  provider file ID, source hash, expected Wave fields and line items, evidence
  template, and current archive blockers without changing either system.
- `wave_attachment_binary_readback` accepts the file downloaded back from Wave
  and computes the archival evidence inside FAB.
- `record_wave_attachment_verification` records metadata attestation only and
  does not satisfy the binary-readback gate.
- `archive_verified_drive_sources` defaults to a dry run and can move only
  documents that already satisfy every policy gate.

Neither command can delete a source file or bypass unresolved reviews.
Successful fresh evidence resolves only an earlier `drive_wave_archive_blocked`
review; unrelated review items continue to block archival.

The operator dashboard reads the same work-order endpoint. An empty queue is
not represented as completed delivery when Drive authorization is missing; the
connector state remains `needs_authorization` until the configured folder can
be read with the persisted token.
