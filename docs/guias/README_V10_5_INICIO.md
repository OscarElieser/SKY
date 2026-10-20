# Iniciar SKY IA v10.5 — Global Continuity & Secure Recovery

**Visión y autoría conceptual:** Oscar Elieser Chamorro Guzmán.

SKY v10.5 conserva las funciones de v10.4: proyectos, automatizaciones supervisadas, Office Studio, metaverso, multimedia, comunidad, Multi-IA y panel minimalista. BAQUEANO solo se muestra al creador que supera la autenticación administrativa.

## Instalación segura

1. Extraé este ZIP en una carpeta nueva, sin sobrescribir v10.4.
2. Tené Python 3.11 o superior. Creá un entorno virtual e instalá `pip install -r requirements.txt -r requirements_studio.txt`.
3. Para multimedia instalá FFmpeg y FFprobe. En Windows asegurá que estén disponibles en PATH.
4. Conservá en privado tu `.env`, los datos de `local_data`, los tokens y el secreto MFA. **No los añadas a Git.**
5. Ejecutá `INICIAR_SKY_V9_WINDOWS.bat` o `python -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765`. No expongas `0.0.0.0` a Internet sin la infraestructura segura descrita en `SEGURIDAD_V10_5.md`.
6. Entrá en `http://127.0.0.1:8765/sky` y abrí Espacios solo cuando necesités herramientas especializadas.

## Transcripción de voz local (opcional)

- `faster-whisper` **no viene instalado** en la distribución y no se descarga automáticamente ningún modelo.
- Instalá el paquete de forma explícita: `pip install 'faster-whisper>=1.1,<2'`.
- Instalá un modelo CTranslate2 compatible en tu computadora según sus licencias y definí `SKY_STT_MODEL_DIR` con la carpeta local que contiene `model.bin` y `config.json`.
- En Espacios → Creative Studio → Video → «Reconocimiento de voz local» comprobá disponibilidad; luego seleccioná el audio para transcribir. Se permite un máximo de 60 segundos y 10 MB. Revisá siempre el texto resultante.
- La API autenticada incluye `GET /api/global-media/stt/capabilities` y `POST /api/global-media/stt/transcribe` (multipart `file`, `language` opcional).
- Nunca se envía audio al exterior por esta función. La precisión depende del modelo, idioma y grabación. **La prueba con un modelo real sigue pendiente de instalación y validación.**

## Respaldo cifrado de bases y medios

Con SKY apagado para una prueba completa y una contraseña fuerte almacenada de forma segura, usá:

```bash
export SKY_BACKUP_PASSPHRASE='TU-FRASE-SECRETA-LARGA-DE-EJEMPLO'
python -m neural_core.sky_recovery_full create --file /carpeta-segura/sky-v105.skybackup
python -m neural_core.sky_recovery_full verify --file /carpeta-segura/sky-v105.skybackup
python -m neural_core.sky_recovery_full restore --file /carpeta-segura/sky-v105.skybackup --destination /carpeta-nueva/sky-recuperado
```

Usá rutas y sintaxis equivalentes en Windows. Se verifica el contenido cifrado y se restaura **solo fuera de la instalación actual**. La colección actual es la biblioteca gestionada por Creative Studio; no reemplaza un plan integral de copia de todos los archivos y secretos autorizados.

## Pruebas

`PYTHONPATH=. pytest -q` comprueba código, API, motores heredados y la nueva recuperación.

Para comprobar sintaxis JavaScript: `node --check metaverse/static/creative.js`.

## Seguridad y limitaciones

No hay auditoría externa ni despliegue público certificado. Los idiomas del selector no equivalen a traducciones completas; SKY publica una auditoría de cobertura real por interfaz. Gemini y otros proveedores siguen requiriendo credenciales propias, consentimiento y validación independiente.

Documentación: `CHANGELOG_V10_5.md`, `SEGURIDAD_V10_5.md`, `VALIDACION_V10_5.md`.
