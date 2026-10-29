# SKY Android 0.8.24 — pruebas de aceptación verificables

Este protocolo distingue **código implementado**, **prueba de emulador aprobada**
y **prueba real en el Samsung**. El teléfono nunca se considera validado solo
porque GitHub Actions termine en verde.

## Paso 1. Verificaciones automáticas

- Rama: `main`, ruta de aplicación `mobile/android-agent/`.
- `SKY Mobile Android Agent`: `assembleStandardDebug`,
  `testStandardDebugUnitTest`, revisión de manifiesto y firma temporal.
- `SKY Android - runtime emulator smoke`: pruebas JUnit y ejecución
  `connectedStandardDebugAndroidTest` en emuladores Android API 35 y 36.
  El entorno es virtual: no garantiza audio, pantalla bloqueada,
  Spotify, YouTube ni micrófono físico.
- `SKY Android Signed Release Candidate`: `testStandardDebugUnitTest`,
  compilación estándar con clave privada, firma verificada, paquete
  `ni.sky.mobileagent` y publicación de APK 0.8.24 si todo el flujo pasa.
- Descargar exclusivamente una APK firmada y verificada en
  <https://github.com/OscarElieser/SKY/releases>.
- No desinstalar la versión previa ni desactivar Play Protect para forzar
  instalaciones; comprobar la huella del firmante y hacer respaldo.

## Paso 2. Pruebas en Samsung (Android 16)

Abrir SKY > Ajustes > Autodiagnóstico Android. Registrar versión 0.8.24,
modelo, permisos, motor de reconocimiento en dispositivo, voz, notificaciones,
estado de servicio manos libres, última frase captada y códigos de error.
Si no aparece `0.8.24`, la prueba corresponde a un APK anterior.

### A. Órdenes de aplicaciones, 5 intentos por orden

| Voz/texto | Aceptación real |
| --- | --- |
| «SKY abre YouTube» | YouTube queda visible y operativo, no solo intent enviado |
| «SKY abre Spotify» | Spotify queda visible; si no está instalado, SKY lo explica |
| «SKY abre Word» | Word aparece si está instalado; sin permiso previo pedir confirmación |
| «SKY reproduce [canción] en YouTube» | La canción solicitada SE ESCUCHA en YouTube; abrir una búsqueda no cuenta |
| «SKY reproduce [canción] en Spotify» | Hay reproducción audible real; si la app rechaza el intent marcar FALLO |

La APK estándar NO incluye un servicio de accesibilidad. Descubrir y abrir
una actividad no autoriza controlar botones internos, mensajes privados,
publicaciones, instalaciones ni pagos. Cada API o sistema tiene límites.
El registro `SENT`/«ENVIADA_SIN_VERIFICAR» nunca significa éxito.

### B. Pantalla bloqueada y manos libres

1. En primer plano, habilitar permiso de micrófono y activación manos libres
   voluntaria. Comprobar notificación permanente de SKY.
2. Con pantalla encendida, decir «SKY», esperar respuesta, dar una orden de
   volumen y una orden multimedia. Repetir cinco veces.
3. Bloquear la pantalla durante 10 minutos, mantener el servicio iniciado
   previamente desde SKY, y repetir cinco intentos de «SKY». Medir
   respuesta y consultar el autodiagnóstico tras desbloquear.
4. Comprobar que el reconocimiento muestra `active` y el momento de última
   detección. Registrar cualquier error del servicio. Una sesión interrumpida
   por Android se marca como fallo, no se anuncia como siempre activa.
5. Para abrir aplicaciones mientras está bloqueada, usar la notificación,
   desbloquear con huella/PIN y verificar. No eludir el bloqueo.
6. Detener manos libres desde la notificación. Verificar que no continúe
   escuchando. Reiniciar el teléfono y confirmar que SKY NO inicia el micrófono
   sin nueva acción voluntaria.

**Límite documentado:** Android restringe el inicio de servicios de micrófono
en segundo plano y `SpeechRecognizer` no está diseñado como un motor de
hotword siempre activo. El fabricante puede suspenderlo aun con servicio FGS.
Esto debe medirse en el hardware real; no prometer disponibilidad continua.

### C. Memoria y aprendizaje sin conexión

1. Desconectar red. Decir «SKY recuerda que mi prueba local es 12345».
   Consultar «SKY qué recuerdas de mí». Verificar la respuesta.
2. Reiniciar la app; comprobar persistencia en SQLite y el perfil. Eliminar
   el dato voluntariamente y confirmar que deja de aparecer.
3. Crear una nota local. El almacén devuelve
   `VERIFIED_LOCAL` únicamente cuando termina la escritura real.
4. Entrar en Ajustes > «APRENDIZAJE COMPROBADO». Comprobar que solo las
   acciones `VERIFIED_LOCAL` y `FAILED` cambian los parámetros de
   una neurona logística muy pequeña. `SENT` y `CANCELLED` no entrenan.
5. Reiniciar los indicadores y constatar que NO se eliminan recuerdos,
   historial, permisos ni archivos.
6. Este entrenamiento adaptativo de indicadores **no cambia pesos del LLM**.
   No declarar «modelo neuronal reentrenado» como estado del producto.

### D. Privacidad y seguridad

- Verificar que una pregunta sobre recuerdos/historial se resuelve
  localmente sin red, salvo búsqueda expresamente autorizada.
- Confirmar que cada consulta que incluya perfil privado requiera
  la casilla «Enviar datos privados» y que esta se desmarque después.
- Comprobar que cancelar una publicación, mensaje o pago no lo ejecute.
- No subir capturas de llaves API, PIN, datos biométricos o datos privados.
- Documentar errores, versión, estado, hora y pasos para reproducirlos.

## Criterios de cierre

| Capacidad | Estado mínimo para declarar «funciona» |
| --- | --- |
| Control de aplicaciones | 5/5 aperturas observadas, por cada app del alcance |
| Reproducción concreta | 5/5 canciones audibles correctas; intención sola NO vale |
| Manos libres desbloqueado | 5/5 detecciones; errores de STT registrados |
| Manos libres bloqueado | 5/5 detecciones durante 10 minutos, sin eludir bloqueo |
| Aprendizaje local | Memoria persiste; neurona logística aprende solo evidencia |
| Reentrenamiento del LLM | No implementado; no declararlo como probado |

Si alguna prueba falla, se informa **parcial / no verificado** y se corrige
antes de anunciar una versión estable. Este protocolo necesita la participación
del propietario en su teléfono; GitHub y un emulador no pueden sustituirla.
