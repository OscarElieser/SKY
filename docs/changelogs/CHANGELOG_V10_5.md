# SKY IA v10.5 — Global Continuity & Secure Recovery

**Visión y dirección conceptual:** Oscar Elieser Chamorro Guzmán.

## Cambios verificados

1. **Recuperación cifrada extendida** (`neural_core/sky_recovery_full.py`): respalda bases SQLite compatibles y recursos multimedia de la biblioteca privada de Creative Studio. Utiliza AES-256-GCM y scrypt del núcleo de v10.4, instantáneas coherentes de SQLite (incluido WAL), hashes SHA-256 para cada archivo y ZIP protegido contra entradas extrañas, rutas de escape y recursos desmesurados. Restauración offline **solo hacia un directorio inexistente fuera de SKY**. No existe una ruta HTTP para descargar estos respaldos.
2. **Reconocimiento local de voz, bajo configuración explícita** (`neural_core/sky_stt_local.py`, `metaverse/stt_v105_api.py`): motor opcional `faster-whisper`, carpeta `SKY_STT_MODEL_DIR` instalada localmente, sin descargar modelos, máximo 60 segundos y 10 MB, normalización FFmpeg y llamada privada autenticada. La ausencia de un modelo devuelve indisponibilidad, no texto ficticio.
3. **Creative Studio**: panel avanzado plegable para importar una grabación, comprobar el modelo local y obtener una transcripción editable; portada principal intacta.
4. **Localización revisada** (`neural_core/sky_i18n_v105.py`): hasta 50 nuevas etiquetas de navegación/control en ocho idiomas (portugués, francés, alemán, italiano, árabe, chino, japonés y suajili), con reutilización de las traducciones previamente revisadas. No se traducen automáticamente datos privados.
5. **Pruebas**: 10 nuevas pruebas de cifrado/restauración, errores deliberados, symlinks y traversal, idiomas con diferentes escrituras, formato WAV, audio fuera de límite y autenticación de la API. Tests históricos heredados conservados.

## Estado honesto

- **No** se instaló ni descargó un modelo de reconocimiento de voz en el entorno de verificación. Solo se probó la preparación local del audio y la ausencia segura de proveedor; una transcripción real sigue pendiente de que el creador instale y pruebe un modelo.
- El respaldo cubre bases conocidas y la biblioteca multimedia **gestionada por Creative Studio**. Otros activos de proyectos y archivos fuera de dicha biblioteca requieren respaldo adicional; los secretos MFA, tokens y `.env` quedan intencionalmente excluidos.
- No hay auditoría de penetración independiente, certificación de rendimiento mundial ni traducción completa a todos los idiomas.
- BAQUEANO no ha sido modificado en producción. Su acceso permanece limitado al creador.

## Comandos

```bash
# La contraseña se suministra exclusivamente por entorno, nunca en el repositorio.
export SKY_BACKUP_PASSPHRASE='FRASE-LARGA-SECRETA-CONSERVADA-FUERA-DE-SKY'
python -m neural_core.sky_recovery_full create --file /ruta/segura/copia.skybackup
python -m neural_core.sky_recovery_full verify --file /ruta/segura/copia.skybackup
python -m neural_core.sky_recovery_full restore --file /ruta/segura/copia.skybackup --destination /ruta/nueva/sky-recuperado
```

Para transcripción opcional instalá `faster-whisper` compatible, descargá legalmente un modelo CTranslate2 mediante un procedimiento externo revisado y configurá `SKY_STT_MODEL_DIR` con la ruta **local** que contiene `model.bin` y `config.json`. No publiques modelos ni audio privado en GitHub.
