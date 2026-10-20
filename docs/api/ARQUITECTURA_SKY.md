## Complemento SKY v8.0: Experience Engine / Office Studio

El motor documental de SKY se implementa en `neural_core/sky_office.py`, con
una interfaz propia en `/office` y rutas autenticadas en `metaverse/api.py`.
Esta ampliación **no sustituye** el metaverso social v7 ni sus bases de datos.

Flujo: usuario → especificación limitada → motor local Office → descarga DOCX,
PPTX, XLSX, PDF, CSV, Markdown o HTML. La ampliación mediante Gemini/OpenAI/
Claude/Ollama es opcional y seleccionada explícitamente.

La redacción con modelo externo no cambia la arquitectura de permisos del
servidor. La clave SKY controla la API privada. El creador Office del v8 es
del propietario; la incorporación de editores de documentos para cada cuenta
de comunidad requiere autenticación aislada, cuotas y políticas por proyecto.

Futuros pasos: almacenamiento versionado con permisos; coedición; importación
sin pérdida; inclusión de gráficos e imágenes; colaboración; reproducción de
diapositivas dentro de mundos 3D.

---

# Evolución SKY v7.0: comunidad social inmersiva

**Capas:** navegador HTML/CSS/JS WebGL → FastAPI HTTP/WS con usuarios e invitaciones → SQLite WAL (mundo / comunidad separados) → extensiones multi-IA y memoria explícita. Autenticación bearer por usuario y clave propietaria independiente. Los sockets difunden presencia y posiciones y guardan conversaciones. La voz usa señalización WebRTC, sin almacenar audio. Un solo worker mientras no exista broker Redis.

**Fundador de la visión:** Oscar Elieser Chamorro Guzmán. El expediente de concepción no equivale al registro jurídico de una marca.

---

# Arquitectura SKY v6.0

```text
SKY Universal Personal
 ├── Streamlit :8501 (memoria, modelos, voz, finanzas, BAQUEANO, fotos/3D)
 ├── SKY Engine API FastAPI :8765 (clave local, OpenAPI, /v1/chat/completions)
 │    ├── Metaverse Engine procedural (mundo -> escena JSON)
 │    ├── Base local SQLite (escenas versionadas)
 │    ├── Export GLB usando Trimesh y Studio 2.5D desde foto
 │    ├── Presencia virtual WebSocket con ticket temporal
 │    └── Chat / herramientas / metas -> módulos previos SKY
 ├── WebGL propio + Canvas2D de reserva (navegador, sin CDN)
 ├── WebXR (experimental y condicionado al visor/navegador/HTTPS)
 ├── Motores externos opcionales bajo clave (GPT/Gemini/Claude...)
 └── Ollama local opcional
```

SKY controla su **servidor, los permisos, sus datos, las escenas y las herramientas**. La API no concede capacidades ilimitadas por sí sola; las capacidades dependen de módulos efectivamente implementados, modelos instalados y permisos. Esta versión no ejecuta comandos arbitrarios ni transacciones financieras reales.

Ver [SKY_ENGINE_API.md](SKY_ENGINE_API.md) para rutas y prueba.

---

# Arquitectura de SKY Universal v5.0

## SKY como producto propio

No existe una forma legítima de extraer los pesos privados, datasets o mecanismos internos completos de OpenAI GPT, Anthropic Claude o Google Gemini para incrustarlos íntegramente en una aplicación privada. SKY **sí** puede poseer y ejecutar su propio motor de decisión, memoria, herramientas, interfaces, automatizaciones, visión 2.5D y modelos de pesos abiertos descargados por el usuario en Ollama. Para capacidades cerradas recurre a APIs con consentimiento y facturación del propietario de la cuenta.

```
           SKY — voz / chat / cámara / fotografías / web / proyectos
                                 │
                   ┌─────────────┴───────────────┐
                   │   NÚCLEO LOCAL DE SKY       │
                   │ herramientas + permisos     │
                   │ memoria + metas + feedback  │
                   └───────┬───────────────┬─────┘
                           │               │
        motores externos seleccionados     │ funciones internas
        Gemini / OpenAI / Claude           ├─ Studio 3D: PNG/GLB y ensamblaje
        Mistral / Groq / DeepSeek          ├─ Cálculos / objetivos / registros
        o modelo abierto Ollama local      ├─ MLP + GRU experimental
                                          ├─ BAQUEANO lectura/PR con revisión
                                          └─ Agentes autorizados de dispositivos
```

## Niveles de autonomía

- **A0**: leer documentos o memoria propia y responder.
- **A1**: ejecutar operaciones locales no sensibles explícitamente solicitadas, como aritmética y ensamblar GLB.
- **A2**: producir propuestas revisables (borradores, campañas, Pull Requests).
- **A3**: acciones autorizadas con confirmación específica: usar un agente emparejado.
- **A4**: acciones sensibles (pagos, producción, cuentas administrativas): requieren una integración dedicada, permisos mínimos, evidencia y confirmación. No implementadas como acciones universales.

El objetivo de SKY no es prometer capacidad sin límites. Su objetivo es ser un asistente confiable, ampliable y útil que distinga entre recomendaciones, simulaciones, operaciones realmente ejecutadas y tareas aún pendientes.

## Ruta técnica para visión 3D avanzada

**Funciona en v5.0:** cámara/foto, cajas, segmentación asistida GrabCut, piezas RGBA, extrusión 2.5D, malla coloreada, posicionamiento 3D, ZIP recuperable y exportación GLB.

**Fases posteriores:** segmentación de precisión con modelos locales (SAM2), inferencia de profundidad con modelos de código abierto, captura multivista, reconstrucción con COLMAP u otro motor de fotogrametría y edición CAD en Blender. Cada una requiere dependencias, aceleración o datos; ninguna está incorporada ni validada en v5.0.

## Protección del ecosistema BAQUEANO

No modificar el repositorio original por defecto. Conservar ramas, backups y revisión humana. Firebase, Supabase, Hostinger, Cloudflare y GitHub constituyen el stack previsto. Evitar desplegar secretos en frontend. Registro de cambios y revisiones antes de producción.

## SKY Live

Motor de estado de solo lectura para BAQUEANO, con latido persistente y consulta cada 30 minutos mientras esté activo en la computadora. No es disponibilidad 24/7 sin un dispositivo encendido. No instala un servicio ni envía notificaciones push.

## Evolución v9.6: coordinación contextual sin recargar la portada

`neural_core/sky_intelligent.py` conserva el planificador persistente de v9.5 e incorpora clasificación local ampliada, borradores por secciones y revisiones de propuestas/entregables guardadas en SQLite. `metaverse/intelligent_api.py` expone rutas privadas, y `sky-home.js` presenta los controles solo cuando un plan está pendiente o un trabajo se completó. Los artefactos se realizan con Workbench y se enlazan al Project Hub existente; no se sustituye el motor de mundos, documentos ni diseños.

La UI y el API administrativo de BAQUEANO continúan restringidos a la clave maestra. Ninguna revisión sobrescribe archivos ni despliega cambios.

## SKY v9.7 — Creative Studio & Reliability

`metaverse/creative_api.py` introduce rutas privadas que llaman a `neural_core/sky_creative.py` para almacenar medios por hash SHA-256 y preservar proyectos `image` y `video` independientes del resto del ecosistema. `sky_projects.py` reconoce vínculos `creative` y exporta sus recetas con versiones. `sky_backup.py` agrega opcionalmente la biblioteca completa a las copias locales. La página `metaverse/static/creative.html` es interna y está accesible desde **Espacios**, sin nuevos accesos principales.

La ruta de publicación de documentos y mundos y el control de BAQUEANO no cambian. Los renders se realizan en un worker local con una instantánea aprobada de receta; los procesos interrumpidos quedan a revisión conservadora para no modificar silenciosamente el resultado. El procesamiento creativo es local con Pillow y FFmpeg, salvo generación externa Gemini solicitada expresamente.

## SKY Global Intelligence v10.2 — arquitectura integrada

- `neural_core/sky_languages.py` negocia BCP-47 y pistas de escritura (no sustituye reconocimiento semántico). `neural_core/sky_global_ui.py` centraliza glosarios públicos con cobertura explícita.
- `metaverse/language_api.py` entrega catálogo y preferencias. `community_api.py` persiste el idioma de cada usuario comunitario por separado en SQLite.
- `metaverse/static/sky-global-i18n.js` aplica glosario estático en las páginas de SKY; el texto privado y los chats no se envían a traductores automáticamente. `sky-global-i18n.css` cubre RTL.
- `neural_core/sky_subtitles.py` y `metaverse/global_media_api.py` reutilizan los medios del Creative Studio para SRT/VTT, MP4 y narración bajo consentimiento.
- `metaverse/owner_mfa.py`, `security_api.py`, `deployment_v102.py` y `distributed_limits.py` refuerzan el acceso privado y bloquean arranques públicos incompletos. La verificación de autenticidad y cifrado del proxy y un WAF deben quedar fuera del proceso Python.
- El resto de los módulos y BAQUEANO no se sustituyen ni se modifican; BAQUEANO conserva acceso reservado al creador.
