# SKY Engine API v6.0 — Especificación de integración

**Base URL por defecto:** `http://127.0.0.1:8765` (solo equipo local). Documentación Swagger disponible en `/docs`.

**Autenticación:** enviar `X-SKY-KEY: <clave_privada>` en solicitudes `/api` y `/v1`. La clave se crea en `local_data/sky_api_token.txt` la primera vez que SKY API necesita autenticar una solicitud; también puede establecerse en `.env` como `SKY_API_KEY` con 24 o más caracteres. **No incluir la clave en apps públicas, repositorios o URLs.**

## Rutas funcionales

| Método | Ruta | Uso |
|---|---|---|
| GET | `/api/health` | Estado mínimo, público |
| GET | `/api/capabilities` | Capacidades realmente configuradas, solo propietario |
| GET | `/api/worlds` | Mundos del propietario |
| POST | `/api/worlds` | Crear mundo desde descripción y semilla |
| GET | `/api/worlds/{id}` | Recuperar escena JSON |
| PUT | `/api/worlds/{id}` | Guardar modificaciones, versión optimista |
| POST | `/api/worlds/{id}/generate` | Añadir o recrear por descripción |
| POST | `/api/worlds/{id}/objects` | Añadir pieza geométrica autorizada |
| DELETE | `/api/worlds/{id}` | Eliminar mundo (sin papelera) |
| GET | `/api/worlds/{id}/export.glb` | Descargar GLB editable |
| POST | `/api/studio/photo-to-glb` | Foto (JPG/PNG/WebP), máscara y extrusión 2.5D local |
| POST | `/api/chat` | Chat SKY local o con proveedor configurado |
| POST | `/api/tools/run` | Ejecutar herramienta permitida (cálculo, metas, hora) |
| GET | `/api/evolution` | Estado de objetivos, mejoras y evaluaciones |
| POST | `/api/ws-ticket` | Solicitar pase temporal, válido una vez por 35 segundos |
| WS | `/api/ws/{id}?ticket=...` | Presencia/posición/chat de sala, mismo proceso |
| GET | `/v1/models` | Lista de IDs de modelos compatibles |
| POST | `/v1/chat/completions` | Subconjunto compatible con cliente OpenAI, sin streaming |

### Crear un mundo

```bash
# No pegues una clave real en mensajes ni repositorios.
export SKY_TOKEN="$(cat local_data/sky_api_token.txt)"
curl -X POST http://127.0.0.1:8765/api/worlds \
  -H "X-SKY-KEY: $SKY_TOKEN" -H 'Content-Type: application/json' \
  --data '{"name":"Mi ciudad","prompt":"Ciudad futurista con edificios y negocios","seed":25}'
```

### Consumir SKY desde Python, en el mismo equipo

```python
from pathlib import Path
import httpx
key = Path('local_data/sky_api_token.txt').read_text().strip()
res = httpx.post('http://127.0.0.1:8765/v1/chat/completions',
    headers={'X-SKY-KEY':key}, json={
        'model':'local',
        'messages':[{'role':'user','content':'/sky calcula 150*3'}]},timeout=30)
res.raise_for_status()
print(res.json()['choices'][0]['message']['content'])
```

## Privacidad y despliegue

- El servidor inicia solo en `127.0.0.1` y almacena datos en SQLite `local_data/sky_metaverse.sqlite3`. No es un SaaS remoto ni un servidor público.
- Para celular o un dispositivo remoto, realizar configuración adicional con autenticación, Tailscale Serve y HTTPS. No publicar el puerto 8765 ni el token de propietario en Internet. Para múltiples usuarios reales, implementar identidades por usuario, cuentas y roles, más límites de consumo.
- WebSocket con ticket de un uso; sus mensajes y presencia son efímeros, no un metaverso masivo ni persistente entre servidores.
- Las modificaciones de escenas utilizan control de versiones. Ante `HTTP 409`, recargar antes de guardar.
- La API es **de SKY** pero las respuestas libres de modelos externos todavía requieren cuentas y acceso; Ollama puede funcionar localmente con un modelo descargado. Crear un servidor API no crea por sí solo un modelo general sin conexión o sin costes.
- WebGL básico corre dentro del navegador, sin CDN. VR experimental usa WebXR si existe visor compatible y HTTPS en dispositivos remotos. Si no hay WebGL, SKY dibuja una vista de reserva con proyección en Canvas 2D.
- Los objetos `box`, `sphere`, `cylinder`, `cone`, `tree`, `house`, `palm`, `torus`, `rock`, `tower`, `platform` son geometrías proceduralmente generadas. No incluye generación física de terrenos reales, multijugador masivo, modelado 3D fotorrealista automático, vídeo/cine, juegos en red persistentes ni una IA consciente.
- `POST /api/studio/photo-to-glb` produce una **extrusión 2.5D** guiada por caja normalizada, con 12 MB de límite y procesamiento local. No reconstruye los lados ocultos de una sola foto.
