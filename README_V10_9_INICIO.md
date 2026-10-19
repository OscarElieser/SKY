# SKY IA v10.9 — Instalación y verificación integral

**Visión y autoría conceptual:** Oscar Elieser Chamorro Guzmán.

La versión 10.9 conserva las versiones anteriores, los módulos de imágenes/video y la portada minimalista. No modifica BAQUEANO en producción.

## 1. Inicio local

Desde la raíz del ZIP extraído instalá Python 3.11+, FFmpeg y las dependencias:

```bash
python -m pip install -r requirements_studio.txt -r requirements_production.txt
python -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765
```

La dirección predeterminada debe continuar siendo `127.0.0.1`, no una IP pública.

## 2. Comprobar el conjunto Docker + Redis + HTTPS (solo CI efímero)

```bash
python -m scripts.audit_stack_v109
# En un runner Ubuntu nuevo, Docker instalado y ningún deploy/secrets preexistente:
docker build --pull -f deploy/Dockerfile -t sky-v109:local .
SKY_SMOKE_IMAGE=sky-v109:local bash scripts/ci_stack_smoke_v109.sh
```

El script falla si ya existe una carpeta de secretos o el archivo temporal de CA. Crea secretos aleatorios locales únicamente para el ensayo y elimina sus recursos al terminar. Arranca cuatro contenedores; el proxy HTTPS se liga solo a `127.0.0.1:18443` y usa CA de pruebas con validación de cadena, no `curl -k`. Se comprueba Redis, API y renderizador sin ruta de red. **No ejecutés esto sobre una instalación real ni sin revisar los permisos.**

GitHub Actions ejecuta este control sobre un runner temporal. La aprobación real de cada job debe consultarse en la página de Actions del repositorio; el código estático por sí solo no confirma el resultado.

## 3. Restaurar un respaldo cifrado en otro servidor, manualmente

El operador debe copiar el archivo `.skybackup` **cifrado** a un equipo separado a través de un canal autenticado; debe recibir la huella SHA-256 por un canal confiable y disponer de la contraseña fuera del backup. En el servidor de destino:

```bash
# Copiá el archivo cifrado y la clave privada a rutas controladas.
chmod 600 /srv/sky-private/backup-key
python -m scripts.cross_host_recovery_v109 restore \
  --file /srv/import/sky-backup.skybackup \
  --expected-sha256 HUELLASHA256DE64CARACTERES \
  --key-file /srv/sky-private/backup-key \
  --destination /srv/sky-restored/new-install
```

El destino **no debe existir**; la restauración no reemplaza proyectos, bases o medios activos. Validá los datos y las políticas de acceso antes de una migración. No se trasladan claves ni certificados mediante el respaldo.

Para verificar el mecanismo sin usar datos reales:

```bash
# En CI, el contenedor receptor es independiente, sin red ni acceso a datos vivos.
SKY_SMOKE_IMAGE=sky-v109:local bash scripts/ci_cross_container_v109.sh
```

**Importante:** ese ensayo en contenedor independiente no equivale a una restauración completada en otro servidor físico de tu propiedad.

## 4. Comprobar reconocimiento de voz auténtico

El workflow `.github/workflows/sky-v109-stack-and-recovery.yml` define un job de voz que instala `faster-whisper`, obtiene un modelo público `Systran/faster-whisper-tiny` **solo en el runner** y genera tres muestras sintéticas con eSpeak-ng en ES/FR/EN. Ejecuta el cálculo WER existente, que usa el modelo **real**, no una simulación. Las grabaciones, los pesos y las transcripciones no se suben al repositorio; se intenta guardar únicamente métricas. Un fallo de modelo/precisión se registra como fallo, no como validación superada.

Para audio propio, seguí el procedimiento del `README_V10_8_INICIO.md`, utilizando archivos con permiso de las personas grabadas y modelos locales previamente auditados. No enviés grabaciones privadas a proveedores sin autorización explícita.

## 5. Pruebas locales

```bash
python -m scripts.audit_stack_v109
python -m pytest -q tests/test_sky_v10_9_stack.py
python scripts/security_audit_v103.py .
```

La suite completa de SKY se ejecuta en tres grupos en GitHub Actions para evitar bloqueos de salida detectados en pruebas multimedia del entorno local. El README y la documentación de versiones anteriores se conservan.

**Pendientes:** servidor externo de recuperación, DNS/TLS público, carga concurrente real, pentest independiente y evaluación de voz natural multilingüe. Sin esas comprobaciones no se considera certificado para producción mundial.

## 7. Hallazgos de integración en GitHub Actions

Consultá `INCIDENCIAS_CI_V10_9.md` para los resultados de los trabajos Docker/TLS/Redis, regresión y Whisper real. El ensayo inicial detectó dependencias faltantes y un HEALTHCHECK de renderizador incorrecto, ya corregidos en el código. La calidad del modelo pequeño en español quedó por encima del umbral de errores y no debe presentarse como aprobada.
