# SKY Android — extensión inicial inspirada en Siri y Bixby

**Fecha:** 14 de noviembre de 2026  
**Alcance:** SOLO `mobile/android-agent`; no afecta SKY Windows ni BAQUEANO.  
**Estado:** código en revisión, NO es APK certificada ni prueba real Samsung.

## Funciones añadidas

| Voz/texto del usuario | Acción preparada | Confirmación |
| --- | --- | --- |
| «SKY llama al 8888-7777» | `ACTION_DIAL` con número | Teléfono: el usuario inicia la llamada |
| «SKY llama a mamá» | Abre marcador; no consulta contactos | Usuario busca contacto e inicia llamada |
| «SKY envía un SMS a mamá que diga Estoy llegando» | `ACTION_SENDTO` + borrador `sms_body` | Usuario elige contacto y pulsa Enviar |
| «SKY envía un SMS al 8888-7777 que diga Llegaré tarde» | `ACTION_SENDTO` con número | Usuario confirma destinatario y envío |
| «SKY llévame a Granada Nicaragua» | `ACTION_VIEW` con `geo:0,0?q=` y destino codificado | Usuario valida destino e inicia navegación |
| «SKY abre ajustes de wifi» | `Settings.ACTION_WIFI_SETTINGS` | Usuario cambia ajustes |
| «SKY activa Bluetooth» | Abre ajustes Bluetooth, NO activa automáticamente | Usuario realiza el cambio |

El motor existente ya contempla acciones supervisadas de alarmas, temporizadores,
reproducción multimedia, aplicaciones instaladas, notas, búsqueda y escucha
manos libres con consentimiento; se reutiliza en lugar de duplicarlo.

## Límite de seguridad

- No se añaden permisos `CALL_PHONE`, `READ_CONTACTS`, `SEND_SMS`,
  `QUERY_ALL_PACKAGES` ni accesibilidad a la APK estándar.
- Todos los comandos pasan por `SkyActionTrustBoundary`: solamente
  propietario por voz o texto; jamás respuestas LLM, webs ni documentos.
- Se muestra aprobación antes de abrir el marcador, Mensajes o Mapas.
- `startActivity` significa **solicitud entregada a Android**, no llamada,
  SMS, navegación o ajuste completado.
- Si el destino es un contacto por nombre, SKY no inventa un número ni
  presume acceso a la agenda: el usuario lo selecciona dentro de la app.
- El servicio manos libres ya existente conserva su política de permisos,
  notificación visible y confirmación para órdenes en segundo plano.

## Validación requerida antes de publicar APK

1. GitHub Actions: `:app:assembleStandardDebug` y
   `:app:testStandardDebugUnitTest`.
2. Comprobar el manifiesto final: sin permisos peligrosos nuevos, sin
   servicios de accesibilidad en el flavor `standard`.
3. Emuladores Android 15 y 16: acción sin aplicación compatible, permisos
   denegados, pantalla bloqueada, retorno a SKY y comandos sin coincidencia.
4. Samsung Galaxy físico: micrófono, SMS no enviado, llamada no cursada,
   mapa con destino correcto, ajustes Wi-Fi/Bluetooth y recepción de
   confirmaciones por voz/pantalla.
5. APK de distribución: compilación, firma de release propia, compatibilidad
   con versión instalada, hash SHA-256, Play Protect y prueba de actualización
   sin pérdida de datos. **No anunciar APK lista** sin estas evidencias.

## Próximas etapas separadas

- Assistant Role / `VoiceInteractionService` para que SKY pueda ser
  asistente predeterminada **solo si** el usuario la selecciona. Requiere
  servicios y pruebas específicos; no basta con declarar el rol.
- Activación de palabra clave con motor local eficiente, consumo energético
  medido y consentimiento; no tratar `SpeechRecognizer` como escucha
  continua ilimitada.
- Contactos y llamadas por nombre con permisos específicos, diálogos de
  consentimiento, coincidencias ambiguas y protección de datos.
- Recordatorios persistentes, rutinas aprobadas, interacción contextual,
  reproducción comprobable y pruebas end-to-end en Samsung.
- No prometer cambios de Wi-Fi/Bluetooth ni control de apps protegidas
  que Android no permita a una aplicación ordinaria.
