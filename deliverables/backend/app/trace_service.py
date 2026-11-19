from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from .db import connection, json_dumps, json_loads, new_id, next_seq, utc_now
from .events import EventBroker


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _duration_ms(started_at: str, ended_at: str | None) -> int | None:
    start = _parse_dt(started_at)
    end = _parse_dt(ended_at)
    if not start or not end:
        return None
    return max(0, int((end - start).total_seconds() * 1000))


class TraceService:
    def __init__(self, broker: EventBroker) -> None:
        self.broker = broker

    async def event(
        self,
        session_id: str,
        run_id: str,
        event_type: str,
        payload: dict[str, Any],
        span_id: str | None = None,
        parent_span_id: str | None = None,
    ) -> dict[str, Any]:
        event_id = new_id("evt")
        created_at = utc_now()
        with connection() as conn:
            seq = next_seq(conn, session_id)
            conn.execute(
                """
                INSERT INTO trace_events
                (id, session_id, run_id, seq, event_type, span_id, parent_span_id, created_at, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    session_id,
                    run_id,
                    seq,
                    event_type,
                    span_id,
                    parent_span_id,
                    created_at,
                    json_dumps(payload),
                ),
            )
        message = {
            "type": "trace.event",
            "seq": seq,
            "event_id": event_id,
            "session_id": session_id,
            "run_id": run_id,
            "event": event_type,
            "span_id": span_id,
            "timestamp": created_at,
            "data": payload,
        }
        await self.broker.publish(session_id, message)
        return message

    async def start_span(
        self,
        session_id: str,
        run_id: str,
        kind: str,
        name: str,
        summary: str,
        parent_span_id: str | None = None,
        status: str = "running",
        input_data: Any = None,
    ) -> str:
        span_id = new_id("span")
        started_at = utc_now()
        with connection() as conn:
            conn.execute(
                """
                INSERT INTO trace_spans
                (id, session_id, run_id, parent_span_id, kind, name, started_at, status, summary, input_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    span_id,
                    session_id,
                    run_id,
                    parent_span_id,
                    kind,
                    name,
                    started_at,
                    status,
                    summary,
                    json_dumps(input_data) if input_data is not None else None,
                ),
            )
        await self.broker.publish(
            session_id,
            {
                "type": "span.started",
                "span_id": span_id,
                "session_id": session_id,
                "run_id": run_id,
                "data": {
                    "kind": kind,
                    "name": name,
                    "summary": summary,
                    "parent_span_id": parent_span_id,
                    "started_at": started_at,
                    "status": status,
                },
            },
        )
        return span_id

    async def finish_span(
        self,
        session_id: str,
        run_id: str,
        span_id: str,
        status: str,
        summary: str | None = None,
        output_data: Any = None,
        error: Any = None,
        usage: Any = None,
    ) -> None:
        ended_at = utc_now()
        with connection() as conn:
            row = conn.execute(
                "SELECT started_at, summary FROM trace_spans WHERE id = ?",
                (span_id,),
            ).fetchone()
            if not row:
                return
            duration_ms = _duration_ms(row["started_at"], ended_at)
            conn.execute(
                """
                UPDATE trace_spans
                SET ended_at = ?, duration_ms = ?, status = ?, summary = COALESCE(?, summary),
                    output_json = ?, error_json = ?, usage_json = ?
                WHERE id = ?
                """,
                (
                    ended_at,
                    duration_ms,
                    status,
                    summary,
                    json_dumps(output_data) if output_data is not None else None,
                    json_dumps(error) if error is not None else None,
                    json_dumps(usage) if usage is not None else None,
                    span_id,
                ),
            )
        await self.broker.publish(
            session_id,
            {
                "type": "span.completed",
                "span_id": span_id,
                "session_id": session_id,
                "run_id": run_id,
                "data": {
                    "status": status,
                    "summary": summary or row["summary"],
                    "ended_at": ended_at,
                    "duration_ms": duration_ms,
                },
            },
        )

    async def record_tool_call(
        self,
        session_id: str,
        run_id: str,
        span_id: str | None,
        tool_name: str,
        args: dict[str, Any],
        result: str,
        status: str = "success",
        error_code: str | None = None,
        started_at: str | None = None,
        ended_at: str | None = None,
    ) -> str:
        call_id = new_id("tool")
        started = started_at or utc_now()
        ended = ended_at or utc_now()
        digest = hashlib.sha256(json_dumps(args).encode("utf-8")).hexdigest()
        with connection() as conn:
            conn.execute(
                """
                INSERT INTO tool_calls
                (id, session_id, run_id, span_id, tool_name, args_json, args_digest, risk, status,
                 started_at, ended_at, duration_ms, result_summary, error_code)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'write', ?, ?, ?, ?, ?, ?)
                """,
                (
                    call_id,
                    session_id,
                    run_id,
                    span_id,
                    tool_name,
                    json_dumps(args),
                    digest,
                    status,
                    started,
                    ended,
                    _duration_ms(started, ended),
                    result[:1000],
                    error_code,
                ),
            )
        return call_id

    def get_trace(self, session_id: str) -> dict[str, Any]:
        with connection() as conn:
            session = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if not session:
                raise KeyError("SESSION_NOT_FOUND")
            messages = [
                dict(row)
                for row in conn.execute(
                    "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at",
                    (session_id,),
                ).fetchall()
            ]
            runs = [
                dict(row)
                for row in conn.execute(
                    "SELECT * FROM runs WHERE session_id = ? ORDER BY started_at",
                    (session_id,),
                ).fetchall()
            ]
            spans = [
                dict(row)
                for row in conn.execute(
                    "SELECT * FROM trace_spans WHERE session_id = ? ORDER BY started_at",
                    (session_id,),
                ).fetchall()
            ]
            tool_calls = [
                dict(row)
                for row in conn.execute(
                    "SELECT * FROM tool_calls WHERE session_id = ? ORDER BY started_at",
                    (session_id,),
                ).fetchall()
            ]
            goals = [
                dict(row)
                for row in conn.execute(
                    "SELECT * FROM goals WHERE session_id = ? ORDER BY created_at",
                    (session_id,),
                ).fetchall()
            ]

        started = [row["started_at"] for row in spans if row.get("started_at")]
        ended = [row["ended_at"] for row in spans if row.get("ended_at")]
        total_ms = 0
        if started and ended:
            first = min(started)
            last = max(ended)
            total_ms = _duration_ms(first, last) or 0

        user_rounds = sum(1 for item in messages if item["role"] == "user")
        call_count = len(spans)
        error_count = sum(1 for item in spans if item["status"] == "error")
        success_count = sum(1 for item in spans if item["status"] == "success")
        token_rows = [
            value
            for item in spans
            if isinstance((value := json_loads(item.get("usage_json"), {})), dict)
        ]
        total_tokens = sum(int(item.get("total_tokens", 0) or 0) for item in token_rows)
        tokens_per_second = (
            round(total_tokens / (total_ms / 1000), 2) if total_ms > 0 else 0
        )

        for span in spans:
            span["input"] = json_loads(span.pop("input_json", None), None)
            span["output"] = json_loads(span.pop("output_json", None), None)
            span["error"] = json_loads(span.pop("error_json", None), None)
            span["usage"] = json_loads(span.pop("usage_json", None), None)
            if span["duration_ms"] is None:
                span["duration_ms"] = _duration_ms(span["started_at"], span.get("ended_at")) or 0

        return {
            "session": dict(session),
            "summary": {
                "total_duration_ms": total_ms,
                "round_count": user_rounds,
                "call_count": call_count,
                "error_count": error_count,
                "success_rate": round(success_count / call_count * 100, 1) if call_count else 0,
                "total_tokens": total_tokens,
                "tokens_per_second": tokens_per_second,
            },
            "messages": messages,
            "runs": runs,
            "spans": spans,
            "tool_calls": tool_calls,
            "goals": goals,
        }

    def lookup(self, identifier: str) -> dict[str, Any]:
        tables = [
            ("session", "sessions", "id"),
            ("run", "runs", "id"),
            ("span", "trace_spans", "id"),
            ("event", "trace_events", "id"),
            ("tool_call", "tool_calls", "id"),
            ("goal", "goals", "id"),
            ("checkpoint", "checkpoints", "id"),
        ]
        with connection() as conn:
            for entity, table, column in tables:
                row = conn.execute(f"SELECT * FROM {table} WHERE {column} = ?", (identifier,)).fetchone()
                if row:
                    data = dict(row)
                    for key in list(data):
                        if key.endswith("_json"):
                            data[key[:-5]] = json_loads(data.pop(key), None)
                    return {"entity": entity, "data": data}
        raise KeyError("ID_NOT_FOUND")


def span_from_event(
    kind: str,
    name: str,
    started_at: str,
    ended_at: str,
    status: str,
    summary: str,
    parent_span_id: str | None = None,
) -> dict[str, Any]:
    duration = _duration_ms(started_at, ended_at) or 0
    return {
        "id": new_id("span"),
        "parent_span_id": parent_span_id,
        "kind": kind,
        "name": name,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_ms": duration,
        "status": status,
        "summary": summary,
    }

