/* ── Theme ────────────────────────────────────────────────────────────────── */
(function initTheme() {
  const saved = localStorage.getItem('vr-theme') || 'dark';
  document.documentElement.dataset.theme = saved;

  document.getElementById('themeToggleBtn').addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    localStorage.setItem('vr-theme', next);
  });
})();

/* ── Global application state ─────────────────────────────────────────────── */
const App = {
  indexStatus: 'idle',
  currentFilename: null,
  currentProjectSlug: null,
  isStreaming: false,

  setStatus(status, label) {
    this.indexStatus = status;
    const dot  = document.getElementById('statusDot');
    const text = document.getElementById('statusText');
    dot.className = `status-dot ${status}`;
    text.textContent = label || status;

    const sendBtn = document.getElementById('sendBtn');
    if (sendBtn) sendBtn.disabled = (status !== 'ready') || this.isStreaming;
  },

  setStreaming(val) {
    this.isStreaming = val;
    const sendBtn = document.getElementById('sendBtn');
    if (sendBtn) sendBtn.disabled = val || (this.indexStatus !== 'ready');
  },
};

/* ── Resizable divider ────────────────────────────────────────────────────── */
(function initDivider() {
  const workspace = document.getElementById('workspace');
  const panelDoc  = document.getElementById('panelDoc');
  const divider   = document.getElementById('divider');

  let dragging = false, startX = 0, startW = 0;

  divider.addEventListener('mousedown', (e) => {
    dragging = true;
    startX   = e.clientX;
    startW   = panelDoc.getBoundingClientRect().width;
    divider.classList.add('dragging');
    document.body.style.cursor    = 'col-resize';
    document.body.style.userSelect = 'none';
  });

  document.addEventListener('mousemove', (e) => {
    if (!dragging) return;
    const totalW = workspace.getBoundingClientRect().width;
    const newW   = Math.max(200, Math.min(totalW - 260, startW + (e.clientX - startX)));
    panelDoc.style.flex = `0 0 ${newW}px`;
  });

  document.addEventListener('mouseup', () => {
    if (!dragging) return;
    dragging = false;
    divider.classList.remove('dragging');
    document.body.style.cursor    = '';
    document.body.style.userSelect = '';
  });
})();

/* ── File upload helpers ──────────────────────────────────────────────────── */
async function uploadFileObject(file) {
  if (!file) return;

  const suffix = file.name.split('.').pop().toLowerCase();
  if (!['txt', 'md', 'pdf'].includes(suffix) && file.name.includes('.')) {
    App.setStatus('error', 'Only .txt, .md, and .pdf files are supported');
    return;
  }

  App.setStatus('indexing', 'Uploading…');

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/api/files/upload', { method: 'POST', body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      App.setStatus('error', err.detail || 'Upload failed');
      return;
    }
    const data = await res.json();
    App.currentFilename = data.filename;
    document.getElementById('docFilename').textContent = data.filename;
    App.setStatus('indexing', suffix === 'pdf' ? 'Converting PDF via MinerU…' : 'Indexing…');
    pollStatus();
    Viewer.loadContent();
    if (typeof Chat !== 'undefined') Chat.onProjectActivated(data.filename);
  } catch {
    App.setStatus('error', 'Network error');
  }
}

/* ── Button-based upload ──────────────────────────────────────────────────── */
(function initUpload() {
  const fileInput   = document.getElementById('fileInput');
  const uploadLabel = document.getElementById('uploadLabel');

  fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    fileInput.value = '';
    uploadLabel.classList.add('disabled');
    await uploadFileObject(file);
    uploadLabel.classList.remove('disabled');
  });
})();

/* ── Drag-and-drop upload ─────────────────────────────────────────────────── */
(function initDragDrop() {
  const dropZone = document.getElementById('dropZone');

  // A full-viewport transparent div that sits above everything (including any
  // PDF iframe) while a drag is in progress.  By keeping it in the parent
  // document's stacking context with z-index:9999 it physically covers the
  // iframe, so all dragover/drop events land here instead of on the browser's
  // native PDF viewer (which would otherwise trigger a file download).
  const dragScreen = document.createElement('div');
  dragScreen.style.cssText = 'position:fixed;inset:0;z-index:9999;display:none;';
  document.body.appendChild(dragScreen);

  function _showOverlay() {
    dropZone.classList.add('active');
    dragScreen.style.display = 'block';
  }

  function _hideOverlay() {
    dropZone.classList.remove('active');
    dragScreen.style.display = 'none';
  }

  // Prevent browser default file-open on any stray drop outside our handler
  document.addEventListener('dragover', (e) => e.preventDefault());
  document.addEventListener('drop',     (e) => e.preventDefault());

  // Use window capture-phase so this fires before any element (including the
  // iframe's internal document) can process the dragenter event.
  window.addEventListener('dragenter', (e) => {
    if (!e.dataTransfer?.types?.includes('Files')) return;
    _showOverlay();
  }, true);

  // dragScreen now catches all subsequent drag events ─────────────────────────

  dragScreen.addEventListener('dragover', (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  });

  // Only hide when the drag truly leaves the browser window
  dragScreen.addEventListener('dragleave', (e) => {
    if (e.relatedTarget !== null) return;
    _hideOverlay();
  });

  dragScreen.addEventListener('drop', async (e) => {
    e.preventDefault();
    _hideOverlay();
    const file = e.dataTransfer.files[0];
    await uploadFileObject(file);
  });
})();

/* ── Status polling ───────────────────────────────────────────────────────── */
function pollStatus() {
  const interval = setInterval(async () => {
    try {
      const res  = await fetch('/api/files/status');
      const data = await res.json();
      switch (data.status) {
        case 'indexing':
          App.setStatus('indexing', data.message || 'Indexing…');
          break;
        case 'ready':
          App.setStatus('ready', data.filename ? `Ready · ${data.filename}` : 'Ready');
          clearInterval(interval);
          // Reload viewer once indexing is done so PDF viewer / markdown
          // is shown with the final file_type from the backend.
          Viewer.loadContent();
          break;
        case 'error':
          App.setStatus('error', data.message || 'Error');
          clearInterval(interval);
          break;
        default:
          clearInterval(interval);
      }
    } catch {
      clearInterval(interval);
    }
  }, 1500);
}

/* ── Projects panel ───────────────────────────────────────────────────────── */
(function initProjectsPanel() {
  const btn      = document.getElementById('projectsBtn');
  const dropdown = document.getElementById('projectsDropdown');
  const list     = document.getElementById('projectsList');

  let projects = [];

  /* ── Render project list ─────────────────────────────────────────────────── */
  function renderProjects() {
    if (!projects.length) {
      list.innerHTML = '<div class="projects-empty">No indexed projects yet</div>';
      return;
    }
    list.innerHTML = projects.map(p => {
      const ext      = p.filename.split('.').pop().toUpperCase().slice(0, 3);
      const date     = new Date(p.indexed_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
      const active   = p.is_active ? ' active' : '';
      return `
        <div class="project-item${active}" data-slug="${p.slug}">
          <div class="project-item-icon">${ext}</div>
          <div class="project-item-info">
            <div class="project-item-name">${p.filename}</div>
            <div class="project-item-date">${date}</div>
          </div>
          <button class="project-item-delete" data-slug="${p.slug}" title="Delete project">
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24"
              fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>`;
    }).join('');

    // Activate on click
    list.querySelectorAll('.project-item').forEach(el => {
      el.addEventListener('click', (e) => {
        if (e.target.closest('.project-item-delete')) return;
        activateProject(el.dataset.slug);
      });
    });

    // Delete on ×
    list.querySelectorAll('.project-item-delete').forEach(el => {
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        deleteProject(el.dataset.slug);
      });
    });
  }

  /* ── Fetch projects from API ─────────────────────────────────────────────── */
  async function fetchProjects() {
    try {
      const res  = await fetch('/api/projects');
      const data = await res.json();
      projects   = data.projects || [];
      renderProjects();
    } catch { /* ignore */ }
  }

  /* ── Activate a project ──────────────────────────────────────────────────── */
  async function activateProject(slug) {
    closeDropdown();
    App.setStatus('indexing', 'Loading project…');
    try {
      const res = await fetch(`/api/projects/${encodeURIComponent(slug)}/activate`, { method: 'POST' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        App.setStatus('error', err.detail || 'Failed to load project');
        return;
      }
      const data = await res.json();
      App.currentFilename    = data.filename;
      App.currentProjectSlug = slug;
      document.getElementById('docFilename').textContent = data.filename;
      App.setStatus('ready', `Ready · ${data.filename}`);
      // Mark active in local state
      projects.forEach(p => { p.is_active = p.slug === slug; });
      renderProjects();
      Viewer.loadContent();
      if (typeof Chat !== 'undefined') Chat.onProjectActivated(data.filename);
    } catch {
      App.setStatus('error', 'Network error');
    }
  }

  /* ── Delete a project ────────────────────────────────────────────────────── */
  async function deleteProject(slug) {
    if (!confirm(`Delete project "${slug}"? This will remove its index data.`)) return;
    try {
      const res = await fetch(`/api/projects/${encodeURIComponent(slug)}`, { method: 'DELETE' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(err.detail || 'Delete failed');
        return;
      }
      projects = projects.filter(p => p.slug !== slug);
      renderProjects();
    } catch {
      alert('Network error during delete');
    }
  }

  /* ── Toggle dropdown ─────────────────────────────────────────────────────── */
  function openDropdown() {
    dropdown.classList.remove('hidden');
    btn.classList.add('open');
    fetchProjects();
  }

  function closeDropdown() {
    dropdown.classList.add('hidden');
    btn.classList.remove('open');
  }

  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    dropdown.classList.contains('hidden') ? openDropdown() : closeDropdown();
  });

  document.addEventListener('click', () => closeDropdown());
  dropdown.addEventListener('click', (e) => e.stopPropagation());

  /* ── On page load: check server status & auto-restore if already ready ───── */
  (async function checkInitialStatus() {
    try {
      const res  = await fetch('/api/files/status');
      const data = await res.json();
      if (data.status === 'ready' && data.filename) {
        App.currentFilename = data.filename;
        document.getElementById('docFilename').textContent = data.filename;
        App.setStatus('ready', `Ready · ${data.filename}`);
        Viewer.loadContent();
        if (typeof Chat !== 'undefined') Chat.onProjectActivated(data.filename);
      }
    } catch { /* ignore */ }
  })();
})();

