# SKY: voz natural nicaragüense, trato de tú y texto ordenado

**Regla de estilo del usuario:** tratarle de **tú** en español (tú, quieres,
puedes, dime), de forma cercana y respetuosa, con estilo nicaragüense natural.
Evitar el trato de usted y el voseo si no los solicita. No exagerar
regionalismos ni improvisar acentos. La precisión de una voz física depende de
las voces instaladas en Windows, Android y el navegador.

## Dos salidas, una sola respuesta

- **Escrita:** el historial y el chat muestran el contenido completo,
  conservando títulos, listas, puntuación, enlaces, fórmulas y cifras.
- **Hablada:** la copia para TTS quita marcadores Markdown, emojis, bloques de
  código y direcciones URL largas; convierte enlaces en su etiqueta y
  los bloques de código en «Código disponible en pantalla».
  Conserva coma y punto como señales de pausa, y **no** los convierte a
  las palabras «coma» o «punto». No manipula la respuesta ni las órdenes.
  Mantiene separadores de números como 3,14 y 1.500.

## Canales y límites

- `neural_core/sky_voice_queue.py` prepara el texto para la voz local
  de Windows con `sky_spoken_text.preparar_voz`, sin afectar la cola ni
  las interrupciones.
- `metaverse/static/hud.js` utiliza `sky-spoken-text.js` tanto para
  el sintetizador del navegador como para Piper. Se prioriza una voz
  española nicaragüense instalada, pero no se instala ni descarga ninguna.
- `SkyEyeVoicePanel.kt` limpia el texto solo antes de Android TTS;
  la respuesta en pantalla se mantiene intacta. Android ya prioriza
  una voz `es-NI` disponible.
- `sky_cerebro`, el cerebro general, el chat móvil emparejado y Gemini
  móvil reciben una guía de tuteo, ritmo oral y formato escrito claro.
  Las respuestas del modelo pueden seguir equivocándose; el filtro no
  cambia la veracidad del contenido ni promete un acento exacto.

## Comprobación

Windows, tras actualizar `main`, reiniciar SKY y recargar HUD
con Ctrl + Shift + R:

```powershell
& .\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_sky_natural_voice_text.py" -v
```

Probar por voz: «SKY, explícame en dos oraciones qué es la fotosíntesis»
y luego una respuesta con lista, enlace y cifra decimal. Debe hablar con
tú y sin verbalizar signos; el texto completo permanece escrito.
Para hablar con acento local se necesita una voz española instalada
compatible (preferible Nicaragua, luego otras voces hispanas).
Reiniciar la escucha Vosk por el menú de SKY, no abrir dos micrófonos.

Android: la versión `0.8.8` debe superar el workflow de
compilación, las pruebas de `SkySpokenTextTest` y la firma release.
Una APK firmada en CI **no** demuestra el acento ni la entonación;
hay que instalarla y escucharla en el teléfono real, conservando la
clave privada en el almacén cifrado. No insertar credenciales en código.

Estos cambios **no** modifican el reconocimiento STT, los PIN, las
autorizaciones de aplicaciones, las órdenes de dispositivos, la memoria,
los proveedores ni las reglas de autonomía supervisada.
