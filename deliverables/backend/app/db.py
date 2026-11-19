from __future__ import annotations

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4


APP_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("AGENTSHOW_DATA_DIR", str(APP_DIR.parent.parent / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "agentshow.db"

_lock = threading.RLock()


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:16]}"


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    with _lock:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def init_db() -> None:
    with connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'idle',
                model_name TEXT NOT NULL DEFAULT 'Demo Agent',
                workspace_path TEXT NOT NULL,
                goal TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS app_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, created_at);

            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                goal_id TEXT,
                status TEXT NOT NULL,
                model_name TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                stop_reason TEXT,
                usage_json TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_runs_session ON runs(session_id, started_at);

            CREATE TABLE IF NOT EXISTS trace_spans (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                parent_span_id TEXT,
                kind TEXT NOT NULL,
                name TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                duration_ms INTEGER,
                status TEXT NOT NULL,
                summary TEXT NOT NULL,
                input_json TEXT,
                output_json TEXT,
                error_json TEXT,
                usage_json TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_spans_session ON trace_spans(session_id, started_at);
            CREATE INDEX IF NOT EXISTS idx_spans_run ON trace_spans(run_id, started_at);
            CREATE INDEX IF NOT EXISTS idx_spans_parent ON trace_spans(parent_span_id);

            CREATE TABLE IF NOT EXISTS trace_events (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                seq INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                span_id TEXT,
                parent_span_id TEXT,
                created_at TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                UNIQUE(session_id, seq)
            );
            CREATE INDEX IF NOT EXISTS idx_events_session ON trace_events(session_id, seq);
            CREATE INDEX IF NOT EXISTS idx_events_run ON trace_events(run_id, seq);

            CREATE TABLE IF NOT EXISTS tool_calls (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                span_id TEXT,
                tool_name TEXT NOT NULL,
                args_json TEXT NOT NULL,
                args_digest TEXT NOT NULL,
                risk TEXT NOT NULL,
                status TEXT NOT NULL,
                approval_id TEXT,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                duration_ms INTEGER,
                result_summary TEXT,
                error_code TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_tools_session ON tool_calls(session_id, started_at);

            CREATE TABLE IF NOT EXISTS providers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                protocol TEXT NOT NULL,
                base_url TEXT NOT NULL,
                model TEXT NOT NULL,
                api_key_ciphertext TEXT,
                api_key_hint TEXT,
                enabled INTEGER NOT NULL DEFAULT 1,
                is_default INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS skill_preferences (
                name TEXT PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS goals (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                objective TEXT NOT NULL,
                criteria_json TEXT NOT NULL,
                constraints_json TEXT NOT NULL,
                skills_json TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL,
                current_iteration INTEGER NOT NULL DEFAULT 0,
                max_iterations INTEGER NOT NULL DEFAULT 5,
                progress_summary TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                ended_at TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_goals_session ON goals(session_id, created_at);

            CREATE TABLE IF NOT EXISTS goal_iterations (
                id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL,
                iteration_no INTEGER NOT NULL,
                run_id TEXT,
                status TEXT NOT NULL,
                plan TEXT,
                summary TEXT,
                evidence_json TEXT,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_goal_iterations ON goal_iterations(goal_id, iteration_no);

            CREATE TABLE IF NOT EXISTS checkpoints (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                run_id TEXT,
                goal_id TEXT,
                goal_iteration_id TEXT,
                kind TEXT NOT NULL,
                pi_entry_id TEXT,
                last_event_seq INTEGER NOT NULL DEFAULT 0,
                context_hash TEXT,
                workspace_snapshot_id TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_checkpoints_session ON checkpoints(session_id, created_at);

            CREATE TABLE IF NOT EXISTS approvals (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                tool_call_id TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                args_json TEXT NOT NULL,
                args_digest TEXT NOT NULL,
                risk TEXT NOT NULL,
                status TEXT NOT NULL,
                requested_at TEXT NOT NULL,
                decided_at TEXT,
                decided_by TEXT,
                feedback TEXT
            );
            """
        )
        goal_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(goals)").fetchall()
        }
        if "skills_json" not in goal_columns:
            conn.execute(
                "ALTER TABLE goals ADD COLUMN skills_json TEXT NOT NULL DEFAULT '[]'"
            )


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def json_loads(value: str | None, default: Any = None) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def next_seq(conn: sqlite3.Connection, session_id: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(seq), 0) + 1 AS next_seq FROM trace_events WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    return int(row["next_seq"])

