/* Vista de reproducción: sincroniza un <audio> con el estado del servidor (modo navegador)
   o controla ffplay en el servidor (modo local). */
(() => {
  const $ = (s) => document.querySelector(s);
  const I = SR.icons;
  const audio = new Audio();
  audio.preload = 'auto';

  let unlocked = false;
  let loadedToken = -1;
  let appliedSeek = -1;
  let pendingSeek = 0;

  const isBrowserMode = () => SR.state && SR.state.player.mode === 'browser';

  // En modo navegador la posición real es la del <audio>.
  SR.getPosition = () => (isBrowserMode() && loadedToken === SR.state.player.track_token && audio.src && !isNaN(audio.currentTime) && audio.readyState > 0
    ? audio.currentTime : null);

  const api = (path, body) => SR.api(path, body).catch((e) => SR.toast(e.message, 'error'));

  // ---------------------------------------------------------- sincronización de audio
  function syncAudio() {
    const p = SR.state.player;
    const cur = p.current;
    $('#unlock').classList.toggle('hidden', !(p.mode === 'browser' && !unlocked));

    if (p.mode !== 'browser' || !cur) {
      if (!audio.paused) audio.pause();
      if (!cur && audio.src) { audio.removeAttribute('src'); audio.load(); loadedToken = -1; }
      if (p.mode !== 'browser') loadedToken = -1; // recargar al volver a modo navegador
      return;
    }

    audio.volume = Math.max(0, Math.min(1, p.volume / 100));

    if (loadedToken !== p.track_token) {
      loadedToken = p.track_token;
      appliedSeek = p.seek_token;
      pendingSeek = p.position;
      audio.src = `/media/${cur.id}?t=${p.track_token}`;
    } else if (appliedSeek !== p.seek_token) {
      appliedSeek = p.seek_token;
      if (audio.readyState > 0) audio.currentTime = p.position; else pendingSeek = p.position;
    }

    if (p.playing && audio.paused && unlocked) {
      audio.play().catch((err) => {
        if (err.name === 'NotAllowedError') { unlocked = false; $('#unlock').classList.remove('hidden'); }
      });
    } else if (!p.playing && !audio.paused) {
      audio.pause();
    }
  }

  audio.addEventListener('loadedmetadata', () => {
    if (pendingSeek > 0.5) audio.currentTime = pendingSeek;
    pendingSeek = 0;
  });
  audio.addEventListener('ended', () => SR.send({ type: 'ended', token: loadedToken }));
  audio.addEventListener('error', () => {
    if (!audio.getAttribute('src') || !isBrowserMode()) return;
    SR.send({ type: 'error', token: loadedToken, message: 'El navegador no pudo reproducir el audio' });
  });
  setInterval(() => {
    if (isBrowserMode() && !audio.paused && loadedToken === SR.state.player.track_token) {
      SR.send({ type: 'progress', token: loadedToken, position: audio.currentTime });
    }
  }, 2000);

  let playerShareUrl = '';
  const qrModal = $('#qr-modal');
  function openQrModal() { if (qrModal) qrModal.classList.remove('hidden'); }
  function closeQrModal() { if (qrModal) qrModal.classList.add('hidden'); }
  const playerQrBox = $('#player-qr-box');
  if (playerQrBox) playerQrBox.addEventListener('click', openQrModal);
  const modalClose = $('#qr-modal-close');
  if (modalClose) modalClose.addEventListener('click', closeQrModal);
  const modalBg = $('#qr-modal-bg');
  if (modalBg) modalBg.addEventListener('click', closeQrModal);

  // ---------------------------------------------------------- UI
  function render() {
    const s = SR.state;
    if (!s) return;
    if (!s.admin) { location.href = '/login?next=/player'; return; }
    const p = s.player;
    const cur = p.current;
    const img = cur && cur.thumbnail ? `url('${cur.thumbnail.replace(/'/g, '%27')}')` : '';

    if (s.share_url && s.share_url !== playerShareUrl) {
      playerShareUrl = s.share_url;
      const clean = s.share_url.replace(/^https?:\/\//, '');
      const shareEl = $('#share-url');
      if (shareEl) shareEl.textContent = clean;
      const modalShare = $('#modal-share-url');
      if (modalShare) modalShare.textContent = s.share_url;
      const qrSrc = `/qr.svg?url=${encodeURIComponent(s.share_url)}&v=${Date.now()}`;
      const playerQrImg = $('#player-qr-img');
      if (playerQrImg) playerQrImg.src = qrSrc;
      const modalImg = $('#modal-qr-img');
      if (modalImg) modalImg.src = qrSrc;
    }

    $('#player-root').classList.toggle('playing', !!(p.playing && cur));
    $('#player-root').classList.toggle('paused', !(p.playing && cur));
    $('#cover').style.backgroundImage = img;
    $('#cover').innerHTML = cur && cur.thumbnail ? '' : I.music;
    $('#backdrop').style.backgroundImage = img;
    $('#stage-title').textContent = cur ? cur.title : 'Nada sonando';
    $('#stage-artist').textContent = cur ? (cur.artist || '') : (p.playing ? 'Esperando a que haya canciones listas…' : 'Pulsa play para empezar la fiesta');
    $('#stage-eyebrow').lastElementChild.textContent = cur ? (p.playing ? 'Sonando ahora' : 'En pausa') : 'En espera';
    const by = $('#stage-by');
    by.classList.toggle('hidden', !cur);
    by.innerHTML = cur ? `${I.user} Pedida por ${SR.esc(cur.guest_name || 'Anónimo')}` : '';
    $('#now-duration').textContent = SR.fmtTime(cur ? cur.duration : 0);
    $('#toggle-btn').innerHTML = p.playing ? I.pause : I.play;
    document.title = cur ? `${p.playing ? '▶' : '❚❚'} ${cur.title} · SongRequest` : 'Reproductor · SongRequest';

    $('#mode-browser').classList.toggle('active', p.mode === 'browser');
    $('#mode-local').classList.toggle('active', p.mode === 'local');
    $('#mode-local').disabled = !p.local_available;
    $('#mode-local').title = p.local_available ? 'Reproducir por los altavoces del servidor con ffplay' : 'ffplay no encontrado en el servidor';
    $('#mode-hint').textContent = p.error ? `⚠ ${p.error}` : p.mode === 'local'
      ? 'El audio suena por los altavoces del equipo donde corre el servidor.'
      : 'El audio suena en esta pestaña. Mantenla abierta (solo una pestaña reproductor a la vez).';

    const vol = $('#volume');
    if (document.activeElement !== vol) vol.value = p.volume;
    vol.style.setProperty('--fill', vol.value + '%');

    const queue = s.requests.filter((r) => ['approved', 'downloading', 'ready'].includes(r.status)).sort((a, b) => a.position - b.position);
    $('#queue-count').textContent = queue.length;
    SR.patch($('#queue-list'), queue.length
      ? queue.map((r, i) => SR.trackRow(r, { index: i + 1, showStatus: r.status !== 'ready' })).join('')
      : SR.emptyState('music', 'No hay canciones en cola'));

    syncAudio();
  }

  // ---------------------------------------------------------- eventos
  $('#toggle-btn').addEventListener('click', () => { unlocked = true; api('/api/player/toggle'); });
  $('#next-btn').addEventListener('click', () => api('/api/player/next'));
  $('#stop-btn').addEventListener('click', () => api('/api/player/stop'));
  document.querySelectorAll('[data-mode]').forEach((b) => b.addEventListener('click', () => {
    if (b.dataset.mode === 'browser') unlocked = true;
    api('/api/player/mode', { mode: b.dataset.mode });
  }));
  const vol = $('#volume');
  vol.addEventListener('input', () => {
    vol.style.setProperty('--fill', vol.value + '%');
    if (isBrowserMode()) audio.volume = vol.value / 100; // respuesta inmediata
  });
  vol.addEventListener('change', () => api('/api/player/volume', { value: Number(vol.value) }));
  $('#seek-bar').addEventListener('click', (e) => {
    const cur = SR.state && SR.state.player.current;
    if (!cur || !cur.duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    api('/api/player/seek', { value: ((e.clientX - rect.left) / rect.width) * cur.duration });
  });
  $('#unlock-btn').addEventListener('click', () => { unlocked = true; render(); });
  $('#unlock-local').addEventListener('click', () => { api('/api/player/mode', { mode: 'local' }); });
  document.addEventListener('keydown', (e) => {
    if (e.target.matches('input, textarea')) return;
    if (e.code === 'Space') { e.preventDefault(); unlocked = true; api('/api/player/toggle'); }
    if (e.code === 'ArrowRight' && e.shiftKey) api('/api/player/next');
  });

  fetch('/api/share').then((r) => r.json()).then(({ url }) => { $('#share-url').textContent = url.replace(/^https?:\/\//, ''); });

  SR.on('state', render);
  SR.connect('player');
  SR.startProgressLoop();
})();
