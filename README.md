# 🌌 SKY IA — Universal v10.2 | Global Intelligence

**Visión y autoría conceptual:** Oscar Elieser Chamorro Guzmán.

Plataforma tecnológica personal que integra asistencia multi-IA privada, metaverso 3D, flujos de trabajo autónomos, estudio creativo de video/animación, generación de documentos de oficina (Word, Excel, PowerPoint, PDF) y agente de dispositivos locales.

---

## ⚡ Inicio Rápido (Windows)

Para iniciar cualquier componente de SKY, ejecuta el menú interactivo unificado:
```cmd
SKY_INICIAR.bat
```
Desde este panel podrás elegir fácilmente:
1. **Metaverso y API:** [http://127.0.0.1:8765/sky](http://127.0.0.1:8765/sky)
2. **Panel General Streamlit:** [http://127.0.0.1:8501](http://127.0.0.1:8501)
3. **Estudio Creativo de Video:** [http://127.0.0.1:8765/creative](http://127.0.0.1:8765/creative)
4. **Office Studio (Documentos):** [http://127.0.0.1:8765/office](http://127.0.0.1:8765/office)
5. **Agente de Dispositivo Local:** `agente_dispositivo.py`
6. **Diagnóstico del Motor:** `sky_preflight.py`
7. **Suite de Pruebas Automatizadas:** 199 tests en `pytest`

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
