from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .db import connection, json_dumps, new_id, utc_now
from .events import EventBroker
from .trace_service import TraceService


ROOT = Path(__file__).resolve().parents[3]
AGENT_HOST_DIR = ROOT / "deliverables" / "agent-host"


@dataclass
class RunState:
    session_id: str
    run_id: str
    goal_id: str | None
    root_span_id: str
    future: asyncio.Future[dict[str, Any]]
    answer_parts: list[str] = field(default_factory=list)
    current_model_span: str | None = None
    tool_spans: dict[str, str] = field(default_factory=dict)
    tool_starts: dict[str, str] = field(default_factory=dict)
    goal_report: dict[str, Any] | None = None


@dataclass
class AgentProcess:
    process: asyncio.subprocess.Process
    stdout_task: asyncio.Task[None]
    stderr_task: asyncio.Task[None]
    ready: asyncio.Event


class AgentManager:
    def __init__(self, broker: EventBroker, trace: TraceService) -> None:
        self.broker = broker
        self.trace = trace
        self._processes: dict[str, AgentProcess] = {}
        self._runs: dict[str, RunState] = {}
        self._write_locks: dict[str, asyncio.Lock] = {}

    def _session(self, session_id: str) -> dict[str, Any]:
        with connection() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not row:
            raise KeyError("SESSION_NOT_FOUND")
        return dict(row)

    def _provider_protocol(self) -> str:
        with connection() as conn:
            row = conn.execute(
                "SELECT protocol FROM providers WHERE enabled = 1 ORDER BY is_default DESC, created_at LIMIT 1"
            ).fetchone()
        return row["protocol"] if row else "demo"

    async def warmup(self, session_id: str) -> dict[str, Any]:
        session = self._session(session_id)
        if self._provider_protocol() == "demo":
            return {"warmed": False, "mode": "demo"}
        process = await self._ensure_process(session_id, session["workspace_path"])
        await asyncio.wait_for(process.ready.wait(), timeout=15)
        return {"warmed": True, "mode": "pi"}

    async def run_prompt(
        self,
        session_id: str,
        message: str,
        *,
        goal_id: str | None = None,
        goal_mode: bool = False,
        goal: dict[str, Any] | None = None,
        skill_context: str | None = None,
    ) -> dict[str, Any]:
        session = self._session(session_id)
        run_id = new_id("run")
        started_at = utc_now()
        model_name = session["model_name"]
        with connection() as conn:
            conn.execute(
                """
                INSERT INTO runs (id, session_id, goal_id, status, model_name, started_at)
                VALUES (?, ?, ?, 'running', ?, ?)
                """,
                (run_id, session_id, goal_id, model_name, started_at),
            )
            conn.execute(
                "UPDATE sessions SET status = 'running', updated_at = ? WHERE id = ?",
                (started_at, session_id),
            )

        root_span = await self.trace.start_span(
            session_id,
            run_id,
            "run",
            "Agent Run",
            "正在执行 Agent",
            input_data={"message": message[:1000], "goal_mode": goal_mode},
        )
        future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        state = RunState(session_id, run_id, goal_id, root_span, future)
        self._runs[run_id] = state

        if self._provider_protocol() == "demo":
            asyncio.create_task(self._run_demo(state, message, goal_mode=goal_mode, goal=goal))
        else:
            try:
                process = await self._ensure_process(session_id, session["workspace_path"])
                await process.ready.wait()
                lock = self._write_locks.setdefault(session_id, asyncio.Lock())
                async with lock:
                    assert process.process.stdin is not None
                    command = {
                        "type": "prompt",
                        "run_id": run_id,
                        "message": message,
                        "goal_mode": goal_mode,
                        "goal": goal,
                        "skill_context": skill_context,
                    }
                    process.process.stdin.write((json.dumps(command, ensure_ascii=False) + "\n").encode("utf-8"))
                    await process.process.stdin.drain()
            except Exception as exc:
                await self._fail_run(state, f"Pi Agent 启动失败: {exc}")

        return await future

    async def _run_demo(
        self,
        state: RunState,
        message: str,
        *,
        goal_mode: bool,
        goal: dict[str, Any] | None,
    ) -> None:
        model_span = await self.trace.start_span(
            state.session_id,
            state.run_id,
            "llm",
            "Demo 模型调用",
            "生成演示回答",
            parent_span_id=state.root_span_id,
            input_data={"message": message},
        )
        await asyncio.sleep(0.02)
        objective = goal.get("objective") if goal else None
        answer = (
            f"已收到：{message[:200]}。"
            "这是 Demo Agent 的运行结果。配置真实 API Key 后，Agent Host 会切换到 Pi 工具循环。"
        )
        if goal_mode and objective:
            answer = (
                f"目标“{objective}”已在 Demo 模式完成一次演示迭代。"
                "当前没有真实模型和工具执行，因此在真实模式下应继续验证完成标准。"
            )
        for start in range(0, len(answer), 12):
            delta = answer[start : start + 12]
            state.answer_parts.append(delta)
            await self.broker.publish(
                state.session_id,
                {
                    "type": "assistant.delta",
                    "session_id": state.session_id,
                    "run_id": state.run_id,
                    "delta": delta,
                },
            )
            await asyncio.sleep(0.02)
        await self.trace.finish_span(
            state.session_id,
            state.run_id,
            model_span,
            "success",
            "Demo 模型回答完成",
            usage={"total_tokens": 128},
        )
        if goal_mode:
            state.goal_report = {
                "status": "completed",
                "summary": "Demo 模式已完成一轮演示",
                "remaining": "真实模式需要运行完成标准",
            }
        await self._complete_run(state, answer, "completed")

    async def _ensure_process(self, session_id: str, workspace_path: str) -> AgentProcess:
        existing = self._processes.get(session_id)
        if existing and existing.process.returncode is None:
            return existing

        host_entry = AGENT_HOST_DIR / "dist" / "host.js"
        if not host_entry.exists():
            raise RuntimeError("Agent Host 未构建，请先运行 npm run build")
        env = dict(os.environ)
        env.update(
            {
                "AGENTSHOW_WORKSPACE": workspace_path,
                "AGENTSHOW_INTERNAL_BASE_URL": os.getenv(
                    "AGENTSHOW_INTERNAL_LLM_URL", "http://127.0.0.1:8000/internal/llm/v1"
                ),
                "AGENTSHOW_SERVICE_TOKEN": os.getenv("AGENTSHOW_SERVICE_TOKEN", ""),
                "AGENTSHOW_MODEL_ALIAS": "agentshow",
            }
        )
        process = await asyncio.create_subprocess_exec(
            "node",
            str(host_entry),
            cwd=str(AGENT_HOST_DIR),
            env=env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        ready = asyncio.Event()
        stdout_task = asyncio.create_task(self._read_stdout(session_id, process, ready))
        stderr_task = asyncio.create_task(self._read_stderr(process))
        wrapped = AgentProcess(process, stdout_task, stderr_task, ready)
        self._processes[session_id] = wrapped
        return wrapped

    async def _read_stdout(
        self,
        session_id: str,
        process: asyncio.subprocess.Process,
        ready: asyncio.Event,
    ) -> None:
        assert process.stdout is not None
        while line := await process.stdout.readline():
            raw = line.decode("utf-8", errors="replace").strip()
            if not raw:
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "host_ready":
                ready.set()
                continue
            run_id = event.get("run_id")
            state = self._runs.get(run_id)
            if not state:
                continue
            await self._handle_host_event(state, event)

    async def _read_stderr(self, process: asyncio.subprocess.Process) -> None:
        assert process.stderr is not None
        while line := await process.stderr.readline():
            text = line.decode("utf-8", errors="replace").strip()
            if text:
                print(f"[agent-host] {text}", file=sys.stderr)

    async def _handle_host_event(self, state: RunState, event: dict[str, Any]) -> None:
        event_type = event.get("type")
        data = event.get("data") or {}
        if event_type == "assistant_delta":
            delta = str(event.get("delta", ""))
            if delta:
                state.answer_parts.append(delta)
                await self.broker.publish(
                    state.session_id,
                    {
                        "type": "assistant.delta",
                        "session_id": state.session_id,
                        "run_id": state.run_id,
                        "delta": delta,
                    },
                )
        elif event_type == "model_started":
            state.current_model_span = await self.trace.start_span(
                state.session_id,
                state.run_id,
                "llm",
                "模型调用",
                "等待模型返回",
                parent_span_id=state.root_span_id,
            )
        elif event_type == "model_completed" and state.current_model_span:
            raw_usage = data.get("usage") or {}
            usage = {
                "input_tokens": raw_usage.get("input", 0),
                "output_tokens": raw_usage.get("output", 0),
                "reasoning_tokens": raw_usage.get("reasoning", 0),
                "total_tokens": raw_usage.get("totalTokens")
                or (
                    int(raw_usage.get("input", 0) or 0)
                    + int(raw_usage.get("output", 0) or 0)
                ),
            }
            await self.trace.finish_span(
                state.session_id,
                state.run_id,
                state.current_model_span,
                "success",
                "模型调用完成",
                usage=usage,
            )
            state.current_model_span = None
        elif event_type == "tool_execution_start":
            tool_id = str(data.get("tool_call_id", new_id("call")))
            span_id = await self.trace.start_span(
                state.session_id,
                state.run_id,
                "tool",
                str(data.get("tool_name", "tool")),
                f"调用 {data.get('tool_name', 'tool')}",
                parent_span_id=state.root_span_id,
                input_data=data.get("args"),
            )
            state.tool_spans[tool_id] = span_id
            state.tool_starts[tool_id] = utc_now()
        elif event_type == "tool_execution_end":
            tool_id = str(data.get("tool_call_id", ""))
            span_id = state.tool_spans.get(tool_id)
            status = "error" if data.get("is_error") else "success"
            result = str(data.get("result", ""))
            if span_id:
                await self.trace.finish_span(
                    state.session_id,
                    state.run_id,
                    span_id,
                    status,
                    result[:500] or str(data.get("tool_name", "工具执行完成")),
                    output_data=result,
                    error={"message": result} if status == "error" else None,
                )
                await self.trace.record_tool_call(
                    state.session_id,
                    state.run_id,
                    span_id,
                    str(data.get("tool_name", "tool")),
                    data.get("args") or {},
                    result,
                    status=status,
                    error_code="TOOL_ERROR" if status == "error" else None,
                    started_at=state.tool_starts.get(tool_id),
                    ended_at=utc_now(),
                )
        elif event_type == "goal_report":
            state.goal_report = data
            await self.trace.event(
                state.session_id,
                state.run_id,
                "goal.iteration.reported",
                data,
                span_id=state.root_span_id,
            )
        elif event_type == "run_completed":
            await self._complete_run(
                state,
                str(data.get("answer", "".join(state.answer_parts))),
                str(data.get("stop_reason", "completed")),
            )
        elif event_type == "run_failed":
            await self._fail_run(state, str(data.get("message", "Agent Run 失败")))

    async def _complete_run(
        self,
        state: RunState,
        answer: str,
        stop_reason: str,
    ) -> None:
        if state.future.done():
            return
        now = utc_now()
        answer = answer or "".join(state.answer_parts)
        await self.trace.finish_span(
            state.session_id,
            state.run_id,
            state.root_span_id,
            "success" if stop_reason not in {"error", "aborted"} else "error",
            "Agent Run 完成" if stop_reason != "error" else "Agent Run 失败",
            usage={"total_tokens": max(120, len(answer) // 3)},
        )
        with connection() as conn:
            conn.execute(
                "UPDATE runs SET status = 'completed', ended_at = ?, stop_reason = ? WHERE id = ?",
                (now, stop_reason, state.run_id),
            )
            conn.execute(
                "UPDATE sessions SET status = 'idle', updated_at = ? WHERE id = ?",
                (now, state.session_id),
            )
            if answer:
                conn.execute(
                    "INSERT INTO messages (id, session_id, role, content, created_at) VALUES (?, ?, 'assistant', ?, ?)",
                    (new_id("msg"), state.session_id, answer, now),
                )
            checkpoint_id = new_id("ckpt")
            last_seq = conn.execute(
                "SELECT COALESCE(MAX(seq), 0) FROM trace_events WHERE session_id = ?",
                (state.session_id,),
            ).fetchone()[0]
            conn.execute(
                """
                INSERT INTO checkpoints
                (id, session_id, run_id, goal_id, goal_iteration_id, kind, pi_entry_id,
                 last_event_seq, context_hash, workspace_snapshot_id, status, created_at)
                VALUES (?, ?, ?, ?, NULL, 'run', NULL, ?, NULL, NULL, 'completed', ?)
                """,
                (checkpoint_id, state.session_id, state.run_id, state.goal_id, int(last_seq), now),
            )
        await self.broker.publish(
            state.session_id,
            {
                "type": "run.completed",
                "session_id": state.session_id,
                "run_id": state.run_id,
                "data": {
                    "answer": answer,
                    "stop_reason": stop_reason,
                    "goal_report": state.goal_report,
                    "checkpoint_id": checkpoint_id,
                },
            },
        )
        state.future.set_result(
            {
                "run_id": state.run_id,
                "answer": answer,
                "goal_report": state.goal_report,
                "stop_reason": stop_reason,
            }
        )
        self._runs.pop(state.run_id, None)

    async def _fail_run(self, state: RunState, message: str) -> None:
        if state.future.done():
            return
        now = utc_now()
        await self.trace.finish_span(
            state.session_id,
            state.run_id,
            state.root_span_id,
            "error",
            message[:500],
            error={"message": message},
        )
        with connection() as conn:
            conn.execute(
                "UPDATE runs SET status = 'failed', ended_at = ?, stop_reason = ? WHERE id = ?",
                (now, message[:500], state.run_id),
            )
            conn.execute(
                "UPDATE sessions SET status = 'idle', updated_at = ? WHERE id = ?",
                (now, state.session_id),
            )
        await self.broker.publish(
            state.session_id,
            {
                "type": "run.failed",
                "session_id": state.session_id,
                "run_id": state.run_id,
                "data": {"message": message},
            },
        )
        state.future.set_result(
            {
                "run_id": state.run_id,
                "answer": "",
                "goal_report": None,
                "stop_reason": "error",
                "error": message,
            }
        )
        self._runs.pop(state.run_id, None)

    async def shutdown(self) -> None:
        for process in self._processes.values():
            if process.process.returncode is None:
                process.process.terminate()
        for process in self._processes.values():
            await asyncio.gather(process.stdout_task, process.stderr_task, return_exceptions=True)
        self._processes.clear()

