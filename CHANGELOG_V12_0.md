# SKY IA v12.0 — Unificado: HUD + JARVIS + Asistente Personal

**Dirección conceptual:** Oscar Elieser Chamorro Guzmán.

Esta versión reúne en `main` todo lo que estaba separado: los 47 commits de la rama `feature/sky-windows-desktop-controller-media` (SKY JARVIS: control de escritorio, HUD holográfico, voz continua, notas, tareas), el Asistente Personal v11.1 y una interfaz nueva.

## Interfaz HUD (nueva pantalla principal: `http://127.0.0.1:8765/`)

- Núcleo holográfico animado que cambia de color y ritmo según el estado (en espera, escuchando, pensando, hablando, ejecutando, atención) y reacciona al nivel real del micrófono y de la voz de SKY.
- Conversación por voz: tocá el núcleo, el botón MIC, la barra espaciadora o F2. **CONV** activa la conversación continua: SKY vuelve a escucharte después de responder. Podés interrumpirlo hablándole o con Esc.
- Confirmaciones por voz: cuando una acción necesita permiso, SKY pregunta "¿Lo hago?" y acepta "sí / dale / confirmo" o "no / cancelá".
- Voz 100 % local: si instalás faster-whisper y su modelo (`SKY_STT_MODEL_DIR`), el HUD graba y transcribe en tu equipo. Si no, usa el dictado del navegador y lo indica ("puede usar la nube"). Para hablar elige siempre una voz del sistema marcada como local.
- Todos los módulos dentro del HUD como ventanas holográficas arrastrables, minimizables y ampliables, con barra de ventanas: Clásico (`/sky`), Creative, Office, Flujos, Metaverso, Studio 3D, Comunidad y el panel de negocio. El panel Streamlit (deportes, finanzas, visión) se abre aparte.
- Reproductor de YouTube interno con la API oficial (`YOUTUBE_API_KEY`), que obedece "ponelo en mini", "pantalla completa", "pausá el video", "siguiente" y demás.
- Paneles en vivo: CPU, RAM y batería; motor de IA y privacidad; permisos activos; Casa; tareas en segundo plano; pendientes de la voz manos libres; notas; **registro verificado** de acciones.
- Funciona en el celular (pestañas Sistema / Núcleo / Módulos). La interfaz clásica sigue en `/sky`, y `/asistente` redirige al HUD.

## Cerebro y privacidad

- **Modo 100 % local** con `SKY_LOCAL_ONLY=1`: el selector de proveedores sólo permite Ollama, en TODO SKY (chat, HUD, voz, Intérprete).
- Respuestas por voz breves y naturales; por escrito, el cerebro completo de SKY (documentos, memorias, evidencias).
- Intérprete combinado: el de JARVIS manda en reproductor, ventanas, notas, tareas, redes y carpetas de Windows/OneDrive; el del Asistente, en música por servicio (Spotify/YouTube/YouTube Music), volumen exacto, capturas, portapapeles, notificaciones y bloqueo.

## Casa y oficina: Home Assistant

- `SKY_HA_URL` + `SKY_HA_TOKEN`. Órdenes como "enciende la luz de la sala", "apaga las luces del cuarto", "activa la escena cine", "pon el aire a 22 grados", "abre el portón", "cierra la puerta principal". Accesos rápidos en el panel Casa.
- Sólo actúa sobre entidades que existen en tu Home Assistant (no le quita frases a la IA). Luces, enchufes, ventiladores, multimedia y escenas pueden ir sin clic (`SKY_HA_AUTO`); cerraduras, portones y cortinas, clima y scripts **siempre** piden confirmación. Ninguna cerradura se abre por voz. Las alarmas no se controlan.

## Intérprete de código (Open Interpreter)

- `python sky_interprete.py` u opción **I** del menú: SKY escribe y ejecuta código en tu PC (organizar archivos, convertir documentos, programar, administrar el sistema) con tu modelo local de Ollama por defecto. **Muestra cada bloque y espera tu "y"** antes de ejecutarlo. Es un modo aparte: la voz y el HUD no ejecutan código arbitrario.

## Agente del equipo v6.0 (fusión de los dos "v5")

- 16 capacidades: estado, webs, apps básicas, 30+ apps (verificadas en Windows), multimedia, volumen, reproducir, notificaciones, **tareas**, archivos y carpetas (con OneDrive), **ventanas**, **notas**, **escribir en la app activa**, capturas, portapapeles y bloqueo.
- Perfil por defecto: sólo lo de bajo riesgo (apps, música, volumen, webs, avisos, tareas). `--perfil completo` suma lo demás; ventanas, archivos, notas, escritura y portapapeles **siempre** piden confirmación.
- Las variables de JARVIS (`SKY_WINDOW_ACTIONS`, `SKY_ALL_CAPABILITIES`, `SKY_NOTES_ENABLED`) siguen autorizando.
- Registro verificable `/verify_action`, `/actions_history` y nuevo `/tasks`.

## Correcciones de errores encontrados al revisar la rama JARVIS

- **Permisos que no se aplicaban:** el agente anunciaba que ventanas, escritura y archivos dependían de `SKY_WINDOW_ACTIONS`/`SKY_ALL_CAPABILITIES`, pero los ejecutaba igual. Ahora se aplican siempre.
- **Éxitos simulados:** `player_control`, `voice_control` y `holographic_window` respondían "VERIFIED" sin hacer nada; ahora responden `status: UI` (los aplica la interfaz).
- **"Ya está abierta tu carpeta" sin abrirla** en macOS/Linux: ahora abre con el programa del sistema o informa el error.
- Búsqueda de documentos por nombre con `../`, separadores o comodines; ruta directa fuera de tu perfil. Ahora se rechazan, junto con los enlaces simbólicos.
- macOS: las apps `.app` se abren con `open` (antes se intentaban ejecutar como programa).
- **Supervisor:** cerraba cualquier proceso que ocupara los puertos 8765/8766, aunque no fuera de SKY. Ahora sólo reinicia instancias de SKY. Usaba `shell=True` para `netstat`/`taskkill`; ya no.
- **Inicio automático con Windows roto:** el acceso directo pasaba `--minimized`, que no existía.
- La voz manos libres no se cae con órdenes de control de voz o de interfaz (llegaban sin `params`).
- Los tests de carpetas especiales dependían de que existiera `~/Documents` real (fallaban en CI Linux).
- Reproductor: se deja de leer la página de resultados de YouTube por scraping. Sin `YOUTUBE_API_KEY`, la búsqueda se abre en tu navegador. El "catálogo verificado" (que ponía Queen ante cualquier frase con "música") no se usa en el HUD.
- Seguridad HTTP: los módulos sólo se pueden incrustar **dentro de SKY** (cabeceras `Sec-Fetch-*` que el navegador fija); en cualquier otro caso sigue `X-Frame-Options: DENY`. El permiso de YouTube aplica sólo a la página del HUD.
- Dependencias alineadas con la auditoría (`Pillow>=13`, `cryptography>=50`): la revisión "SKY security and global regression" falló en `main` por esto.

## Evidencia y límites

- Pruebas ejecutadas en esta revisión: 36 nuevas de v12, 52 del Asistente, 159 de las suites JARVIS y de dispositivos (`test_sky_devices`, `test_windows_desktop_control`, `test_sky_jarvis_fase1`, `test_sky_jarvis_local`, `test_sky_notes_local`, `test_multi_device_and_launcher`, `test_holographic_windows`): **todas aprobadas**. El entorno de desarrollo no permitía instalar las dependencias pesadas de la app completa (trimesh, torch); las pruebas de API se verificaron contra los routers reales con autenticación equivalente. **Confirmar el run de GitHub Actions** antes de declarar verde el pipeline completo.
- HUD probado en Chromium (1440 px y 390 px) contra el agente real con efectos del sistema simulados: sin errores de consola y sin desbordes horizontales.
- No se pudo probar en un Windows real: teclas multimedia, ventanas, apertura de apps y carpetas, micrófono y voces. Probalo en tu PC.
- Open Interpreter, faster-whisper, Ollama y Home Assistant no estaban disponibles en el entorno: su integración está probada con dobles de prueba.
- La transcripción local depende del modelo que instales; el dictado del navegador (Chrome/Edge) puede enviar audio a los servidores del navegador.
