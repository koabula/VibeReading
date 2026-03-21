from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from backend.api.schemas import ChatRequest, IndexStatus
from backend.core.rag_tools import scroll_event_queue
from backend.core.state import app_state

router = APIRouter()


class _TaggedStreamParser:
    _OPEN_TAGS = {
        "<thought>": "thought",
        "<message_to_user>": "message_to_user",
    }
    _CLOSE_TAGS = {
        "thought": "</thought>",
        "message_to_user": "</message_to_user>",
    }
    _MAX_TAG_LEN = max(
        len(tag)
        for tag in [*_OPEN_TAGS.keys(), *_CLOSE_TAGS.values()]
    )

    def __init__(self) -> None:
        self._buffer = ""
        self._mode: str | None = None

    def feed(self, chunk: str) -> list[dict]:
        self._buffer += chunk
        return self._drain(final=False)

    def flush(self) -> list[dict]:
        return self._drain(final=True)

    def parse_complete(self, text: str) -> dict[str, str]:
        thought_parts: list[str] = []
        message_parts: list[str] = []

        cursor = 0
        while cursor < len(text):
            next_tag = self._find_next_open_tag_in_text(text, cursor)
            if next_tag is None:
                trailing = text[cursor:]
                if trailing:
                    thought_parts.append(trailing)
                break

            idx, tag, mode = next_tag
            if idx > cursor:
                thought_parts.append(text[cursor:idx])

            close_tag = self._CLOSE_TAGS[mode]
            content_start = idx + len(tag)
            close_idx = text.find(close_tag, content_start)
            if close_idx == -1:
                remainder = text[idx:]
                if remainder:
                    thought_parts.append(remainder)
                break

            content = text[content_start:close_idx]
            if content:
                if mode == "thought":
                    thought_parts.append(content)
                else:
                    message_parts.append(content)
            cursor = close_idx + len(close_tag)

        return {
            "thought": "".join(thought_parts),
            "message_to_user": "".join(message_parts),
        }

    def _drain(self, *, final: bool) -> list[dict]:
        events: list[dict] = []

        while self._buffer:
            if self._mode is None:
                next_tag = self._find_next_open_tag()
                if next_tag is None:
                    text, rest = self._split_safe_tail(self._buffer, self._MAX_TAG_LEN - 1, final=final)
                    if text:
                        events.append({"type": "thought", "content": text})
                    self._buffer = rest
                    break

                idx, tag, mode = next_tag
                prefix = self._buffer[:idx]
                if prefix:
                    events.append({"type": "thought", "content": prefix})
                self._buffer = self._buffer[idx + len(tag):]
                self._mode = mode
                continue

            close_tag = self._CLOSE_TAGS[self._mode]
            idx = self._buffer.find(close_tag)
            if idx != -1:
                content = self._buffer[:idx]
                if content:
                    events.append({"type": self._mode, "content": content})
                self._buffer = self._buffer[idx + len(close_tag):]
                self._mode = None
                continue

            text, rest = self._split_safe_tail(self._buffer, len(close_tag) - 1, final=final)
            if text:
                events.append({"type": self._mode, "content": text})
            self._buffer = rest
            break

        if final and self._buffer:
            fallback_type = self._mode or "thought"
            events.append({"type": fallback_type, "content": self._buffer})
            self._buffer = ""
            self._mode = None

        return events

    def _find_next_open_tag(self) -> tuple[int, str, str] | None:
        return self._find_next_open_tag_in_text(self._buffer, 0)

    def _find_next_open_tag_in_text(self, text: str, start: int) -> tuple[int, str, str] | None:
        matches: list[tuple[int, str, str]] = []
        for tag, mode in self._OPEN_TAGS.items():
            idx = text.find(tag, start)
            if idx != -1:
                matches.append((idx, tag, mode))
        if not matches:
            return None
        return min(matches, key=lambda item: item[0])

    @staticmethod
    def _split_safe_tail(text: str, keep: int, *, final: bool) -> tuple[str, str]:
        if final or keep <= 0 or len(text) <= keep:
            return (text, "") if final else ("", text)
        return text[:-keep], text[-keep:]


async def _stream_agent(request: ChatRequest) -> AsyncGenerator[dict, None]:
    """Consume the agent's astream_events and yield SSE-ready dicts."""
    from backend.core.agent import get_agent  # lazy: agent is expensive to import

    if app_state.index_status not in {IndexStatus.ready, IndexStatus.idle}:
        yield {"data": json.dumps({"type": "error", "content": "Knowledge graph is not ready yet."})}
        yield {"data": json.dumps({"type": "done"})}
        return

    agent = get_agent()

    # Single queue carries all events: text chunks, tool_calls, scroll_to, …
    queue: asyncio.Queue[dict | None] = asyncio.Queue(maxsize=512)
    parser = _TaggedStreamParser()
    token = scroll_event_queue.set(queue)
    final_message_to_user = ""
    streamed_message_to_user = ""

    # Build full message list: prior conversation turns + current user message
    prior = [
        {"role": m.get("role", "user"), "content": m.get("content", "")}
        for m in (request.history or [])
        if m.get("content")
    ]
    input_payload = {"messages": prior + [{"role": "user", "content": request.message}]}

    async def _consume_events() -> None:
        nonlocal final_message_to_user, streamed_message_to_user
        try:
            async for event in agent.astream_events(
                input_payload,
                version="v2",
                config={"recursion_limit": 50},
            ):
                kind = event.get("event", "")

                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        for item in parser.feed(str(chunk.content)):
                            if item.get("type") == "thought":
                                await queue.put(item)
                            elif item.get("type") == "message_to_user":
                                content = str(item.get("content", ""))
                                if content:
                                    streamed_message_to_user += content
                                    await queue.put({"type": "message_to_user", "content": content})

                elif kind == "on_chain_end" and event.get("name") == "LangGraph":
                    output = event.get("data", {}).get("output", {})
                    messages = output.get("messages", []) if isinstance(output, dict) else []
                    if messages:
                        last = messages[-1]
                        content = getattr(last, "content", "") if last is not None else ""
                        if isinstance(content, list):
                            content = "".join(
                                part.get("text", "")
                                for part in content
                                if isinstance(part, dict)
                            )
                        if isinstance(content, str) and content:
                            parsed = parser.parse_complete(content)
                            final_message_to_user = parsed.get("message_to_user", "").strip()

                elif kind == "on_tool_start":
                    tool_name = event.get("name", "")
                    tool_input = event.get("data", {}).get("input", {})
                    await queue.put({"type": "tool_call", "tool_name": tool_name, "tool_input": tool_input})

        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            # Detect LangGraph recursion limit so the frontend can offer "Continue"
            if "recursion_limit" in msg.lower() or "recursion limit" in msg.lower():
                await queue.put({"type": "recursion_limit"})
            else:
                await queue.put({"type": "error", "content": msg})
        finally:
            for item in parser.flush():
                if item.get("type") == "thought":
                    await queue.put(item)
            if final_message_to_user:
                remaining = final_message_to_user[len(streamed_message_to_user):]
                if remaining:
                    await queue.put({"type": "message_to_user", "content": remaining})
            await queue.put(None)  # sentinel

    task = asyncio.create_task(_consume_events())

    try:
        while True:
            item = await queue.get()
            if item is None:
                break
            # All items are plain dicts (text, tool_call, scroll_to, error, …)
            yield {"data": json.dumps(item)}
    finally:
        scroll_event_queue.reset(token)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    yield {"data": json.dumps({"type": "done"})}


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=422, detail="Message cannot be empty")

    return EventSourceResponse(_stream_agent(request))
