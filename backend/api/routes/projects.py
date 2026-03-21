from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.api.schemas import IndexStatus, ProjectChatHistory
from backend.config import settings
from backend.core.state import app_state

router = APIRouter()

_SESSION_META = "session_meta.json"
_GRAPHML      = "graph_chunk_entity_relation.graphml"
_CHAT_HISTORY = "chat_history.json"


# ---------------------------------------------------------------------------
# Schemas (local to this module, simple enough to not need schemas.py)
# ---------------------------------------------------------------------------

class ProjectInfo(BaseModel):
    slug: str
    filename: str
    file_path: str
    indexed_at: str
    is_active: bool


class ProjectListResponse(BaseModel):
    projects: list[ProjectInfo]


class ActivateResponse(BaseModel):
    status: str
    slug: str
    filename: str
    message: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iter_projects() -> list[dict]:
    """Scan the projects directory and return valid project metadata dicts."""
    projects_dir = settings.projects_dir
    if not projects_dir.exists():
        return []

    results = []
    for subdir in sorted(projects_dir.iterdir()):
        if not subdir.is_dir():
            continue
        meta_path = subdir / _SESSION_META
        graphml   = subdir / _GRAPHML
        if not (meta_path.exists() and graphml.exists()):
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta.setdefault("slug", subdir.name)
            results.append(meta)
        except Exception:
            continue
    return results


def _project_dir(slug: str) -> Path:
    return settings.projects_dir / slug


def _ensure_project_exists(slug: str) -> Path:
    project_dir = _project_dir(slug)
    meta_path = project_dir / _SESSION_META
    graphml = project_dir / _GRAPHML
    if not (meta_path.exists() and graphml.exists()):
        raise HTTPException(
            status_code=404,
            detail=f"Project '{slug}' not found or its index is incomplete.",
        )
    return project_dir


def _chat_history_path(slug: str) -> Path:
    return _project_dir(slug) / _CHAT_HISTORY


def _load_chat_history(slug: str) -> ProjectChatHistory:
    path = _chat_history_path(slug)
    if not path.exists():
        return ProjectChatHistory()

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read chat history: {exc}") from exc

    try:
        return ProjectChatHistory.model_validate(payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Invalid chat history format: {exc}") from exc


def _save_chat_history(slug: str, history: ProjectChatHistory) -> None:
    path = _chat_history_path(slug)
    path.write_text(
        json.dumps(history.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=ProjectListResponse)
async def list_projects() -> ProjectListResponse:
    """Return all previously indexed projects."""
    raw      = _iter_projects()
    active   = app_state.current_project_slug
    projects = [
        ProjectInfo(
            slug       = p.get("slug", ""),
            filename   = p.get("filename", ""),
            file_path  = p.get("file_path", ""),
            indexed_at = p.get("indexed_at", ""),
            is_active  = p.get("slug", "") == active,
        )
        for p in raw
    ]
    return ProjectListResponse(projects=projects)


@router.post("/{slug}/activate", response_model=ActivateResponse)
async def activate_project(slug: str) -> ActivateResponse:
    """Load an existing project without re-indexing."""
    if app_state.index_status == IndexStatus.indexing:
        raise HTTPException(status_code=409, detail="Indexing already in progress")

    project_dir = _ensure_project_exists(slug)
    meta_path   = project_dir / _SESSION_META

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read project metadata: {exc}") from exc

    filename          = meta.get("filename", slug)
    file_path         = Path(meta.get("file_path", ""))
    file_type         = meta.get("file_type", "text")
    original_pdf_str  = meta.get("original_pdf_path")
    original_pdf_path = Path(original_pdf_str) if original_pdf_str else None

    # Restore page map and paragraph map for PDF projects
    page_map: dict | None = None
    paragraph_map: dict | None = None
    if file_type == "pdf":
        page_map_path = project_dir / "page_map.json"
        if page_map_path.exists():
            try:
                raw_map = json.loads(page_map_path.read_text(encoding="utf-8"))
                page_map = {int(k): v for k, v in raw_map.items()}
            except Exception:
                page_map = None

        para_map_path = project_dir / "paragraph_map.json"
        if para_map_path.exists():
            try:
                raw_para = json.loads(para_map_path.read_text(encoding="utf-8"))
                paragraph_map = {int(k): v for k, v in raw_para.items()}
            except Exception:
                paragraph_map = None

    def _do_load() -> None:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
        from NanoRAG import NanoRAG  # noqa: PLC0415

        rag = NanoRAG(
            working_dir=project_dir,
            env_file=Path(__file__).parent.parent.parent.parent / ".env",
        )
        app_state.current_filename     = filename
        app_state.current_file_path    = file_path if file_path.exists() else None
        app_state.current_project_slug = slug
        app_state.file_type            = file_type

        # Resolve the original PDF path: prefer the project-local copy so the
        # project is self-contained even if uploads/ was cleared.
        resolved_pdf: Path | None = None
        if file_type == "pdf":
            # First try the project-local copy (original.pdf / original.PDF etc.)
            for candidate in project_dir.glob("original.*"):
                if candidate.suffix.lower() == ".pdf":
                    resolved_pdf = candidate
                    break
            # Fall back to the path stored in metadata
            if resolved_pdf is None and original_pdf_path and original_pdf_path.exists():
                resolved_pdf = original_pdf_path

        app_state.original_pdf_path    = resolved_pdf
        app_state.pdf_page_map         = page_map
        app_state.pdf_paragraph_map    = paragraph_map
        app_state.set_rag(rag)
        app_state.set_status(IndexStatus.ready, f"Loaded · {filename}")

    try:
        await asyncio.to_thread(_do_load)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to load project: {exc}") from exc

    return ActivateResponse(
        status   = "ready",
        slug     = slug,
        filename = filename,
        message  = f"Project '{filename}' loaded successfully.",
    )


@router.delete("/{slug}")
async def delete_project(slug: str) -> dict:
    """Delete a project and all its index data. Cannot delete the active project."""
    if app_state.current_project_slug == slug:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete the currently active project. Activate another project first.",
        )

    project_dir = settings.projects_dir / slug
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail=f"Project '{slug}' not found.")

    shutil.rmtree(project_dir, ignore_errors=True)
    return {"status": "deleted", "slug": slug}


@router.get("/{slug}/chat-history", response_model=ProjectChatHistory)
async def get_chat_history(slug: str) -> ProjectChatHistory:
    _ensure_project_exists(slug)
    return _load_chat_history(slug)


@router.put("/{slug}/chat-history", response_model=ProjectChatHistory)
async def put_chat_history(slug: str, history: ProjectChatHistory) -> ProjectChatHistory:
    _ensure_project_exists(slug)
    _save_chat_history(slug, history)
    return history
