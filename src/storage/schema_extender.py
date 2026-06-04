from typing import Any, Dict

from src.storage.database import Database


class SchemaExtender:
    """Adds optional FAB tables without requiring a full migration framework yet."""

    def __init__(self, config: Dict[str, Any]):
        self.database = Database(config)

    def ensure_learning_schema(self) -> None:
        with self.database.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS vendor_aliases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vendor_id INTEGER NOT NULL,
                    alias TEXT NOT NULL,
                    normalized_alias TEXT NOT NULL,
                    confidence_score REAL NOT NULL DEFAULT 1.0,
                    approved INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    UNIQUE(vendor_id, normalized_alias),
                    FOREIGN KEY(vendor_id) REFERENCES vendors(id)
                );

                CREATE TABLE IF NOT EXISTS category_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT,
                    vendor_id INTEGER,
                    category TEXT NOT NULL,
                    category_path_json TEXT NOT NULL DEFAULT '[]',
                    confidence_score REAL NOT NULL DEFAULT 1.0,
                    source TEXT NOT NULL DEFAULT 'manual_correction',
                    approved INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(vendor_id) REFERENCES vendors(id)
                );

                CREATE TABLE IF NOT EXISTS category_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_name TEXT NOT NULL UNIQUE,
                    category TEXT NOT NULL,
                    pattern TEXT NOT NULL,
                    rule_type TEXT NOT NULL DEFAULT 'text_contains',
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS document_corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT NOT NULL,
                    correction_type TEXT NOT NULL,
                    before_json TEXT NOT NULL DEFAULT '{}',
                    after_json TEXT NOT NULL DEFAULT '{}',
                    explanation TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )
