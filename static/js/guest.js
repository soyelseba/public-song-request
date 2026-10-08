/* Vista de invitados: enviar peticiones y ver la cola. */
(() => {
  const $ = (s) => document.querySelector(s);
  const guestId = localStorage.sr_guest_id || (localStorage.sr_guest_id = SR.uid());
  let myIds = JSON.parse(localStorage.sr_my || '[]');

  const form = $('#request-form');
  const input = $('#q');
  const nameInput = $('#guest-name');
  const badge = $('#detect-badge');
  const btn = $('#submit-btn');
  nameInput.value = localStorage.sr_name || '';

  function updateBadge() {
    const p = SR.detectPlatform(input.value);
    badge.className = `detect ${p}`;
    badge.innerHTML = p === 'none' ? '' : `${SR.icon(SR.platformIcon(p))}${SR.platformLabel(p)}`;
  }
  input.addEventListener('input', updateBadge);

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = input.value.trim();
    if (query.length < 2) return;
    const label = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Enviando…';
    try {
      localStorage.sr_name = nameInput.value.trim();
      const res = await SR.api('/api/requests', { query, guest_name: nameInput.value.trim(), guest_id: guestId });
      myIds = [res.id, ...myIds].slice(0, 25);
      localStorage.sr_my = JSON.stringify(myIds);
      input.value = '';
      updateBadge();
      SR.toast('¡Petición enviada! El DJ la revisará pronto 🎧', 'success');
      render();
    } catch (err) {
      SR.toast(err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.innerHTML = label;
    }
  });

  function render() {
    const s = SR.state;
    if (!s) return;
    SR.renderNow();

    $('#closed-banner').classList.toggle('hidden', s.settings.requests_open);
    btn.disabled = !s.settings.requests_open;

    const byId = new Map(s.requests.map((r) => [r.id, r]));
    const mine = myIds.map((id) => byId.get(id)).filter(Boolean);
    $('#mine-count').textContent = mine.length;
    $('#mine-card').classList.toggle('hidden', mine.length === 0);
    SR.patch($('#mine-list'), mine.map((r) => SR.trackRow(r)).join(''));

    const queue = s.requests
      .filter((r) => ['approved', 'downloading', 'ready'].includes(r.status))
      .sort((a, b) => a.position - b.position);
    $('#queue-count').textContent = queue.length;
    SR.patch($('#queue-list'), queue.length
      ? queue.map((r, i) => SR.trackRow(r, { index: i + 1, showStatus: r.status !== 'ready' })).join('')
      : SR.emptyState('music', 'La cola está vacía. ¡Sé el primero en pedir algo!'));
  }

  SR.on('state', render);
  SR.connect('guest');
  SR.startProgressLoop();
  updateBadge();
})();
