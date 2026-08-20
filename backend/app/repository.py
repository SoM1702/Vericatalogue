from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import ProductRecord, ReviewAgentPlan


class ProductRepository:
    """Small SQLite repository kept intentionally replaceable for a future database adapter."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS products (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id TEXT NOT NULL,
                    attribute_field TEXT NOT NULL,
                    action TEXT NOT NULL,
                    note TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS review_agent_runs (
                    id TEXT PRIMARY KEY,
                    product_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def save(self, product: ProductRecord) -> ProductRecord:
        payload = product.model_dump_json()
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO products(id, created_at, payload) VALUES (?, ?, ?)",
                (product.id, product.created_at.isoformat(), payload),
            )
        return product

    def get(self, product_id: str) -> ProductRecord | None:
        with self._connect() as connection:
            row = connection.execute("SELECT payload FROM products WHERE id = ?", (product_id,)).fetchone()
        return ProductRecord.model_validate_json(row["payload"]) if row else None

    def list_all(self) -> list[ProductRecord]:
        with self._connect() as connection:
            rows = connection.execute("SELECT payload FROM products ORDER BY created_at DESC").fetchall()
        return [ProductRecord.model_validate_json(row["payload"]) for row in rows]

    def add_audit_event(self, product_id: str, attribute_field: str, action: str, note: str | None) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO audit_events(product_id, attribute_field, action, note, created_at) VALUES (?, ?, ?, ?, ?)",
                (product_id, attribute_field, action, note, datetime.now(timezone.utc).isoformat()),
            )

    def save_review_agent_run(self, plan: ReviewAgentPlan) -> ReviewAgentPlan:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO review_agent_runs(id, product_id, payload, created_at) VALUES (?, ?, ?, ?)",
                (plan.id, plan.product_id, plan.model_dump_json(), plan.created_at.isoformat()),
            )
        return plan

    def latest_review_agent_run(self, product_id: str) -> ReviewAgentPlan | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM review_agent_runs WHERE product_id = ? ORDER BY created_at DESC LIMIT 1",
                (product_id,),
            ).fetchone()
        return ReviewAgentPlan.model_validate_json(row["payload"]) if row else None
