# SKY GUARDIAN — Protección personal y seguridad ciudadana

**Estado:** base inicial en la rama `feature/sky-guardian-civic-safety-20261023`. **No** hay conexión con cámaras, sistemas policiales, satélites privados ni servicios de emergencia. SKY continúa como única interfaz del usuario.

## Objetivo

Crear un asistente de seguridad personal y prevención de incidentes capaz de reunir información autorizada, organizar evidencias, emitir alertas configuradas y ayudar a preparar respuestas para personas y negocios **sin sustituir a profesionales de seguridad ni a las autoridades**.

## Funcionalidad realmente implementada

- `neural_core/sky_guardian.py`: inventario privado de cámaras con declaración de autorización del propietario; ninguna dirección RTSP, contraseña ni imagen se captura por ahora.
- Registro de incidentes reportados manualmente por el propietario: alarma de humo, fuga de agua, falta de corriente, apertura de puerta, movimiento en propiedad autorizada, cámara sin conexión y solicitud SOS.
- Prioridad por categoría, historial limitado a 30 días y reconocimiento manual de avisos. Un reporte manual **no significa que SKY lo haya verificado con sensores** ni que haya contactado a la Policía.
- Catálogo de fuentes verificadas de información pública: Copernicus Browser, NASA Worldview, INETER, SINAPRED y Policía Nacional.
- `metaverse/guardian_api.py`: endpoints con autorización y segundo factor cuando SKY lo tenga habilitado.
- Pruebas `tests/test_sky_guardian.py` contra acceso no autorizado, inventario de cámaras sin permiso, afirmaciones falsas de acceso en vivo, registro de avisos y retención de información.

## API

| Método | Endpoint | Función |
|---|---|---|
| GET | `/api/sky/guardian/capabilities` | Estado real, límites y fuentes públicas |
| GET | `/api/sky/guardian/cameras` | Inventario de cámaras declaradas como autorizadas |
| POST | `/api/sky/guardian/cameras` | Registrar `name`, `area` y `owner_attested: true`, sin credenciales |
| DELETE | `/api/sky/guardian/cameras/{id}` | Retirar cámara del inventario |
| GET | `/api/sky/guardian/events` | Historial privado de avisos |
| POST | `/api/sky/guardian/events` | Registrar incidente observado manualmente |
| POST | `/api/sky/guardian/events/{id}/acknowledge` | Confirmar recepción de un aviso |

Ejemplo manual:
```json
{"event_type":"smoke_alarm"}
```

La respuesta incluye `observation: owner_reported_unverified`, `police_contacted: false` y `alert_dispatched: false`. No se debe mostrar un indicador «todo asegurado» si faltan sensores o comunicación real.

## Etapas para cámaras autorizadas

1. El propietario instala una cámara propia y acredita el consentimiento y el alcance del monitoreo.
2. Inventario y reglas de zona/horario con mínima recopilación de datos.
3. Integrar **solo dispositivos autorizados** mediante estándar ONVIF o RTSP dentro de la red local/VPN segura, sin exploración de cámaras ajenas ni exposición de puertos.
4. Guardar credenciales en el almacén de secretos de SKY; probar TLS, autenticación, cifrado y retención.
5. Procesamiento opcional de eventos de seguridad del hogar (humo, inundación, cámara caída y puerta abierta), confirmación humana antes de acciones externas.
6. Alerta configurable a contactos **seleccionados por el propietario**, tras consentimiento del destinatario y pruebas de entrega. No activar automáticamente llamadas policiales o mensajes públicos.
7. Registros de auditoría, pausa de cámaras, eliminación/expiración y revisión de alertas falsas.

Excluir explícitamente vigilancia encubierta, reconocimiento facial/biométrico policial, seguimiento masivo de personas, identificación por apariencia o decisiones automatizadas que afecten derechos.

## Satélites y mapas

- **Copernicus Browser:** `https://dataspace.copernicus.eu/browser/`. Datos de observación terrestre para riesgos, cambios territoriales e inundaciones.
- **NASA Worldview:** `https://worldview.earthdata.nasa.gov/`. Imágenes de observación con disponibilidad temporal variable.
- **INETER:** `https://www.ineter.gob.ni/geoportales/vulnerabilidades-amenazas/index.html`.
- **SINAPRED:** `https://www.sinapred.gob.ni/`.
- **Policía / Tránsito:** `https://www.policia.gob.ni/`, únicamente comunicación y recursos públicos.

Las imágenes satelitales públicas **no son video en directo de una calle** ni permiten identificar a una persona específica. La conexión a un satélite de telecomunicaciones es un proyecto distinto, con terminales, cobertura, permisos y costos. Esta primera versión **solo cataloga enlaces públicos**; no descarga automáticamente imágenes ni se conecta a un satélite.

## Colaboración eventual con instituciones

Se puede preparar un producto institucional con contratos y acreditaciones para asistencia administrativa, reportes de emergencias, gestión autorizada de infraestructura, educación vial, orientación ciudadana y monitoreo de desastres.

**No hay acceso hoy a redes, bases de datos, cámaras, expedientes ni canales de la Policía Nacional o Tránsito.** Para obtener cualquier integración hace falta autorización oficial, definición de propósito, protección de datos, registro de accesos, pruebas de seguridad y supervisión humana.

La Ley 787 de Protección de Datos Personales y la Ley 903 de Servicios de Seguridad Privada deben revisarse con asesoría jurídica antes de operar servicios comerciales de vigilancia. La inclusión de una cámara en el inventario de SKY no constituye licencia o permiso público.

## Evolución futura de «guardaespaldas digital»

- Comando voluntario de emergencia, confirmación del contexto y pantalla SOS.
- Estado de batería, red, dispositivos, cámaras y sensores **propios**.
- Protocolos personales de salida segura, contactos de confianza y compartición de ubicación puntual **solo opt-in**, sin rastreo de terceros.
- Integración con sensores domésticos autorizados y alertas por fallos verificables.
- Resúmenes preventivos de riesgos en rutas mediante información oficial y no discriminatoria.
- Modo sin conexión para consultar recursos previamente descargados y redactar alertas, sin fingir que envió comunicaciones.
- Verificaciones periódicas de disponibilidad, pruebas de alarmas y ejercicios simulados.

**No es garantía de protección física ni un sistema de alerta certificado** hasta completar implementación, validaciones y obligaciones correspondientes. Mantener la PR en borrador hasta las pruebas de CI y ensayos reales autorizados.
