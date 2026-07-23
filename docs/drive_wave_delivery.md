# Verified source-to-Wave delivery

FAB treats retained Google Drive files and trusted Gmail scanner attachments as
source evidence, with Wave as the downstream accounting surface. A matching
transaction or receipt icon alone is not enough to complete delivery or archive
a source document.

## Lifecycle

1. The Google Drive connector downloads direct children of the configured
   intake folder. The read-only Gmail scanner connector accepts only PDF
   attachments from explicitly trusted senders, records the Gmail message and
   attachment IDs, and confines every local copy to the configured download
   root. Both paths compute a local SHA-256 digest and retain source provenance
   in the operations ledger.
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
5. A verified Gmail scanner work order becomes complete while the source email
   remains unchanged and the local evidence remains retained. No Gmail label,
   message, or attachment mutation is performed.
6. For Drive sources only, the worker runs a move-only archive pass under a
   per-document lease. It
   downloads the current Drive source again, requires recent Wave readback
   evidence, verifies its SHA-256 and complete provider identity, and re-runs
   every archive gate immediately before moving the same provider file ID.
7. FAB reads the Drive file back after the move and requires the same SHA-256, file
   ID, filename, MIME type, size, and archive parent. A failed postcondition
   triggers a move-only rollback to the intake folder and never marks the
   lifecycle archived.

Any failed Drive gate leaves the source in the intake folder. Any failed Gmail
gate leaves both the email and local evidence unchanged. FAB never deletes a
source in this workflow.

## Required Wave evidence

- configured Wave business ID and external transaction ID;
- exactly one matching Wave transaction, an official Wave transaction URL,
  a fresh observation timestamp, and a finished/reviewed transaction state;
- server-computed attachment SHA-256 exactly equal to the source SHA-256;
- exact attachment size, filename, and MIME type equality;
- a provider attachment object ID, attachment-present readback, and successful
  opening and download of the stored attachment;
- explicit proof that the attachment's parent transaction ID equals the unique
  Wave transaction ID;
- reviewed transaction state;
- observed Wave values for vendor, date, amount, currency, category, and
  description. FAB computes these matches server-side and binds them to a
  digest of the current expected fields; a later bookkeeping edit invalidates
  the evidence;
- invoice-number and VAT matches when those fields exist on the source.

The FAB bookkeeping record must exist, target `waveapps_business`, be outside
all review states, and have reached an archivable record status. Source hash,
provider identity, filename, MIME type, and size are mandatory rather than
best-effort metadata. Older records that lack these values remain pending until
FAB re-ingests or repairs their evidence. For Gmail scanner sources, the trusted
sender, scanner policy marker, Gmail message ID, attachment ID, and download-root
confinement are mandatory. For Drive sources, the intake and archive folder IDs
must be different; FAB blocks the workflow before any Drive update when they are
equal.

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
- `wave_attachment_work_orders` returns the exact local source path, provider
  identity, source hash, expected Wave fields and line items, evidence template,
  and current verification or archive blockers without changing either system.
- `wave_attachment_binary_readback` accepts the file downloaded back from Wave
  and computes the archival evidence inside FAB.
- `record_wave_attachment_verification` records metadata attestation only and
  does not satisfy the binary-readback gate.
- `archive_verified_drive_sources` defaults to a dry run and can move only
  documents that already satisfy every policy gate.

Neither command can delete a source file, bypass unresolved reviews, reuse
legacy v1 evidence, or run two archive moves for the same document at once.
Successful fresh evidence resolves only an earlier `drive_wave_archive_blocked`
review; unrelated review items continue to block delivery. The current work
order contract is `fab-source-wave-work-order-v3`. The compatibility endpoint
remains `/api/drive-wave/work-orders`.

The operator dashboard reads the same work-order endpoint. Gmail delivery can
continue independently of Drive archive authorization, but missing Drive
authorization remains visible until the configured folder can be read with the
persisted token.
