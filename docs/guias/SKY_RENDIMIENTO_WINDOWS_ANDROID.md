# SKY: rendimiento medible en Windows y Android

## Qué cambió (28/10/2026)

**Windows (API/HUD/manos libres):** En modo `SKY_CEREBRO=subasta`, cuando
`SKY_LOCAL_FAST_CONTEXT=1` y una pregunta pública no necesita historial ni
permisos, el motor coloca **Ollama instalado primero**. Solo reordena las
ofertas ya autorizadas: si Ollama está caído o falla, las ofertas cloud
permanecen disponibles, sujetas a las preferencias de privacidad,
autorizaciones y cooldowns ya existentes. Las tareas complejas, personales,
documentales, de acción y con historial no cambian. La nueva ruta no
garantiza 1-2 segundos: depende de RAM, GPU y velocidad de tokens del modelo.

**Android:** La aplicación deja de colocar respuestas del chat detrás del
sondeo periódico de órdenes del agente; conserva tres colas seriales,
una para acciones generales, otra para chat y otra para sondeos, sin
introducir ejecución paralela de acciones autorizadas. Muestra los
**segundos de petición-respuesta** junto a la procedencia de cada respuesta,
sin imprimir texto privado ni tokens de acceso. Las consultas explícitamente
breves y ciertas definiciones simples generan menos tokens de SALIDA en
Gemini, sin perder turnos de historial ni recortar peticiones largas. La
elección actual de Gemini 3.5 Flash-Lite se mantiene, así como el consentimiento
y el cifrado de claves. La voz empieza después de recibir texto completo
en este modo: el tiempo hasta audio audible aún necesita medición real.

## Pruebas de Windows

```powershell
Set-Location "C:\Users\PC 1\Documents\Desktop\SKY"
git pull --ff-only origin main
& .\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_sky_windows_fast_local_turn.py" -v
& .\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_sky_ai_auction.py" -v
& .\.venv\Scripts\python.exe -m neural_core.sky_latency_probe --models llama3.2 --skip-direct --fast-context
```

Reiniciar el supervisor SKY para que la API cargue el nuevo código.
Medir una pregunta nueva y sencilla, luego otra que dependa del historial.
No almacenar prompts ni claves en logs. El modo `auto` que selecciona el
propietario manualmente conserva su semántica; la subasta solo cambia en
preguntas que cumplen la condición estricta de contexto local breve.

## Pruebas Android

Compilar `app:assembleStandardDebug` y correr
`app:testStandardDebugUnitTest`. El CI Android también comprueba que el
APK estándar no incluye AccessibilityService y verifica la firma de
prueba. Si el flujo privado de firma release dispone de sus credenciales,
publica un candidato beta firmado **0.8.7**, que requiere instalación y
comprobación manual; un build CI no prueba latencia real del teléfono.

En el teléfono probar, con consentimiento de conexión válido:
- Consulta corta: «SKY, explícame en dos oraciones qué es la fotosíntesis».
- Petición larga: un documento o investigación debe conservar respuesta
  extensa y la semántica del historial.
- Sin Windows: el modo Android independiente debe seguir funcionando
  por su proveedor configurado.
- Con SKY Core: una consulta de chat no debe quedar bloqueada por un
  sondeo lento del agente.
- Comprobar el tiempo visible de la petición. No confundirlo con el tiempo
  de audio o reconocimiento de voz.
- Probar órdenes locales y permisos Android igual que antes.

**Pendiente de comprobar:** percentiles P50/P95 por dispositivo, tiempo
de primera palabra audible, calidad de respuesta y estabilidad de red
con la aplicación instalada. No se garantiza velocidad de conversación
en tiempo real hasta que esas medidas lo confirmen.
