# SKY IA v10.2 — Guía de instalación y uso

**SKY IA — visión y dirección: Oscar Elieser Chamorro Guzmán.**

## Actualización sin pérdidas

1. Conservá v10.1 hasta completar tus pruebas. Respaldá su `local_data/`, biblioteca y `.env` **fuera** del repositorio Git.
2. Descomprimí el ZIP v10.2 en una carpeta diferente. Instalá las dependencias existentes; para subtítulos MP4 se requieren `ffmpeg` y `ffprobe` con soporte `subtitles/libass`.
3. Probá `python -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765` o los iniciadores de la versión anterior. No expongás directamente el puerto a Internet.
4. Tras comprobar el arranque, con SKY apagado, trasladá los datos privados respaldados según los módulos que uses. Si cambiás el esquema o el host, verificá también las rutas configuradas en `.env`.
5. Verificá `PYTHONPATH=. pytest -q` y `python scripts/benchmark_sky_v10.py --requests 80 --workers 8` (la prueba de rendimiento es solo local).

## Idiomas realmente disponibles

El selector **🌐** aparece en el encabezado de las páginas SKY y se aplica sin recargar. El catálogo incluye 90 idiomas y preferencias de usuario persistentes. El núcleo de navegación cuenta con traducciones revisadas para español, inglés, portugués, francés, alemán, italiano, árabe, chino, japonés, coreano, ruso, hindi, indonesio, turco y suajili. Otras etiquetas del catálogo se pueden seleccionar y se enviarán como preferencia a un modelo compatible, pero **su interfaz puede seguir mostrando frases en español** hasta que tengan traducciones revisadas.

La orientación RTL se usa para árabe, hebreo, persa, urdu y pastún. La voz del navegador usa el idioma seleccionado, pero su funcionamiento y calidad dependen de Web Speech/navegador. No se envía automáticamente contenido privado a proveedores externos.

Las cuentas comunitarias guardan su propio idioma en `user_languages`; no comparten la preferencia con otros usuarios. El creador conserva la configuración local.

## Edición y subtítulos

En **Espacios → Estudio creativo**, abrí el apartado plegable «Subtítulos y narración multilingüe». Pegá un SRT con tiempos, elegí idioma, exportá `.vtt` o seleccioná un video ya importado para crear un MP4 subtitulado. El original queda intacto.

Podés crear un MP3 narrado mediante gTTS **solo después de marcar el consentimiento**; esa opción envía a un servicio externo el texto que escribiste. No sincroniza automáticamente labios ni traduce el texto por sí sola. Las funciones de transcripción automática y doblaje avanzado se reservaron para versiones posteriores.

## Activar el MFA del creador

El segundo factor TOTP **es opcional en modo local**, para conservar la compatibilidad. Para activarlo:

1. En tu propia máquina ejecutá `python scripts/setup_owner_mfa.py`. No compartás lo que se imprime.
2. Guardá `SKY_OWNER_MFA_SECRET=<secreto_B32>` solamente en tu `.env` local o gestor de secretos. Escaneá el enlace OTP en un autenticador TOTP de confianza.
3. Reiniciá SKY. Al acceder como creador se pedirá la clave privada y después el código temporal de seis cifras.
4. Una sesión de segundo factor dura 20 minutos, puede revocarse y no reemplaza el primer factor. Si perdés la aplicación autenticadora, recuperá el secreto desde un respaldo protegido; no hay recuperación por correo implementada.

**Nunca publiques `.env`, el secreto MFA, tokens ni los códigos en GitHub.** Al modificar el secreto, las sesiones anteriores pierden sentido tras reiniciar el servicio.

## Despliegue público (sin certificar)

El modo `SKY_DEPLOYMENT_MODE=public` **bloquea el arranque** si falta un dominio autorizado, un secreto MFA, `SKY_REDIS_URL`, indicación de proxy TLS o separación del renderizador `SKY_CREATIVE_WORKER=0`. Esas condiciones son mínimas, no una certificación. Se requieren además WAF, mitigación DDoS, escáner de dependencias y de archivos, auditoría externa, almacenamiento privado, rotación de claves, backups restaurables y pruebas de carga/pentest.

Instalá Redis por separado con `pip install -r requirements_production.txt`; mantenelo aislado de Internet. El servicio de medios requiere worker aislado para producción; la ruta de subtítulos locales se bloquea en modo público hasta incorporar una cola específica.

Ver [SEGURIDAD_V10_2.md](SEGURIDAD_V10_2.md) y [VALIDACION_V10_2.md](VALIDACION_V10_2.md).

## Proyecto y autoría

SKY IA sigue siendo un único ecosistema. BAQUEANO continúa reservado al creador y su sitio/repo de producción no se modifican al actualizar SKY. La mención de autoría conceptual no sustituye el registro legal de una marca ni las licencias de terceros.
