/* SKY v11.1 — panel del Asistente Personal. Sin dependencias externas. */
(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const chat = $('chat'), input = $('input'), form = $('composer'), mic = $('mic');
  const deviceSel = $('device-select'), deviceState = $('device-state');
  const history = [];
  let ownerKey = '';
  let help = null;

  const store = {
    get(k) { try { return sessionStorage.getItem(k) || ''; } catch { return ''; } },
    set(k, v) { try { sessionStorage.setItem(k, v); } catch { /* modo privado */ } },
  };

  function el(tag, cls, text) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }

  function headers(extra = {}) {
    const h = { 'X-SKY-KEY': ownerKey, 'Content-Type': 'application/json', ...extra };
    if (window.SKYOwnerAuth) Object.assign(h, window.SKYOwnerAuth.headers());
    const dev = deviceSel.value;
    if (dev && dev !== 'local') {
      let tok = store.get('sky-device-token:' + dev);
      if (!tok) {
        tok = (prompt('Token del dispositivo "' + dev + '" (se guarda sólo en esta pestaña):') || '').trim();
        if (tok) store.set('sky-device-token:' + dev, tok);
      }
      if (tok) h['X-SKY-DEVICE-TOKEN'] = tok;
    }
    return h;
  }

  async function api(path, opts = {}) {
    const r = await fetch(path, { ...opts, headers: headers(opts.headers) });
    let data = {};
    try { data = await r.json(); } catch { /* respuesta vacía */ }
    if (!r.ok) throw new Error(typeof data.detail === 'string' ? data.detail : ('Error HTTP ' + r.status));
    return data;
  }

  function scroll() { chat.scrollTop = chat.scrollHeight; }
  function hideWelcome() { const w = $('welcome'); if (w) w.remove(); }

  function say(text) {
    if (!$('tts').checked || !('speechSynthesis' in window)) return;
    const u = new SpeechSynthesisUtterance(String(text).slice(0, 600));
    u.lang = 'es-419';
    speechSynthesis.cancel(); speechSynthesis.speak(u);
  }

  function addMsg(role, text, extraCls = '') {
    hideWelcome();
    const m = el('div', 'msg ' + role + (extraCls ? ' ' + extraCls : ''), text);
    chat.appendChild(m); scroll();
    return m;
  }

  function renderResult(box, res) {
    const ok = res && res.ok !== false;
    const line = el('div', 'result' + (ok ? '' : ' bad'), (ok ? '✓ ' : '✗ ') + (res.message || (ok ? 'Hecho.' : res.error || 'Error')));
    box.appendChild(line);
    if (Array.isArray(res.elementos)) {
      const pre = el('pre', '', res.elementos.map(e => (e.carpeta ? '📁 ' : '📄 ') + e.nombre).join('\n') || '(vacía)');
      box.appendChild(pre);
    } else if (typeof res.text === 'string') {
      box.appendChild(el('pre', '', res.text || '(portapapeles vacío)'));
    } else if (res.device) {
      const s = res.system || {};
      const parts = [res.device + ' · ' + res.platform + ' ' + (res.system_version || ''),
        'Perfil: ' + res.profile + ' · Agente ' + (res.agent_version || '')];
      if (s.bateria_percent !== undefined) parts.push('Batería: ' + s.bateria_percent + '%' + (s.cargando ? ' (cargando)' : ''));
      if (s.cpu_percent !== undefined) parts.push('CPU: ' + s.cpu_percent + '% · RAM: ' + s.memoria_percent + '%');
      box.appendChild(el('pre', '', parts.join('\n')));
    } else if (res.archivo) {
      box.appendChild(el('pre', '', res.archivo));
    }
    scroll();
    say(res.message || '');
  }

  function addAction(data) {
    hideWelcome();
    const p = data.propuesta;
    const box = el('div', 'action');
    box.appendChild(el('div', 'title', '⚡ ' + p.description));
    box.appendChild(el('div', 'sub', 'Acción: ' + p.action + (deviceSel.value !== 'local' ? ' · ' + deviceSel.value : ' · este equipo')));
    chat.appendChild(box);
    if (data.ejecucion) { renderResult(box, data.ejecucion); return; }
    if (data.aviso) { box.appendChild(el('div', 'note', data.aviso)); scroll(); return; }
    const btns = el('div', 'btns');
    const yes = el('button', 'btn primary', 'Ejecutar'); yes.type = 'button';
    const no = el('button', 'btn', 'Cancelar'); no.type = 'button';
    btns.append(yes, no); box.appendChild(btns); scroll();
    yes.addEventListener('click', async () => {
      yes.disabled = no.disabled = true;
      try {
        const res = await api('/api/asistente/ejecutar', { method: 'POST',
          body: JSON.stringify({ action: p.action, params: p.params, dispositivo: deviceSel.value }) });
        renderResult(box, res);
      } catch (e) { renderResult(box, { ok: false, error: e.message }); }
      btns.remove();
    });
    no.addEventListener('click', () => { btns.remove(); box.appendChild(el('div', 'sub', 'Cancelado.')); });
  }

  async function send(text) {
    text = String(text || '').trim();
    if (!text) return;
    addMsg('user', text);
    input.value = '';
    const thinking = addMsg('sky', '…');
    try {
      const data = await api('/api/asistente/mensaje', { method: 'POST', body: JSON.stringify({
        texto: text, historial: history.slice(-12), dispositivo: deviceSel.value }) });
      thinking.remove();
      if (data.tipo === 'accion') {
        addAction(data);
      } else {
        addMsg('sky', data.mensaje || '', data.tipo === 'error' ? 'error' : '');
        if (data.tipo !== 'error') say(data.mensaje);
      }
      history.push({ role: 'user', content: text });
      history.push({ role: 'assistant', content: data.mensaje || (data.propuesta && data.propuesta.description) || '' });
    } catch (e) {
      thinking.textContent = 'No pude contactar a SKY: ' + e.message;
      thinking.classList.add('error');
    }
  }

  async function loadDevice() {
    deviceState.textContent = 'conectando…'; deviceState.className = 'pill';
    const list = $('caps');
    try {
      const st = await api('/api/asistente/dispositivo?dispositivo=' + encodeURIComponent(deviceSel.value));
      deviceState.textContent = (st.device || 'equipo') + ' · ' + (st.profile || '');
      deviceState.className = 'pill ok';
      list.textContent = '';
      (help ? help.capacidades : []).forEach(c => {
        const on = (st.enabled || []).includes(c.id);
        const li = el('li', on ? '' : 'off');
        li.appendChild(el('span', '', c.nombre));
        li.appendChild(el('span', 'tag', on ? ((st.auto_confirm || []).includes(c.id) ? 'auto' : 'activa') : 'apagada'));
        li.title = c.descripcion;
        list.appendChild(li);
      });
    } catch (e) {
      deviceState.textContent = 'agente apagado'; deviceState.className = 'pill bad';
      list.textContent = '';
      list.appendChild(el('li', 'muted', e.message));
    }
  }

  async function loadVoice() {
    const ul = $('voice');
    try {
      const data = await api('/api/asistente/voz');
      ul.textContent = '';
      if (!data.pendientes.length) { ul.appendChild(el('li', 'muted', 'Sin pendientes.')); return; }
      data.pendientes.slice().reverse().forEach(item => {
        const li = el('li');
        li.appendChild(el('div', '', '“' + item.text + '”'));
        li.appendChild(el('div', 'muted', item.description || item.action));
        const btns = el('div', 'btns');
        const run = el('button', 'btn primary', 'Ejecutar'); run.type = 'button';
        const drop = el('button', 'btn', 'Descartar'); drop.type = 'button';
        run.addEventListener('click', async () => {
          try {
            const res = await api('/api/asistente/ejecutar', { method: 'POST',
              body: JSON.stringify({ action: item.action, params: item.params, dispositivo: deviceSel.value }) });
            addMsg('sky', '🎙️ ' + (res.message || 'Hecho.'));
          } catch (e) { addMsg('sky', e.message, 'error'); }
          await api('/api/asistente/voz/' + encodeURIComponent(item.id), { method: 'DELETE' }).catch(() => {});
          loadVoice();
        });
        drop.addEventListener('click', async () => {
          await api('/api/asistente/voz/' + encodeURIComponent(item.id), { method: 'DELETE' }).catch(() => {});
          loadVoice();
        });
        btns.append(run, drop); li.appendChild(btns); ul.appendChild(li);
      });
    } catch { /* sin acceso todavía */ }
  }

  function setupMic() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { mic.title = 'Tu navegador no soporta dictado por voz (usá Chrome o Edge)'; mic.disabled = true; return; }
    const rec = new SR();
    rec.lang = 'es-419'; rec.interimResults = true; rec.maxAlternatives = 1;
    let active = false;
    const orb = document.querySelector('.orb');
    rec.onresult = (ev) => {
      let txt = '';
      for (const r of ev.results) txt += r[0].transcript;
      input.value = txt;
      if (ev.results[ev.results.length - 1].isFinal) send(txt);
    };
    rec.onend = () => { active = false; mic.classList.remove('on'); orb.classList.remove('listening'); };
    rec.onerror = () => rec.onend();
    mic.addEventListener('click', () => {
      if (active) { rec.stop(); return; }
      try { rec.start(); active = true; mic.classList.add('on'); orb.classList.add('listening'); } catch { /* ya activo */ }
    });
  }

  async function init() {
    try {
      const b = await (await fetch('/api/client/bootstrap')).json();
      ownerKey = b.key || store.get('sky-owner-key');
    } catch { ownerKey = store.get('sky-owner-key'); }
    if (!ownerKey) {
      ownerKey = (prompt('Llave del dueño (X-SKY-KEY):') || '').trim();
      if (ownerKey) store.set('sky-owner-key', ownerKey);
    }
    try {
      help = await api('/api/asistente/ayuda');
      deviceSel.textContent = '';
      help.dispositivos.forEach(d => {
        const o = el('option', '', d.name === 'local' ? 'Este equipo' : d.name); o.value = d.name;
        deviceSel.appendChild(o);
      });
      const chips = $('chips');
      help.ejemplos.forEach(g => g.frases.slice(0, 2).forEach(f => {
        const c = el('button', 'chip', f); c.type = 'button';
        c.addEventListener('click', () => send(f));
        chips.appendChild(c);
      }));
    } catch (e) { addMsg('sky', 'No pude autenticarme con SKY: ' + e.message, 'error'); }
    loadDevice(); loadVoice();
    setInterval(loadVoice, 15000);
  }

  form.addEventListener('submit', (e) => { e.preventDefault(); send(input.value); });
  deviceSel.addEventListener('change', loadDevice);
  setupMic();
  init();
})();
