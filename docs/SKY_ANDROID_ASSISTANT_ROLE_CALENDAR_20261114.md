# SKY Android — fase 2: asistente predeterminada y recordatorios por fecha

**Capa:** Android exclusivamente, en rama apilada sobre PR #108.  
**Estado:** revisión técnica/CI, sin prueba física todavía.

## 1. Asistente del sistema, de forma opcional

- `MainActivity` declara `ACTION_ASSIST` + categoría `DEFAULT` para ofrecer una Activity apta para el rol Assistant.
- Botón en Ajustes: «ELEGIR SKY COMO ASISTENTE DE ANDROID».
- `SkyAssistantRole` verifica si el sistema admite el rol mediante `RoleManager`, si está concedido y solicita el rol mediante el diálogo oficial del sistema.
- Se comprueba el resultado real mediante `isRoleHeld`; aceptar un diálogo no equivale a haber obtenido el rol.
- Al recibir `ACTION_ASSIST`, SKY abre la conversación solo si el dispositivo está desbloqueado. Ignora cualquier contexto suministrado por otras aplicaciones.
- Esta primera etapa **NO implementa** `VoiceInteractionService`, DSP, captura automática del micrófono ni interrupción de la pantalla bloqueada. La escucha local actual se habilita por separado y con consentimiento.
- Android/Samsung pueden no ofrecer el rol: la interfaz debe decirlo claramente.
- Las configuraciones de Android pueden revocar o sustituir el rol en cualquier momento.

## 2. Recordatorios del usuario con día y hora explícitos

Comandos admitidos en texto/voz: 
- «SKY recuérdame mañana a las 8:30 am comprar pan».
- «SKY recuérdame hoy a las 21:45 tomar medicamentos».
- «SKY ponme un recordatorio pasado mañana a las 12 pm reunión de clases».

`SkyReminderCommand` verifica día relativo, formato de hora, título y frases encadenadas. `SkyAndroidActions` calcula la hora local exacta, rechaza eventos pasados y abre `CalendarContract.Events.CONTENT_URI` con `ACTION_INSERT` y la hora propuesta.

**SKY no garantiza alertas sin guardar el evento y habilitar una notificación en Calendario.** El diálogo invita al usuario a revisar esos valores y confirmar. No se pide permiso de calendario, notificaciones, contactos, llamadas ni SMS adicional.

## 3. Estado de Android y seguridad

- Sin cambios en Windows, API SKY, modelos, Firebase, BAQUEANO ni `shared`.
- Sin cambios al flavor `assistive` ni a los servicios de accesibilidad.
- El rol Assistant puede otorgar privilegios Android particulares por política del sistema; el código nuevo no hace uso de lectura de pantalla, SMS o llamadas.
- La app estándar no añade `BIND_VOICE_INTERACTION`, `CALL_PHONE`, `READ_CONTACTS`, `SEND_SMS` o `READ_CALENDAR`.
- La fecha/alarma no se presenta como creada por el solo envío del Intent.
- `SkyActionTrustBoundary` exige que la orden proceda directamente del propietario (voz o texto).

## 4. Criterios de aceptación

- [ ] Build `:app:assembleStandardDebug`, test `:app:testStandardDebugUnitTest`.
- [ ] Manifesto final con `ACTION_ASSIST` pero sin servicios de accesibilidad estándar.
- [ ] Android 15/16: selector de asistente, aceptar/rechazar/revocar y mensaje correspondiente.
- [ ] Samsung: role request visible si One UI lo permite; comando sin acceso a datos privados.
- [ ] Calendario instalado: fecha y hora exactas, título con acentos, notificación configurada y evento guardado por el usuario.
- [ ] Calendario no instalado: mensaje real de app no encontrada.
- [ ] Reconocimiento de voz y permisos previos siguen estables.
- [ ] APK final firmada con clave propia, Play Protect, verificación de actualización sobre 0.8.47 preservando datos y SHA-256 comprobado.

## 5. Pendientes reales

- Sistema completo `VoiceInteractionService` con sesiones aisladas, medición de batería y voz; no es equivalente al rol `ACTION_ASSIST`.
- Hotword local, medido y sin escucha oculta, compatible con políticas modernas.
- Recordatorios nativos persistentes y recuperación tras reinicio (en lugar de delegar al Calendario), con permisos y notificaciones auditados.
- Contactos por nombre elegidos con el selector oficial, sin lectura indiscriminada de la agenda.
- Rutinas encadenadas por pasos y confirmaciones humanas.
