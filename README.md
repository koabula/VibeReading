# VibeReading
English | [中文](./README_CN.md)
> Stop Reading books by yourself, vibe reading now.

VibeReading is an AI assistant for deep document reading. After you upload a file, it builds a knowledge-graph index and helps you locate, explain, and connect content through streaming conversations.

The project currently supports both text and PDF workflows, including multi-project management, chat history, in-document navigation, and precise PDF positioning.

## 1. Core Capabilities

- Document upload and indexing
  - Supports `.txt`, `.md`, and `.pdf`
  - Text files go directly through the GraphRAG indexing pipeline
  - PDF files are first parsed to Markdown via MinerU, then indexed

- Knowledge-graph retrieval and QA
  - Uses `nano-graphrag` to build an entity-relation graph
  - Agent tools cover local/global retrieval, node details, and neighborhood exploration
  - Chat endpoint uses SSE streaming for real-time frontend rendering

- Document-viewer linkage
  - Supports citation links in `doc://scroll?line=N` format
  - In PDF mode, Markdown line numbers are mapped back to PDF page/position
  - Built-in PDF.js reader supports zoom, paging, page jump, and text selection

- Project management
  - Each indexing result is persisted under `projects/<slug>/`
  - Supports listing projects, activating projects, and deleting non-active projects
  - Supports one-time migration from legacy `nano_graphrag_cache/` layout

- Conversation experience
  - Multi-turn context support (`history`)
  - Local conversation snapshots, isolated per project
  - One-click continue when the agent reaches recursion/step limits

## 2. Tech Stack

- Backend
  - FastAPI
  - LangChain + LangGraph ReAct Agent
  - `nano-graphrag` (GraphRAG)
  - OpenAI-compatible API endpoints (e.g., Qwen-compatible endpoints)

- Frontend
  - Vanilla HTML/CSS/JavaScript
  - marked (Markdown rendering)
  - KaTeX (math rendering)
  - PDF.js (PDF rendering and interactions)

## 3. Project Structure (Key Paths)

```text
VibeReading/
├── backend/
│   ├── app.py                     # FastAPI entry, mounts API and frontend static assets
│   ├── config.py                  # .env settings loader
│   ├── api/
│   │   ├── schemas.py             # Pydantic models
│   │   └── routes/
│   │       ├── files.py           # Upload/status/content/raw-file endpoints
│   │       ├── chat.py            # SSE streaming chat endpoint
│   │       └── projects.py        # Project list/activate/delete
│   └── core/
│       ├── agent.py               # Agent construction and system prompt
│       ├── rag_tools.py           # Agent toolset (RAG + document navigation)
│       ├── mineru.py              # MinerU PDF parsing client
│       └── state.py               # Shared runtime state
├── frontend/
│   ├── index.html                 # Page skeleton
│   ├── css/styles.css             # Styles
│   └── js/
│       ├── app.js                 # Upload, status polling, project management, theme switch
│       ├── viewer.js              # Document/PDF viewer
│       └── chat.js                # Streaming chat rendering and history management
├── NanoRAG.py                     # GraphRAG wrapper (index/query/graph export)
├── projects/                      # Project-scoped index data
├── uploads/                       # Uploaded files
├── pyproject.toml                 # Python dependencies
└── README_CN.md                   # Chinese readme
```

## 4. Prerequisites

- Python 3.11+
- `uv` is recommended for dependency management and running
- Valid LLM/embedding API keys
- MinerU token if you need PDF parsing

Install dependencies:

```bash
uv sync
```

`uv sync` installs the full runtime dependency set declared in `pyproject.toml` and pinned by `uv.lock`, including `nano-graphrag`. You should not need to manually install extra Python packages afterward.

## 5. Configure `.env`

Copy the template:

```bash
cp .env.example .env
```

Key variables:

- NanoRAG (required)
  - `NANO_GRAPHRAG_API_KEY`: required
  - `NANO_GRAPHRAG_BASE_URL`: optional, defaults to DashScope-compatible URL
  - `NANO_GRAPHRAG_BEST_MODEL`: optional
  - `NANO_GRAPHRAG_CHEAP_MODEL`: optional
  - `NANO_GRAPHRAG_EMBEDDING_MODEL`: optional

- Agent (optional, falls back to NanoRAG values when omitted)
  - `AGENT_API_KEY`
  - `AGENT_BASE_URL`
  - `AGENT_MODEL`

- MinerU (required only for PDF uploads, Apply for a token at https://mineru.net/apiManage/docs)
  - `MINERU_API_KEY`

- Storage paths (optional)
  - `PROJECTS_DIR`: defaults to `projects`
  - `UPLOAD_DIR`: defaults to `uploads`

Note: the current code uses `PROJECTS_DIR` and `UPLOAD_DIR`. `NANO_WORKING_DIR` is only a legacy compatibility field and is not part of the current main flow.

## 6. Run

Development mode with hot reload:

```bash
uv run uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000 --reload-dir backend --reload-dir frontend --reload-exclude .venv --reload-exclude .uv-cache --reload-exclude projects --reload-exclude uploads
```

Stable mode without hot reload:

```bash
uv run uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

Use the hot-reload command for local development. Use the non-reload command if you just want to run the app stably.

Open in your browser:

```text
http://localhost:8000
```

## 7. Usage

1. Upload a document (`.txt` / `.md` / `.pdf`)
2. Wait until status changes from `indexing` to `ready`
3. Ask questions in the chat panel
4. Click citation links in answers (`doc://scroll?line=N`) to navigate
5. Switch previous projects from the top `Projects` dropdown

Notes:

- PDF files are converted to Markdown for indexing and semantic positioning, then mapped back to PDF page positions.
- Chat history is stored locally in the browser, per project.

## 8. Main Backend APIs

- File APIs
  - `POST /api/files/upload`: upload file and trigger background indexing
  - `GET /api/files/status`: get indexing status and current file type
  - `GET /api/files/content`: get current text/markdown content
  - `GET /api/files/raw`: get original file (used by embedded PDF preview)

- Chat API
  - `POST /api/chat/stream`: SSE streaming response

- Project APIs
  - `GET /api/projects`: list projects
  - `POST /api/projects/{slug}/activate`: activate project
  - `DELETE /api/projects/{slug}`: delete project (cannot delete the active one)

## 9. Data Directory Notes

- `uploads/`
  - Raw uploaded files

- `projects/<slug>/`
  - `session_meta.json`: project metadata
  - `graph_chunk_entity_relation.graphml`: graph structure
  - `kv_store_*.json`, `vdb_entities.json`: GraphRAG index artifacts
  - `full.md`: Markdown converted from PDF (PDF projects only)
  - `page_map.json` / `paragraph_map.json`: Markdown line to PDF position maps (PDF projects only)
  - `original.pdf` (or equivalent suffix): project-local copy of the original PDF
