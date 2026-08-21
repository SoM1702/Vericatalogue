from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import AgentDecision, ProductRecord, ReviewAgentPlan


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
        connection = self._connect()
        try:
            with connection:
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
                    CREATE TABLE IF NOT EXISTS agent_decisions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        product_id TEXT NOT NULL,
                        attribute_field TEXT NOT NULL,
                        agent_name TEXT NOT NULL,
                        agent_action TEXT NOT NULL,
                        input_context TEXT,
                        output TEXT,
                        evidence_ids TEXT,
                        reason TEXT,
                        confidence REAL,
                        created_at TEXT NOT NULL
                    );
                    """
                )
        finally:
            connection.close()

    def save(self, product: ProductRecord) -> ProductRecord:
        payload = product.model_dump_json()
        connection = self._connect()
        try:
            with connection:
                connection.execute(
                    "INSERT OR REPLACE INTO products(id, created_at, payload) VALUES (?, ?, ?)",
                    (product.id, product.created_at.isoformat(), payload),
                )
        finally:
            connection.close()
        return product

    def get(self, product_id: str) -> ProductRecord | None:
        connection = self._connect()
        try:
            row = connection.execute("SELECT payload FROM products WHERE id = ?", (product_id,)).fetchone()
            return ProductRecord.model_validate_json(row["payload"]) if row else None
        finally:
            connection.close()

    def list_all(self) -> list[ProductRecord]:
        connection = self._connect()
        try:
            rows = connection.execute("SELECT payload FROM products ORDER BY created_at DESC").fetchall()
            return [ProductRecord.model_validate_json(row["payload"]) for row in rows]
        finally:
            connection.close()

    def add_audit_event(self, product_id: str, attribute_field: str, action: str, note: str | None) -> None:
        connection = self._connect()
        try:
            with connection:
                connection.execute(
                    "INSERT INTO audit_events(product_id, attribute_field, action, note, created_at) VALUES (?, ?, ?, ?, ?)",
                    (product_id, attribute_field, action, note, datetime.now(timezone.utc).isoformat()),
                )
        finally:
            connection.close()

    def save_review_agent_run(self, plan: ReviewAgentPlan) -> ReviewAgentPlan:
        connection = self._connect()
        try:
            with connection:
                connection.execute(
                    "INSERT INTO review_agent_runs(id, product_id, payload, created_at) VALUES (?, ?, ?, ?)",
                    (plan.id, plan.product_id, plan.model_dump_json(), plan.created_at.isoformat()),
                )
        finally:
            connection.close()
        return plan

    def latest_review_agent_run(self, product_id: str) -> ReviewAgentPlan | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT payload FROM review_agent_runs WHERE product_id = ? ORDER BY created_at DESC LIMIT 1",
                (product_id,),
            ).fetchone()
            return ReviewAgentPlan.model_validate_json(row["payload"]) if row else None
        finally:
            connection.close()

    def save_agent_decision(self, decision: AgentDecision) -> AgentDecision:
        connection = self._connect()
        try:
            with connection:
                connection.execute(
                    """
                    INSERT INTO agent_decisions(
                        product_id, attribute_field, agent_name, agent_action,
                        input_context, output, evidence_ids, reason, confidence, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        decision.product_id,
                        decision.attribute_field,
                        decision.agent_name,
                        decision.agent_action,
                        decision.input_context,
                        decision.output,
                        json.dumps(decision.evidence_ids),
                        decision.reason,
                        decision.confidence,
                        decision.created_at.isoformat(),
                    ),
                )
        finally:
            connection.close()
        return decision

    def get_agent_decisions(self, product_id: str) -> list[AgentDecision]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM agent_decisions WHERE product_id = ? ORDER BY created_at ASC",
                (product_id,),
            ).fetchall()
            decisions = []
            for row in rows:
                decisions.append(
                    AgentDecision(
                        product_id=row["product_id"],
                        attribute_field=row["attribute_field"],
                        agent_name=row["agent_name"],
                        agent_action=row["agent_action"],
                        input_context=row["input_context"],
                        output=row["output"],
                        evidence_ids=json.loads(row["evidence_ids"]) if row["evidence_ids"] else [],
                        reason=row["reason"],
                        confidence=row["confidence"],
                        created_at=datetime.fromisoformat(row["created_at"]),
                    )
                )
            return decisions
        finally:
            connection.close()


