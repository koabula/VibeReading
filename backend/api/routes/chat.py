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
    token = scroll_event_queue.set(queue)

    # Build full message list: prior conversation turns + current user message
    prior = [
        {"role": m.get("role", "user"), "content": m.get("content", "")}
        for m in (request.history or [])
        if m.get("content")
    ]
    input_payload = {"messages": prior + [{"role": "user", "content": request.message}]}

    async def _consume_events() -> None:
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
                        await queue.put({"type": "text", "content": chunk.content})

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
