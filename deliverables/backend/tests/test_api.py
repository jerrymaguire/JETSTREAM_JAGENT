from __future__ import annotations

import asyncio
import io
import os
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient


TEST_DIR = tempfile.mkdtemp(prefix="agentshow-test-")
os.environ["AGENTSHOW_DATA_DIR"] = TEST_DIR
os.environ["AGENTSHOW_SERVICE_TOKEN"] = "test-service-token"

from app.main import agent_manager, app  # noqa: E402
from app.events import EventBroker  # noqa: E402
from app.db import json_dumps, json_loads, row_to_dict  # noqa: E402
from app.llm_gateway import _chat_url  # noqa: E402
import pytest  # noqa: E402
from app.skills import build_skill_context  # noqa: E402
from docx import Document  # noqa: E402
from app.security import decrypt_secret, encrypt_secret, mask_secret  # noqa: E402


def wait_until(predicate, timeout: float = 8.0, interval: float = 0.1):
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    raise AssertionError("condition was not met before timeout")


def test_health_and_demo_trace() -> None:
    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["ok"] is True

        trace = client.get("/api/sessions/sess_demo_001/trace")
        assert trace.status_code == 200
        payload = trace.json()
        assert payload["summary"]["total_duration_ms"] == 12_840
        assert payload["summary"]["round_count"] == 3
        assert payload["summary"]["call_count"] == 16
        assert len(payload["spans"]) == 16


def test_id_lookup() -> None:
    with TestClient(app) as client:
        response = client.get("/api/lookup/span_demo_tool_3")
        assert response.status_code == 200
        data = response.json()
        assert data["entity"] == "span"
        assert data["data"]["name"] == "search_code"


def test_provider_key_is_masked() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/api/providers",
            json={
                "name": "Test Provider",
                "protocol": "openai-compatible",
                "base_url": "https://example.com/v1",
                "model": "test-model",
                "api_key": "sk-test-secret-value",
                "is_default": False,
            },
        )
        assert created.status_code == 200
        body = created.json()
        assert body["api_key_set"] is True
        assert body["api_key_hint"] == "sk-...alue"
        assert "sk-test-secret-value" not in str(body)


def test_session_create_and_messages() -> None:
    with TestClient(app) as client:
        created = client.post("/api/sessions", json={"title": "测试会话"})
        assert created.status_code == 200
        session_id = created.json()["id"]
        detail = client.get(f"/api/sessions/{session_id}")
        assert detail.status_code == 200
        assert detail.json()["messages"] == []
        assert Path(TEST_DIR, "agentshow.db").exists()


def test_first_message_auto_names_session() -> None:
    with TestClient(app) as client:
        created = client.post("/api/sessions", json={"title": "新对话"})
        session_id = created.json()["id"]
        response = client.post(
            f"/api/sessions/{session_id}/messages",
            json={"content": "请帮我完成支付文档的回归检查"},
        )
        assert response.status_code == 200
        detail = client.get(f"/api/sessions/{session_id}").json()
        assert detail["title"] == "完成支付文档的回归检查"


def test_session_rename_and_delete() -> None:
    with TestClient(app) as client:
        created = client.post("/api/sessions", json={"title": "待重命名"})
        session_id = created.json()["id"]
        renamed = client.patch(
            f"/api/sessions/{session_id}",
            json={"title": "手动编辑后的对话名称"},
        )
        assert renamed.status_code == 200
        assert renamed.json()["title"] == "手动编辑后的对话名称"

        deleted = client.delete(f"/api/sessions/{session_id}")
        assert deleted.status_code == 200
        missing = client.get(f"/api/sessions/{session_id}")
        assert missing.status_code == 404


def test_demo_session_deletion_is_persistent() -> None:
    with TestClient(app) as client:
        deleted = client.delete("/api/sessions/sess_demo_001")
        assert deleted.status_code == 200
    with TestClient(app) as client:
        missing = client.get("/api/sessions/sess_demo_001")
        assert missing.status_code == 404


def test_demo_chat_generates_trace_and_checkpoint() -> None:
    with TestClient(app) as client:
        created = client.post("/api/sessions", json={"title": "聊天测试"})
        session_id = created.json()["id"]
        sent = client.post(
            f"/api/sessions/{session_id}/messages",
            json={"content": "请生成一条演示回答"},
        )
        assert sent.status_code == 200

        detail = wait_until(
            lambda: (
                value
                if len((value := client.get(f"/api/sessions/{session_id}").json())["messages"]) >= 2
                else None
            )
        )
        assert detail["messages"][-1]["role"] == "assistant"
        trace = client.get(f"/api/sessions/{session_id}/trace").json()
        assert trace["summary"]["call_count"] >= 2
        checkpoints = client.get(f"/api/sessions/{session_id}/checkpoints").json()
        assert checkpoints
        assert client.get(f"/api/traces/{trace['spans'][0]['run_id']}").status_code == 200


def test_goal_loop_completes_in_demo_mode() -> None:
    with TestClient(app) as client:
        created = client.post("/api/sessions", json={"title": "Goal 测试"})
        session_id = created.json()["id"]
        response = client.post(
            f"/api/sessions/{session_id}/goals",
            json={
                "objective": "完成自动测试目标",
                "criteria": ["生成一次演示运行"],
                "constraints": ["不输出密钥"],
                "max_iterations": 2,
                "auto_start": True,
            },
        )
        assert response.status_code == 200
        goal_id = response.json()["id"]
        goal = wait_until(
            lambda: (
                next(
                    (
                        item
                        for item in client.get(f"/api/sessions/{session_id}/goals").json()
                        if item["id"] == goal_id and item["status"] == "completed"
                    ),
                    None,
                )
            )
        )
        assert goal["current_iteration"] == 1
        assert goal["iterations"][0]["status"] == "completed"


def test_internal_demo_stream() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/internal/llm/v1/chat/completions",
            headers={"Authorization": "Bearer test-service-token"},
            json={
                "model": "agentshow",
                "stream": True,
                "messages": [{"role": "user", "content": "hello"}],
            },
        )
        assert response.status_code == 200
        assert "data:" in response.text
        assert "[DONE]" in response.text


def test_provider_credential_lifecycle_and_checkpoint() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/api/providers",
            json={
                "name": "生命周期 Provider",
                "protocol": "openai-compatible",
                "base_url": "https://example.com/v1",
                "model": "lifecycle-model",
                "api_key": "sk-lifecycle-secret",
                "is_default": False,
            },
        ).json()
        provider_id = created["id"]
        updated = client.put(
            f"/api/providers/{provider_id}/credential",
            json={"api_key": "sk-updated-secret"},
        )
        assert updated.status_code == 200
        assert updated.json()["api_key_hint"] == "sk-...cret"
        assert client.delete(f"/api/providers/{provider_id}/credential").status_code == 200

        demo_test = client.post("/api/providers/provider_demo/test")
        assert demo_test.status_code == 200
        assert demo_test.json()["ok"] is True

        session = client.post("/api/sessions", json={"title": "Checkpoint 测试"}).json()
        checkpoint = client.post(
            f"/api/sessions/{session['id']}/checkpoints",
            json={"kind": "manual"},
        )
        assert checkpoint.status_code == 200
        listed = client.get(f"/api/sessions/{session['id']}/checkpoints").json()
        assert any(item["id"] == checkpoint.json()["id"] for item in listed)
        events = client.get(f"/api/sessions/{session['id']}/events").json()
        assert isinstance(events, list)


def test_security_and_lookup_errors() -> None:
    encrypted = encrypt_secret("sk-security-test")
    assert decrypt_secret(encrypted) == "sk-security-test"
    assert mask_secret("sk-security-test") == "sk-...test"
    with TestClient(app) as client:
        assert client.get("/api/lookup/not-found").status_code == 404
        assert client.get("/api/sessions/not-found/trace").status_code == 404
        assert client.delete("/api/sessions/not-found").status_code == 200


def test_agent_manager_demo_run_directly() -> None:
    with TestClient(app) as client:
        created = client.post("/api/sessions", json={"title": "Agent Manager 测试"})
        session_id = created.json()["id"]
        result = asyncio.run(
            agent_manager.run_prompt(session_id, "请直接执行一次 Demo Agent 测试")
        )
        assert result["stop_reason"] == "completed"
        assert "Demo Agent" in result["answer"]
        trace = client.get(f"/api/sessions/{session_id}/trace").json()
        assert trace["summary"]["call_count"] >= 2
        assert trace["tool_calls"] == []


def test_agent_manager_pi_branch_with_fake_process() -> None:
    with TestClient(app) as client:
        provider = client.post(
            "/api/providers",
            json={
                "name": "Pi 分支测试",
                "protocol": "openai-compatible",
                "base_url": "http://127.0.0.1:8117/v1",
                "model": "mock",
                "api_key": "sk-test-value",
                "is_default": True,
            },
        ).json()
        created = client.post("/api/sessions", json={"title": "Pi 分支测试"})
        session_id = created.json()["id"]

        class FakeStdin:
            def __init__(self):
                self.data = b""

            def write(self, data):
                self.data += data

            async def drain(self):
                return None

        fake_stdin = FakeStdin()
        fake_process = SimpleNamespace(
            ready=asyncio.Event(),
            process=SimpleNamespace(stdin=fake_stdin),
        )
        original_ensure = agent_manager._ensure_process

        async def fake_ensure(_session_id, _workspace):
            fake_process.ready.set()
            return fake_process

        async def scenario():
            agent_manager._ensure_process = fake_ensure
            existing_runs = set(agent_manager._runs)
            task = asyncio.create_task(
                agent_manager.run_prompt(session_id, "执行 Pi 分支测试")
            )
            for _ in range(50):
                new_runs = set(agent_manager._runs) - existing_runs
                if new_runs:
                    break
                await asyncio.sleep(0.01)
            new_runs = set(agent_manager._runs) - existing_runs
            if not new_runs:
                task.cancel()
                raise AssertionError("new run state was not created")
            state = agent_manager._runs[next(iter(new_runs))]
            await agent_manager._handle_host_event(
                state, {"type": "assistant_delta", "delta": "Pi "}
            )
            await agent_manager._handle_host_event(state, {"type": "model_started"})
            await agent_manager._handle_host_event(
                state, {"type": "model_completed", "data": {}}
            )
            await agent_manager._handle_host_event(
                state,
                {
                    "type": "tool_execution_start",
                    "data": {"tool_call_id": "call-1", "tool_name": "list_files", "args": {}},
                },
            )
            await agent_manager._handle_host_event(
                state,
                {
                    "type": "tool_execution_end",
                    "data": {
                        "tool_call_id": "call-1",
                        "tool_name": "list_files",
                        "result": "README.md",
                        "is_error": False,
                    },
                },
            )
            await agent_manager._handle_host_event(
                state,
                {
                    "type": "goal_report",
                    "data": {"status": "completed", "summary": "done"},
                },
            )
            await agent_manager._handle_host_event(
                state,
                {"type": "run_completed", "data": {"answer": "Pi path complete"}},
            )
            return await task

        try:
            result = asyncio.run(scenario())
        finally:
            agent_manager._ensure_process = original_ensure
            client.delete(f"/api/providers/{provider['id']}")

        assert result["answer"] == "Pi path complete"
        assert b'"type": "prompt"' in fake_stdin.data
        trace = client.get(f"/api/sessions/{session_id}/trace").json()
        assert any(span["kind"] == "tool" for span in trace["spans"])


def test_event_broker_publish_and_unsubscribe() -> None:
    async def scenario():
        broker = EventBroker()
        queue = broker.subscribe("session-test")
        await broker.publish("session-test", {"type": "event", "value": 1})
        received = await queue.get()
        broker.unsubscribe("session-test", queue)
        await broker.publish("session-test", {"type": "ignored"})
        return received, queue.empty()

    received, empty = asyncio.run(scenario())
    assert received == {"type": "event", "value": 1}
    assert empty is True


def test_db_json_helpers() -> None:
    assert row_to_dict(None) is None
    encoded = json_dumps({"name": "JAgent"})
    assert json_loads(encoded) == {"name": "JAgent"}
    assert json_loads("invalid-json", {"fallback": True}) == {"fallback": True}
    assert json_loads(None, []) == []


def test_gateway_and_missing_session_helpers() -> None:
    assert _chat_url("https://example.com/v1") == "https://example.com/v1/chat/completions"
    assert (
        _chat_url("https://example.com/v1/chat/completions")
        == "https://example.com/v1/chat/completions"
    )
    with pytest.raises(KeyError):
        agent_manager._session("missing-session")


def test_default_skill_discovery_and_path_loading() -> None:
    with TestClient(app) as client:
        skills = client.get("/api/skills").json()
        names = {skill["name"] for skill in skills}
        assert "software-delivery-pm" in names
        assert "software-delivery-frontend" in names
        assert len(skills) >= 10

        detail = client.get("/api/skills/software-delivery-pm")
        assert detail.status_code == 200
        assert "# 软件交付流水线" in detail.json()["content"]

        disabled = client.patch(
            "/api/skills/software-delivery-pm",
            json={"enabled": False},
        )
        assert disabled.status_code == 200
        assert disabled.json()["enabled"] is False
        enabled = client.patch(
            "/api/skills/software-delivery-pm",
            json={"enabled": True},
        )
        assert enabled.json()["enabled"] is True

        custom_dir = Path(TEST_DIR, "custom-skill")
        custom_dir.mkdir(parents=True, exist_ok=True)
        (custom_dir / "SKILL.md").write_text(
            "---\nname: custom-test-skill\ndescription: Custom E2E skill\n"
            "metadata:\n  version: '1.0.0'\n---\n# Custom\nFollow this skill.",
            encoding="utf-8",
        )
        added = client.post("/api/skills/add-path", json={"path": str(custom_dir)})
        assert added.status_code == 200
        assert added.json()["skills"][0]["name"] == "custom-test-skill"
        assert client.post("/api/skills/add-path", json={"path": "not-found"}).status_code == 400


def test_skill_context_injection() -> None:
    context = build_skill_context(["software-delivery-pm", "software-delivery-frontend"])
    assert "<skill name=\"software-delivery-pm\"" in context
    assert "<skill name=\"software-delivery-frontend\"" in context
    assert "Skill 不能扩大工具权限" in context


def test_document_import_export_and_attachment_message() -> None:
    with TestClient(app) as client:
        markdown = "# 测试文档\n\n这是附件内容。".encode("utf-8")
        extracted = client.post(
            "/api/documents/extract",
            files={"file": ("notes.md", markdown, "text/markdown")},
        )
        assert extracted.status_code == 200
        assert "这是附件内容" in extracted.json()["text"]

        docx_buffer = io.BytesIO()
        document = Document()
        document.add_paragraph("Word 文档测试内容")
        document.save(docx_buffer)
        docx_extract = client.post(
            "/api/documents/extract",
            files={
                "file": (
                    "notes.docx",
                    docx_buffer.getvalue(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        assert docx_extract.status_code == 200
        assert "Word 文档测试内容" in docx_extract.json()["text"]

        for export_format, prefix in (("md", b"# "), ("docx", b"PK"), ("pdf", b"%PDF")):
            exported = client.post(
                "/api/documents/export",
                json={
                    "format": export_format,
                    "title": "JAgent 测试导出",
                    "content": "导出内容",
                },
            )
            assert exported.status_code == 200
            assert exported.content.startswith(prefix)

        created = client.post("/api/sessions", json={"title": "附件会话"})
        session_id = created.json()["id"]
        attachment = extracted.json()
        sent = client.post(
            f"/api/sessions/{session_id}/messages",
            json={
                "content": "请分析附件",
                "attachments": [attachment],
            },
        )
        assert sent.status_code == 200
        detail = wait_until(
            lambda: (
                value
                if len((value := client.get(f"/api/sessions/{session_id}").json())["messages"]) >= 2
                else None
            )
        )
        assert "notes.md" in detail["messages"][0]["content"]
        trace = client.get(f"/api/sessions/{session_id}/trace").json()
        assert trace["summary"]["tokens_per_second"] > 0


def test_session_warmup_demo_mode() -> None:
    with TestClient(app) as client:
        created = client.post("/api/sessions", json={"title": "预热测试"})
        warmed = client.post(f"/api/sessions/{created.json()['id']}/warmup")
        assert warmed.status_code == 200
        assert warmed.json() == {"warmed": False, "mode": "demo"}

