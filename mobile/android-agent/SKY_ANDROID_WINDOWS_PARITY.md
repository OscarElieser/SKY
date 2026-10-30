# SKY IA · Hoja de interoperabilidad Windows / Android

Fecha: 2026-10-30. Alcance de esta entrega: **solo SKY Android**. No tocar el código de Windows ni BAQUEANO.

## Principio de diseño
Una sola identidad conversacional SKY, con capacidades específicas por plataforma y autorización supervisada. Los resultados se anuncian como reales únicamente tras confirmación de la herramienta. La interfaz principal es voz/texto, no un catálogo de botones.

## Capacidades verificadas en el repositorio

| Función | Base de SKY Windows (código existente) | SKY Android (código existente) | Estado |
|---|---|---|---|
| Selección y respaldo de modelos IA | `neural_core/sky_ai_auction.py` | `SkyPhoneCloud.kt`, `SkyGroqCloud.kt`, `SkyGeminiModes.kt` | Conectores distintos; falta unificar métricas y rutas |
| Word, Excel, PowerPoint | `neural_core/sky_office.py`, `sky_word_editor.py` | `SkyNativeWord.kt`, `SkyNativeExcel.kt`, `SkyNativePowerPoint.kt` | Exportación nativa disponible; faltan plantillas premium y edición verificable en apps |
| Investigación académica | `neural_core/sky_research_connectors.py` | `SkyAcademicResearch.kt` (Semantic Scholar) | Nueva búsqueda de metadatos con fuentes; no garantiza revisión por pares |
| Consulta web factual | `neural_core/sky_research_connectors.py`, `sky_web_learning.py` | Gemini con grounding, Open-Meteo y `SkyPublicResearch.kt` (Wikipedia) | Capacidad parcial; faltan noticias y fuentes generales gratuitas confiables |
| Memoria personal | SKY Windows `USER.md` y memoria | `SkyOwnerContext.kt`, `SkyLongTermMemory.kt`, `SkyOwnerIdentity.kt` | Importación voluntaria; identidad y hechos con autorización, sin sincronización automática |
| Subagentes y orquestación | `sky_subagents.py`, `sky_unified_agents.py` | `SkyAndroidCognition.kt`, router local | Clasificador local, no orquestador pleno en Android |
| Red social Instagram | `sky_social_hub.py` | `SkyInstagramMobileLink.kt`, `SkyInstagramInbox.kt`, `SkyInstagramAlerts.kt` | Recepción y avisos; falta respuesta API con consentimiento y confirmación |
| Voz | `sky_voice_local.py`, `sky_voice_queue.py` | `SkyHandsFreeService.kt`, `SkyEyeVoicePanel.kt` | Manos libres bajo límites Android, no reconocimiento biométrico del propietario |
| Creación multimedia | `sky_design_ai.py`, `sky_video_gen.py` | `SkyGeneratedImage.kt`, `SkyAiVideo.kt`, `SkyVerticalVideo.kt` | Funciones distintas, requieren pruebas de calidad y exportación reales |

## Cambios Android de esta fase

1. Contrato de salida profesional compartido entre Gemini y Groq (`SkyResponseQuality`): acciones verificadas, uso responsable de fuentes, tono natural.
2. Preguntas directas sobre identidad propia a partir del perfil **local** (`SkyOwnerIdentity`); «recuerda que ...» guarda hechos personales explícitos. No hay perfil precargado en el APK, no se publica información del propietario en GitHub.
3. Wikipedia en español: consulta y respuesta enciclopédica con enlace de fuente; no equivale a noticias en vivo.
4. Semantic Scholar: búsqueda de metadatos bibliográficos públicos y enlaces; el usuario debe validar calidad y revisión por pares de cada publicación.
5. Las rutas no ejecutan acciones del modelo en el dispositivo ni autorizan mensajes, llamadas o pagos.

## Lo siguiente, medido y no simulado

- Instagram: borrador real → revisión → confirmación específica → envío por API oficial → recibo verificable. Ver #86.
- Notificaciones con app cerrada: FCM y servidor HTTPS autenticado, sin lectura privada en pantalla bloqueada. Ver #87.
- Conectores móviles por capacidad: iniciar/reproducir con comprobación; Android no concede control irrestricto de apps de terceros.
- Oficina premium: plantillas, layout, PDF/DOCX/XLSX/PPTX correctos, contenido editable y pruebas al abrir.
- Calidad de respuesta: métricas de precisión con fuentes, latencia, fallo/recuperación y pruebas de prompts.
- Identidad entre plataformas: **exportación/importación explícita** como hoy, futura sincronización cifrada y opt-in, nunca exposición de USER.md en APK/GitHub.
- Validación física en Samsung y métricas de batería, permisos, red y bloqueo; no declarar `100 %` ni escalado para 100 mil usuarios sin pruebas.

## Pruebas para aceptar esta fase

`gradle -p mobile/android-agent :app:testStandardDebugUnitTest :app:assembleStandardRelease` en CI; pruebas de emulador API 35/36; firma y publicación solo tras éxito. Después, el propietario deberá comprobar en Samsung que «¿quién soy yo?» responde a su perfil local, que `recuerda que ...` se guarda solo tras su orden y que `busca en Wikipedia` y `busca artículos científicos` devuelven enlaces auténticos. Para noticias actuales, exigir Gemini Search u otra fuente realmente vigente.

