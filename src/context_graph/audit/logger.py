"""
Compliance Audit Logger — immutable, append-only action log.

Records every review action for SOC 2, HIPAA, and PCI-DSS compliance
evidence. The audit log is strictly insert-only: no UPDATE or DELETE
operations are ever performed on the audit_log table.

Usage:
    logger = AuditLogger("/path/to/db")
    await logger.initialize()  # Creates table if needed
    await logger.log(
        action="finding_validated",
        actor="user-123",
        review_id="review-456",
        target_type="finding",
        target_id="finding-789",
        details={"status": "validated", "notes": "Confirmed."},
    )
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import aiosqlite

logger = logging.getLogger(__name__)

# Valid action types for the audit log
ACTION_TYPES = {
    "review_created",
    "review_completed",
    "finding_validated",
    "finding_assigned",
    "comment_added",
    "feedback_submitted",
    "lifecycle_changed",
    "consensus_vote",
    "cross_team_request",
    "cross_team_response",
    "pattern_saved",
    "gate_override",
    "prd_change_accepted",
    "prd_change_rejected",
    "review_request_created",
    "review_request_responded",
    "decision_logged",
}


class AuditLogger:
    """Append-only audit logger backed by SQLite.

    All writes are INSERT operations. There are no update or delete
    methods on this class — the audit trail is immutable.
    """

    CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS audit_log (
        id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        review_id TEXT,
        action TEXT NOT NULL,
        actor TEXT NOT NULL,
        actor_team TEXT,
        target_type TEXT,
        target_id TEXT,
        details_json TEXT NOT NULL DEFAULT '{}',
        ip_address TEXT,
        created_at TEXT NOT NULL
    )
    """

    CREATE_INDEXES_SQL = [
        "CREATE INDEX IF NOT EXISTS idx_audit_log_review ON audit_log(review_id)",
        "CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action)",
        "CREATE INDEX IF NOT EXISTS idx_audit_log_actor ON audit_log(actor)",
        "CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_audit_log_target ON audit_log(target_type, target_id)",
    ]

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self._initialized = False

    async def initialize(self) -> None:
        """Create the audit_log table and indexes if they don't exist."""
        if self._initialized:
            return

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(self.CREATE_TABLE_SQL)
            for idx_sql in self.CREATE_INDEXES_SQL:
                await db.execute(idx_sql)
            await db.commit()

        self._initialized = True

    async def log(
        self,
        action: str,
        actor: str,
        review_id: str | None = None,
        actor_team: str | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> str:
        """Write an audit log entry. Returns the entry ID.

        This is the ONLY write operation. No updates or deletes exist.
        """
        await self.initialize()

        entry_id = str(uuid4())
        now = datetime.utcnow().isoformat() + "Z"

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO audit_log
                   (id, timestamp, review_id, action, actor, actor_team,
                    target_type, target_id, details_json, ip_address, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry_id,
                    now,
                    review_id,
                    action,
                    actor,
                    actor_team,
                    target_type,
                    target_id,
                    json.dumps(details or {}, default=str),
                    ip_address,
                    now,
                ),
            )
            await db.commit()

        return entry_id

    async def get_review_log(
        self,
        review_id: str,
        action_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get all audit entries for a review, chronologically."""
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if action_filter:
                cursor = await db.execute(
                    "SELECT * FROM audit_log WHERE review_id = ? AND action = ? ORDER BY timestamp ASC",
                    (review_id, action_filter),
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM audit_log WHERE review_id = ? ORDER BY timestamp ASC",
                    (review_id,),
                )
            rows = await cursor.fetchall()

        return [self._row_to_dict(row) for row in rows]

    async def get_entries(
        self,
        from_date: str | None = None,
        to_date: str | None = None,
        action: str | None = None,
        actor: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Query audit log with optional filters."""
        await self.initialize()

        conditions = []
        params: list[Any] = []

        if from_date:
            conditions.append("timestamp >= ?")
            params.append(from_date)
        if to_date:
            conditions.append("timestamp <= ?")
            params.append(to_date)
        if action:
            conditions.append("action = ?")
            params.append(action)
        if actor:
            conditions.append("actor = ?")
            params.append(actor)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                f"SELECT * FROM audit_log WHERE {where_clause} ORDER BY timestamp DESC LIMIT ?",
                params,
            )
            rows = await cursor.fetchall()

        return [self._row_to_dict(row) for row in rows]

    async def get_stats(self) -> dict[str, Any]:
        """Get audit log statistics."""
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM audit_log")
            total = (await cursor.fetchone())[0]

            cursor = await db.execute(
                "SELECT action, COUNT(*) as cnt FROM audit_log GROUP BY action ORDER BY cnt DESC"
            )
            by_action = {row[0]: row[1] for row in await cursor.fetchall()}

            cursor = await db.execute(
                "SELECT actor, COUNT(*) as cnt FROM audit_log GROUP BY actor ORDER BY cnt DESC LIMIT 10"
            )
            by_actor = {row[0]: row[1] for row in await cursor.fetchall()}

        return {
            "total_entries": total,
            "by_action": by_action,
            "top_actors": by_actor,
        }

    def _row_to_dict(self, row: Any) -> dict[str, Any]:
        """Convert a database row to a dict."""
        d = dict(row)
        if "details_json" in d:
            try:
                d["details"] = json.loads(d["details_json"])
            except (json.JSONDecodeError, TypeError):
                d["details"] = {}
            del d["details_json"]
        return d
