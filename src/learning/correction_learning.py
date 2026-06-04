import re
from typing import Any, Dict, Optional

from src.storage.database import Database
from src.storage.schema_extender import SchemaExtender


class CorrectionLearningService:
    """Applies manual-review corrections and stores what FAB should learn from them."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.database = Database(config)
        SchemaExtender(config).ensure_learning_schema()

    def apply_document_correction(self, document_id: str, correction: Dict[str, Any], explanation: str = "") -> Dict[str, Any]:
        before = self._current_document_snapshot(document_id)
        corrected_fields = correction.get("extracted_data", {}) or {}
        vendor_name = correction.get("vendor_name") or corrected_fields.get("vendor_name")
        category = correction.get("category")
        category_path = correction.get("category_path", [])

        if corrected_fields:
            self._apply_field_corrections(document_id, corrected_fields)
        vendor_id = self._upsert_vendor(vendor_name, category) if vendor_name else None
        if vendor_id and correction.get("vendor_alias"):
            self._upsert_vendor_alias(vendor_id, correction["vendor_alias"])
        if category:
            self._record_category_decision(document_id, vendor_id, category, category_path)

        after = self._current_document_snapshot(document_id)
        now = self.database.now()
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO document_corrections (document_id, correction_type, before_json, after_json, explanation, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (document_id, correction.get("correction_type", "manual_review"), self.database.json_dumps(before), self.database.json_dumps(after), explanation, now),
            )
        self.database.add_audit_log("document", document_id, "manual_correction_applied", before, after, explanation, "user")
        return {"status": "correction_applied", "document_id": document_id, "vendor_id": vendor_id, "category": category}

    def create_category_rule(self, rule_name: str, category: str, pattern: str, rule_type: str = "text_contains") -> Dict[str, Any]:
        now = self.database.now()
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO category_rules (rule_name, category, pattern, rule_type, active, created_at, updated_at)
                VALUES (?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(rule_name) DO UPDATE SET
                    category=excluded.category,
                    pattern=excluded.pattern,
                    rule_type=excluded.rule_type,
                    active=1,
                    updated_at=excluded.updated_at
                """,
                (rule_name, category, pattern, rule_type, now, now),
            )
        self.database.add_audit_log("category_rule", rule_name, "upserted", None, {"category": category, "pattern": pattern, "rule_type": rule_type}, "Category rule learned", "user")
        return {"status": "rule_saved", "rule_name": rule_name, "category": category, "pattern": pattern, "rule_type": rule_type}

    def suggest_from_history(self, vendor_name: str) -> Optional[Dict[str, Any]]:
        normalized = self._normalize(vendor_name)
        vendor = self.database.fetch_one("SELECT * FROM vendors WHERE normalized_name = ?", (normalized,))
        if not vendor:
            alias = self.database.fetch_one("SELECT vendor_id FROM vendor_aliases WHERE normalized_alias = ? AND approved = 1", (normalized,))
            if alias:
                vendor = self.database.fetch_one("SELECT * FROM vendors WHERE id = ?", (alias["vendor_id"],))
        if not vendor:
            return None
        decision = self.database.fetch_one(
            "SELECT * FROM category_decisions WHERE vendor_id = ? AND approved = 1 ORDER BY created_at DESC LIMIT 1",
            (vendor["id"],),
        )
        return {"vendor": vendor, "category_decision": decision}

    def _apply_field_corrections(self, document_id: str, corrected_fields: Dict[str, Any]) -> None:
        now = self.database.now()
        with self.database.connect() as connection:
            for field_name, field_value in corrected_fields.items():
                connection.execute(
                    "INSERT INTO extracted_fields (document_id, field_name, field_value, confidence_score, source, requires_review, created_at) VALUES (?, ?, ?, 1.0, 'manual_correction', 0, ?)",
                    (document_id, field_name, self.database.json_dumps(field_value) if isinstance(field_value, (dict, list)) else str(field_value), now),
                )

    def _upsert_vendor(self, vendor_name: str, default_category: str = None) -> int:
        normalized = self._normalize(vendor_name)
        now = self.database.now()
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO vendors (name, normalized_name, approved, default_category, metadata_json, created_at, updated_at)
                VALUES (?, ?, 1, ?, '{}', ?, ?)
                ON CONFLICT(normalized_name) DO UPDATE SET
                    name=excluded.name,
                    approved=1,
                    default_category=COALESCE(excluded.default_category, vendors.default_category),
                    updated_at=excluded.updated_at
                """,
                (vendor_name, normalized, default_category, now, now),
            )
            row = connection.execute("SELECT id FROM vendors WHERE normalized_name = ?", (normalized,)).fetchone()
            return int(row["id"])

    def _upsert_vendor_alias(self, vendor_id: int, alias: str) -> None:
        now = self.database.now()
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO vendor_aliases (vendor_id, alias, normalized_alias, confidence_score, approved, created_at)
                VALUES (?, ?, ?, 1.0, 1, ?)
                ON CONFLICT(vendor_id, normalized_alias) DO NOTHING
                """,
                (vendor_id, alias, self._normalize(alias), now),
            )

    def _record_category_decision(self, document_id: str, vendor_id: int, category: str, category_path: Any) -> None:
        now = self.database.now()
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO category_decisions (document_id, vendor_id, category, category_path_json, confidence_score, source, approved, created_at) VALUES (?, ?, ?, ?, 1.0, 'manual_correction', 1, ?)",
                (document_id, vendor_id, category, self.database.json_dumps(category_path or []), now),
            )

    def _current_document_snapshot(self, document_id: str) -> Dict[str, Any]:
        return {
            "document": self.database.fetch_one("SELECT * FROM documents WHERE id = ?", (document_id,)),
            "fields": self.database.fetch_all("SELECT field_name, field_value, confidence_score, source FROM extracted_fields WHERE document_id = ?", (document_id,)),
        }

    @staticmethod
    def _normalize(value: str) -> str:
        value = (value or "").lower().strip()
        value = re.sub(r"[^a-z0-9]+", " ", value)
        return re.sub(r"\s+", " ", value).strip()
