from functools import wraps
from typing import Any, Dict

from flask import Flask, abort, jsonify, request

from src.storage.database import Database


def create_app(config: Dict[str, Any] = None) -> Flask:
    config = config or {}
    app = Flask(__name__)
    database = Database(config)
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
        counts = database.fetch_all(
            "SELECT current_state, COUNT(*) AS count FROM documents GROUP BY current_state ORDER BY current_state"
        )
        pending_reviews = database.fetch_all(
            "SELECT COUNT(*) AS count FROM manual_review_items WHERE status = 'pending'"
        )[0]["count"]
        open_missing_receipts = database.fetch_all(
            "SELECT COUNT(*) AS count FROM missing_receipt_alerts WHERE status = 'open'"
        )[0]["count"]
        return jsonify(
            {
                "application": "FAB",
                "mode": "local-ngrok-compatible",
                "document_state_counts": counts,
                "pending_manual_reviews": pending_reviews,
                "open_missing_receipts": open_missing_receipts,
                "endpoints": [
                    "/documents",
                    "/manual-review",
                    "/audit-log",
                    "/posting-attempts",
                    "/reconciliation-results",
                    "/missing-receipts",
                    "/bank-transactions",
                ],
            }
        )

    @app.get("/documents")
    @require_auth
    def documents():
        return jsonify(database.fetch_all(
            "SELECT id, source, original_filename, current_state, created_at, updated_at FROM documents ORDER BY updated_at DESC LIMIT 200"
        ))

    @app.get("/documents/<document_id>")
    @require_auth
    def document_detail(document_id: str):
        document = database.fetch_one("SELECT * FROM documents WHERE id = ?", (document_id,))
        if not document:
            abort(404, description="Document not found")
        return jsonify(
            {
                "document": document,
                "ocr_results": database.fetch_all("SELECT * FROM ocr_results WHERE document_id = ? ORDER BY created_at DESC", (document_id,)),
                "extracted_fields": database.fetch_all("SELECT * FROM extracted_fields WHERE document_id = ? ORDER BY field_name", (document_id,)),
                "manual_reviews": database.fetch_all("SELECT * FROM manual_review_items WHERE document_id = ? ORDER BY created_at DESC", (document_id,)),
                "audit_log": database.fetch_all("SELECT * FROM audit_log WHERE entity_id = ? ORDER BY created_at DESC LIMIT 100", (document_id,)),
                "posting_attempts": database.fetch_all("SELECT * FROM posting_attempts WHERE document_id = ? ORDER BY created_at DESC", (document_id,)),
                "reconciliation_results": database.fetch_all("SELECT * FROM reconciliation_results WHERE document_id = ? ORDER BY created_at DESC", (document_id,)),
            }
        )

    @app.get("/manual-review")
    @require_auth
    def manual_review():
        status = request.args.get("status", "pending")
        return jsonify(database.fetch_all(
            "SELECT * FROM manual_review_items WHERE status = ? ORDER BY created_at DESC LIMIT 200",
            (status,),
        ))

    @app.post("/manual-review/<int:item_id>/resolve")
    @require_auth
    def resolve_manual_review(item_id: int):
        payload = request.get_json(silent=True) or {}
        resolution = payload.get("resolution", "resolved")
        new_status = payload.get("status", "resolved")
        with database.connect() as connection:
            connection.execute(
                "UPDATE manual_review_items SET status = ?, resolution = ?, resolved_at = ? WHERE id = ?",
                (new_status, resolution, database.now(), item_id),
            )
        database.add_audit_log("manual_review_item", str(item_id), "resolved", None, payload, resolution, "user")
        return jsonify({"status": "resolved", "item_id": item_id})

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
        return jsonify(database.fetch_all(
            "SELECT * FROM missing_receipt_alerts WHERE status = ? ORDER BY created_at DESC LIMIT 200",
            (status,),
        ))

    @app.get("/bank-transactions")
    @require_auth
    def bank_transactions():
        return jsonify(database.fetch_all("SELECT * FROM bank_transactions ORDER BY transaction_date DESC LIMIT 300"))

    return app
