from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


_ENV_FILE = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_FILE, override=False)


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def _optional(name: str, default: str) -> str:
    return os.getenv(name, default).strip() or default


@dataclass(frozen=True)
class Settings:
    # NanoRAG LLM / embedding
    nano_base_url: str = field(
        default_factory=lambda: _optional(
            "NANO_GRAPHRAG_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
    )
    nano_api_key: str = field(default_factory=lambda: _require("NANO_GRAPHRAG_API_KEY"))
    nano_best_model: str = field(
        default_factory=lambda: _optional("NANO_GRAPHRAG_BEST_MODEL", "qwen3-max-2026-01-23")
    )
    nano_cheap_model: str = field(
        default_factory=lambda: _optional("NANO_GRAPHRAG_CHEAP_MODEL", "qwen3.5-flash")
    )
    nano_embedding_model: str = field(
        default_factory=lambda: _optional("NANO_GRAPHRAG_EMBEDDING_MODEL", "text-embedding-v3")
    )

    # Agent LLM (defaults to same as NanoRAG if not set)
    agent_api_key: str = field(
        default_factory=lambda: _optional("AGENT_API_KEY", os.getenv("NANO_GRAPHRAG_API_KEY", ""))
    )
    agent_base_url: str = field(
        default_factory=lambda: _optional(
            "AGENT_BASE_URL",
            _optional("NANO_GRAPHRAG_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        )
    )
    agent_model: str = field(
        default_factory=lambda: _optional(
            "AGENT_MODEL",
            _optional("NANO_GRAPHRAG_BEST_MODEL", "qwen3-max-2026-01-23"),
        )
    )

    # Storage
    projects_dir: Path = field(
        default_factory=lambda: Path(os.getenv("PROJECTS_DIR", "projects"))
    )
    upload_dir: Path = field(
        default_factory=lambda: Path(os.getenv("UPLOAD_DIR", "uploads"))
    )


def make_slug(filename: str) -> str:
    """Convert a filename to a filesystem-safe project slug.
    E.g. 'Part 1 (Final).md' → 'part_1__final__md'
    """
    base = re.sub(r"[^\w]", "_", filename.lower())
    base = re.sub(r"_+", "_", base).strip("_")
    return base or "project"


settings = Settings()
