# SKY Android — ciclo de ejecución verificable (código 0.8.27)

**Estado:** cambios subidos a `main`; la compilación en GitHub Actions y la prueba física en el Samsung son requisitos distintos. No es un certificado de que todas las aplicaciones de terceros puedan controlarse.

## Objetivo y criterios de verdad

Una orden **enviada** a Android no prueba que otra aplicación haya abierto, recibido un mensaje o iniciado reproducción. Desde esta actualización cada acción cubierta deja un recibo local que distingue:

- `VERIFICADA_LOCAL`: SKY comprobó un efecto observable dentro de las capacidades Android permitidas.
- `ENVIADA_SIN_VERIFICAR`: Android recibió un Intent o un evento multimedia; el resultado en otra aplicación sigue sin comprobarse.
- `FALLIDA`: excepción o error conocido en ejecución.
- `RECHAZADA`: permiso denegado, acción duplicada, límite del dispositivo o cancelación.
- `RESPUESTA_REMOTA_RECIBIDA`: se obtuvo una respuesta, pero no se verificó el resultado final.
- `ESTADO_DESCONOCIDO`: estado no reconocido, nunca se presenta como éxito.

## Qué se integró

1. Se corrigió el encaminamiento de órdenes por voz: `processDailyCommand(transcript, spoken = true)` transmite el origen explícito del propietario a `SkyAndroidActions.run`; una respuesta de IA, una página web o un documento nunca adquieren ese permiso.
2. `SkyQuickActions` informa acciones a `SkyActionEvidence`: la variación de volumen solo es exitosa si `getStreamVolume` cambia; `PLAY/NEXT/PAUSE` siguen siendo **enviadas, no verificadas**; `KeyguardDismissCallback` verifica el desbloqueo solo cuando Android lo confirma y no elude PIN o biometría.
3. Guardado de notas: `SharedPreferences.commit()` debe concluir satisfactoriamente y la última nota **se relee y compara** antes de declararla guardada.
4. Resumen local SQL: `SkyActionEvidence.summary()` obtiene los conteos por estado de la base de datos, sin leer el contenido de las notas ni subir evidencias a servidores.
5. En Configuración aparece **RESUMEN DE EJECUCIÓN · RESULTADOS COMPROBADOS**, además del listado de evidencias detallado existente.
6. El aprendizaje local clasifica los controles Android de audio en su categoría correcta; nunca aprende de eventos `SENT` como si fueran resultados exitosos.
7. El catálogo sigue evitando solicitudes de confianza redundantes: cuando ya existe autorización general, elegir entre nombres de apps ambiguos no pide un segundo permiso de apertura.

## Comprobación en hardware físico

Después de instalar una APK release **firmada, publicada y aprobada por CI**:

- Desde una orden de voz, decir «SKY, sube el volumen». Revisar que cambia el volumen real, y en Configuración → Resumen de ejecución que hay evidencia verificada; repetir a volumen máximo y comprobar rechazo, sin éxito falso.
- Decir «SKY, siguiente canción» en un reproductor compatible. Revisar la app de música; el registro debe continuar como `ENVIADA_SIN_VERIFICAR` aunque el usuario oiga el cambio.
- Decir «SKY, anota: prueba de verificación local». Revisar Mis notas y el resumen: solo debe haber verificación tras escritura y lectura de vuelta.
- Intentar «SKY, abre YouTube» por voz y por chat. La apertura queda como **enviada**, no como carga completada; permisos de aplicaciones intactos.
- Desde Configuración revocar Control supervisado y comprobar que SKY vuelve a solicitar autorización para abrir apps.
- Comprobar el bloqueo: nunca deben ignorarse huella, patrón o PIN. Las opciones dependen de Android.
- Verificar que no se alteraron las funciones de Windows ni los datos anteriores.

## Pruebas automatizadas incorporadas

- `SkyExecutionEvidenceRuntimeTest.kt`: usa SQLite de Android REAL (emulador) y comprueba aumentos en contadores de enviado, verificado, fallido y rechazado.
- `SkyVerifiedLearningTest.kt`: confirma clasificación de controles de audio y que las acciones simplemente enviadas no entrenan el aprendizaje.
- Compilación y pruebas Android: `.github/workflows/sky-mobile-agent.yml`, `sky-android-runtime-smoke.yml` y `sky-mobile-release.yml`.

**No implementado en este bloque:** comprobar visualmente otras aplicaciones sin accesibilidad consentida, editar/eliminar datos de apps ajenas, autorización remota global, ejecución de tareas compuestas o garantía de funcionamiento con pantalla bloqueada. Son capacidades separadas que requieren integraciones oficiales, permisos, pruebas y controles específicos.
