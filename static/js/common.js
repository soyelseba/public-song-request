/* Utilidades compartidas: WebSocket en tiempo real, API, iconos, render de pistas. */
(() => {
  const S = 'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"';
  const F = 'viewBox="0 0 24 24" fill="currentColor" stroke="none"';
  const ICONS = {
    play: `<svg ${F}><path d="M7 4.5v15a1 1 0 0 0 1.5.86l12.5-7.5a1 1 0 0 0 0-1.72L8.5 3.64A1 1 0 0 0 7 4.5z"/></svg>`,
    pause: `<svg ${F}><rect x="6" y="4" width="4" height="16" rx="1.2"/><rect x="14" y="4" width="4" height="16" rx="1.2"/></svg>`,
    next: `<svg ${F}><path d="M5 5.2v13.6a1 1 0 0 0 1.55.83L16 13.2V18a1 1 0 0 0 2 0V6a1 1 0 0 0-2 0v4.8L6.55 4.37A1 1 0 0 0 5 5.2z"/></svg>`,
    stop: `<svg ${F}><rect x="5" y="5" width="14" height="14" rx="2.5"/></svg>`,
    check: `<svg ${S}><path d="M20 6 9 17l-5-5"/></svg>`,
    x: `<svg ${S}><path d="M18 6 6 18M6 6l12 12"/></svg>`,
    up: `<svg ${S}><path d="m18 15-6-6-6 6"/></svg>`,
    down: `<svg ${S}><path d="m6 9 6 6 6-6"/></svg>`,
    top: `<svg ${S}><path d="m17 11-5-5-5 5M17 18l-5-5-5 5"/></svg>`,
    trash: `<svg ${S}><path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>`,
    retry: `<svg ${S}><path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/></svg>`,
    volume: `<svg ${S}><path d="M11 5 6 9H2v6h4l5 4V5z"/><path d="M15.5 8.5a5 5 0 0 1 0 7M19 5a10 10 0 0 1 0 14"/></svg>`,
    music: `<svg ${S}><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>`,
    search: `<svg ${S}><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>`,
    link: `<svg ${S}><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>`,
    zap: `<svg ${S}><path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/></svg>`,
    logout: `<svg ${S}><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/></svg>`,
    send: `<svg ${S}><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></svg>`,
    server: `<svg ${S}><rect x="4" y="2" width="16" height="20" rx="2"/><circle cx="12" cy="14" r="4"/><path d="M12 6h.01"/></svg>`,
    globe: `<svg ${S}><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>`,
    user: `<svg ${S}><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`,
    requeue: `<svg ${S}><path d="M11 12H3M16 6H3M16 18H3M18 9v6M21 12h-6"/></svg>`,
    shield: `<svg ${S}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>`,
    headphones: `<svg ${S}><path d="M3 14h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a9 9 0 0 1 18 0v7a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3"/></svg>`,
    inbox: `<svg ${S}><path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/></svg>`,
    list: `<svg ${S}><path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/></svg>`,
    history: `<svg ${S}><path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l4 2"/></svg>`,
    alert: `<svg ${S}><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg>`,
    sparkles: `<svg ${S}><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/></svg>`,
    youtube: `<svg ${F}><path d="M23 7.2a3 3 0 0 0-2.1-2.1C19 4.6 12 4.6 12 4.6s-7 0-8.9.5A3 3 0 0 0 1 7.2 31 31 0 0 0 .5 12a31 31 0 0 0 .5 4.8 3 3 0 0 0 2.1 2.1c1.9.5 8.9.5 8.9.5s7 0 8.9-.5a3 3 0 0 0 2.1-2.1 31 31 0 0 0 .5-4.8 31 31 0 0 0-.5-4.8zM9.75 15.02V8.98L15.5 12l-5.75 3.02z"/></svg>`,
    spotify: `<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill="currentColor"/><path d="M6.5 9.4c3.8-1.2 7.9-.9 11 .9M7 12.6c3.1-.9 6.4-.6 9 .8M7.6 15.6c2.4-.6 4.9-.4 6.9.7" stroke="#0b0b12" stroke-width="1.7" fill="none" stroke-linecap="round"/></svg>`,
    soundcloud: `<svg ${F}><path d="M17.5 10.2a4.6 4.6 0 0 0-1.3.2A6 6 0 0 0 10.4 6v12.2h7.1a4 4 0 0 0 0-8zM8.4 7.6h1.1v10.6H8.4zM6.4 9.2h1.1v9H6.4zM4.4 10.8h1.1v7.4H4.4zM2.4 12.6h1.1v5.6H2.4z"/></svg>`,
  };

  const STATUS = {
    resolving: 'Buscando…', pending: 'En revisión', approved: 'Aprobada', downloading: 'Descargando',
    ready: 'En cola', playing: 'Sonando', played: 'Reproducida', rejected: 'Rechazada', error: 'Error',
  };
  const PLATFORM = { youtube: 'YouTube', spotify: 'Spotify', soundcloud: 'SoundCloud', search: 'Búsqueda', web: 'Enlace' };

  const listeners = {};
  const SR = {
    state: null,
    receivedAt: 0,
    connected: false,
    icons: ICONS,
    getPosition: null, // puede sobrescribirse (p. ej. el reproductor web usa audio.currentTime)

    icon: (name) => ICONS[name] || '',
    on(evt, fn) { (listeners[evt] ||= []).push(fn); },
    emit(evt, data) { (listeners[evt] || []).forEach((fn) => fn(data)); },

    connect(role = 'guest') {
      let retry = 0;
      const open = () => {
        const proto = location.protocol === 'https:' ? 'wss' : 'ws';
        const ws = new WebSocket(`${proto}://${location.host}/ws?role=${role}`);
        SR.ws = ws;
        ws.onopen = () => { retry = 0; SR.connected = true; SR.emit('connection', true); };
        ws.onmessage = (e) => {
          const m = JSON.parse(e.data);
          if (m.type === 'state') {
            SR.state = m; SR.receivedAt = performance.now(); SR.emit('state', m);
          } else if (m.type === 'progress' && SR.state && SR.state.player.track_token === m.token) {
            SR.state.player.position = m.position; SR.receivedAt = performance.now();
          }
        };
        ws.onclose = () => {
          SR.connected = false; SR.emit('connection', false);
          setTimeout(open, Math.min(6000, 400 * 2 ** retry++));
        };
      };
      open();
      SR.on('connection', (on) => {
        const el = document.getElementById('conn-status');
        if (!el) return;
        el.classList.toggle('online', on);
        el.querySelector('span:last-child').textContent = on ? 'En vivo' : 'Reconectando…';
      });
    },

    send(obj) { if (SR.ws && SR.ws.readyState === 1) SR.ws.send(JSON.stringify(obj)); },

    async api(path, body, method = 'POST') {
      const res = await fetch(path, {
        method, headers: { 'Content-Type': 'application/json' },
        body: body === undefined ? (method === 'POST' ? '{}' : undefined) : JSON.stringify(body),
      });
      let data = null;
      try { data = await res.json(); } catch { /* vacío */ }
      if (!res.ok) {
        let msg = data && data.detail;
        if (Array.isArray(msg)) msg = msg.map((d) => d.msg).join(', ');
        if (res.status === 401 && !msg) msg = 'Sesión expirada';
        throw new Error(msg || `Error ${res.status}`);
      }
      return data;
    },

    position() {
      if (SR.getPosition) { const p = SR.getPosition(); if (p !== null && p !== undefined) return p; }
      const p = SR.state && SR.state.player;
      if (!p || !p.current) return 0;
      let pos = p.position + (p.playing ? (performance.now() - SR.receivedAt) / 1000 : 0);
      if (p.current.duration) pos = Math.min(pos, p.current.duration);
      return Math.max(0, pos);
    },

    fmtTime(s) {
      if (!s && s !== 0) return '–:––';
      s = Math.max(0, Math.floor(s));
      const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = String(s % 60).padStart(2, '0');
      return h ? `${h}:${String(m).padStart(2, '0')}:${sec}` : `${m}:${sec}`;
    },

    esc(v) {
      return String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    },

    uid() {
      if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
      return 'g-' + Math.random().toString(36).slice(2) + Date.now().toString(36);
    },

    detectPlatform(q) {
      q = (q || '').trim().toLowerCase();
      if (!q) return 'none';
      if (/(youtube\.com|youtu\.be)/.test(q)) return 'youtube';
      if (q.includes('spotify.com') || q.startsWith('spotify:')) return 'spotify';
      if (q.includes('soundcloud.com')) return 'soundcloud';
      if (/^https?:\/\//.test(q)) return 'web';
      return 'search';
    },
    platformIcon: (p) => ({ youtube: 'youtube', spotify: 'spotify', soundcloud: 'soundcloud', web: 'link' }[p] || 'search'),
    platformLabel: (p) => PLATFORM[p] || 'Búsqueda',
    statusLabel: (s) => STATUS[s] || s,

    toast(msg, type = 'info', ms = 3800) {
      let box = document.querySelector('.toasts');
      if (!box) { box = document.createElement('div'); box.className = 'toasts'; document.body.appendChild(box); }
      const el = document.createElement('div');
      el.className = `toast ${type}`;
      el.innerHTML = `${ICONS[type === 'success' ? 'check' : type === 'error' ? 'alert' : 'sparkles']}<span>${SR.esc(msg)}</span>`;
      box.appendChild(el);
      setTimeout(() => { el.classList.add('out'); setTimeout(() => el.remove(), 320); }, ms);
    },

    /** Fila de pista reutilizable. */
    trackRow(r, { index = null, actions = '', showStatus = true } = {}) {
      const title = r.title || r.query || 'Buscando…';
      const sub = [r.artist, r.duration ? SR.fmtTime(r.duration) : null].filter(Boolean).map(SR.esc).join(' · ');
      const thumb = r.thumbnail ? `style="background-image:url('${SR.esc(r.thumbnail)}')"` : '';
      const pct = r.status === 'downloading' && r.progress != null ? ` ${Math.round(r.progress)}%` : '';
      return `
        <li class="track ${r.status === 'playing' ? 'is-playing' : ''}" data-id="${r.id}">
          ${index !== null ? `<span class="track-index">${index}</span>` : ''}
          <div class="thumb" ${thumb}>${r.thumbnail ? '' : ICONS.music}
            <span class="platform ${r.platform || 'search'}">${ICONS[SR.platformIcon(r.platform)]}</span></div>
          <div class="track-meta">
            <div class="track-title" title="${SR.esc(title)}">${SR.esc(title)}</div>
            <div class="track-sub">${sub}${sub ? ' · ' : ''}<span class="by">por ${SR.esc(r.guest_name || 'Anónimo')}</span></div>
            ${r.error && ['error', 'rejected'].includes(r.status) ? `<div class="track-error">${SR.esc(r.error)}</div>` : ''}
            ${r.status === 'downloading' ? `<div class="mini-progress"><i style="width:${r.progress || 2}%"></i></div>` : ''}
          </div>
          ${showStatus ? `<span class="chip chip-${r.status}">${SR.statusLabel(r.status)}${pct}</span>` : ''}
          ${actions ? `<div class="track-actions">${actions}</div>` : ''}
        </li>`;
    },

    emptyState(icon, text) { return `<li class="empty">${ICONS[icon]}<div>${SR.esc(text)}</div></li>`; },

    /** Rellena la tarjeta "Sonando ahora" (ids now-*). */
    renderNow() {
      const p = SR.state && SR.state.player;
      const cur = p && p.current;
      const $ = (id) => document.getElementById(id);
      const set = (id, fn) => { const el = $(id); if (el) fn(el); };
      const img = cur && cur.thumbnail ? `url('${cur.thumbnail.replace(/'/g, '%27')}')` : '';
      set('now-art', (el) => { el.style.backgroundImage = img; el.innerHTML = cur && cur.thumbnail ? '' : ICONS.music; });
      set('now-bg', (el) => { el.style.backgroundImage = img; });
      set('now-title', (el) => { el.textContent = cur ? (cur.title || 'Sin título') : 'Nada sonando'; });
      set('now-artist', (el) => { el.textContent = cur ? (cur.artist || '') : 'La pista está libre… ¡pide la primera canción!'; });
      set('now-by', (el) => { el.innerHTML = cur ? `${ICONS.user} pedida por ${SR.esc(cur.guest_name || 'Anónimo')}` : ''; el.classList.toggle('hidden', !cur); });
      set('now-duration', (el) => { el.textContent = SR.fmtTime(cur ? cur.duration : 0); });
      set('now-card', (el) => { el.classList.toggle('paused', !(p && p.playing && cur)); el.classList.toggle('playing', !!(p && p.playing && cur)); });
      set('now-eyebrow', (el) => { el.lastChild.textContent = cur ? (p.playing ? ' Sonando ahora' : ' En pausa') : ' En espera'; });
    },

    startProgressLoop() {
      const tick = () => {
        const cur = SR.state && SR.state.player.current;
        const pos = SR.position();
        const pct = cur && cur.duration ? Math.min(100, (pos / cur.duration) * 100) : 0;
        const fill = document.getElementById('now-progress');
        if (fill) fill.style.width = pct + '%';
        const el = document.getElementById('now-elapsed');
        if (el) el.textContent = SR.fmtTime(cur ? pos : 0);
        requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    },

    /** Reemplaza innerHTML solo si cambió (evita parpadeos). */
    patch(el, html) { if (el && el._html !== html) { el._html = html; el.innerHTML = html; } },

    hydrateIcons(root = document) {
      root.querySelectorAll('[data-icon]').forEach((el) => { el.insertAdjacentHTML('afterbegin', ICONS[el.dataset.icon] || ''); });
    },
  };

  window.SR = SR;
  document.addEventListener('DOMContentLoaded', () => SR.hydrateIcons());
})();
