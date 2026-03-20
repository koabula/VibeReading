/* ── Document Viewer ──────────────────────────────────────────────────────── */
const Viewer = {
  async loadContent() {
    try {
      const res  = await fetch('/api/files/content');
      if (!res.ok) return;
      const data = await res.json();

      const empty   = document.getElementById('docEmpty');
      const content = document.getElementById('docContent');

      empty.style.display = 'none';
      content.hidden      = false;

      // Render markdown without injecting raw <a> tags into the source text —
      // that approach broke heading / code-block parsing in marked.js.
      // Line anchors are injected AFTER rendering via _injectLineAnchors().
      const lineCount = data.content.split('\n').length;
      content.innerHTML = renderMarkdownWithMath(data.content);
      applyKatex(content);
      _injectLineAnchors(content, lineCount);

      document.getElementById('docFilename').textContent = data.filename;
    } catch (err) {
      console.error('Viewer: failed to load content', err);
    }
  },

  /**
   * Scroll the document panel to the closest anchor to the given 1-based line number.
   * Anchors are injected proportionally across rendered block elements by
   * _injectLineAnchors(), so we find the nearest one.
   */
  scrollToLine(lineNumber) {
    const anchors = Array.from(
      document.querySelectorAll('#docContent .doc-line-anchor[id^="doc-line-"]')
    );
    if (!anchors.length) return;

    // Find the anchor whose estimated line number is closest to the requested one
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

    // Brief highlight flash on the parent block
    const target = best.parentElement || best;
    target.classList.add('doc-line-highlight');
    setTimeout(() => target.classList.remove('doc-line-highlight'), 1800);
  },
};

/**
 * After rendering, distribute invisible line anchors across the top-level
 * block elements proportional to the original text's line count.
 *
 * This avoids injecting raw HTML into the markdown source (which breaks
 * marked.js heading/code-block parsing).  Accuracy is proportional, not
 * exact, but that is sufficient for the scroll-to-line use case.
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
 *
 * marked.js wraps multiline $$...$$ blocks in separate <p> tags, splitting the
 * KaTeX delimiters across DOM elements and preventing auto-render from finding
 * them. We extract math blocks first, parse the rest, then restore them.
 *
 * NOTE: line-anchor injection was intentionally removed from this function.
 * Injecting <a> tags before heading lines (e.g. "<a>## Title") causes marked
 * to treat them as paragraphs, not headings.  Use _injectLineAnchors() instead.
 */
function renderMarkdownWithMath(text) {
  if (typeof marked === 'undefined') return _escapeHtml(text);

  const displayBlocks = [];
  const inlineBlocks  = [];

  // 1. Extract display math $$...$$ (multiline-safe, greedy-shy).
  //    Use a real <div> as placeholder — marked.js treats <div> as a block-level
  //    HTML element and will NOT wrap it in <p>, whereas custom elements like
  //    <katex-d> get wrapped in <p>, producing invalid <p><div>...</div></p>.
  let processed = text.replace(/\$\$([\s\S]+?)\$\$/g, (_, inner) => {
    const idx = displayBlocks.length;
    displayBlocks.push(inner);
    return `\n\n<div class="__katex_d__" data-i="${idx}"></div>\n\n`;
  });

  // 2. Extract inline math $...$ (single-line, not preceded/followed by $)
  processed = processed.replace(/(?<!\$)\$(?!\$)([^\n$]+?)\$(?!\$)/g, (_, inner) => {
    const idx = inlineBlocks.length;
    inlineBlocks.push(inner);
    return `<katex-i data-i="${idx}"></katex-i>`;
  });

  // 3. Parse remaining markdown
  let html = marked.parse(processed, { breaks: true, gfm: true });

  // 4. Restore display math — HTML-encode so the browser stores raw LaTeX in the text node
  if (displayBlocks.length) {
    html = html.replace(/<div class="__katex_d__" data-i="(\d+)">\s*<\/div>/g, (_, i) => {
      const math = _encodeMathForHtml(displayBlocks[parseInt(i, 10)]);
      return `<div class="katex-display-wrap">$$${math}$$</div>`;
    });
  }

  // 5. Restore inline math
  if (inlineBlocks.length) {
    html = html.replace(/<katex-i data-i="(\d+)"><\/katex-i>/g, (_, i) => {
      const math = _encodeMathForHtml(inlineBlocks[parseInt(i, 10)]);
      return `<span class="katex-inline-wrap">$${math}$</span>`;
    });
  }

  return html;
}

/**
 * Run KaTeX auto-render on a container after its innerHTML has been set.
 * renderMathInElement scans text nodes for delimiter patterns.
 */
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

/** HTML-encode <, >, & so raw LaTeX survives being placed in innerHTML. */
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
