import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone
from typing import Any, Dict, Optional, Sequence


VENDOR_CATEGORY_RULE_STATUSES = {"suggested", "approved", "rejected", "disabled", "learned"}
GOVERNED_VENDOR_CATEGORY_RULE_STATUSES = {"approved", "rejected", "disabled"}


def default_ledger_path() -> str:
    """Return a Windows-friendly local FAB ledger path without using the repo."""
    base_dir = (
        os.environ.get("FAB_LOCAL_DATA_DIR")
        or os.environ.get("LOCALAPPDATA")
        or os.path.join(os.path.expanduser("~"), ".fab")
    )
    return os.path.join(base_dir, "FAB", "fab_operations.sqlite3")


class LocalOperationsLedger:
    """SQLite operations ledger for local-first FAB workflow runs.

    The ledger mirrors the web operations API shape closely enough that the
    existing Python pipeline can keep one reporting surface for both online and
    offline/local operation. It stores metadata, OCR text, statuses, review
    items, routing attempts, reconciliation matches, and audit events, but it
    does not store credentials or raw attachment bytes.
    """

    def __init__(self, path: str):
        if not path:
            raise ValueError("Local ledger path is required")
        self.path = os.path.abspath(os.path.expanduser(path))
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def _connection(self):
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _init_schema(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS workflow_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT NOT NULL,
                    trigger_source TEXT NOT NULL,
                    documents_imported INTEGER NOT NULL DEFAULT 0,
                    documents_processed INTEGER NOT NULL DEFAULT 0,
                    documents_needing_review INTEGER NOT NULL DEFAULT 0,
                    error_message TEXT,
                    metadata_json TEXT,
                    started_at TEXT,
                    finished_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS source_accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_type TEXT NOT NULL,
                    source_identifier TEXT NOT NULL,
                    label TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    last_seen_at TEXT,
                    last_scan_at TEXT,
                    documents_seen INTEGER NOT NULL DEFAULT 0,
                    documents_imported INTEGER NOT NULL DEFAULT 0,
                    duplicates_detected INTEGER NOT NULL DEFAULT 0,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(source_type, source_identifier)
                );

                CREATE INDEX IF NOT EXISTS idx_local_sources_type
                    ON source_accounts(source_type);
                CREATE INDEX IF NOT EXISTS idx_local_sources_status
                    ON source_accounts(status);

                CREATE TABLE IF NOT EXISTS bookkeeping_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_account_id INTEGER,
                    source TEXT NOT NULL,
                    source_document_id TEXT,
                    original_filename TEXT NOT NULL,
                    mime_type TEXT,
                    storage_path TEXT,
                    document_type TEXT NOT NULL DEFAULT 'unknown',
                    processing_status TEXT NOT NULL DEFAULT 'imported',
                    duplicate_fingerprint TEXT,
                    duplicate_of_document_id INTEGER,
                    vendor_name TEXT,
                    category TEXT,
                    transaction_date TEXT,
                    total_amount REAL,
                    vat_amount REAL,
                    confidence_score REAL,
                    reconciliation_status TEXT NOT NULL DEFAULT 'not_started',
                    ocr_text TEXT,
                    extracted_data_json TEXT,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(source, source_document_id)
                );

                CREATE INDEX IF NOT EXISTS idx_local_docs_status
                    ON bookkeeping_documents(processing_status);
                CREATE INDEX IF NOT EXISTS idx_local_docs_source
                    ON bookkeeping_documents(source, source_document_id);
                CREATE INDEX IF NOT EXISTS idx_local_docs_duplicate
                    ON bookkeeping_documents(duplicate_fingerprint);

                CREATE INDEX IF NOT EXISTS idx_local_runs_status
                    ON workflow_runs(status);

                CREATE TABLE IF NOT EXISTS review_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER,
                    reason TEXT NOT NULL,
                    details TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    corrected_data_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_local_review_status
                    ON review_items(status);

                CREATE TABLE IF NOT EXISTS duplicate_candidates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    candidate_document_id INTEGER NOT NULL,
                    match_type TEXT NOT NULL,
                    confidence_score REAL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    reason TEXT,
                    evidence_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(document_id, candidate_document_id, match_type)
                );

                CREATE INDEX IF NOT EXISTS idx_local_duplicates_document
                    ON duplicate_candidates(document_id);
                CREATE INDEX IF NOT EXISTS idx_local_duplicates_candidate
                    ON duplicate_candidates(candidate_document_id);
                CREATE INDEX IF NOT EXISTS idx_local_duplicates_status
                    ON duplicate_candidates(status);

                CREATE TABLE IF NOT EXISTS document_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_key TEXT NOT NULL,
                    group_type TEXT NOT NULL DEFAULT 'scanner_batch',
                    title TEXT,
                    status TEXT NOT NULL DEFAULT 'candidate',
                    primary_document_id INTEGER,
                    confidence_score REAL,
                    reason TEXT,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(group_key)
                );

                CREATE INDEX IF NOT EXISTS idx_local_document_groups_status
                    ON document_groups(status);
                CREATE INDEX IF NOT EXISTS idx_local_document_groups_type
                    ON document_groups(group_type);

                CREATE TABLE IF NOT EXISTS document_group_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER NOT NULL,
                    document_id INTEGER NOT NULL,
                    role TEXT NOT NULL DEFAULT 'page',
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'active',
                    metadata_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(group_id, document_id)
                );

                CREATE INDEX IF NOT EXISTS idx_local_group_members_group
                    ON document_group_members(group_id);
                CREATE INDEX IF NOT EXISTS idx_local_group_members_document
                    ON document_group_members(document_id);
                CREATE INDEX IF NOT EXISTS idx_local_group_members_status
                    ON document_group_members(status);

                CREATE TABLE IF NOT EXISTS extracted_fields (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    field_name TEXT NOT NULL,
                    field_value_json TEXT,
                    normalized_value TEXT,
                    confidence_score REAL,
                    source TEXT NOT NULL DEFAULT 'local_processing',
                    provenance_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_local_extracted_fields_document
                    ON extracted_fields(document_id);
                CREATE INDEX IF NOT EXISTS idx_local_extracted_fields_name
                    ON extracted_fields(field_name);

                CREATE TABLE IF NOT EXISTS review_corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    review_item_id INTEGER,
                    document_id INTEGER,
                    original_data_json TEXT,
                    corrected_data_json TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_local_corrections_document
                    ON review_corrections(document_id);

                CREATE TABLE IF NOT EXISTS vendor_category_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    normalized_vendor_name TEXT NOT NULL,
                    vendor_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    target_system TEXT NOT NULL DEFAULT 'none',
                    confidence_score REAL,
                    status TEXT NOT NULL DEFAULT 'learned',
                    source_document_id TEXT,
                    usage_count INTEGER NOT NULL DEFAULT 1,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(normalized_vendor_name, category, target_system)
                );

                CREATE INDEX IF NOT EXISTS idx_local_vendor_rules_vendor
                    ON vendor_category_rules(normalized_vendor_name);
                CREATE INDEX IF NOT EXISTS idx_local_vendor_rules_status
                    ON vendor_category_rules(status);

                CREATE TABLE IF NOT EXISTS routing_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER,
                    bookkeeping_record_id INTEGER,
                    workflow_run_id INTEGER,
                    target TEXT NOT NULL,
                    status TEXT NOT NULL,
                    external_id TEXT,
                    message TEXT,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_local_routing_status
                    ON routing_attempts(status);
            CREATE INDEX IF NOT EXISTS idx_local_routing_target
                ON routing_attempts(target);
            CREATE INDEX IF NOT EXISTS idx_local_routing_record
                ON routing_attempts(bookkeeping_record_id);

                CREATE TABLE IF NOT EXISTS export_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bookkeeping_record_id INTEGER,
                    document_id INTEGER,
                    routing_attempt_id INTEGER,
                    workflow_run_id INTEGER,
                    target_system TEXT NOT NULL DEFAULT 'waveapps',
                    target_account TEXT,
                    action_id TEXT,
                    surface TEXT,
                    operation_id TEXT,
                    status TEXT NOT NULL DEFAULT 'approval_required',
                    safety TEXT NOT NULL DEFAULT 'requires_confirmation',
                    approval_required INTEGER NOT NULL DEFAULT 1,
                    approved_at TEXT,
                    approved_by TEXT,
                    external_submission TEXT NOT NULL DEFAULT 'not_executed',
                    submitted_at TEXT,
                    external_id TEXT,
                    message TEXT,
                    payload_json TEXT,
                    result_json TEXT,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE UNIQUE INDEX IF NOT EXISTS idx_local_exports_routing_unique
                    ON export_attempts(routing_attempt_id)
                    WHERE routing_attempt_id IS NOT NULL;
                CREATE UNIQUE INDEX IF NOT EXISTS idx_local_exports_operation_unique
                    ON export_attempts(operation_id)
                    WHERE operation_id IS NOT NULL;
                CREATE INDEX IF NOT EXISTS idx_local_exports_status
                    ON export_attempts(status);
                CREATE INDEX IF NOT EXISTS idx_local_exports_external
                    ON export_attempts(external_submission);
                CREATE INDEX IF NOT EXISTS idx_local_exports_target
                    ON export_attempts(target_system);
                CREATE INDEX IF NOT EXISTS idx_local_exports_document
                    ON export_attempts(document_id);

                CREATE TABLE IF NOT EXISTS reconciliation_matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER,
                    bank_transaction_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    confidence_score REAL,
                    amount_difference REAL,
                    matched_at TEXT,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_local_reconciliation_status
                    ON reconciliation_matches(status);
                CREATE INDEX IF NOT EXISTS idx_local_reconciliation_document
                    ON reconciliation_matches(document_id);
                CREATE INDEX IF NOT EXISTS idx_local_reconciliation_bank_tx
                    ON reconciliation_matches(bank_transaction_id);

                CREATE TABLE IF NOT EXISTS bank_statement_imports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL DEFAULT 'manual_import',
                    account_identifier TEXT NOT NULL DEFAULT 'default',
                    filename TEXT,
                    format TEXT NOT NULL DEFAULT 'json',
                    status TEXT NOT NULL DEFAULT 'running',
                    rows_seen INTEGER NOT NULL DEFAULT 0,
                    rows_imported INTEGER NOT NULL DEFAULT 0,
                    duplicates INTEGER NOT NULL DEFAULT 0,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_local_bank_imports_account
                    ON bank_statement_imports(account_identifier);
                CREATE INDEX IF NOT EXISTS idx_local_bank_imports_status
                    ON bank_statement_imports(status);

                CREATE TABLE IF NOT EXISTS bank_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    import_id INTEGER,
                    account_identifier TEXT NOT NULL DEFAULT 'default',
                    transaction_id TEXT NOT NULL,
                    transaction_date TEXT,
                    amount REAL,
                    currency TEXT NOT NULL DEFAULT 'EUR',
                    description TEXT,
                    counterparty TEXT,
                    status TEXT NOT NULL DEFAULT 'imported',
                    reconciliation_status TEXT NOT NULL DEFAULT 'not_started',
                    duplicate_fingerprint TEXT,
                    source TEXT NOT NULL DEFAULT 'manual_import',
                    metadata_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(account_identifier, transaction_id)
                );

                CREATE INDEX IF NOT EXISTS idx_local_bank_tx_account
                    ON bank_transactions(account_identifier);
                CREATE INDEX IF NOT EXISTS idx_local_bank_tx_status
                    ON bank_transactions(status);
                CREATE INDEX IF NOT EXISTS idx_local_bank_tx_reconciliation
                    ON bank_transactions(reconciliation_status);
                CREATE INDEX IF NOT EXISTS idx_local_bank_tx_date
                    ON bank_transactions(transaction_date);
                CREATE INDEX IF NOT EXISTS idx_local_bank_tx_fingerprint
                    ON bank_transactions(duplicate_fingerprint);

                CREATE TABLE IF NOT EXISTS bookkeeping_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER,
                    bank_transaction_id INTEGER,
                    source_type TEXT NOT NULL DEFAULT 'document',
                    record_type TEXT NOT NULL DEFAULT 'expense',
                    status TEXT NOT NULL DEFAULT 'draft',
                    target_system TEXT NOT NULL DEFAULT 'waveapps',
                    target_account TEXT,
                    vendor_name TEXT,
                    category TEXT,
                    record_date TEXT,
                    amount REAL,
                    vat_amount REAL,
                    currency TEXT NOT NULL DEFAULT 'EUR',
                    description TEXT,
                    confidence_score REAL,
                    review_required INTEGER NOT NULL DEFAULT 0,
                    export_status TEXT NOT NULL DEFAULT 'not_started',
                    reconciliation_status TEXT NOT NULL DEFAULT 'not_started',
                    metadata_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE UNIQUE INDEX IF NOT EXISTS idx_local_records_document_unique
                    ON bookkeeping_records(document_id)
                    WHERE document_id IS NOT NULL;
                CREATE UNIQUE INDEX IF NOT EXISTS idx_local_records_bank_unique
                    ON bookkeeping_records(bank_transaction_id)
                    WHERE bank_transaction_id IS NOT NULL;
                CREATE INDEX IF NOT EXISTS idx_local_records_status
                    ON bookkeeping_records(status);
                CREATE INDEX IF NOT EXISTS idx_local_records_target
                    ON bookkeeping_records(target_system);
                CREATE INDEX IF NOT EXISTS idx_local_records_export
                    ON bookkeeping_records(export_status);
                CREATE INDEX IF NOT EXISTS idx_local_records_reconciliation
                    ON bookkeeping_records(reconciliation_status);

                CREATE TABLE IF NOT EXISTS bookkeeping_record_line_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bookkeeping_record_id INTEGER NOT NULL,
                    line_index INTEGER NOT NULL DEFAULT 0,
                    item_name TEXT,
                    description TEXT,
                    quantity REAL,
                    unit_price REAL,
                    amount REAL,
                    tax_amount REAL,
                    tax_rate REAL,
                    tax_code TEXT,
                    category TEXT,
                    account_name TEXT,
                    source TEXT NOT NULL DEFAULT 'extraction',
                    confidence_score REAL,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(bookkeeping_record_id, line_index),
                    FOREIGN KEY(bookkeeping_record_id) REFERENCES bookkeeping_records(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_local_record_lines_record
                    ON bookkeeping_record_line_items(bookkeeping_record_id);
                CREATE INDEX IF NOT EXISTS idx_local_record_lines_account
                    ON bookkeeping_record_line_items(account_name);
                CREATE INDEX IF NOT EXISTS idx_local_record_lines_tax
                    ON bookkeeping_record_line_items(tax_code);

                CREATE TABLE IF NOT EXISTS wave_report_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_run_id INTEGER,
                    operation_id TEXT NOT NULL,
                    workflow_id TEXT,
                    report_type TEXT NOT NULL,
                    report_section TEXT,
                    action_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'planned',
                    safety TEXT NOT NULL DEFAULT 'read_only',
                    from_date TEXT,
                    to_date TEXT,
                    as_of_date TEXT,
                    basis TEXT,
                    account_option TEXT,
                    account_name TEXT,
                    contact_option TEXT,
                    contact_name TEXT,
                    cash_mode TEXT,
                    export_format TEXT,
                    row_count INTEGER,
                    total_debits REAL,
                    total_credits REAL,
                    total_amount REAL,
                    external_submission TEXT NOT NULL DEFAULT 'not_executed',
                    metadata_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(operation_id)
                );

                CREATE INDEX IF NOT EXISTS idx_local_wave_reports_type
                    ON wave_report_snapshots(report_type);
                CREATE INDEX IF NOT EXISTS idx_local_wave_reports_status
                    ON wave_report_snapshots(status);
                CREATE INDEX IF NOT EXISTS idx_local_wave_reports_workflow
                    ON wave_report_snapshots(workflow_id);

                CREATE TABLE IF NOT EXISTS wave_operation_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_run_id INTEGER,
                    workflow_id TEXT,
                    operation_id TEXT NOT NULL,
                    surface TEXT,
                    action_id TEXT,
                    mode TEXT,
                    safety TEXT NOT NULL DEFAULT 'unsupported',
                    status TEXT NOT NULL DEFAULT 'planned',
                    plan_status TEXT,
                    plan_json TEXT,
                    capability_plan_json TEXT,
                    requires_confirmation INTEGER,
                    requires_credentials INTEGER,
                    required_fields_json TEXT,
                    missing_fields_json TEXT,
                    external_submission TEXT NOT NULL DEFAULT 'not_executed',
                    payload_json TEXT,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(operation_id)
                );

                CREATE INDEX IF NOT EXISTS idx_local_wave_ops_status
                    ON wave_operation_snapshots(status);
                CREATE INDEX IF NOT EXISTS idx_local_wave_ops_surface
                    ON wave_operation_snapshots(surface);
                CREATE INDEX IF NOT EXISTS idx_local_wave_ops_safety
                    ON wave_operation_snapshots(safety);
                CREATE INDEX IF NOT EXISTS idx_local_wave_ops_workflow
                    ON wave_operation_snapshots(workflow_id);

                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor_user_id INTEGER,
                    action TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT,
                    details_json TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_local_audit_entity
                    ON audit_events(entity_type, entity_id);
                CREATE INDEX IF NOT EXISTS idx_local_audit_created
                    ON audit_events(created_at);
                """
            )
            self._ensure_column(
                connection,
                "bookkeeping_documents",
                "source_account_id",
                "INTEGER",
            )
            self._ensure_column(
                connection,
                "bookkeeping_documents",
                "reconciliation_status",
                "TEXT NOT NULL DEFAULT 'not_started'",
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_local_docs_reconciliation
                    ON bookkeeping_documents(reconciliation_status)
                """
            )
            self._ensure_bookkeeping_record_schema(connection)
            self._ensure_bookkeeping_record_line_item_schema(connection)
            self._ensure_routing_attempt_schema(connection)
            self._ensure_export_attempt_schema(connection)
            self._ensure_wave_operation_snapshot_schema(connection)

    def upsert_source_account(self, payload: Dict[str, Any]) -> int:
        source_type = str(payload.get("sourceType") or payload.get("source_type") or "unknown").strip()
        source_identifier = str(payload.get("sourceIdentifier") or payload.get("source_identifier") or "").strip()
        if not source_identifier:
            raise ValueError("sourceIdentifier is required for a source account")
        label = str(payload.get("label") or os.path.basename(source_identifier) or source_identifier).strip()
        status = str(payload.get("status") or "active").strip() or "active"
        now = self._now()
        last_seen_at = self._date_text(payload.get("lastSeenAt") or payload.get("last_seen_at"))
        last_scan_at = self._date_text(payload.get("lastScanAt") or payload.get("last_scan_at"))
        documents_seen = self._int(payload.get("documentsSeen") or payload.get("documents_seen"), 0)
        documents_imported = self._int(payload.get("documentsImported") or payload.get("documents_imported"), 0)
        duplicates_detected = self._int(payload.get("duplicatesDetected") or payload.get("duplicates_detected"), 0)

        with self._connection() as connection:
            existing = connection.execute(
                """
                SELECT * FROM source_accounts
                WHERE source_type = ? AND source_identifier = ?
                LIMIT 1
                """,
                (source_type, source_identifier),
            ).fetchone()
            if existing:
                source_account_id = int(existing["id"])
                self._update_with_connection(
                    connection,
                    "source_accounts",
                    source_account_id,
                    {
                        "label": label,
                        "status": status,
                        "last_seen_at": last_seen_at or existing["last_seen_at"],
                        "last_scan_at": last_scan_at or existing["last_scan_at"],
                        "documents_seen": int(existing["documents_seen"] or 0) + documents_seen,
                        "documents_imported": int(existing["documents_imported"] or 0) + documents_imported,
                        "duplicates_detected": int(existing["duplicates_detected"] or 0) + duplicates_detected,
                        "metadata_json": self._json(self._redact_sensitive(payload.get("metadata"))),
                        "updated_at": now,
                    },
                )
                return source_account_id
            return self._insert_with_connection(
                connection,
                "source_accounts",
                {
                    "source_type": source_type,
                    "source_identifier": source_identifier,
                    "label": label,
                    "status": status,
                    "last_seen_at": last_seen_at,
                    "last_scan_at": last_scan_at,
                    "documents_seen": documents_seen,
                    "documents_imported": documents_imported,
                    "duplicates_detected": duplicates_detected,
                    "metadata_json": self._json(self._redact_sensitive(payload.get("metadata"))),
                    "created_at": now,
                    "updated_at": now,
                },
            )

    def create_workflow_run(self, payload: Dict[str, Any], preferred_id: Optional[int] = None) -> int:
        now = self._now()
        values = {
            "id": preferred_id,
            "status": payload.get("status", "running"),
            "trigger_source": payload.get("triggerSource") or payload.get("trigger_source") or "manual",
            "documents_imported": self._int(payload.get("documentsImported"), 0),
            "documents_processed": self._int(payload.get("documentsProcessed"), 0),
            "documents_needing_review": self._int(payload.get("documentsNeedingReview"), 0),
            "error_message": payload.get("errorMessage"),
            "metadata_json": self._json(payload.get("metadata")),
            "started_at": self._date_text(payload.get("startedAt")) or now,
            "finished_at": self._date_text(payload.get("finishedAt")),
            "created_at": now,
            "updated_at": now,
        }
        return self._insert("workflow_runs", values)

    def update_workflow_run(self, workflow_run_id: int, payload: Dict[str, Any]) -> None:
        fields = {
            "status": payload.get("status"),
            "documents_imported": payload.get("documentsImported"),
            "documents_processed": payload.get("documentsProcessed"),
            "documents_needing_review": payload.get("documentsNeedingReview"),
            "error_message": payload.get("errorMessage"),
            "started_at": self._date_text(payload.get("startedAt")),
            "finished_at": self._date_text(payload.get("finishedAt")),
            "updated_at": self._now(),
        }
        self._update("workflow_runs", workflow_run_id, fields)

    def register_document(self, payload: Dict[str, Any], preferred_id: Optional[int] = None) -> int:
        now = self._now()
        values = {
            "id": preferred_id,
            "source_account_id": payload.get("sourceAccountId") or payload.get("source_account_id"),
            "source": payload.get("source", "unknown"),
            "source_document_id": payload.get("sourceDocumentId"),
            "original_filename": payload.get("originalFilename", "unknown"),
            "mime_type": payload.get("mimeType"),
            "storage_path": payload.get("storagePath"),
            "document_type": payload.get("documentType", "unknown"),
            "processing_status": payload.get("processingStatus", "imported"),
            "duplicate_fingerprint": payload.get("duplicateFingerprint"),
            "duplicate_of_document_id": payload.get("duplicateOfDocumentId"),
            "vendor_name": payload.get("vendorName"),
            "category": payload.get("category"),
            "transaction_date": payload.get("transactionDate"),
            "total_amount": self._float(payload.get("totalAmount")),
            "vat_amount": self._float(payload.get("vatAmount")),
            "confidence_score": self._float(payload.get("confidenceScore")),
            "reconciliation_status": payload.get("reconciliationStatus", "not_started"),
            "ocr_text": payload.get("ocrText"),
            "extracted_data_json": self._json(payload.get("extractedData")),
            "metadata_json": self._json(payload.get("metadata")),
            "created_at": now,
            "updated_at": now,
        }
        with self._connection() as connection:
            existing_id = self._existing_document_id(connection, values["source"], values["source_document_id"])
            if existing_id is not None:
                update_values = dict(values)
                update_values.pop("id", None)
                update_values.pop("created_at", None)
                self._update_with_connection(connection, "bookkeeping_documents", existing_id, update_values)
                return existing_id
            return self._insert_with_connection(connection, "bookkeeping_documents", values)

    def update_document(self, document_id: int, payload: Dict[str, Any]) -> None:
        fields = {
            "source_account_id": payload.get("sourceAccountId") or payload.get("source_account_id"),
            "source": payload.get("source"),
            "source_document_id": payload.get("sourceDocumentId"),
            "original_filename": payload.get("originalFilename"),
            "mime_type": payload.get("mimeType"),
            "storage_path": payload.get("storagePath"),
            "document_type": payload.get("documentType"),
            "processing_status": payload.get("processingStatus"),
            "duplicate_fingerprint": payload.get("duplicateFingerprint"),
            "duplicate_of_document_id": payload.get("duplicateOfDocumentId"),
            "vendor_name": payload.get("vendorName"),
            "category": payload.get("category"),
            "transaction_date": payload.get("transactionDate"),
            "total_amount": self._float(payload.get("totalAmount")),
            "vat_amount": self._float(payload.get("vatAmount")),
            "confidence_score": self._float(payload.get("confidenceScore")),
            "reconciliation_status": payload.get("reconciliationStatus"),
            "ocr_text": payload.get("ocrText"),
            "extracted_data_json": self._json(payload.get("extractedData")),
            "metadata_json": self._json(payload.get("metadata")),
            "updated_at": self._now(),
        }
        self._update("bookkeeping_documents", document_id, fields)

    def clear_document_duplicate(self, document_id: int) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE bookkeeping_documents
                SET duplicate_of_document_id = NULL, updated_at = ?
                WHERE id = ?
                """,
                (self._now(), document_id),
            )

    def create_review_item(self, payload: Dict[str, Any], preferred_id: Optional[int] = None) -> int:
        now = self._now()
        return self._insert(
            "review_items",
            {
                "id": preferred_id,
                "document_id": payload.get("documentId"),
                "reason": payload.get("reason", "manual_review"),
                "details": payload.get("details"),
                "status": payload.get("status", "pending"),
                "corrected_data_json": self._json(payload.get("correctedData")),
                "created_at": now,
                "updated_at": now,
            },
        )

    def record_duplicate_candidate(self, payload: Dict[str, Any], preferred_id: Optional[int] = None) -> int:
        document_id = self._optional_int(payload.get("documentId") or payload.get("document_id"))
        candidate_document_id = self._optional_int(
            payload.get("candidateDocumentId") or payload.get("candidate_document_id")
        )
        if document_id is None or candidate_document_id is None:
            raise ValueError("documentId and candidateDocumentId are required for a duplicate candidate")
        if document_id == candidate_document_id:
            raise ValueError("duplicate candidate cannot reference the same document twice")
        match_type = str(payload.get("matchType") or payload.get("match_type") or "unknown").strip() or "unknown"
        now = self._now()
        values = {
            "id": preferred_id,
            "document_id": document_id,
            "candidate_document_id": candidate_document_id,
            "match_type": match_type,
            "confidence_score": self._float(self._first_present(payload.get("confidenceScore"), payload.get("confidence_score"))),
            "status": payload.get("status") or "pending",
            "reason": payload.get("reason"),
            "evidence_json": self._json(self._redact_sensitive(payload.get("evidence"))),
            "created_at": now,
            "updated_at": now,
        }
        with self._connection() as connection:
            existing = connection.execute(
                """
                SELECT id FROM duplicate_candidates
                WHERE document_id = ? AND candidate_document_id = ? AND match_type = ?
                LIMIT 1
                """,
                (document_id, candidate_document_id, match_type),
            ).fetchone()
            if existing:
                candidate_id = int(existing["id"])
                update_values = dict(values)
                update_values.pop("id", None)
                update_values.pop("created_at", None)
                self._update_with_connection(connection, "duplicate_candidates", candidate_id, update_values)
                return candidate_id
            return self._insert_with_connection(connection, "duplicate_candidates", values)

    def list_duplicate_candidates(
        self,
        status: Optional[Any] = None,
        document_id: Optional[int] = None,
        candidate_document_id: Optional[int] = None,
        limit: int = 100,
    ) -> list:
        limit = self._bounded_limit(limit)
        query = "SELECT * FROM duplicate_candidates"
        params = []
        where = []
        self._append_status_filter(where, params, "status", status)
        if document_id is not None:
            where.append("document_id = ?")
            params.append(document_id)
        if candidate_document_id is not None:
            where.append("candidate_document_id = ?")
            params.append(candidate_document_id)
        if where:
            query = f"{query} WHERE {' AND '.join(where)}"
        query = f"{query} ORDER BY updated_at DESC, id DESC LIMIT ?"
        params.append(limit)
        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def resolve_duplicate_candidates_for_document(
        self,
        document_id: int,
        status: str,
        resolution: Optional[str] = None,
    ) -> int:
        metadata = {"resolution": resolution} if resolution else None
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM duplicate_candidates
                WHERE document_id = ? AND status IN ('pending', 'in_review')
                """,
                (document_id,),
            ).fetchall()
            updated = 0
            for row in rows:
                evidence = self._row_to_dict(row).get("evidence") or {}
                if metadata:
                    evidence = {**evidence, **metadata}
                self._update_with_connection(
                    connection,
                    "duplicate_candidates",
                    int(row["id"]),
                    {
                        "status": status,
                        "evidence_json": self._json(evidence),
                        "updated_at": self._now(),
                    },
                )
                updated += 1
            return updated

    def upsert_document_group(self, payload: Dict[str, Any], preferred_id: Optional[int] = None) -> int:
        group_key = str(payload.get("groupKey") or payload.get("group_key") or "").strip()
        if not group_key:
            raise ValueError("groupKey is required for a document group")
        now = self._now()
        values = {
            "id": preferred_id,
            "group_key": group_key,
            "group_type": payload.get("groupType") or payload.get("group_type") or "scanner_batch",
            "title": payload.get("title"),
            "status": payload.get("status") or "candidate",
            "primary_document_id": self._optional_int(
                payload.get("primaryDocumentId") or payload.get("primary_document_id")
            ),
            "confidence_score": self._float(self._first_present(payload.get("confidenceScore"), payload.get("confidence_score"))),
            "reason": payload.get("reason"),
            "metadata_json": self._json(self._redact_sensitive(payload.get("metadata"))),
            "created_at": now,
            "updated_at": now,
        }
        with self._connection() as connection:
            existing = connection.execute(
                "SELECT id FROM document_groups WHERE group_key = ? LIMIT 1",
                (group_key,),
            ).fetchone()
            if existing:
                group_id = int(existing["id"])
                update_values = dict(values)
                update_values.pop("id", None)
                update_values.pop("created_at", None)
                self._update_with_connection(connection, "document_groups", group_id, update_values)
                return group_id
            return self._insert_with_connection(connection, "document_groups", values)

    def add_document_to_group(self, group_id: int, document_id: int, payload: Optional[Dict[str, Any]] = None) -> int:
        payload = payload or {}
        now = self._now()
        values = {
            "group_id": group_id,
            "document_id": document_id,
            "role": payload.get("role") or "page",
            "sort_order": self._int(payload.get("sortOrder") or payload.get("sort_order"), 0),
            "status": payload.get("status") or "active",
            "metadata_json": self._json(self._redact_sensitive(payload.get("metadata"))),
            "created_at": now,
            "updated_at": now,
        }
        with self._connection() as connection:
            existing = connection.execute(
                """
                SELECT id FROM document_group_members
                WHERE group_id = ? AND document_id = ?
                LIMIT 1
                """,
                (group_id, document_id),
            ).fetchone()
            if existing:
                member_id = int(existing["id"])
                update_values = dict(values)
                update_values.pop("group_id", None)
                update_values.pop("document_id", None)
                update_values.pop("created_at", None)
                self._update_with_connection(connection, "document_group_members", member_id, update_values)
                return member_id
            return self._insert_with_connection(connection, "document_group_members", values)

    def remove_document_from_group(self, group_id: int, document_id: int, reason: Optional[str] = None) -> int:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT * FROM document_group_members
                WHERE group_id = ? AND document_id = ?
                LIMIT 1
                """,
                (group_id, document_id),
            ).fetchone()
            if not row:
                return 0
            member = self._row_to_dict(row)
            metadata = member.get("metadata") or {}
            if reason:
                metadata["removedReason"] = reason
            self._update_with_connection(
                connection,
                "document_group_members",
                int(row["id"]),
                {
                    "status": "removed",
                    "metadata_json": self._json(metadata),
                    "updated_at": self._now(),
                },
            )
            return 1

    def update_document_group_status(self, group_id: int, status: str, resolution: Optional[str] = None) -> None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM document_groups WHERE id = ? LIMIT 1",
                (group_id,),
            ).fetchone()
            if not row:
                return
            group = self._row_to_dict(row)
            metadata = group.get("metadata") or {}
            if resolution:
                metadata["resolution"] = resolution
            self._update_with_connection(
                connection,
                "document_groups",
                group_id,
                {
                    "status": status,
                    "metadata_json": self._json(metadata),
                    "updated_at": self._now(),
                },
            )

    def get_document_group(self, group_id: int) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM document_groups WHERE id = ? LIMIT 1",
                (group_id,),
            ).fetchone()
            return self._document_group_with_members(connection, row) if row else None

    def list_document_groups(
        self,
        status: Optional[Any] = None,
        group_type: Optional[str] = None,
        document_id: Optional[int] = None,
        limit: int = 100,
    ) -> list:
        limit = self._bounded_limit(limit)
        query = "SELECT DISTINCT g.* FROM document_groups g"
        params = []
        where = []
        if document_id is not None:
            query = f"{query} JOIN document_group_members m ON m.group_id = g.id"
            where.append("m.document_id = ?")
            params.append(document_id)
        self._append_status_filter(where, params, "g.status", status)
        if group_type:
            where.append("g.group_type = ?")
            params.append(group_type)
        if where:
            query = f"{query} WHERE {' AND '.join(where)}"
        query = f"{query} ORDER BY g.updated_at DESC, g.id DESC LIMIT ?"
        params.append(limit)
        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()
            return [self._document_group_with_members(connection, row) for row in rows]

    def replace_extracted_fields(
        self,
        document_id: int,
        fields: Sequence[Dict[str, Any]],
        source: str = "local_processing",
    ) -> None:
        now = self._now()
        with self._connection() as connection:
            connection.execute(
                "DELETE FROM extracted_fields WHERE document_id = ? AND source = ?",
                (document_id, source),
            )
            for field in fields:
                field_name = str(field.get("fieldName") or field.get("field_name") or "").strip()
                if not field_name:
                    continue
                field_source = str(field.get("source") or source)
                connection.execute(
                    """
                    INSERT INTO extracted_fields (
                        document_id,
                        field_name,
                        field_value_json,
                        normalized_value,
                        confidence_score,
                        source,
                        provenance_json,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document_id,
                        field_name,
                        self._json(field.get("value")),
                        self._normalized_field_value(field.get("value")),
                        self._float(field.get("confidenceScore") or field.get("confidence_score")),
                        field_source,
                        self._json(field.get("provenance")),
                        now,
                        now,
                    ),
                )

    def list_extracted_fields(
        self,
        document_id: Optional[int] = None,
        field_name: Optional[str] = None,
        limit: int = 100,
    ) -> list:
        limit = self._bounded_limit(limit)
        query = "SELECT * FROM extracted_fields"
        params = []
        where = []
        if document_id is not None:
            where.append("document_id = ?")
            params.append(document_id)
        if field_name:
            where.append("field_name = ?")
            params.append(field_name)
        if where:
            query = f"{query} WHERE {' AND '.join(where)}"
        query = f"{query} ORDER BY id ASC LIMIT ?"
        params.append(limit)
        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def create_routing_attempt(self, payload: Dict[str, Any], preferred_id: Optional[int] = None) -> int:
        return self._insert(
            "routing_attempts",
            {
                "id": preferred_id,
                "document_id": payload.get("documentId"),
                "bookkeeping_record_id": self._optional_int(self._payload_value(
                    payload,
                    "bookkeepingRecordId",
                    "bookkeeping_record_id",
                )),
                "workflow_run_id": payload.get("workflowRunId"),
                "target": payload.get("target", "none"),
                "status": payload.get("status", "pending"),
                "external_id": payload.get("externalId"),
                "message": payload.get("message"),
                "metadata_json": self._json(payload.get("metadata")),
                "created_at": self._now(),
            },
        )

    def get_routing_attempt(self, routing_attempt_id: int) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM routing_attempts WHERE id = ? LIMIT 1",
                (routing_attempt_id,),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def upsert_export_attempt(self, payload: Dict[str, Any], preferred_id: Optional[int] = None) -> int:
        now = self._now()
        values = self._export_attempt_values(payload, now=now, include_defaults=True)
        values["id"] = preferred_id
        values["created_at"] = now
        values["updated_at"] = now
        with self._connection() as connection:
            existing_id = self._existing_export_attempt_id(
                connection,
                routing_attempt_id=values.get("routing_attempt_id"),
                operation_id=values.get("operation_id"),
            )
            if existing_id is not None:
                update_values = self._export_attempt_values(payload, now=now, include_defaults=False)
                update_values["updated_at"] = now
                self._update_with_connection(connection, "export_attempts", existing_id, update_values)
                return existing_id
            return self._insert_with_connection(connection, "export_attempts", values)

    def update_export_attempt(self, export_attempt_id: int, payload: Dict[str, Any]) -> None:
        values = self._export_attempt_values(payload, now=self._now(), include_defaults=False)
        values["updated_at"] = self._now()
        self._update("export_attempts", export_attempt_id, values)

    def claim_export_attempt(
        self,
        export_attempt_id: int,
        allowed_statuses: Optional[Any] = None,
    ) -> Dict[str, Any]:
        allowed = {str(status) for status in (allowed_statuses or ("approved",))}
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM export_attempts WHERE id = ? LIMIT 1",
                (export_attempt_id,),
            ).fetchone()
            if not row:
                return {"status": "not_found", "exportAttemptId": export_attempt_id}
            current_status = str(row["status"] or "")
            if current_status not in allowed:
                return {
                    "status": "not_claimable",
                    "exportAttemptId": export_attempt_id,
                    "currentStatus": current_status,
                }
            now = self._now()
            cursor = connection.execute(
                """
                UPDATE export_attempts
                SET status = 'execution_in_progress', updated_at = ?
                WHERE id = ? AND status = ?
                """,
                (now, export_attempt_id, current_status),
            )
            if cursor.rowcount != 1:
                return {"status": "already_claimed", "exportAttemptId": export_attempt_id}
            return {
                "status": "claimed",
                "exportAttemptId": export_attempt_id,
                "attempt": self._row_to_dict(row),
            }

    def get_export_attempt(self, export_attempt_id: int) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM export_attempts WHERE id = ? LIMIT 1",
                (export_attempt_id,),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def list_export_attempts(
        self,
        status: Optional[Any] = None,
        external_submission: Optional[Any] = None,
        target_system: Optional[str] = None,
        document_id: Optional[int] = None,
        bookkeeping_record_id: Optional[int] = None,
        limit: int = 100,
    ) -> list:
        limit = self._bounded_limit(limit)
        query = "SELECT * FROM export_attempts"
        params = []
        where = []
        self._append_status_filter(where, params, "status", status)
        self._append_status_filter(where, params, "external_submission", external_submission)
        if target_system:
            where.append("target_system = ?")
            params.append(target_system)
        if document_id is not None:
            where.append("document_id = ?")
            params.append(document_id)
        if bookkeeping_record_id is not None:
            where.append("bookkeeping_record_id = ?")
            params.append(bookkeeping_record_id)
        if where:
            query = f"{query} WHERE {' AND '.join(where)}"
        query = f"{query} ORDER BY updated_at DESC, id DESC LIMIT ?"
        params.append(limit)
        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def create_reconciliation_match(self, payload: Dict[str, Any], preferred_id: Optional[int] = None) -> int:
        return self._insert(
            "reconciliation_matches",
            {
                "id": preferred_id,
                "document_id": payload.get("documentId"),
                "bank_transaction_id": payload.get("bankTransactionId", "unknown"),
                "status": payload.get("status", "review"),
                "confidence_score": self._float(payload.get("confidenceScore")),
                "amount_difference": self._float(payload.get("amountDifference")),
                "matched_at": self._date_text(payload.get("matchedAt")),
                "metadata_json": self._json(payload.get("metadata")),
                "created_at": self._now(),
            },
        )

    def update_reconciliation_match(self, reconciliation_match_id: int, payload: Dict[str, Any]) -> None:
        self._update(
            "reconciliation_matches",
            reconciliation_match_id,
            {
                "document_id": payload.get("documentId"),
                "bank_transaction_id": payload.get("bankTransactionId"),
                "status": payload.get("status"),
                "confidence_score": self._float(payload.get("confidenceScore")),
                "amount_difference": self._float(payload.get("amountDifference")),
                "matched_at": self._date_text(payload.get("matchedAt")),
                "metadata_json": self._json(payload.get("metadata")),
            },
        )

    def upsert_bookkeeping_record(self, payload: Dict[str, Any], preferred_id: Optional[int] = None) -> int:
        now = self._now()
        document_id = self._optional_int(self._payload_value(payload, "documentId", "document_id"))
        bank_transaction_id = self._optional_int(self._payload_value(
            payload,
            "bankTransactionId",
            "bank_transaction_id",
        ))
        insert_values = self._bookkeeping_record_values(payload, now=now, include_defaults=True)
        insert_values["id"] = preferred_id
        insert_values["created_at"] = now
        insert_values["updated_at"] = now

        with self._connection() as connection:
            existing_id = self._existing_bookkeeping_record_id(
                connection,
                document_id=document_id,
                bank_transaction_id=bank_transaction_id,
            )
            if existing_id is not None:
                update_values = self._bookkeeping_record_values(payload, now=now, include_defaults=False)
                update_values["updated_at"] = now
                self._update_with_connection(connection, "bookkeeping_records", existing_id, update_values)
                return existing_id
            return self._insert_with_connection(connection, "bookkeeping_records", insert_values)

    def update_bookkeeping_record(self, record_id: int, payload: Dict[str, Any]) -> None:
        values = self._bookkeeping_record_values(payload, now=self._now(), include_defaults=False)
        values["updated_at"] = self._now()
        self._update("bookkeeping_records", record_id, values)

    def get_bookkeeping_record(self, record_id: int) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM bookkeeping_records WHERE id = ? LIMIT 1",
                (record_id,),
            ).fetchone()
            return self._bookkeeping_record_with_line_items(connection, row) if row else None

    def get_bookkeeping_record_by_document(self, document_id: int) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM bookkeeping_records WHERE document_id = ? LIMIT 1",
                (document_id,),
            ).fetchone()
            return self._bookkeeping_record_with_line_items(connection, row) if row else None

    def get_bookkeeping_record_by_bank_transaction(self, bank_transaction_id: int) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM bookkeeping_records WHERE bank_transaction_id = ? LIMIT 1",
                (bank_transaction_id,),
            ).fetchone()
            return self._bookkeeping_record_with_line_items(connection, row) if row else None

    def list_bookkeeping_records(
        self,
        status: Optional[Any] = None,
        export_status: Optional[Any] = None,
        reconciliation_status: Optional[Any] = None,
        target_system: Optional[str] = None,
        source_type: Optional[str] = None,
        limit: int = 100,
    ) -> list:
        limit = self._bounded_limit(limit)
        query = "SELECT * FROM bookkeeping_records"
        params = []
        where = []
        self._append_status_filter(where, params, "status", status)
        self._append_status_filter(where, params, "export_status", export_status)
        self._append_status_filter(where, params, "reconciliation_status", reconciliation_status)
        if target_system:
            where.append("target_system = ?")
            params.append(target_system)
        if source_type:
            where.append("source_type = ?")
            params.append(source_type)
        if where:
            query = f"{query} WHERE {' AND '.join(where)}"
        query = f"{query} ORDER BY updated_at DESC, id DESC LIMIT ?"
        params.append(limit)
        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()
            return [self._bookkeeping_record_with_line_items(connection, row) for row in rows]

    def replace_bookkeeping_record_line_items(
        self,
        bookkeeping_record_id: int,
        line_items: Sequence[Dict[str, Any]],
    ) -> int:
        now = self._now()
        with self._connection() as connection:
            connection.execute(
                "DELETE FROM bookkeeping_record_line_items WHERE bookkeeping_record_id = ?",
                (bookkeeping_record_id,),
            )
            inserted = 0
            for index, item in enumerate(line_items or []):
                values = self._bookkeeping_line_item_values(
                    item,
                    bookkeeping_record_id=bookkeeping_record_id,
                    line_index=index,
                    now=now,
                )
                self._insert_with_connection(connection, "bookkeeping_record_line_items", values)
                inserted += 1
            return inserted

    def list_bookkeeping_record_line_items(
        self,
        bookkeeping_record_id: Optional[int] = None,
        limit: int = 100,
    ) -> list:
        limit = self._bounded_limit(limit)
        query = "SELECT * FROM bookkeeping_record_line_items"
        params = []
        if bookkeeping_record_id is not None:
            query = f"{query} WHERE bookkeeping_record_id = ?"
            params.append(bookkeeping_record_id)
        query = f"{query} ORDER BY bookkeeping_record_id DESC, line_index ASC, id ASC LIMIT ?"
        params.append(limit)
        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def list_vendor_summaries(self, limit: int = 100) -> list:
        limit = self._bounded_limit(limit)
        records = self.list_bookkeeping_records(limit=500)
        documents = self.list_documents(limit=500)
        rules = self.list_vendor_category_rules(limit=500)
        summaries: Dict[str, Dict[str, Any]] = {}

        for record in records:
            vendor_name = _directory_label(record.get("vendor_name"), "Unknown vendor")
            summary = _vendor_summary(summaries, vendor_name)
            summary["recordCount"] += 1
            if record.get("document_id"):
                summary["documentIds"].add(int(record["document_id"]))
            if record.get("bank_transaction_id"):
                summary["bankTransactionCount"] += 1
            _increment(summary["categories"], _directory_label(record.get("category"), "Unassigned"))
            _increment(summary["targetSystems"], _directory_label(record.get("target_system"), "unknown"))
            _increment(summary["recordStatuses"], _directory_label(record.get("status"), "unknown"))
            _increment(summary["exportStatuses"], _directory_label(record.get("export_status"), "unknown"))
            _increment(summary["reconciliationStatuses"], _directory_label(record.get("reconciliation_status"), "unknown"))
            currency = str(record.get("currency") or "EUR")
            summary["amountByCurrency"][currency] = round(
                summary["amountByCurrency"].get(currency, 0.0) + (self._float(record.get("amount")) or 0.0),
                2,
            )
            if bool(record.get("review_required")) or str(record.get("status") or "") in {"needs_review", "failed", "duplicate"}:
                summary["reviewRequiredCount"] += 1
            if str(record.get("export_status") or "") in {"ready", "draft_prepared", "awaiting_approval"}:
                summary["exportReadyCount"] += 1
            if str(record.get("status") or "") == "failed":
                summary["failedCount"] += 1
            _latest(summary, record.get("updated_at") or record.get("created_at"))

        for document in documents:
            vendor_name = _directory_label(document.get("vendor_name"), "Unknown vendor")
            summary = _vendor_summary(summaries, vendor_name)
            summary["documentIds"].add(int(document["id"]))
            _increment(summary["documentStatuses"], _directory_label(document.get("processing_status"), "unknown"))
            if str(document.get("processing_status") or "") in {"needs_review", "failed", "duplicate"}:
                summary["reviewRequiredCount"] += 1
            if str(document.get("processing_status") or "") == "failed":
                summary["failedCount"] += 1
            _latest(summary, document.get("updated_at") or document.get("imported_at") or document.get("created_at"))

        for rule in rules:
            vendor_name = _directory_label(rule.get("vendor_name"), "Unknown vendor")
            summary = _vendor_summary(summaries, vendor_name)
            summary["ruleCount"] += 1
            if rule.get("status") == "approved":
                summary["approvedRuleCount"] += 1
            if rule.get("status") == "suggested":
                summary["suggestedRuleCount"] += 1
            _increment(summary["ruleStatuses"], _directory_label(rule.get("status"), "unknown"))
            _increment(summary["categories"], _directory_label(rule.get("category"), "Unassigned"))
            if len(summary["rules"]) < 8:
                summary["rules"].append({
                    "id": rule.get("id"),
                    "category": rule.get("category"),
                    "targetSystem": rule.get("target_system"),
                    "status": rule.get("status"),
                    "usageCount": rule.get("usage_count"),
                })
            _latest(summary, rule.get("updated_at") or rule.get("created_at"))

        return _finalize_directory_summaries(summaries.values(), limit=limit)

    def list_category_summaries(self, limit: int = 100) -> list:
        limit = self._bounded_limit(limit)
        records = self.list_bookkeeping_records(limit=500)
        documents = self.list_documents(limit=500)
        rules = self.list_vendor_category_rules(limit=500)
        summaries: Dict[str, Dict[str, Any]] = {}

        for record in records:
            category = _directory_label(record.get("category"), "Unassigned")
            summary = _category_summary(summaries, category)
            summary["recordCount"] += 1
            if record.get("document_id"):
                summary["documentIds"].add(int(record["document_id"]))
            if record.get("bank_transaction_id"):
                summary["bankTransactionCount"] += 1
            _increment(summary["vendors"], _directory_label(record.get("vendor_name"), "Unknown vendor"))
            _increment(summary["targetSystems"], _directory_label(record.get("target_system"), "unknown"))
            _increment(summary["recordStatuses"], _directory_label(record.get("status"), "unknown"))
            _increment(summary["exportStatuses"], _directory_label(record.get("export_status"), "unknown"))
            _increment(summary["reconciliationStatuses"], _directory_label(record.get("reconciliation_status"), "unknown"))
            currency = str(record.get("currency") or "EUR")
            summary["amountByCurrency"][currency] = round(
                summary["amountByCurrency"].get(currency, 0.0) + (self._float(record.get("amount")) or 0.0),
                2,
            )
            if bool(record.get("review_required")) or str(record.get("status") or "") in {"needs_review", "failed", "duplicate"}:
                summary["reviewRequiredCount"] += 1
            if str(record.get("export_status") or "") in {"ready", "draft_prepared", "awaiting_approval"}:
                summary["exportReadyCount"] += 1
            if str(record.get("status") or "") == "failed":
                summary["failedCount"] += 1
            _latest(summary, record.get("updated_at") or record.get("created_at"))

        for document in documents:
            category = _directory_label(document.get("category"), "Unassigned")
            summary = _category_summary(summaries, category)
            summary["documentIds"].add(int(document["id"]))
            _increment(summary["documentStatuses"], _directory_label(document.get("processing_status"), "unknown"))
            _increment(summary["vendors"], _directory_label(document.get("vendor_name"), "Unknown vendor"))
            if str(document.get("processing_status") or "") in {"needs_review", "failed", "duplicate"}:
                summary["reviewRequiredCount"] += 1
            if str(document.get("processing_status") or "") == "failed":
                summary["failedCount"] += 1
            _latest(summary, document.get("updated_at") or document.get("imported_at") or document.get("created_at"))

        for rule in rules:
            category = _directory_label(rule.get("category"), "Unassigned")
            summary = _category_summary(summaries, category)
            summary["ruleCount"] += 1
            if rule.get("status") == "approved":
                summary["approvedRuleCount"] += 1
            if rule.get("status") == "suggested":
                summary["suggestedRuleCount"] += 1
            _increment(summary["ruleStatuses"], _directory_label(rule.get("status"), "unknown"))
            _increment(summary["vendors"], _directory_label(rule.get("vendor_name"), "Unknown vendor"))
            if len(summary["rules"]) < 8:
                summary["rules"].append({
                    "id": rule.get("id"),
                    "vendorName": rule.get("vendor_name"),
                    "targetSystem": rule.get("target_system"),
                    "status": rule.get("status"),
                    "usageCount": rule.get("usage_count"),
                })
            _latest(summary, rule.get("updated_at") or rule.get("created_at"))

        return _finalize_directory_summaries(summaries.values(), limit=limit)

    def record_wave_report_snapshot(self, payload: Dict[str, Any], preferred_id: Optional[int] = None) -> int:
        operation_id = str(payload.get("operationId") or payload.get("operation_id") or "").strip()
        if not operation_id:
            raise ValueError("operationId is required for a Wave report snapshot")
        report_type = str(payload.get("reportType") or payload.get("report_type") or "unknown").strip() or "unknown"
        now = self._now()
        values = {
            "id": preferred_id,
            "workflow_run_id": payload.get("workflowRunId") or payload.get("workflow_run_id"),
            "operation_id": operation_id,
            "workflow_id": payload.get("workflowId") or payload.get("workflow_id"),
            "report_type": report_type,
            "report_section": payload.get("reportSection") or payload.get("report_section"),
            "action_id": payload.get("actionId") or payload.get("action_id") or "report_table_read",
            "status": payload.get("status", "planned"),
            "safety": payload.get("safety", "read_only"),
            "from_date": self._date_text(payload.get("fromDate") or payload.get("from_date")),
            "to_date": self._date_text(payload.get("toDate") or payload.get("to_date")),
            "as_of_date": self._date_text(payload.get("asOfDate") or payload.get("as_of_date")),
            "basis": payload.get("basis"),
            "account_option": self._first_present(payload.get("accountOption"), payload.get("account_option")),
            "account_name": self._first_present(payload.get("accountName"), payload.get("account_name")),
            "contact_option": self._first_present(payload.get("contactOption"), payload.get("contact_option")),
            "contact_name": self._first_present(payload.get("contactName"), payload.get("contact_name")),
            "cash_mode": self._first_present(payload.get("cashMode"), payload.get("cash_mode")),
            "export_format": self._first_present(payload.get("exportFormat"), payload.get("export_format"), payload.get("format")),
            "row_count": self._optional_int(self._first_present(payload.get("rowCount"), payload.get("row_count"))),
            "total_debits": self._float(self._first_present(payload.get("totalDebits"), payload.get("total_debits"))),
            "total_credits": self._float(self._first_present(payload.get("totalCredits"), payload.get("total_credits"))),
            "total_amount": self._float(self._first_present(payload.get("totalAmount"), payload.get("total_amount"))),
            "external_submission": self._first_present(payload.get("externalSubmission"), payload.get("external_submission")) or "not_executed",
            "metadata_json": self._json(self._redact_sensitive(payload.get("metadata"))),
            "created_at": now,
            "updated_at": now,
        }
        with self._connection() as connection:
            existing = connection.execute(
                """
                SELECT id FROM wave_report_snapshots
                WHERE operation_id = ?
                LIMIT 1
                """,
                (operation_id,),
            ).fetchone()
            if existing:
                snapshot_id = int(existing["id"])
                update_values = dict(values)
                update_values.pop("id", None)
                update_values.pop("created_at", None)
                self._update_with_connection(connection, "wave_report_snapshots", snapshot_id, update_values)
                return snapshot_id
            return self._insert_with_connection(connection, "wave_report_snapshots", values)

    def get_wave_report_snapshot(self, snapshot_id: int) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM wave_report_snapshots WHERE id = ? LIMIT 1",
                (int(snapshot_id),),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def list_wave_report_snapshots(
        self,
        report_type: Optional[str] = None,
        workflow_id: Optional[str] = None,
        status: Optional[Any] = None,
        limit: int = 100,
    ) -> list:
        limit = self._bounded_limit(limit)
        query = "SELECT * FROM wave_report_snapshots"
        params = []
        where = []
        if report_type:
            where.append("report_type = ?")
            params.append(report_type)
        if workflow_id:
            where.append("workflow_id = ?")
            params.append(workflow_id)
        if status:
            if isinstance(status, Sequence) and not isinstance(status, str):
                statuses = [str(item) for item in status if item]
                if statuses:
                    placeholders = ", ".join("?" for _ in statuses)
                    where.append(f"status IN ({placeholders})")
                    params.extend(statuses)
            else:
                where.append("status = ?")
                params.append(status)
        if where:
            query = f"{query} WHERE {' AND '.join(where)}"
        query = f"{query} ORDER BY updated_at DESC, id DESC LIMIT ?"
        params.append(limit)
        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def record_wave_operation_snapshot(self, payload: Dict[str, Any], preferred_id: Optional[int] = None) -> int:
        operation_id = str(payload.get("operationId") or payload.get("operation_id") or "").strip()
        if not operation_id:
            raise ValueError("operationId is required for a Wave operation snapshot")
        now = self._now()
        plan = payload.get("plan") or {}
        capability_plan = payload.get("capability_plan") or payload.get("capabilityPlan") or {}

        with self._connection() as connection:
            existing_snapshot = connection.execute(
                """
                SELECT * FROM wave_operation_snapshots
                WHERE operation_id = ?
                LIMIT 1
                """,
                (operation_id,),
            ).fetchone()
            if existing_snapshot:
                existing_snapshot = self._row_to_dict(existing_snapshot)

        has_payload_key = lambda key: key in payload
        requires_confirmation = self._payload_value(payload, "requiresConfirmation", "requires_confirmation")
        if requires_confirmation is None:
            requires_confirmation = self._payload_value(plan, "requires_confirmation")
        if (
            requires_confirmation is None
            and existing_snapshot is not None
            and not (has_payload_key("requiresConfirmation") or has_payload_key("requires_confirmation"))
        ):
            requires_confirmation = existing_snapshot.get("requires_confirmation")

        requires_credentials = self._payload_value(payload, "requiresCredentials", "requires_credentials")
        if requires_credentials is None:
            requires_credentials = self._payload_value(plan, "requires_credentials")
        if (
            requires_credentials is None
            and existing_snapshot is not None
            and not (has_payload_key("requiresCredentials") or has_payload_key("requires_credentials"))
        ):
            requires_credentials = existing_snapshot.get("requires_credentials")

        required_fields = self._payload_value(
            payload,
            "requiredFields",
            "required_fields",
            "requiredFieldsList",
            default=self._payload_value(plan, "required_fields"),
        )
        if (
            required_fields is None
            and existing_snapshot is not None
            and not (
                has_payload_key("requiredFields")
                or has_payload_key("required_fields")
                or has_payload_key("requiredFieldsList")
            )
        ):
            required_fields = existing_snapshot.get("required_fields")
        missing_fields = self._payload_value(
            payload,
            "missingFields",
            "missing_fields",
            default=self._payload_value(plan, "missing_fields"),
        )
        if (
            missing_fields is None
            and existing_snapshot is not None
            and not (has_payload_key("missingFields") or has_payload_key("missing_fields"))
        ):
            missing_fields = existing_snapshot.get("missing_fields")

        status = self._payload_value(payload, "status")
        if status is None and not has_payload_key("status") and existing_snapshot is not None:
            status = existing_snapshot.get("status")
        safety = self._payload_value(payload, "safety")
        if safety is None and not has_payload_key("safety") and existing_snapshot is not None:
            safety = existing_snapshot.get("safety")
        surface = self._payload_value(payload, "surface")
        if surface is None and not has_payload_key("surface") and existing_snapshot is not None:
            surface = existing_snapshot.get("surface")
        action_id = self._payload_value(payload, "actionId", "action_id")
        if (
            action_id is None
            and not (has_payload_key("actionId") or has_payload_key("action_id"))
            and existing_snapshot is not None
        ):
            action_id = existing_snapshot.get("action_id")
        mode = self._payload_value(payload, "mode")
        if mode is None and not has_payload_key("mode") and existing_snapshot is not None:
            mode = existing_snapshot.get("mode")
        workflow_run_id = self._payload_value(payload, "workflowRunId", "workflow_run_id")
        if (
            workflow_run_id is None
            and not (has_payload_key("workflowRunId") or has_payload_key("workflow_run_id"))
            and existing_snapshot is not None
        ):
            workflow_run_id = existing_snapshot.get("workflow_run_id")
        workflow_id = self._payload_value(payload, "workflowId", "workflow_id")
        if (
            workflow_id is None
            and not (has_payload_key("workflowId") or has_payload_key("workflow_id"))
            and existing_snapshot is not None
        ):
            workflow_id = existing_snapshot.get("workflow_id")
        plan_status = self._payload_value(payload, "planStatus", "plan_status")
        if plan_status is None and not (
            has_payload_key("planStatus") or has_payload_key("plan_status") or has_payload_key("plan")
        ):
            plan_status = existing_snapshot.get("plan_status") if existing_snapshot else None
        if plan_status is None:
            plan_status = self._payload_value(plan, "status")

        external_submission = self._payload_value(payload, "externalSubmission", "external_submission")
        if (
            external_submission is None
            and not (has_payload_key("externalSubmission") or has_payload_key("external_submission"))
            and existing_snapshot is not None
        ):
            external_submission = existing_snapshot.get("external_submission")

        if status is None:
            status = "planned"
        if safety is None:
            safety = "unsupported"
        if external_submission is None:
            external_submission = "not_executed"

        operation_payload = self._payload_value(payload, "payload")
        if (
            operation_payload is None
            and existing_snapshot is not None
            and not (has_payload_key("payload") or has_payload_key("payload_json"))
        ):
            operation_payload = existing_snapshot.get("payload")

        metadata = payload.get("metadata")
        if metadata is None and existing_snapshot is not None and not has_payload_key("metadata"):
            metadata = existing_snapshot.get("metadata")

        values = {
            "id": preferred_id,
            "workflow_run_id": workflow_run_id,
            "operation_id": operation_id,
            "workflow_id": workflow_id,
            "surface": surface,
            "action_id": action_id,
            "mode": mode,
            "safety": safety,
            "status": status,
            "plan_status": plan_status,
            "plan_json": self._json(plan),
            "capability_plan_json": self._json(capability_plan),
            "requires_confirmation": self._bool_int(requires_confirmation) if requires_confirmation is not None else None,
            "requires_credentials": self._bool_int(requires_credentials) if requires_credentials is not None else None,
            "required_fields_json": self._json(required_fields),
            "missing_fields_json": self._json(missing_fields),
            "external_submission": external_submission,
            "payload_json": self._json(operation_payload),
            "metadata_json": self._json(self._redact_sensitive(metadata)),
            "created_at": now,
            "updated_at": now,
        }

        with self._connection() as connection:
            existing = connection.execute(
                """
                SELECT id FROM wave_operation_snapshots
                WHERE operation_id = ?
                LIMIT 1
                """,
                (operation_id,),
            ).fetchone()
            if existing:
                snapshot_id = int(existing["id"])
                update_values = dict(values)
                update_values.pop("id", None)
                update_values.pop("created_at", None)
                self._update_with_connection(connection, "wave_operation_snapshots", snapshot_id, update_values)
                return snapshot_id
            return self._insert_with_connection(connection, "wave_operation_snapshots", values)

    def _ensure_wave_operation_snapshot_schema(self, connection: sqlite3.Connection) -> None:
        index_names = {
            row["name"]: row["unique"]
            for row in connection.execute("PRAGMA index_list(wave_operation_snapshots)").fetchall()
        }
        unique_indexes_to_replace = {
            "idx_local_wave_ops_status",
            "idx_local_wave_ops_surface",
            "idx_local_wave_ops_safety",
            "idx_local_wave_ops_workflow",
        }
        for index_name in unique_indexes_to_replace:
            if index_names.get(index_name) == 1:
                connection.execute(f'DROP INDEX "{index_name}"')
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS wave_operation_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_run_id INTEGER,
                workflow_id TEXT,
                operation_id TEXT NOT NULL,
                surface TEXT,
                action_id TEXT,
                mode TEXT,
                safety TEXT NOT NULL DEFAULT 'unsupported',
                status TEXT NOT NULL DEFAULT 'planned',
                plan_status TEXT,
                plan_json TEXT,
                capability_plan_json TEXT,
                requires_confirmation INTEGER,
                requires_credentials INTEGER,
                required_fields_json TEXT,
                missing_fields_json TEXT,
                external_submission TEXT NOT NULL DEFAULT 'not_executed',
                payload_json TEXT,
                metadata_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(operation_id)
            )
            """
        )
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(wave_operation_snapshots)").fetchall()
        }
        required_columns = {
            "workflow_run_id": "INTEGER",
            "workflow_id": "TEXT",
            "operation_id": "TEXT NOT NULL",
            "surface": "TEXT",
            "action_id": "TEXT",
            "mode": "TEXT",
            "safety": "TEXT NOT NULL DEFAULT 'unsupported'",
            "status": "TEXT NOT NULL DEFAULT 'planned'",
            "plan_status": "TEXT",
            "plan_json": "TEXT",
            "capability_plan_json": "TEXT",
            "requires_confirmation": "INTEGER",
            "requires_credentials": "INTEGER",
            "required_fields_json": "TEXT",
            "missing_fields_json": "TEXT",
            "external_submission": "TEXT NOT NULL DEFAULT 'not_executed'",
            "payload_json": "TEXT",
            "metadata_json": "TEXT",
            "created_at": "TEXT NOT NULL DEFAULT ''",
            "updated_at": "TEXT NOT NULL DEFAULT ''",
        }
        for column, definition in required_columns.items():
            if column not in columns:
                connection.execute(f"ALTER TABLE wave_operation_snapshots ADD COLUMN {column} {definition}")
        connection.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_local_wave_ops_status
                ON wave_operation_snapshots(status);
            CREATE INDEX IF NOT EXISTS idx_local_wave_ops_surface
                ON wave_operation_snapshots(surface);
            CREATE INDEX IF NOT EXISTS idx_local_wave_ops_safety
                ON wave_operation_snapshots(safety);
            CREATE INDEX IF NOT EXISTS idx_local_wave_ops_workflow
                ON wave_operation_snapshots(workflow_id);
            """
        )

    def get_wave_operation_snapshot(self, operation_id: str) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM wave_operation_snapshots WHERE operation_id = ? LIMIT 1",
                (operation_id,),
            ).fetchone()
        if not row:
            return None
        return self._row_to_dict(row)

    def list_wave_operation_snapshots(
        self,
        surface: Optional[str] = None,
        workflow_id: Optional[str] = None,
        action_id: Optional[str] = None,
        safety: Optional[str] = None,
        status: Optional[Any] = None,
        operation_id: Optional[str] = None,
        limit: int = 100,
    ) -> list:
        limit = self._bounded_limit(limit)
        query = "SELECT * FROM wave_operation_snapshots"
        params = []
        where = []
        if surface:
            where.append("surface = ?")
            params.append(surface)
        if workflow_id:
            where.append("workflow_id = ?")
            params.append(workflow_id)
        if action_id:
            where.append("action_id = ?")
            params.append(action_id)
        if safety:
            where.append("safety = ?")
            params.append(safety)
        if status:
            if isinstance(status, Sequence) and not isinstance(status, str):
                statuses = [str(item) for item in status if item]
                if statuses:
                    placeholders = ", ".join("?" for _ in statuses)
                    where.append(f"status IN ({placeholders})")
                    params.extend(statuses)
            else:
                where.append("status = ?")
                params.append(status)
        if operation_id:
            where.append("operation_id = ?")
            params.append(operation_id)
        if where:
            query = f"{query} WHERE {' AND '.join(where)}"
        query = f"{query} ORDER BY updated_at DESC, id DESC LIMIT ?"
        params.append(limit)
        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def record_audit_event(self, payload: Dict[str, Any], preferred_id: Optional[int] = None) -> int:
        return self._insert(
            "audit_events",
            {
                "id": preferred_id,
                "actor_user_id": payload.get("actorUserId"),
                "action": payload.get("action", "workflow.event"),
                "entity_type": payload.get("entityType", "unknown"),
                "entity_id": payload.get("entityId"),
                "details_json": self._json(payload.get("details")),
                "created_at": self._now(),
            },
        )

    def dashboard_metrics(self) -> Dict[str, int]:
        with self._connection() as connection:
            return {
                "documents": self._count(connection, "bookkeeping_documents"),
                "pending_review": self._count(
                    connection,
                    "review_items",
                    "status IN ('pending', 'in_review')",
                ),
                "duplicates": self._count(
                    connection,
                    "bookkeeping_documents",
                    "duplicate_of_document_id IS NOT NULL",
                ),
                "duplicate_candidates": self._count(connection, "duplicate_candidates"),
                "open_duplicate_candidates": self._count(
                    connection,
                    "duplicate_candidates",
                    "status IN ('pending', 'in_review')",
                ),
                "document_groups": self._count(connection, "document_groups"),
                "open_document_groups": self._count(
                    connection,
                    "document_groups",
                    "status IN ('candidate', 'needs_review', 'in_review')",
                ),
                "suggested_vendor_rules": self._count(
                    connection,
                    "vendor_category_rules",
                    "status = 'suggested'",
                ),
                "unreconciled_documents": self._count(
                    connection,
                    "bookkeeping_documents",
                    "processing_status IN ('processed', 'reviewed', 'validated', 'ready_to_route', 'export_draft_prepared', 'routed') "
                    "AND reconciliation_status NOT IN ('approved', 'reconciled')",
                ),
                "failed_documents": self._count(
                    connection,
                    "bookkeeping_documents",
                    "processing_status = 'failed'",
                ),
                "bank_statement_imports": self._count(connection, "bank_statement_imports"),
                "bank_transactions": self._count(connection, "bank_transactions"),
                "unreconciled_bank_transactions": self._count(
                    connection,
                    "bank_transactions",
                    "reconciliation_status NOT IN ('approved', 'reconciled', 'ignored')",
                ),
                "bookkeeping_records": self._count(connection, "bookkeeping_records"),
                "bookkeeping_record_line_items": self._count(connection, "bookkeeping_record_line_items"),
                "bookkeeping_records_needing_review": self._count(
                    connection,
                    "bookkeeping_records",
                    "review_required = 1 OR status IN ('needs_review', 'failed', 'duplicate')",
                ),
                "export_ready_records": self._count(
                    connection,
                    "bookkeeping_records",
                    "status IN ('ready_to_route', 'reviewed', 'validated') "
                    "AND export_status IN ('not_started', 'ready') "
                    "AND review_required = 0",
                ),
                "export_attempts": self._count(connection, "export_attempts"),
                "export_attempts_needing_approval": self._count(
                    connection,
                    "export_attempts",
                    "approval_required = 1 AND status IN ('approval_required', 'prepared')",
                ),
                "approved_export_attempts": self._count(
                    connection,
                    "export_attempts",
                    "status = 'approved' AND external_submission = 'approved_not_executed'",
                ),
                "supervised_export_attempts": self._count(
                    connection,
                    "export_attempts",
                    "status = 'supervision_required' AND external_submission = 'not_executed'",
                ),
                "executed_export_attempts": self._count(
                    connection,
                    "export_attempts",
                    "external_submission IN ('executed', 'submitted')",
                ),
                "wave_report_snapshots": self._count(connection, "wave_report_snapshots"),
                "wave_operation_snapshots": self._count(connection, "wave_operation_snapshots"),
                "audit_events": self._count(connection, "audit_events"),
            }

    def list_workflow_runs(self, status: Optional[Any] = None, limit: int = 100) -> list:
        limit = self._bounded_limit(limit)
        query = "SELECT * FROM workflow_runs"
        params = []
        if status:
            if isinstance(status, Sequence) and not isinstance(status, str):
                statuses = [str(item) for item in status if item]
                if statuses:
                    placeholders = ", ".join("?" for _ in statuses)
                    query = f"{query} WHERE status IN ({placeholders})"
                    params.extend(statuses)
            else:
                query = f"{query} WHERE status = ?"
                params.append(status)
        query = f"{query} ORDER BY updated_at DESC, id DESC LIMIT ?"
        params.append(limit)
        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def list_source_accounts(
        self,
        source_type: Optional[str] = None,
        status: Optional[Any] = None,
        limit: int = 100,
    ) -> list:
        limit = self._bounded_limit(limit)
        query = "SELECT * FROM source_accounts"
        params = []
        where = []
        if source_type:
            where.append("source_type = ?")
            params.append(source_type)
        if status:
            if isinstance(status, Sequence) and not isinstance(status, str):
                statuses = [str(item) for item in status if item]
                if statuses:
                    placeholders = ", ".join("?" for _ in statuses)
                    where.append(f"status IN ({placeholders})")
                    params.extend(statuses)
            else:
                where.append("status = ?")
                params.append(status)
        if where:
            query = f"{query} WHERE {' AND '.join(where)}"
        query = f"{query} ORDER BY updated_at DESC, id DESC LIMIT ?"
        params.append(limit)
        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def list_documents(self, status: Optional[Any] = None, limit: int = 100) -> list:
        limit = self._bounded_limit(limit)
        query = "SELECT * FROM bookkeeping_documents"
        params = []
        if status:
            if isinstance(status, Sequence) and not isinstance(status, str):
                statuses = [str(item) for item in status if item]
                if statuses:
                    placeholders = ", ".join("?" for _ in statuses)
                    query = f"{query} WHERE processing_status IN ({placeholders})"
                    params.extend(statuses)
            else:
                query = f"{query} WHERE processing_status = ?"
                params.append(status)
        query = f"{query} ORDER BY updated_at DESC, id DESC LIMIT ?"
        params.append(limit)
        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def get_document_by_source(self, source: str, source_document_id: str) -> Optional[Dict[str, Any]]:
        if not source_document_id:
            return None
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT * FROM bookkeeping_documents
                WHERE source = ? AND source_document_id = ?
                LIMIT 1
                """,
                (source, source_document_id),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def find_document_by_fingerprint(
        self,
        duplicate_fingerprint: str,
        exclude_source_document_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if not duplicate_fingerprint:
            return None
        query = """
            SELECT * FROM bookkeeping_documents
            WHERE duplicate_fingerprint = ?
        """
        params = [duplicate_fingerprint]
        if exclude_source_document_id:
            query = f"{query} AND COALESCE(source_document_id, '') != ?"
            params.append(exclude_source_document_id)
        query = f"{query} ORDER BY id ASC LIMIT 1"
        with self._connection() as connection:
            row = connection.execute(query, params).fetchone()
        return self._row_to_dict(row) if row else None

    def get_document(self, document_id: int) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            document = connection.execute(
                "SELECT * FROM bookkeeping_documents WHERE id = ? LIMIT 1",
                (document_id,),
            ).fetchone()
            if not document:
                return None
            result = self._row_to_dict(document)
            result["review_items"] = [
                self._row_to_dict(row)
                for row in connection.execute(
                    "SELECT * FROM review_items WHERE document_id = ? ORDER BY created_at DESC",
                    (document_id,),
                ).fetchall()
            ]
            result["duplicate_candidates"] = [
                self._row_to_dict(row)
                for row in connection.execute(
                    """
                    SELECT * FROM duplicate_candidates
                    WHERE document_id = ? OR candidate_document_id = ?
                    ORDER BY updated_at DESC, id DESC
                    """,
                    (document_id, document_id),
                ).fetchall()
            ]
            result["document_groups"] = [
                self._document_group_with_members(connection, row)
                for row in connection.execute(
                    """
                    SELECT DISTINCT g.* FROM document_groups g
                    JOIN document_group_members m ON m.group_id = g.id
                    WHERE m.document_id = ?
                    ORDER BY g.updated_at DESC, g.id DESC
                    """,
                    (document_id,),
                ).fetchall()
            ]
            result["extracted_fields"] = [
                self._row_to_dict(row)
                for row in connection.execute(
                    "SELECT * FROM extracted_fields WHERE document_id = ? ORDER BY id ASC",
                    (document_id,),
                ).fetchall()
            ]
            result["routing_attempts"] = [
                self._row_to_dict(row)
                for row in connection.execute(
                    "SELECT * FROM routing_attempts WHERE document_id = ? ORDER BY created_at DESC",
                    (document_id,),
                ).fetchall()
            ]
            result["export_attempts"] = [
                self._row_to_dict(row)
                for row in connection.execute(
                    "SELECT * FROM export_attempts WHERE document_id = ? ORDER BY updated_at DESC, id DESC",
                    (document_id,),
                ).fetchall()
            ]
            result["reconciliation_matches"] = [
                self._row_to_dict(row)
                for row in connection.execute(
                    "SELECT * FROM reconciliation_matches WHERE document_id = ? ORDER BY created_at DESC",
                    (document_id,),
                ).fetchall()
            ]
            record = connection.execute(
                "SELECT * FROM bookkeeping_records WHERE document_id = ? LIMIT 1",
                (document_id,),
            ).fetchone()
            result["bookkeeping_record"] = (
                self._bookkeeping_record_with_line_items(connection, record)
                if record else None
            )
            result["review_corrections"] = [
                self._row_to_dict(row)
                for row in connection.execute(
                    "SELECT * FROM review_corrections WHERE document_id = ? ORDER BY created_at DESC",
                    (document_id,),
                ).fetchall()
            ]
            result["audit_events"] = [
                self._row_to_dict(row)
                for row in connection.execute(
                    """
                    SELECT * FROM audit_events
                    WHERE entity_type = 'bookkeeping_document' AND entity_id = ?
                    ORDER BY created_at DESC
                    """,
                    (str(document_id),),
                ).fetchall()
            ]
            return result

    def list_review_items(
        self,
        status: Optional[Any] = None,
        limit: int = 100,
        document_id: Optional[int] = None,
    ) -> list:
        limit = self._bounded_limit(limit)
        query = "SELECT * FROM review_items"
        params = []
        where = []
        if status:
            if isinstance(status, Sequence) and not isinstance(status, str):
                statuses = [str(item) for item in status if item]
                if statuses:
                    placeholders = ", ".join("?" for _ in statuses)
                    where.append(f"status IN ({placeholders})")
                    params.extend(statuses)
            else:
                where.append("status = ?")
                params.append(status)
        if document_id is not None:
            where.append("document_id = ?")
            params.append(document_id)
        if where:
            query = f"{query} WHERE {' AND '.join(where)}"
        query = f"{query} ORDER BY created_at DESC, id DESC LIMIT ?"
        params.append(limit)
        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def get_review_item(self, review_item_id: int) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM review_items WHERE id = ? LIMIT 1",
                (review_item_id,),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def resolve_review_item(
        self,
        review_item_id: int,
        status: str = "resolved",
        resolution: Optional[str] = None,
        corrected_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        review_data = dict(corrected_data or {})
        if resolution:
            review_data["resolution"] = resolution
        self._update(
            "review_items",
            review_item_id,
            {
                "status": status,
                "corrected_data_json": self._json(review_data) if review_data else None,
                "updated_at": self._now(),
            },
        )

    def record_review_correction(self, payload: Dict[str, Any], preferred_id: Optional[int] = None) -> int:
        return self._insert(
            "review_corrections",
            {
                "id": preferred_id,
                "review_item_id": payload.get("reviewItemId"),
                "document_id": payload.get("documentId"),
                "original_data_json": self._json(payload.get("originalData")),
                "corrected_data_json": self._json(payload.get("correctedData")),
                "status": payload.get("status", "resolved"),
                "created_at": self._now(),
            },
        )

    def list_review_corrections(
        self,
        document_id: Optional[int] = None,
        limit: int = 100,
    ) -> list:
        limit = self._bounded_limit(limit)
        query = "SELECT * FROM review_corrections"
        params = []
        if document_id is not None:
            query = f"{query} WHERE document_id = ?"
            params.append(document_id)
        query = f"{query} ORDER BY created_at DESC, id DESC LIMIT ?"
        params.append(limit)
        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def list_routing_attempts(
        self,
        status: Optional[Any] = None,
        target: Optional[str] = None,
        document_id: Optional[int] = None,
        bookkeeping_record_id: Optional[int] = None,
        limit: int = 100,
    ) -> list:
        limit = self._bounded_limit(limit)
        query = "SELECT * FROM routing_attempts"
        params = []
        where = []
        if status:
            if isinstance(status, Sequence) and not isinstance(status, str):
                statuses = [str(item) for item in status if item]
                if statuses:
                    placeholders = ", ".join("?" for _ in statuses)
                    where.append(f"status IN ({placeholders})")
                    params.extend(statuses)
            else:
                where.append("status = ?")
                params.append(status)
        if target:
            where.append("target = ?")
            params.append(target)
        if document_id is not None:
            where.append("document_id = ?")
            params.append(document_id)
        if bookkeeping_record_id is not None:
            where.append("(bookkeeping_record_id = ? OR metadata_json LIKE ? OR metadata_json LIKE ?)")
            params.extend([
                int(bookkeeping_record_id),
                f'%"bookkeepingRecordId": {int(bookkeeping_record_id)}%',
                f'%"bookkeeping_record_id": {int(bookkeeping_record_id)}%',
            ])
        if where:
            query = f"{query} WHERE {' AND '.join(where)}"
        query = f"{query} ORDER BY created_at DESC, id DESC LIMIT ?"
        params.append(limit)
        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def get_reconciliation_match(self, reconciliation_match_id: int) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM reconciliation_matches WHERE id = ? LIMIT 1",
                (reconciliation_match_id,),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def list_reconciliation_matches(
        self,
        status: Optional[Any] = None,
        document_id: Optional[int] = None,
        bank_transaction_id: Optional[str] = None,
        limit: int = 100,
    ) -> list:
        limit = self._bounded_limit(limit)
        query = "SELECT * FROM reconciliation_matches"
        params = []
        where = []
        if status:
            if isinstance(status, Sequence) and not isinstance(status, str):
                statuses = [str(item) for item in status if item]
                if statuses:
                    placeholders = ", ".join("?" for _ in statuses)
                    where.append(f"status IN ({placeholders})")
                    params.extend(statuses)
            else:
                where.append("status = ?")
                params.append(status)
        if document_id is not None:
            where.append("document_id = ?")
            params.append(document_id)
        if bank_transaction_id:
            where.append("bank_transaction_id = ?")
            params.append(bank_transaction_id)
        if where:
            query = f"{query} WHERE {' AND '.join(where)}"
        query = f"{query} ORDER BY created_at DESC, id DESC LIMIT ?"
        params.append(limit)
        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def create_bank_statement_import(self, payload: Dict[str, Any], preferred_id: Optional[int] = None) -> int:
        now = self._now()
        return self._insert(
            "bank_statement_imports",
            {
                "id": preferred_id,
                "source": payload.get("source", "manual_import"),
                "account_identifier": payload.get("accountIdentifier") or payload.get("account_identifier") or "default",
                "filename": payload.get("filename"),
                "format": payload.get("format", "json"),
                "status": payload.get("status", "running"),
                "rows_seen": self._int(payload.get("rowsSeen") or payload.get("rows_seen"), 0),
                "rows_imported": self._int(payload.get("rowsImported") or payload.get("rows_imported"), 0),
                "duplicates": self._int(payload.get("duplicates"), 0),
                "metadata_json": self._json(self._redact_sensitive(payload.get("metadata"))),
                "created_at": now,
                "updated_at": now,
            },
        )

    def update_bank_statement_import(self, import_id: int, payload: Dict[str, Any]) -> None:
        self._update(
            "bank_statement_imports",
            import_id,
            {
                "source": payload.get("source"),
                "account_identifier": payload.get("accountIdentifier") or payload.get("account_identifier"),
                "filename": payload.get("filename"),
                "format": payload.get("format"),
                "status": payload.get("status"),
                "rows_seen": self._optional_int(self._first_present(payload.get("rowsSeen"), payload.get("rows_seen"))),
                "rows_imported": self._optional_int(self._first_present(payload.get("rowsImported"), payload.get("rows_imported"))),
                "duplicates": self._optional_int(payload.get("duplicates")),
                "metadata_json": self._json(self._redact_sensitive(payload.get("metadata"))),
                "updated_at": self._now(),
            },
        )

    def list_bank_statement_imports(
        self,
        account_identifier: Optional[str] = None,
        status: Optional[Any] = None,
        limit: int = 100,
    ) -> list:
        limit = self._bounded_limit(limit)
        query = "SELECT * FROM bank_statement_imports"
        params = []
        where = []
        if account_identifier:
            where.append("account_identifier = ?")
            params.append(account_identifier)
        if status:
            if isinstance(status, Sequence) and not isinstance(status, str):
                statuses = [str(item) for item in status if item]
                if statuses:
                    placeholders = ", ".join("?" for _ in statuses)
                    where.append(f"status IN ({placeholders})")
                    params.extend(statuses)
            else:
                where.append("status = ?")
                params.append(status)
        if where:
            query = f"{query} WHERE {' AND '.join(where)}"
        query = f"{query} ORDER BY updated_at DESC, id DESC LIMIT ?"
        params.append(limit)
        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def upsert_bank_transaction(self, payload: Dict[str, Any], preferred_id: Optional[int] = None) -> int:
        account_identifier = str(
            payload.get("accountIdentifier") or payload.get("account_identifier") or "default"
        ).strip() or "default"
        transaction_id = str(payload.get("transactionId") or payload.get("transaction_id") or "").strip()
        if not transaction_id:
            raise ValueError("transactionId is required for a bank transaction")
        now = self._now()
        values = {
            "id": preferred_id,
            "import_id": payload.get("importId") or payload.get("import_id"),
            "account_identifier": account_identifier,
            "transaction_id": transaction_id,
            "transaction_date": self._date_text(
                self._first_present(
                    payload.get("transactionDate"),
                    payload.get("transaction_date"),
                    payload.get("date"),
                )
            ),
            "amount": self._float(self._first_present(payload.get("amount"), payload.get("transactionAmount"))),
            "currency": payload.get("currency") or "EUR",
            "description": payload.get("description"),
            "counterparty": payload.get("counterparty"),
            "status": payload.get("status", "imported"),
            "reconciliation_status": payload.get("reconciliationStatus") or payload.get("reconciliation_status") or "not_started",
            "duplicate_fingerprint": payload.get("duplicateFingerprint") or payload.get("duplicate_fingerprint"),
            "source": payload.get("source", "manual_import"),
            "metadata_json": self._json(self._redact_sensitive(payload.get("metadata"))),
            "created_at": now,
            "updated_at": now,
        }
        with self._connection() as connection:
            existing = connection.execute(
                """
                SELECT id FROM bank_transactions
                WHERE account_identifier = ? AND transaction_id = ?
                LIMIT 1
                """,
                (account_identifier, transaction_id),
            ).fetchone()
            if existing:
                transaction_record_id = int(existing["id"])
                update_values = dict(values)
                update_values.pop("id", None)
                update_values.pop("created_at", None)
                self._update_with_connection(connection, "bank_transactions", transaction_record_id, update_values)
                return transaction_record_id
            return self._insert_with_connection(connection, "bank_transactions", values)

    def update_bank_transaction(self, bank_transaction_id: int, payload: Dict[str, Any]) -> None:
        self._update(
            "bank_transactions",
            bank_transaction_id,
            {
                "import_id": payload.get("importId") or payload.get("import_id"),
                "account_identifier": payload.get("accountIdentifier") or payload.get("account_identifier"),
                "transaction_id": payload.get("transactionId") or payload.get("transaction_id"),
                "transaction_date": self._date_text(
                    self._first_present(
                        payload.get("transactionDate"),
                        payload.get("transaction_date"),
                        payload.get("date"),
                    )
                ),
                "amount": self._float(self._first_present(payload.get("amount"), payload.get("transactionAmount"))),
                "currency": payload.get("currency"),
                "description": payload.get("description"),
                "counterparty": payload.get("counterparty"),
                "status": payload.get("status"),
                "reconciliation_status": payload.get("reconciliationStatus") or payload.get("reconciliation_status"),
                "duplicate_fingerprint": payload.get("duplicateFingerprint") or payload.get("duplicate_fingerprint"),
                "source": payload.get("source"),
                "metadata_json": self._json(self._redact_sensitive(payload.get("metadata"))),
                "updated_at": self._now(),
            },
        )

    def get_bank_transaction(self, bank_transaction_id: int) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM bank_transactions WHERE id = ? LIMIT 1",
                (bank_transaction_id,),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def get_bank_transaction_by_identity(
        self,
        account_identifier: str,
        transaction_id: str,
    ) -> Optional[Dict[str, Any]]:
        if not transaction_id:
            return None
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT * FROM bank_transactions
                WHERE account_identifier = ? AND transaction_id = ?
                LIMIT 1
                """,
                (account_identifier or "default", transaction_id),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def list_bank_transactions(
        self,
        account_identifier: Optional[str] = None,
        status: Optional[Any] = None,
        reconciliation_status: Optional[Any] = None,
        limit: int = 100,
    ) -> list:
        limit = self._bounded_limit(limit)
        query = "SELECT * FROM bank_transactions"
        params = []
        where = []
        if account_identifier:
            where.append("account_identifier = ?")
            params.append(account_identifier)
        if status:
            if isinstance(status, Sequence) and not isinstance(status, str):
                statuses = [str(item) for item in status if item]
                if statuses:
                    placeholders = ", ".join("?" for _ in statuses)
                    where.append(f"status IN ({placeholders})")
                    params.extend(statuses)
            else:
                where.append("status = ?")
                params.append(status)
        if reconciliation_status:
            if isinstance(reconciliation_status, Sequence) and not isinstance(reconciliation_status, str):
                statuses = [str(item) for item in reconciliation_status if item]
                if statuses:
                    placeholders = ", ".join("?" for _ in statuses)
                    where.append(f"reconciliation_status IN ({placeholders})")
                    params.extend(statuses)
            else:
                where.append("reconciliation_status = ?")
                params.append(reconciliation_status)
        if where:
            query = f"{query} WHERE {' AND '.join(where)}"
        query = f"{query} ORDER BY transaction_date DESC, updated_at DESC, id DESC LIMIT ?"
        params.append(limit)
        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def upsert_vendor_category_rule(self, payload: Dict[str, Any]) -> int:
        vendor_name = str(payload.get("vendorName") or payload.get("vendor_name") or "").strip()
        category = str(payload.get("category") or "").strip()
        target_system = str(payload.get("targetSystem") or payload.get("target_system") or "none").strip() or "none"
        if not vendor_name or not category:
            raise ValueError("vendorName and category are required for a vendor category rule")
        normalized_vendor_name = self._normalize_text(vendor_name)
        now = self._now()
        confidence_score = self._float(payload.get("confidenceScore"))
        metadata = payload.get("metadata")
        source_document_id = payload.get("sourceDocumentId")
        status = str(payload.get("status", "learned") or "learned").strip()
        if status not in VENDOR_CATEGORY_RULE_STATUSES:
            raise ValueError(f"Unsupported vendor category rule status: {status}")

        with self._connection() as connection:
            existing = connection.execute(
                """
                SELECT * FROM vendor_category_rules
                WHERE normalized_vendor_name = ? AND category = ? AND target_system = ?
                LIMIT 1
                """,
                (normalized_vendor_name, category, target_system),
            ).fetchone()
            if existing:
                rule_id = int(existing["id"])
                existing_status = str(existing["status"] or "")
                effective_status = status
                if existing_status in GOVERNED_VENDOR_CATEGORY_RULE_STATUSES and status == "suggested":
                    effective_status = existing_status
                self._update_with_connection(
                    connection,
                    "vendor_category_rules",
                    rule_id,
                    {
                        "vendor_name": vendor_name,
                        "confidence_score": confidence_score,
                        "status": effective_status,
                        "source_document_id": source_document_id,
                        "usage_count": int(existing["usage_count"] or 0) + 1,
                        "metadata_json": self._json(metadata),
                        "updated_at": now,
                    },
                )
                return rule_id
            return self._insert_with_connection(
                connection,
                "vendor_category_rules",
                {
                    "normalized_vendor_name": normalized_vendor_name,
                    "vendor_name": vendor_name,
                    "category": category,
                    "target_system": target_system,
                    "confidence_score": confidence_score,
                    "status": status,
                    "source_document_id": source_document_id,
                    "usage_count": 1,
                    "metadata_json": self._json(metadata),
                    "created_at": now,
                    "updated_at": now,
                },
            )

    def get_vendor_category_rule(self, rule_id: int) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM vendor_category_rules WHERE id = ? LIMIT 1",
                (rule_id,),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def update_vendor_category_rule_status(
        self,
        rule_id: int,
        status: str,
        resolution: Optional[str] = None,
        actor: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        status = str(status or "").strip()
        if status not in VENDOR_CATEGORY_RULE_STATUSES:
            raise ValueError(f"Unsupported vendor category rule status: {status}")
        now = self._now()
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM vendor_category_rules WHERE id = ? LIMIT 1",
                (rule_id,),
            ).fetchone()
            if not row:
                return None
            rule = self._row_to_dict(row)
            metadata = rule.get("metadata") or {}
            history = list(metadata.get("statusHistory") or [])
            history.append({
                "from": rule.get("status"),
                "to": status,
                "resolution": resolution,
                "actor": actor,
                "changedAt": now,
            })
            metadata["statusHistory"] = history
            if resolution:
                metadata["lastResolution"] = resolution
            if actor:
                metadata["lastActor"] = actor
            self._update_with_connection(
                connection,
                "vendor_category_rules",
                rule_id,
                {
                    "status": status,
                    "metadata_json": self._json(metadata),
                    "updated_at": now,
                },
            )
            updated = connection.execute(
                "SELECT * FROM vendor_category_rules WHERE id = ? LIMIT 1",
                (rule_id,),
            ).fetchone()
        return self._row_to_dict(updated) if updated else None

    def list_vendor_category_rules(
        self,
        vendor_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> list:
        limit = self._bounded_limit(limit)
        query = "SELECT * FROM vendor_category_rules"
        params = []
        where = []
        if vendor_name:
            where.append("normalized_vendor_name = ?")
            params.append(self._normalize_text(vendor_name))
        if status:
            where.append("status = ?")
            params.append(status)
        if where:
            query = f"{query} WHERE {' AND '.join(where)}"
        query = f"{query} ORDER BY updated_at DESC, id DESC LIMIT ?"
        params.append(limit)
        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def list_audit_events(self, limit: int = 100) -> list:
        limit = self._bounded_limit(limit)
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM audit_events ORDER BY created_at DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def _insert(self, table: str, values: Dict[str, Any]) -> int:
        with self._connection() as connection:
            return self._insert_with_connection(connection, table, values)

    @staticmethod
    def _insert_with_connection(connection: sqlite3.Connection, table: str, values: Dict[str, Any]) -> int:
        values = {key: value for key, value in values.items() if value is not None}
        columns = ", ".join(values.keys())
        placeholders = ", ".join("?" for _ in values)
        cursor = connection.execute(
            f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
            tuple(values.values()),
        )
        return int(values.get("id") or cursor.lastrowid)

    def _update(self, table: str, record_id: int, values: Dict[str, Any]) -> None:
        with self._connection() as connection:
            self._update_with_connection(connection, table, record_id, values)

    @staticmethod
    def _update_with_connection(
        connection: sqlite3.Connection,
        table: str,
        record_id: int,
        values: Dict[str, Any],
    ) -> None:
        values = {key: value for key, value in values.items() if value is not None}
        if not values:
            return
        assignments = ", ".join(f"{key} = ?" for key in values)
        connection.execute(
            f"UPDATE {table} SET {assignments} WHERE id = ?",
            (*values.values(), record_id),
        )

    @staticmethod
    def _existing_document_id(
        connection: sqlite3.Connection,
        source: str,
        source_document_id: Optional[str],
    ) -> Optional[int]:
        if not source_document_id:
            return None
        row = connection.execute(
            """
            SELECT id FROM bookkeeping_documents
            WHERE source = ? AND source_document_id = ?
            LIMIT 1
            """,
            (source, source_document_id),
        ).fetchone()
        return int(row["id"]) if row else None

    @staticmethod
    def _existing_bookkeeping_record_id(
        connection: sqlite3.Connection,
        document_id: Optional[int],
        bank_transaction_id: Optional[int],
    ) -> Optional[int]:
        if document_id is not None:
            row = connection.execute(
                "SELECT id FROM bookkeeping_records WHERE document_id = ? LIMIT 1",
                (document_id,),
            ).fetchone()
            if row:
                return int(row["id"])
        if bank_transaction_id is not None:
            row = connection.execute(
                "SELECT id FROM bookkeeping_records WHERE bank_transaction_id = ? LIMIT 1",
                (bank_transaction_id,),
            ).fetchone()
            if row:
                return int(row["id"])
        return None

    @staticmethod
    def _existing_export_attempt_id(
        connection: sqlite3.Connection,
        routing_attempt_id: Optional[int],
        operation_id: Optional[str],
    ) -> Optional[int]:
        if routing_attempt_id is not None:
            row = connection.execute(
                "SELECT id FROM export_attempts WHERE routing_attempt_id = ? LIMIT 1",
                (routing_attempt_id,),
            ).fetchone()
            if row:
                return int(row["id"])
        if operation_id:
            row = connection.execute(
                "SELECT id FROM export_attempts WHERE operation_id = ? LIMIT 1",
                (operation_id,),
            ).fetchone()
            if row:
                return int(row["id"])
        return None

    @staticmethod
    def _count(connection: sqlite3.Connection, table: str, where: Optional[str] = None) -> int:
        query = f"SELECT COUNT(*) AS count FROM {table}"
        if where:
            query = f"{query} WHERE {where}"
        row = connection.execute(query).fetchone()
        return int(row["count"] if row else 0)

    @staticmethod
    def _ensure_column(
        connection: sqlite3.Connection,
        table: str,
        column: str,
        definition: str,
    ) -> None:
        columns = {
            row["name"]
            for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in columns:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _ensure_export_attempt_schema(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS export_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bookkeeping_record_id INTEGER,
                document_id INTEGER,
                routing_attempt_id INTEGER,
                workflow_run_id INTEGER,
                target_system TEXT NOT NULL DEFAULT 'waveapps',
                target_account TEXT,
                action_id TEXT,
                surface TEXT,
                operation_id TEXT,
                status TEXT NOT NULL DEFAULT 'approval_required',
                safety TEXT NOT NULL DEFAULT 'requires_confirmation',
                approval_required INTEGER NOT NULL DEFAULT 1,
                approved_at TEXT,
                approved_by TEXT,
                external_submission TEXT NOT NULL DEFAULT 'not_executed',
                submitted_at TEXT,
                external_id TEXT,
                message TEXT,
                payload_json TEXT,
                result_json TEXT,
                metadata_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(export_attempts)").fetchall()
        }
        required_columns = {
            "bookkeeping_record_id": "INTEGER",
            "document_id": "INTEGER",
            "routing_attempt_id": "INTEGER",
            "workflow_run_id": "INTEGER",
            "target_system": "TEXT NOT NULL DEFAULT 'waveapps'",
            "target_account": "TEXT",
            "action_id": "TEXT",
            "surface": "TEXT",
            "operation_id": "TEXT",
            "status": "TEXT NOT NULL DEFAULT 'approval_required'",
            "safety": "TEXT NOT NULL DEFAULT 'requires_confirmation'",
            "approval_required": "INTEGER NOT NULL DEFAULT 1",
            "approved_at": "TEXT",
            "approved_by": "TEXT",
            "external_submission": "TEXT NOT NULL DEFAULT 'not_executed'",
            "submitted_at": "TEXT",
            "external_id": "TEXT",
            "message": "TEXT",
            "payload_json": "TEXT",
            "result_json": "TEXT",
            "metadata_json": "TEXT",
            "created_at": "TEXT NOT NULL DEFAULT ''",
            "updated_at": "TEXT NOT NULL DEFAULT ''",
        }
        for column, definition in required_columns.items():
            if column not in columns:
                connection.execute(f"ALTER TABLE export_attempts ADD COLUMN {column} {definition}")
        connection.executescript(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_local_exports_routing_unique
                ON export_attempts(routing_attempt_id)
                WHERE routing_attempt_id IS NOT NULL;
            CREATE UNIQUE INDEX IF NOT EXISTS idx_local_exports_operation_unique
                ON export_attempts(operation_id)
                WHERE operation_id IS NOT NULL;
            CREATE INDEX IF NOT EXISTS idx_local_exports_status
                ON export_attempts(status);
            CREATE INDEX IF NOT EXISTS idx_local_exports_external
                ON export_attempts(external_submission);
            CREATE INDEX IF NOT EXISTS idx_local_exports_target
                ON export_attempts(target_system);
            CREATE INDEX IF NOT EXISTS idx_local_exports_document
                ON export_attempts(document_id);
            """
        )

    def _ensure_routing_attempt_schema(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS routing_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER,
                bookkeeping_record_id INTEGER,
                workflow_run_id INTEGER,
                target TEXT NOT NULL,
                status TEXT NOT NULL,
                external_id TEXT,
                message TEXT,
                metadata_json TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        self._ensure_column(
            connection,
            "routing_attempts",
            "bookkeeping_record_id",
            "INTEGER",
        )
        connection.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_local_routing_status
                ON routing_attempts(status);
            CREATE INDEX IF NOT EXISTS idx_local_routing_target
                ON routing_attempts(target);
            CREATE INDEX IF NOT EXISTS idx_local_routing_record
                ON routing_attempts(bookkeeping_record_id);
            """
        )

    def _ensure_bookkeeping_record_schema(self, connection: sqlite3.Connection) -> None:
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(bookkeeping_records)").fetchall()
        }
        required_columns = {
            "document_id": "INTEGER",
            "bank_transaction_id": "INTEGER",
            "source_type": "TEXT NOT NULL DEFAULT 'document'",
            "record_type": "TEXT NOT NULL DEFAULT 'expense'",
            "status": "TEXT NOT NULL DEFAULT 'draft'",
            "target_system": "TEXT NOT NULL DEFAULT 'waveapps'",
            "target_account": "TEXT",
            "vendor_name": "TEXT",
            "category": "TEXT",
            "record_date": "TEXT",
            "amount": "REAL",
            "vat_amount": "REAL",
            "currency": "TEXT NOT NULL DEFAULT 'EUR'",
            "description": "TEXT",
            "confidence_score": "REAL",
            "review_required": "INTEGER NOT NULL DEFAULT 0",
            "export_status": "TEXT NOT NULL DEFAULT 'not_started'",
            "reconciliation_status": "TEXT NOT NULL DEFAULT 'not_started'",
            "metadata_json": "TEXT",
            "created_at": "TEXT NOT NULL DEFAULT ''",
            "updated_at": "TEXT NOT NULL DEFAULT ''",
        }
        for column, definition in required_columns.items():
            if column not in columns:
                connection.execute(f"ALTER TABLE bookkeeping_records ADD COLUMN {column} {definition}")
        connection.executescript(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_local_records_document_unique
                ON bookkeeping_records(document_id)
                WHERE document_id IS NOT NULL;
            CREATE UNIQUE INDEX IF NOT EXISTS idx_local_records_bank_unique
                ON bookkeeping_records(bank_transaction_id)
                WHERE bank_transaction_id IS NOT NULL;
            CREATE INDEX IF NOT EXISTS idx_local_records_status
                ON bookkeeping_records(status);
            CREATE INDEX IF NOT EXISTS idx_local_records_target
                ON bookkeeping_records(target_system);
            CREATE INDEX IF NOT EXISTS idx_local_records_export
                ON bookkeeping_records(export_status);
            CREATE INDEX IF NOT EXISTS idx_local_records_reconciliation
                ON bookkeeping_records(reconciliation_status);
            """
        )

    def _ensure_bookkeeping_record_line_item_schema(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS bookkeeping_record_line_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bookkeeping_record_id INTEGER NOT NULL,
                line_index INTEGER NOT NULL DEFAULT 0,
                item_name TEXT,
                description TEXT,
                quantity REAL,
                unit_price REAL,
                amount REAL,
                tax_amount REAL,
                tax_rate REAL,
                tax_code TEXT,
                category TEXT,
                account_name TEXT,
                source TEXT NOT NULL DEFAULT 'extraction',
                confidence_score REAL,
                metadata_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(bookkeeping_record_id, line_index),
                FOREIGN KEY(bookkeeping_record_id) REFERENCES bookkeeping_records(id) ON DELETE CASCADE
            )
            """
        )
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(bookkeeping_record_line_items)").fetchall()
        }
        required_columns = {
            "bookkeeping_record_id": "INTEGER NOT NULL DEFAULT 0",
            "line_index": "INTEGER NOT NULL DEFAULT 0",
            "item_name": "TEXT",
            "description": "TEXT",
            "quantity": "REAL",
            "unit_price": "REAL",
            "amount": "REAL",
            "tax_amount": "REAL",
            "tax_rate": "REAL",
            "tax_code": "TEXT",
            "category": "TEXT",
            "account_name": "TEXT",
            "source": "TEXT NOT NULL DEFAULT 'extraction'",
            "confidence_score": "REAL",
            "metadata_json": "TEXT",
            "created_at": "TEXT NOT NULL DEFAULT ''",
            "updated_at": "TEXT NOT NULL DEFAULT ''",
        }
        for column, definition in required_columns.items():
            if column not in columns:
                connection.execute(f"ALTER TABLE bookkeeping_record_line_items ADD COLUMN {column} {definition}")
        connection.executescript(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_local_record_lines_unique
                ON bookkeeping_record_line_items(bookkeeping_record_id, line_index);
            CREATE INDEX IF NOT EXISTS idx_local_record_lines_record
                ON bookkeeping_record_line_items(bookkeeping_record_id);
            CREATE INDEX IF NOT EXISTS idx_local_record_lines_account
                ON bookkeeping_record_line_items(account_name);
            CREATE INDEX IF NOT EXISTS idx_local_record_lines_tax
                ON bookkeeping_record_line_items(tax_code);
            """
        )

    @classmethod
    def _bookkeeping_record_values(
        cls,
        payload: Dict[str, Any],
        now: str,
        include_defaults: bool,
    ) -> Dict[str, Any]:
        default = (lambda value: value) if include_defaults else (lambda value: None)
        review_required = cls._payload_value(payload, "reviewRequired", "review_required")
        if review_required is None and include_defaults:
            review_required = 0
        return {
            "document_id": cls._optional_int(cls._payload_value(payload, "documentId", "document_id")),
            "bank_transaction_id": cls._optional_int(cls._payload_value(
                payload,
                "bankTransactionId",
                "bank_transaction_id",
            )),
            "source_type": cls._payload_value(payload, "sourceType", "source_type", default=default("document")),
            "record_type": cls._payload_value(payload, "recordType", "record_type", default=default("expense")),
            "status": cls._payload_value(payload, "status", default=default("draft")),
            "target_system": cls._payload_value(payload, "targetSystem", "target_system", default=default("waveapps")),
            "target_account": cls._payload_value(payload, "targetAccount", "target_account"),
            "vendor_name": cls._payload_value(payload, "vendorName", "vendor_name"),
            "category": cls._payload_value(payload, "category"),
            "record_date": cls._date_text(cls._payload_value(payload, "recordDate", "record_date", "transactionDate", "transaction_date")),
            "amount": cls._float(cls._payload_value(payload, "amount", "totalAmount", "total_amount")),
            "vat_amount": cls._float(cls._payload_value(payload, "vatAmount", "vat_amount")),
            "currency": cls._payload_value(payload, "currency", default=default("EUR")),
            "description": cls._payload_value(payload, "description"),
            "confidence_score": cls._float(cls._payload_value(payload, "confidenceScore", "confidence_score")),
            "review_required": cls._bool_int(review_required) if review_required is not None else None,
            "export_status": cls._payload_value(payload, "exportStatus", "export_status", default=default("not_started")),
            "reconciliation_status": cls._payload_value(
                payload,
                "reconciliationStatus",
                "reconciliation_status",
                default=default("not_started"),
            ),
            "metadata_json": cls._json(cls._redact_sensitive(cls._payload_value(payload, "metadata", "metadata_json"))),
        }

    @classmethod
    def _bookkeeping_line_item_values(
        cls,
        payload: Dict[str, Any],
        bookkeeping_record_id: int,
        line_index: int,
        now: str,
    ) -> Dict[str, Any]:
        return {
            "bookkeeping_record_id": bookkeeping_record_id,
            "line_index": cls._optional_int(cls._payload_value(payload, "lineIndex", "line_index")) or line_index,
            "item_name": cls._payload_value(payload, "itemName", "item_name", "name", "item"),
            "description": cls._payload_value(payload, "description"),
            "quantity": cls._float(cls._payload_value(payload, "quantity", "qty")),
            "unit_price": cls._float(cls._payload_value(payload, "unitPrice", "unit_price", "price")),
            "amount": cls._float(cls._payload_value(payload, "amount", "totalAmount", "total_amount")),
            "tax_amount": cls._float(cls._payload_value(
                payload,
                "taxAmount",
                "tax_amount",
                "vatAmount",
                "vat_amount",
            )),
            "tax_rate": cls._float(cls._payload_value(
                payload,
                "taxRate",
                "tax_rate",
                "vatRate",
                "vat_rate",
            )),
            "tax_code": cls._payload_value(payload, "taxCode", "tax_code", "salesTax", "sales_tax", "tax"),
            "category": cls._payload_value(payload, "category"),
            "account_name": cls._payload_value(payload, "accountName", "account_name", "account", "targetAccount"),
            "source": cls._payload_value(payload, "source", default="extraction"),
            "confidence_score": cls._float(cls._payload_value(payload, "confidenceScore", "confidence_score")),
            "metadata_json": cls._json(cls._redact_sensitive(cls._payload_value(payload, "metadata", "metadata_json"))),
            "created_at": now,
            "updated_at": now,
        }

    @classmethod
    def _export_attempt_values(
        cls,
        payload: Dict[str, Any],
        now: str,
        include_defaults: bool,
    ) -> Dict[str, Any]:
        default = (lambda value: value) if include_defaults else (lambda value: None)
        approval_required = cls._payload_value(payload, "approvalRequired", "approval_required")
        if approval_required is None and include_defaults:
            approval_required = 1
        return {
            "bookkeeping_record_id": cls._optional_int(cls._payload_value(
                payload,
                "bookkeepingRecordId",
                "bookkeeping_record_id",
            )),
            "document_id": cls._optional_int(cls._payload_value(payload, "documentId", "document_id")),
            "routing_attempt_id": cls._optional_int(cls._payload_value(
                payload,
                "routingAttemptId",
                "routing_attempt_id",
            )),
            "workflow_run_id": cls._optional_int(cls._payload_value(payload, "workflowRunId", "workflow_run_id")),
            "target_system": cls._payload_value(payload, "targetSystem", "target_system", default=default("waveapps")),
            "target_account": cls._payload_value(payload, "targetAccount", "target_account"),
            "action_id": cls._payload_value(payload, "actionId", "action_id"),
            "surface": cls._payload_value(payload, "surface"),
            "operation_id": cls._payload_value(payload, "operationId", "operation_id"),
            "status": cls._payload_value(payload, "status", default=default("approval_required")),
            "safety": cls._payload_value(payload, "safety", default=default("requires_confirmation")),
            "approval_required": cls._bool_int(approval_required) if approval_required is not None else None,
            "approved_at": cls._date_text(cls._payload_value(payload, "approvedAt", "approved_at")),
            "approved_by": cls._payload_value(payload, "approvedBy", "approved_by"),
            "external_submission": cls._payload_value(
                payload,
                "externalSubmission",
                "external_submission",
                default=default("not_executed"),
            ),
            "submitted_at": cls._date_text(cls._payload_value(payload, "submittedAt", "submitted_at")),
            "external_id": cls._payload_value(payload, "externalId", "external_id"),
            "message": cls._payload_value(payload, "message"),
            "payload_json": cls._json(cls._redact_sensitive(cls._payload_value(payload, "payload", "payload_json"))),
            "result_json": cls._json(cls._redact_sensitive(cls._payload_value(payload, "result", "result_json"))),
            "metadata_json": cls._json(cls._redact_sensitive(cls._payload_value(payload, "metadata", "metadata_json"))),
        }

    @staticmethod
    def _payload_value(payload: Dict[str, Any], *keys: str, default: Any = None) -> Any:
        for key in keys:
            if key in payload:
                return payload.get(key)
        return default

    @staticmethod
    def _append_status_filter(where: list, params: list, column: str, value: Optional[Any]) -> None:
        if not value:
            return
        if isinstance(value, Sequence) and not isinstance(value, str):
            statuses = [str(item) for item in value if item]
            if statuses:
                placeholders = ", ".join("?" for _ in statuses)
                where.append(f"{column} IN ({placeholders})")
                params.extend(statuses)
            return
        where.append(f"{column} = ?")
        params.append(str(value))

    @classmethod
    def _row_to_dict(cls, row: sqlite3.Row) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for key in row.keys():
            value = row[key]
            if key.endswith("_json"):
                result[key[:-5]] = cls._json_load(value)
            else:
                result[key] = value
        return result

    @classmethod
    def _bookkeeping_record_with_line_items(
        cls,
        connection: sqlite3.Connection,
        row: sqlite3.Row,
    ) -> Dict[str, Any]:
        record = cls._row_to_dict(row)
        line_rows = connection.execute(
            """
            SELECT * FROM bookkeeping_record_line_items
            WHERE bookkeeping_record_id = ?
            ORDER BY line_index ASC, id ASC
            """,
            (record["id"],),
        ).fetchall()
        record["line_items"] = [cls._row_to_dict(line_row) for line_row in line_rows]
        record["line_item_count"] = len(record["line_items"])
        return record

    @classmethod
    def _document_group_with_members(
        cls,
        connection: sqlite3.Connection,
        row: sqlite3.Row,
    ) -> Dict[str, Any]:
        group = cls._row_to_dict(row)
        member_rows = connection.execute(
            """
            SELECT
                m.*,
                d.original_filename,
                d.source,
                d.source_document_id,
                d.processing_status,
                d.storage_path
            FROM document_group_members m
            LEFT JOIN bookkeeping_documents d ON d.id = m.document_id
            WHERE m.group_id = ?
            ORDER BY m.status ASC, m.sort_order ASC, m.id ASC
            """,
            (group["id"],),
        ).fetchall()
        members = []
        for member_row in member_rows:
            member = cls._row_to_dict(member_row)
            member["document"] = {
                "id": member.get("document_id"),
                "original_filename": member.pop("original_filename", None),
                "source": member.pop("source", None),
                "source_document_id": member.pop("source_document_id", None),
                "processing_status": member.pop("processing_status", None),
                "storage_path": member.pop("storage_path", None),
            }
            members.append(member)
        group["members"] = members
        group["member_count"] = len([member for member in members if member.get("status") == "active"])
        return group

    @staticmethod
    def _json(value: Any) -> Optional[str]:
        if value is None:
            return None
        return json.dumps(value, sort_keys=True, default=LocalOperationsLedger._json_default)

    @staticmethod
    def _json_load(value: Optional[str]) -> Any:
        if value is None or value == "":
            return None
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value

    @staticmethod
    def _json_default(value: Any) -> str:
        if isinstance(value, bytes):
            return f"<bytes:{len(value)}>"
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return str(value)

    @classmethod
    def _redact_sensitive(cls, value: Any) -> Any:
        secret_markers = ("token", "password", "secret", "credential", "authorization", "api_key", "apikey")
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                key_text = str(key)
                if any(marker in key_text.lower() for marker in secret_markers):
                    result[key] = "<redacted>"
                else:
                    result[key] = cls._redact_sensitive(item)
            return result
        if isinstance(value, list):
            return [cls._redact_sensitive(item) for item in value]
        return value

    @staticmethod
    def _float(value: Any) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _int(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _bool_int(value: Any) -> int:
        if isinstance(value, str):
            return 0 if value.strip().lower() in {"", "0", "false", "no", "off"} else 1
        return 1 if bool(value) else 0

    @staticmethod
    def _optional_int(value: Any) -> Optional[int]:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _first_present(*values: Any) -> Any:
        for value in values:
            if value is not None and value != "":
                return value
        return None

    @classmethod
    def _bounded_limit(cls, value: Any) -> int:
        parsed = cls._int(value, 100)
        return max(1, min(parsed, 500))

    @staticmethod
    def _date_text(value: Any) -> Optional[str]:
        if value is None or value == "":
            return None
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return str(value)

    @staticmethod
    def _normalize_text(value: str) -> str:
        return " ".join(str(value or "").strip().lower().split())

    @classmethod
    def _normalized_field_value(cls, value: Any) -> Optional[str]:
        if value in (None, ""):
            return None
        if isinstance(value, (dict, list)):
            return cls._json(value)
        return str(value)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _directory_label(value: Any, fallback: str) -> str:
    text = str(value or "").strip()
    return text or fallback


def _directory_key(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _increment(container: Dict[str, int], key: str, amount: int = 1) -> None:
    container[key] = container.get(key, 0) + amount


def _latest(summary: Dict[str, Any], timestamp: Any) -> None:
    if timestamp and str(timestamp) > str(summary.get("latestActivityAt") or ""):
        summary["latestActivityAt"] = str(timestamp)


def _vendor_summary(summaries: Dict[str, Dict[str, Any]], vendor_name: str) -> Dict[str, Any]:
    key = _directory_key(vendor_name)
    if key not in summaries:
        summaries[key] = {
            "vendorName": vendor_name,
            "normalizedVendorName": key,
            "recordCount": 0,
            "documentIds": set(),
            "bankTransactionCount": 0,
            "amountByCurrency": {},
            "categories": {},
            "targetSystems": {},
            "recordStatuses": {},
            "documentStatuses": {},
            "exportStatuses": {},
            "reconciliationStatuses": {},
            "reviewRequiredCount": 0,
            "exportReadyCount": 0,
            "failedCount": 0,
            "ruleCount": 0,
            "approvedRuleCount": 0,
            "suggestedRuleCount": 0,
            "ruleStatuses": {},
            "rules": [],
            "latestActivityAt": "",
        }
    return summaries[key]


def _category_summary(summaries: Dict[str, Dict[str, Any]], category: str) -> Dict[str, Any]:
    key = _directory_key(category)
    if key not in summaries:
        summaries[key] = {
            "category": category,
            "normalizedCategory": key,
            "recordCount": 0,
            "documentIds": set(),
            "bankTransactionCount": 0,
            "amountByCurrency": {},
            "vendors": {},
            "targetSystems": {},
            "recordStatuses": {},
            "documentStatuses": {},
            "exportStatuses": {},
            "reconciliationStatuses": {},
            "reviewRequiredCount": 0,
            "exportReadyCount": 0,
            "failedCount": 0,
            "ruleCount": 0,
            "approvedRuleCount": 0,
            "suggestedRuleCount": 0,
            "ruleStatuses": {},
            "rules": [],
            "latestActivityAt": "",
        }
    return summaries[key]


def _finalize_directory_summaries(summaries: Any, limit: int) -> list:
    finalized = []
    for summary in summaries:
        item = dict(summary)
        document_ids = item.pop("documentIds", set())
        item["documentCount"] = len(document_ids)
        item["documentIds"] = sorted(document_ids)[:25]
        for key in (
            "categories",
            "vendors",
            "targetSystems",
            "recordStatuses",
            "documentStatuses",
            "exportStatuses",
            "reconciliationStatuses",
            "ruleStatuses",
        ):
            if key in item:
                item[key] = _ranked_counts(item[key])
        item["needsAttention"] = bool(item.get("reviewRequiredCount") or item.get("failedCount"))
        finalized.append(item)
    finalized.sort(
        key=lambda item: (
            int(item.get("needsAttention") or 0),
            int(item.get("reviewRequiredCount") or 0),
            str(item.get("latestActivityAt") or ""),
            int(item.get("recordCount") or 0) + int(item.get("documentCount") or 0),
        ),
        reverse=True,
    )
    return finalized[:limit]


def _ranked_counts(values: Dict[str, int]) -> list:
    return [
        {"value": key, "count": count}
        for key, count in sorted(values.items(), key=lambda item: (-item[1], item[0]))
    ]
