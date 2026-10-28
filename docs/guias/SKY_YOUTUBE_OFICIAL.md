# SKY IA · Integración YouTube oficial

## Objetivo y límites

SKY presenta resultados de búsqueda y reproduce videos autorizados en una miniventana del HUD con el reproductor oficial de YouTube. No descarga audio/video, no elude DRM, restricciones regionales ni decisiones de sus titulares, no transforma el audio del iframe en un servicio separado y no modifica el player oficial.

* La búsqueda interna utiliza **YouTube Data API v3** con `search.list` (`type=video`, `videoEmbeddable=true`) y verifica cada candidato mediante `videos.list` (`status.embeddable`, `privacyStatus` y restricciones regionales).
* La reproducción se integra con **YouTube IFrame Player API**, URL de dominio oficial, parámetro `origin` y `Referrer-Policy: strict-origin-when-cross-origin`. La interfaz usa eventos `onStateChange`, `onError`, `onAutoplayBlocked`.
* La API de YouTube **puede** señalar un video como incrustable y, aun así, el reproductor puede denegarlo por Content ID o políticas adicionales.
* Si el reproductor notifica errores 100, 101 o 150, SKY ofrece o intenta automáticamente otro candidato de la misma búsqueda, sin repetir IDs. Si no hay más, deja un enlace oficial al video.
* Ante error 153, revisar que la página cargue bajo `http://127.0.0.1:8765/` y que el navegador no suprima `Referer`. No falsear encabezados ni identidad del cliente. Revisar también extensiones de privacidad y políticas del navegador.
* Sin clave de Data API, SKY **no hace scraping** de `youtube.com/results`: puede incrustar un enlace completo del usuario cuando YouTube lo permita y ofrece un enlace a la búsqueda oficial.

## Configuración en Windows

1. Abrir [Google Cloud Console](https://console.cloud.google.com/) con una cuenta autorizada y seleccionar o crear un proyecto.
2. En **API y servicios → Biblioteca**, habilitar **YouTube Data API v3**.
3. En **Credenciales**, generar una clave de API para esta integración. Restringir su uso a YouTube Data API v3; aplicar restricciones de aplicación compatibles con llamadas del backend Python de SKY, sin exponer la clave en `hud.js` ni en HTML.
4. Agregar en el archivo local `.env` (nunca hacer commit):
   ```dotenv
   YOUTUBE_API_KEY=PEGAR_LA_CLAVE_SOLO_EN_TU_EQUIPO
   SKY_YOUTUBE_REGION=NI
   ```
5. Reiniciar SKY con `python iniciar_sky_autonomo.py --stop` y `SKY_INICIAR.bat` (opción 0), refrescar HUD con Ctrl+F5 y volver a probar.
6. Ejecutar `python -m pytest -q tests/test_sky_youtube_search.py`. Los tests no sustituyen una prueba con internet, región y navegador reales.

No compartir claves, PIN ni archivos `.env` en incidencias, capturas o GitHub.

## Controles y cuentas

Los controles de reproducir, pausar, volumen, subtítulos, pantalla completa y calidad que ofrezca YouTube permanecen en el reproductor oficial. SKY también dispone de sus comandos de reproducir, pausar, siguiente, anterior y ventana flotante. La disponibilidad concreta de algunos controles depende del video, del navegador y de YouTube.

**Subir videos, dar Me gusta, comentar, administrar suscripciones o editar listas de reproducción en la cuenta** no se habilita simplemente con una clave API; requieren OAuth 2.0 y permisos explícitos del usuario. No deben declararse integrados mientras no existan flujos oficiales probados.

## Fallos típicos

| Código IFrame | Interpretación | Respuesta legítima |
| --- | --- | --- |
| 2 | Parámetro inválido | Revisar ID y URL |
| 5 | Reproducción HTML5 fallida | Otro candidato legítimo |
| 100 | Video eliminado o privado | Otro video o página oficial |
| 101 / 150 | Titular impide incrustación | Otro candidato permitido o abrir en YouTube |
| 153 | Sin Referer o identificación equivalente | Corregir identidad del cliente y configuración del navegador |
| Autoplay bloqueado | Política del navegador | Pedir pulsación del usuario en Play |

Referencias oficiales:

- https://developers.google.com/youtube/iframe_api_reference
- https://developers.google.com/youtube/data/reference/rest/v3/search/list
- https://developers.google.com/youtube/data/reference/rest/v3/videos/list
- https://developers.google.com/youtube/terms/required-minimum-functionality
- https://developers.google.com/youtube/terms/developer-policies


## Diagnóstico de búsqueda y reproducción (Windows)

Desde la raíz de SKY, sin imprimir la clave privada:

    & .\.venv\Scripts\python.exe -m scripts.sky_diagnostico_youtube "Los Enanitos Verdes Mi primer día sin ti"

El reporte indica si SKY encuentra la clave local, si recibe resultados mediante la API oficial y qué URLs/IDs se consideran incrustables conforme a los metadatos. No hay que importar manualmente hud_api para analizarlo.

Interpretación:
- api_configurada=true significa que SKY encuentra la clave en su entorno o archivo .env; **no** prueba autorización ni cuota.
- origen=youtube_data_api significa que la API produjo resultados mediante videos.list. La marca metadatos_de_incrustacion no equivale a reproducción efectiva.
- reproduccion_confirmada=false es intencional: solo el navegador puede confirmar el comienzo mediante onStateChange del IFrame Player.
- Cuando el iframe queda bloqueado sin emitir onError, SKY muestra tras doce segundos una alternativa con enlace oficial y otro candidato pendiente. La opción también aparece en la conversación.
- Los errores 101/150 señalan inserción denegada por el propietario; el 153 indica falta de identificación Referer. Son situaciones distintas y no deben confundirse con una API key inválida.

SKY no debe burlar restricciones, copiar el video ni retransmitir su audio como mecanismo alternativo. Si YouTube impide la inserción, la página original es la alternativa autorizada.
