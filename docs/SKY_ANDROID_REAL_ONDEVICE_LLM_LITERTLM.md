# SKY Android: motor generativo LiteRT-LM realmente local (experimental)

## Implementación

- Se añade **LiteRT-LM 0.18.0** y Kotlin **2.3.0** (versión compatible con AGP 8.9.2), conservando la configuración de `versionCode` y el paquete estable hasta completar pruebas.
- `SkyOnDeviceLm` usa `Engine` + `Conversation` de LiteRT-LM, backend **CPU** para maximizar compatibilidad, sin servidor HTTP, ni un puerto en red ni claves de terceros. Carga/genera/cierra desde un único ejecutor en segundo plano.
- En Ajustes, el propietario puede seleccionar manualmente un archivo **.litertlm** de origen confiable con Storage Access Framework, copiarlo a `filesDir`, validar un tamaño entre 32 MiB y 3 GiB y recibir el **SHA-256** para comparar con el del proveedor.
- No se distribuyen pesos del modelo en la APK, por tamaño/licencia. El motor nativo puede aumentar el peso de APK; requiere verificar ABIs reales, RAM, temperatura y batería del Samsung.
- El modo **CONVERSACIÓN SOLO LOCAL** responde con un LLM local cuando un modelo fue importado; conserva comandos del teléfono y memorias existentes; no envía consultas a la nube. La salida del LLM solo es texto: **no** autoriza llamadas, instalación, borrados ni pagos.
- Los modelos remotos siguen disponibles si se desactiva explícitamente el modo local, sin cambiar sus permisos ni desactivar HTTPS.

## Estado de validación

**Implementación de código ≠ inferencia verificada en el teléfono.** Es imprescindible:
1. GitHub CI: `assembleStandardDebug`, `testStandardDebugUnitTest`, comprobar manifiesto y firma temporal de CI. No publicar APK si falla.
2. Ejecutar pruebas Android 15/16 con **modelo real**, no solo verificaciones de compilación; importar `Qwen3-0.6B.litertlm` compatible o equivalente con licencia verificada, comprobar SHA-256 oficial.
3. Confirmar que el motor genera una respuesta en el teléfono **sin datos móviles y sin Wi-Fi**, y que la respuesta aparece en el historial y puede reproducirse por voz.
4. Probar 15 turnos consecutivos; medir primer token/segundos, tiempo total, memoria pico, carga de CPU y temperatura; bloquear conversaciones concurrentes.
5. Verificar actualización desde 0.8.50 firmada sin borrar datos o perder registros; confirmar el tipo de firma y Play Protect. No desinstalar la APK previa por defecto.
6. Mantener PR #111 y esta fase separados hasta aprobar las dos.

## Funciones futuras (sin afirmar que ya funcionan)

- Streaming de tokens, cancelación del LLM en una inferencia en curso, carga de modelo configurable y benchmark en Samsung.
- Contexto local persistente para reabrir conversaciones, selección entre modelos y validación oficial de checksum de catálogo.
- Modelos multimodales de imagen/audio, análisis documental y herramientas controladas desde agentes.
- Claude, Grok y otros solo mediante API/servicio oficiales cifrados y credenciales autorizadas.
- Reducción del peso de APK con distribución de runtime/modelo por variante o Play AI Delivery, preservando actualización firmada.

## Fuentes técnicas

- LiteRT-LM guía oficial: https://developers.google.com/edge/litert-lm/android
- Android/LiteRT-LM skill: https://developer.android.com/agents/skills/device-ai/litert/litert-lm/skill
- Kotlin KGP/AGP compatibilidad: https://kotlinlang.org/docs/gradle-configure-project.html

Esta fase modifica solo `mobile/android-agent` y documentación. Windows, servidor API, bases de datos, credenciales y BAQUEANO no se alteran.
