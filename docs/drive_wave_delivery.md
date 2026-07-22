# Verified Google Drive to Wave delivery

FAB treats the Google Drive file as the source of record and Wave as the
downstream accounting surface. A matching transaction or receipt icon alone is
not enough to archive a source document.

## Lifecycle

1. The Google Drive connector downloads direct children of the configured
   intake folder and records the provider file ID, provider checksum, size, and
   a local SHA-256 digest in the operations ledger.
2. FAB processes and validates the document, resolves duplicates and review
   items, and prepares or finds the matching Wave transaction.
3. A browser or HAI executor uploads the exact local source file to Wave and
   reads the transaction and stored attachment back.
4. The executor records evidence through
   `POST /api/drive-wave/documents/<id>/attachment-evidence` or the HAI command
   `record_wave_attachment_verification`.
5. The worker runs a move-only archive pass. It downloads the current Drive
   source again, requires recent Wave readback evidence, verifies its SHA-256
   and provider metadata, moves the same provider file ID, and verifies the
   destination parent.

Any failed gate leaves the source in the intake folder and creates a review
item. FAB never deletes a Drive source in this workflow.

## Required Wave evidence

- configured Wave business ID and external transaction ID;
- source SHA-256 and either an attachment SHA-256 or the exact upload-source
  SHA-256;
- a provider attachment object ID, attachment-present readback, and successful
  opening of the stored attachment;
- reviewed transaction state;
- positive readback matches for vendor, date, amount, currency, category, and
  description;
- invoice-number and VAT matches when those fields exist on the source.

## Configuration

Set the following values in the local ignored `config/config.ini` file:

```ini
[google_drive]
enabled = true
folder_id = <intake-folder-id>
archive_verified_files = true
wave_archive_folder_id = <archive-folder-id>
wave_attachment_evidence_max_age_seconds = 900
interactive_auth = false

[waveapps_business]
id = <wave-business-id>
```

The normal intake connector uses read-only Drive access. Moving existing Drive
files requires a separately authorized full-Drive token. Perform that OAuth
upgrade once under supervision by temporarily enabling `interactive_auth`, then
disable interactive authorization before restarting the worker.

## HAI contract

The HAI manifest exposes two bounded commands:

- `record_wave_attachment_verification` records readback evidence only.
- `archive_verified_drive_sources` defaults to a dry run and can move only
  documents that already satisfy every policy gate.

Neither command can delete a source file or bypass unresolved reviews.
Successful fresh evidence resolves only an earlier `drive_wave_archive_blocked`
review; unrelated review items continue to block archival.
