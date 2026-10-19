# SKY IA v10.8 — Operación privada y recuperación comprobable

**Visión y autoría conceptual:** Oscar Elieser Chamorro Guzmán.

## 1. Instalar y arrancar sin exposición pública

SKY v10.8 conserva los módulos de v10.7, la portada minimalista y los permisos del creador sobre BAQUEANO. Primero instalá `python -m pip install -r requirements_studio.txt -r requirements_production.txt pytest` y asegurá FFmpeg/FFprobe. Iniciá localmente con `python -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765`. No abras ese puerto a Internet sin un entorno de producción auditado.

## 2. Programar respaldos reales (no desde HTTP)

El administrador decide cuándo correr `scripts.backup_operations_v108`. **No se inicia automáticamente al arrancar SKY**. Prepará una ruta fuera del proyecto, por ejemplo `/var/backups/sky`, permisos `0700`, y una contraseña privada en `/etc/sky/private/backup-passphrase` con permisos `0600` (propietario correcto). La clave no debe ir a GitHub, al ZIP o a un comando shell visible.

```bash
export SKY_BACKUP_PASSPHRASE_FILE=/etc/sky/private/backup-passphrase
python -m scripts.backup_operations_v108 once --directory /var/backups/sky --keep 7
python -m scripts.backup_operations_v108 rehearse --directory /var/backups/sky --rpo-hours 48
```

Cada ejecución crea una copia cifrada de las bases de SKY y los medios privados que el proyecto gestiona, verifica SQLite/SHA-256, y solamente entonces rota archivos con nombres administrados. Nunca elimina archivos con otro nombre ni backups cuya autenticidad no pueda validar. Retención configurable entre 2 y 90. La restauración se prueba fuera de la carpeta original y reporta segundos transcurridos y edad estimada de la copia.

**Advertencia:** no respalda servidores completos, secretos, modelos locales, DNS, certificados TLS o servicios externos. Guardá la clave de cifrado por separado en un gestor de secretos, con estrategia fuera del servidor. Una carpeta local de backup no protege frente a pérdida de la máquina.

### Ejecución periódica (Linux/systemd)

Los ejemplos `deploy/systemd/sky-backup.service` y `deploy/systemd/sky-backup.timer` deben ser adaptados a rutas y permisos reales antes de instalarse. Verificá que el usuario `sky` pueda leer las bases y medios y escribir en el directorio de respaldo. El timer es diario; su ejecución requiere que un operador lo habilite. **No hay timer habilitado automáticamente**.

## 3. Aislamiento de contenedores

```bash
python -m scripts.container_preflight_v108
```

Este comando audita únicamente la configuración YAML y el estado de instalación de Docker. Si existe un Docker operativo, se puede ejecutar una prueba aislada **solo tras construir la imagen localmente**, sin puertos ni red:

```bash
docker build -f deploy/Dockerfile -t sky-ci:v10.8 .
export SKY_SMOKE_IMAGE=sky-ci:v10.8
python -m scripts.container_preflight_v108 --runtime
```

Ninguno de esos comandos levanta la plataforma pública ni comprueba certificados TLS, Redis auténtico o firewall. El workflow de GitHub propone un build y un test aislado; su aprobación efectiva debe consultarse en la pestaña Actions.

## 4. Reconocimiento de voz en al menos dos idiomas

SKY **no incluye** pesos Whisper ni descarga archivos automáticamente. Para una prueba real instalá `faster-whisper` y un modelo CTranslate2 local confiable. Indicá su ubicación con `SKY_STT_MODEL_DIR` y prepará dos WAV reales en `samples/` (cada uno hasta 60 segundos), además de un manifiesto JSON local:

```json
[
  {"file":"spanish.wav","language":"es","reference":"frase realmente pronunciada"},
  {"file":"french.wav","language":"fr","reference":"phrase réellement prononcée"}
]
```

```bash
export SKY_STT_MODEL_DIR=/ruta/a/modelo/ctranslate2
python -m scripts.benchmark_voice_multilingual_v108 --manifest samples.json --audio-dir samples --threshold 0.35
```

El informe contiene WER por idioma y hashes del audio, **no las transcripciones originales**. No hay evidencia de calidad hasta ejecutar realmente el modelo. En ausencia del modelo devuelve un estado explícito de no ejecución.

## 5. Ampliación de idiomas

Se incorporan 18 etiquetas operativas revisadas para inglés, portugués, francés, alemán, italiano, árabe, chino, japonés y suajili. Los demás idiomas conservan el comportamiento de fallback explícito. El catálogo global de idiomas y traducción de contenido dinámico no equivale a todas las pantallas traducidas.

## 6. Validación y publicación

- `python -m pytest -q` — prueba de regresión completa.
- `python scripts/security_audit_v103.py .` — búsqueda local heurística de patrones de secretos, no un pentest.
- `python -m scripts.container_preflight_v108` — configuración, **no Docker real**.
- `python -m scripts.backup_operations_v108 rehearse --directory ...` — recuperación real dentro de una carpeta temporal, **no recuperación de un centro de datos**.

El despliegue mundial continúa pendiente de revisión de dependencias, ejecución de contenedores, gestión de claves, pruebas de carga y auditoría externa independiente. BAQUEANO no se modificó.
