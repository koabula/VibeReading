from __future__ import annotations

import asyncio
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from threading import Thread
from typing import Any

import networkx as nx
import numpy as np
from dotenv import load_dotenv
from openai import AsyncOpenAI, BadRequestError

from nano_graphrag import GraphRAG, QueryParam
from nano_graphrag._utils import EmbeddingFunc, compute_args_hash
from nano_graphrag.base import BaseKVStorage


@dataclass
class NanoRAGConfig:
    base_url: str
    api_key: str
    best_model: str
    cheap_model: str
    embedding_model: str


class NanoRAG:
    ENV_BASE_URL = "NANO_GRAPHRAG_BASE_URL"
    ENV_API_KEY = "NANO_GRAPHRAG_API_KEY"
    ENV_BEST_MODEL = "NANO_GRAPHRAG_BEST_MODEL"
    ENV_CHEAP_MODEL = "NANO_GRAPHRAG_CHEAP_MODEL"
    ENV_EMBEDDING_MODEL = "NANO_GRAPHRAG_EMBEDDING_MODEL"

    DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    DEFAULT_BEST_MODEL = "qwen3-max-2026-01-23"
    DEFAULT_CHEAP_MODEL = "qwen3.5-flash"
    DEFAULT_EMBEDDING_MODEL = "text-embedding-v3"

    def __init__(
        self,
        working_dir: str | Path,
        env_file: str | Path = ".env",
        *,
        enable_llm_cache: bool = True,
        best_model_max_token_size: int = 8192,
        cheap_model_max_token_size: int = 8192,
        best_model_max_async: int = 4,
        cheap_model_max_async: int = 4,
        embedding_batch_num: int = 8,
        embedding_func_max_async: int = 4,
    ) -> None:
        self.working_dir = Path(working_dir)
        self.env_file = Path(env_file)

        self.index_graphml_file = self.working_dir / "graph_chunk_entity_relation.graphml"
        self.index_full_docs_file = self.working_dir / "kv_store_full_docs.json"
        self.index_text_chunks_file = self.working_dir / "kv_store_text_chunks.json"
        self.index_vdb_entities_file = self.working_dir / "vdb_entities.json"
        self.index_html_file = self.working_dir / "graph_chunk_entity_relation.html"

        self.enable_llm_cache = enable_llm_cache
        self.best_model_max_token_size = best_model_max_token_size
        self.cheap_model_max_token_size = cheap_model_max_token_size
        self.best_model_max_async = best_model_max_async
        self.cheap_model_max_async = cheap_model_max_async
        self.embedding_batch_num = embedding_batch_num
        self.embedding_func_max_async = embedding_func_max_async

        self.config = self._load_config()
        self.client = AsyncOpenAI(api_key=self.config.api_key, base_url=self.config.base_url)

        self.rag: GraphRAG | None = None
        self.reload()

    def _get_required_env(self, name: str) -> str:
        value = os.getenv(name, "").strip()
        if not value:
            raise RuntimeError(f"Missing required env var: {name}. Please set it in .env")
        return value

    def _load_config(self) -> NanoRAGConfig:
        load_dotenv(dotenv_path=self.env_file, override=False)

        base_url = os.getenv(self.ENV_BASE_URL, self.DEFAULT_BASE_URL).strip()
        best_model = os.getenv(self.ENV_BEST_MODEL, self.DEFAULT_BEST_MODEL).strip()
        cheap_model = os.getenv(self.ENV_CHEAP_MODEL, self.DEFAULT_CHEAP_MODEL).strip()
        embedding_model = os.getenv(
            self.ENV_EMBEDDING_MODEL, self.DEFAULT_EMBEDDING_MODEL
        ).strip()

        if not base_url:
            raise RuntimeError(
                f"Missing env var: {self.ENV_BASE_URL}. Please set it in .env"
            )
        if not best_model:
            raise RuntimeError(
                f"Missing env var: {self.ENV_BEST_MODEL}. Please set it in .env"
            )
        if not cheap_model:
            raise RuntimeError(
                f"Missing env var: {self.ENV_CHEAP_MODEL}. Please set it in .env"
            )
        if not embedding_model:
            raise RuntimeError(
                f"Missing env var: {self.ENV_EMBEDDING_MODEL}. Please set it in .env"
            )

        return NanoRAGConfig(
            base_url=base_url,
            api_key=self._get_required_env(self.ENV_API_KEY),
            best_model=best_model,
            cheap_model=cheap_model,
            embedding_model=embedding_model,
        )

    def _ensure_rag(self) -> GraphRAG:
        if self.rag is None:
            self.reload()
        return self.rag

    def _run_async(self, coro):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        result_box: dict[str, Any] = {}
        error_box: dict[str, BaseException] = {}

        def _runner() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result_box["value"] = loop.run_until_complete(coro)
            except BaseException as exc:  # noqa: BLE001
                error_box["value"] = exc
            finally:
                loop.close()

        thread = Thread(target=_runner, daemon=True)
        thread.start()
        thread.join()

        if "value" in error_box:
            raise error_box["value"]
        return result_box.get("value")

    def _is_non_empty_json(self, file_path: Path) -> bool:
        if not file_path.exists() or file_path.stat().st_size == 0:
            return False
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            return bool(payload)
        except (OSError, json.JSONDecodeError):
            return False

    def has_reusable_index(self) -> bool:
        if not self.working_dir.exists():
            return False
        if not self.index_graphml_file.exists() or self.index_graphml_file.stat().st_size == 0:
            return False
        if not self.index_vdb_entities_file.exists() or self.index_vdb_entities_file.stat().st_size == 0:
            return False
        if not self._is_non_empty_json(self.index_full_docs_file):
            return False
        if not self._is_non_empty_json(self.index_text_chunks_file):
            return False
        return True

    async def _chat_complete_if_cache(
        self,
        model: str,
        prompt: str,
        system_prompt: str | None = None,
        history_messages: list[dict] | None = None,
        **kwargs,
    ) -> str:
        history_messages = history_messages or []
        hashing_kv: BaseKVStorage | None = kwargs.pop("hashing_kv", None)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(history_messages)
        messages.append({"role": "user", "content": prompt})

        if hashing_kv is not None:
            args_hash = compute_args_hash(model, messages)
            if_cache_return = await hashing_kv.get_by_id(args_hash)
            if if_cache_return is not None:
                return if_cache_return["return"]

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs,
            )
        except BadRequestError as exc:
            if "response_format" in str(exc):
                kwargs.pop("response_format", None)
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    **kwargs,
                )
            else:
                raise

        result = response.choices[0].message.content or ""

        if hashing_kv is not None:
            await hashing_kv.upsert({args_hash: {"return": result, "model": model}})
            await hashing_kv.index_done_callback()

        return result

    async def _embedding_raw(self, texts: list[str]) -> np.ndarray:
        try:
            response = await self.client.embeddings.create(
                model=self.config.embedding_model,
                input=texts,
                encoding_format="float",
            )
        except BadRequestError as exc:
            if "encoding_format" in str(exc):
                response = await self.client.embeddings.create(
                    model=self.config.embedding_model,
                    input=texts,
                )
            else:
                raise

        return np.array([item.embedding for item in response.data], dtype=np.float32)

    def _make_model_func(self, model: str):
        async def _model_func(
            prompt: str,
            system_prompt: str | None = None,
            history_messages: list[dict] | None = None,
            **kwargs,
        ) -> str:
            return await self._chat_complete_if_cache(
                model=model,
                prompt=prompt,
                system_prompt=system_prompt,
                history_messages=history_messages,
                **kwargs,
            )

        return _model_func

    def _get_cached_embedding_dim(self) -> int | None:
        if not self.index_vdb_entities_file.exists() or self.index_vdb_entities_file.stat().st_size == 0:
            return None
        try:
            payload = json.loads(self.index_vdb_entities_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        dim = payload.get("embedding_dim")
        if isinstance(dim, int) and dim > 0:
            return dim
        return None

    def _build_embedding_func(self) -> EmbeddingFunc:
        async def _embedding_func(texts: list[str]) -> np.ndarray:
            return await self._embedding_raw(texts)

        dim = self._get_cached_embedding_dim()
        if dim is None:
            probe = self._run_async(self._embedding_raw(["embedding dimension probe"]))
            dim = int(probe.shape[1])

        return EmbeddingFunc(
            embedding_dim=dim,
            max_token_size=8192,
            func=_embedding_func,
        )

    def _build_rag(self) -> GraphRAG:
        return GraphRAG(
            working_dir=str(self.working_dir),
            enable_llm_cache=self.enable_llm_cache,
            best_model_func=self._make_model_func(self.config.best_model),
            cheap_model_func=self._make_model_func(self.config.cheap_model),
            embedding_func=self._build_embedding_func(),
            best_model_max_token_size=self.best_model_max_token_size,
            cheap_model_max_token_size=self.cheap_model_max_token_size,
            best_model_max_async=self.best_model_max_async,
            cheap_model_max_async=self.cheap_model_max_async,
            embedding_batch_num=self.embedding_batch_num,
            embedding_func_max_async=self.embedding_func_max_async,
        )

    def reload(self) -> GraphRAG:
        self.rag = self._build_rag()
        return self.rag

    def clear_index(self, *, reload_after_clear: bool = True) -> None:
        if self.working_dir.exists():
            shutil.rmtree(self.working_dir)
        if reload_after_clear:
            self.reload()

    def incremental_insert(self, content: str, *, parts: int = 2) -> int:
        if parts < 2:
            raise ValueError("parts must be >= 2")

        rag = self._ensure_rag()
        inserted_parts = 0
        total = len(content)
        for idx in range(parts):
            start = (total * idx) // parts
            end = (total * (idx + 1)) // parts
            piece = content[start:end].strip()
            if not piece:
                continue
            rag.insert(piece)
            inserted_parts += 1
        return inserted_parts

    def index(
        self,
        content: str | list[str],
        *,
        reuse_existing: bool = True,
        force_rebuild: bool = False,
        incremental: bool = False,
        incremental_parts: int = 2,
    ) -> str:
        if force_rebuild:
            self.clear_index(reload_after_clear=True)

        if reuse_existing and self.has_reusable_index():
            return "reused"

        rag = self._ensure_rag()
        if incremental and isinstance(content, str):
            self.incremental_insert(content, parts=incremental_parts)
        else:
            rag.insert(content)
        return "indexed"

    def index_file(
        self,
        input_file: str | Path,
        *,
        reuse_existing: bool = True,
        force_rebuild: bool = False,
        incremental: bool = False,
        incremental_parts: int = 2,
        encoding: str = "utf-8",
    ) -> str:
        input_path = Path(input_file)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        content = input_path.read_text(encoding=encoding)
        return self.index(
            content,
            reuse_existing=reuse_existing,
            force_rebuild=force_rebuild,
            incremental=incremental,
            incremental_parts=incremental_parts,
        )

    def query(
        self,
        question: str,
        *,
        mode: str = "local",
        only_need_context: bool = False,
        **query_kwargs,
    ) -> str:
        if mode not in {"local", "global", "naive"}:
            raise ValueError("mode must be one of: local, global, naive")

        param = QueryParam(mode=mode, only_need_context=only_need_context)
        for key, value in query_kwargs.items():
            if not hasattr(param, key):
                raise ValueError(f"Unknown QueryParam field: {key}")
            setattr(param, key, value)

        rag = self._ensure_rag()
        return rag.query(question, param=param)

    def get_graph_data(self, *, graphml_path: str | Path | None = None) -> dict:
        graph_path = Path(graphml_path) if graphml_path else self.index_graphml_file
        if not graph_path.exists():
            raise FileNotFoundError(f"GraphML file not found: {graph_path}")
        graph = nx.read_graphml(graph_path)
        return self._graph_to_vis_payload(graph)

    def get_node_details(self, node_id: str, *, graphml_path: str | Path | None = None) -> dict:
        graph_path = Path(graphml_path) if graphml_path else self.index_graphml_file
        if not graph_path.exists():
            raise FileNotFoundError(f"GraphML file not found: {graph_path}")
        graph = nx.read_graphml(graph_path)
        if node_id not in graph:
            raise KeyError(f"Node not found: {node_id}")
        attrs = graph.nodes[node_id]
        return {
            "id": node_id,
            "entity_type": str(attrs.get("entity_type", "UNKNOWN")).strip('"'),
            "description": str(attrs.get("description", "")),
            "degree": graph.degree(node_id),
            "neighbors": list(graph.neighbors(node_id)),
        }

    def get_node_neighbors(
        self,
        node_id: str,
        *,
        depth: int = 1,
        graphml_path: str | Path | None = None,
    ) -> dict:
        graph_path = Path(graphml_path) if graphml_path else self.index_graphml_file
        if not graph_path.exists():
            raise FileNotFoundError(f"GraphML file not found: {graph_path}")
        graph = nx.read_graphml(graph_path)
        if node_id not in graph:
            raise KeyError(f"Node not found: {node_id}")

        reachable = {node_id}
        frontier = {node_id}
        for _ in range(depth):
            next_frontier: set[str] = set()
            for n in frontier:
                for nb in graph.neighbors(n):
                    if nb not in reachable:
                        next_frontier.add(nb)
            reachable |= next_frontier
            frontier = next_frontier
            if not frontier:
                break

        subgraph = graph.subgraph(reachable)
        return self._graph_to_vis_payload(subgraph)

    @staticmethod
    def _graph_to_vis_payload(graph: nx.Graph) -> dict:
        nodes = []
        edges = []

        for node_id, attrs in graph.nodes(data=True):
            degree = graph.degree(node_id)
            entity_type = str(attrs.get("entity_type", "UNKNOWN")).strip('"')
            description = str(attrs.get("description", ""))
            if len(description) > 500:
                description = description[:500] + "..."

            tooltip_lines = [
                f"id: {node_id}",
                f"type: {entity_type}",
                f"degree: {degree}",
            ]
            if description:
                tooltip_lines.extend(["", description])

            nodes.append(
                {
                    "id": str(node_id),
                    "label": str(node_id),
                    "group": entity_type,
                    "value": max(1, degree),
                    "title": "\\n".join(tooltip_lines),
                }
            )

        for source, target, attrs in graph.edges(data=True):
            try:
                weight = float(attrs.get("weight", 1.0))
            except (TypeError, ValueError):
                weight = 1.0

            description = str(attrs.get("description", ""))
            if len(description) > 500:
                description = description[:500] + "..."

            edges.append(
                {
                    "from": str(source),
                    "to": str(target),
                    "value": max(1.0, abs(weight)),
                    "label": f"{weight:.2f}",
                    "title": description,
                }
            )

        return {"nodes": nodes, "edges": edges}

    @staticmethod
    def _build_interactive_html(payload: dict, title: str) -> str:
        payload_json = json.dumps(payload, ensure_ascii=False)

        template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>__TITLE__</title>
  <script src="https://unpkg.com/vis-network@9.1.2/dist/vis-network.min.js"></script>
  <link href="https://unpkg.com/vis-network@9.1.2/dist/dist/vis-network.min.css" rel="stylesheet" />
  <style>
    body {
      margin: 0;
      font-family: Segoe UI, Tahoma, sans-serif;
      background: #f8fafc;
      color: #1f2937;
    }
    .toolbar {
      display: flex;
      gap: 10px;
      align-items: center;
      padding: 12px;
      border-bottom: 1px solid #e5e7eb;
      background: #ffffff;
      position: sticky;
      top: 0;
      z-index: 10;
    }
    .toolbar input {
      min-width: 320px;
      border: 1px solid #d1d5db;
      border-radius: 8px;
      padding: 8px 10px;
      font-size: 14px;
    }
    .toolbar button {
      border: 1px solid #d1d5db;
      border-radius: 8px;
      background: #ffffff;
      padding: 8px 10px;
      cursor: pointer;
    }
    .meta {
      margin-left: auto;
      font-size: 13px;
      color: #6b7280;
    }
    #network {
      width: 100%;
      height: calc(100vh - 58px);
      background: radial-gradient(circle at 20% 20%, #ffffff 0%, #eef2ff 100%);
    }
  </style>
</head>
<body>
  <div class="toolbar">
    <input id="keyword" type="text" placeholder="Search node id/type/description..." />
    <button id="searchBtn">Highlight</button>
    <button id="resetBtn">Reset</button>
    <button id="fitBtn">Fit</button>
    <div class="meta" id="meta"></div>
  </div>
  <div id="network"></div>

  <script>
    const payload = __PAYLOAD__;
    const nodeDataset = new vis.DataSet(payload.nodes);
    const edgeDataset = new vis.DataSet(payload.edges);

    const options = {
      nodes: {
        shape: "dot",
        scaling: { min: 8, max: 30 },
        font: { size: 14 },
        borderWidth: 1,
      },
      edges: {
        smooth: true,
        width: 1,
        color: { color: "#9ca3af" },
      },
      interaction: {
        hover: true,
        navigationButtons: true,
        keyboard: true,
      },
      physics: {
        stabilization: false,
        barnesHut: {
          gravitationalConstant: -2600,
          springLength: 150,
          springConstant: 0.03,
          damping: 0.1,
        },
      },
    };

    const container = document.getElementById("network");
    const network = new vis.Network(
      container,
      { nodes: nodeDataset, edges: edgeDataset },
      options
    );

    document.getElementById("meta").textContent =
      `${payload.nodes.length} nodes, ${payload.edges.length} edges`;

    function resetNodeStyle() {
      const updates = payload.nodes.map((n) => ({
        id: n.id,
        color: null,
        hidden: false,
      }));
      nodeDataset.update(updates);
    }

    function highlight() {
      const keyword = document.getElementById("keyword").value.trim().toLowerCase();
      if (!keyword) {
        resetNodeStyle();
        return;
      }

      const updates = payload.nodes.map((n) => {
        const text = `${n.label} ${n.group || ""} ${n.title || ""}`.toLowerCase();
        const matched = text.includes(keyword);
        return {
          id: n.id,
          color: matched
            ? { background: "#f59e0b", border: "#b45309" }
            : { background: "#e5e7eb", border: "#9ca3af" },
          hidden: false,
        };
      });
      nodeDataset.update(updates);
    }

    document.getElementById("searchBtn").addEventListener("click", highlight);
    document.getElementById("keyword").addEventListener("keydown", (evt) => {
      if (evt.key === "Enter") {
        highlight();
      }
    });
    document.getElementById("resetBtn").addEventListener("click", () => {
      document.getElementById("keyword").value = "";
      resetNodeStyle();
    });
    document.getElementById("fitBtn").addEventListener("click", () => network.fit());
  </script>
</body>
</html>
"""
        return template.replace("__PAYLOAD__", payload_json).replace("__TITLE__", title)

    def export_interactive_graph(
        self,
        *,
        graphml_path: str | Path | None = None,
        output_html_path: str | Path | None = None,
    ) -> Path:
        graph_path = Path(graphml_path) if graphml_path else self.index_graphml_file
        if not graph_path.exists():
            raise FileNotFoundError(f"GraphML file not found: {graph_path}")

        output_path = Path(output_html_path) if output_html_path else self.index_html_file
        graph = nx.read_graphml(graph_path)
        payload = self._graph_to_vis_payload(graph)
        html = self._build_interactive_html(payload, f"nano-graphrag graph: {graph_path.name}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")
        return output_path
