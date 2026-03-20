# VibeReading

An AI-powered reading assistant that builds a knowledge graph from your documents and lets you explore them through a conversational agent.

## Features

- Upload `.txt` or `.md` files and automatically index them into a GraphRAG knowledge graph
- Chat with an AI agent that can query the graph, explore node neighborhoods, and synthesize answers
- Interactive knowledge graph visualization with real-time node highlighting when the agent accesses nodes
- Resizable split panel: document viewer on the left, chat on the right

## Architecture

```
VibeReading/
├── NanoRAG.py              # GraphRAG wrapper (nano-graphrag)
├── backend/
│   ├── app.py              # FastAPI entry point
│   ├── config.py           # Settings from .env
│   ├── api/
│   │   ├── schemas.py      # Pydantic request/response models
│   │   └── routes/
│   │       ├── files.py    # Upload, index status, content
│   │       ├── chat.py     # SSE streaming chat
│   │       └── graph.py    # Graph data & node traversal
│   └── core/
│       ├── state.py        # Shared app state (RAG instance, index status)
│       ├── rag_tools.py    # LangChain tools wrapping NanoRAG
│       └── agent.py        # deepagents agent setup
└── frontend/
    ├── index.html
    ├── css/styles.css
    └── js/
        ├── app.js          # Global state, file upload, panel resize
        ├── viewer.js       # Markdown document renderer
        ├── graph.js        # vis-network graph visualization
        └── chat.js         # SSE chat consumer, streaming renderer
```

## Setup

### 1. Install dependencies

```bash
uv sync
```

### 2. Configure environment

Copy and fill in your API keys:

```bash
cp .env.example .env
```

`.env` variables:

```ini
# NanoRAG — used for document indexing and graph construction
NANO_GRAPHRAG_API_KEY=your_api_key
NANO_GRAPHRAG_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
NANO_GRAPHRAG_BEST_MODEL=qwen3-max-2026-01-23
NANO_GRAPHRAG_CHEAP_MODEL=qwen3.5-flash
NANO_GRAPHRAG_EMBEDDING_MODEL=text-embedding-v3

# Agent — used for the conversational assistant (defaults to NanoRAG values if not set)
AGENT_API_KEY=your_api_key
AGENT_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
AGENT_MODEL=qwen3-max-2026-01-23

# Storage (optional, defaults shown)
NANO_WORKING_DIR=nano_graphrag_cache
UPLOAD_DIR=uploads
```

### 3. Run

```bash
uv run uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

Then open [http://localhost:8000](http://localhost:8000) in your browser.

## Usage

1. Click **Upload File** and select a `.txt` or `.md` document
2. Wait for the indexing status to show **Ready** (this may take a few minutes for large files)
3. Type questions in the chat panel on the right
4. Click **Knowledge Graph** to open the graph visualization overlay
5. When the agent queries or traverses nodes, they are automatically highlighted in the graph
