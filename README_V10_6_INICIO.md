# SKY IA v10.6 — Instalación, voz y restauración

**Proyecto y dirección conceptual:** Oscar Elieser Chamorro Guzmán.

SKY conserva los módulos de v10.5 y la portada minimalista. BAQUEANO sigue reservado al creador con control en la API. Mantené SKY detrás de `127.0.0.1` mientras falten las protecciones descritas en `SEGURIDAD_V10_6.md`.

## Instalación local

```bash
python -m venv .venv
# activar el entorno virtual correspondiente
python -m pip install -r requirements.txt -r requirements_studio.txt
python -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765
```

Se necesita FFmpeg/FFprobe para el estudio creativo y la preparación de audio. El iniciador de Windows heredado sigue incluido.

## Reconocimiento de voz real (opcional, por el creador)

SKY no contiene pesos de modelos de reconocimiento. Instalá `faster-whisper>=1.1,<2` y un modelo CTranslate2 **desde una fuente que hayas revisado y autorizado**. Configurá `SKY_STT_MODEL_DIR` como una carpeta local con `model.bin` y `config.json`. No se descargan pesos en segundo plano.

`POST /api/global-media/stt/transcribe` exige la clave y la sesión MFA cuando corresponda; prepara y verifica hasta **60 segundos** y **10 MB** de audio y transcribe en otro proceso con un máximo de 100 segundos. El idioma puede seleccionarse o dejarse a detección del motor. El proceso hijo no recibe las claves API del padre. Esto **no es una sandbox del sistema operativo**: en producción debe ejecutar con permisos mínimos dentro de un contenedor o VM aislada.

Para **probar de verdad** un modelo instalado con una grabación de la que conozcás el texto:

```bash
PYTHONPATH=. python -m scripts.validate_local_voice_v106 \
  --audio /ruta/voz-real.wav --language es \
  --expected 'texto pronunciado realmente' --max-wer 0.40
```

El comando reporta WER y termina con fallo cuando el modelo está ausente o la precisión no alcanza el umbral. Los archivos y transcripciones no se publican. Las grabaciones sintéticas o producidas con TTS deben identificarse como tales y no reemplazan una evaluación humana multilingüe.

## Recuperación cifrada

Con `SKY_BACKUP_PASSPHRASE` definido **en una terminal privada o gestor de secretos**, ejecutá:

```bash
PYTHONPATH=. python -m neural_core.sky_recovery_drill_v106
```

Por defecto genera datos sintéticos, cifra, verifica, restaura en una carpeta aislada y comprueba que los datos originales no se alteren. Para verificar las bases y medios admitidos en tu propia instalación, **apagá SKY**, guardá una copia adicional y utilizá `--installed`. El ensayo nunca sobreescribe bases activas. **No incluye archivos arbitrarios del equipo, proveedores externos ni claves secretas.**

## Pruebas

```bash
PYTHONPATH=. pytest -q
node --check metaverse/static/creative.js
python scripts/security_audit_v103.py .
```

Si Windows no admite `PYTHONPATH=.`, podés ejecutar `set PYTHONPATH=.` en CMD o `$env:PYTHONPATH='.'` en PowerShell antes del comando.

## Archivos importantes

- `CHANGELOG_V10_6.md`, `VALIDACION_V10_6.md`, `SEGURIDAD_V10_6.md`.
- `neural_core/sky_stt_isolated_v106.py`, `neural_core/sky_stt_worker_v106.py`, `scripts/validate_local_voice_v106.py`.
- `neural_core/sky_recovery_drill_v106.py`, `neural_core/sky_i18n_v106.py`.

La interfaz permanece simple, y los módulos avanzados están dentro de «Espacios». No se modificó BAQUEANO.
