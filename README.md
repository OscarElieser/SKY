# 🌌 SKY IA — Universal v11.1 | Asistente Personal

**Visión y autoría conceptual:** Oscar Elieser Chamorro Guzmán.

Plataforma tecnológica personal que integra un **asistente personal que controla tu equipo con tu autorización** (música, volumen, apps, archivos, capturas, voz), asistencia multi-IA privada, metaverso 3D, flujos de trabajo autónomos, estudio creativo de video/animación, generación de documentos de oficina (Word, Excel, PowerPoint, PDF) y agente de dispositivos locales.

---

## ⚡ Inicio Rápido (Windows)

Para iniciar cualquier componente de SKY, ejecuta el menú interactivo unificado:
```cmd
SKY_INICIAR.bat
```
Desde este panel podrás elegir fácilmente:
0. **🆕 Asistente Personal SKY:** [http://127.0.0.1:8765/asistente](http://127.0.0.1:8765/asistente) — agente + API + panel con voz en un clic. Guía: [README_V11_1_INICIO.md](README_V11_1_INICIO.md)
1. **Metaverso y API:** [http://127.0.0.1:8765/sky](http://127.0.0.1:8765/sky)
2. **Panel General Streamlit:** [http://127.0.0.1:8501](http://127.0.0.1:8501)
3. **Estudio Creativo de Video:** [http://127.0.0.1:8765/creative](http://127.0.0.1:8765/creative)
4. **Office Studio (Documentos):** [http://127.0.0.1:8765/office](http://127.0.0.1:8765/office)
5. **Agente de Dispositivo Local:** `agente_dispositivo.py` (puerto 8766; permisos con `--perfil basico|multimedia|completo`, u opción 9 del menú)
6. **Diagnóstico del Motor:** `sky_preflight.py`
7. **Suite de Pruebas Automatizadas:** 199 tests en `pytest`

---

## 🗣️ Asistente Personal (v11.1)

Decile a SKY, por texto o voz: *"reproduce Bad Bunny en Spotify"*, *"sube el volumen"*, *"pausa la música"*, *"abre WhatsApp"*, *"abre mis documentos"*, *"toma una captura"*, *"bloquea la pantalla"*. Todo lo demás lo responde la IA que configures.

Vos decidís qué puede hacer en tu PC (la política vive sólo ahí):

```bash
python agente_dispositivo.py --perfil completo --carpeta ~/Música --carpeta ~/Documentos
python agente_dispositivo.py --ver-politica
```

SKY nunca ejecuta comandos de shell, nunca abre programas o scripts, no sale de tus carpetas autorizadas, no instala nada ni paga. Detalles: [CHANGELOG_V11_1.md](CHANGELOG_V11_1.md) · API: [docs/api/SKY_ASISTENTE_PERSONAL_API.md](docs/api/SKY_ASISTENTE_PERSONAL_API.md)

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
