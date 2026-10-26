# -*- coding: utf-8 -*-
"""Corrección reversible del HUD de SKY: saludo inmediato + timeout de streaming.
Ejecutar desde la carpeta SKY con su Python del entorno virtual.
No toca modelos, credenciales, .env, permisos ni servicios.
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "neural_core" / "sky_asistente_personal.py"
HUD = ROOT / "metaverse" / "static" / "hud.js"

SALUDO_ANTES = """    if stop:
        return stop
    try:
        from . import sentinel_estado"""
SALUDO_DESPUES = """    if stop:
        return stop
    # SKY-SALUDO-INMEDIATO: no cargar Ollama para una bienvenida simple.
    # La parada de emergencia sigue evaluándose antes de este atajo.
    saludo = re.sub(r'[\\s,;:.!¡?¿]+', ' ', _norm(texto)).strip()
    if saludo in {'hola sky', 'sky hola', 'hola', 'buenas sky', 'buenas',
                  'buenos dias sky', 'buenas tardes sky', 'buenas noches sky'}:
        return {'tipo': 'respuesta', 'mensaje': 'Hola, te escucho. ¿Qué necesitás?',
                'proveedor': 'sky-local'}
    try:
        from . import sentinel_estado"""

STREAM_FUNCTION = r'''  async function enviarStream(texto) {
    // SKY-STREAM-TIMEOUT: no dejar el HUD en PROCESANDO indefinidamente.
    const control = new AbortController();
    let finalizado = false;
    const aviso = setTimeout(() => {
      if (!finalizado && estado === 'thinking') setState('thinking', 'Ollama sigue procesando la respuesta…');
    }, 12000);
    const limite = setTimeout(() => control.abort(), 90000);
    let acumulado = '', pendiente = '', resto = '', vivo = null;
    const soltarFrases = (forzar) => {
      const m = pendiente.match(/^[\s\S]*[.!?…:;](?=\s|$)/);
      if (m && m[0].trim().length > 2) { encolar(limpiarParaVoz(m[0])); pendiente = pendiente.slice(m[0].length); }
      if (forzar && pendiente.trim()) { encolar(limpiarParaVoz(pendiente)); pendiente = ''; }
    };
    try {
      const r = await fetch('/api/asistente/stream', {
        method: 'POST', headers: headers(), signal: control.signal,
        body: JSON.stringify({ texto, historial: S.historial.slice(-12), modo: 'voz', dispositivo: 'local' })
      });
      if (!r.ok || !r.body) throw new Error('HTTP ' + r.status);
      S.historial.push({ role: 'user', content: texto });
      const lector = r.body.getReader(), dec = new TextDecoder();
      for (;;) {
        const { value, done } = await lector.read();
        if (done) break;
        resto += dec.decode(value, { stream: true });
        let nl;
        while ((nl = resto.indexOf('\n')) >= 0) {
          const linea = resto.slice(0, nl).trim(); resto = resto.slice(nl + 1);
          if (!linea) continue;
          let ev; try { ev = JSON.parse(linea); } catch { continue; }
          if (ev.delta) {
            if (!vivo) vivo = addMsg('sky', '', 'live');
            acumulado += ev.delta; pendiente += ev.delta; vivo.textContent = acumulado; scroll();
            soltarFrases(false);
          }
          if (ev.final) {
            finalizado = true;
            if (vivo) vivo.classList.remove('live');
            if (ev.final.transmitido) {
              soltarFrases(true);
              const msg = ev.final.mensaje || acumulado;
              if (vivo) vivo.textContent = msg; else addMsg('sky', msg);
              if (!acumulado && msg) encolar(limpiarParaVoz(msg));
              S.lastSky = msg;
              S.historial.push({ role: 'assistant', content: msg.slice(0, 4000) });
              await speak(''); seguirConversacion();
              if (!S.speaking) setState('idle', 'Listo.');
            } else {
              if (vivo && !acumulado.trim()) vivo.remove();
              await responder(ev.final, 'voz');
            }
            return;
          }
        }
      }
      throw new Error('La conexión terminó sin una respuesta final.');
    } catch (e) {
      if (vivo) vivo.classList.remove('live');
      const mensaje = control.signal.aborted
        ? 'Ollama tardó más de 90 segundos. Probá otra vez o revisá su uso de memoria con ollama ps.'
        : 'SKY no completó la respuesta: ' + e.message;
      addMsg('sky', mensaje, 'err');
      setState('error', 'No se completó la respuesta');
    } finally {
      clearTimeout(aviso);
      clearTimeout(limite);
    }
  }
'''


def parchear():
    if not (BACKEND.is_file() and HUD.is_file()):
        raise SystemExit("[ERROR] Guardá este archivo directamente en la carpeta raíz SKY, al lado de SKY_INICIAR.bat")
    backend = BACKEND.read_text(encoding="utf-8")
    hud = HUD.read_text(encoding="utf-8")
    changes: list[tuple[Path, str, str]] = []
    if "SKY-SALUDO-INMEDIATO" not in backend:
        if backend.count(SALUDO_ANTES) != 1:
            raise SystemExit("[ERROR] El código de sky_asistente_personal.py no coincide; no se modificó nada.")
        nuevo = backend.replace(SALUDO_ANTES, SALUDO_DESPUES, 1)
        compile(nuevo, str(BACKEND), "exec")
        changes.append((BACKEND, backend, nuevo))
    if "SKY-STREAM-TIMEOUT" not in hud:
        begin = "  async function enviarStream(texto) {\n"
        end = "  async function decir(texto, extra) {\n"
        if hud.count(begin) != 1 or hud.count(end) != 1:
            raise SystemExit("[ERROR] El código de hud.js no coincide; no se modificó nada.")
        before, rest = hud.split(begin, 1)
        original, after = rest.split(end, 1)
        required = ["/api/asistente/stream", "r.body.getReader()", "soltarFrases(true)", "await responder(ev.final, 'voz')"]
        if not all(s in original for s in required):
            raise SystemExit("[ERROR] El flujo de hud.js cambió; no se modificó nada.")
        new_hud = before + STREAM_FUNCTION + end + after
        changes.append((HUD, hud, new_hud))
    if not changes:
        print("[OK] Ambos cambios ya estaban aplicados. Sin acciones.")
        return
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Save all backups before making *any* changes.
    for path, old, _ in changes:
        backup = path.with_name(path.name + ".respaldo_" + stamp)
        backup.write_text(old, encoding="utf-8")
        print("Respaldo:", backup.relative_to(ROOT))
    for path, _, updated in changes:
        temp = path.with_name(path.name + ".sky_nuevo")
        temp.write_text(updated, encoding="utf-8")
        os.replace(temp, path)
        print("Actualizado:", path.relative_to(ROOT))
    print("\n[OK] Reiniciá SKY (opción 0) y actualizá Chrome con Ctrl+Shift+R.")
    print("No modifica archivos .env, modelos ni permisos.")


if __name__ == "__main__":
    parchear()
