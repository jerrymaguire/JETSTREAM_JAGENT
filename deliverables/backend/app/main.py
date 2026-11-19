from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import (
    FastAPI,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .agent_manager import AgentManager
from .db import (
    connection,
    init_db,
    json_dumps,
    json_loads,
    new_id,
    utc_now,
)
from .demo import seed_demo
from .events import EventBroker
from .goal_supervisor import GoalSupervisor
from .llm_gateway import demo_stream, provider_public, proxy_chat_completion
from .schemas import (
    CheckpointCreate,
    CredentialUpdate,
    DocumentExportRequest,
    GoalCreate,
    MessageCreate,
    ProviderCreate,
    SessionCreate,
    SkillPathRequest,
    SkillToggleRequest,
)
from .documents import (
    attachment_context,
    export_docx,
    export_markdown,
    export_pdf,
    extract_document,
)
from .security import decrypt_secret, encrypt_secret, mask_secret
from .skills import (
    add_skill_root,
    build_skill_context,
    discover_skills,
    set_skill_enabled,
    skill_content,
)
from .trace_service import TraceService


ROOT = Path(__file__).resolve().parents[3]
FRONTEND_DIST = ROOT / "deliverables" / "frontend" / "dist"
DEFAULT_WORKSPACE = ROOT / "workspace"
DEFAULT_WORKSPACE.mkdir(parents=True, exist_ok=True)

broker = EventBroker()
trace = TraceService(broker)
agent_manager = AgentManager(broker, trace)
goal_supervisor = GoalSupervisor(agent_manager, broker)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    seed_demo()
    if not os.getenv("AGENTSHOW_SERVICE_TOKEN"):
        os.environ["AGENTSHOW_SERVICE_TOKEN"] = secrets.token_urlsafe(32)
    yield
    await agent_manager.shutdown()


app = FastAPI(title="JAgent API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _session_row(session_id: str) -> dict[str, Any]:
    with connection() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    return dict(row)


def _messages(session_id: str) -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at",
            (session_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def _goals(session_id: str) -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM goals WHERE session_id = ? ORDER BY created_at DESC",
            (session_id,),
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["criteria"] = json_loads(item.pop("criteria_json"), [])
        item["constraints"] = json_loads(item.pop("constraints_json"), [])
        item["skills"] = json_loads(item.pop("skills_json", None), [])
        result.append(item)
    return result


def _session_list() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM sessions ORDER BY updated_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def derive_session_title(text: str, max_length: int = 28) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    normalized = re.sub(
        r"^(请帮我|帮我|帮忙|请|目标是|目标[:：]?|希望)[:：\s]*",
        "",
        normalized,
    )
    normalized = normalized.split("\n", 1)[0].strip("。；;，,：: ")
    if len(normalized) > max_length:
        normalized = f"{normalized[:max_length].rstrip()}..."
    return normalized or "新对话"


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "jagent-api",
        "time": utc_now(),
        "agent_host": "ready",
    }


@app.get("/api/providers")
async def providers() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute("SELECT * FROM providers ORDER BY is_default DESC, created_at").fetchall()
    return [provider_public(dict(row)) for row in rows]


@app.get("/api/skills")
async def list_skills() -> list[dict[str, Any]]:
    return discover_skills()


@app.post("/api/skills/scan")
async def scan_skills() -> list[dict[str, Any]]:
    return discover_skills()


@app.post("/api/skills/add-path")
async def add_skill_path(payload: SkillPathRequest) -> dict[str, Any]:
    try:
        return add_skill_root(payload.path)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/skills/{skill_id}")
async def get_skill(skill_id: str) -> dict[str, Any]:
    try:
        return skill_content(skill_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Skill not found") from exc


@app.patch("/api/skills/{skill_id}")
async def toggle_skill(skill_id: str, payload: SkillToggleRequest) -> dict[str, Any]:
    if not any(item["id"] == skill_id for item in discover_skills()):
        raise HTTPException(status_code=404, detail="Skill not found")
    set_skill_enabled(skill_id, payload.enabled)
    return next(item for item in discover_skills() if item["id"] == skill_id)


@app.post("/api/documents/extract")
async def extract_uploaded_document(file: UploadFile = File(...)) -> dict[str, Any]:
    try:
        data = await file.read()
        attachment = extract_document(file.filename or "document", data)
        return attachment.model_dump()
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/documents/export")
async def export_document(payload: DocumentExportRequest) -> Response:
    if payload.format == "docx":
        content = export_docx(payload.title, payload.content)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        extension = "docx"
    elif payload.format == "pdf":
        content = export_pdf(payload.title, payload.content)
        media_type = "application/pdf"
        extension = "pdf"
    else:
        content = export_markdown(payload.title, payload.content)
        media_type = "text/markdown; charset=utf-8"
        extension = "md"
    filename = quote(f"{payload.title[:60]}.{extension}")
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@app.post("/api/providers")
async def create_provider(payload: ProviderCreate) -> dict[str, Any]:
    provider_id = new_id("provider")
    now = utc_now()
    ciphertext = encrypt_secret(payload.api_key) if payload.api_key else None
    hint = mask_secret(payload.api_key) if payload.api_key else None
    with connection() as conn:
        if payload.is_default:
            conn.execute("UPDATE providers SET is_default = 0")
        conn.execute(
            """
            INSERT INTO providers
            (id, name, protocol, base_url, model, api_key_ciphertext, api_key_hint,
             enabled, is_default, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
            """,
            (
                provider_id,
                payload.name,
                payload.protocol,
                payload.base_url.rstrip("/"),
                payload.model,
                ciphertext,
                hint,
                1 if payload.is_default else 0,
                now,
                now,
            ),
        )
        row = conn.execute("SELECT * FROM providers WHERE id = ?", (provider_id,)).fetchone()
    return provider_public(dict(row))


@app.put("/api/providers/{provider_id}/credential")
async def save_credential(provider_id: str, payload: CredentialUpdate) -> dict[str, Any]:
    now = utc_now()
    ciphertext = encrypt_secret(payload.api_key)
    hint = mask_secret(payload.api_key)
    with connection() as conn:
        cursor = conn.execute(
            """
            UPDATE providers
            SET api_key_ciphertext = ?, api_key_hint = ?, updated_at = ?
            WHERE id = ?
            """,
            (ciphertext, hint, now, provider_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Provider not found")
        row = conn.execute("SELECT * FROM providers WHERE id = ?", (provider_id,)).fetchone()
    return provider_public(dict(row))


@app.delete("/api/providers/{provider_id}/credential")
async def delete_credential(provider_id: str) -> dict[str, Any]:
    with connection() as conn:
        conn.execute(
            "UPDATE providers SET api_key_ciphertext = NULL, api_key_hint = NULL, updated_at = ? WHERE id = ?",
            (utc_now(), provider_id),
        )
    return {"ok": True}


@app.delete("/api/providers/{provider_id}")
async def delete_provider(provider_id: str) -> dict[str, Any]:
    with connection() as conn:
        row = conn.execute("SELECT protocol FROM providers WHERE id = ?", (provider_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Provider not found")
        if row["protocol"] == "demo":
            raise HTTPException(status_code=409, detail="Demo Provider 不能删除")
        conn.execute("DELETE FROM providers WHERE id = ?", (provider_id,))
        conn.execute(
            "UPDATE providers SET is_default = 1 WHERE id = 'provider_demo'"
        )
    return {"ok": True}


@app.post("/api/providers/{provider_id}/test")
async def test_provider(provider_id: str) -> dict[str, Any]:
    with connection() as conn:
        row = conn.execute("SELECT * FROM providers WHERE id = ?", (provider_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Provider not found")
    provider = dict(row)
    if provider["protocol"] == "demo":
        return {"ok": True, "message": "Demo Provider 可用", "model": provider["model"]}
    key = decrypt_secret(provider["api_key_ciphertext"])
    if not key:
        raise HTTPException(status_code=409, detail="未配置 API Key")
    url = provider["base_url"].rstrip("/")
    url = url if url.endswith("/chat/completions") else f"{url}/chat/completions"
    body = {
        "model": provider["model"],
        "messages": [{"role": "user", "content": "Reply with OK"}],
        "max_tokens": 8,
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                content=json.dumps(body).encode("utf-8"),
            )
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=response.text[:1500])
        return {"ok": True, "message": "连接成功", "model": provider["model"]}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"连接失败: {exc}") from exc


@app.get("/api/sessions")
async def list_sessions() -> list[dict[str, Any]]:
    return _session_list()


@app.post("/api/sessions")
async def create_session(payload: SessionCreate) -> dict[str, Any]:
    session_id = new_id("sess")
    now = utc_now()
    workspace = payload.workspace_path or str(DEFAULT_WORKSPACE)
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO sessions
            (id, title, status, model_name, workspace_path, goal, created_at, updated_at)
            VALUES (?, ?, 'idle', ?, ?, NULL, ?, ?)
            """,
            (session_id, payload.title, payload.model_name, workspace, now, now),
        )
    return _session_row(session_id)


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str) -> dict[str, Any]:
    session = _session_row(session_id)
    return {
        **session,
        "messages": _messages(session_id),
        "goals": _goals(session_id),
    }


@app.patch("/api/sessions/{session_id}")
async def update_session(session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    title = str(payload.get("title") or "").strip()
    if title:
        with connection() as conn:
            conn.execute(
                "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
                (title, utc_now(), session_id),
            )
    return _session_row(session_id)


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str) -> dict[str, Any]:
    with connection() as conn:
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    return {"ok": True}


@app.post("/api/sessions/{session_id}/messages")
async def send_message(session_id: str, payload: MessageCreate) -> dict[str, Any]:
    session = _session_row(session_id)
    if session["status"] == "running":
        raise HTTPException(status_code=409, detail="当前会话已有运行中的 Agent")
    now = utc_now()
    message_id = new_id("msg")
    display_content = payload.content
    if payload.attachments:
        display_content += "\n\n附件：" + "、".join(item.name for item in payload.attachments)
    contexts = [
        build_skill_context(payload.skills),
        attachment_context(payload.attachments),
    ]
    agent_context = "\n\n".join(item for item in contexts if item)
    with connection() as conn:
        conn.execute(
            "INSERT INTO messages (id, session_id, role, content, created_at) VALUES (?, ?, 'user', ?, ?)",
            (message_id, session_id, display_content, now),
        )
        title = session["title"]
        if title in {"新对话", "未命名对话", ""}:
            title = derive_session_title(payload.content)
        conn.execute(
            "UPDATE sessions SET title = ?, updated_at = ?, status = 'running' WHERE id = ?",
            (title, now, session_id),
        )
    await broker.publish(
        session_id,
        {
            "type": "session.updated",
            "session_id": session_id,
            "data": {"title": title},
        },
    )
    asyncio.create_task(
        agent_manager.run_prompt(
            session_id,
            payload.content,
            skill_context=agent_context or None,
        )
    )
    await broker.publish(
        session_id,
        {
            "type": "message.started",
            "session_id": session_id,
            "data": {"message_id": message_id, "role": "user", "content": display_content},
        },
    )
    return {"accepted": True, "session_id": session_id}


@app.post("/api/sessions/{session_id}/warmup")
async def warmup_session(session_id: str) -> dict[str, Any]:
    _session_row(session_id)
    try:
        return await agent_manager.warmup(session_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Agent warmup failed: {exc}") from exc


@app.get("/api/sessions/{session_id}/trace")
async def get_trace(session_id: str) -> dict[str, Any]:
    try:
        return trace.get_trace(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Session not found") from exc


@app.get("/api/traces/{run_id}")
async def get_run_trace(run_id: str) -> dict[str, Any]:
    with connection() as conn:
        run = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        spans = [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM trace_spans WHERE run_id = ? ORDER BY started_at", (run_id,)
            ).fetchall()
        ]
    return {"run": dict(run), "spans": spans}


@app.get("/api/sessions/{session_id}/events")
async def get_events(session_id: str, after_seq: int = 0) -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM trace_events WHERE session_id = ? AND seq > ? ORDER BY seq LIMIT 5000",
            (session_id, after_seq),
        ).fetchall()
    return [
        {
            "seq": row["seq"],
            "event_id": row["id"],
            "session_id": row["session_id"],
            "run_id": row["run_id"],
            "event": row["event_type"],
            "span_id": row["span_id"],
            "timestamp": row["created_at"],
            "data": json_loads(row["payload_json"], {}),
        }
        for row in rows
    ]


@app.get("/api/lookup/{identifier}")
async def lookup(identifier: str) -> dict[str, Any]:
    try:
        return trace.lookup(identifier)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="ID not found") from exc


@app.get("/api/sessions/{session_id}/checkpoints")
async def list_checkpoints(session_id: str) -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM checkpoints WHERE session_id = ? ORDER BY created_at DESC",
            (session_id,),
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/sessions/{session_id}/checkpoints")
async def create_checkpoint(session_id: str, payload: CheckpointCreate) -> dict[str, Any]:
    checkpoint_id = new_id("ckpt")
    with connection() as conn:
        last_seq = conn.execute(
            "SELECT COALESCE(MAX(seq), 0) FROM trace_events WHERE session_id = ?",
            (session_id,),
        ).fetchone()[0]
        conn.execute(
            """
            INSERT INTO checkpoints
            (id, session_id, run_id, goal_id, goal_iteration_id, kind, pi_entry_id,
             last_event_seq, context_hash, workspace_snapshot_id, status, created_at)
            VALUES (?, ?, ?, NULL, NULL, ?, ?, ?, ?, ?, 'ready', ?)
            """,
            (
                checkpoint_id,
                session_id,
                payload.run_id,
                payload.kind,
                payload.pi_entry_id,
                payload.last_event_seq or int(last_seq),
                payload.context_hash,
                payload.workspace_snapshot_id,
                utc_now(),
            ),
        )
    await broker.publish(
        session_id,
        {"type": "checkpoint.created", "session_id": session_id, "data": {"checkpoint_id": checkpoint_id}},
    )
    return {"id": checkpoint_id, "kind": payload.kind, "status": "ready"}


@app.post("/api/sessions/{session_id}/goals")
async def create_goal(session_id: str, payload: GoalCreate) -> dict[str, Any]:
    session = _session_row(session_id)
    with connection() as conn:
        active = conn.execute(
            """
            SELECT id FROM goals
            WHERE session_id = ? AND status NOT IN ('completed','cancelled','blocked')
            LIMIT 1
            """,
            (session_id,),
        ).fetchone()
    if active:
        raise HTTPException(status_code=409, detail="当前会话已有进行中的目标")
    goal_id = new_id("goal")
    now = utc_now()
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO goals
            (id, session_id, objective, criteria_json, constraints_json, skills_json, status,
             current_iteration, max_iterations, progress_summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'draft', 0, ?, '等待启动', ?)
            """,
            (
                goal_id,
                session_id,
                payload.objective,
                json_dumps(payload.criteria),
                json_dumps(payload.constraints),
                json_dumps(payload.skills),
                payload.max_iterations,
                now,
            ),
        )
        conn.execute(
            "UPDATE sessions SET goal = ?, updated_at = ? WHERE id = ?",
            (payload.objective, now, session_id),
        )
        title = session["title"]
        if title in {"新对话", "未命名对话", ""}:
            title = derive_session_title(payload.objective)
            conn.execute(
                "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
                (title, now, session_id),
            )
    await broker.publish(
        session_id,
        {
            "type": "session.updated",
            "session_id": session_id,
            "data": {"title": title if "title" in locals() else session["title"]},
        },
    )
    if payload.auto_start:
        await goal_supervisor.start(goal_id)
    return {"id": goal_id, "status": "draft" if not payload.auto_start else "running"}


@app.get("/api/sessions/{session_id}/goals")
async def get_goals(session_id: str) -> list[dict[str, Any]]:
    goals = _goals(session_id)
    with connection() as conn:
        for goal in goals:
            rows = conn.execute(
                "SELECT * FROM goal_iterations WHERE goal_id = ? ORDER BY iteration_no",
                (goal["id"],),
            ).fetchall()
            goal["iterations"] = [dict(row) for row in rows]
    return goals


@app.post("/api/goals/{goal_id}/start")
async def start_goal(goal_id: str) -> dict[str, Any]:
    with connection() as conn:
        row = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Goal not found")
        conn.execute("UPDATE goals SET status = 'planning' WHERE id = ?", (goal_id,))
    await goal_supervisor.start(goal_id)
    return {"ok": True, "goal_id": goal_id}


@app.post("/api/goals/{goal_id}/pause")
async def pause_goal(goal_id: str) -> dict[str, Any]:
    with connection() as conn:
        row = conn.execute("SELECT session_id FROM goals WHERE id = ?", (goal_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Goal not found")
        conn.execute("UPDATE goals SET status = 'paused' WHERE id = ?", (goal_id,))
    await broker.publish(
        row["session_id"],
        {"type": "goal.paused", "session_id": row["session_id"], "data": {"goal_id": goal_id}},
    )
    return {"ok": True}


@app.post("/api/goals/{goal_id}/cancel")
async def cancel_goal(goal_id: str) -> dict[str, Any]:
    with connection() as conn:
        row = conn.execute("SELECT session_id FROM goals WHERE id = ?", (goal_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Goal not found")
        conn.execute(
            "UPDATE goals SET status = 'cancelled', ended_at = ? WHERE id = ?",
            (utc_now(), goal_id),
        )
    await broker.publish(
        row["session_id"],
        {"type": "goal.cancelled", "session_id": row["session_id"], "data": {"goal_id": goal_id}},
    )
    return {"ok": True}


@app.post("/api/goals/{goal_id}/resume")
async def resume_goal(goal_id: str) -> dict[str, Any]:
    with connection() as conn:
        row = conn.execute("SELECT status FROM goals WHERE id = ?", (goal_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Goal not found")
        conn.execute("UPDATE goals SET status = 'running' WHERE id = ?", (goal_id,))
    await goal_supervisor.start(goal_id)
    return {"ok": True}


@app.websocket("/api/ws/sessions/{session_id}")
async def websocket_events(websocket: WebSocket, session_id: str, after_seq: int = 0) -> None:
    await websocket.accept()
    queue = broker.subscribe(session_id)
    try:
        replay = await get_events(session_id, after_seq)
        for event in replay:
            await websocket.send_json({"type": "trace.event", **event})
        while True:
            payload = await queue.get()
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        pass
    finally:
        broker.unsubscribe(session_id, queue)


@app.post("/internal/llm/v1/chat/completions")
async def internal_chat_completions(http_request: Request, body: dict[str, Any]):
    return StreamingResponse(
        proxy_chat_completion(body, http_request.headers.get("authorization")),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/internal/llm/v1/models")
async def internal_models() -> dict[str, Any]:
    return {"data": [{"id": "agentshow", "object": "model"}]}


if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/")
    async def frontend_index() -> FileResponse:
        return FileResponse(FRONTEND_DIST / "index.html")

    @app.get("/{path:path}")
    async def frontend_fallback(path: str) -> FileResponse:
        candidate = FRONTEND_DIST / path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")

