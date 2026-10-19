# SKY IA v10.7 — instalación, verificación y seguridad operativa

**Visión y autoría conceptual:** Oscar Elieser Chamorro Guzmán.

## 1. Uso local (opción recomendada para pruebas)

1. Guardá una copia completa de v10.6 y de tus datos privados antes de actualizar. No compartás tu `.env`, claves, `local_data` ni modelos locales.
2. Descomprimí el ZIP de v10.7 en un directorio nuevo.
3. Python 3.11+ y FFmpeg/FFprobe en PATH. Instalá las dependencias según el módulo: `python -m pip install -r requirements_studio.txt` y, para pruebas, `python -m pip install pytest pyyaml`.
4. Iniciá la versión local con `python -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765` (o con el iniciador Windows heredado).
5. Entrá en `http://127.0.0.1:8765/sky`. No redirijás el puerto 8765 a Internet.
6. La portada sigue minimalista, las herramientas están dentro de «Espacios» y BAQUEANO continúa reservado al creador mediante autenticación privada.

## 2. Qué cambia en v10.7

- Lectura de `SKY_API_KEY_FILE` y `SKY_OWNER_MFA_SECRET_FILE`: secretos en archivos privados fuera de Git; usar solo una de las dos modalidades por secreto.
- Base de contenedores opcional en `deploy/`: API sin publicación directa de puertos, renderizador sin red y Redis en red interna detrás de un proxy TLS.
- Guion de aprovisionamiento **local** de claves aleatorias, sin mostrarlas en registros.
- 22 textos estáticos de navegación y edición revisados para inglés, portugués, francés, árabe, chino, japonés y suajili. No se traduce automáticamente información privada.
- Ensayo de recuperación de datos cifrados SQLite + PNG, comprobando contraseña incorrecta y alteración deliberada del archivo, todo en carpetas temporales.
- Auditor opcional de un modelo `faster-whisper` **ya instalado** y un audio de referencia local con tasa WER; si no hay modelo se declara explícitamente la ausencia. No se descargan pesos ni audios.

## 3. Voz local real: instalación opcional

Requiere una máquina que pueda alojar el modelo y `faster-whisper`. No hay modelo incluido ni ensayos de transcripción real certificados en esta entrega.

```bash
python -m pip install 'faster-whisper>=1.1,<2'
export SKY_STT_MODEL_DIR=/ruta/absoluta/a/modelo-ctranslate2
python -m scripts.audit_voice_model_v107
python -m scripts.audit_voice_model_v107 --audio /ruta/local/prueba.wav --reference 'Palabras realmente pronunciadas' --language es
```

El auditor no envía audio a terceros. La última orden devuelve un resumen de conteos, hash del modelo y WER sin imprimir la frase reconocida. **El administrador debe instalar un modelo de fuente confiable y revisar su licencia y hash** antes de utilizarlo.

## 4. Contenedores (referencia de despliegue, NO certificada)

**Requiere Docker Compose moderno y un servidor con DNS/TLS configurados. No se ejecutó Docker en el entorno de desarrollo.** No desplegués sin un profesional que revise permisos de secretos, aislamiento, respaldos, TLS, autenticación, WAF y monitoreo.

```bash
cp deploy/production.env.example deploy/production.env
# Editar dominio público propio en deploy/production.env.
python scripts/provision_secrets_v107.py --directory deploy/secrets
# Asegurar permisos de lectura de los secretos por UID 10001 en los contenedores.
# Para TOTP: leer deploy/secrets/sky_mfa_seed.txt en consola privada,
# registrar manualmente la semilla en el autenticador y borrarla de la pantalla.
docker compose --env-file deploy/production.env -f deploy/compose.yml config --quiet
# Levantar solo DESPUÉS de verificar secretos, dominio, DNS, certificados y protección.
docker compose --env-file deploy/production.env -f deploy/compose.yml up --build -d
```

Docker Compose con secretos basados en ficheros puede conservar permisos originales del host; comprobá que los procesos no-root realmente pueden leer sus propios secretos. Nunca resolvás ese problema subiendo claves a Git o haciéndolas públicas en el host. Las imágenes no están fijadas por digest ni sus dependencias congeladas en un lockfile: es **pendiente de hardening** antes de producción.

### Arquitectura de referencia

`Internet → Caddy HTTPS → SKY API (UID 10001) → Redis autenticado (red interna)`;
`SKY Renderer (UID 10001, network_mode:none) ↔ volumen privado sky_local`.

No se expone el puerto de la API ni de Redis al host; solo 80 y 443 en el proxy. Los flujos autónomos están desactivados en este perfil de despliegue. Redis con política sin persistencia actúa únicamente como control de tasa, **no como base de datos permanente**.

## 5. Recuperación ante desastres

Ejecutar una prueba de recuperación de medios y SQLite cifrados sin tocar los datos activos:

```bash
export SKY_BACKUP_PASSPHRASE='una-frase-privada-de-ensayo-de-16-caracteres-o-mas'
python -m scripts.disaster_recovery_v107
```

La prueba usa ficheros sintéticos y valida SQLite WAL, medios, verificación de datos, contraseña incorrecta, alteraciones y conservación del original. **No restaura un servidor entero ni simula pérdida de red, DNS, almacenamiento remoto, claves o nube.** Para recuperación real: detener SKY, realizar respaldo de bases y medios con `python -m neural_core.sky_recovery_full create --file ...`, verificar su integridad, restaurar fuera del directorio activo, revisar antes de migrar y arrancar solo tras verificación. Preservar la contraseña separadamente en un gestor de secretos. Probar una restauración en otra máquina bajo supervisión.

## 6. Seguridad y operaciones antes de producción

- Mantener MFA del creador, dominio limitado, clave API fuerte y contraseñas fuera del repositorio.
- Separar almacenamiento y workers; escanear archivos cargados y establecer cuotas reales; configurar WAF, monitoreo, retención y eliminación de datos.
- Probar Docker en servidor real con usuarios sin privilegios, secreto montado, Redis, Caddy, TLS y reinicios.
- Fijar imágenes y dependencias por digest/hashes, generar SBOM, análisis de vulnerabilidades y pentest externo.
- Verificar fronteras de permisos: **ninguna cuenta comunitaria debe ver BAQUEANO o la API del propietario**.

## 7. Estado de validación

`PYTHONPATH=. pytest -q`: 245 pruebas aprobadas (233 heredadas + 12 nuevas). La definición YAML fue analizada, **Docker no fue ejecutado**, los modelos de voz no estaban instalados y no se realizaron transcripciones reales. Los porcentajes de cobertura representan únicamente etiquetas estáticas que reconoce el auditor.

Más información: [CHANGELOG_V10_7.md](CHANGELOG_V10_7.md), [SEGURIDAD_V10_7.md](SEGURIDAD_V10_7.md) y [VALIDACION_V10_7.md](VALIDACION_V10_7.md).
