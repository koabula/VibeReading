from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.api.schemas import IndexStatus
from backend.config import settings
from backend.core.state import app_state

router = APIRouter()

_SESSION_META = "session_meta.json"
_GRAPHML      = "graph_chunk_entity_relation.graphml"


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

    project_dir = settings.projects_dir / slug
    meta_path   = project_dir / _SESSION_META
    graphml     = project_dir / _GRAPHML

    if not (meta_path.exists() and graphml.exists()):
        raise HTTPException(
            status_code=404,
            detail=f"Project '{slug}' not found or its index is incomplete.",
        )

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read project metadata: {exc}") from exc

    filename  = meta.get("filename", slug)
    file_path = Path(meta.get("file_path", ""))

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
