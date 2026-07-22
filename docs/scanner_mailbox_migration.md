# Scanner mailbox migration

FAB incorporates the useful behavior from `Noodzakelijk-Online/025-Scan-to-folder-automation` as a first-class Gmail scanner profile. It does not import the legacy NestJS/Freshdesk application or any credential material from that repository.

## Active data path

1. Gmail is searched with `label:all from:eprintcenter@hp8.us has:attachment filename:pdf`.
2. FAB independently checks the parsed sender address, filename, MIME type, size, and PDF signature.
3. The attachment is written to a content-addressed local evidence path and registered by Gmail message and attachment ID.
4. Exact-content duplicates and changed provider revisions are held in the existing review workflow.
5. The autonomous cycle runs OCR, extraction, validation, learned vendor categorization, and Wave draft preparation.
6. External posting remains approval-gated. Drive-originated files retain the stricter Wave transaction and exact attachment readback gate before move-only archival.

The Gmail source message remains unchanged. FAB does not mark it read, relabel it, move it, or delete it.

## Cutover

1. Open **Gmail scanner** in the FAB operator dashboard.
2. Install a Google desktop OAuth client whose Cloud project has Gmail API enabled.
3. Complete the read-only consent flow and verify the connector becomes ready.
4. Run **Sync sources** and confirm a scanner PDF reaches the FAB review workspace with Gmail provenance.
5. Disable the old Apps Script time trigger only after that proof succeeds. Leaving both collectors active can create redundant Drive copies.
6. Revoke and rotate any credentials committed in the older repository's tracked `.env`; FAB does not consume them.

Do not delete the old Drive folder or its documents as part of this cutover. Existing Drive evidence continues through FAB's independent high-assurance delivery workflow.
