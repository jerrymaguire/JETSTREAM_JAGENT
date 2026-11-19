from __future__ import annotations

import asyncio
import json
import os
from typing import Any, AsyncIterator

import httpx
from fastapi import HTTPException

from .db import connection
from .security import decrypt_secret


def get_default_provider() -> dict[str, Any]:
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM providers WHERE enabled = 1 ORDER BY is_default DESC, created_at LIMIT 1"
        ).fetchone()
    if not row:
        raise HTTPException(status_code=409, detail="请先配置模型 Provider 和 API Key")
    return dict(row)


def _chat_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def verify_internal_token(authorization: str | None) -> None:
    expected = os.getenv("AGENTSHOW_SERVICE_TOKEN")
    if not expected:
        return
    supplied = (authorization or "").removeprefix("Bearer ").strip()
    if supplied != expected:
        raise HTTPException(status_code=401, detail="Invalid internal service token")


async def proxy_chat_completion(
    body: dict[str, Any],
    authorization: str | None,
) -> AsyncIterator[bytes]:
    verify_internal_token(authorization)
    provider = get_default_provider()
    if provider["protocol"] == "demo":
        async for chunk in demo_stream(body):
            yield chunk
        return

    key = decrypt_secret(provider["api_key_ciphertext"])
    if not key:
        raise HTTPException(status_code=409, detail="当前 Provider 尚未配置 API Key")

    upstream_body = dict(body)
    upstream_body["model"] = provider["model"]
    payload = json.dumps(upstream_body, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    timeout = httpx.Timeout(connect=20.0, read=300.0, write=30.0, pool=20.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        async with client.stream("POST", _chat_url(provider["base_url"]), headers=headers, content=payload) as response:
            if response.status_code >= 400:
                detail = (await response.aread()).decode("utf-8", errors="replace")
                raise HTTPException(status_code=response.status_code, detail=detail[:2000])
            async for chunk in response.aiter_bytes():
                yield chunk


async def demo_stream(body: dict[str, Any]) -> AsyncIterator[bytes]:
    messages = body.get("messages") or []
    user_text = ""
    for message in reversed(messages):
        if message.get("role") == "user":
            content = message.get("content")
            user_text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
            break
    answer = (
        "这是 Demo Agent 的本地演示回答。"
        f"你刚才的问题是：{user_text[:160]}。"
        "当前没有配置真实模型密钥，但对话、会话保存和 Trace 结构仍可正常演示。"
    )
    request_id = "chatcmpl-demo"
    created = 1_763_000_000
    model = body.get("model", "demo")

    def record(delta: dict[str, Any], finish_reason: str | None = None) -> bytes:
        payload = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": delta,
                    "finish_reason": finish_reason,
                }
            ],
        }
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")

    yield record({"role": "assistant", "content": ""})
    for start in range(0, len(answer), 18):
        await asyncio.sleep(0.015)
        yield record({"content": answer[start : start + 18]})
    yield record({}, "stop")
    yield b"data: [DONE]\n\n"


def provider_public(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "protocol": row["protocol"],
        "base_url": row["base_url"],
        "model": row["model"],
        "api_key_set": bool(row.get("api_key_ciphertext")),
        "api_key_hint": row.get("api_key_hint"),
        "enabled": bool(row["enabled"]),
        "is_default": bool(row["is_default"]),
    }

