from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path

from backend.api.schemas import IndexStatus


@dataclass
class AppState:
    """Singleton holding shared mutable state across requests."""

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    # Current indexing state
    index_status: IndexStatus = IndexStatus.idle
    index_message: str = ""
    current_filename: str | None = None
    current_file_path: Path | None = None
    current_project_slug: str | None = None

    # File type: "text" for plain-text/markdown, "pdf" for PDF uploads
    file_type: str = "text"

    # For PDF files: path to the original PDF, the sparse line→page map, and the
    # paragraph-level map {md_line: {"page": N, "y_frac": 0.0–1.0}} from MinerU bbox data.
    original_pdf_path: Path | None = None
    pdf_page_map: dict | None = None
    pdf_paragraph_map: dict | None = None

    # The NanoRAG instance – created lazily after first successful index
    _rag: object | None = field(default=None, repr=False)

    def set_status(self, status: IndexStatus, message: str = "") -> None:
        with self._lock:
            self.index_status = status
            self.index_message = message

    def get_rag(self):
        with self._lock:
            return self._rag

    def set_rag(self, rag) -> None:
        with self._lock:
            self._rag = rag

    def project_working_dir(self) -> Path | None:
        """Return the working directory for the currently active project."""
        from backend.config import settings  # lazy to avoid circular import
        if self.current_project_slug:
            return settings.projects_dir / self.current_project_slug
        return None


app_state = AppState()
