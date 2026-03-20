from __future__ import annotations

import sys
from pathlib import Path

# Force UTF-8 on Windows at both the OS console level and Python stream level.
# SetConsoleOutputCP(65001) is the reliable fix; reconfigure is a belt-and-suspenders fallback.
if sys.platform == "win32":
    import os, ctypes
    try:
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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.api.routes import files, chat, projects as projects_route

app = FastAPI(title="VibeReading API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(projects_route.router, prefix="/api/projects", tags=["projects"])

frontend_dir = Path(__file__).parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
