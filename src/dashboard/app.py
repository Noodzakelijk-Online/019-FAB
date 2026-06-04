from functools import wraps
from typing import Any, Dict

from flask import Flask, abort, jsonify, request

from src.backup.backup_manager import BackupManager
from src.exceptions.exception_memory import ExceptionMemory
from src.learning.correction_learning import CorrectionLearningService
from src.missing_receipts.follow_up_manager import MissingReceiptFollowUpManager
from src.storage.database import Database
from src.storage.schema_extender import SchemaExtender


def create_app(config: Dict[str, Any] = None) -> Flask:
    config = config or {}
    app = Flask(__name__)
    database = Database(config)
    SchemaExtender(config).ensure_learning_schema()
    backup_manager = BackupManager(config)
    exception_memory = ExceptionMemory(config)
    follow_up_manager = MissingReceiptFollowUpManager(config)
    correction_learning = CorrectionLearningService(config)
    dashboard_token = config.get("dashboard_access_token")

    def require_auth(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not dashboard_token:
                abort(503, description="Dashboard token is not configured.")
            provided = request.headers.get("X-FAB-Token")
            if provided != dashboard_token:
                abort(401, description="Invalid or missing FAB dashboard token.")
            return func(*args, **kwargs)
        return wrapper

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "service": "FAB local dashboard"})

    @app.get("/")
    @require_auth
    def index():
        counts = database.fetch_all("SELECT current_state, COUNT(*) AS count FROM documents GROUP BY current_state ORDER BY current_state")
        pending_reviews = database.fetch_all("SELECT COUNT(*) AS count FROM manual_review_items WHERE status = 'pending'")[0]["count"]
        open_missing_receipts = database.fetch_all("SELECT COUNT(*) AS count FROM missing_receipt_alerts WHERE status = 'open'")[0]["count"]
        open_followups = database.fetch_all("SELECT COUNT(*) AS count FROM outreach_reminders WHERE status = 'open'")[0]["count"]
        return jsonify({
            "application": "FAB",
            "mode": "local-ngrok-compatible",
            "document_state_counts": counts,
            "pending_manual_reviews": pending_reviews,
            "open_missing_receipts": open_missing_receipts,
            "open_followups": open_followups,
            "endpoints": [
                "/documents", "/manual-review", "/audit-log", "/posting-attempts",
                "/reconciliation-results", "/missing-receipts", "/bank-transactions",
                "/exceptions", "/outreach-reminders", "/vendors", "/category-decisions",
                "/category-rules", "/document-corrections", "/backups",
            ],
        })

    @app.get("/documents")
    @require_auth
    def documents():
        return jsonify(database.fetch_all("SELECT id, source, original_filename, current_state, created_at, updated_at FROM documents ORDER BY updated_at DESC LIMIT 200"))

    @app.get("/documents/<document_id>")
    @require_auth
    def document_detail(document_id: str):
        document = database.fetch_one("SELECT * FROM documents WHERE id = ?", (document_id,))
        if not document:
            abort(404, description="Document not found")
        return jsonify({
            "document": document,
            "ocr_results": database.fetch_all("SELECT * FROM ocr_results WHERE document_id = ? ORDER BY created_at DESC", (document_id,)),
            "extracted_fields": database.fetch_all("SELECT * FROM extracted_fields WHERE document_id = ? ORDER BY field_name", (document_id,)),
            "manual_reviews": database.fetch_all("SELECT * FROM manual_review_items WHERE document_id = ? ORDER BY created_at DESC", (document_id,)),
            "audit_log": database.fetch_all("SELECT * FROM audit_log WHERE entity_id = ? ORDER BY created_at DESC LIMIT 100", (document_id,)),
            "posting_attempts": database.fetch_all("SELECT * FROM posting_attempts WHERE document_id = ? ORDER BY created_at DESC", (document_id,)),
            "reconciliation_results": database.fetch_all("SELECT * FROM reconciliation_results WHERE document_id = ? ORDER BY created_at DESC", (document_id,)),
            "corrections": database.fetch_all("SELECT * FROM document_corrections WHERE document_id = ? ORDER BY created_at DESC", (document_id,)),
        })

    @app.post("/documents/<document_id>/corrections")
    @require_auth
    def apply_document_correction(document_id: str):
        payload = request.get_json(silent=True) or {}
        correction = payload.get("correction") or payload
        explanation = payload.get("explanation", "Manual correction from dashboard")
        return jsonify(correction_learning.apply_document_correction(document_id, correction, explanation))

    @app.get("/manual-review")
    @require_auth
    def manual_review():
        status = request.args.get("status", "pending")
        return jsonify(database.fetch_all("SELECT * FROM manual_review_items WHERE status = ? ORDER BY created_at DESC LIMIT 200", (status,)))

    @app.post("/manual-review/<int:item_id>/resolve")
    @require_auth
    def resolve_manual_review(item_id: int):
        payload = request.get_json(silent=True) or {}
        resolution = payload.get("resolution", "resolved")
        new_status = payload.get("status", "resolved")
        with database.connect() as connection:
            connection.execute("UPDATE manual_review_items SET status = ?, resolution = ?, resolved_at = ? WHERE id = ?", (new_status, resolution, database.now(), item_id))
        database.add_audit_log("manual_review_item", str(item_id), "resolved", None, payload, resolution, "user")
        return jsonify({"status": "resolved", "item_id": item_id})

    @app.post("/manual-review/<int:item_id>/apply-correction")
    @require_auth
    def apply_review_correction(item_id: int):
        review = database.fetch_one("SELECT * FROM manual_review_items WHERE id = ?", (item_id,))
        if not review:
            abort(404, description="Manual review item not found")
        payload = request.get_json(silent=True) or {}
        correction = payload.get("correction") or payload
        explanation = payload.get("explanation", "Manual review correction applied")
        result = correction_learning.apply_document_correction(review["document_id"], correction, explanation)
        with database.connect() as connection:
            connection.execute("UPDATE manual_review_items SET status = 'resolved', resolution = ?, resolved_at = ? WHERE id = ?", (explanation, database.now(), item_id))
        return jsonify(result)

    @app.get("/audit-log")
    @require_auth
    def audit_log():
        return jsonify(database.fetch_all("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 300"))

    @app.get("/posting-attempts")
    @require_auth
    def posting_attempts():
        return jsonify(database.fetch_all("SELECT * FROM posting_attempts ORDER BY updated_at DESC LIMIT 200"))

    @app.get("/reconciliation-results")
    @require_auth
    def reconciliation_results():
        return jsonify(database.fetch_all("SELECT * FROM reconciliation_results ORDER BY created_at DESC LIMIT 300"))

    @app.get("/missing-receipts")
    @require_auth
    def missing_receipts():
        status = request.args.get("status", "open")
        return jsonify(database.fetch_all("SELECT * FROM missing_receipt_alerts WHERE status = ? ORDER BY created_at DESC LIMIT 200", (status,)))

    @app.get("/bank-transactions")
    @require_auth
    def bank_transactions():
        return jsonify(database.fetch_all("SELECT * FROM bank_transactions ORDER BY transaction_date DESC LIMIT 300"))

    @app.get("/exceptions")
    @require_auth
    def exceptions():
        active = request.args.get("active", "1")
        return jsonify(database.fetch_all("SELECT * FROM exceptions WHERE active = ? ORDER BY created_at DESC LIMIT 300", (int(active),)))

    @app.post("/exceptions")
    @require_auth
    def approve_exception():
        payload = request.get_json(silent=True) or {}
        exception_type = payload.get("exception_type")
        context = payload.get("context") or {}
        explanation = payload.get("explanation")
        if not exception_type or not explanation:
            abort(400, description="exception_type and explanation are required")
        return jsonify(exception_memory.approve_exception(exception_type, context, explanation))

    @app.post("/exceptions/<fingerprint>/deactivate")
    @require_auth
    def deactivate_exception(fingerprint: str):
        payload = request.get_json(silent=True) or {}
        reason = payload.get("reason", "Exception deactivated from dashboard")
        status = "deactivated" if exception_memory.deactivate_exception(fingerprint, reason) else "not_found"
        return jsonify({"status": status})

    @app.get("/outreach-reminders")
    @require_auth
    def outreach_reminders():
        status = request.args.get("status", "open")
        return jsonify(database.fetch_all("SELECT * FROM outreach_reminders WHERE status = ? ORDER BY updated_at DESC LIMIT 300", (status,)))

    @app.post("/outreach-reminders/<transaction_id>/complete")
    @require_auth
    def complete_outreach(transaction_id: str):
        payload = request.get_json(silent=True) or {}
        reason = payload.get("reason", "Receipt received and processed")
        return jsonify({"completed": follow_up_manager.mark_completed(transaction_id, reason)})

    @app.post("/outreach-reminders/<transaction_id>/stop")
    @require_auth
    def stop_outreach(transaction_id: str):
        payload = request.get_json(silent=True) or {}
        reason = payload.get("reason", "Stopped from dashboard")
        return jsonify({"stopped": follow_up_manager.stop_follow_up(transaction_id, reason)})

    @app.get("/outreach-reminders/due")
    @require_auth
    def due_outreach():
        return jsonify(follow_up_manager.reminders_due())

    @app.get("/vendors")
    @require_auth
    def vendors():
        return jsonify(database.fetch_all("SELECT * FROM vendors ORDER BY updated_at DESC LIMIT 300"))

    @app.get("/category-decisions")
    @require_auth
    def category_decisions():
        return jsonify(database.fetch_all("SELECT * FROM category_decisions ORDER BY created_at DESC LIMIT 300"))

    @app.get("/category-rules")
    @require_auth
    def category_rules():
        return jsonify(database.fetch_all("SELECT * FROM category_rules WHERE active = 1 ORDER BY updated_at DESC LIMIT 300"))

    @app.post("/category-rules")
    @require_auth
    def create_category_rule():
        payload = request.get_json(silent=True) or {}
        return jsonify(correction_learning.create_category_rule(
            payload.get("rule_name"), payload.get("category"), payload.get("pattern"), payload.get("rule_type", "text_contains")
        ))

    @app.get("/document-corrections")
    @require_auth
    def document_corrections():
        return jsonify(database.fetch_all("SELECT * FROM document_corrections ORDER BY created_at DESC LIMIT 300"))

    @app.get("/backups")
    @require_auth
    def list_backups():
        return jsonify(backup_manager.list_backups())

    @app.post("/backups")
    @require_auth
    def create_backup():
        payload = request.get_json(silent=True) or {}
        paths = payload.get("paths")
        backup_config = payload.get("backup_config", {"type": "zip"})
        result = backup_manager.perform_backup(paths, backup_config)
        database.add_audit_log("backup", result.get("path", "unknown"), "backup_created", None, result, result.get("status", "unknown"), "user")
        return jsonify(result)

    @app.post("/backups/restore")
    @require_auth
    def restore_backup():
        payload = request.get_json(silent=True) or {}
        backup_path = payload.get("backup_path")
        restore_dir = payload.get("restore_dir", "restore_preview")
        allow_overwrite = bool(payload.get("allow_overwrite", False))
        if not backup_path:
            abort(400, description="backup_path is required")
        result = backup_manager.restore_backup(backup_path, restore_dir, allow_overwrite=allow_overwrite)
        database.add_audit_log("backup", backup_path, "backup_restore_requested", None, result, result.get("status", "unknown"), "user")
        return jsonify(result)

    return app
