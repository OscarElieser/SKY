# SKY Mobile Unlock — teléfonos importados de Estados Unidos para Claro y Tigo

**Objetivo:** ayudar al propietario de un teléfono comprado en EE. UU. a determinar si está bloqueado por un operador estadounidense y completar un procedimiento válido de liberación para usar una línea en Nicaragua.

**Estado del desarrollo:** asistencia técnica + diagnóstico USB **solo de lectura para Android autorizado**. No es un generador de códigos, no ofrece liberación real sin el proveedor original ni desbloquea iCloud, Google FRP, PIN, equipos denunciados o IMEI bloqueados. El módulo está aislado en una PR de desarrollo, no desplegado.

## Distinguir bloqueos

| Problema | Qué puede hacer SKY | Quién resuelve realmente |
|---|---|---|
| SIM/network/carrier lock (AT&T, T-Mobile, Verizon, etc.) | Identificación, orientación de elegibilidad, guía de solicitud y comprobaciones posteriores | Operador original o sus mecanismos oficiales |
| Cobertura/compatibilidad con Claro/Tigo | Consultar el modelo, comprobar bandas LTE/VoLTE publicadas y realizar pruebas de red | Fabricante + operador nicaragüense |
| iPhone indica “SIM no compatible” | Mostrar cómo comprobar el estado de bloqueo de operador en Ajustes > General > Información | Operador original; Apple no realiza este desbloqueo |
| Android pide “SIM network unlock PIN” | Indicar que se solicite código/procedimiento al operador original | Operador original; no adivinar ni probar códigos indiscriminadamente |
| Bloqueo de pantalla, iCloud, FRP o teléfono denunciado | Orientar por recuperación oficial de cuenta y comprobantes de compra | Propietario y servicio autorizado; SKY no lo evade |
| IMEI bloqueado o alterado | Derivar a atención oficial; nunca cambiar identidad de hardware | Operadores y autoridades según procedimiento |

### Qué aporta el USB/USB-C

En Windows, instalar Android SDK Platform Tools, conectar el teléfono propio mediante un cable con transferencia de datos y, si el equipo lo permite, activar **Depuración USB** y aceptar el aviso RSA **en el propio teléfono**. SKY consulta solo propiedades permitidas mediante ADB: fabricante, modelo, Android, identificador de variante y estado SIM. No consulta ni conserva serial, IMEI, IMSI, ICCID, contactos, fotos, cuentas ni mensajes.

**Importante:** ADB no expone universalmente el estado de bloqueo de operador. \`gsm.sim.state=READY\` no demuestra que se haya liberado la red. El diagnóstico no cambia un solo bit del teléfono; no ejecuta comandos para instalar, borrar, desbloquear el bootloader ni flashear.

Un teléfono bloqueado por PIN suele impedir aceptar la depuración USB. SKY mostrará que requiere autorización en pantalla, nunca intentará forzar la conexión. En iPhone el reconocimiento por USB tampoco otorga facultad de liberación del operador.

**SDK oficial:** https://developer.android.com/tools/releases/platform-tools

## Flujo completo de SKY

1. Registrar consentimiento del titular para diagnosticar el equipo.
2. Conectar un Android por USB-C con depuración autorizada; o elegir modo iPhone de comprobación manual.
3. SKY identifica el modelo Android que el teléfono permite consultar, sin extraer identificadores personales.
4. Propietario indica operador de origen: AT&T, T-Mobile, Verizon o desconocido.
5. SKY registra **solo el estado reportado por el propietario**: “SIM no compatible”, “solicita PIN de red”, “sin servicio”, “SIM aceptada”, “sin restricciones SIM” o “sin comprobar”. No trata esa declaración como una certificación.
6. SKY dirige al portal oficial de liberación y los requisitos vigentes. No inventa códigos, elegibilidad ni pagos.
7. Tras confirmación del operador original, se prueba una SIM/eSIM Claro o Tigo. Confirmar soporte de bandas del modelo exacto, LTE/VoLTE, llamadas, SMS y datos. La ausencia de señal **no siempre** se debe al bloqueo.
8. SKY anota el estado observado; solo afirma “liberado” cuando hay evidencia verificable procedente del proveedor y prueba de servicio.

## Portales oficiales

- AT&T: https://www.att.com/deviceunlock/
- T-Mobile: https://es.t-mobile.com/support/devices/unlock-your-mobile-wireless-device
- Verizon: https://espanol.verizon.com/support/device-unlocking-policy/
- Apple: https://support.apple.com/en-la/109316
- Tigo Nicaragua (equipos importados/eSIM): https://ayuda.tigo.com.ni/hc/centro-de-ayuda/articles/1740422978

Las condiciones y tiempos de desbloqueo pueden cambiar; SKY deberá consultar los enlaces oficiales actuales antes de aconsejar. Tigo Nicaragua indica que no libera dispositivos bloqueados por otros operadores y que debe solicitarse al proveedor de origen.

## API propia de SKY

Todas las rutas heredan la autenticación \`X-SKY-KEY\` y el segundo factor configurado.

\`\`\`http
GET /api/sky/mobile-unlock/capabilities
POST /api/sky/mobile-unlock/diagnose-usb
POST /api/sky/mobile-unlock/plan
\`\`\`

### Diagnóstico USB

\`\`\`json
{"owner_attested":true}
\`\`\`

Devuelve \`device.manufacturer\`, \`device.model\`, \`device.android_version\`, \`device.device\`, \`device.sim_state\`, y siempre \`carrier_lock_state: "unknown"\`. Si falta ADB, o hay cero, varios, desconectados o no autorizados, devuelve el estado real sin ejecutar comandos de liberación.

### Orientación por operador

\`\`\`json
{
  "owner_attested":true,
  "source_carrier":"T_MOBILE",
  "target_carrier":"CLARO_NI",
  "os_family":"android",
  "observed_state":"network_unlock_requested"
}
\`\`\`

Devuelve instrucciones, enlace del proveedor y \`unlock_performed: false\`. El agente no debe presentar el resultado como desbloqueo real.

## Implementación y validación

- \`neural_core/sky_mobile_unlock.py\`: comandos ADB estrictamente de lectura; no llama al sistema mediante \`shell=True\`.
- \`metaverse/mobile_unlock_api.py\`: validación de consentimiento y rutas autenticadas.
- \`tests/test_sky_mobile_unlock.py\`: permisos, múltiples dispositivos, autorización RSA pendiente, no modificación del teléfono y ausencia de declaraciones falsas.
- GitHub Actions Linux y Windows deben pasar en la revisión final.
- Pruebas físicas autorizadas en un teléfono real aún pendientes.

Esta primera fase **no realiza automáticamente el desbloqueo de red**, porque no existe un comando ADB universal ni facultad legítima de SKY para cambiar las autorizaciones de AT&T/T-Mobile/Verizon. La siguiente fase debe incluir un asistente de solicitud oficial y comprobaciones de compatibilidad por modelo, sin guardar IMEI ni datos financieros en el núcleo.
