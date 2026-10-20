# SKY IA v9.9 — Timeline avanzado y selección guiada

**Visión y promoción del proyecto:** Oscar Elieser Chamorro Guzmán.

## Implementado sobre v9.8 (sin sustituir sus módulos)

- Hasta 16 fotogramas clave de posición (`caption_keyframes`) por clip, en segundos relativos a su duración efectiva.
- Interpolación lineal o suave (`caption_easing=linear|smooth`) mediante expresiones de FFmpeg verificadas en un MP4 real.
- Selección guiada GrabCut: coordenadas positivas (`foreground`) y negativas (`background`) sobre una fotografía, radio de pincel y validación estricta de posiciones.
- El editor privado incorpora entradas para puntos guía y una secuencia editable de fotogramas JSON. Ambos guardan revisiones del proyecto en SKY Creative Studio.
- Mantiene las máscaras, stickers, versiones `.skyzip`, tareas en cola, Project Hub y demás funciones de v9.8.

## Validación

183 pruebas automatizadas superadas (180 anteriores + 3 nuevas); `node --check` sobre el JavaScript del editor. Se exportó y reimportó un proyecto con 4 fotogramas clave y un MP4 real.

## Límites explícitos

No incluye aún una línea de tiempo visual con arrastre de puntos, seguimiento automático de objetos, rotoscopia de precisión ni generación de largometrajes por IA. No se verificó Gemini con una clave API real. No se desplegó SKY públicamente ni se alteró BAQUEANO.
