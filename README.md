# 🌌 SKY IA — Universal v12.3 | HUD · Asistente Personal

**Visión y autoría conceptual:** Oscar Elieser Chamorro Guzmán.

Plataforma tecnológica personal con una **interfaz HUD** y un **asistente personal que controla tu equipo, tu casa y tus apps con tu autorización** (voz local, Ollama 100 % local, Home Assistant, ventanas, música, documentos), asistencia multi-IA privada, metaverso 3D, flujos de trabajo autónomos, estudio creativo de video/animación, generación de documentos de oficina (Word, Excel, PowerPoint, PDF) y agente de dispositivos locales.

---

## ⚡ Inicio Rápido (Windows)

**Primera vez:** doble clic en `INSTALAR_SKY_WINDOWS.bat` (instala Python, librerías, Ollama y su modelo, la voz natural Piper y la escucha local). Guía completa: [README_V12_INICIO.md](README_V12_INICIO.md).

Para iniciar cualquier componente de SKY, ejecuta el menú interactivo unificado:
```cmd
SKY_INICIAR.bat
```
Desde este panel podrás elegir fácilmente:
0. **🆕 SKY completo (HUD):** [http://127.0.0.1:8765/](http://127.0.0.1:8765/) — agente + API + voz + interfaz en un clic. Guía: [README_V12_INICIO.md](README_V12_INICIO.md)
1. **Interfaz clásica y API:** [http://127.0.0.1:8765/sky](http://127.0.0.1:8765/sky)
2. **Panel General Streamlit:** [http://127.0.0.1:8501](http://127.0.0.1:8501)
3. **Estudio Creativo de Video:** [http://127.0.0.1:8765/creative](http://127.0.0.1:8765/creative)
4. **Office Studio (Documentos):** [http://127.0.0.1:8765/office](http://127.0.0.1:8765/office)
5. **Agente del equipo:** `agente_dispositivo.py` (puerto 8766; permisos con `--perfil basico|multimedia|completo`, u opción 6 del menú)
   · **Intérprete de código:** opción I (`sky_interprete.py`, Open Interpreter con confirmación de cada paso)
6. **Diagnóstico del Motor:** `sky_preflight.py`
7. **Diagnóstico y pruebas:** `python sky_diagnostico.py` · más de 600 tests en `pytest`

---

## 🛰️ SKY v12.3 — HUD y Asistente Personal

- **WhatsApp:** hablale a SKY desde tu celular (API oficial de Meta), con texto o notas de voz; confirma lo sensible con un código. Guía: [docs/guias/SKY_WHATSAPP.md](docs/guias/SKY_WHATSAPP.md)
- **Skills y tareas programadas por voz:** "todos los días a las 8 prepara las respuestas de los correos". **Perfil USER.md** que SKY lee en cada respuesta.
- **Cerebro con herramientas también con Claude, GPT o Gemini**, y **SKY 24/7** con reinicio automático. Novedades: [CHANGELOG_V12_3.md](CHANGELOG_V12_3.md)

- **Aprende sola:** las frases nuevas que salen bien se vuelven atajos instantáneos; le podés enseñar órdenes, contarle datos tuyos y corregirla. Todo se puede revisar, exportar y borrar.
- **Se alimenta de internet:** "aprende sobre…" (Wikipedia y noticias, con fuentes) y "sigue el tema…" con novedades diarias. `SKY_INTERNET=0` lo apaga.
- **KPIs reales:** mide cada petición, mensaje y acción; detecta problemas sola y responde "¿qué está fallando?" con evidencia. Panel de rendimiento a pedido. Novedades: [CHANGELOG_V12_2.md](CHANGELOG_V12_2.md) · Estado real: [docs/ESTADO_REAL_SKY.md](docs/ESTADO_REAL_SKY.md)
- **Parada de emergencia** ("SKY, para todo") y niveles de riesgo 1–3 en cada acción.

- **Entiende a la primera:** las órdenes conocidas se resuelven al instante, y las demás las interpreta un **cerebro local con herramientas** (Ollama), que también entiende referencias como "más fuerte" o "cerralo".
- **Voz fluida:** empieza a hablar con la primera frase, con voz natural **Piper** local y escucha continua **"SKY…"** transcrita en tu PC.
- **Agenda:** recordatorios, alarmas y rutinas ("buenos días"); avisos en el HUD, en el escritorio y en el celular.
- **Mensajes:** leer y responder correo con tu confirmación, WhatsApp con el mensaje ya escrito, y contactos.
- **Instalador único** y **diagnóstico** (botón DIAG) que dice cómo arreglar lo que falte. Novedades: [CHANGELOG_V12_1.md](CHANGELOG_V12_1.md)

Hablale o escribile a SKY desde el **núcleo holográfico**: *"reproduce Bad Bunny en Spotify"*, *"pon el video en pantalla completa"*, *"organiza las ventanas"*, *"abre mis documentos"*, *"crea una nota agenda que diga…"*, *"prepara una presentación sobre…"*, *"enciende la luz de la sala"*, *"toma una captura"*. Todo lo demás lo responde la IA (100 % local con Ollama y `SKY_LOCAL_ONLY=1`).

Todos los módulos (clásico, Creative, Office, Flujos, Metaverso, Studio 3D, Comunidad, reproductor) se abren **dentro** del HUD como ventanas holográficas.

Vos decidís qué controla SKY en tu PC (la política vive sólo ahí):

```bash
python agente_dispositivo.py --perfil completo --carpeta ~/Música --carpeta ~/Documentos
python agente_dispositivo.py --ver-politica
```

SKY no ejecuta comandos de shell desde la voz ni el HUD, no abre programas o scripts como archivos, no sale de tus carpetas, no instala nada ni paga. Para automatizar con código está el **Intérprete** (opción I), que muestra cada paso antes de ejecutarlo. Detalles: [CHANGELOG_V12_0.md](CHANGELOG_V12_0.md) · API: [docs/api/SKY_ASISTENTE_PERSONAL_API.md](docs/api/SKY_ASISTENTE_PERSONAL_API.md)

---

## 📁 Estructura del Proyecto

```text
SKY/
├── SKY_INICIAR.bat        # Lanzador central interactivo para Windows
├── app.py                 # Panel de control Streamlit (puerto 8501)
├── requirements.txt       # Dependencias principales del proyecto
├── .env                   # Variables de entorno y llaves de acceso local
├── metaverse/             # Motor FastAPI, WebSockets y vistas web del metaverso
├── neural_core/           # Núcleo de inteligencia, 3D, oficina, flujos y video
├── tests/                 # Suite de pruebas automatizadas (199 tests aprobados)
├── local_data/            # Bases de datos SQLite locales y token de autenticación
└── docs/                  # Documentación organizada
    ├── guias/             # Manuales de inicio y validaciones por versión
    ├── changelogs/        # Registro de cambios (v9.0 a v10.2)
    ├── api/               # Especificaciones de arquitectura y APIs
    ├── manifiestos/       # Manifiestos de integridad y hashes SHA-256
    ├── legal/             # Documentos de autoría y propiedad conceptual
    └── capturas/          # Capturas de pantalla e imágenes de muestra
```

---

## 📚 Documentación

* **Guías de versiones:** [docs/guias/](docs/guias/)
* **Historial de cambios:** [docs/changelogs/](docs/changelogs/)
* **Especificaciones de APIs:** [docs/api/](docs/api/)
* **Manifiestos SHA256:** [docs/manifiestos/](docs/manifiestos/)
* **Expediente de Autoría:** [docs/legal/](docs/legal/)
