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
  // multi-turn context. It is also persisted on the backend per project.
  let history         = [];   // [{role, content}, …]
  let currentFilename = null; // used for the history panel label
  let currentProjectSlug = null;
  let savedConversations = [];

  const MAX_HISTORY_TURNS = 10; // keep last N user/assistant pairs (20 msgs)

  function clearRenderedMessages() {
    while (messagesEl.children.length > 1) messagesEl.removeChild(messagesEl.lastChild);
  }

  function sanitizeMessages(messages) {
    return Array.isArray(messages)
      ? messages.filter(msg =>
          msg &&
          typeof msg.role === 'string' &&
          typeof msg.content === 'string' &&
          msg.content.length > 0
        )
      : [];
  }

  function sanitizeSavedConversations(conversations) {
    return Array.isArray(conversations)
      ? conversations
          .filter(conv => conv && typeof conv.id === 'string' && typeof conv.savedAt === 'string')
          .map(conv => ({
            id: conv.id,
            savedAt: conv.savedAt,
            preview: typeof conv.preview === 'string' ? conv.preview : '',
            messages: sanitizeMessages(conv.messages),
          }))
      : [];
  }

  async function persistHistory() {
    if (!currentProjectSlug) return;
    try {
      await fetch(`/api/projects/${encodeURIComponent(currentProjectSlug)}/chat-history`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_messages: history,
          saved_conversations: savedConversations,
        }),
      });
    } catch {
      /* ignore transient persistence failures */
    }
  }

  async function loadAndRestoreHistory() {
    history = [];
    savedConversations = [];

    if (!currentProjectSlug) {
      clearRenderedMessages();
      scrollToBottomForce();
      return;
    }

    try {
      const res = await fetch(`/api/projects/${encodeURIComponent(currentProjectSlug)}/chat-history`);
      if (res.ok) {
        const payload = await res.json();
        history = sanitizeMessages(payload.current_messages);
        savedConversations = sanitizeSavedConversations(payload.saved_conversations);
      }
    } catch {
      history = [];
      savedConversations = [];
    }

    // Remove all message nodes except the intro
    clearRenderedMessages();

    history.forEach(msg => {
      if (msg.role === 'user') _appendUserMsg(msg.content);
      else                     _appendAssistantMsg(msg.content);
    });

    scrollToBottomForce();
  }

  /** Push current history to the "saved" list. */
  async function saveSnapshot() {
    if (!history.length) return;
    const preview = (history.find(m => m.role === 'user')?.content || '').slice(0, 80);
    savedConversations.unshift({
      id: Date.now().toString(),
      savedAt: new Date().toISOString(),
      preview,
      messages: [...history],
    });
    savedConversations = savedConversations.slice(0, 15);
    await persistHistory();
  }

  /** Load a saved conversation (replaces current). */
  async function loadConversation(conv) {
    history = [...conv.messages];
    await persistHistory();
    clearRenderedMessages();
    history.forEach(msg => {
      if (msg.role === 'user') _appendUserMsg(msg.content);
      else                     _appendAssistantMsg(msg.content);
    });
    scrollToBottomForce();
  }

  /** Start fresh — saves current first. */
  async function newChat() {
    await saveSnapshot();
    history = [];
    await persistHistory();
    clearRenderedMessages();
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
    const body = document.createElement('div');
    body.className = 'assistant-message-body';
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.innerHTML = renderMarkdownWithMath(text);
    el.innerHTML = '<div class="message-avatar">V</div>';
    body.appendChild(bubble);
    el.appendChild(body);
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
      if (!savedConversations.length) {
        historyListEl.innerHTML = '<div class="history-empty">No saved conversations for this project</div>';
        return;
      }
      historyListEl.innerHTML = savedConversations.map(conv => {
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
        el.addEventListener('click', async (e) => {
          if (e.target.closest('.history-item-del')) return;
          const id   = el.dataset.id;
          const conv = savedConversations.find(c => c.id === id);
          if (conv) {
            await loadConversation(conv);
            closeHistory();
          }
        });
      });

      historyListEl.querySelectorAll('.history-item-del').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          e.stopPropagation();
          await deleteConversation(btn.dataset.id);
        });
      });
    } catch { historyListEl.innerHTML = '<div class="history-empty">Error loading history</div>'; }
  }

  async function deleteConversation(id) {
    savedConversations = savedConversations.filter(c => c.id !== id);
    await persistHistory();
    renderHistoryDropdown();
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
    async onProjectActivated(filename, slug) {
      currentFilename = filename;
      currentProjectSlug = slug || null;
      await loadAndRestoreHistory();
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
    const body = document.createElement('div');
    body.className = 'assistant-message-body';
    const thinking = document.createElement('details');
    thinking.className = 'thinking-block hidden';
    thinking.innerHTML = `
      <summary class="thinking-summary">
        <span>Thinking</span>
      </summary>
      <div class="thinking-content"></div>
    `;
    const thinkingContent = thinking.querySelector('.thinking-content');
    el.innerHTML = `
      <div class="message-avatar">V</div>
    `;
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.innerHTML = '<span class="typing-cursor"></span>';
    body.appendChild(thinking);
    body.appendChild(bubble);
    el.appendChild(body);
    messagesEl.appendChild(el);
    scrollToBottomForce();
    return { bubble, thinking, thinkingContent };
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
      rag_local_query:        'Retrieving local context…',
      rag_global_query:       'Retrieving global context…',
      explore_node_neighbors: 'Exploring graph neighbors…',
      get_node_details:       'Inspecting node details…',
      list_key_entities:      'Listing key entities…',
      get_document_info:      'Fetching document info…',
      read_document:          'Reading document…',
      search_document:        'Searching document…',
      create_doc_link:        'Creating reference link…',
      scroll_to_line:         'Jumping to line…',
    };
    return labels[name] || `${name}…`;
  }

  function formatToolThought(toolName, toolInput) {
    const input = toolInput && typeof toolInput === 'object' ? toolInput : {};
    switch (toolName) {
      case 'get_document_info':
        return 'Fetching document info.';
      case 'search_document':
        return input.query
          ? `Searching for: "${String(input.query)}".`
          : 'Searching the document.';
      case 'read_document': {
        const start = Number.parseInt(input.start_line, 10);
        const end = Number.parseInt(input.end_line, 10);
        if (Number.isFinite(start) && Number.isFinite(end)) {
          return `Reading lines ${start}-${end}.`;
        }
        return 'Reading document content.';
      }
      case 'scroll_to_line': {
        const line = Number.parseInt(input.line_number, 10);
        if (Number.isFinite(line)) {
          return `Jumping to line ${line}.`;
        }
        return 'Jumping to a document location.';
      }
      case 'rag_local_query':
        return 'Retrieving local context.';
      case 'rag_global_query':
        return 'Retrieving global context.';
      case 'list_key_entities':
        return 'Inspecting key entities.';
      case 'get_node_details':
        return 'Inspecting graph node details.';
      case 'explore_node_neighbors':
        return 'Exploring related graph nodes.';
      default:
        return `Calling tool: ${toolName}.`;
    }
  }

  function updateThinkingBlock(thinking, thinkingContent, text) {
    const hasThought = !!text.trim();
    thinking.classList.toggle('hidden', !hasThought);
    if (!hasThought) {
      thinkingContent.innerHTML = '';
      return;
    }
    thinkingContent.innerHTML = renderMarkdownWithMath(text);
    applyKatex(thinkingContent);
    activateDocLinks(thinkingContent);
  }

  function updateBubble(bubble, text, streaming) {
    const hasText = !!text.trim();
    if (!hasText && !streaming) {
      bubble.classList.add('hidden');
      bubble.innerHTML = '';
      return;
    }

    bubble.classList.remove('hidden');
    let html = renderMarkdownWithMath(text || '');
    if (streaming) html += '<span class="typing-cursor"></span>';

    bubble.innerHTML = html || '<span class="typing-cursor"></span>';
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

    const assistantView = createAssistantBubble();
    let   visibleText   = '';
    let   thoughtText   = '';
    let   currentToolEl = null;

    const cleanup = () => {
      if (currentToolEl) { currentToolEl.remove(); currentToolEl = null; }
      assistantView.bubble.querySelectorAll('.typing-cursor').forEach(c => c.remove());
      App.setStreaming(false);
    };

    const finaliseBubble = () => {
      updateBubble(assistantView.bubble, visibleText, false);
      updateThinkingBlock(assistantView.thinking, assistantView.thinkingContent, thoughtText);
      applyKatex(assistantView.bubble);
      activateDocLinks(assistantView.bubble);
      scrollToBottom();
    };

    // Snapshot history BEFORE adding current message (sent as context).
    // Sanitize to ensure only valid {role, content} string pairs are sent.
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
        assistantView.bubble.innerHTML = `<span style="color:var(--error)">Error ${res.status}: ${escapeHtml(String(detail))}</span>`;
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

            case 'message_to_user':
            case 'text':
              visibleText += event.content;
              updateBubble(assistantView.bubble, visibleText, true);
              activateDocLinks(assistantView.bubble);
              scrollToBottom();
              break;

            case 'thought':
              thoughtText += event.content;
              updateThinkingBlock(assistantView.thinking, assistantView.thinkingContent, thoughtText);
              scrollToBottom();
              break;

            case 'tool_call': {
              if (currentToolEl) currentToolEl.remove();
              currentToolEl = createToolIndicator(event.tool_name);
              thoughtText += (thoughtText.trim() ? '\n\n' : '') + formatToolThought(event.tool_name, event.tool_input);
              updateThinkingBlock(assistantView.thinking, assistantView.thinkingContent, thoughtText);
              updateBubble(assistantView.bubble, visibleText, true);
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
              if (visibleText.trim()) {
                history.push({ role: 'user', content: text });
                history.push({ role: 'assistant', content: visibleText });
                await persistHistory();
              }
              createRecursionLimitBanner(() => {
                sendMessage('Please continue from where you left off.');
              });
              return;

            case 'error':
              visibleText += `\n\n*Error: ${escapeHtml(event.content)}*`;
              updateBubble(assistantView.bubble, visibleText, false);
              break;

            case 'done':
              cleanup();
              finaliseBubble();
              // Record completed turn in history
              if (visibleText.trim()) {
                history.push({ role: 'user',      content: text });
                history.push({ role: 'assistant', content: visibleText });
                await persistHistory();
              } else if (thoughtText.trim()) {
                console.debug('Assistant produced thought only; skipping empty visible reply.');
              }
              return;
          }
        }
      }
    } catch (err) {
      assistantView.bubble.innerHTML = `<span style="color:var(--error)">Connection error: ${escapeHtml(String(err))}</span>`;
    } finally {
      cleanup();
    }
  }

})();
