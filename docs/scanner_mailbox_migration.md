# Scanner mailbox migration

Repository `Noodzakelijk-Online/025-Scan-to-folder-automation` at audited source commit `e3078d9` contains two different collectors: a bundled Apps Script that copies HP ePrint PDF attachments from Gmail to one fixed Drive folder, and a separate NestJS service that copies selected Freshdesk ticket content to Drive. FAB incorporates both useful collection policies as first-class read-only connector profiles. It does not import the legacy services or any credential material from that repository.

## Active data path

1. Gmail is searched with `label:all from:eprintcenter@hp8.us has:attachment filename:pdf`.
2. FAB independently checks the parsed sender address, filename, MIME type, size, and PDF signature.
3. The attachment is staged, flushed, checksum-verified, and atomically published to a content-addressed FAB evidence path before it is registered by Gmail message and attachment ID. A verified existing file is reused; conflicting retained bytes are never overwritten. Source readiness exposes profile `hp_eprint_v1`, the audited repository/commit, and delivery path `gmail_to_fab_direct` so operators can distinguish this migration from a generic mailbox query.
4. Exact-content duplicates and changed provider revisions are held in the existing review workflow.
5. The autonomous cycle runs OCR, semantic document typing, extraction, validation, learned vendor categorization, and Wave draft preparation. Receipts and vendor invoices are postable evidence. Credit notes become review-gated posting reversals that reduce the original expense and input VAT. Order confirmations, estimates, bank statements, insurance policies, and government correspondence become non-posting supporting evidence.
6. Every accepted scanner PDF receives a source-to-Wave attachment work order. Completion requires the exact stored Wave attachment to be downloaded and verified against the retained source hash, size, filename, MIME type, transaction, and bookkeeping fields.
7. External posting remains approval-gated. Gmail messages and local evidence remain unchanged after verification. Drive-originated files retain the stricter move-only archival gate.

Supporting-evidence records never expose extracted coverage limits, thresholds, deductibles, or other contextual figures as transaction amounts. The original observations remain attached to the source evidence. Conflicting invoice/policy classifications stay blocked until an operator records an audited document-type decision in the review workspace.

The Gmail source message remains unchanged. FAB does not mark it read, relabel it, move it, or delete it. Unlike the old hourly script, the durable provider checkpoint and immutable content hash make overlapping scans idempotent without silently skipping older mail.

## Freshdesk collector consolidation

The optional `freshdesk.financial_filter_enabled` profile ports repository 025's
financial keyword policy into FAB without its ticket-closing or duplicate-Drive
side effects:

1. FAB searches configured Freshdesk ticket statuses, defaulting to open and
   pending (`2,3`), and fetches full ticket details through the read-only API.
2. Subject and normalized description text are matched against configurable
   keywords. The audited legacy terms are the default profile, with the malformed
   concatenated term normalized to `uw bestelling` and `invoice`.
3. A matched ticket description is retained as immutable UTF-8 text and forced
   to a non-posting `supporting_document` record. It can support review but can
   never become a Wave posting.
4. Ticket and conversation attachments are content-addressed, size bounded, and
   optionally restricted to PDF filename/MIME/signature evidence before entering
   the normal duplicate, OCR, review, routing, and attachment-readback workflow.
   The financial profile requires HTTPS and forwards Freshdesk credentials only
   to the configured Freshdesk API host, never to an external attachment host.
5. Diagnostics record matched/filtered tickets, retained descriptions,
   attachments, rejections, the source repository/commit, and
   `externalSubmission=not_executed`.

FAB never closes, relabels, or otherwise mutates the Freshdesk ticket. It does
not copy Freshdesk evidence to Drive because the authoritative local ledger
already retains the source bytes and provenance. One ticket or attachment
failure is isolated so already retained evidence remains auditable.

Repository 025's mutable word-list page maps to the governed
`financial_keywords` configuration, its background-job toggle maps to FAB's
existing worker schedule, and its WebSocket/file progress stream maps to FAB's
durable workflow steps, diagnostics, audit events, and dashboard connection
status. The standalone NestJS/React service is therefore not run alongside FAB.

## Cutover

1. Open **Gmail scanner** in the FAB operator dashboard.
2. Install a Google desktop OAuth client whose Cloud project has Gmail API enabled.
3. Complete the read-only consent flow and verify the connector becomes ready.
4. Run **Sync sources** and confirm a scanner PDF reaches the FAB review workspace with Gmail provenance.
5. Disable the old Apps Script time trigger only after that proof succeeds. Leaving both collectors active can create redundant Drive copies.
6. If a deployed copy of repository 025 has real credentials outside the checked-in placeholders, revoke or rotate them after cutover; FAB does not consume them.

Repository 025 did not categorize documents or create Wave entries. Those downstream responsibilities belong to FAB and remain subject to field validation, account mapping, approval, attachment readback, and archive gates.

Do not delete the old Drive folder or its documents as part of this cutover. Existing Drive evidence continues through FAB's independent high-assurance delivery workflow.
