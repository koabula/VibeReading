"""MinerU PDF parsing client.

Calls the MinerU 精准解析 API to convert a PDF file into Markdown and a
structured content list, then builds a line-to-page mapping so the Agent can
cite specific pages in the original PDF.

API flow (batch file-upload mode):
  1. POST /api/v4/file-urls/batch  → batch_id + OSS upload URL
  2. PUT <oss_url>                 → upload the raw PDF bytes
  3. GET /api/v4/extract-results/batch/{batch_id}  (poll until done)
  4. Download full_zip_url → extract full.md + *_content_list.json
"""

from __future__ import annotations

import asyncio
import io
import json
import time
import zipfile
from pathlib import Path
from typing import Any

import httpx

MINERU_BASE = "https://mineru.net"
_POLL_INTERVAL = 5   # seconds between status polls
_POLL_TIMEOUT  = 600 # seconds before we give up


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def parse_pdf(
    pdf_path: Path, api_key: str
) -> tuple[str, dict[int, int], dict[str, Any], dict[int, dict[str, Any]]]:
    """Parse *pdf_path* via MinerU and return
    ``(markdown_text, page_map, model_data, paragraph_map)``.

    ``page_map`` maps every 1-based markdown line number to the 1-based PDF
    page number it came from.  The mapping is sparse: only the *first* line of
    each new page is stored; callers should use :func:`line_to_page` to look
    up arbitrary line numbers.

    ``paragraph_map`` provides sub-page precision: each entry maps a 1-based
    markdown line to ``{"page": N, "y_frac": 0.0–1.0}`` derived from
    MinerU's para_block bounding boxes.  Empty dict if unavailable.

    ``model_data`` is the raw ``*_model.json`` dict from MinerU.
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        batch_id, oss_url = await _request_upload_url(client, api_key, pdf_path.name)
        await _upload_file(client, oss_url, pdf_path)
        zip_url = await _poll_until_done(client, api_key, batch_id)
        markdown, content_list, model_data = await _download_and_extract(client, zip_url)

    # Prefer the richer model.json structure for page mapping (para_blocks give
    # one anchor per page with verified text); fall back to content_list.
    # Guard with isinstance: some MinerU zip variants return a list as the root
    # of *_model.json rather than the expected {"pdf_info": [...]} dict.
    clean_model = model_data if isinstance(model_data, dict) else {}
    if clean_model.get("pdf_info"):
        page_map      = _build_page_map_from_model(clean_model, markdown)
        paragraph_map = _build_paragraph_map_from_model(clean_model, markdown)
    else:
        page_map      = _build_page_map(content_list, markdown)
        paragraph_map = {}
    return markdown, page_map, clean_model, paragraph_map


def line_to_page(line_number: int, page_map: dict[int, int]) -> int:
    """Return the 1-based PDF page that contains *line_number*.

    ``page_map`` is sparse (only page-boundary lines are stored).  We find the
    largest stored key that is ≤ *line_number* and return its page value.
    Falls back to page 1 if the map is empty.
    """
    if not page_map:
        return 1
    keys = sorted(page_map.keys())
    result = page_map[keys[0]]
    for k in keys:
        if k <= line_number:
            result = page_map[k]
        else:
            break
    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _request_upload_url(
    client: httpx.AsyncClient, api_key: str, filename: str
) -> tuple[str, str]:
    """Request a batch upload URL from MinerU. Returns (batch_id, oss_url)."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "files": [{"name": filename}],
        "model_version": "vlm",
    }
    resp = await client.post(
        f"{MINERU_BASE}/api/v4/file-urls/batch",
        headers=headers,
        json=payload,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"MinerU upload-URL request failed: {data.get('msg')}")
    batch_id: str = data["data"]["batch_id"]
    oss_url: str  = data["data"]["file_urls"][0]
    return batch_id, oss_url


async def _upload_file(
    client: httpx.AsyncClient, oss_url: str, pdf_path: Path
) -> None:
    """PUT the PDF bytes to the OSS signed URL (no auth header required)."""
    pdf_bytes = await asyncio.to_thread(pdf_path.read_bytes)
    resp = await client.put(oss_url, content=pdf_bytes, timeout=120.0)
    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"MinerU OSS upload failed with HTTP {resp.status_code}: {resp.text[:200]}"
        )


async def _poll_until_done(
    client: httpx.AsyncClient, api_key: str, batch_id: str
) -> str:
    """Poll the batch result endpoint until state == 'done'. Returns full_zip_url."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "*/*",
    }
    url = f"{MINERU_BASE}/api/v4/extract-results/batch/{batch_id}"
    deadline = time.monotonic() + _POLL_TIMEOUT

    while time.monotonic() < deadline:
        await asyncio.sleep(_POLL_INTERVAL)
        resp = await client.get(url, headers=headers, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"MinerU poll error: {data.get('msg')}")

        results: list[dict[str, Any]] = data["data"].get("extract_result", [])
        if not results:
            continue

        item = results[0]
        state: str = item.get("state", "")

        if state == "done":
            return item["full_zip_url"]
        if state == "failed":
            raise RuntimeError(f"MinerU parsing failed: {item.get('err_msg', 'unknown error')}")
        # states: pending / running / converting / waiting-file → keep polling

    raise TimeoutError(
        f"MinerU parsing timed out after {_POLL_TIMEOUT}s for batch {batch_id}"
    )


async def _download_and_extract(
    client: httpx.AsyncClient, zip_url: str
) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    """Download the result zip and extract full.md, content_list.json, and model.json."""
    resp = await client.get(zip_url, timeout=120.0, follow_redirects=True)
    resp.raise_for_status()
    zip_bytes = resp.content

    markdown = ""
    content_list: list[dict[str, Any]] = []
    model_data: dict[str, Any] = {}

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()

        # Locate full.md
        md_candidates = [n for n in names if n.endswith("full.md")]
        if md_candidates:
            with zf.open(md_candidates[0]) as f:
                markdown = f.read().decode("utf-8")

        # Locate *_content_list.json
        cl_candidates = [n for n in names if n.endswith("_content_list.json")]
        if cl_candidates:
            with zf.open(cl_candidates[0]) as f:
                content_list = json.loads(f.read().decode("utf-8"))

        # Locate *_model.json (contains pdf_info with para_blocks + bounding boxes)
        model_candidates = [n for n in names if n.endswith("_model.json")]
        if model_candidates:
            with zf.open(model_candidates[0]) as f:
                model_data = json.loads(f.read().decode("utf-8"))

    if not markdown:
        raise RuntimeError("MinerU result zip did not contain full.md")

    return markdown, content_list, model_data


def _build_page_map_from_model(
    model_data: dict[str, Any], markdown: str
) -> dict[int, int]:
    """Build a sparse line→page mapping using MinerU's ``*_model.json`` structure.

    ``model_data["pdf_info"]`` is a list where each element represents one PDF
    page (0-based index = page_idx).  Each page contains ``para_blocks``, each
    block has ``lines > spans > content`` text fields plus a ``bbox``.

    For every page we take the first para_block's concatenated span text, search
    for it as a substring in the markdown lines, and record the matching line
    number as the start of that page.  This gives paragraph-level precision
    compared to the flat content_list approach.

    Falls back to ``{1: 1}`` if model_data is empty or unusable.
    """
    pdf_info: list[dict[str, Any]] = model_data.get("pdf_info", [])
    if not pdf_info or not markdown:
        return {1: 1}

    md_lines = markdown.splitlines()
    page_map: dict[int, int] = {}
    search_start = 0  # advance forward so we don't re-match earlier regions

    for page_obj in pdf_info:
        page_num: int = page_obj.get("page_idx", 0) + 1  # convert to 1-based
        para_blocks: list[dict[str, Any]] = page_obj.get("para_blocks", [])

        if not para_blocks:
            page_map.setdefault(search_start + 1, page_num)
            continue

        # Gather text from the first para_block's spans
        first_block = para_blocks[0]
        text_parts: list[str] = []
        for line in first_block.get("lines", []):
            for span in line.get("spans", []):
                chunk = span.get("content", "").strip()
                if chunk:
                    text_parts.append(chunk)
        probe = " ".join(text_parts)[:40].strip()

        if not probe:
            page_map.setdefault(search_start + 1, page_num)
            continue

        matched_line: int | None = None
        for idx in range(search_start, len(md_lines)):
            if probe in md_lines[idx]:
                matched_line = idx + 1  # convert to 1-based
                search_start = idx      # advance cursor for next page
                break

        if matched_line is not None:
            page_map[matched_line] = page_num
        else:
            page_map.setdefault(search_start + 1, page_num)

    return page_map or {1: 1}


def _build_paragraph_map_from_model(
    model_data: dict[str, Any], markdown: str
) -> dict[int, dict[str, Any]]:
    """Build a dense paragraph-level map from MinerU's ``*_model.json`` structure.

    For *every* para_block across all pages (not just the first per page) we
    try to locate the matching markdown line via substring search and record:

        {md_line: {"page": <1-based page>, "y_frac": <0.0–1.0 from page top>}}

    ``y_frac`` is derived from ``bbox[1] / page_height`` where the page height
    comes from ``page_obj["page_size"][1]``.  bbox coordinates are in MinerU's
    image-space (origin at top-left), so y_frac increases downward.

    Returns an empty dict if model_data is unusable so callers can fall back
    to the simpler page map.
    """
    pdf_info: list[dict[str, Any]] = model_data.get("pdf_info", [])
    if not pdf_info or not markdown:
        return {}

    md_lines = markdown.splitlines()
    para_map: dict[int, dict[str, Any]] = {}
    search_start = 0  # advance monotonically to avoid re-matching earlier text

    for page_obj in pdf_info:
        page_num: int = page_obj.get("page_idx", 0) + 1
        page_size: list = page_obj.get("page_size", [612, 792])
        page_height: float = float(page_size[1]) if len(page_size) >= 2 else 792.0

        para_blocks: list[dict[str, Any]] = page_obj.get("para_blocks", [])

        for block in para_blocks:
            # Gather span text to build a search probe.
            text_parts: list[str] = []
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    chunk = span.get("content", "").strip()
                    if chunk:
                        text_parts.append(chunk)
            probe = " ".join(text_parts)[:40].strip()
            if not probe:
                continue

            matched_line: int | None = None
            for idx in range(search_start, len(md_lines)):
                if probe in md_lines[idx]:
                    matched_line = idx + 1  # 1-based
                    search_start = idx      # advance cursor
                    break

            if matched_line is None:
                continue

            bbox: list = block.get("bbox", [0, 0, 0, 0])
            y_top  = float(bbox[1]) if len(bbox) >= 2 else 0.0
            y_frac = round(max(0.0, min(1.0, y_top / page_height)), 4) if page_height else 0.0

            # Keep only the first block per markdown line to avoid duplicate keys.
            if matched_line not in para_map:
                para_map[matched_line] = {"page": page_num, "y_frac": y_frac}

    return para_map


def _build_page_map(
    content_list: list[dict[str, Any]], markdown: str = ""
) -> dict[int, int]:
    """Build a sparse line→page mapping from the content_list items.

    When *markdown* is provided we use substring matching to find the exact
    line in ``full.md`` where each PDF page begins, producing a precise map.
    Specifically, for the first content_list item on each new page we take the
    first 40 characters of its ``text`` field and search for that substring
    among the markdown lines.  The first matching line number is used as the
    page boundary.

    If *markdown* is empty (legacy / fallback) we fall back to the old
    newline-count estimation so existing callers are not broken.

    Returns a sparse dict mapping {line_number: page_number}.
    """
    if not content_list:
        return {1: 1}

    # ── Text-alignment mode ──────────────────────────────────────────────────
    if markdown:
        md_lines = markdown.splitlines()

        page_map: dict[int, int] = {}
        current_page = -1
        search_start = 0  # advance forward so we don't match the same region twice

        for item in content_list:
            page_idx: int = item.get("page_idx", 0)
            page_num = page_idx + 1

            if page_num == current_page:
                continue  # only record the first item of each new page

            current_page = page_num
            text: str = (item.get("text", "") or "").strip()
            if not text:
                # No text to match; fall back to current search position
                page_map[search_start + 1] = page_num
                continue

            probe = text[:40]
            matched_line: int | None = None
            for idx in range(search_start, len(md_lines)):
                if probe in md_lines[idx]:
                    matched_line = idx + 1  # convert to 1-based
                    search_start = idx      # advance cursor for next page
                    break

            if matched_line is not None:
                page_map[matched_line] = page_num
            else:
                # Probe not found; keep the cursor and record approximate position
                page_map[search_start + 1] = page_num

        if not page_map:
            page_map[1] = 1
        return page_map

    # ── Fallback: line-count estimation (no markdown provided) ───────────────
    fallback_map: dict[int, int] = {}
    current_line = 1
    current_page = -1

    for item in content_list:
        page_idx: int = item.get("page_idx", 0)
        page_num = page_idx + 1

        if page_num != current_page:
            fallback_map[current_line] = page_num
            current_page = page_num

        text: str = item.get("text", "") or ""
        item_lines = text.count("\n") + 1 + 1
        current_line += max(item_lines, 1)

    return fallback_map
