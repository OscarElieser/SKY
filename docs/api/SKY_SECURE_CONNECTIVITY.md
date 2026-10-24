# SKY Secure Device Hub — conexión profesional, Wi-Fi, Bluetooth, infrarrojo e IoT

**Estado:** módulo inicial de SKY en una rama de desarrollo, sin despliegue y sin controles universales. SKY es la única interfaz conversacional; las Skills y conectores trabajan internamente. Las conexiones exigen propiedad o permiso verificable y autorización del propietario de SKY.

## Principio operativo

**Descubrir ≠ emparejar ≠ autenticar ≠ controlar.** Cada fase tiene evidencia independiente.

1. **Descubrimiento voluntario:** anuncios mDNS/Bonjour por Wi-Fi o anuncios BLE locales, durante 2 a 6 segundos. No se obtienen contraseñas, MAC, direcciones IP ni identificadores para conservarlos.
2. **Registro del dueño:** clasificar equipo y vía autorizada; un registro no indica conexión válida.
3. **Emparejamiento externo legítimo:** en Android, confirmación de depuración USB; en Windows, agente SKY con token; para Bluetooth, cuadro de emparejamiento del sistema; para Matter, alta con QR/código por controlador compatible; para cámaras, credenciales del propietario; para infrarrojo, puente/emisor IR.
4. **Comprobación técnica real:** SKY consulta exclusivamente agentes previamente registrados o entidades Home Assistant configuradas, sin comandos que alteren estados; cada resultado identifica el origen de la verificación.
5. **Acción:** la API ya existente de SKY y el agente aplican capacidades, permisos y aprobaciones de un solo uso antes de actuar. Los descubrimientos no otorgan permiso de control.
6. **Auditoría:** recibos y estado real, sin confundir `SENT` con `VERIFIED`.

## Rutas de la API (propietario autenticado)

| Método | Ruta | Función actual |
|---|---|---|
| GET | `/api/sky/device-hub/capabilities` | Motores, límites y dependencias detectadas |
| GET | `/api/sky/device-hub/devices` | Registro privado de dispositivos declarados |
| POST | `/api/sky/device-hub/devices` | Alta con consentimiento y conector permitido |
| DELETE | `/api/sky/device-hub/devices/{id}` | Elimina registro de SKY (no sustituye revocar credenciales del proveedor) |
| GET | `/api/sky/device-hub/devices/{id}/probe` | Prueba de conexión autenticada, de solo lectura |
| POST | `/api/sky/device-hub/discover/bluetooth` | Anuncios BLE temporales, sin emparejar ni guardar direcciones |
| POST | `/api/sky/device-hub/discover/wifi` | Anuncios mDNS locales de Google Cast, AirPlay, Matter, HomeKit |
| POST | `/api/sky/device-hub/security/audit-plan` | Lista de revisión defensiva para sitio, teléfono, computadora o IoT |

Todas requieren `X-SKY-KEY`; cuando MFA está habilitada también `X-SKY-SESSION`. Las pruebas a agentes remotos requieren su token `X-SKY-DEVICE-TOKEN` únicamente en la cabecera del pedido de comprobación, **nunca guardado en SKY Hub**.

### Ejemplo: registrar computadora con agente SKY

```json
{
  "name":"Mi laptop",
  "device_type":"laptop",
  "transport":"wifi",
  "connector":"sky_agent",
  "connection_ref":"Oficina SKY",
  "owner_attested":true
}
```

`connection_ref` debe coincidir con un agente SKY previamente registrado. Después se ejecuta `GET /devices/{id}/probe` enviando el token específico del agente. SKY confirma si realmente respondió el servicio esperado; el registro inicial siempre dice `registered_unverified`.

### Ejemplo: TV con puente infrarrojo

```json
{
  "name":"Televisor de sala",
  "device_type":"television",
  "transport":"infrared",
  "connector":"home_assistant",
  "connection_ref":"remote.sala",
  "owner_attested":true
}
```

El puente IR debe estar instalado y emparejado en Home Assistant. Esta ruta **solo comprueba** que la entidad `remote.sala` esté disponible; no transmite IR ni ejecuta controles de televisión. Para controlar comandos posteriormente, se necesitará un adaptador IR explícito que pase por la aprobación de SKY. Sin emisor físico no existe salida infrarroja.

### Ejemplo: celular Android por USB

```json
{
  "name":"Mi Android",
  "device_type":"phone",
  "transport":"usb",
  "connector":"adb_readonly",
  "connection_ref":"",
  "owner_attested":true
}
```

`probe` reutiliza SKY Mobile Unlock, que comprueba que exista **un solo** Android conectado y autorizado en pantalla. Es lectura de modelo/versión y estado de conexión; no libera SIM, descifra aplicaciones ni extrae mensajes.

### Ejemplo: exploración voluntaria BLE

```json
{"owner_network_confirmed":true,"seconds":3}
```

Requiere instalar voluntariamente `bleak`, Bluetooth activo y permiso del sistema. La respuesta muestra únicamente nombres anunciados, **sin identificadores persistentes ni emparejamiento**. Aceptar un dispositivo de terceros no autoriza intervenirlo.

Wi-Fi/mDNS requiere opcionalmente `zeroconf`; los resultados son anuncios, no acceso a equipos. Tampoco hace búsquedas por rangos IP, barridos de puertos, ataques de contraseñas ni explotación.

## Dependencias opcionales

```powershell
python -m pip install -r requirements_connectivity_optional.txt
```

No se instalan automáticamente. Las funciones ya existentes de SKY Home Assistant, agentes autorizados y ADB funcionan sin Bleak o Zeroconf si sus propias dependencias están configuradas.

## Tabla de integración por dispositivo

| Equipo | Conexión prevista | Estado técnico |
|---|---|---|
| Windows/laptop con agente SKY | Wi-Fi/Ethernet vía HTTPS/Tailscale | Prueba autenticada reutiliza agente existente, requiere token |
| Android autorizado | USB-C vía ADB | Diagnóstico de solo lectura; control por app/permiso aún pendiente |
| iPhone/iPad | API de app propia + permisos de iOS | No existe control universal ni desbloqueo por USB |
| TV inteligente | mDNS para ver anuncios; Home Assistant media_player para funciones permitidas | Descubrimiento opcional, control depende de integración/approval existente |
| Cámaras | Registro SKY Guardian, ONVIF/RTSP autorizados | Streaming y autenticación ONVIF pendientes: no ver video hoy |
| Sensores Bluetooth LE | Anuncios BLE; servicio GATT y emparejamiento aún por implementar | Solo descubrimiento opcional |
| Sensores y automatización IoT | Matter emparejado con controlador compatible/Home Assistant | SKY NO realiza commissioning Matter por sí sola |
| TV o aire acondicionado IR | Puente/emisor físico (p.ej. Home Assistant infrared/remote) | Solo consulta de entidad remota; emisión IR en SKY pendiente |

Referencias de implementación: Bleak (https://bleak.readthedocs.io/en/stable/); Matter commissioning (https://developers.home.google.com/matter/primer/commissioning); Home Assistant REST (https://developers.home-assistant.io/docs/api/rest/); Infrared (https://www.home-assistant.io/integrations/infrared/); ONVIF (https://www.onvif.org/profiles/).

## SKY Cybersecurity — auditorías legales

SKY puede preparar y posteriormente ejecutar —tras integrar herramientas y pruebas seguras— auditorías de **sitios y dispositivos propios o autorizados**, con estas etapas: inventario de activos, verificación de actualizaciones, políticas de contraseñas/MFA, configuración TLS y cabeceras, exposición de administración remota, copias de seguridad, informes y remediación.

La ruta `security/audit-plan` **solo construye el plan**; todavía no verifica vulnerabilidades activamente ni lanza herramientas de pentesting. Para un servicio comercial se debe documentar el alcance, el consentimiento del titular, la identidad del responsable, las actividades permitidas, ventanas de prueba y protección de datos.

No implementar: acceder a equipos de terceros, leer chats privados, instalar spyware, cracking de credenciales, saltar PIN/FRP/iCloud, tomar cámaras ajenas, ataques de denegación de servicio, propagación sin autorización ni vigilancia encubierta. Un pago no constituye permiso para invadir equipos.

## Validación antes de uso productivo

- `tests/test_sky_secure_connectivity.py`: permisos de usuario, consentimiento, transporte, registro, ADB, autenticación del agente, consulta Home Assistant, anuncios BLE/mDNS y auditorías sin exploración activa.
- CI Linux y Windows debe aprobar el último SHA. La prueba real de Bluetooth requiere equipo físico; el CI usa simulaciones.
- Asegurarse de que `metaverse/asistente_api.py` inicia sin rutas duplicadas y conservar sus acciones autorizadas de voz/texto.
- No fusionar ni desplegar sin revisión. Desactivar la función si se detectan dispositivos inesperados y no publicar agentes en puertos abiertos a Internet.
