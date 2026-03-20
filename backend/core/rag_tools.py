from __future__ import annotations

import asyncio
import contextvars
import json
from typing import Annotated

from langchain_core.tools import tool

# ---------------------------------------------------------------------------
# Per-request event queues (ContextVar so each SSE connection gets its own)
# ---------------------------------------------------------------------------

# Generic event queue: carries dicts (text, tool_call, scroll_to, …)
# RAG tools that used to push node-id lists now push scroll_to events instead.
scroll_event_queue: contextvars.ContextVar[asyncio.Queue | None] = contextvars.ContextVar(
    "scroll_event_queue", default=None
)


async def _push_scroll(line: int) -> None:
    queue = scroll_event_queue.get()
    if queue is not None:
        await queue.put({"type": "scroll_to", "line": line, "highlight": True})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_rag():
    from backend.core.state import app_state  # lazy import avoids circular deps

    rag = app_state.get_rag()
    if rag is None:
        raise RuntimeError("Knowledge graph not ready. Please upload and index a document first.")
    return rag


def _get_doc_lines() -> list[str]:
    from backend.core.state import app_state

    path = app_state.current_file_path
    if path is None or not path.exists():
        raise RuntimeError("No document loaded. Please upload a file first.")
    return path.read_text(encoding="utf-8").splitlines()


# ---------------------------------------------------------------------------
# RAG tools (knowledge graph)
# ---------------------------------------------------------------------------

@tool
async def rag_local_query(
    question: Annotated[str, "The question to answer using local graph context"],
) -> str:
    """Query the knowledge graph in LOCAL mode.
    Best for specific, entity-centric questions about particular concepts or terms.
    Returns retrieved context passages from the knowledge graph."""
    rag = _get_rag()
    context = await asyncio.to_thread(rag.query, question, mode="local", only_need_context=True)
    return str(context)


@tool
async def rag_global_query(
    question: Annotated[str, "The question to answer using global graph context"],
) -> str:
    """Query the knowledge graph in GLOBAL mode.
    Best for broad, thematic questions about the overall content or high-level concepts.
    Returns retrieved context passages from the knowledge graph."""
    rag = _get_rag()
    context = await asyncio.to_thread(rag.query, question, mode="global", only_need_context=True)
    return str(context)


@tool
async def explore_node_neighbors(
    node_id: Annotated[str, "The exact node ID to explore (case-sensitive)"],
    depth: Annotated[int, "How many hops to traverse (1 = direct neighbors, 2 = two hops). Default 1."] = 1,
) -> str:
    """Explore the knowledge graph by traversing neighbors of a given node.
    Use this to discover related concepts and entities connected to a node.
    Returns a JSON object with the neighboring nodes and edges."""
    rag = _get_rag()
    try:
        subgraph = await asyncio.to_thread(
            rag.get_node_neighbors, node_id, depth=max(1, min(depth, 3))
        )
    except KeyError:
        return json.dumps({"error": f"Node '{node_id}' not found in the knowledge graph."})

    return json.dumps(subgraph, ensure_ascii=False)


@tool
async def get_node_details(
    node_id: Annotated[str, "The exact node ID to inspect (case-sensitive)"],
) -> str:
    """Get detailed information about a specific node in the knowledge graph,
    including its type, description, degree, and list of direct neighbors."""
    rag = _get_rag()
    try:
        details = await asyncio.to_thread(rag.get_node_details, node_id)
    except KeyError:
        return json.dumps({"error": f"Node '{node_id}' not found in the knowledge graph."})

    return json.dumps(details, ensure_ascii=False)


@tool
async def list_key_entities(
    top_n: Annotated[int, "Number of top entities to return (max 20). Default 12."] = 12,
) -> str:
    """List the most central entities in the knowledge graph, ranked by their
    number of connections (degree centrality). Use this as a first step when
    asked about the document's overall structure, main topics, key concepts,
    or when building a mental map of the content."""
    rag = _get_rag()
    data = await asyncio.to_thread(rag.get_graph_data)
    nodes = data.get("nodes", [])
    if not nodes:
        return json.dumps({"error": "Knowledge graph has no nodes yet."})

    top_n = max(1, min(top_n, 20))
    nodes_sorted = sorted(nodes, key=lambda n: n.get("value", 0), reverse=True)
    top = nodes_sorted[:top_n]

    result = [
        {
            "id": n["id"],
            "type": n.get("group", "UNKNOWN"),
            "connections": n.get("value", 0),
            "description": (n.get("title") or "").split("\n\n")[-1][:300].strip(),
        }
        for n in top
    ]
    return json.dumps(result, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Document tools
# ---------------------------------------------------------------------------

@tool
async def get_document_info() -> str:
    """Return basic metadata about the current document: filename, total lines,
    and total character count. Always call this first to know the valid line range
    before calling read_document."""
    from backend.core.state import app_state

    path = app_state.current_file_path
    if path is None or not path.exists():
        return json.dumps({"error": "No document loaded."})

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    return json.dumps({
        "filename": app_state.current_filename or path.name,
        "total_lines": len(lines),
        "total_chars": len(text),
    }, ensure_ascii=False)


@tool
async def read_document(
    start_line: Annotated[int, "First line to read, 1-based (inclusive)"],
    end_line: Annotated[int, "Last line to read, 1-based (inclusive). Max 200 lines per call."],
) -> str:
    """Read a contiguous range of lines from the current document.
    Each returned line is prefixed with its line number so you can cite exact positions.
    Use get_document_info first to know the total line count."""
    lines = await asyncio.to_thread(_get_doc_lines)
    total = len(lines)

    start = max(1, start_line)
    end   = min(total, end_line, start + 199)  # cap at 200 lines

    selected = lines[start - 1 : end]
    numbered = "\n".join(f"{start + i:>6} | {line}" for i, line in enumerate(selected))
    return f"Lines {start}–{end} of {total}:\n\n{numbered}"


@tool
async def search_document(
    query: Annotated[str, "Text to search for in the document (case-insensitive substring match)"],
) -> str:
    """Search the raw document text for a substring and return up to 20 matching lines
    with their line numbers. Use this to quickly locate a term or passage before
    calling read_document or create_doc_link."""
    lines = await asyncio.to_thread(_get_doc_lines)
    q = query.lower()
    matches = [
        {"line": i + 1, "text": line.strip()}
        for i, line in enumerate(lines)
        if q in line.lower()
    ][:20]

    if not matches:
        return json.dumps({"matches": [], "message": f"No occurrences of '{query}' found."})
    return json.dumps({"matches": matches, "total_found": len(matches)}, ensure_ascii=False, indent=2)


@tool
def create_doc_link(
    display_text: Annotated[str, "The clickable text the user will see"],
    line_number: Annotated[int, "The document line number to jump to when clicked"],
) -> str:
    """Create a Markdown hyperlink that, when clicked in the chat, scrolls the
    document viewer to the given line number and highlights it.
    Embed the returned string verbatim in your response.
    Example output: [Theorem 2.1](doc://scroll?line=45)"""
    return f"[{display_text}](doc://scroll?line={line_number})"


@tool
async def scroll_to_line(
    line_number: Annotated[int, "The 1-based line number to scroll the document viewer to"],
) -> str:
    """Immediately scroll the left-side document viewer to the specified line number
    and briefly highlight it. Use this to proactively guide the user's attention
    while explaining a passage."""
    lines = await asyncio.to_thread(_get_doc_lines)
    total = len(lines)
    line = max(1, min(line_number, total))
    await _push_scroll(line)
    return f"Document viewer scrolled to line {line} (of {total})."


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

ALL_TOOLS = [
    # RAG / knowledge-graph tools
    rag_local_query,
    rag_global_query,
    explore_node_neighbors,
    get_node_details,
    list_key_entities,
    # Document navigation & reading tools
    get_document_info,
    read_document,
    search_document,
    create_doc_link,
    scroll_to_line,
]
