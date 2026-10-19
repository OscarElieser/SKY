# SKY Creative API · contrato v9.7

La API de SKY sigue siendo `FastAPI`; estas rutas son **privadas** y requieren cabecera `X-SKY-KEY`. No se incorpora ninguna API secreta nueva ni se publica el servidor en Internet.

| Método | Endpoint | Función |
|---|---|---|
| GET | `/creative` | Interfaz del Estudio creativo |
| GET | `/api/creative/capabilities` | Capacidades locales e instaladas |
| POST | `/api/creative/assets` | Subir un medio validado (`multipart/form-data`, campo `file`) |
| GET | `/api/creative/assets` | Biblioteca privada |
| GET | `/api/creative/assets/{id}/download` | Descargar archivo original/exportado |
| GET | `/api/creative/assets/{id}/preview` | Vista previa protegida |
| POST | `/api/creative/generate-image` | Generar imagen con Gemini bajo solicitud explícita |
| POST | `/api/creative/projects` | Crear proyecto de imagen o video con receta JSON |
| GET | `/api/creative/projects` | Listar proyectos creativos |
| GET / PUT | `/api/creative/projects/{id}` | Leer / actualizar proyecto con `expected_version` |
| GET | `/api/creative/projects/{id}/versions` | Historial de recetas editables |
| POST | `/api/creative/projects/{id}/command` | Edición local por instrucción admitida, control de versión |
| POST | `/api/creative/projects/{id}/image/render?format=png` | Render PNG/JPG/WEBP a biblioteca |
| POST | `/api/creative/projects/{id}/video/render` | Poner MP4 en cola (instantánea inmutable de la receta) |
| GET | `/api/creative/projects/{id}/exports` | Historial de entregables |
| GET | `/api/creative/jobs` y `/api/creative/jobs/{id}` | Estado y progreso de renders |
| POST | `/api/creative/jobs/{id}/cancel` | Cancelar tarea **en cola** |
| POST | `/api/creative/jobs/{id}/retry` | Reintentar tarea fallida o interrumpida |
| GET | `/api/creative/projects/{id}/portable` | Descargar `.skyzip` con medios y receta |
| POST | `/api/creative/portable` | Importar `.skyzip` validado |

### Ejemplo

```bash
curl -H "X-SKY-KEY: TU_CLAVE_PRIVADA" \
  -F "file=@foto.png" http://127.0.0.1:8765/api/creative/assets
```

Una imagen editable admite capas `image`, `text`, `rectangle` y `adjustments` (brillo, contraste, saturación, nitidez y desenfoque). Un video editable contiene `clips` con `asset_id`, `start`, `end`, `speed` y `caption`, y música opcional mediante `music_asset_id` y `music_volume`.

**Política de privacidad:** los medios **no se transmiten a proveedores externos** para editar/exportar. La única excepción es la acción explícita `/generate-image` que solicita una imagen a Gemini desde la descripción indicada. La compatibilidad con fuentes de imágenes de terceros queda sujeta a sus condiciones de licencia y derechos.

## v9.9 — Fotogramas múltiples y selección guiada

La API de creación de video acepta por clip `caption_keyframes` (lista de 2 a 16 objetos `{t,x,y}` en segundos efectivos y píxeles) y `caption_easing` (`linear` o `smooth`). La alternativa heredada `caption_motion` continúa funcionando. El render siempre usa la receta congelada cuando se aprueba, sin sobrescribir proyectos.

`POST /api/creative/assets/{id}/selection` puede recibir, además del rectángulo, `foreground:[[x,y],...]`, `background:[[x,y],...]` y `brush_radius:4` (1–20). Los puntos no son órdenes de reconstrucción semántica: guían GrabCut, sujeto a contraste e iluminación.


## SKY v10.0 — Tracking, capas y previsualización

- `POST /api/creative/assets/{aid}/track`: seguimiento local del área `[x,y,w,h]` sobre video; `start`, `end`, `step`, `width`, `height`, `speed`. Devuelve `keyframes` con confianza por muestra. Exige clave privada.
- Los clips de video admiten `overlays: [{asset_id,width,x,y,opacity,from,to,keyframes:[{t,x,y,confidence}]}]` (hasta 8 capas). Se guardan en versiones y paquetes `.skyzip`.
- `GET /api/creative/projects/{pid}/video/frame?t=1.0`: PNG extraído del último render MP4 **de la misma versión del proyecto**; responde 409 si aún no está exportada. Requiere clave privada.
- `POST /api/creative/gemini/check`: verificación real de Gemini bajo solicitud de propietario, consume cuota; sin clave responde 503.
- Edición local en español: `mueve capa 1 del clip 1 a x 50 y 40` / `opacidad capa 1 del clip 1 a 0.6`.

Limitaciones: seguimiento aproximado por plantilla, no identificación semántica ni generación de largometrajes.

## SKY v10.2 — Subtítulos y narración multilingües

Los módulos creativos pueden exportar WebVTT Unicode o quemar subtítulos SRT sobre un video MP4 local, usando únicamente la biblioteca privada del creador. El nuevo apartado en el editor es plegable. La narración MP3 con gTTS requiere consentimiento expreso. Rutas, tipos y limitaciones: [SKY_GLOBAL_API.md](SKY_GLOBAL_API.md).
