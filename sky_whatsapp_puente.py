"""SKY v12.3 — Puente de WhatsApp: el ÚNICO servicio de SKY pensado para recibir tráfico de internet.

Escucha en 127.0.0.1:8770 y sólo tiene dos rutas:
    GET  /whatsapp/webhook   verificación de Meta (hub.challenge)
    POST /whatsapp/webhook   mensajes, con firma X-Hub-Signature-256 obligatoria
    GET  /salud              {"ok": true}
La API principal de SKY (8765) y el agente del equipo (8766) siguen sin exponerse.

Publicarlo (elegí uno):
    tailscale funnel --bg 8770          → https://TU-PC.TU-RED.ts.net/whatsapp/webhook
    cloudflared tunnel --url http://127.0.0.1:8770
Guía completa: docs/guias/SKY_WHATSAPP.md

Uso:  python sky_whatsapp_puente.py [--puerto 8770] [--probar "mensaje"]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))


def _cargar_env() -> None:
    env = RAIZ / '.env'
    if not env.exists():
        return
    for linea in env.read_text(encoding='utf-8', errors='ignore').splitlines():
        linea = linea.strip()
        if linea and not linea.startswith('#') and '=' in linea:
            k, v = linea.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_cargar_env()
from neural_core import sky_whatsapp as wa  # noqa: E402

MAX_CUERPO = 1_000_000


class Puente(BaseHTTPRequestHandler):
    server_version = 'SKY-WhatsApp'
    sys_version = ''

    def log_message(self, fmt, *args):  # sin contenidos ni números en los registros
        return

    def _responder(self, codigo: int, cuerpo: bytes = b'', tipo: str = 'text/plain; charset=utf-8') -> None:
        self.send_response(codigo)
        self.send_header('Content-Type', tipo)
        self.send_header('Content-Length', str(len(cuerpo)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        if cuerpo:
            self.wfile.write(cuerpo)

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == '/salud':
            return self._responder(200, b'{"ok": true}', 'application/json')
        if url.path != '/whatsapp/webhook':
            return self._responder(404)
        q = parse_qs(url.query)
        desafio = wa.verificar_suscripcion(q.get('hub.mode', [''])[0], q.get('hub.verify_token', [''])[0],
                                           q.get('hub.challenge', [''])[0])
        return self._responder(200, desafio.encode()) if desafio else self._responder(403)

    def do_POST(self):
        if urlsplit(self.path).path != '/whatsapp/webhook':
            return self._responder(404)
        try:
            largo = int(self.headers.get('Content-Length') or 0)
        except ValueError:
            return self._responder(400)
        if largo <= 0 or largo > MAX_CUERPO:
            return self._responder(413)
        cuerpo = self.rfile.read(largo)
        if not wa.firma_valida(cuerpo, self.headers.get('X-Hub-Signature-256', '')):
            from neural_core import sky_metricas
            sky_metricas.registrar('servicio', 'whatsapp_firma', False, detalle='firma inválida')
            return self._responder(401)
        try:
            payload = json.loads(cuerpo)
        except ValueError:
            return self._responder(400)
        # Meta exige respuesta rápida: se confirma ya y se procesa en segundo plano.
        self._responder(200, b'OK')
        threading.Thread(target=wa.procesar, args=(payload,), daemon=True).start()

    def do_PUT(self):
        self._responder(405)

    do_DELETE = do_PATCH = do_PUT


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--puerto', type=int, default=int(os.getenv('SKY_WA_PORT', '8770')))
    ap.add_argument('--probar', help='Procesa este texto como si lo hubieras mandado por WhatsApp e imprime la respuesta')
    a = ap.parse_args()
    if a.probar:
        print(wa.atender_texto(a.probar))
        return 0
    e = wa.estado()
    if not e['configurado']:
        print('Falta configurar en .env: ' + ', '.join(e['faltan'] or ['SKY_WA_OWNER válido / SKY_WA_PHONE_ID numérico']))
        print('Guía: docs/guias/SKY_WHATSAPP.md')
        return 2
    srv = ThreadingHTTPServer(('127.0.0.1', a.puerto), Puente)
    print(f'SKY · puente de WhatsApp en http://127.0.0.1:{a.puerto}/whatsapp/webhook (dueño {e["dueno"]})')
    print(f'Publicalo con: tailscale funnel --bg {a.puerto}')
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
