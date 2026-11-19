from __future__ import annotations

import asyncio
import json
from typing import Any

from .agent_manager import AgentManager
from .db import connection, json_dumps, new_id, utc_now
from .events import EventBroker
from .skills import build_skill_context


class GoalSupervisor:
    def __init__(self, agent: AgentManager, broker: EventBroker) -> None:
        self.agent = agent
        self.broker = broker
        self._tasks: dict[str, asyncio.Task[None]] = {}

    async def start(self, goal_id: str) -> None:
        existing = self._tasks.get(goal_id)
        if existing and not existing.done():
            return
        self._tasks[goal_id] = asyncio.create_task(self._run_goal(goal_id))

    async def _run_goal(self, goal_id: str) -> None:
        with connection() as conn:
            goal = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
        if not goal:
            return
        goal_data = dict(goal)
        if goal_data["status"] in {"cancelled", "completed"}:
            return
        now = utc_now()
        with connection() as conn:
            conn.execute(
                "UPDATE goals SET status = 'running', started_at = COALESCE(started_at, ?) WHERE id = ?",
                (now, goal_id),
            )
        await self.broker.publish(
            goal_data["session_id"],
            {"type": "goal.started", "session_id": goal_data["session_id"], "data": {"goal_id": goal_id}},
        )

        criteria = self._decode(goal_data["criteria_json"], [])
        constraints = self._decode(goal_data["constraints_json"], [])
        skills = self._decode(goal_data.get("skills_json"), [])
        max_iterations = int(goal_data["max_iterations"])
        start_iteration = int(goal_data["current_iteration"] or 0) + 1

        for iteration_no in range(start_iteration, max_iterations + 1):
            current = self._get_goal(goal_id)
            if current["status"] in {"paused", "cancelled"}:
                return
            iteration_id = new_id("iter")
            started_at = utc_now()
            with connection() as conn:
                conn.execute(
                    "UPDATE goals SET current_iteration = ?, status = 'running', progress_summary = ? WHERE id = ?",
                    (iteration_no, f"正在执行第 {iteration_no} 轮", goal_id),
                )
                conn.execute(
                    """
                    INSERT INTO goal_iterations
                    (id, goal_id, iteration_no, status, plan, started_at)
                    VALUES (?, ?, ?, 'running', ?, ?)
                    """,
                    (
                        iteration_id,
                        goal_id,
                        iteration_no,
                        f"检查目标并执行第 {iteration_no} 轮最有价值的工作",
                        started_at,
                    ),
                )
            await self.broker.publish(
                goal_data["session_id"],
                {
                    "type": "goal.iteration.started",
                    "session_id": goal_data["session_id"],
                    "data": {
                        "goal_id": goal_id,
                        "iteration_id": iteration_id,
                        "iteration_no": iteration_no,
                    },
                },
            )
            result = await self.agent.run_prompt(
                goal_data["session_id"],
                f"继续推进目标：{goal_data['objective']}",
                goal_id=goal_id,
                goal_mode=True,
                goal={
                    "objective": goal_data["objective"],
                    "criteria": criteria,
                    "constraints": constraints,
                    "iteration": iteration_no,
                },
                skill_context=build_skill_context(skills),
            )
            report = result.get("goal_report") or {}
            report_status = str(report.get("status", "in_progress"))
            summary = str(report.get("summary") or result.get("answer", ""))[:2000]
            remaining = report.get("remaining")
            ended_at = utc_now()
            with connection() as conn:
                conn.execute(
                    """
                    UPDATE goal_iterations
                    SET run_id = ?, status = ?, summary = ?, evidence_json = ?, ended_at = ?
                    WHERE id = ?
                    """,
                    (
                        result["run_id"],
                        report_status,
                        summary,
                        json_dumps({"answer": result.get("answer", ""), "remaining": remaining}),
                        ended_at,
                        iteration_id,
                    ),
                )
                checkpoint_id = new_id("ckpt")
                last_seq = conn.execute(
                    "SELECT COALESCE(MAX(seq), 0) FROM trace_events WHERE session_id = ?",
                    (goal_data["session_id"],),
                ).fetchone()[0]
                conn.execute(
                    """
                    INSERT INTO checkpoints
                    (id, session_id, run_id, goal_id, goal_iteration_id, kind,
                     pi_entry_id, last_event_seq, context_hash, workspace_snapshot_id, status, created_at)
                    VALUES (?, ?, ?, ?, ?, 'goal_iteration', NULL, ?, NULL, NULL, 'completed', ?)
                    """,
                    (
                        checkpoint_id,
                        goal_data["session_id"],
                        result["run_id"],
                        goal_id,
                        iteration_id,
                        int(last_seq),
                        ended_at,
                    ),
                )
            await self.broker.publish(
                goal_data["session_id"],
                {
                    "type": "goal.iteration.completed",
                    "session_id": goal_data["session_id"],
                    "data": {
                        "goal_id": goal_id,
                        "iteration_id": iteration_id,
                        "iteration_no": iteration_no,
                        "status": report_status,
                        "summary": summary,
                        "remaining": remaining,
                        "checkpoint_id": checkpoint_id,
                    },
                },
            )
            if report_status == "completed":
                await self._finish_goal(goal_id, "completed", summary)
                return
            if report_status == "blocked":
                await self._finish_goal(goal_id, "waiting_user", summary)
                return
            with connection() as conn:
                conn.execute(
                    "UPDATE goals SET progress_summary = ? WHERE id = ?",
                    (summary or f"第 {iteration_no} 轮完成，继续推进", goal_id),
                )
            await asyncio.sleep(0.2)

        await self._finish_goal(goal_id, "blocked", "达到最大迭代轮次，需要用户确认")

    async def _finish_goal(self, goal_id: str, status: str, summary: str) -> None:
        current = self._get_goal(goal_id)
        now = utc_now()
        with connection() as conn:
            conn.execute(
                "UPDATE goals SET status = ?, progress_summary = ?, ended_at = ? WHERE id = ?",
                (status, summary, now if status in {"completed", "blocked", "cancelled"} else None, goal_id),
            )
        await self.broker.publish(
            current["session_id"],
            {
                "type": f"goal.{status}",
                "session_id": current["session_id"],
                "data": {"goal_id": goal_id, "status": status, "summary": summary},
            },
        )

    def _get_goal(self, goal_id: str) -> dict[str, Any]:
        with connection() as conn:
            row = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
        if not row:
            raise KeyError("GOAL_NOT_FOUND")
        return dict(row)

    @staticmethod
    def _decode(value: str, default: Any) -> Any:
        try:
            return json.loads(value)
        except Exception:
            return default

