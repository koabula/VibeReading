from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── File endpoints ────────────────────────────────────────────────────────────

class IndexStatus(str, Enum):
    idle = "idle"
    indexing = "indexing"
    ready = "ready"
    error = "error"


class FileUploadResponse(BaseModel):
    filename: str
    status: IndexStatus
    message: str


class FileStatusResponse(BaseModel):
    status: IndexStatus
    filename: str | None = None
    message: str | None = None
    file_type: str = "text"
    pdf_page_map: dict | None = None
    pdf_paragraph_map: dict | None = None


class FileContentResponse(BaseModel):
    filename: str
    content: str


# ── Chat endpoints ────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message to the agent")
    history: list[dict] = Field(
        default_factory=list,
        description="Previous conversation turns [{role, content}, …]",
    )


# SSE event payloads (serialised to JSON and sent as `data:` lines)

class SSETextChunk(BaseModel):
    type: str = "text"
    content: str


class SSENodesAccessed(BaseModel):
    type: str = "nodes_accessed"
    node_ids: list[str]


class SSEToolCall(BaseModel):
    type: str = "tool_call"
    tool_name: str
    tool_input: dict[str, Any]


class SSEDone(BaseModel):
    type: str = "done"


# ── Session / reload ─────────────────────────────────────────────────────────

class SessionInfo(BaseModel):
    filename: str
    file_path: str
    indexed_at: str


class SessionListResponse(BaseModel):
    sessions: list[SessionInfo]


class ReloadResponse(BaseModel):
    status: IndexStatus
    filename: str
    message: str


# ── SSE scroll event ─────────────────────────────────────────────────────────

class SSEScrollTo(BaseModel):
    type: str = "scroll_to"
    line: int
    highlight: bool = True
