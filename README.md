## SKY Android 0.8.45 — integridad de investigaciones extensas (código en validación)

**Se corrigió un defecto P0 de continuidad:** aunque SQLite archivaba el texto completo de cada trabajo, el contexto enviado para continuarlo podía exceder el contrato del servidor y producir errores **422**. La ruta privada ahora limita el contexto a **8 turnos × 4.000 caracteres**, con extractos **marcados explícitamente** y sin borrar los originales del historial; las nubes externas mantienen 8 × 2.000 caracteres y sus consentimientos. Se mejoró el transporte de respuestas Unicode hasta 512 KB con corte seguro, y se conserva el identificador auténtico de operación de Ollama en el metadato de historial.

No se incrementan artificialmente los límites del modelo: 48.000 caracteres por petición / hasta 6.144 tokens de salida, condicionados por hardware y un contexto Ollama configurado. Se deben certificar CI, emuladores, Samsung físico y generación de un modelo Ollama real antes de anunciarlo como comercial. Se conserva SKY Windows, BAQUEANO, firma, seguridad y versiones anteriores.

[Diagnóstico, pruebas y criterios P0](docs/SKY_ANDROID_0845_CONTINUIDAD_Y_TRAZABILIDAD.md) · [GitHub Actions](https://github.com/OscarElieser/SKY/actions).

---

## SKY Android 0.8.44 — respuestas naturales y trabajo profesional (en validación)

**Código en revisión:** **184 expresiones (176 nuevas y 8 respuestas anteriores conservadas)** de diez categorías (saludos, despedidas, agradecimiento, refranes, motivación, chistes, trabalenguas, adivinanzas, reflexión y estudio), rotación sin uso de nubes ni desvíos de solicitudes académicas. Se amplía **solo la ruta SKY API privada** hasta 48.000 caracteres por consulta, con hasta 6.144 tokens de respuesta si el operador tiene Ollama real configurado para 65.536 tokens de contexto; las nubes externas mantienen 4.000 caracteres y autorizaciones. Se corrigió el historial Android para guardar los textos largos completos. Las órdenes explícitas de planificación generan un **artefacto Markdown editable** en el historial (plan de tesis, investigación o programación), sin afirmar que el trabajo ya esté terminado.

**Pendiente de certificar:** ejecución en servidor de pesos Ollama reales, calidad del contenido, Android 15/16 y Samsung físico (audio, voz, archivos, seguridad y Play Protect), métricas de carga y preparación comercial. No tocar SKY Windows ni BAQUEANO. El código debe pasar CI y firmarse antes de anunciar APK disponible.

[Capacidades, criterios y pruebas de 0.8.44](docs/SKY_ANDROID_0844_EXPRESIONES_Y_TRABAJOS_EXTENSOS.md) · [GitHub Actions](https://github.com/OscarElieser/SKY/actions).

---

## SKY Android 0.8.43 — corrección de instalación Play Protect (candidato, no certificado)

Se elimina de la APK **estándar** el servicio de acceso amplio a notificaciones que estaba en el manifiesto 0.8.42; se mantiene en la variante experimental separada, **no publicada**. Google documenta el bloqueo de instalaciones externas que solicitan ese permiso. La nueva build conservará el mismo paquete, firma de release y datos instalados si Android acepta actualizarla, pero **no se garantiza** que Play Protect permita instalarla hasta probar el APK firmado en Samsung. Se refuerzan las auditorías del binario y el test instrumentado. SKY no debe reportar reproducción audible sin evidencia.

Los cambios académicos de [32.000 caracteres / hasta 4.096 tokens Ollama](docs/SKY_P0_ACADEMIC_32K_2026-10-30.md) están integrados en `main` y se incluirán en la nueva compilación. La ejecución de pesos reales de Ollama, las pruebas de voz/audio y archivos en Samsung siguen pendientes de aceptación.

**Documento de seguridad y pasos de aceptación:** [SKY Android Play Protect 0.8.43](docs/SKY_ANDROID_PLAY_PROTECT_0843.md). **Sin cambios en SKY Windows ni BAQUEANO.**

---

## SKY IA — prioridad P0 de contexto académico y pruebas reales (30/10/2026)

**Cambio de código sujeto a CI y aceptación física:** el chat emparejado mediante SKY API privada y SKY Automático local admite hasta **32.000 caracteres** por turno, sin recortar el texto, y presupuesto de **hasta 4.096 tokens de salida** para consultas de más de 4.000 caracteres. El servidor debe tener capacidad de contexto suficiente (`SKY_INFERENCE_NUM_CTX=32768` para entradas de más de 16.000); una configuración insuficiente se rechaza. Esto no significa capacidad ilimitada ni demuestra un modelo Ollama desplegado. Los proveedores externos mantienen el límite de 4.000 caracteres y consentimiento independiente. SKY Windows y BAQUEANO no se alteran.

**Prioridad de cierre:** verificar respuesta académica extensa con modelo Ollama real → probar audio, voz, archivos e historial en Samsung → auditar seguridad multiusuario y carga. [Guía P0, límites, pruebas y evidencias](docs/SKY_P0_ACADEMIC_32K_2026-10-30.md) · [Auditoría comercial](docs/AUDITORIA_SKY_ANDROID_API_PRELANZAMIENTO_2026-10-30.md) · [Actions](https://github.com/OscarElieser/SKY/actions).

**Verificación:** contratos y pruebas CI en el repositorio; modelo GPU real y pruebas físicas Android aún pendientes. [Matriz de capacidades, pruebas y criterios para mejorar puntuaciones](docs/SKY_CAPACIDADES_VERIFICABLES_Y_HOJA_DE_CALIDAD_2026.md) · [Auditoría técnica](docs/AUDITORIA_SKY_ANDROID_API_PRELANZAMIENTO_2026-10-30.md) · [Actions](https://github.com/OscarElieser/SKY/actions).

---

## Auditoría real de preparación para el mercado (30/10/2026)

**Dictamen NO-GO para lanzamiento comercial abierto.** La APK 0.8.42 firmada se publicó desde el commit `d2834ef0`, anterior a los cambios nuevos de `sky_auto` y no certifica el `main` actual. El proyecto Supabase `SKY-IA` está activo y ya hospeda `sky-platform-readiness` (JWT obligatorio), pero NO se ha conectado un servidor de inferencia Ollama probado. El motor local de SKY tiene límite de dos generaciones simultáneas por proceso. La regresión de seguridad que inicialmente falló 4 casos se corrigió y la nueva prueba backend alcanzó 59/59, pero falta aprobar Android y realizar pruebas en Samsung y GPU.

**Informe técnico completo y puertas de lanzamiento:** [Auditoría SKY Android / API — sostenibilidad, escalabilidad, seguridad e infraestructura](docs/AUDITORIA_SKY_ANDROID_API_PRELANZAMIENTO_2026-10-30.md).

---

## SKY Automático — motor propio primero, sin elegir API manualmente (30/10/2026)

**Implementado como nueva ruta móvil en `main`, pendiente de pruebas de CI y de despliegue real.** SKY Android usa `sky_auto` de forma predeterminada cuando dispone del chat privado de SKY emparejado y autorizado. Selecciona Ollama de SKY primero y solo considera servicios externos si el propietario los ha autorizado y el servidor los ha permitido explícitamente. Las rutas anteriores `ollama`, `auto` y proveedores manuales permanecen disponibles, sin eliminación de funciones ni modificaciones a SKY Windows.

La ruta `neural_core/sky_smart_router.py` mantiene lista de respaldo del servidor `SKY_AUTO_CLOUD_ORDER`: vacía por defecto (solo local), por ejemplo `groq,openrouter,mistral` tras configurar claves, cuotas y autorización comercial. Una cuota agotada provoca enfriamiento temporal, máximo dos intentos externos diferentes y nunca una sustitución oculta de proveedor. El consentimiento de enviar consultas a terceros es opcional, explícito y revocable desde Ajustes en la app; sin él no existe transferencia remota. Incluye pruebas aisladas y CI de enrutamiento, autenticación y privacidad.

[Arquitectura y salvaguardas de SKY Automático](docs/SKY_API_AUTOMATICA_2026.md) · [GitHub Actions](https://github.com/OscarElieser/SKY/actions) · [Releases Android](https://github.com/OscarElieser/SKY/releases).

---

## SKY API — conectores opcionales y con autorización (30/10/2026)

Se agregaron al backend de SKY los adaptadores **OpenRouter, Mistral, Groq y Cloudflare Workers AI**, compatibles con chat completions de texto. **Ollama propio sigue siendo la opción predeterminada** de SKY Android. Las claves externas pertenecen al servidor, nunca a la APK ni a Git. El uso externo requiere consentimiento individual de Nube y Datos privados y no tiene fallback automático a proveedores de pago. **Gemini permanece integrado por su vía existente**; ninguna integración ha sido validada aún con claves reales desde este trabajo.

[Instrucciones, modelos, seguridad y pruebas de conectores](docs/SKY_API_PROVEEDORES_COMPATIBLES_2026.md) · [SKY Inference Gateway y escalabilidad comercial](docs/SKY_API_COMERCIAL_INFERENCIA_2026.md).

---

## SKY API propia — ruta Ollama segura para Android (30/10/2026)

**Implementación de código en `main`, aún no certificada por APK ni despliegue productivo.** Android puede optar por usar primero la API privada de SKY sobre **HTTPS con un token limitado de chat**, solicitando al servidor un modelo Ollama disponible en loopback. Se agregó verificación autenticada de disponibilidad del modelo, sin exponer el puerto 11434, sin copiar claves maestras a la APK y sin sustituir silenciosamente un proveedor externo. No es inferencia nativa en Android y no elimina costos ni límites de operación.

- Código: `mobile/android-agent/app/src/main/java/ni/sky/mobileagent/SkyOwnApiRoutingPolicy.kt`, `metaverse/mobile_chat_api.py`; pruebas `SkyOwnApiRoutingPolicyTest.kt` y `tests/test_sky_mobile_chat.py`.
- Guía: [SKY API comercial — seguridad, inferencia, licencias, capacidad y pendientes](docs/SKY_API_COMERCIAL_INFERENCIA_2026.md).
- Versión declarada en el código Android: **0.8.42**. La versión publicada más reciente debe verificarse en [Releases](https://github.com/OscarElieser/SKY/releases); no instalar una APK sin firma y evidencias verificadas.

> Los estados históricos que aparecen más abajo reflejan auditorías anteriores. No sustituyen el resultado actual de [GitHub Actions](https://github.com/OscarElieser/SKY/actions).

---

## SKY Core unificado · Windows y Android

**Organización del repositorio:** [Mapa oficial de carpetas y plan de migración segura](docs/arquitectura/ESTRUCTURA_REPOSITORIO_SKY.md). Mantener las rutas existentes hasta superar pruebas de compatibilidad.

SKY es un solo producto con dos ejecutores nativos independientes. El [contrato de seguridad común](shared/sky_core_contract_v1.json) establece autorizaciones, riesgos y evidencias compartidas; los conectores Python y Kotlin lo aplican sin compartir claves, permisos, datos privados ni exigir que Windows permanezca encendido. **No se ha implementado todavía sincronización de memoria ni paridad total**. Las acciones de alto riesgo exigen autorización individual y confirmación desde una interfaz local.

[Arquitectura, seguridad y migración sin pérdida](docs/SKY_UNIFIED_CORE_SECURITY.md) · [Matriz de capacidades Windows/Android](docs/SKY_WINDOWS_ANDROID_PARITY_2026-10-29.md) · [Estado de compilaciones](https://github.com/OscarElieser/SKY/actions).

---

## Auditoría de consolidación en `main` — 30/10/2026

**Fuente de verdad:** `main` es la rama de integración, pero tener otras ramas o etiquetas no significa que sus cambios estén incorporados ni que deban eliminarse. No hacer merges forzados ni reescribir historial sin comparación de archivos, conflictos y pruebas satisfactorias.

- **Issues:** 7 abiertos (a la hora de revisión), dedicados a voz y pruebas Android, agentes y herramientas, autonomía supervisada, Instagram y memoria multimodal. Un issue es seguimiento de trabajo; no demuestra por sí solo un bug.
- **Pull requests:** [#96, sesiones de voz y sueño persistente Android](https://github.com/OscarElieser/SKY/pull/96), permanece abierto. GitHub reportó `mergeable=false`, `mergeable_state=dirty`: requiere resolver conflictos y volver a comprobar las pruebas antes de fusionarlo. **No se ha fusionado.**
- **Ramas:** aproximadamente 99 visibles, incluyendo respaldos, ramas históricas, versiones y desarrollos. Las ramas `fix/sky-android-voice-session-isolation-20261030`, `feature/sky-multiagent-quality-20261030`, `feature/sky-reflective-core-20261030` y `feature/sky-android-local-playback-proof-20261030` mostraron commits divergentes con respecto a `main`. La rama `feature/sky-mobile-agent-android-20261026` se encontró completamente detrás de `main` y sin commits exclusivos. Estas comparaciones **no certifican que todo su código funcional falte o sobre**: requieren revisión por archivo.
- **Etiquetas:** se mostraron 36 tags; son referencias de versiones y **no deben fusionarse como ramas** ni borrarse por limpieza.
- **Seguridad:** la corrección del test obsoleto de adopción de servicios se publicó en `main`; su aceptación depende de un GitHub Actions verde. Conservar el control que impide adoptar procesos de origen no acreditado.
- **APK:** el código Android declara `0.8.41`; una versión declarada no equivale a una APK firmada publicada. Verificar [Releases](https://github.com/OscarElieser/SKY/releases), huella de firma, SHA-256 y pruebas reales antes de instalar.

### Criterios de integración sin pérdida

1. Comparar `main...rama` para conocer commits exclusivos y archivos afectados.
2. Resolver conflictos mediante revisión; no usar `force push`, no reescribir `main`, no borrar respaldos ni ramas con trabajo exclusivo.
3. Ejecutar pruebas Android y de seguridad aplicables antes de fusionar, y comprobar nuevamente el estado de `main`.
4. Registrar en PR o issue la evidencia de integración, pruebas y pendientes; cerrar únicamente aquello que esté demostrado.
5. Mantener separadas la validación en CI, la instalación de APK y las pruebas físicas en Samsung.

---

## Estado verificable — 30 de octubre de 2026

**SKY Android:** el código de `main` declara la versión **0.8.41** (`versionCode 54`). Esto **no equivale a una APK publicada ni probada**. Consultá [GitHub Releases](https://github.com/OscarElieser/SKY/releases) para obtener exclusivamente versiones firmadas, con su huella y SHA-256. La última APK publicada al momento de esta revisión era **0.8.38**; confirmar de nuevo antes de instalar.

**Operaciones locales de archivos Android (en validación):** interpretar instrucciones, mostrar propuesta, aprobar o cancelar, crear/modificar archivos de texto en almacenamiento privado, guardar respaldos con metadatos persistentes, listar copias verificadas y restaurarlas con aprobación individual. Registro local de estados y huellas SHA-256. **No** implica editar archivos de terceros, ejecutar cambios remotos con tokens del chat móvil, ni certificar ejecución sobre un Samsung real. Pruebas instrumentadas, compilación firmada y Android 15/16 deben aprobarse para declarar disponibilidad. No desactivar Play Protect.

**Seguridad y regresión:** el flujo `security-v103.yml` falló en el commit `43c2a7a` con **526 pruebas superadas y 1 fallida**. La prueba antigua exigía adoptar un servicio SKY activo sin comprobar propiedad, contradiciendo el control actual que evita duplicar o tomar procesos existentes. Se ajustó **solo la prueba de regresión**, sin cambiar el ejecutor de Windows; la corrección requiere una nueva ejecución verde para considerarse verificada. [Consultar resultados](https://github.com/OscarElieser/SKY/actions/workflows/security-v103.yml).

**Principio:** ninguna compilación, acción, envío, restauración o protección se anuncia como funcional solo por existir su código. La ejecución real y la evidencia deben confirmarse por separado.

---

# 🌌 SKY IA — Asistente personal, docente y plataforma modular

**Versión base:** `12.6.0` · **Rama oficial:** [`main`](https://github.com/OscarElieser/SKY/tree/main) · **Estado:** desarrollo activo, con pruebas automatizadas y validaciones de hardware e integraciones aún pendientes.

**Visión y autoría conceptual:** Oscar Elieser Chamorro Guzmán.

SKY IA es un proyecto de asistente inteligente que reúne **voz, texto, control autorizado del equipo, docencia interactiva, investigación académica, desarrollo de proyectos, trabajo profesional y herramientas creativas** en un mismo núcleo. Su interfaz principal es un **HUD holográfico**, conectado a una **API propia de FastAPI** y módulos especializados.

> **Compromiso técnico:** diferenciar una propuesta, un borrador, una consulta, una acción enviada y una acción realmente verificada. El código presente en GitHub no implica que cada servicio externo o dispositivo esté instalado y funcionando en cualquier computadora.

[![Seguridad](https://github.com/OscarElieser/SKY/actions/workflows/security-v103.yml/badge.svg?branch=main)](https://github.com/OscarElieser/SKY/actions/workflows/security-v103.yml)
[![SKY Aula](https://github.com/OscarElieser/SKY/actions/workflows/sky-academy-tests.yml/badge.svg?branch=main)](https://github.com/OscarElieser/SKY/actions/workflows/sky-academy-tests.yml)
[![SKY Core](https://github.com/OscarElieser/SKY/actions/workflows/sky-core-consolidation.yml/badge.svg?branch=main)](https://github.com/OscarElieser/SKY/actions/workflows/sky-core-consolidation.yml)

**Navegación:** [Inicio](#-inicio-rápido-en-windows) · [Funciones](#-capacidades-del-ecosistema) · [Docencia e investigación](#-educación-investigación-e-innovación) · [Skills](#-skills-profesionales) · [Seguridad](#-seguridad-y-privacidad) · [API](#-api-propia) · [Pruebas](#-pruebas-y-verificación) · [Documentación](#-documentación).

---



> **Instagram / Meta (29/10/2026):** webhook HTTPS verificado, función de Supabase v16 desplegada y bandeja privada de eventos añadida con RLS, deduplicación y acceso autenticado. Todavía faltan una entrega real a la v16, permisos/suscripciones en Meta y su interfaz Android; no se activan respuestas automáticas. [Evidencias y próximos ensayos](supabase/SKY_INSTAGRAM_DEPLOYMENT.md).

## 📱 SKY Android 0.8.27 — ejecución verificable y aprendizaje de resultados

El módulo móvil integra controles Android con resultados observables: cambios de volumen comprobados antes/después, notas reabiertas tras guardar, evidencias persistentes diferenciadas de simples solicitudes, métricas locales por tipo de resultado y validación explícita del origen del propietario al ejecutar órdenes por voz. Las aperturas de apps y los eventos musicales **no** se consideran tareas terminadas si Android solo aceptó la solicitud. El trabajo conserva los límites de permisos y no modifica SKY Windows.

**Publicación verificada el 29/10/2026:** la versión firmada [SKY Android 0.8.27](https://github.com/OscarElieser/SKY/releases/tag/sky-android-v0.8.27) está publicada como beta personal. [Compilación y controles de firma aprobados](https://github.com/OscarElieser/SKY/actions/runs/40859332903) y [pruebas del emulador Android 15/16 aprobadas](https://github.com/OscarElieser/SKY/actions/runs/40859332929). Estas verificaciones no equivalen a aceptación en el Samsung real: siguen pendientes las pruebas de voz, batería, pantalla bloqueada, proveedores externos y reproducción audible. [Guía de ejecución](mobile/android-agent/docs/SKY_EXECUTION_EVIDENCE_0.8.27.md) · [Protocolo de aceptación física](mobile/android-agent/docs/ANDROID_REAL_DEVICE_ACCEPTANCE.md).

---

## 🧠 Núcleo evolutivo propio, seguridad y evidencias — actualización 28/10/2026

La **API propia de SKY** utiliza FastAPI y el sistema existente de autorización. Ahora también contiene un **motor adaptativo nativo** en `neural_core/sky_adaptive_policy.py`: procesa datos operacionales agregados del propio SKY, calcula fiabilidad por rol (intervalos de Wilson) y sugiere cuándo revisar fallos o seguir con pruebas supervisadas. **Funciona sin llamar a Gemini, ChatGPT ni otro proveedor para esa operación.** Es aprendizaje estadístico consultivo, no un LLM independiente de producción, no entrenamiento automático de pesos y no sustituye el razonamiento generativo.

**API nueva (requiere autenticación SKY):** `GET /api/sky/cognition/native-evolution` y `POST /api/sky/cognition/adaptive-plan`. La consulta no ejecuta comandos, no amplía permisos, no almacena texto ni cambia código. Los resultados de acción deben venir de un ejecutor real: la salida de una IA no es una prueba.

**Seguridad por capas:** identidad y autenticación; validación de entrada y separación de fuentes no confiables; privacidad y memoria cifrada; planificación sin autoridad implícita; autorización y ejecución supervisada; evidencia de resultados; CI, firmas y distribución. La arquitectura se basa en mínimo privilegio y controles contra inyección de instrucciones, exceso de agencia y exposición de secretos. Los controles no equivalen a una certificación externa.

**Evidencias y trazabilidad:** `.github/workflows/sky-native-core-evidence.yml` compila el componente nativo, ejecuta sus pruebas en GitHub Actions y conserva un manifiesto JSON con resultado real, commit, hashes SHA-256 y URL del run (**artefacto temporal de 90 días**). No incluye datos privados. La compilación firmada de Android tiene su propio workflow y requiere además pruebas en el teléfono.

[**Arquitectura detallada, siete capas de seguridad, API y matriz de pruebas**](docs/arquitectura/SKY_CORE_EVOLUCION_SEGURIDAD_EVIDENCIAS.md) · [**Evidencia del núcleo en GitHub Actions**](https://github.com/OscarElieser/SKY/actions/workflows/sky-native-core-evidence.yml) · [**APK publicadas**](https://github.com/OscarElieser/SKY/releases)

**Estado:** los cambios de código en `main` y la ejecución de GitHub Actions deben comprobarse por separado. No se afirma funcionamiento de la API en un servidor externo, aprendizaje autónomo ilimitado, equivalencia con otras IAs, ni soporte para 100 000 conexiones sin ensayos de carga.

---

## 📱 SKY Android — núcleo móvil autónomo (código 0.8.27; publicación independiente)

**SKY Android funciona de forma independiente de SKY Windows** para
conversaciones por Gemini y acciones locales autorizadas. El desarrollo
Android no modifica los servicios del PC. **Versión de código actual: 0.8.27**;
las APK de GitHub Releases pueden ir por detrás si CI o las pruebas todavía
no han terminado. La autorización Meta de Instagram en Supabase existe,
pero la identidad del perfil y la vinculación física del teléfono requieren
verificación independiente. Los apartados 0.8.6 y anteriores son históricos.

[**Ver APK realmente publicadas en GitHub Releases**](https://github.com/OscarElieser/SKY/releases) ·
[Guía móvil](mobile/android-agent/README.md) ·
[Instalación y verificación](mobile/android-agent/apk/README.md)

### Nuevo en 0.8.6 — preparación de Instagram API con Creador

- **Instagram personal no admite acceso API profesional.** Desde
  Instagram se puede cambiar a **Creador**, conservando publicaciones
  y seguidores, pero pasando a un perfil público.
- SKY Android muestra una guía paso a paso para convertir la cuenta,
  registrar localmente que el usuario hizo el cambio y revisar los
  requisitos de **Instagram API with Instagram Login** de Meta.
- La confirmación de Creador dentro de SKY **no significa conectado**.
  Todavía faltan una app Meta configurada, permisos OAuth y un backend
  HTTPS seguro sin claves privadas dentro del APK.
- Permisos previstos: `instagram_business_basic`,
  `instagram_business_manage_insights` y
  `instagram_business_content_publish`, solicitados por finalidad
  cuando estén disponibles y aprobados.
- No se requiere una Página de Facebook para la ruta
  **Instagram Login**; SKY Windows permanece sin cambios.

[Guía de Instagram y autorización oficial](mobile/android-agent/INSTAGRAM_OAUTH_SETUP.md).
La APK debe verificarse en CI y publicarse en Releases antes de instalar.

### Nuevo en 0.8.5 — perfiles sociales identificados localmente

- **Catálogo de redes en Android:** perfiles públicos de Instagram,
  Threads, TikTok, Facebook, YouTube, X y otras redes, identificados
  mediante JSON descargado por el usuario o añadidos manualmente.
- **Sin divulgar datos:** el repositorio no incluye los perfiles
  personales, teléfonos ni correos del propietario; Android almacena
  los identificadores importados solo en preferencias privadas locales.
- **Enlaces públicos y Estudio Creativo:** abrir el perfil registrado,
  editarlo, retirarlo o crear contenido para esa plataforma.
- **Sin confundir identificación con conexión OAuth:** un usuario
  público no permite a SKY consultar métricas privadas, publicar
  automáticamente ni enviar mensajes. Esas capacidades requieren
  consentimiento, autorización y permisos oficiales por plataforma.
- **Android independiente:** no se cambia SKY Windows, no se introduce
  clave privada ni se activa un servicio que lea todas las cuentas.

**Versión de código:** `0.8.5` (`versionCode 18`), a comprobar con
compilación firmada y prueba de importación JSON en el Samsung.

### Nuevo en 0.8.4 — órdenes musicales sin repetir SKY

- **Control multimedia Android:** `siguiente`, `atrás`,
  `cambia de música`, `repite`, `subí el volumen`,
  `bajá el volumen`, `pará` y `reanudar`, mediante el
  reproductor activo y ajustes de audio del teléfono.
- **Acción verificable, no promesa:** para siguiente/anterior/pausa
  se envían pulsaciones multimedia estándar; la app reproductora
  determina si se cumplen. «Repite» intenta volver al inicio enviando
  anterior, que puede cambiar la pista. No existe aún bucle completo.
  El volumen informa si Android modificó el nivel.
- **Pantalla de bloqueo:** la voz «activá el teléfono» solicita
  el desbloqueo **solo mientras SKY está visible y escuchando**.
  Android exige PIN o biometría cuando corresponde. No se evade
  el bloqueo ni se mantiene el micrófono escuchando con pantalla
  apagada en esta versión.
- **Pruebas y control:** panel de órdenes multimedia en Ajustes
  para validar la acción sin voz; tests unitarios del intérprete
  de comandos. Requiere pruebas en el Samsung real.
- **Redes sociales:** compartir identificadores públicos ayuda a
  preparar conectores, pero no equivale a acceso a estadísticas o
  publicación. Para ello se necesitan autorizaciones OAuth y
  permisos de las plataformas; jamás almacenar contraseñas en GitHub.

**Código Android `0.8.4`, versionCode `17`** en `main`.
Comprobar la compilación y firma antes de instalar desde
[Releases](https://github.com/OscarElieser/SKY/releases).
El PC y el proyecto SKY Windows permanecen intactos.

### Nuevo en 0.8.3 — creador y analista local de redes

- **Análisis de métricas reales importadas:** panel en Android que acepta
  CSV del usuario con plataforma, publicación, vistas, likes, comentarios,
  compartidos, seguidores y fecha. Calcula interacción y destaca contenido;
  **no sincroniza todavía con redes por OAuth** ni inventa métricas.
- **Video MP4 generado en el teléfono:** 10 segundos verticales H.264
  (720×1280, 15 fps), fondos y textos originales animados desde un
  guion editable. Exportación local usando MediaCodec/OpenGL ES.
  **Sin audio ni fotografías** en esta primera etapa; se completa en
  el editor de la red. Requiere pruebas reales de GPU/codificador.
- **Publicación asistida:** compartir guiones y MP4 vía el selector
  oficial Android. La aplicación receptora y el usuario controlan
  destinatario, privacidad y publicación. La publicación directa
  automática requiere API, consentimiento y permisos de plataforma.
- **Arquitectura móvil:** Android gestiona interfaces, herramientas,
  archivos, métricas y permisos; Gemini ayuda en generación de texto
  cuando el usuario habilita conexión. No se modifican módulos Windows.
- **Sin accesos ocultos:** no hay lectura de chats, uso clandestino
  de cámara/micrófono, tokens de redes extraídos ni automatización de
  seguidores/likes. Toda función comunica si la acción fue iniciada,
  completada o requiere confirmación.

**Estado:** código `0.8.3` en `main`; la APK no debe presentarse
como disponible hasta aprobar pruebas y firma en GitHub Actions y
publicarse en [Releases](https://github.com/OscarElieser/SKY/releases).
[Documentación Android y formatos CSV](mobile/android-agent/README.md).

### Evolución 0.8.2: hablá con SKY como con una compañera

- **Sin repetir «SKY»:** órdenes directas de música y conversación fluida
  voluntaria, solo con la app abierta y máximo ocho turnos seguidos.
- **Spotify, YouTube Music y YouTube:** reproducir canciones mediante el
  intent oficial de Android, con búsqueda como respaldo. No confundir
  solicitud a la app con reproducción confirmada.
- **Contactos elegidos:** lista privada, fragmento recibido aportado por el
  usuario y redacción natural con Gemini. Borradores editables para WhatsApp
  con selección de chat y envío final por el usuario. **Sin lectura de
  conversaciones ni autorrespuestas ocultas**.
- **Cámara de una foto:** apertura voluntaria, confirmación antes de enviar
  una miniatura a Gemini y comentario de lo visible sin inferir emociones
  ni diagnosticar salud mental. No hay cámara continua.
- **Compañera cercana:** respuestas cálidas, humor y apoyo sin saludos
  mecánicos ni declarar acciones que no se verificaron.
- **Seguridad:** no solicitar control irrestricto, contactos ni permisos de
  mensajería en segundo plano; no exponer claves ni materiales privados.

**Estado de la etapa anterior:** código 0.8.2 integrado en `main`; la descarga de APK
solo se recomienda cuando la compilación, firma y SHA-256 aparezcan
en [GitHub Releases](https://github.com/OscarElieser/SKY/releases).
La app instalada se conserva hasta completar pruebas en Android.

### Experiencia y herramientas Android

- **Interfaz viva:** únicamente ojos y boca animados, sin máscara ni rostro;
  estados visuales mientras SKY escucha, piensa y habla.
- **Conversación:** voz mediante SpeechRecognizer/TextToSpeech, charla con
  Gemini desde internet, escucha fluida opcional únicamente en primer plano.
- **Acciones supervisadas:** abrir aplicaciones instaladas, alarmas, notas,
  temporizadores, búsquedas y borradores de WhatsApp con confirmación
  del propietario. SKY no envía mensajes a escondidas.
- **SKY Estudio Creativo:** ideas, guiones, ganchos, subtítulos, descripciones,
  cinco hashtags y planes de siete días para **TikTok, Instagram, Facebook,
  YouTube, X, Threads, Snapchat, Pinterest y LinkedIn**.
- **Creación sin cámara:** guiones con tomas propias, pantalla, subtítulos
  y narración opcional; no requiere mostrar el rostro ni hablar ante cámara.
- **Publicación supervisada:** borrador editable y menú de compartir oficial de
  Android. Las aplicaciones receptoras deciden qué formatos aceptan; SKY
  no afirma haber publicado. No usa bots, seguidores o likes falsos.
- **Crecimiento real:** recomendaciones basadas en la información aportada
  por el usuario. SKY todavía no tiene acceso automático a estadísticas,
  cuentas sociales, tendencias actuales ni permisos OAuth de publicación.

**Estado:** versión 0.8.2 de código Android en `main`. La APK debe
superar compilación, tests y firma antes de descargarse desde GitHub Releases,
y se validará posteriormente en el Samsung. Conservá la instalación anterior
hasta confirmar el nuevo paquete. Si Play Protect bloquea la instalación,
no fuerces el proceso.

**Seguridad:** la clave Gemini se configura y cifra en el teléfono para
beta privada. La distribución pública exige migrar a un backend autenticado
con cuotas y prevención de abuso; SKY no solicita contraseñas de redes
sociales ni automatiza acciones sociales sin aprobación.

---

## ✨ Capacidades del ecosistema

| Componente | Función disponible en el repositorio | Alcance / requisitos |
| --- | --- | --- |
| **SKY CORE y HUD** | Conversación, herramientas, paneles y ventanas holográficas | La experiencia depende del motor seleccionado y servicios disponibles. |
| **Voz y texto** | Vosk, faster-whisper, Piper y dictado/síntesis del navegador, según configuración | Requiere validar micrófono, modelos, audio y permisos en el equipo real. |
| **OpenJarvis opcional** | Motor externo de IA de texto por API local, con selector, diagnóstico y KPI | Desactivado por defecto; requiere instalación aislada y agente simple. [Guía](docs/guias/SKY_OPENJARVIS.md). |
| **SKY Creative Evolution** | Obras en nueve idiomas, capítulos versionados, imágenes Gemini mejoradas, WAV instrumental original y montaje MP4 real desde escenas ilustradas | Capacidades según modelo/FFmpeg instalado, autorización de API y render confirmado. [Guía](docs/guias/SKY_CREATIVE_EVOLUTION.md). |
| **Agente del dispositivo** | Apps, webs HTTPS, controles multimedia, notas, ventanas y otras acciones según perfil | Necesita agente autenticado, política local y confirmaciones cuando corresponda. |
| **Office y Creative Studio** | Documentos, hojas, presentaciones, PDF, medios, video y recursos visuales | Algunas funciones precisan bibliotecas, modelos o API de terceros. |
| **SKY Aula** | Lecciones por nivel, sesiones, siete etapas, retroalimentación formativa y borradores | Revisión docente obligatoria; no equivale a un currículo oficial validado. |
| **SKY Scholar e Impacto** | Planes de investigación, OpenAlex, Crossref, metadatos DOI y fuentes registradas | Consultar metadatos no significa leer ni verificar el artículo íntegro. |
| **Innovación** | Planteamiento de problemas, Canvas, hipótesis, MVP, pitch y revisión por rúbrica aportada | No se inventan resultados de campo ni se garantizan premios. |
| **Pro Skills** | Redacción, diseño, programación, ingeniería, contabilidad, gestión, marketing, RR. HH. y más | Guías de respuesta propias, no instalación automática de terceros. |
| **Memoria y conocimiento** | Biblioteca documental, memoria explícita, búsqueda y registros | Almacenamiento/configuración privada; verificar fuentes antes de considerarlas hechos. |
| **SKY Guardian y Device Hub** | Inventario consentido, incidentes declarados, diagnóstico y conexión limitada | No da acceso automático a cámaras, cuentas, redes policiales o teléfonos ajenos. |
| **SKY SENTINEL y KPI** | Autenticación, PIN opcional, MFA, políticas, parada de emergencia, métricas y diagnósticos | Las pruebas CI no sustituyen auditoría independiente ni ensayo físico. |

SKY también mantiene el **metaverso 3D y la comunidad**, las automatizaciones, el módulo deportivo, la gestión de proyectos y conectores opcionales para correo, WhatsApp, Home Assistant y motores de IA locales o en la nube.

## 🚀 Inicio rápido en Windows

### 1. Instalación

**Para instalar todas las dependencias declaradas en otra computadora Windows** (Python, voz, LoRA, Office, MCP, Node/Flutter y herramientas externas optativas), usá el archivo maestro `requirements_sky_all.txt` y el instalador de una sola ejecución:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\INSTALAR_DEPENDENCIAS_SKY.ps1" -Perfil Completo -Herramientas
```

En tu PC de casa con 8 GB RAM, empezá por `-Perfil Casa` en vez de instalar todos los módulos pesados. Documentación: [Instalación completa de SKY](docs/INSTALACION_COMPLETA_SKY.md).

Para el instalador operativo tradicional, descargá o cloná el repositorio y ejecutá en su carpeta:

```bat
INSTALAR_SKY_WINDOWS.bat
```

El instalador utiliza `instalar_sky.ps1` para preparar Python, el entorno y los componentes seleccionados. Puede necesitar internet para descargar dependencias y modelos.

Opciones documentadas:

```bat
INSTALAR_SKY_WINDOWS.bat -Local
INSTALAR_SKY_WINDOWS.bat -Modelo qwen2.5:7b
```

**No asumás que Ollama, los modelos de voz o los servicios externos están listos si el instalador reporta errores.** Para más detalles consultá [Inicio v12](README_V12_INICIO.md).

### 2. Iniciar SKY

```bat
SKY_INICIAR.bat
```

Elegí **`0 — SKY COMPLETO`** para iniciar el HUD, la API, la voz y el agente configurado. Las otras opciones del menú permiten abrir Office Studio, Creative Studio, Streamlit, el diagnóstico, los permisos del dispositivo y las pruebas.

| Componente | Dirección local |
| --- | --- |
| HUD principal | [`http://127.0.0.1:8765/`](http://127.0.0.1:8765/) |
| SKY Aula e Innovación | [`http://127.0.0.1:8765/aula`](http://127.0.0.1:8765/aula) |
| Interfaz clásica | [`http://127.0.0.1:8765/sky`](http://127.0.0.1:8765/sky) |
| Office Studio | [`http://127.0.0.1:8765/office`](http://127.0.0.1:8765/office) |
| Creative Studio | [`http://127.0.0.1:8765/creative`](http://127.0.0.1:8765/creative) |
| Panel Streamlit (si se inicia) | [`http://127.0.0.1:8501/`](http://127.0.0.1:8501/) |

**Son direcciones de la propia computadora, no páginas públicas.**

### 3. Comprobar el funcionamiento

```bat
.venv\Scripts\python.exe sky_diagnostico.py
.venv\Scripts\python.exe iniciar_sky_autonomo.py --status
```

También podés usar la **opción 7** de `SKY_INICIAR.bat`. La disponibilidad real de voz, Ollama, periféricos y servicios se debe comprobar en el equipo que ejecutará SKY.

### 4. Configuración privada

Si la instalación no generó ya tu configuración:

```bat
copy .env.example .env
```

La plantilla [.env.example](.env.example) contiene variables opcionales. Completá **únicamente las necesarias** y no publiques `.env`. La API puede crear una clave propia en archivos locales; no se debe copiar esa clave al repositorio.

## 🎙️ Hablá o escribile a SKY

Ejemplos de solicitudes para los módulos correspondientes:

- **Equipo:** «SKY, abrí Word»; «organizá mis ventanas»; «abrí mis documentos».
- **Música:** «pausá la canción»; «siguiente»; «silenciá el sonido».
- **Productividad:** «prepará una presentación sobre energía solar»; «mostrame mis pendientes».
- **Docencia:** «SKY, impartí una clase de números naturales para primaria»; «SKY, siguiente paso de la clase».
- **Investigación:** «prepará un plan de investigación sobre movilidad sostenible»; «buscá publicaciones académicas sobre educación inclusiva».
- **Innovación:** «armemos un proyecto para Hackathon Nicaragua sobre reciclaje».
- **Rendimiento:** «mostrame los KPI y los errores recientes».

Los comandos conocidos pueden usar herramientas directas; otros requieren el proveedor de IA configurado. **Una respuesta en texto no acredita que una orden se ejecutó.** Las modificaciones, envíos y accesos dependen de permisos reales y autorizaciones específicas.

Guías: [inicio y comandos](README_V12_INICIO.md) · [manos libres y agente local](README_SKY_JARVIS_LOCAL.md).

## 🎓 Educación, investigación e innovación

### SKY Aula: docente interactivo

El módulo [SKY Aula](docs/api/SKY_AULA_INNOVACION_INVESTIGACION.md) trabaja con **educación inicial, primaria, secundaria, formación técnica, universidad, maestría y doctorado**. Cada lección puede organizarse en siete momentos: bienvenida, saberes previos, explicación, ejemplo, práctica, reflexión y cierre.

Permite iniciar una sesión, avanzar por etapas, recibir respuestas del estudiante, ofrecer orientación formativa y exportar borradores de materiales. Los contenidos para estudiantes deben revisarse por un docente; la actividad no supone una calificación clínica, oficial ni automática.

### SKY Scholar: fuentes académicas

SKY combina planificación metodológica y consulta de referencias por vías delimitadas:

- **OpenAlex:** búsqueda de registros bibliográficos.
- **Crossref:** búsqueda de publicaciones y consulta de metadatos DOI.
- **Google Académico:** enlaces de búsqueda manual; **no se simula una API oficial ni se extraen automáticamente sus resultados**.
- **Universidades y GitHub:** catálogo y lectura controlada de recursos públicos o repositorios autorizados.
- **Documentos del usuario:** lectura de archivos compatibles; los escaneos, imágenes y medios pueden necesitar herramientas adicionales.

Las referencias bibliográficas requieren revisión del trabajo original. Nunca tratar un título, DOI o extracto como demostración automática de las conclusiones del artículo.

### Innovation Lab y competencias

Preparación de propuestas para **Hackathon Nicaragua, Rally Nacional Nicaragua Innova, Rally Latinoamericano de Innovación, INNOVATEC** y problemas de educación, salud, transporte, ambiente, industria, cultura y sociedad.

Entregables de apoyo: problema, causas, objetivos SMART, hipótesis, propuesta de valor, Canvas, MVP/prototipo, plan de validación, pitch y documentación. El presupuesto, la rúbrica, la evidencia, los usuarios y el impacto **deben verificarse**; el sistema no garantiza ganar concursos.

Leé [SKY Impacto, Scholar y Pro Skills](docs/guias/SKY_IMPACTO_EDUCACION_INNOVACION.md).

## 🧰 Skills profesionales

Existen perfiles en `neural_core/sky_pro_skills.py` y cuatro guías para agentes compatibles con archivos `SKILL.md`:

| Skill local | Para qué se utiliza |
| --- | --- |
| [SKY Humanize](.agents/skills/sky-humanize/SKILL.md) | Redacción natural, manteniendo hechos, referencias e intención |
| [SKY Impeccable](.agents/skills/sky-impeccable/SKILL.md) | Calidad gráfica, identidad visual, UI/UX y accesibilidad |
| [SKY Academic Research](.agents/skills/sky-academic-research/SKILL.md) | Investigación, fuentes, método, citas y límites de la evidencia |
| [SKY Professional Global](.agents/skills/sky-professional-global/SKILL.md) | Orientación en ingeniería, software, finanzas, gestión y otras disciplinas |

**Importante:** son guías **propias del proyecto**; no se han instalado automáticamente productos externos denominados Humanizer o Impeccable. El [catálogo de 78 skills](docs/api/SKY_CATALOGO_78_SKILLS_2026.md) describe ideas **propuestas**, no 78 integraciones activas.

## 🧠 Arquitectura

```text
Usuario ─── voz / texto / documentos
                 │
                 ▼
            SKY CORE + HUD
                 │
          SKY API (FastAPI)
                 │
      ┌──────────┼─────────────┐
      ▼          ▼             ▼
   SENTINEL    Motor IA     Especialistas
   claves,     Ollama       Aula · Scholar
   PIN, MFA    / APIs       Impacto · Skills
   permisos                 Office · Guardian
      └──────────┼─────────────┘
                 ▼
       Herramientas autorizadas
     Agente Windows / archivos /
       memoria / dispositivos
                 │
                 ▼
        Resultados y telemetría
```

La arquitectura **reutiliza la API propia de SKY**. Los routers añaden capacidades sin sustituir los controles del núcleo ni conceder permisos universales al agente.

### Estructura del proyecto

```text
SKY/
├── README.md                       # Guía principal
├── VERSION.txt                     # Versión base
├── README_V12_INICIO.md            # Manual Windows
├── INSTALAR_SKY_WINDOWS.bat        # Instalador
├── SKY_INICIAR.bat                  # Menú central
├── iniciar_sky_autonomo.py         # Arranque y estado
├── agente_dispositivo.py           # Agente autorizado
├── sky_manos_libres.py             # Reconocimiento local
├── sky_diagnostico.py              # Diagnóstico
├── app.py                          # Streamlit alternativo
├── metaverse/                      # API y vistas (HUD, Aula, Office)
│   ├── api.py
│   ├── academy_api.py
│   ├── impacto_api.py
│   ├── guardian_api.py
│   └── device_hub_api.py
├── neural_core/                    # Núcleo, investigación y herramientas
│   ├── sky_aula.py
│   ├── sky_impacto.py
│   ├── sky_scholarly.py
│   ├── sky_pro_skills.py
│   └── sky_office.py
├── .agents/skills/                 # Skills de proyecto
├── tests/                          # Pruebas automatizadas
├── .github/workflows/              # GitHub Actions
├── docs/                           # Manuales y especificaciones
└── .env.example                    # Configuración de muestra
```

Los datos locales, modelos y secretos **no forman parte de la configuración pública**.

## 🔐 Seguridad y privacidad

**SKY SENTINEL** protege la API con credenciales del dueño, segundo factor opcional, PIN opcional, políticas de dispositivo, confirmaciones para operaciones sensibles, parada de emergencia y registros.

1. **API privada:** las solicitudes a rutas de propietario necesitan `X-SKY-KEY`; si se habilita MFA, también `X-SKY-SESSION`.
2. **Dispositivos autorizados:** cada agente mantiene su token, perfil de capacidades y restricciones de carpetas/herramientas.
3. **Acciones sensibles:** no convertir una instrucción de voz en autorización automática para borrar, enviar, pagar, cambiar permisos o instalar.
4. **Fuentes no confiables:** los archivos, sitios, correos y repositorios leídos son datos para analizar, no instrucciones del sistema.
5. **Conexiones remotas:** usar redes privadas configuradas, nunca publicar directamente los puertos locales de SKY.

El HUD en navegador móvil **no implica control nativo del sistema Android o iOS**. La conectividad y los módulos Guardian/móvil requieren autorización, dispositivos reales y pruebas.

Consulta [SKY SENTINEL](docs/seguridad/SENTINEL_FASES_1_2.md), [conectividad segura](docs/api/SKY_SECURE_CONNECTIVITY.md) y [estado real](docs/ESTADO_REAL_SKY.md).

## 🔌 API propia

El servicio principal funciona en `127.0.0.1:8765`. Las siguientes rutas comparten la aplicación FastAPI y sus controles:

| Prefijo | Componente |
| --- | --- |
| `/api/asistente` | Mensajería, streaming y acciones autorizadas |
| `/api/impacto` | Investigación, fuentes, Scholar, skills y planificación |
| `/api/sky/academy` | Lecciones, sesiones, proyectos y documentos |
| `/api/sky/knowledge` | Biblioteca documental privada |
| `/api/sky/neural-memory` | Memoria explícita y reportes |
| `/api/sky/reader` | Análisis de documentos e imágenes/medios |
| `/api/sky/guardian` | Incidentes e inventario autorizado |
| `/api/sky/device-hub` | Dispositivos y comprobaciones limitadas |
| `/api/sky/mobile-unlock` | Diagnóstico legítimo de móviles, **sin eludir bloqueos** |

Consulta autenticada de ejemplo en PowerShell:

```powershell
# Cargar la clave solamente en el equipo local.
$headers = @{ "X-SKY-KEY" = $env:SKY_API_KEY }
Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/sky/academy/capabilities" -Headers $headers
```

Si la clave se generó en un archivo privado, seguí el procedimiento local de tu instalación; añadí `X-SKY-SESSION` si MFA está habilitada. Las rutas no conceden acceso automático a servidores universitarios, cuentas de correo o datos privados de terceros.

## ✅ Pruebas y verificación

```bat
.venv\Scripts\python.exe -m pytest -q tests
```

O usá la **opción 9** del menú principal. Para revisar directamente los módulos añadidos:

```bat
.venv\Scripts\python.exe -m pytest -q tests/test_sky_academy_innovation.py tests/test_sky_impacto.py tests/test_sky_scholarly_skills.py
.venv\Scripts\python.exe -m pytest -q tests/test_sky_core_consolidation.py
```

Los flujos de [GitHub Actions](https://github.com/OscarElieser/SKY/actions) verifican suites delimitadas de regresión, seguridad, API y módulos. El éxito de un flujo **no garantiza** que cada micrófono, cámara, app, teléfono, modelo o cuenta de terceros funcione fuera del entorno de pruebas.

## 🔌 SKY MCP Hub — cliente oficial con permisos

SKY incorpora un cliente **Model Context Protocol v2** opcional dentro de su API existente, que permite descubrir herramientas MCP instaladas localmente y llamarlas **solamente con autorización individual y PIN del propietario**. No se descargan servidores ni se conceden accesos automáticamente.

Referencias auditadas: Filesystem, Playwright, GitHub, Notion, Tavily, Mem0, ClickHouse, Google News y otras. Algunos enlaces son editores o asistentes (Claude Code, Cursor, Windsurf, Cline, Continue, LibreChat, Chainlit, Cherry Studio y NextChat), **no servidores que reemplacen el HUD**. Los proyectos archivados o no oficiales se documentan sin instalarse.

**Configuración:** `requirements_mcp_optional.txt`, `~/.neuralt/mcp-servers.json`, `SKY_MCP_ENABLED=1` y una allowlist de herramientas. La API privada expone `/api/sky/mcp/catalogue`, `/discover`, `/prepare` y `/execute`. GitHub se fuerza a solo lectura y Filesystem exige una carpeta restringida.

[Guía y auditoría completa de integraciones MCP](docs/api/SKY_MCP_HUB_INTEGRACIONES_2026.md).

**Estado:** puente MCP desarrollado, desactivado por defecto; la instalación y autenticación de cada servidor requieren acciones explícitas en tu PC. No es un IDE autónomo ilimitado.

## 🔬 SKY Verification Lab — seguimiento de las seis prioridades

Tras revisar el video sobre skills, subagentes, conectores, seguridad y memoria, se añadió una capa **de verificación no intrusiva** sobre la API actual:

- **Inventario honesto:** subagentes y skills propios, estado de preparación de GitHub/Supabase/Vercel y ausencia de cliente MCP general confirmado.
- **Pruebas de entorno:** señales de disponibilidad de Ollama, Piper y paquetes de voz; sin afirmar pruebas físicas de micrófono ni ejecución en Windows.
- **Evidencia y citas:** lectura digital de PDF con hash SHA256 y páginas reales, DOCX/texto sin páginas inventadas y localización de citas con revisión humana.
- **Evaluación formativa privada:** criterios y preguntas para revisión docente sin almacenar ni calificar automáticamente respuestas.
- **KPIs reales:** aprovechamiento de la telemetría de SKY, con valores nulos cuando no se registraron muestras.
- **Vista previa de orquestación:** consulta de roles y skills antes de delegar, **sin ejecutar herramientas ni crear permisos**.

Entrá a `GET /api/sky/verification/capabilities` con tus credenciales del dueño. Guía detallada: [SKY Verification Lab y validación en Windows](docs/api/SKY_VERIFICATION_LAB_VIDEO_PRIORIDADES.md).

**Pendiente:** conexión MCP conforme al protocolo oficial y ensayos completos de voz, Ollama, agentes, permisos y hardware en tu computadora. Los chequeos automáticos no sustituyen esas pruebas.

## 🌐 SKY GLOBAL — comprobaciones reales e inclusión

SKY incorporó un informe privado de preparación internacional en
`GET /api/sky/global/readiness`, integrado al botón **DIAG**. Comprueba
el arranque público, la disponibilidad efectiva de Redis y la cobertura de
etiquetas traducidas; también muestra pruebas de seguridad, accesibilidad,
rendimiento, protección de datos y despliegue internacional que aún **no han
sido acreditadas**. La API no expone secretos y no altera los servicios actuales.

El HUD principal incorpora cambio de idioma para las etiquetas revisadas,
acceso con teclado, anuncios de estado y reducción voluntaria del movimiento.
No debe confundirse la interfaz parcialmente traducida con conversación o voz
validada en todos los idiomas.

[Guía operativa, pruebas y requisitos de SKY GLOBAL](docs/api/SKY_GLOBAL_READINESS.md).

## 🗺️ Prioridades siguientes

- Validar voz, Ollama, Piper, permisos y acciones reales en el equipo Windows de destino.
- Armonizar las autorizaciones entre HUD, agente, memoria, dispositivos y herramientas especializadas.
- Extender la investigación a documentos completos, citas por página, contrastación y verificación de afirmaciones.
- Desarrollar evaluaciones didácticas confiables con protección de datos de estudiantes.
- Ampliar conectores oficiales y dispositivos compatibles mediante autorización explícita.
- Mejorar KPIs de tareas completadas, fiabilidad, latencia y costos sin inventar resultados.

## 📚 Documentación

| Referencia | Contenido |
| --- | --- |
| [Inicio v12](README_V12_INICIO.md) | Instalación, voz y uso |
| [Estado real de capacidades](docs/ESTADO_REAL_SKY.md) | Funciones, requisitos y limitaciones (incluye estado histórico v12.5) |
| [Auditoría v12.6](docs/AUDITORIA_V12_6.md) | Hallazgos con evidencia, correcciones, pruebas y pendientes en Windows |
| [Windows v12.6 (PowerShell)](docs/guias/SKY_WINDOWS_V12_6.md) | PIN, arranque único, estado, detener e inicio automático; cómo volver atrás |
| [Hermes Agent como consultor](docs/guias/SKY_HERMES.md) | Instalar Hermes, dejarlo sin herramientas que actúen y preguntarle desde SKY |
| [YouTube oficial en SKY](docs/guias/SKY_YOUTUBE_OFICIAL.md) | Data API v3, clave local, incrustación permitida, errores 100/101/150/153, restricciones y controles del reproductor |
| [Arquitectura](docs/api/ARQUITECTURA_SKY.md) | Diseño y evolución del sistema |
| [SKY Aula](docs/api/SKY_AULA_INNOVACION_INVESTIGACION.md) | Enseñanza, innovación y API |
| [SKY Impacto / Scholar](docs/guias/SKY_IMPACTO_EDUCACION_INNOVACION.md) | Investigación académica, fuentes y skills |
| [SKY Guardian](docs/api/SKY_GUARDIAN_NICARAGUA.md) | Alertas e inventario consentido |
| [Conectividad](docs/api/SKY_SECURE_CONNECTIVITY.md) | Dispositivos, Wi-Fi, Bluetooth e IR |
| [Multimodal](docs/api/SKY_MULTIMODAL_WEB_PRODUCCION_SEGURA.md) | Documentos, imágenes, audio y video |
| [API del asistente](docs/api/SKY_ASISTENTE_PERSONAL_API.md) | Mensajes, acciones y permisos |
| [SKY SENTINEL](docs/seguridad/SENTINEL_FASES_1_2.md) | Seguridad y modelo de amenazas |
| [Guías de versiones](docs/guias/) y [changelogs](docs/changelogs/) | Registro histórico |

> Algunas guías conservan el estado de la rama donde fueron redactadas. Para conocer la situación actual consultá `main`, `VERSION.txt`, el código y las pruebas.

## 👤 Autoría y licencia

**Visión y autoría conceptual:** Oscar Elieser Chamorro Guzmán. [Expediente de autoría](docs/guias/AUTORIA_SKY_IA_Oscar_Elieser_Chamorro_Guzman.md).

Este repositorio público no contiene actualmente un archivo `LICENSE` en su raíz. Publicarlo en GitHub **no concede automáticamente una licencia general de reutilización**; consultá al titular antes de redistribuirlo. Los modelos, bibliotecas y APIs de terceros mantienen sus respectivas condiciones.

---

**SKY IA — Un solo núcleo, múltiples capacidades y resultados verificables.**

## Núcleo reflexivo de SKY — recuperación, pruebas y corrección segura (2026-10-30)

SKY utiliza `neural_core/sky_reflective_core.py` para registrar **resultados categorizados de las pruebas de habilidades** y recuperar recomendaciones antes de generar otras propuestas. El ciclo de `sky_skill_builder.proponer()` está limitado a tres intentos con detección de código repetido; las habilidades sólo pueden instalarse mediante la aprobación preexistente del propietario y después de superar nuevamente las pruebas.

La opción `SKY_REFLECTIVE_SEMANTIC=1` activa recuperación por embeddings de categorías estáticas mediante un modelo Ollama **local** (`nomic-embed-text`), con fallback determinista cuando no esté disponible. La memoria local no guarda prompts, código generado ni stack traces. Las estadísticas son de pruebas, **no** pruebas de acciones reales sobre Android/Windows, ni entrenamiento automático del modelo.

Detalles, requisitos y comandos de prueba: [docs/SKY_REFLECTIVE_CORE.md](docs/SKY_REFLECTIVE_CORE.md).

## Calidad multiagente y reparación de síntesis (2026-10-30)

SKY añade revisión consultiva en `neural_core/sky_multiagent_quality.py`: integra lecciones categóricas y anónimas de pruebas anteriores en la planificación de especialistas; comprueba algunas afirmaciones falsas de acciones realizadas y permite **una** nueva síntesis antes de devolver el control al asistente original. No instala software, no concede permisos ni equivale a verificación factual. Se conserva el único núcleo `sky_unified_agents`, con métricas y ruta autenticada `/api/sky/cognition/multiagent-quality`.

Detalle: [docs/SKY_MULTIAGENT_QUALITY_GATE.md](docs/SKY_MULTIAGENT_QUALITY_GATE.md).

### Windows: seguridad de arranque y reparación de regresiones PR52 (30/10/2026)

La reparación conservadora impide un segundo supervisor cuando la API de SKY ya responde, rechaza puertos ajenos sin cerrar servicios, normaliza los puntos de inserción para archivos CRLF de Windows y conserva pruebas de rechazo de cambios no seguros. Los reparadores siguen exigiendo aprobación explícita para aplicar cambios. Evidencia, alcance y límites: [docs/SKY_WINDOWS_PR52_REGRESSION_REPAIR.md](docs/SKY_WINDOWS_PR52_REGRESSION_REPAIR.md).
