# SKY Android 0.8.40 — Protocolo de aceptación científica y archivos

**Estado:** implementado en código de `main`; la compilación firmada, los emuladores y el Samsung real requieren evidencia independiente.
**Alcance:** exclusivamente Android. No modificar SKY Windows. No publicar APK solo por cambiar `versionName`.

## Prerrequisitos

- APK estándar firmada por la misma clave que la versión instalada; verificar certificado y SHA-256.
- GitHub Actions: `signed-release` y emuladores Android API 35 / API 36 en estado satisfactorio.
- Confirmación de versión `0.8.40` dentro del APK; instalación/actualización sin perder historial.
- Kit de pruebas proporcionado al propietario: PDF de tres páginas, video MP4 corto y ejercicios científicos.
- Confirmación manual de la versión de Android System WebView y de permisos de selección de archivos.

## Caso 1 — Respuesta académica de química

Solicitar una reacción reversible y la expresión de su constante de equilibrio. Comprobar que las fracciones, los subíndices, las flechas reversibles y los títulos no muestran LaTeX ni Markdown crudo en pantalla. Solicitar explicación por voz y confirmar que no se leen comandos como `frac`, `text` ni `rightleftharpoons`.

**Resultado esperado:** explicación ordenada con hipótesis (reacción elemental si se deriva la ley cinética), sustitución, unidades cuando aplican y ningún valor inventado. Documentar errores de cálculo por separado de errores de visualización.

## Caso 2 — Respuesta muy extensa

Solicitar una explicación de varias páginas con fórmulas y tablas. Comprobar que aparece **Leer respuesta completa**, se puede desplazar y copiar la respuesta íntegra, el historial conserva la respuesta y no se produce bloqueo o cierre. Abrir y cerrar repetidamente y observar el consumo de memoria.

## Caso 3 — PDF de tres páginas

Adjuntar el PDF. Confirmar que aparece la primera página, avanzar hasta la tercera, retroceder y cerrar/reabrir la vista. Comprobar que una navegación pendiente no actualiza una ventana cerrada. Instrucción: "Revisá el ejercicio de física de las tres páginas y localizá el error".

**Resultado esperado:** vista previa local antes de cualquier envío, descripción honesta del contenido parcial y capacidad de detectar que 5 kg × 2 m/s² da 10 N (no 20 N) tras análisis autorizado.

## Caso 4 — Video MP4

Adjuntar video de cuatro segundos y comprobar un fotograma decodificado del propio archivo y su duración. No confundir miniatura con comprensión semántica del video. Pedir un resumen solo tras la autorización al motor compatible; si el proveedor no lo soporta, mostrar el error, no inventar escenas.

## Caso 5 — Consentimiento y conservación

- Adjuntar PDF sin escribir tarea. Pulsar enviar: debe solicitar la instrucción, **sin** cargar el archivo a Gemini.
- Escribir una tarea y pulsar enviar. Cancelar en el cuadro de autorización: no debe iniciarse la carga.
- Autorizar una sola vez: comprobar progreso, cancelación, respuesta, trazabilidad y comportamiento de borrado temporal.
- Cancelar una carga: informar sin presentar análisis inventado, permitir reintentar.
- Mantener el historial previo, permisos y ajustes existentes tras actualizar la APK.

## Caso 6 — Formatos y resistencia

Probar PNG/JPEG, TXT/CSV, DOCX/XLSX/PPTX, PDF y MP4; verificar diferencias entre vista previa completa, parcial, metadatos y formato no compatible. No ejecutar macros, HTML, scripts ni enlaces incluidos en documentos. Probar archivos vacíos, corruptos y superiores a los límites del lector: deben rechazarse con un mensaje claro.

## Evidencias obligatorias

Para cada caso guardar: versión APK, versión Android, captura de pantalla, hora, entrada, resultado observable, **PASÓ/FALLÓ/BLOQUEADO**, logs sin credenciales y referencia al run/commit. Un test unitario o un emulador no sustituyen la prueba física.

## Estado al escribir este documento

- Código del renderizado científico, visor completo, TTS y vistas previas: incorporado a `main`.
- Compilación local aislada del limpiador TTS: ejecutada y superó ejemplos de química y matemáticas.
- Resultado del pipeline firmado y pruebas en Samsung para 0.8.40: **NO VERIFICADO**.
- APK publicada 0.8.40: **NO CONFIRMADA**; no recomendar instalar hasta verificar su presencia en Releases.

[Compilaciones Android](https://github.com/OscarElieser/SKY/actions/workflows/sky-mobile-release.yml) · [APK publicadas](https://github.com/OscarElieser/SKY/releases).
