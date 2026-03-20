from __future__ import annotations

import json
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File

from backend.api.schemas import (
    FileContentResponse,
    FileStatusResponse,
    FileUploadResponse,
    IndexStatus,
)
from backend.config import settings, make_slug
from backend.core.state import app_state

router = APIRouter()

_SESSION_META = "session_meta.json"
_GRAPHML      = "graph_chunk_entity_relation.graphml"


# ---------------------------------------------------------------------------
# Session metadata helpers (per-project)
# ---------------------------------------------------------------------------

def _project_dir(slug: str) -> Path:
    return settings.projects_dir / slug


def _save_session_meta(slug: str, filename: str, file_path: Path) -> None:
    d = _project_dir(slug)
    d.mkdir(parents=True, exist_ok=True)
    meta = {
        "filename": filename,
        "slug": slug,
        "file_path": str(file_path),
        "indexed_at": datetime.now(timezone.utc).isoformat(),
    }
    (d / _SESSION_META).write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")


def _load_session_meta(slug: str) -> dict | None:
    d = _project_dir(slug)
    meta_path = d / _SESSION_META
    if meta_path.exists() and (d / _GRAPHML).exists():
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


# ---------------------------------------------------------------------------
# One-time migration: nano_graphrag_cache/ → projects/{slug}/
# ---------------------------------------------------------------------------

def _migrate_legacy_data() -> None:
    """Move old single-project data (nano_graphrag_cache/) into the new structure."""
    old_dir  = Path("nano_graphrag_cache")
    old_meta = old_dir / _SESSION_META

    if settings.projects_dir.exists() or not old_meta.exists():
        return  # nothing to migrate

    try:
        meta = json.loads(old_meta.read_text(encoding="utf-8"))
        slug = make_slug(meta.get("filename", "legacy"))
        dest = _project_dir(slug)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(old_dir), str(dest))
        print(f"[VibeReading] Migrated legacy data → projects/{slug}/")
    except Exception as exc:
        print(f"[VibeReading] Legacy migration skipped: {exc}")


_migrate_legacy_data()


# ---------------------------------------------------------------------------
# Background indexing thread
# ---------------------------------------------------------------------------

def _run_indexing(file_path: Path, slug: str, filename: str) -> None:
    """Background thread: initialise NanoRAG and index the uploaded file."""
    import sys, os

    # Re-apply UTF-8 on Windows (tqdm writes Braille chars that choke GBK console)
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
            ctypes.windll.kernel32.SetConsoleCP(65001)
        except Exception:
            pass
        os.environ.setdefault("PYTHONIOENCODING", "utf-8:replace")
        for _s in ("stdout", "stderr"):
            _stream = getattr(sys, _s, None)
            if _stream and hasattr(_stream, "reconfigure"):
                try:
                    _stream.reconfigure(encoding="utf-8", errors="replace")
                except Exception:
                    pass

    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from NanoRAG import NanoRAG  # noqa: PLC0415

    working_dir = _project_dir(slug)
    working_dir.mkdir(parents=True, exist_ok=True)

    app_state.set_status(IndexStatus.indexing, "Building knowledge graph…")
    try:
        rag = NanoRAG(
            working_dir=working_dir,
            env_file=Path(__file__).parent.parent.parent.parent / ".env",
        )
        status = rag.index_file(
            file_path,
            reuse_existing=False,
            force_rebuild=True,
            incremental=True,
            incremental_parts=4,
        )
        app_state.set_rag(rag)
        app_state.set_status(IndexStatus.ready, f"Index complete ({status})")
        _save_session_meta(slug=slug, filename=filename, file_path=file_path)
    except Exception as exc:  # noqa: BLE001
        app_state.set_status(IndexStatus.error, str(exc))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)) -> FileUploadResponse:
    if app_state.index_status == IndexStatus.indexing:
        raise HTTPException(status_code=409, detail="Indexing already in progress")

    filename = file.filename or "upload.txt"
    suffix   = Path(filename).suffix.lower()
    if suffix not in {".txt", ".md", ""}:
        raise HTTPException(
            status_code=415,
            detail="Only plain-text (.txt) and Markdown (.md) files are supported",
        )

    slug = make_slug(filename)

    upload_dir = settings.upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / filename
    dest.write_bytes(await file.read())

    app_state.current_filename    = filename
    app_state.current_file_path   = dest
    app_state.current_project_slug = slug
    app_state.set_status(IndexStatus.indexing, "Queued for indexing")

    thread = threading.Thread(
        target=_run_indexing, args=(dest, slug, filename), daemon=True
    )
    thread.start()

    return FileUploadResponse(
        filename=filename,
        status=IndexStatus.indexing,
        message="File uploaded, indexing started in background",
    )


@router.get("/status", response_model=FileStatusResponse)
async def get_status() -> FileStatusResponse:
    return FileStatusResponse(
        status=app_state.index_status,
        filename=app_state.current_filename,
        message=app_state.index_message,
    )


@router.get("/content", response_model=FileContentResponse)
async def get_content() -> FileContentResponse:
    path = app_state.current_file_path
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="No file has been uploaded yet")
    return FileContentResponse(
        filename=app_state.current_filename or path.name,
        content=path.read_text(encoding="utf-8"),
    )
