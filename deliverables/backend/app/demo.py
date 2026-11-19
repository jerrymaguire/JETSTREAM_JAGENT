from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

from .db import connection, json_dumps, utc_now


SESSION_ID = "sess_demo_001"
RUN_ID = "run_demo_001"
GOAL_ID = "goal_demo_001"


def _iso(base: datetime, ms: int) -> str:
    return (base + timedelta(milliseconds=ms)).isoformat()


def seed_demo() -> None:
    with connection() as conn:
        marker = conn.execute("SELECT value FROM app_meta WHERE key = 'demo_seeded'").fetchone()
        if marker:
            return
        exists = conn.execute("SELECT 1 FROM sessions WHERE id = ?", (SESSION_ID,)).fetchone()
        if exists:
            now = utc_now()
            conn.execute(
                """
                INSERT OR IGNORE INTO providers
                (id, name, protocol, base_url, model, api_key_ciphertext, api_key_hint,
                 enabled, is_default, created_at, updated_at)
                VALUES ('provider_demo', 'Demo Agent', 'demo', '', 'demo', NULL, NULL, 1, 1, ?, ?)
                """,
                (now, now),
            )
            conn.execute(
                "INSERT OR REPLACE INTO app_meta (key, value) VALUES ('demo_seeded', '1')"
            )
            return

        base = datetime(2026, 11, 19, 8, 30, 0, tzinfo=UTC)
        created = _iso(base, 0)
        ended = _iso(base, 12_840)
        conn.execute(
            """
            INSERT INTO sessions
            (id, title, status, model_name, workspace_path, goal, created_at, updated_at)
            VALUES (?, ?, 'idle', 'DeepSeek Harness Demo', ?, ?, ?, ?)
            """,
            (
                SESSION_ID,
                "支付文档整理与回归检查",
                "D:\\wj\\projects\\AI\\GeekAgent\\Week5\\AgentShow\\workspace",
                "整理支付会话文档、FAQ 和历史问题，并完成一次回归检查。",
                created,
                ended,
            ),
        )

        messages = [
            ("msg_demo_01", "user", "梳理支付会话文档和 FAQ，保留历史问题作为背景材料。", 0),
            (
                "msg_demo_02",
                "assistant",
                "已完成目录扫描、文档读取和初版整理。发现支付接口说明和 FAQ 存在重复内容，已合并并写入支付会话文档。",
                4_510,
            ),
            ("msg_demo_03", "user", "再检查一次回归影响，并跑一下现有测试。", 4_600),
            (
                "msg_demo_04",
                "assistant",
                "回归检查完成：文档引用已修正，测试命令通过。历史问题被保留在单独章节，没有删除。",
                8_120,
            ),
            ("msg_demo_05", "user", "最后确认差异和验收项。", 8_300),
            (
                "msg_demo_06",
                "assistant",
                "最终检查完成。已覆盖支付文档、FAQ、历史问题、回归测试和变更摘要。失败的外部抓取已隔离，不影响本地交付。",
                10_420,
            ),
        ]
        for message_id, role, content, offset in messages:
            conn.execute(
                "INSERT INTO messages (id, session_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
                (message_id, SESSION_ID, role, content, _iso(base, offset)),
            )

        conn.execute(
            """
            INSERT INTO runs
            (id, session_id, goal_id, status, model_name, started_at, ended_at, stop_reason, usage_json)
            VALUES (?, ?, ?, 'completed', 'DeepSeek Harness Demo', ?, ?, 'completed', ?)
            """,
            (
                RUN_ID,
                SESSION_ID,
                GOAL_ID,
                created,
                ended,
                json_dumps({"input_tokens": 2140, "output_tokens": 486, "total_tokens": 2626}),
            ),
        )

        conn.execute(
            """
            INSERT INTO goals
            (id, session_id, objective, criteria_json, constraints_json, status,
             current_iteration, max_iterations, progress_summary, created_at, started_at, ended_at)
            VALUES (?, ?, ?, ?, ?, 'completed', 2, 5, ?, ?, ?, ?)
            """,
            (
                GOAL_ID,
                SESSION_ID,
                "整理支付会话文档、FAQ 和历史问题，并验证回归。",
                json_dumps(["文档合并", "FAQ 完整", "历史问题保留", "测试通过"]),
                json_dumps(["不删除历史资料", "不修改业务代码"]),
                "全部完成标准通过",
                created,
                created,
                ended,
            ),
        )

        span_specs = [
            ("span_demo_root", None, "run", "完整会话执行", 0, 12_840, "success", "支付文档整理与回归检查"),
            ("span_demo_llm_1", "span_demo_root", "llm", "规划整理步骤", 120, 1_350, "success", "扫描工作区并识别支付文档、FAQ 和历史材料"),
            ("span_demo_tool_1", "span_demo_root", "tool", "list_files", 1_350, 1_460, "success", "发现 14 个相关 Markdown 文件"),
            ("span_demo_tool_2", "span_demo_root", "tool", "read_file", 1_460, 1_600, "success", "读取 payment-session.md"),
            ("span_demo_tool_3", "span_demo_root", "tool", "search_code", 1_600, 1_820, "success", "定位 FAQ 和重复标题"),
            ("span_demo_llm_2", "span_demo_root", "llm", "合并文档", 1_820, 3_650, "success", "整理支付流程和常见问题"),
            ("span_demo_tool_4", "span_demo_root", "tool", "write_file", 3_650, 3_830, "success", "写入整理后的支付会话文档"),
            ("span_demo_llm_3", "span_demo_root", "llm", "生成第一轮回答", 3_830, 4_510, "success", "总结文档处理结果"),
            ("span_demo_tool_5", "span_demo_root", "tool", "git_diff", 4_600, 4_730, "success", "读取文档变更"),
            ("span_demo_llm_4", "span_demo_root", "llm", "回归审查", 4_730, 6_890, "success", "检查引用、历史问题和回归风险"),
            ("span_demo_tool_6", "span_demo_root", "tool", "run_test", 6_890, 7_350, "success", "命令退出码 0，12 个测试通过"),
            ("span_demo_llm_5", "span_demo_root", "llm", "生成回归回答", 7_350, 8_120, "success", "说明回归结果和保留内容"),
            ("span_demo_tool_7", "span_demo_root", "tool", "git_diff", 8_300, 8_460, "success", "读取最终差异"),
            ("span_demo_tool_8", "span_demo_root", "tool", "write_file", 8_460, 8_610, "success", "写入最终说明"),
            ("span_demo_llm_6", "span_demo_root", "llm", "最终验收", 8_610, 10_420, "success", "汇总完成标准"),
            ("span_demo_tool_9", "span_demo_root", "tool", "fetch_url", 10_600, 11_020, "error", "外部资料抓取失败，已隔离，不影响本地结果"),
        ]

        usage_by_span = {
            "span_demo_llm_1": {"total_tokens": 360},
            "span_demo_llm_2": {"total_tokens": 512},
            "span_demo_llm_3": {"total_tokens": 214},
            "span_demo_llm_4": {"total_tokens": 648},
            "span_demo_llm_5": {"total_tokens": 208},
            "span_demo_llm_6": {"total_tokens": 684},
        }

        for span_id, parent, kind, name, start_ms, end_ms, status, summary in span_specs:
            conn.execute(
                """
                INSERT INTO trace_spans
                (id, session_id, run_id, parent_span_id, kind, name, started_at, ended_at,
                 duration_ms, status, summary, input_json, output_json, error_json, usage_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    span_id,
                    SESSION_ID,
                    RUN_ID,
                    parent,
                    kind,
                    name,
                    _iso(base, start_ms),
                    _iso(base, end_ms),
                    end_ms - start_ms,
                    status,
                    summary,
                    json_dumps({"preview": summary}),
                    json_dumps({"preview": summary}),
                    json_dumps({"message": "外部资料不可达"}) if status == "error" else None,
                    json_dumps(usage_by_span.get(span_id)),
                ),
            )

        for index, (span_id, parent, kind, name, start_ms, end_ms, status, summary) in enumerate(span_specs, start=1):
            conn.execute(
                """
                INSERT INTO trace_events
                (id, session_id, run_id, seq, event_type, span_id, parent_span_id, created_at, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"evt_demo_{index:03d}",
                    SESSION_ID,
                    RUN_ID,
                    index,
                    f"{kind}.{'completed' if status == 'success' else 'failed'}",
                    span_id,
                    parent,
                    _iso(base, end_ms),
                    json_dumps({"name": name, "summary": summary, "status": status}),
                ),
            )

        tool_spans = [spec for spec in span_specs if spec[2] == "tool"]
        for index, (span_id, _parent, _kind, name, start_ms, end_ms, status, summary) in enumerate(tool_spans, start=1):
            args = {"tool": name, "path": "docs/payment-session.md"} if name != "run_test" else {"command": "pytest -q"}
            conn.execute(
                """
                INSERT INTO tool_calls
                (id, session_id, run_id, span_id, tool_name, args_json, args_digest, risk, status,
                 started_at, ended_at, duration_ms, result_summary, error_code)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'read', ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"tool_demo_{index:03d}",
                    SESSION_ID,
                    RUN_ID,
                    span_id,
                    name,
                    json_dumps(args),
                    hashlib.sha256(json_dumps(args).encode("utf-8")).hexdigest(),
                    status,
                    _iso(base, start_ms),
                    _iso(base, end_ms),
                    end_ms - start_ms,
                    summary,
                    "EXTERNAL_FETCH_FAILED" if status == "error" else None,
                ),
            )

        conn.execute(
            """
            INSERT INTO checkpoints
            (id, session_id, run_id, goal_id, goal_iteration_id, kind, pi_entry_id,
             last_event_seq, context_hash, workspace_snapshot_id, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'goal_iteration', ?, ?, ?, ?, 'completed', ?)
            """,
            (
                "ckpt_demo_001",
                SESSION_ID,
                RUN_ID,
                GOAL_ID,
                "iter_demo_001",
                "pi_entry_demo_001",
                16,
                hashlib.sha256(b"demo-context").hexdigest(),
                "snapshot_demo_001",
                ended,
            ),
        )

        now = utc_now()
        conn.execute(
            """
            INSERT INTO providers
            (id, name, protocol, base_url, model, api_key_ciphertext, api_key_hint,
             enabled, is_default, created_at, updated_at)
            VALUES ('provider_demo', 'Demo Agent', 'demo', '', 'demo', NULL, NULL, 1, 1, ?, ?)
            """,
            (now, now),
        )
        conn.execute(
            "INSERT OR REPLACE INTO app_meta (key, value) VALUES ('demo_seeded', '1')"
        )

