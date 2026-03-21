from __future__ import annotations

import asyncio
import json
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse

from backend.api.schemas import (
    FileContentResponse,
    FileStatusResponse,
    FileUploadResponse,
    IndexStatus,
)
from backend.config import settings, make_slug
from backend.core.state import app_state

router = APIRouter()

_SESSION_META   = "session_meta.json"
_GRAPHML        = "graph_chunk_entity_relation.graphml"
_PAGE_MAP       = "page_map.json"
_PARAGRAPH_MAP  = "paragraph_map.json"


# ---------------------------------------------------------------------------
# Session metadata helpers (per-project)
# ---------------------------------------------------------------------------

def _project_dir(slug: str) -> Path:
    return settings.projects_dir / slug


def _save_session_meta(
    slug: str,
    filename: str,
    file_path: Path,
    file_type: str = "text",
    original_pdf_path: Path | None = None,
) -> None:
    d = _project_dir(slug)
    d.mkdir(parents=True, exist_ok=True)
    meta = {
        "filename": filename,
        "slug": slug,
        "file_path": str(file_path),
        "file_type": file_type,
        "original_pdf_path": str(original_pdf_path) if original_pdf_path else None,
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
# Background indexing — text files (existing logic)
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
            incremental_parts=2,
        )
        app_state.set_rag(rag)
        app_state.set_status(IndexStatus.ready, f"Index complete ({status})")
        _save_session_meta(slug=slug, filename=filename, file_path=file_path)
    except Exception as exc:  # noqa: BLE001
        app_state.set_status(IndexStatus.error, str(exc))


# ---------------------------------------------------------------------------
# Background indexing — PDF files (MinerU + NanoRAG)
# ---------------------------------------------------------------------------

def _run_pdf_indexing(pdf_path: Path, slug: str, filename: str) -> None:
    """Background thread: convert PDF via MinerU, then index the markdown."""
    import sys, os

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
    from backend.core.mineru import parse_pdf  # noqa: PLC0415
    from dotenv import load_dotenv as _reload_env  # noqa: PLC0415

    working_dir = _project_dir(slug)
    working_dir.mkdir(parents=True, exist_ok=True)

    # Re-read .env on every call so the key is picked up even when the user
    # adds MINERU_API_KEY after the server has already started (uvicorn --reload
    # only watches .py files, not .env).
    _env_file = Path(__file__).parent.parent.parent.parent / ".env"
    _reload_env(dotenv_path=_env_file, override=True)
    api_key = os.getenv("MINERU_API_KEY", "").strip()

    if not api_key:
        app_state.set_status(
            IndexStatus.error,
            "MINERU_API_KEY is not set. Please add it to your .env file.",
        )
        return

    # Step 1: convert PDF → markdown via MinerU
    app_state.set_status(IndexStatus.indexing, "Converting PDF via MinerU…")
    try:
        markdown_text, page_map, model_data, paragraph_map = asyncio.run(
            parse_pdf(pdf_path, api_key)
        )
    except Exception as exc:
        app_state.set_status(IndexStatus.error, f"MinerU error: {exc}")
        return

    # Step 2: index the markdown with NanoRAG using the in-memory string.
    # IMPORTANT: force_rebuild=True triggers NanoRAG.clear_index() which calls
    # shutil.rmtree(working_dir), wiping the entire project directory.  By passing
    # markdown_text directly (instead of a file path) and running NanoRAG *first*,
    # we ensure the rmtree fires before we write any of our own files.
    app_state.set_status(IndexStatus.indexing, "Building knowledge graph…")
    try:
        rag = NanoRAG(
            working_dir=working_dir,
            env_file=Path(__file__).parent.parent.parent.parent / ".env",
        )
        status = rag.index(
            markdown_text,
            reuse_existing=False,
            force_rebuild=True,
            incremental=True,
            incremental_parts=2,
        )
        app_state.set_rag(rag)
    except Exception as exc:  # noqa: BLE001
        app_state.set_status(IndexStatus.error, str(exc))
        return

    # Step 3: persist files AFTER NanoRAG's rmtree has already executed.
    # working_dir now exists again (NanoRAG recreated it for its own index files).
    md_path = working_dir / "full.md"
    md_path.write_text(markdown_text, encoding="utf-8")

    page_map_path = working_dir / _PAGE_MAP
    page_map_path.write_text(
        json.dumps({str(k): v for k, v in page_map.items()}, ensure_ascii=False),
        encoding="utf-8",
    )

    # Save the paragraph map {md_line: {page, y_frac}} for sub-page navigation.
    if paragraph_map:
        para_map_path = working_dir / _PARAGRAPH_MAP
        para_map_path.write_text(
            json.dumps({str(k): v for k, v in paragraph_map.items()}, ensure_ascii=False),
            encoding="utf-8",
        )

    # Save the raw MinerU model.json (pdf_info with para_blocks + bboxes).
    if isinstance(model_data, dict) and model_data:
        model_json_path = working_dir / "model.json"
        model_json_path.write_text(
            json.dumps(model_data, ensure_ascii=False), encoding="utf-8"
        )

    # Keep a self-contained copy of the original PDF inside the project directory
    # so the viewer works even if the uploads/ folder is cleared later.
    project_pdf_path = working_dir / ("original" + pdf_path.suffix.lower())
    import shutil as _shutil
    _shutil.copy2(str(pdf_path), str(project_pdf_path))

    # Step 4: update app_state and save session metadata
    app_state.file_type           = "pdf"
    app_state.original_pdf_path   = project_pdf_path
    app_state.pdf_page_map        = page_map
    app_state.pdf_paragraph_map   = paragraph_map or None
    app_state.current_file_path   = md_path

    app_state.set_status(IndexStatus.ready, f"Index complete ({status})")
    _save_session_meta(
        slug=slug,
        filename=filename,
        file_path=md_path,
        file_type="pdf",
        original_pdf_path=project_pdf_path,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)) -> FileUploadResponse:
    if app_state.index_status == IndexStatus.indexing:
        raise HTTPException(status_code=409, detail="Indexing already in progress")

    filename = file.filename or "upload.txt"
    suffix   = Path(filename).suffix.lower()
    if suffix not in {".txt", ".md", ".pdf", ""}:
        raise HTTPException(
            status_code=415,
            detail="Only plain-text (.txt), Markdown (.md), and PDF (.pdf) files are supported",
        )

    slug = make_slug(filename)

    upload_dir = settings.upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / filename
    dest.write_bytes(await file.read())

    app_state.current_filename     = filename
    app_state.current_file_path    = dest
    app_state.current_project_slug = slug
    app_state.set_status(IndexStatus.indexing, "Queued for indexing")

    if suffix == ".pdf":
        # Reset PDF-specific state
        app_state.file_type         = "pdf"
        app_state.original_pdf_path = dest
        app_state.pdf_page_map      = None

        thread = threading.Thread(
            target=_run_pdf_indexing, args=(dest, slug, filename), daemon=True
        )
    else:
        app_state.file_type         = "text"
        app_state.original_pdf_path = None
        app_state.pdf_page_map      = None

        thread = threading.Thread(
            target=_run_indexing, args=(dest, slug, filename), daemon=True
        )

    thread.start()

    return FileUploadResponse(
        filename=filename,
        slug=slug,
        status=IndexStatus.indexing,
        message="File uploaded, indexing started in background",
    )


@router.get("/status", response_model=FileStatusResponse)
async def get_status() -> FileStatusResponse:
    return FileStatusResponse(
        status=app_state.index_status,
        filename=app_state.current_filename,
        slug=app_state.current_project_slug,
        message=app_state.index_message,
        file_type=app_state.file_type,
        pdf_page_map=app_state.pdf_page_map,
        pdf_paragraph_map=app_state.pdf_paragraph_map,
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


@router.get("/raw")
async def get_raw_file() -> FileResponse:
    """Serve the original uploaded file (used for in-browser PDF display)."""
    if app_state.file_type == "pdf" and app_state.original_pdf_path:
        path = app_state.original_pdf_path
    else:
        path = app_state.current_file_path

    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="No file has been uploaded yet")

    media_type = "application/pdf" if path.suffix.lower() == ".pdf" else "text/plain"
    return FileResponse(
        path=path,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{path.name}"'},
    )
