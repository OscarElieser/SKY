# SKY IA v10.3 — Guía de instalación y actualización

Proyecto desarrollado bajo la visión de **Oscar Elieser Chamorro Guzmán**.

## Primer inicio

1. Crear una carpeta nueva; no sobrescribir los archivos de SKY v10.2. Descomprimir el ZIP íntegro.
2. Instalar Python 3.11+, FFmpeg/FFprobe; eSpeak o eSpeak-NG para voz local.
3. `python -m pip install -r requirements_studio.txt` (o usar el iniciador compatible del sistema operativo).
4. Ejecutar `python -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765`.
5. Abrir `http://127.0.0.1:8765/sky` y elegir idioma; `Espacios` contiene las herramientas avanzadas.
6. En el estudio creativo, `Subtítulos y narración multilingüe` → `Narración local y doblaje sin nube` permite generar WAV y doblar MP4.

### Instalaciones anteriores

Con SKY detenido, respaldar `.env`, `local_data/` y archivos de salida antes de trasladar datos privados. No publicar esas carpetas en GitHub. Nunca copiar el ZIP antiguo sobre el nuevo sin respaldo.

### Ejecución segura

- No ejecutar SKY con `--host 0.0.0.0` ni poner la API directa en Internet. La revisión de seguridad pública sigue pendiente.
- La clave `X-SKY-KEY` debe permanecer privada; configurar el segundo factor del creador siguiendo `SEGURIDAD_V10_2.md`.
- El doblaje local usa eSpeak, genera voz sintética y *reemplaza* el audio del MP4 de salida; el video original no se modifica. Duración máxima 60 segundos por exportación local.
- Para usar un motor de transcripción local opcional, instalar `faster-whisper`, descargar y verificar un modelo mediante los canales oficiales, fijar `SKY_WHISPER_LOCAL_MODEL` a una carpeta local; el endpoint de diagnóstico no descarga nada ni transcribe por sí solo.
- gTTS y Gemini son externos; enviar texto requiere autorización explícita y claves del titular, nunca publicadas en el repositorio.

### Auditorías reproducibles

`PYTHONPATH=. pytest -q`

`python scripts/audit_ui_locales.py`

`python scripts/security_audit_v103.py .`

`node --check metaverse/static/sky-global-i18n.js`

`node --check metaverse/static/creative.js`

**Importante:** los 90 idiomas listados en el selector no constituyen una cobertura total. La auditoría revela las etiquetas traducidas y las faltantes; no se traducen automáticamente datos privados.

## Historial de versiones

Consultar `HISTORIAL_VERSIONES.md` para la lista comprobada y sus sumas SHA-256. El archivo histórico puede transferirse a GitHub usando el script con autenticación propia sin forzar la rama principal.
