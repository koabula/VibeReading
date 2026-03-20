/* ── Chat Interface ───────────────────────────────────────────────────────── */
(function initChat() {
  const messagesEl  = document.getElementById('chatMessages');
  const inputEl     = document.getElementById('chatInput');
  const sendBtn     = document.getElementById('sendBtn');
  const newChatBtn  = document.getElementById('newChatBtn');
  const historyBtn  = document.getElementById('historyBtn');
  const historyDropdown = document.getElementById('historyDropdown');
  const historyListEl   = document.getElementById('historyList');

  /* ── Scroll-to-bottom floating button (rendered in HTML) ────────────────── */
  // Use optional chaining throughout — if the browser serves a cached HTML
  // without this element, we must not crash; the send button must still work.
  const scrollBtn = document.getElementById('scrollToBottomBtn');

  scrollBtn?.addEventListener('click', () => {
    userScrolledAway = false;
    scrollBtn.classList.add('hidden');
    messagesEl.scrollTo({ top: messagesEl.scrollHeight, behavior: 'smooth' });
  });

  /* ── Auto-resize textarea ───────────────────────────────────────────────── */
  inputEl.addEventListener('input', () => {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 160) + 'px';
  });

  inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!sendBtn.disabled) sendMessage();
    }
  });

  sendBtn.addEventListener('click', () => sendMessage());

  /* ── Auto-scroll helpers ────────────────────────────────────────────────── */
  let userScrolledAway = false;

  function isNearBottom() {
    return messagesEl.scrollHeight - messagesEl.scrollTop - messagesEl.clientHeight < 80;
  }

  messagesEl.addEventListener('scroll', () => {
    userScrolledAway = !isNearBottom();
    scrollBtn?.classList.toggle('hidden', !userScrolledAway);
  });

  function scrollToBottom() {
    if (!userScrolledAway) {
      messagesEl.scrollTo({ top: messagesEl.scrollHeight, behavior: 'smooth' });
    }
  }

  function scrollToBottomForce() {
    userScrolledAway = false;
    scrollBtn?.classList.add('hidden');
    messagesEl.scrollTo({ top: messagesEl.scrollHeight, behavior: 'smooth' });
  }

  /* ── Conversation history ───────────────────────────────────────────────── */
  // history[] is sent to the backend with each request so the agent has
  // multi-turn context. It is also saved to localStorage per project.
  let history         = [];   // [{role, content}, …]
  let currentFilename = null; // used as localStorage key

  const MAX_HISTORY_TURNS = 10; // keep last N user/assistant pairs (20 msgs)

  function historyKey() { return 'vr_chat_'  + (currentFilename || '__default__'); }
  function savedKey()   { return 'vr_saved_' + (currentFilename || '__default__'); }

  function persistHistory() {
    try { localStorage.setItem(historyKey(), JSON.stringify(history)); } catch { /* quota */ }
  }

  /** Clear visual messages and restore history from localStorage. */
  function loadAndRestoreHistory() {
    history = [];
    try {
      const raw = localStorage.getItem(historyKey());
      if (raw) history = JSON.parse(raw);
    } catch { history = []; }

    // Remove all message nodes except the intro
    while (messagesEl.children.length > 1) messagesEl.removeChild(messagesEl.lastChild);

    history.forEach(msg => {
      if (msg.role === 'user') _appendUserMsg(msg.content);
      else                     _appendAssistantMsg(msg.content);
    });

    scrollToBottomForce();
  }

  /** Push current history to the "saved" list. */
  function saveSnapshot() {
    if (!history.length) return;
    try {
      const saved = JSON.parse(localStorage.getItem(savedKey()) || '[]');
      const preview = (history.find(m => m.role === 'user')?.content || '').slice(0, 80);
      saved.unshift({
        id:      Date.now().toString(),
        savedAt: new Date().toISOString(),
        preview,
        messages: [...history],
      });
      localStorage.setItem(savedKey(), JSON.stringify(saved.slice(0, 15)));
    } catch { /* quota */ }
  }

  /** Load a saved conversation (replaces current). */
  function loadConversation(conv) {
    history = [...conv.messages];
    persistHistory();
    while (messagesEl.children.length > 1) messagesEl.removeChild(messagesEl.lastChild);
    history.forEach(msg => {
      if (msg.role === 'user') _appendUserMsg(msg.content);
      else                     _appendAssistantMsg(msg.content);
    });
    scrollToBottomForce();
  }

  /** Start fresh — saves current first. */
  function newChat() {
    saveSnapshot();
    history = [];
    persistHistory();
    while (messagesEl.children.length > 1) messagesEl.removeChild(messagesEl.lastChild);
    scrollToBottomForce();
  }

  /** Append a user message silently (without sending). */
  function _appendUserMsg(text) {
    const el = document.createElement('div');
    el.className = 'message user-message';
    el.innerHTML = `<div class="message-avatar">U</div>
      <div class="message-bubble">${escapeHtml(text)}</div>`;
    messagesEl.appendChild(el);
  }

  /** Append an assistant message silently (rendered markdown, no streaming). */
  function _appendAssistantMsg(text) {
    const el = document.createElement('div');
    el.className = 'message assistant-message';
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.innerHTML = renderMarkdownWithMath(text);
    el.innerHTML = '<div class="message-avatar">V</div>';
    el.appendChild(bubble);
    messagesEl.appendChild(el);
    applyKatex(bubble);
    activateDocLinks(bubble);
  }

  /* ── History dropdown ───────────────────────────────────────────────────── */
  function renderHistoryDropdown() {
    // Update project label in dropdown header
    const hdr = historyDropdown.querySelector('.history-hdr');
    if (hdr) {
      const label = currentFilename
        ? escapeHtml(currentFilename)
        : 'No project loaded';
      hdr.innerHTML = `History <span class="history-hdr-project">${label}</span>`;
    }

    try {
      const saved = JSON.parse(localStorage.getItem(savedKey()) || '[]');
      if (!saved.length) {
        historyListEl.innerHTML = '<div class="history-empty">No saved conversations for this project</div>';
        return;
      }
      historyListEl.innerHTML = saved.map(conv => {
        const date  = new Date(conv.savedAt).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: '2-digit' });
        const turns = conv.messages.filter(m => m.role === 'user').length;
        return `<div class="history-item" data-id="${conv.id}">
          <div class="history-item-preview">${escapeHtml(conv.preview || 'Conversation')}</div>
          <div class="history-item-meta">
            <span>${date} · ${turns} Q${turns !== 1 ? 's' : ''}</span>
            <button class="history-item-del" data-id="${conv.id}" title="Delete this conversation">×</button>
          </div>
        </div>`;
      }).join('');

      historyListEl.querySelectorAll('.history-item').forEach(el => {
        el.addEventListener('click', (e) => {
          if (e.target.closest('.history-item-del')) return;
          const id   = el.dataset.id;
          const conv = saved.find(c => c.id === id);
          if (conv) { loadConversation(conv); closeHistory(); }
        });
      });

      historyListEl.querySelectorAll('.history-item-del').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          deleteConversation(btn.dataset.id);
        });
      });
    } catch { historyListEl.innerHTML = '<div class="history-empty">Error loading history</div>'; }
  }

  function deleteConversation(id) {
    try {
      const saved = JSON.parse(localStorage.getItem(savedKey()) || '[]');
      const updated = saved.filter(c => c.id !== id);
      localStorage.setItem(savedKey(), JSON.stringify(updated));
      renderHistoryDropdown();
    } catch { /* ignore */ }
  }

  function openHistory()  { historyDropdown.classList.remove('hidden'); renderHistoryDropdown(); }
  function closeHistory() { historyDropdown.classList.add('hidden'); }

  historyBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    historyDropdown.classList.contains('hidden') ? openHistory() : closeHistory();
  });
  document.addEventListener('click', () => closeHistory());
  historyDropdown.addEventListener('click', (e) => e.stopPropagation());

  newChatBtn.addEventListener('click', newChat);

  /* ── Called by app.js when a project is activated ──────────────────────── */
  window.Chat = {
    onProjectActivated(filename) {
      if (currentFilename && history.length) {
        localStorage.setItem(historyKey(), JSON.stringify(history));
      }
      currentFilename = filename;
      loadAndRestoreHistory();
    },
  };

  /* ── DOM helpers ────────────────────────────────────────────────────────── */
  function appendUserMessage(text) {
    _appendUserMsg(text);
    scrollToBottomForce();
  }

  function createAssistantBubble() {
    const el = document.createElement('div');
    el.className = 'message assistant-message';
    el.innerHTML = `
      <div class="message-avatar">V</div>
      <div class="message-bubble"><span class="typing-cursor"></span></div>
    `;
    messagesEl.appendChild(el);
    scrollToBottomForce();
    return el.querySelector('.message-bubble');
  }

  /** Single tool indicator — replaced each time a new tool starts. */
  function createToolIndicator(toolName) {
    const el = document.createElement('div');
    el.className = 'message assistant-message tool-row';
    el.innerHTML = `
      <div class="message-avatar">V</div>
      <div class="tool-indicator">
        <span class="tool-dot"></span>
        <span>${formatToolName(toolName)}</span>
      </div>
    `;
    messagesEl.appendChild(el);
    scrollToBottom();
    return el;
  }

  function formatToolName(name) {
    const labels = {
      rag_local_query:        'Searching local context…',
      rag_global_query:       'Searching global context…',
      explore_node_neighbors: 'Exploring graph neighbors…',
      get_node_details:       'Inspecting node…',
      list_key_entities:      'Listing key entities…',
      get_document_info:      'Reading document info…',
      read_document:          'Reading document…',
      search_document:        'Searching document…',
      create_doc_link:        'Creating reference link…',
      scroll_to_line:         'Navigating to line…',
    };
    return labels[name] || `${name}…`;
  }

  function updateBubble(bubble, thoughtSegments, text, streaming) {
    let html = '';

    if (thoughtSegments.length > 0) {
      const inner = thoughtSegments
        .map(t => `<div class="thought-seg">${renderMarkdownWithMath(t)}</div>`)
        .join('');
      const steps = thoughtSegments.length;
      html += `<details class="thinking-block">
        <summary class="thinking-summary">
          <span>Thinking · ${steps} step${steps !== 1 ? 's' : ''}</span>
        </summary>
        <div class="thinking-content">${inner}</div>
      </details>`;
    }

    html += renderMarkdownWithMath(text || '');
    if (streaming) html += '<span class="typing-cursor"></span>';

    bubble.innerHTML = html || (streaming ? '<span class="typing-cursor"></span>' : '<em>no response</em>');
  }

  function activateDocLinks(container) {
    container.querySelectorAll('a[href^="doc://scroll"]').forEach(a => {
      const url  = new URL(a.href.replace('doc://', 'https://doc/'));
      const page = url.searchParams.get('page');
      const line = url.searchParams.get('line');
      a.removeAttribute('href');
      a.className = 'doc-scroll-link';
      a.addEventListener('click', (e) => {
        e.preventDefault();
        if (page !== null) {
          Viewer.scrollToPage(parseInt(page, 10));
        } else {
          Viewer.scrollToLine(parseInt(line || '1', 10));
        }
      });
    });
  }

  function escapeHtml(str) {
    return str
      .replace(/&/g,  '&amp;')
      .replace(/</g,  '&lt;')
      .replace(/>/g,  '&gt;')
      .replace(/"/g,  '&quot;')
      .replace(/'/g,  '&#039;');
  }

  /* ── Recursion-limit banner ─────────────────────────────────────────────── */
  function createRecursionLimitBanner(onContinue) {
    const el = document.createElement('div');
    el.className = 'message assistant-message';
    el.innerHTML = `
      <div class="message-avatar">V</div>
      <div class="recursion-limit-banner">
        <span>Agent reached the step limit mid-way.</span>
        <button class="btn-continue">Continue</button>
        <button class="btn-continue-stop">Stop</button>
      </div>
    `;
    messagesEl.appendChild(el);
    scrollToBottom();
    el.querySelector('.btn-continue').addEventListener('click', () => {
      el.remove();
      onContinue();
    });
    el.querySelector('.btn-continue-stop').addEventListener('click', () => {
      el.remove();
    });
    return el;
  }

  /* ── Main send / stream ─────────────────────────────────────────────────── */
  async function sendMessage(overrideText) {
    const text = (typeof overrideText === 'string' ? overrideText : null) || inputEl.value.trim();
    if (!text || App.isStreaming) return;

    if (!overrideText || typeof overrideText !== 'string') {
      inputEl.value = '';
      inputEl.style.height = 'auto';
    }
    App.setStreaming(true);
    userScrolledAway = false;
    scrollBtn?.classList.add('hidden');

    appendUserMessage(text);

    const bubble          = createAssistantBubble();
    let   rawText         = '';
    let   thoughtSegments = [];
    let   currentToolEl   = null;

    const cleanup = () => {
      if (currentToolEl) { currentToolEl.remove(); currentToolEl = null; }
      bubble.querySelectorAll('.typing-cursor').forEach(c => c.remove());
      App.setStreaming(false);
    };

    const finaliseBubble = () => {
      updateBubble(bubble, thoughtSegments, rawText, false);
      applyKatex(bubble);
      activateDocLinks(bubble);
      scrollToBottom();
    };

    // Snapshot history BEFORE adding current message (sent as context).
    // Sanitize to ensure only valid {role, content} string pairs are sent —
    // stale or corrupt localStorage data could otherwise trigger a backend 422.
    const historySnapshot = history
      .slice(-(MAX_HISTORY_TURNS * 2))
      .filter(m => typeof m.role === 'string' && typeof m.content === 'string' && m.content.length > 0);

    try {
      const res = await fetch('/api/chat/stream', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ message: text, history: historySnapshot }),
      });

      if (!res.ok) {
        let detail = res.statusText;
        try {
          const errBody = await res.json();
          detail = errBody.detail || JSON.stringify(errBody);
        } catch { /* body is not JSON */ }
        bubble.innerHTML = `<span style="color:var(--error)">Error ${res.status}: ${escapeHtml(String(detail))}</span>`;
        return;
      }

      const reader  = res.body.getReader();
      const decoder = new TextDecoder();
      let   buffer  = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (!line.startsWith('data:')) continue;
          const jsonStr = line.slice(5).trim();
          if (!jsonStr) continue;

          let event;
          try { event = JSON.parse(jsonStr); } catch { continue; }

          switch (event.type) {

            case 'text':
              rawText += event.content;
              updateBubble(bubble, thoughtSegments, rawText, true);
              activateDocLinks(bubble);
              scrollToBottom();
              break;

            case 'tool_call': {
              if (rawText.trim()) {
                thoughtSegments.push(rawText);
                rawText = '';
              }
              if (currentToolEl) currentToolEl.remove();
              currentToolEl = createToolIndicator(event.tool_name);
              updateBubble(bubble, thoughtSegments, rawText, true);
              scrollToBottom();
              break;
            }

            case 'nodes_accessed':
              break;

            case 'scroll_to':
              if (typeof event.page === 'number') Viewer.scrollToPage(event.page);
              else if (typeof event.line === 'number') Viewer.scrollToLine(event.line);
              break;

            case 'recursion_limit':
              cleanup();
              finaliseBubble();
              // Record partial response in history
              if (rawText.trim()) {
                history.push({ role: 'user', content: text });
                history.push({ role: 'assistant', content: rawText });
                persistHistory();
              }
              createRecursionLimitBanner(() => {
                sendMessage('Please continue from where you left off.');
              });
              return;

            case 'error':
              rawText += `\n\n*Error: ${escapeHtml(event.content)}*`;
              updateBubble(bubble, thoughtSegments, rawText, false);
              break;

            case 'done':
              cleanup();
              finaliseBubble();
              // Record completed turn in history
              history.push({ role: 'user',      content: text });
              history.push({ role: 'assistant', content: rawText });
              persistHistory();
              return;
          }
        }
      }
    } catch (err) {
      bubble.innerHTML = `<span style="color:var(--error)">Connection error: ${escapeHtml(String(err))}</span>`;
    } finally {
      cleanup();
    }
  }

})();
