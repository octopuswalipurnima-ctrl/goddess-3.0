"""Interactive Web Testing Console for Goddess AI 3.0 (Honney)."""


def get_test_interface_html() -> str:
    """Return the HTML/CSS/JS for the live stream bot testing console."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>🍯 Goddess AI 3.0 — Bot Testing Console</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #090a10;
      --card-bg: rgba(18, 20, 32, 0.75);
      --card-border: rgba(139, 92, 246, 0.22);
      --card-hover: rgba(26, 29, 46, 0.85);
      --primary: #8b5cf6;
      --primary-glow: rgba(139, 92, 246, 0.4);
      --primary-dark: #6d28d9;
      --honey: #f59e0b;
      --honey-glow: rgba(245, 158, 11, 0.35);
      --text: #f3f4f6;
      --text-muted: #9ca3af;
      --text-dim: #6b7280;
      --success: #10b981;
      --success-glow: rgba(16, 185, 129, 0.25);
      --danger: #ef4444;
      --danger-glow: rgba(239, 68, 68, 0.25);
      --radius-lg: 16px;
      --radius-md: 10px;
      --radius-sm: 6px;
      --font-sans: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      background-color: var(--bg);
      background-image:
        radial-gradient(circle at 15% 15%, rgba(139, 92, 246, 0.12) 0%, transparent 40%),
        radial-gradient(circle at 85% 85%, rgba(245, 158, 11, 0.08) 0%, transparent 40%);
      color: var(--text);
      font-family: var(--font-sans);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      line-height: 1.5;
      padding: 2rem 1.25rem;
    }

    .container {
      max-width: 1080px;
      margin: 0 auto;
      width: 100%;
    }

    /* Header */
    header {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 1rem;
      margin-bottom: 2rem;
      padding-bottom: 1.5rem;
      border-bottom: 1px solid var(--card-border);
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 0.85rem;
    }

    .brand-icon {
      font-size: 2.2rem;
      background: linear-gradient(135deg, rgba(245, 158, 11, 0.2), rgba(139, 92, 246, 0.2));
      border: 1px solid var(--card-border);
      padding: 0.35rem 0.65rem;
      border-radius: var(--radius-md);
      box-shadow: 0 0 20px var(--primary-glow);
    }

    .brand-title h1 {
      font-size: 1.45rem;
      font-weight: 800;
      letter-spacing: -0.02em;
      background: linear-gradient(135deg, #fff 40%, var(--primary) 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .brand-title p {
      font-size: 0.82rem;
      color: var(--text-muted);
      font-weight: 500;
    }

    .status-pills {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      flex-wrap: wrap;
    }

    .pill {
      font-size: 0.75rem;
      font-weight: 600;
      padding: 0.35rem 0.75rem;
      border-radius: 9999px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
    }

    .pill.online {
      background: rgba(16, 185, 129, 0.12);
      border-color: rgba(16, 185, 129, 0.3);
      color: #34d399;
    }

    .pill.warning {
      background: rgba(245, 158, 11, 0.12);
      border-color: rgba(245, 158, 11, 0.3);
      color: #fbbf24;
    }

    .pill.offline {
      background: rgba(239, 68, 68, 0.12);
      border-color: rgba(239, 68, 68, 0.3);
      color: #f87171;
    }

    .pill-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background-color: currentColor;
    }

    /* Grid Layout */
    .grid-2 {
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 1.5rem;
      margin-bottom: 1.5rem;
    }

    @media (max-width: 860px) {
      .grid-2 {
        grid-template-columns: 1fr;
      }
    }

    /* Cards */
    .card {
      background: var(--card-bg);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid var(--card-border);
      border-radius: var(--radius-lg);
      padding: 1.5rem;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
      transition: border-color 0.2s, box-shadow 0.2s;
    }

    .card:hover {
      border-color: rgba(139, 92, 246, 0.35);
    }

    .card-title {
      font-size: 1.05rem;
      font-weight: 700;
      margin-bottom: 1rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      color: #fff;
    }

    /* Form & Inputs */
    .form-group {
      margin-bottom: 1.2rem;
    }

    label {
      display: block;
      font-size: 0.84rem;
      font-weight: 600;
      color: var(--text-muted);
      margin-bottom: 0.45rem;
    }

    .input-wrapper {
      position: relative;
      display: flex;
      gap: 0.6rem;
    }

    input[type="text"], input[type="url"] {
      width: 100%;
      background: rgba(10, 12, 20, 0.8);
      border: 1px solid rgba(139, 92, 246, 0.25);
      border-radius: var(--radius-md);
      color: #fff;
      font-family: var(--font-sans);
      font-size: 0.95rem;
      padding: 0.85rem 1rem;
      min-height: 48px;
      outline: none;
      transition: all 0.2s ease;
    }

    input[type="text"]:focus-visible, input[type="url"]:focus-visible {
      border-color: var(--primary);
      box-shadow: 0 0 0 3px var(--primary-glow);
      background: rgba(15, 17, 28, 0.95);
    }

    /* Buttons */
    .btn {
      font-family: var(--font-sans);
      font-size: 0.92rem;
      font-weight: 600;
      border: none;
      border-radius: var(--radius-md);
      padding: 0.85rem 1.4rem;
      min-height: 48px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      transition: all 0.2s ease;
      white-space: nowrap;
      text-decoration: none;
    }

    .btn:focus-visible {
      outline: 2px solid #fff;
      outline-offset: 2px;
    }

    .btn-primary {
      background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
      color: #fff;
      box-shadow: 0 4px 14px var(--primary-glow);
    }

    .btn-primary:hover:not(:disabled) {
      transform: translateY(-1px);
      box-shadow: 0 6px 20px var(--primary-glow);
      filter: brightness(1.1);
    }

    .btn-danger {
      background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%);
      color: #fff;
      box-shadow: 0 4px 14px var(--danger-glow);
    }

    .btn-danger:hover:not(:disabled) {
      transform: translateY(-1px);
      filter: brightness(1.1);
    }

    .btn-secondary {
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: var(--text);
    }

    .btn-secondary:hover:not(:disabled) {
      background: rgba(255, 255, 255, 0.14);
    }

    .btn:disabled {
      opacity: 0.55;
      cursor: not-allowed;
      transform: none !important;
    }

    /* Channel Quick Chips */
    .chip-container {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin-top: 0.75rem;
    }

    .chip {
      font-size: 0.75rem;
      font-weight: 500;
      background: rgba(139, 92, 246, 0.1);
      border: 1px solid rgba(139, 92, 246, 0.2);
      color: #c4b5fd;
      padding: 0.35rem 0.65rem;
      border-radius: var(--radius-sm);
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .chip:hover {
      background: rgba(139, 92, 246, 0.2);
      border-color: var(--primary);
      color: #fff;
    }

    /* Active Stream Box */
    .active-stream-box {
      background: rgba(10, 12, 20, 0.6);
      border: 1px solid rgba(16, 185, 129, 0.3);
      border-radius: var(--radius-md);
      padding: 1.25rem;
      margin-top: 1rem;
    }

    .stream-meta {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 0.75rem;
      margin-top: 0.75rem;
      font-family: var(--font-mono);
      font-size: 0.8rem;
    }

    .meta-item {
      background: rgba(255, 255, 255, 0.03);
      padding: 0.5rem 0.75rem;
      border-radius: var(--radius-sm);
      border: 1px solid rgba(255, 255, 255, 0.05);
    }

    .meta-label {
      color: var(--text-dim);
      font-size: 0.7rem;
      text-transform: uppercase;
      margin-bottom: 0.15rem;
    }

    .meta-val {
      color: var(--text);
      font-weight: 600;
      word-break: break-all;
    }

    /* Chat Log Feed */
    .chat-feed {
      height: 320px;
      overflow-y: auto;
      background: rgba(10, 12, 20, 0.85);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: var(--radius-md);
      padding: 0.85rem;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      font-family: var(--font-mono);
      font-size: 0.82rem;
    }

    .chat-msg {
      padding: 0.45rem 0.65rem;
      border-radius: var(--radius-sm);
      background: rgba(255, 255, 255, 0.03);
      border-left: 3px solid var(--primary);
      animation: fadeIn 0.2s ease-out;
    }

    .chat-msg.bot {
      border-left-color: var(--honey);
      background: rgba(245, 158, 11, 0.08);
    }

    .chat-author {
      font-weight: 700;
      color: #a78bfa;
      margin-right: 0.4rem;
    }

    .chat-msg.bot .chat-author {
      color: #fbbf24;
    }

    .chat-text {
      color: var(--text);
      word-break: break-word;
    }

    .chat-time {
      font-size: 0.68rem;
      color: var(--text-dim);
      float: right;
    }

    .empty-state {
      height: 100%;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      color: var(--text-dim);
      text-align: center;
      gap: 0.5rem;
    }

    /* Toast Notification */
    #toast-container {
      position: fixed;
      bottom: 1.5rem;
      right: 1.5rem;
      z-index: 100;
      display: flex;
      flex-direction: column;
      gap: 0.6rem;
      max-width: 400px;
    }

    .toast {
      background: rgba(20, 24, 38, 0.95);
      backdrop-filter: blur(12px);
      border: 1px solid var(--card-border);
      color: #fff;
      padding: 0.85rem 1.15rem;
      border-radius: var(--radius-md);
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
      font-size: 0.88rem;
      display: flex;
      align-items: center;
      gap: 0.65rem;
      animation: slideIn 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .toast.success { border-color: var(--success); }
    .toast.error { border-color: var(--danger); }

    @keyframes slideIn {
      from { transform: translateX(100%); opacity: 0; }
      to { transform: translateX(0); opacity: 1; }
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(4px); }
      to { opacity: 1; transform: translateY(0); }
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand">
        <div class="brand-icon">🍯</div>
        <div class="brand-title">
          <h1>GODDESS AI 3.0</h1>
          <p>YouTube Live AI Co-Host (Honney) & Moderation Testing Console</p>
        </div>
      </div>
      <div class="status-pills">
        <div id="pill-db" class="pill warning"><span class="pill-dot"></span> <span id="txt-db">DB: Checking</span></div>
        <div id="pill-yt" class="pill warning"><span class="pill-dot"></span> <span id="txt-yt">YT Keys: Checking</span></div>
        <div id="pill-oauth" class="pill warning"><span class="pill-dot"></span> <span id="txt-oauth">OAuth: Checking</span></div>
        <div id="pill-workers" class="pill offline"><span class="pill-dot"></span> <span id="txt-workers">Streams: 0 Live</span></div>
      </div>
    </header>

    <main>
      <div class="grid-2">
        <!-- Left: Stream Connection Form -->
        <section class="card" aria-labelledby="connect-heading">
          <h2 id="connect-heading" class="card-title">🚀 Connect Bot to Live Stream</h2>
          <form id="connect-form" onsubmit="handleConnect(event)">
            <div class="form-group">
              <label for="stream-url">YouTube Live Stream Link or Video ID</label>
              <div class="input-wrapper">
                <input
                  type="text"
                  id="stream-url"
                  name="stream_url"
                  placeholder="Paste YouTube Live URL (e.g. https://www.youtube.com/watch?v=... or Video ID)"
                  autocomplete="off"
                  spellcheck="false"
                  required
                >
                <button type="submit" id="btn-connect" class="btn btn-primary">
                  <span id="btn-connect-text">Connect</span>
                </button>
              </div>
            </div>
          </form>

          <div style="margin-top: 1rem;">
            <label>Configured Channels Quick Scan:</label>
            <div class="chip-container">
              <button type="button" class="chip" onclick="pasteChannel('UCCMwadkzXrznmMpZd5ek6PA', 'Misayuislive')">🎮 Misayuislive (UCCMwadkz...)</button>
              <button type="button" class="chip" onclick="pasteChannel('UCGH_osSgL2FCsBYe6XMxlSQ', 'GODDESS IS LIVE')">👑 GODDESS IS LIVE (UCGH_os...)</button>
              <button type="button" class="chip" onclick="pasteChannel('UCVQ8Qn1JPuZV8VzOgIdUGxQ', 'nawaabo_is_live')">⚔️ nawaabo_is_live (UCVQ8Qn...)</button>
              <button type="button" class="chip" onclick="pasteChannel('UCf4bzltnoyrCM_SAXLTfvAg', 'Winxy')">✨ Winxy (UCf4bzlt...)</button>
              <button type="button" class="chip" style="background: rgba(245, 158, 11, 0.15); color: #fbbf24; border-color: rgba(245, 158, 11, 0.3);" onclick="triggerScan()">🔄 Scan All Channels Now</button>
            </div>
          </div>

          <!-- Active Connection Status Card -->
          <div id="active-stream-panel" style="margin-top: 1.5rem; display: none;">
            <h3 style="font-size: 0.95rem; color: #a78bfa; margin-bottom: 0.5rem;">Active Connected Stream:</h3>
            <div class="active-stream-box">
              <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; flex-wrap: wrap;">
                <div>
                  <h4 id="active-stream-title" style="font-size: 1.05rem; font-weight: 700; color: #fff;">Stream Title</h4>
                  <p id="active-channel-name" style="color: var(--honey); font-size: 0.85rem; font-weight: 600; margin-top: 0.15rem;">Channel</p>
                </div>
                <button type="button" class="btn btn-danger" style="padding: 0.5rem 0.9rem; min-height: 38px; font-size: 0.82rem;" onclick="handleDisconnect()">
                  ⏹ Disconnect
                </button>
              </div>
              <div class="stream-meta">
                <div class="meta-item">
                  <div class="meta-label">Video ID</div>
                  <div id="active-video-id" class="meta-val">-</div>
                </div>
                <div class="meta-item">
                  <div class="meta-label">Live Chat ID</div>
                  <div id="active-chat-id" class="meta-val">-</div>
                </div>
                <div class="meta-item">
                  <div class="meta-label">Worker Status</div>
                  <div id="active-worker-state" class="meta-val" style="color: #34d399;">RUNNING</div>
                </div>
                <div class="meta-item">
                  <div class="meta-label">Messages Polled</div>
                  <div id="active-msg-count" class="meta-val">0</div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- Right: Test Chat Sender -->
        <section class="card" aria-labelledby="send-heading">
          <h2 id="send-heading" class="card-title">💬 Send Test Chat Message (via Bot)</h2>
          <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 1rem;">
            Post a message directly into the active YouTube Live chat using the bot's authenticated OAuth account.
          </p>
          <form id="msg-form" onsubmit="handleSendMessage(event)">
            <div class="form-group">
              <label for="chat-message-text">Message to Post</label>
              <input
                type="text"
                id="chat-message-text"
                placeholder="Type a test greeting or command (e.g. 🍯 Hello stream!)..."
                autocomplete="off"
                required
              >
            </div>
            <button type="submit" id="btn-send-msg" class="btn btn-secondary" style="width: 100%;">
              <span>Post Message to Live Chat</span>
            </button>
          </form>
        </section>
      </div>

      <!-- Live Chat Activity Log -->
      <section class="card" aria-labelledby="chat-heading">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.85rem;">
          <h2 id="chat-heading" class="card-title" style="margin-bottom: 0;">📡 Live Chat Poller & Activity Feed</h2>
          <span style="font-size: 0.75rem; color: var(--text-dim);" id="poll-timer">Auto-refreshing every 2.5s</span>
        </div>
        <div id="chat-feed" class="chat-feed" aria-live="polite">
          <div class="empty-state">
            <p>No active live stream connected yet.</p>
            <p style="font-size: 0.75rem;">Paste a YouTube live stream URL above and click <strong>Connect</strong> to begin polling.</p>
          </div>
        </div>
      </section>
    </main>
  </div>

  <div id="toast-container" aria-live="assertive"></div>

  <script>
    let activeVideoId = null;
    let activeChannelId = null;
    let activeLiveChatId = null;

    function showToast(message, type = 'info') {
      const container = document.getElementById('toast-container');
      const toast = document.createElement('div');
      toast.className = `toast ${type}`;
      toast.innerHTML = `<span>${type === 'success' ? '✅' : (type === 'error' ? '❌' : 'ℹ️')}</span> <span>${message}</span>`;
      container.appendChild(toast);
      setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
      }, 4000);
    }

    function pasteChannel(channelId, name) {
      document.getElementById('stream-url').value = channelId;
      showToast(`Selected channel ${name} (${channelId}). Click Connect or Scan!`, 'info');
    }

    async function handleConnect(e) {
      e.preventDefault();
      const input = document.getElementById('stream-url');
      const btn = document.getElementById('btn-connect');
      const url = input.value.trim();
      if (!url) return;

      btn.disabled = true;
      document.getElementById('btn-connect-text').innerText = 'Connecting...';

      try {
        const resp = await fetch('/api/connect', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url })
        });
        const data = await resp.json();

        if (data.success) {
          showToast(data.message || 'Connected to live stream!', 'success');
          activeVideoId = data.video_id;
          activeChannelId = data.channel_id;
          activeLiveChatId = data.live_chat_id;
          input.value = '';
          fetchStatus();
        } else {
          showToast(data.error || 'Failed to connect to stream', 'error');
        }
      } catch (err) {
        showToast('Network error connecting to stream: ' + err.message, 'error');
      } finally {
        btn.disabled = false;
        document.getElementById('btn-connect-text').innerText = 'Connect';
      }
    }

    async function handleDisconnect() {
      if (!activeVideoId && !activeChannelId) return;
      try {
        const resp = await fetch('/api/disconnect', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ video_id: activeVideoId, channel_id: activeChannelId })
        });
        const data = await resp.json();
        if (data.success) {
          showToast(data.message || 'Disconnected from stream.', 'info');
          activeVideoId = null;
          activeChannelId = null;
          activeLiveChatId = null;
          fetchStatus();
        } else {
          showToast(data.error || 'Failed to disconnect', 'error');
        }
      } catch (err) {
        showToast('Error: ' + err.message, 'error');
      }
    }

    async function triggerScan() {
      showToast('Scanning configured channels for live broadcasts...', 'info');
      try {
        const resp = await fetch('/api/scan', { method: 'POST' });
        const data = await resp.json();
        showToast(`Scan finished! Found ${Object.keys(data.results || {}).length} channels scanned.`, 'success');
        fetchStatus();
      } catch (err) {
        showToast('Scan error: ' + err.message, 'error');
      }
    }

    async function handleSendMessage(e) {
      e.preventDefault();
      const input = document.getElementById('chat-message-text');
      const btn = document.getElementById('btn-send-msg');
      const msg = input.value.trim();
      if (!msg) return;

      if (!activeLiveChatId) {
        showToast('No active live chat connected to send message to.', 'error');
        return;
      }

      btn.disabled = true;
      try {
        const resp = await fetch('/api/send-message', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ live_chat_id: activeLiveChatId, message: msg })
        });
        const data = await resp.json();
        if (data.success) {
          showToast('Message posted to YouTube Live chat!', 'success');
          input.value = '';
          fetchStatus();
        } else {
          showToast(data.error || 'Failed to post message. Ensure OAuth is configured.', 'error');
        }
      } catch (err) {
        showToast('Error posting message: ' + err.message, 'error');
      } finally {
        btn.disabled = false;
      }
    }

    async function fetchStatus() {
      try {
        const resp = await fetch('/api/status');
        if (!resp.ok) return;
        const data = await resp.json();

        // Update DB Pill
        const pillDb = document.getElementById('pill-db');
        const txtDb = document.getElementById('txt-db');
        if (data.database && data.database.connected && data.database.schema_ready) {
          pillDb.className = 'pill online';
          txtDb.innerText = 'DB: Ready';
        } else {
          pillDb.className = 'pill offline';
          txtDb.innerText = 'DB: ' + (data.database ? (data.database.connected ? 'Schema Error' : 'Offline') : 'Error');
        }

        // Update YT Pill
        const pillYt = document.getElementById('pill-yt');
        const txtYt = document.getElementById('txt-yt');
        const healthyKeys = data.youtube_api_keys_healthy || 0;
        if (healthyKeys > 0) {
          pillYt.className = 'pill online';
          txtYt.innerText = `YT Keys: ${healthyKeys} Ready`;
        } else {
          pillYt.className = 'pill offline';
          txtYt.innerText = 'YT Keys: None Ready';
        }

        // Update OAuth Pill
        const pillOauth = document.getElementById('pill-oauth');
        const txtOauth = document.getElementById('txt-oauth');
        if (data.oauth_configured) {
          pillOauth.className = 'pill online';
          txtOauth.innerText = 'OAuth: Ready';
        } else {
          pillOauth.className = 'pill warning';
          txtOauth.innerText = 'OAuth: Not Set';
        }

        // Update Active Streams
        const activeStreams = data.active_streams || [];
        const pillWorkers = document.getElementById('pill-workers');
        const txtWorkers = document.getElementById('txt-workers');
        const panel = document.getElementById('active-stream-panel');

        if (activeStreams.length > 0) {
          pillWorkers.className = 'pill online';
          txtWorkers.innerText = `Streams: ${activeStreams.length} Live`;
          panel.style.display = 'block';

          const primary = activeStreams[0];
          activeVideoId = primary.video_id;
          activeChannelId = primary.channel_id;
          activeLiveChatId = primary.live_chat_id;

          document.getElementById('active-stream-title').innerText = primary.title || ('Stream ' + primary.video_id);
          document.getElementById('active-channel-name').innerText = 'Channel ID: ' + primary.channel_id;
          document.getElementById('active-video-id').innerText = primary.video_id;
          document.getElementById('active-chat-id').innerText = primary.live_chat_id ? (primary.live_chat_id.substring(0, 16) + '...') : 'None';
          document.getElementById('active-worker-state').innerText = primary.state || 'RUNNING';
          document.getElementById('active-msg-count').innerText = primary.seen_messages_count || 0;

          // Render Recent Messages
          renderChat(primary.recent_messages || []);
        } else {
          pillWorkers.className = 'pill offline';
          txtWorkers.innerText = 'Streams: 0 Live';
          panel.style.display = 'none';
          activeLiveChatId = null;
        }

      } catch (err) {
        console.error('Error fetching bot status:', err);
      }
    }

    function renderChat(messages) {
      const feed = document.getElementById('chat-feed');
      if (!messages || messages.length === 0) {
        feed.innerHTML = `
          <div class="empty-state">
            <p>Active live stream connected.</p>
            <p style="font-size: 0.75rem;">Waiting for incoming live chat messages from viewers...</p>
          </div>
        `;
        return;
      }

      feed.innerHTML = messages.map(m => {
        const isBot = m.author === 'Honney' || m.is_bot;
        return `
          <div class="chat-msg ${isBot ? 'bot' : ''}">
            <span class="chat-author">${escapeHtml(m.author || 'Viewer')}:</span>
            <span class="chat-text">${escapeHtml(m.message || '')}</span>
          </div>
        `;
      }).join('');
      feed.scrollTop = feed.scrollHeight;
    }

    function escapeHtml(str) {
      return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    // Polling heartbeat
    fetchStatus();
    setInterval(fetchStatus, 2500);
  </script>
</body>
</html>"""
