from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    title: str = "新对话"
    model_name: str = "Demo Agent"
    workspace_path: str | None = None


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=100_000)
    mode: Literal["prompt", "steer", "follow_up"] = "prompt"
    skills: list[str] = Field(default_factory=list)
    attachments: list["AttachmentInput"] = Field(default_factory=list)


class AttachmentInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    kind: str = Field(default="text", max_length=32)
    text: str = Field(default="", max_length=300_000)
    size: int = Field(default=0, ge=0)


class DocumentExportRequest(BaseModel):
    format: Literal["md", "docx", "pdf"]
    title: str = Field(default="JAgent 对话", max_length=120)
    content: str = Field(min_length=1, max_length=500_000)


class GoalCreate(BaseModel):
    objective: str = Field(min_length=1, max_length=20_000)
    criteria: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    max_iterations: int = Field(default=5, ge=1, le=20)
    auto_start: bool = True
    skills: list[str] = Field(default_factory=list)


class SkillPathRequest(BaseModel):
    path: str = Field(min_length=1, max_length=4096)


class SkillToggleRequest(BaseModel):
    enabled: bool


class ProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    protocol: Literal["openai-compatible", "demo"] = "openai-compatible"
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    api_key: str | None = None
    is_default: bool = True


class CredentialUpdate(BaseModel):
    api_key: str = Field(min_length=1, max_length=10_000)


class CheckpointCreate(BaseModel):
    kind: str = "manual"
    run_id: str | None = None
    pi_entry_id: str | None = None
    last_event_seq: int = 0
    context_hash: str | None = None
    workspace_snapshot_id: str | None = None


class EventPayload(BaseModel):
    event: str
    session_id: str
    run_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)

