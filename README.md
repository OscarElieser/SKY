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


## 📱 SKY Android — Aura Premium 0.7.1 (independiente de Windows)

**Versión móvil publicada:** `0.7.1` · **Estado:** beta personal, compilación Android y firma verificadas en GitHub Actions; las funciones de voz, visualización y acciones locales deben probarse en el teléfono real.

**[⬇ Descargar SKY Android 0.7.1 (APK firmada)](https://github.com/OscarElieser/SKY/releases/download/sky-android-v0.7.1/SKY-IA-Android-v0.7.1-firmada.apk)** · [Página de la versión](https://github.com/OscarElieser/SKY/releases/tag/sky-android-v0.7.1) · [Notas e instalación Android](mobile/android-agent/README.md) · [Guía de APK y verificación](mobile/android-agent/apk/README.md)

La app Android vive en [`mobile/android-agent/`](mobile/android-agent/), tiene su propio código Kotlin y **funciona sin SKY Windows, sin Tailscale y sin emparejamiento** para la conversación mediante Gemini. Windows se mantiene como conexión **opcional** y no se inicia, modifica ni configura al utilizar el modo móvil independiente.

### Experiencia móvil integrada

- **SKY Aura Premium:** rostro vertical animado, ojos expresivos, gestos táctiles, brillo suave y estados visuales de escuchar, pensar, hablar y error.
- **Conversación natural por turnos:** dictado del reconocimiento de voz de Android y respuestas reproducidas por TextToSpeech; se prefiere una voz española instalada de mejor calidad cuando existe. No equivale a voz neuronal propia.
- **Rostro a la vista:** una conversación iniciada por voz no abre automáticamente el panel de texto; el historial escrito permanece disponible al solicitarlo.
- **Modo fluido opcional:** hasta ocho turnos consecutivos en **primer plano**, con micrófono autorizado y parada manual. No constituye escucha continua oculta ni control en segundo plano.
- **Acciones locales supervisadas:** abrir apps compatibles, notas, alarmas, temporizadores, modo acompañante, chistes y otras órdenes implementadas según permisos reales. No concede control universal de cualquier aplicación.
- **IA por internet sin PC:** configuración de una clave personal de Gemini desde Ajustes para beta privada; SKY valida su acceso y la almacena cifrada con Android Keystore. No insertar ni enviar claves en GitHub, capturas, incidencias o chats.

**Instalación:** abrir el enlace de la APK en Chrome desde Android, descargarla de GitHub Releases e instalarla encima de la anterior **solo si conserva el mismo certificado de firma**; no desinstalar sin respaldar los datos. Si Google Play Protect muestra una alerta de riesgo, **no forzar la instalación** y documentar el aviso. La beta no está certificada por Google Play.

**Privacidad:** aunque Android Keystore cifra la clave en reposo, una clave API dentro de un cliente móvil no ofrece seguridad suficiente para una distribución pública. Antes del lanzamiento general será necesario un backend autenticado, control de cuota y medidas contra abuso. La app necesita internet para responder con Gemini; las acciones puramente locales pueden funcionar sin él.

**Publicación y pruebas:** [SKY Android Signed Release Candidate](.github/workflows/sky-mobile-release.yml) compila, verifica firma/manifest, genera SHA-256 y publica las versiones aprobadas en [GitHub Releases](https://github.com/OscarElieser/SKY/releases). El workflow [SKY Mobile Android Agent](.github/workflows/sky-mobile-agent.yml) mantiene pruebas de desarrollo. Las APK no se almacenan como binarios en el árbol de código.

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
