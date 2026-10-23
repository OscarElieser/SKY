# SKY: estado real de cada capacidad (v12.4)

Formato del prompt maestro §20. Cada capacidad tiene uno de estos estados:

- **Implementada y probada**: tiene pruebas automáticas que pasan; las de interfaz también se probaron en Chromium contra la API real.
- **Implementada sin validación completa**: el código existe y tiene pruebas con dobles, pero no se ejecutó en el equipo real (Windows, micrófono, Ollama, Piper, Home Assistant o cuentas reales).
- **Parcial**: cubre una parte de lo pedido.
- **Pendiente**: todavía no existe.
- **Bloqueada**: depende de permisos, cuentas o APIs que SKY no puede obtener sola.

Ninguna capacidad marcada «sin validación completa» debe presentarse como funcionando en tu PC hasta que la pruebes ahí.

## Arquitectura (§17), tal como existe hoy

| Pieza del prompt | Qué es en SKY | Archivos |
|---|---|---|
| SKY CORE | Reglas rápidas → atajos aprendidos → cerebro con herramientas (Ollama) → IA conversacional | `neural_core/sky_asistente_personal.py`, `sky_cerebro.py` |
| SKY API | FastAPI `:8765`, llave del dueño `X-SKY-KEY` + 2FA opcional | `metaverse/api.py`, `asistente_api.py`, `hud_api.py` |
| SKY MEMORY | SQLite local con memorias, documentos y conocimiento (FTS), más atajos y órdenes enseñadas | `neural_core/storage.py`, `sky_aprendizaje.py` |
| SKY AGENT | Agente local `127.0.0.1:8766` con token, política del dueño y registro verificable | `agente_dispositivo.py`, `neural_core/sky_capacidades.py` |
| SKY VOICE | HUD (dictado o faster-whisper local, Piper o voz del sistema) y manos libres con Vosk | `metaverse/static/hud.js`, `sky_tts.py`, `sky_manos_libres.py` |
| SKY CONNECT | Correo IMAP/SMTP, Home Assistant, WhatsApp por enlace, YouTube Data API | `sky_correo.py`, `sky_home_assistant.py`, `sky_contactos.py` |
| SKY AUTOMATION | Recordatorios, alarmas, rutinas con hora y temas que sigue | `sky_rutinas.py`, `_agenda_pump` en `metaverse/api.py` |
| SKY OBSERVABILITY | KPIs reales, detección de problemas, SLO y diagnóstico | `sky_metricas.py`, `sky_diagnostico.py` |
| SKY SECURITY | Llave del dueño, capacidades por herramienta, niveles de riesgo, parada de emergencia, confirmaciones | `sky_capacidades.py`, `security_v101.py`, `owner_mfa.py` |
| SKY UI | HUD holográfico con módulos en ventanas | `metaverse/static/hud.*` |

## Capacidades

| Área | Capacidad | Estado |
|---|---|---|
| Núcleo | Reglas rápidas en español (música, volumen, apps, web, archivos, ventanas, notas, agenda, correo, casa) | Implementada y probada |
| Núcleo | Cerebro con ~24 herramientas validadas: Ollama local o Claude, GPT, Gemini, Groq, DeepSeek y Mistral | Implementada sin validación completa (APIs simuladas con sus formatos oficiales) |
| Núcleo | Planificación de varias acciones encadenadas | Parcial: las skills encadenan pasos que vos definís (también por voz); el cerebro todavía elige **una** herramienta por mensaje |
| Perfil | `USER.md`: quién sos, herramientas, suscripciones; lo leen todos los cerebros | Implementada y probada |
| Skills | Carpeta de skills, 4 integradas, creación y ejecución por voz | Implementada y probada |
| Habilidades | Catálogo nativo: viajes, proyectos, casa, automonitoreo, seguridad, música, creación | Implementada y probada (APIs externas simuladas) |
| Skill Builder | Detección de necesidades, propuesta con IA, revisión estática, pruebas aisladas, aprobación con permisos, versiones | Implementada y probada (aislamiento por proceso; sin contenedor del SO) |
| Integraciones | Centro con vía, requisitos y estado real de 20 plataformas | Implementada y probada |
| Creación | Imágenes (OpenAI, Adobe Firefly), presentaciones (Gamma), letras de canciones | Implementada sin validación completa (APIs simuladas; requiere tus claves) |
| Creación | Canciones con audio (Suno) | **Bloqueada**: Suno no tiene API pública |
| Creación | Diseños en Canva | Pendiente (OAuth de Canva Connect) |
| Aprendizaje | Atajos aprendidos de acciones exitosas, corrección y caducidad | Implementada y probada |
| Aprendizaje | Órdenes enseñadas («cuando diga…») | Implementada y probada |
| Memoria | Datos personales: recordar, corregir, olvidar, exportar y borrar; se rechazan secretos | Implementada y probada |
| Memoria | Cinco niveles (§4) | Parcial: inmediata (historial), semántica (memorias y conocimiento) y procedimental (atajos y órdenes enseñadas). La episódica es el registro de acciones y KPIs, sin resumen. La memoria de largo plazo **entre dispositivos** está pendiente |
| Internet | Aprender sobre un tema (Wikipedia y noticias) con fuentes y fecha, guardado como datos | Implementada sin validación completa (red simulada) |
| Internet | Seguir temas con actualización diaria y aviso | Implementada sin validación completa |
| Investigación | Contrastar varias fuentes y señalar discrepancias (§10) | Pendiente |
| Equipo | Abrir apps, webs, carpetas y documentos; multimedia; volumen; ventanas; notas; capturas; portapapeles; escribir; bloquear | Implementada sin validación completa en Windows (probado con el agente real y efectos del sistema simulados) |
| Equipo | Buscar archivos por **contenido**, editar documentos de Office, ejecutar scripts | Pendiente; los scripts sólo se ejecutan con el Intérprete, en modo aparte y confirmando cada bloque |
| Voz | Escucha continua «SKY…», conversación, interrupción con Esc, respuesta por frases | Implementada sin validación completa (micrófono real sin probar) |
| Voz | Identificación del hablante | Pendiente |
| Agenda | Recordatorios, alarmas, rutinas, «buenos días» | Implementada y probada |
| Automatización | Tareas programadas por voz y en panel (activar, pausar, borrar) | Implementada y probada |
| Correo | Borradores de respuesta preparados por SKY, enviados sólo con tu aprobación | Implementada sin validación completa (IMAP y la IA simulados) |
| Calendario | Google Calendar y otros (OAuth) | Pendiente; requiere crear credenciales OAuth del dueño |
| Correo | Leer sin marcar y responder o enviar con confirmación (contraseña de aplicación) | Implementada sin validación completa (IMAP/SMTP simulados) |
| Drive, Contacts, GitHub, finanzas, salud | Centro de integraciones con OAuth | Pendiente |
| Mensajería | Hablarle a SKY por WhatsApp (API oficial de Meta): texto, notas de voz, confirmaciones con código, avisos | Implementada sin validación completa (Meta simulada; puente HTTP con firma probado). Requiere app de Meta y número Business |
| Mensajería | Mandarle WhatsApp a tus contactos | Abre el chat con el mensaje escrito y vos tocás Enviar. Enviar solo está **bloqueado**: no hay API oficial para cuentas personales |
| Casa | Home Assistant: luces, escenas, clima, cortinas y cerraduras con confirmación | Implementada sin validación completa |
| KPIs | Mediciones reales de API, asistente, acciones, voz, modelo y seguridad; SLO; detección; diagnóstico por voz; panel a pedido | Implementada y probada |
| KPIs | Tokens y costo de la IA en la nube, presupuesto mensual, cupo gratis de WhatsApp | Implementada y probada (el costo requiere que configures el precio por 1000 tokens) |
| Servicio | Arranque con Windows, sin suspensión, reinicio automático de servicios caídos | Implementada sin validación completa en Windows |
| Seguridad | Niveles de riesgo 1–3; el nivel 3 siempre se confirma | Implementada y probada |
| Seguridad | Parada de emergencia (voz o HUD); reanudar sólo con clic | Implementada y probada |
| Seguridad | Control de velocidad (rate limit) por ruta | Pendiente |
| Multidispositivo | Agentes remotos emparejados vía Tailscale con token por dispositivo | Implementada sin validación completa |
| Multidispositivo | App móvil nativa y sincronización de memoria | Pendiente |
| Evolución | Proponer habilidades nuevas, probarlas aisladas y versionarlas (§4) | Implementada y probada con el Skill Builder; SKY **no** modifica su núcleo ni sus controles |

## Próximas fases recomendadas

1. **Validar WhatsApp en tu cuenta de Meta** siguiendo `docs/guias/SKY_WHATSAPP.md`.
2. **Fase 5 (vida digital):** Google Calendar y Drive con OAuth y permisos mínimos, más un Centro de Integraciones con estado, historial y revocación.
3. **Fase 2 (núcleo):** plan de varias acciones encadenadas, con verificación entre pasos y recuperación de errores.
4. **Fase 3 (voz):** validar en tu PC el micrófono, Piper y faster-whisper, y medir la primera voz real con los KPIs.
5. **Seguridad:** límite de velocidad por ruta y por dispositivo.
6. **Fase 9:** sincronizar memoria y atajos entre tus equipos, cifrados, por Tailscale.
