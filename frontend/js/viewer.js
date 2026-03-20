/* ── Document Viewer ──────────────────────────────────────────────────────── */

// PDF.js worker URL (must match the pdf.min.js version loaded in index.html)
const _PDFJS_WORKER_SRC =
  'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

// Module-level PDF state so we can destroy/reload on project switch
let _pdfDoc        = null;   // pdfjsLib.PDFDocumentProxy
let _pdfTotalPages = 0;
let _pdfBaseScale  = 1.0;    // scale that fits the page to the container width
let _pdfZoomFactor = 1.0;    // user-controlled zoom multiplier (1.0 = fit width)

const _PDF_ZOOM_STEP = 0.25;
const _PDF_ZOOM_MIN  = 0.25;
const _PDF_ZOOM_MAX  = 4.0;

const Viewer = {
  currentFileType: 'text',
  /** Sparse line→page map for PDF documents: {lineNumber: pageNumber, …} */
  pdfPageMap: null,
  /** Paragraph-level map from MinerU bbox data: {lineNumber: {page, y_frac}, …} */
  pdfParagraphMap: null,

  /**
   * Load and render the current document.
   * Fetches /api/files/status to determine file_type, then either renders
   * the PDF with PDF.js or the Markdown content.
   */
  async loadContent() {
    try {
      const statusRes = await fetch('/api/files/status');
      if (!statusRes.ok) return;
      const status = await statusRes.json();
      this.currentFileType = status.file_type || 'text';

      // Parse pdf_page_map: backend sends string keys; convert to integers.
      if (status.pdf_page_map && typeof status.pdf_page_map === 'object') {
        this.pdfPageMap = {};
        for (const [k, v] of Object.entries(status.pdf_page_map)) {
          this.pdfPageMap[parseInt(k, 10)] = v;
        }
      } else {
        this.pdfPageMap = null;
      }

      // Parse pdf_paragraph_map: {lineNumber: {page, y_frac}}
      if (status.pdf_paragraph_map && typeof status.pdf_paragraph_map === 'object') {
        this.pdfParagraphMap = {};
        for (const [k, v] of Object.entries(status.pdf_paragraph_map)) {
          this.pdfParagraphMap[parseInt(k, 10)] = v;
        }
      } else {
        this.pdfParagraphMap = null;
      }

      if (this.currentFileType === 'pdf') {
        await this._loadPdf();
      } else {
        await this._loadMarkdown();
      }
    } catch (err) {
      console.error('Viewer: failed to load content', err);
    }
  },

  /**
   * Render the PDF using PDF.js into a scrollable canvas container.
   * All pages are rendered upfront so scrollToPage() can navigate without
   * any network request or iframe reload.  A zoom control bar is added at
   * the top of the container for in-viewer scaling.
   */
  async _loadPdf() {
    const empty   = document.getElementById('docEmpty');
    const content = document.getElementById('docContent');

    empty.style.display = 'none';
    content.hidden      = false;

    // Flex-column container: ctrlBar stays fixed at top, pagesScrollArea handles all scrolling.
    content.style.cssText =
      'position:absolute;inset:0;max-width:none;padding:0;overflow:hidden;background:var(--pdf-bg,#525659);display:flex;flex-direction:column;';

    // Destroy any previously loaded PDF to free memory before re-rendering.
    if (_pdfDoc) {
      try { _pdfDoc.destroy(); } catch (_) { /* ignore */ }
      _pdfDoc = null;
      _pdfTotalPages = 0;
    }
    _pdfZoomFactor = 1.0;  // reset zoom for every new document

    content.innerHTML = '';

    // ── Zoom control bar (always visible — outside the scroll container) ────
    const ctrlBar = document.createElement('div');
    ctrlBar.id = 'pdfCtrlBar';
    ctrlBar.style.cssText =
      'flex-shrink:0;z-index:10;display:flex;align-items:center;' +
      'justify-content:center;gap:8px;padding:5px 12px;' +
      'background:rgba(38,38,38,0.96);backdrop-filter:blur(4px);' +
      'border-bottom:1px solid rgba(255,255,255,0.1);box-sizing:border-box;width:100%;';

    const _btnStyle =
      'padding:2px 10px;font-size:15px;line-height:1.4;cursor:pointer;' +
      'background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);' +
      'color:#ddd;border-radius:4px;transition:background 0.15s;';

    const zoomOutBtn  = document.createElement('button');
    zoomOutBtn.textContent = '−';
    zoomOutBtn.title       = 'Zoom out';
    zoomOutBtn.style.cssText = _btnStyle;

    const zoomLevelEl = document.createElement('span');
    zoomLevelEl.id = 'pdfZoomLevel';
    zoomLevelEl.style.cssText =
      'color:#ccc;font-size:12px;min-width:46px;text-align:center;user-select:none;font-variant-numeric:tabular-nums;';
    zoomLevelEl.textContent = '100%';

    const zoomInBtn = document.createElement('button');
    zoomInBtn.textContent = '+';
    zoomInBtn.title       = 'Zoom in';
    zoomInBtn.style.cssText = _btnStyle;

    const zoomFitBtn = document.createElement('button');
    zoomFitBtn.textContent = 'Fit';
    zoomFitBtn.title       = 'Reset to fit width';
    zoomFitBtn.style.cssText =
      'padding:2px 8px;font-size:12px;cursor:pointer;' +
      'background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);' +
      'color:#ccc;border-radius:4px;transition:background 0.15s;';

    // ── Page navigation controls ──────────────────────────────────────────
    const _sepStyle = 'width:1px;height:18px;background:rgba(255,255,255,0.2);margin:0 4px;flex-shrink:0;';
    const sep1 = document.createElement('div');
    sep1.style.cssText = _sepStyle;

    const prevPageBtn = document.createElement('button');
    prevPageBtn.textContent = '◀';
    prevPageBtn.title       = 'Previous page';
    prevPageBtn.style.cssText = _btnStyle + 'padding:2px 7px;font-size:11px;';

    const pageInputEl = document.createElement('input');
    pageInputEl.type  = 'number';
    pageInputEl.min   = '1';
    pageInputEl.value = '1';
    pageInputEl.title = 'Jump to page';
    pageInputEl.style.cssText =
      'width:44px;padding:1px 4px;font-size:12px;text-align:center;' +
      'background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);' +
      'color:#ddd;border-radius:4px;outline:none;-moz-appearance:textfield;';

    const pageTotalEl = document.createElement('span');
    pageTotalEl.style.cssText = 'color:#aaa;font-size:12px;user-select:none;white-space:nowrap;';
    pageTotalEl.textContent = '/ —';

    const nextPageBtn = document.createElement('button');
    nextPageBtn.textContent = '▶';
    nextPageBtn.title       = 'Next page';
    nextPageBtn.style.cssText = _btnStyle + 'padding:2px 7px;font-size:11px;';

    ctrlBar.append(zoomOutBtn, zoomLevelEl, zoomInBtn, zoomFitBtn, sep1, prevPageBtn, pageInputEl, pageTotalEl, nextPageBtn);
    content.appendChild(ctrlBar);

    // ── Independent scroll area (below the fixed ctrlBar) ────────────────
    // Separating scroll from ctrlBar ensures the toolbar always covers the full width,
    // even when pages are wider than the viewport after zooming.
    const pagesScrollArea = document.createElement('div');
    pagesScrollArea.id = 'pdfPagesScrollArea';
    pagesScrollArea.style.cssText = 'flex:1;overflow-y:auto;overflow-x:auto;min-width:0;';
    content.appendChild(pagesScrollArea);

    // ── Pages container ───────────────────────────────────────────────────
    const pagesWrap = document.createElement('div');
    pagesWrap.id = 'pdfPagesContainer';
    // min-width:max-content lets the wrapper expand when pages are wider than the viewport.
    pagesWrap.style.cssText =
      'padding:16px;display:flex;flex-direction:column;align-items:center;gap:16px;' +
      'box-sizing:border-box;min-width:max-content;';
    pagesScrollArea.appendChild(pagesWrap);

    // Re-render all pages at the current zoom level and restore scroll position.
    // Before re-rendering, CSS zoom is removed to avoid double-scaling. Scroll fraction
    // is preserved because zoom*base_H == base_H*zoom (same effective scrollHeight).
    let _reRenderTimer = null;
    const _doReRender = async () => {
      if (!_pdfDoc) return;
      const scale = _pdfBaseScale * _pdfZoomFactor;
      const frac  = pagesScrollArea.scrollHeight > 0
        ? pagesScrollArea.scrollTop / pagesScrollArea.scrollHeight : 0;
      pagesWrap.style.zoom = ''; // remove CSS zoom before re-render to avoid double-scale
      for (let p = 1; p <= _pdfTotalPages; p++) {
        const wrapper   = document.getElementById(`pdf-page-${p}`);
        if (!wrapper) continue;
        const canvas    = wrapper.querySelector('canvas');
        const textLayer = wrapper.querySelector('.textLayer');
        if (canvas) await _renderPdfPage(_pdfDoc, p, canvas, scale, textLayer);
      }
      // After re-render, scrollHeight ≈ original (canvases now encode the zoom factor),
      // so the same fraction restores the same visual position.
      pagesScrollArea.scrollTop = frac * pagesScrollArea.scrollHeight;
    };

    // Two-phase zoom: CSS zoom gives instant visual preview; debounced re-render
    // produces a crisp canvas at the correct resolution after the user settles.
    const _applyZoom = (factor) => {
      _pdfZoomFactor = Math.max(_PDF_ZOOM_MIN, Math.min(_PDF_ZOOM_MAX, factor));
      zoomLevelEl.textContent = Math.round(_pdfZoomFactor * 100) + '%';
      pagesWrap.style.zoom = _pdfZoomFactor; // instant blurry preview
      if (_reRenderTimer) clearTimeout(_reRenderTimer);
      _reRenderTimer = setTimeout(_doReRender, 400);
    };

    zoomOutBtn.addEventListener('click', () => _applyZoom(_pdfZoomFactor - _PDF_ZOOM_STEP));
    zoomInBtn.addEventListener('click',  () => _applyZoom(_pdfZoomFactor + _PDF_ZOOM_STEP));
    zoomFitBtn.addEventListener('click', () => _applyZoom(1.0));

    // Ctrl+wheel zoom on the scroll area — trackpad pixel mode uses proportional delta,
    // mouse wheel line mode uses fixed step per notch.
    pagesScrollArea.addEventListener('wheel', (e) => {
      if (!e.ctrlKey) return;
      e.preventDefault();
      let delta;
      if (e.deltaMode === 0) {
        delta = -e.deltaY * 0.003; // trackpad/pinch: proportional, damped
      } else {
        delta = e.deltaY < 0 ? _PDF_ZOOM_STEP : -_PDF_ZOOM_STEP; // mouse wheel: fixed step
      }
      _applyZoom(_pdfZoomFactor + delta);
    }, { passive: false });

    // Loading indicator while PDF.js fetches and decodes.
    const loadingEl = document.createElement('div');
    loadingEl.style.cssText = 'color:#ccc;font-size:14px;margin-top:40px;';
    loadingEl.textContent = 'Loading PDF…';
    pagesWrap.appendChild(loadingEl);

    // Initialise PDF.js worker (idempotent after first call).
    const pdfjsLib = window.pdfjsLib;
    if (!pdfjsLib) {
      loadingEl.textContent = 'PDF.js failed to load. Please refresh.';
      console.error('Viewer: pdfjsLib not found on window');
      return;
    }
    pdfjsLib.GlobalWorkerOptions.workerSrc = _PDFJS_WORKER_SRC;

    try {
      _pdfDoc = await pdfjsLib.getDocument('/api/files/raw').promise;
    } catch (err) {
      loadingEl.textContent = 'Failed to load PDF: ' + err.message;
      console.error('Viewer: PDF.js getDocument error', err);
      return;
    }

    _pdfTotalPages = _pdfDoc.numPages;
    pageTotalEl.textContent = '/ ' + _pdfTotalPages;
    pageInputEl.max = String(_pdfTotalPages);
    loadingEl.remove();

    // Compute _pdfBaseScale so the first page fills the available width.
    // This becomes the reference for "100%" zoom.
    const firstPage    = await _pdfDoc.getPage(1);
    const unscaledVp   = firstPage.getViewport({ scale: 1 });
    const innerWidth   = pagesScrollArea.clientWidth - 32;  // subtract page padding
    _pdfBaseScale      = innerWidth > 0
      ? Math.min(innerWidth / unscaledVp.width, 3.0)
      : 1.5;

    const renderScale = _pdfBaseScale * _pdfZoomFactor;

    for (let pageNum = 1; pageNum <= _pdfTotalPages; pageNum++) {
      const pageWrapper = document.createElement('div');
      pageWrapper.id           = `pdf-page-${pageNum}`;
      pageWrapper.dataset.page = pageNum;
      // position:relative is required so the absolute text layer overlays correctly.
      pageWrapper.style.cssText = 'flex-shrink:0;line-height:0;position:relative;';

      const canvas = document.createElement('canvas');
      canvas.style.cssText = 'display:block;box-shadow:0 2px 10px rgba(0,0,0,0.5);';

      // Text layer overlay — transparent HTML elements for text selection/copy.
      const textLayerEl = document.createElement('div');
      textLayerEl.className = 'textLayer';

      pageWrapper.appendChild(canvas);
      pageWrapper.appendChild(textLayerEl);
      pagesWrap.appendChild(pageWrapper);

      await _renderPdfPage(_pdfDoc, pageNum, canvas, renderScale, textLayerEl);
    }

    // ── Page indicator: sync input with scroll position ───────────────────
    // pagesScrollArea is the sole scroll container — no ctrlBar offset needed.
    const _updatePageIndicator = () => {
      const saTop = pagesScrollArea.getBoundingClientRect().top;
      const refY  = saTop + pagesScrollArea.clientHeight * 0.25;
      let   current = 1;
      for (let p = 1; p <= _pdfTotalPages; p++) {
        const el = document.getElementById(`pdf-page-${p}`);
        if (!el) continue;
        if (el.getBoundingClientRect().top <= refY) current = p;
        else break;
      }
      pageInputEl.value = current;
    };
    pagesScrollArea.addEventListener('scroll', _updatePageIndicator, { passive: true });

    // Jump to page on input commit (Enter or blur)
    const _jumpToInputPage = () => {
      const n = parseInt(pageInputEl.value, 10);
      if (n >= 1 && n <= _pdfTotalPages) {
        Viewer.scrollToPosition(n, 0);
      } else {
        _updatePageIndicator(); // restore valid value
      }
    };
    pageInputEl.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); pageInputEl.blur(); } });
    pageInputEl.addEventListener('change', _jumpToInputPage);

    prevPageBtn.addEventListener('click', () => {
      const cur = parseInt(pageInputEl.value, 10) || 1;
      if (cur > 1) Viewer.scrollToPosition(cur - 1, 0);
    });
    nextPageBtn.addEventListener('click', () => {
      const cur = parseInt(pageInputEl.value, 10) || 1;
      if (cur < _pdfTotalPages) Viewer.scrollToPosition(cur + 1, 0);
    });
  },

  /** Load and render the markdown content (original behaviour). */
  async _loadMarkdown() {
    const res  = await fetch('/api/files/content');
    if (!res.ok) return;
    const data = await res.json();

    const empty   = document.getElementById('docEmpty');
    const content = document.getElementById('docContent');

    empty.style.display = 'none';
    content.hidden      = false;
    // Clear any inline styles left over from PDF mode so default CSS applies.
    content.removeAttribute('style');

    const lineCount = data.content.split('\n').length;
    content.innerHTML = renderMarkdownWithMath(data.content);
    applyKatex(content);
    _injectLineAnchors(content, lineCount);

    document.getElementById('docFilename').textContent = data.filename;
  },

  /**
   * Scroll the document panel to the closest anchor to the given 1-based line number.
   * For PDF documents, uses the paragraph map (sub-page accuracy) when available,
   * otherwise falls back to the sparse page map.
   */
  scrollToLine(lineNumber) {
    if (this.currentFileType === 'pdf') {
      const target = _lineToTarget(lineNumber, this.pdfParagraphMap, this.pdfPageMap);
      this.scrollToPosition(target.page, target.yFrac);
      return;
    }
    const anchors = Array.from(
      document.querySelectorAll('#docContent .doc-line-anchor[id^="doc-line-"]')
    );
    if (!anchors.length) return;

    let best     = anchors[0];
    let bestDist = Infinity;
    for (const a of anchors) {
      const n = parseInt(a.id.slice('doc-line-'.length), 10);
      const d = Math.abs(n - lineNumber);
      if (d < bestDist) { bestDist = d; best = a; }
    }

    const docBody = document.getElementById('docBody');
    docBody.scrollTo({
      top:      best.offsetTop - docBody.offsetHeight / 3,
      behavior: 'smooth',
    });

    const target = best.parentElement || best;
    target.classList.add('doc-line-highlight');
    setTimeout(() => target.classList.remove('doc-line-highlight'), 1800);
  },

  /**
   * Scroll the PDF viewer to the top of the given 1-based page number.
   * Convenience wrapper around scrollToPosition.
   */
  scrollToPage(pageNumber) {
    this.scrollToPosition(pageNumber, 0);
  },

  /**
   * Scroll the PDF viewer to an exact vertical position within a page.
   * page  — 1-based PDF page number
   * yFrac — 0.0 (page top) … 1.0 (page bottom)
   *
   * Uses getBoundingClientRect so the calculation is correct regardless of whether
   * CSS zoom is currently applied to pagesWrap (preview phase) or removed (post-render).
   */
  scrollToPosition(page, yFrac) {
    const pageEl     = document.getElementById(`pdf-page-${page}`);
    if (!pageEl) return;

    const scrollArea = document.getElementById('pdfPagesScrollArea');
    if (scrollArea) {
      const pageRect = pageEl.getBoundingClientRect();
      const saRect   = scrollArea.getBoundingClientRect();
      const scrollTarget =
        scrollArea.scrollTop +
        (pageRect.top - saRect.top) +
        (yFrac || 0) * pageRect.height - 8;
      scrollArea.scrollTo({ top: Math.max(0, scrollTarget), behavior: 'smooth' });
    }

    // Brief highlight so the user knows which paragraph was navigated to.
    pageEl.style.outline = '3px solid var(--accent, #4a9eff)';
    setTimeout(() => { pageEl.style.outline = ''; }, 1500);
  },
};

/**
 * Render a single PDF page (1-based) onto the provided canvas element at the
 * given logical scale.  Multiplies by devicePixelRatio so the output is crisp
 * on HiDPI / Retina displays; sets CSS width/height to the logical size so the
 * canvas displays at the correct zoom level on screen.
 *
 * If textLayerEl is provided, also renders an invisible HTML text layer on top
 * of the canvas so the user can select and copy text from the PDF.
 */
async function _renderPdfPage(pdfDoc, pageNum, canvas, scale, textLayerEl = null) {
  try {
    const page         = await pdfDoc.getPage(pageNum);
    const dpr          = window.devicePixelRatio || 1;
    // Physical render resolution = logical scale × device pixel ratio.
    const physViewport = page.getViewport({ scale: scale * dpr });
    // Logical viewport for CSS sizing and text layer coordinate alignment.
    const logViewport  = page.getViewport({ scale });

    // Canvas backing store size (physical pixels).
    canvas.width  = Math.round(physViewport.width);
    canvas.height = Math.round(physViewport.height);
    // CSS display size (logical / CSS pixels) — browser scales to physical.
    canvas.style.width  = Math.round(logViewport.width)  + 'px';
    canvas.style.height = Math.round(logViewport.height) + 'px';

    await page.render({
      canvasContext: canvas.getContext('2d'),
      viewport:      physViewport,
    }).promise;

    // Render the text layer so users can select and copy text from the PDF.
    if (textLayerEl) {
      try {
        const pdfjsLib    = window.pdfjsLib;
        const textContent = await page.getTextContent();

        // Size the overlay to exactly match the logical canvas display area.
        textLayerEl.style.width  = Math.round(logViewport.width)  + 'px';
        textLayerEl.style.height = Math.round(logViewport.height) + 'px';
        textLayerEl.innerHTML    = '';  // clear previous render before re-drawing

        if (typeof pdfjsLib.renderTextLayer === 'function') {
          const task = pdfjsLib.renderTextLayer({
            textContentSource: textContent,
            container:         textLayerEl,
            viewport:          logViewport,
            textDivs:          [],
          });
          // Normalise: PDF.js 3.x returns {promise}, 4.x returns a thenable directly.
          await (task.promise ?? task);
        }
      } catch (tlErr) {
        console.warn(`Viewer: text layer failed for page ${pageNum}`, tlErr);
      }
    }
  } catch (err) {
    console.error(`Viewer: failed to render PDF page ${pageNum}`, err);
  }
}

/**
 * Re-render all already-created page canvases (and their text layers) at the
 * current zoom level.  With CSS zoom this is only needed for quality refresh
 * after the user finishes zooming, not for the visual zoom step itself.
 */
async function _reRenderPdfPages() {
  if (!_pdfDoc) return;
  const container = document.getElementById('pdfPagesContainer');
  if (!container) return;
  const scale    = _pdfBaseScale * _pdfZoomFactor;
  const wrappers = container.querySelectorAll('[data-page]');
  for (const wrapper of wrappers) {
    const pageNum     = parseInt(wrapper.dataset.page, 10);
    const canvas      = wrapper.querySelector('canvas');
    const textLayerEl = wrapper.querySelector('.textLayer');
    if (canvas && pageNum) {
      await _renderPdfPage(_pdfDoc, pageNum, canvas, scale, textLayerEl);
    }
  }
}

/**
 * Convert a 1-based markdown line number to a PDF page number using the
 * sparse page map generated by MinerU (keys are line numbers, values are pages).
 * Falls back to page 1 if the map is absent.
 */
function _lineToPage(lineNumber, pageMap) {
  if (!pageMap) return 1;
  const keys = Object.keys(pageMap).map(Number).sort((a, b) => a - b);
  if (!keys.length) return 1;
  let page = pageMap[keys[0]];
  for (const k of keys) {
    if (k <= lineNumber) page = pageMap[k];
    else break;
  }
  return page;
}

/**
 * Convert a 1-based markdown line number to {page, yFrac} for precise PDF scroll
 * targeting.  Prefers the detailed paragraphMap (from MinerU bbox data) for
 * sub-page accuracy; falls back to the sparse pageMap for page-level navigation.
 */
function _lineToTarget(lineNumber, paragraphMap, pageMap) {
  if (paragraphMap && Object.keys(paragraphMap).length > 0) {
    const keys = Object.keys(paragraphMap).map(Number).sort((a, b) => a - b);
    let best   = paragraphMap[keys[0]];
    for (const k of keys) {
      if (k <= lineNumber) best = paragraphMap[k];
      else break;
    }
    if (best) return { page: best.page, yFrac: best.y_frac ?? 0 };
  }
  return { page: _lineToPage(lineNumber, pageMap), yFrac: 0 };
}

/**
 * After rendering, distribute invisible line anchors across the top-level
 * block elements proportional to the original text's line count.
 */
function _injectLineAnchors(container, lineCount) {
  const blocks = Array.from(container.querySelectorAll(':scope > *'));
  if (!blocks.length || !lineCount) return;

  blocks.forEach((block, i) => {
    const lineNum = Math.max(1, Math.round(((i + 0.5) / blocks.length) * lineCount));
    const anchor  = document.createElement('a');
    anchor.id        = `doc-line-${lineNum}`;
    anchor.className = 'doc-line-anchor';
    block.insertBefore(anchor, block.firstChild);
  });
}

/**
 * Parse markdown while protecting math blocks from being mangled by marked.
 */
function renderMarkdownWithMath(text) {
  if (typeof marked === 'undefined') return _escapeHtml(text);

  const displayBlocks = [];
  const inlineBlocks  = [];

  let processed = text.replace(/\$\$([\s\S]+?)\$\$/g, (_, inner) => {
    const idx = displayBlocks.length;
    displayBlocks.push(inner);
    return `\n\n<div class="__katex_d__" data-i="${idx}"></div>\n\n`;
  });

  processed = processed.replace(/(?<!\$)\$(?!\$)([^\n$]+?)\$(?!\$)/g, (_, inner) => {
    const idx = inlineBlocks.length;
    inlineBlocks.push(inner);
    return `<katex-i data-i="${idx}"></katex-i>`;
  });

  let html = marked.parse(processed, { breaks: true, gfm: true });

  if (displayBlocks.length) {
    html = html.replace(/<div class="__katex_d__" data-i="(\d+)">\s*<\/div>/g, (_, i) => {
      const math = _encodeMathForHtml(displayBlocks[parseInt(i, 10)]);
      return `<div class="katex-display-wrap">$$${math}$$</div>`;
    });
  }

  if (inlineBlocks.length) {
    html = html.replace(/<katex-i data-i="(\d+)"><\/katex-i>/g, (_, i) => {
      const math = _encodeMathForHtml(inlineBlocks[parseInt(i, 10)]);
      return `<span class="katex-inline-wrap">$${math}$</span>`;
    });
  }

  return html;
}

function applyKatex(element) {
  if (typeof renderMathInElement === 'undefined') return;
  renderMathInElement(element, {
    delimiters: [
      { left: '$$',  right: '$$',  display: true  },
      { left: '$',   right: '$',   display: false },
      { left: '\\[', right: '\\]', display: true  },
      { left: '\\(', right: '\\)', display: false },
    ],
    throwOnError: false,
  });
}

// Keep legacy name so other code isn't broken
const renderMath = applyKatex;

function _encodeMathForHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function _escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
