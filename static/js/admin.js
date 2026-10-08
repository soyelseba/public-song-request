/* Panel del administrador. */
(() => {
  const $ = (s) => document.querySelector(s);
  const I = SR.icons;
  const btn = (action, icon, title, cls = '') =>
    `<button class="icon-btn ${cls}" data-action="${action}" title="${title}">${I[icon]}</button>`;

  async function act(fn, okMsg) {
    try { await fn(); if (okMsg) SR.toast(okMsg, 'success', 2200); }
    catch (err) {
      SR.toast(err.message, 'error');
      if (/sesión/i.test(err.message)) setTimeout(() => (location.href = '/login?next=/admin'), 1200);
    }
  }

  // ---------------------------------------------------------- acciones por fila
  document.addEventListener('click', (e) => {
    const b = e.target.closest('[data-action]');
    if (!b) return;
    const li = b.closest('[data-id]');
    const id = li && li.dataset.id;
    const a = b.dataset.action;
    const map = {
      approve: () => SR.api(`/api/requests/${id}/approve`),
      reject: () => SR.api(`/api/requests/${id}/reject`),
      retry: () => SR.api(`/api/requests/${id}/retry`),
      requeue: () => SR.api(`/api/requests/${id}/requeue`),
      play_now: () => SR.api(`/api/requests/${id}/play_now`),
      up: () => SR.api(`/api/requests/${id}/move`, { direction: 'up' }),
      down: () => SR.api(`/api/requests/${id}/move`, { direction: 'down' }),
      top: () => SR.api(`/api/requests/${id}/move`, { direction: 'top' }),
      delete: () => SR.api(`/api/requests/${id}`, undefined, 'DELETE'),
    };
    if (map[a]) { b.disabled = true; act(map[a]).finally(() => (b.disabled = false)); }
  });

  // ---------------------------------------------------------- controles
  $('#toggle-btn').addEventListener('click', () => act(() => SR.api('/api/player/toggle')));
  $('#next-btn').addEventListener('click', () => act(() => SR.api('/api/player/next')));
  $('#stop-btn').addEventListener('click', () => act(() => SR.api('/api/player/stop')));
  $('#set-open').addEventListener('change', (e) => act(() => SR.api('/api/settings', { requests_open: e.target.checked })));
  $('#set-auto').addEventListener('change', (e) => act(() => SR.api('/api/settings', { auto_approve: e.target.checked })));
  $('#approve-all-btn').addEventListener('click', () => act(() => SR.api('/api/approve-all'), 'Todas aprobadas'));
  $('#clear-history-btn').addEventListener('click', () => {
    if (confirm('¿Borrar el historial de canciones reproducidas, rechazadas y con error?')) act(() => SR.api('/api/history/clear'));
  });
  $('#logout-btn').addEventListener('click', async () => { await SR.api('/api/logout'); location.href = '/login?next=/admin'; });
  $('#admin-add').addEventListener('submit', (e) => {
    e.preventDefault();
    const q = $('#admin-q').value.trim();
    if (q.length < 2) return;
    act(async () => {
      await SR.api('/api/requests', { query: q, guest_name: 'DJ', guest_id: 'admin' });
      $('#admin-q').value = '';
    }, 'Añadida');
  });

  // ---------------------------------------------------------- Red & Código QR
  const ipInput = $('#ip-input');
  const saveIpBtn = $('#save-ip-btn');
  const resetIpBtn = $('#reset-ip-btn');
  const qrModal = $('#qr-modal');
  let currentShareUrl = '';

  function openQrModal() {
    if (qrModal) qrModal.classList.remove('hidden');
  }
  function closeQrModal() {
    if (qrModal) qrModal.classList.add('hidden');
  }

  $('#open-qr-btn').addEventListener('click', openQrModal);
  $('#qr-thumb-box').addEventListener('click', openQrModal);
  $('#qr-modal-close').addEventListener('click', closeQrModal);
  $('#qr-modal-bg').addEventListener('click', closeQrModal);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && qrModal && !qrModal.classList.contains('hidden')) {
      closeQrModal();
    }
  });

  $('#copy-btn').addEventListener('click', () => {
    const url = currentShareUrl || $('#share-url').textContent;
    (navigator.clipboard ? navigator.clipboard.writeText(url) : Promise.reject())
      .then(() => SR.toast('Enlace copiado al portapapeles 📋', 'success', 2000))
      .catch(() => prompt('Copia el enlace:', url));
  });

  async function saveIp(val) {
    saveIpBtn.disabled = true;
    try {
      await SR.api('/api/settings', { server_ip: val });
      SR.toast(val ? `IP guardada: ${val} ✔` : 'Restablecido a IP automática ✔', 'success', 2400);
    } catch (err) {
      SR.toast(err.message, 'error');
    } finally {
      saveIpBtn.disabled = false;
    }
  }

  saveIpBtn.addEventListener('click', () => saveIp(ipInput.value.trim()));
  ipInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      saveIp(ipInput.value.trim());
    }
  });
  resetIpBtn.addEventListener('click', () => {
    ipInput.value = '';
    saveIp('');
  });

  const detectedIpsBox = $('#detected-ips');
  if (detectedIpsBox) {
    detectedIpsBox.addEventListener('click', (e) => {
      const pill = e.target.closest('[data-ip]');
      if (!pill) return;
      const ip = pill.dataset.ip;
      ipInput.value = ip;
      saveIp(ip);
    });
  }

  // ---------------------------------------------------------- render
  function render() {
    const s = SR.state;
    if (!s) return;
    if (!s.admin) { location.href = '/login?next=/admin'; return; }
    SR.renderNow();
    const p = s.player;

    $('#toggle-btn').innerHTML = p.playing ? I.pause : I.play;
    $('#set-open').checked = s.settings.requests_open;
    $('#set-auto').checked = s.settings.auto_approve;

    // Actualizar URL y código QR reactivamente
    if (s.share_url && s.share_url !== currentShareUrl) {
      currentShareUrl = s.share_url;
      $('#share-url').textContent = s.share_url;
      const modalShare = $('#modal-share-url');
      if (modalShare) modalShare.textContent = s.share_url;
      const qrSrc = `/qr.svg?url=${encodeURIComponent(s.share_url)}&v=${Date.now()}`;
      const adminQr = $('#admin-qr-img');
      if (adminQr) adminQr.src = qrSrc;
      const modalQr = $('#modal-qr-img');
      if (modalQr) modalQr.src = qrSrc;
    }

    // Campo de IP manual (si no está enfocado por el usuario)
    if (document.activeElement !== ipInput) {
      ipInput.value = s.settings.server_ip || '';
    }

    // Pills con IPs detectadas
    if (detectedIpsBox && s.available_ips && s.available_ips.length) {
      const activeIp = (s.settings.server_ip || '').trim();
      const pillsHtml = s.available_ips.map((ip) => {
        const isCurrent = activeIp === ip || (!activeIp && s.share_url && s.share_url.includes(ip));
        return `<button type="button" class="ip-pill ${isCurrent ? 'active' : ''}" data-ip="${SR.esc(ip)}" title="Seleccionar ${SR.esc(ip)}">${SR.esc(ip)}</button>`;
      }).join('');
      SR.patch(detectedIpsBox, pillsHtml);
    }

    const modeLabel = p.mode === 'local' ? `${I.server} Servidor (ffplay)` : `${I.globe} Navegador`;
    let warn = '';
    if (p.mode === 'browser' && !s.players_online) warn = `<span class="pill warn">${I.alert} Abre la vista Reproductor para escuchar</span>`;
    if (p.error) warn += `<span class="pill warn">${I.alert} ${SR.esc(p.error)}</span>`;
    SR.patch($('#player-status'),
      `<span class="pill">${modeLabel}</span><span class="pill">${I.volume} ${p.volume}%</span>` +
      (p.mode === 'browser' && s.players_online ? `<span class="pill">${I.headphones} ${s.players_online} reproductor(es)</span>` : '') + warn);

    const reqs = s.requests;
    const pending = reqs.filter((r) => ['resolving', 'pending'].includes(r.status));
    const queue = reqs.filter((r) => ['approved', 'downloading', 'ready'].includes(r.status)).sort((a, b) => a.position - b.position);
    const history = reqs.filter((r) => ['played', 'rejected', 'error'].includes(r.status));

    const pc = $('#pending-count');
    pc.textContent = pending.length;
    pc.classList.toggle('hot', pending.some((r) => r.status === 'pending'));
    $('#approve-all-btn').classList.toggle('hidden', !pending.some((r) => r.status === 'pending'));
    document.title = (pending.length ? `(${pending.length}) ` : '') + 'Panel del DJ · SongRequest';

    SR.patch($('#pending-list'), pending.length ? pending.map((r) => SR.trackRow(r, {
      showStatus: r.status === 'resolving',
      actions: r.status === 'pending'
        ? btn('approve', 'check', 'Aprobar', 'ok') + btn('play_now', 'zap', 'Aprobar y poner primera', 'accent') + btn('reject', 'x', 'Rechazar', 'danger')
        : btn('delete', 'trash', 'Eliminar', 'danger'),
    })).join('') : SR.emptyState('inbox', 'Sin peticiones pendientes'));

    $('#queue-count').textContent = queue.length;
    const total = queue.reduce((t, r) => t + (r.duration || 0), 0);
    $('#queue-time').textContent = total ? `≈ ${SR.fmtTime(total)}` : '';
    SR.patch($('#queue-list'), queue.length ? queue.map((r, i) => SR.trackRow(r, {
      index: i + 1,
      showStatus: r.status !== 'ready',
      actions: btn('play_now', 'zap', 'Reproducir ahora', 'accent') +
        (i > 0 ? btn('up', 'up', 'Subir') : '') +
        (i < queue.length - 1 ? btn('down', 'down', 'Bajar') : '') +
        btn('reject', 'x', 'Quitar de la cola', 'danger'),
    })).join('') : SR.emptyState('list', 'La cola está vacía'));

    SR.patch($('#history-list'), history.length ? history.map((r) => SR.trackRow(r, {
      actions: (r.status === 'error' ? btn('retry', 'retry', 'Reintentar') : btn('requeue', 'requeue', 'Volver a encolar')) +
        btn('delete', 'trash', 'Eliminar', 'danger'),
    })).join('') : SR.emptyState('history', 'Aún no hay historial'));
  }

  SR.on('state', render);
  SR.connect('admin');
  SR.startProgressLoop();
})();
