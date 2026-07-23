# Scanner mailbox migration

Repository `Noodzakelijk-Online/025-Scan-to-folder-automation` at audited source commit `e3078d9` contains two different collectors: a bundled Apps Script that copies HP ePrint PDF attachments from Gmail to one fixed Drive folder, and a separate NestJS service that copies selected Freshdesk ticket content to Drive. FAB incorporates the useful Gmail scanner behavior as a first-class scanner profile. It does not import the legacy services or any credential material from that repository; FAB's existing Freshdesk connector remains separately configurable.

## Active data path

1. Gmail is searched with `label:all from:eprintcenter@hp8.us has:attachment filename:pdf`.
2. FAB independently checks the parsed sender address, filename, MIME type, size, and PDF signature.
3. The attachment is written to a content-addressed local evidence path and registered by Gmail message and attachment ID.
4. Exact-content duplicates and changed provider revisions are held in the existing review workflow.
5. The autonomous cycle runs OCR, semantic document typing, extraction, validation, learned vendor categorization, and Wave draft preparation. Receipts and vendor invoices are postable evidence. Order confirmations, estimates, credit notes, bank statements, insurance policies, and government correspondence become non-posting supporting evidence.
6. External posting remains approval-gated. Drive-originated files retain the stricter Wave transaction and exact attachment readback gate before move-only archival.

Supporting-evidence records never expose extracted coverage limits, thresholds, deductibles, or other contextual figures as transaction amounts. The original observations remain attached to the source evidence. Conflicting invoice/policy classifications stay blocked until an operator records an audited document-type decision in the review workspace.

The Gmail source message remains unchanged. FAB does not mark it read, relabel it, move it, or delete it. Unlike the old hourly script, the durable provider checkpoint and immutable content hash make overlapping scans idempotent without silently skipping older mail.

## Cutover

1. Open **Gmail scanner** in the FAB operator dashboard.
2. Install a Google desktop OAuth client whose Cloud project has Gmail API enabled.
3. Complete the read-only consent flow and verify the connector becomes ready.
4. Run **Sync sources** and confirm a scanner PDF reaches the FAB review workspace with Gmail provenance.
5. Disable the old Apps Script time trigger only after that proof succeeds. Leaving both collectors active can create redundant Drive copies.
6. If a deployed copy of repository 025 has real credentials outside the checked-in placeholders, revoke or rotate them after cutover; FAB does not consume them.

Repository 025 did not categorize documents or create Wave entries. Those downstream responsibilities belong to FAB and remain subject to field validation, account mapping, approval, attachment readback, and archive gates.

Do not delete the old Drive folder or its documents as part of this cutover. Existing Drive evidence continues through FAB's independent high-assurance delivery workflow.
