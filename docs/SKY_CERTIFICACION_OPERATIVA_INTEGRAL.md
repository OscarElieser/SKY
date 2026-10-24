# SKY IA — Plan de certificación operativa integral

**Fecha base:** 2026-10-24. **Alcance:** SKY CORE y API propia FastAPI,
voz/texto, Windows, Android, investigación, docencia, teléfono, skills,
integraciones, seguridad, recuperación y métricas.

## Regla de aceptación

**No existe certificación operativa integral hasta obtener evidencias
reproducibles en equipos y cuentas reales.** Un test de GitHub con mocks prueba
lógica y contratos, NO demuestra que una SIM llamó, que Windows abrió Word,
que un alumno recibió la clase, o que un artículo completo fue analizado.

Estados por operación:
- **BLOCKED / NEEDS_CONFIGURATION:** falta permiso, clave, instalador,
  conectividad, contrato o cuenta autorizada;
- **READY:** puede realizar una prueba en entorno real;
- **DISPATCHED:** se envió la instrucción; NO es éxito final;
- **VERIFIED:** evidencia objetiva comprobada sobre el resultado;
- **FAILED:** evidencia de fallo, error de proveedor o política;
- **CERTIFIED:** solamente después del conjunto de pruebas físicas, funcionales,
  seguridad, privacidad y revisión humana independiente.

Registrar para cada evidencia la versión SHA de GitHub, sistema operativo,
modelo/dispositivo, versión de dependencias, configuración sin secretos,
fecha/hora, identificador de tarea sin PII, resultado y evidencia de la acción.
No guardar el número real del propietario, contraseñas, voz, mensajes, claves ni
datos de estudiantes en informes públicos.

## Arranque y pruebas reales sin cargos

En Windows, desde la raíz del repositorio, con SKY previamente instalado:

```powershell
SKY_INICIAR.bat
.\.venv\Scripts\python.exe iniciar_sky_autonomo.py --status
.\.venv\Scripts\python.exe scripts/sky_integral_operational_check.py --research-live
.\.venv\Scripts\python.exe scripts/sky_api_smoke_windows.py
```

La opción `--research-live` hace una solicitud real de metadatos a Crossref,
pero no verifica el texto completo de artículos.

**Prueba con acción física autorizada** (abre calculadora y crea un DOCX
en una carpeta de prueba; no elimina archivos):

```powershell
.\.venv\Scripts\python.exe scripts/sky_e2e_pc_real.py --confirm --app calculator
```

Comprobar el informe real en Documentos/SKY_E2E; debe tener
`overall_pass=true`, cada paso comprobable `physically_verified=true` y
archivo DOCX válido. Repetir con Word/Excel/PowerPoint si están instalados
y expresamente permitidos; observar la ventana visible y corroborar el
contenido del documento. Hacer tests separados de voz continua/manual,
barge-in, reproductores multimedia y recuperación después de reinicio.

## Darle un número a SKY Teléfono

**Vía SIM móvil sin Twilio:** abrir SKY en Chrome Android mediante HTTPS privado,
iniciar sesión, entrar en «Teléfono», introducir destino internacional E.164,
por ejemplo `+505XXXXXXXX` (no almacenar un número real en esta guía) y elegir
«Abrir marcador del móvil» o «Abrir SMS del móvil». SKY consulta la lista de
bloqueos, pide consentimiento y ofrece un SEGUNDO enlace. El sistema Android
realiza la operación cuando la persona confirma. Claro/Tigo/otra operadora
factura según el plan de esa SIM. Desde Windows un navegador puede no disponer
de marcador ni gestor SMS.

**Vía plataforma de telefonía:** para SMS real saliente o llamadas puente
reales desde SKY hacen falta credenciales Twilio de la cuenta propietaria,
un número/servicio habilitado, OTP verificado, PIN SENTINEL, activación
consciente de los flags `SKY_PHONE_ENABLED`, `SKY_PHONE_ALLOW_VERIFY`,
`SKY_PHONE_ALLOW_PAID`, destinos internacionales autorizados, saldo y
consentimiento del destinatario. No publicar esos valores en GitHub/chat.
No ejecutar una llamada de prueba de pago sin autorización y destinatario real.

Los resultados `queued_unverified` sólo confirman aceptación/encolado del
proveedor: los recibos de entrega y callbacks autentificados deben verificar
el resultado final. Llamadas/SMS entrantes, bloqueo de toda la telefonía
del Android e interfaz de llamada directa requieren la ampliación nativa
Android con sus roles y permisos; la PWA NO sustituye un agente nativo.
Emergencias permanecen bajo el marcador oficial del dispositivo.

Opcional, validación de un destino sin llamar:
```powershell
.\.venv\Scripts\python.exe scripts/sky_integral_operational_check.py --target-number +505XXXXXXXX
```

## Matriz obligatoria de aceptación

| Dominio | Evidencia requerida para aprobar | Estado inicial |
|---|---|---|
| Investigación académica | Búsqueda real, DOI/editorial, recuperación autorizada del texto, afirmaciones contrastadas con pasajes y fechas | SIN CERTIFICAR |
| SKY Docencia | Clase completa por voz, preguntas adaptativas, video con contenido realmente leído, escena 3D interactiva, rúbrica por currículo, exportación DOCX | SIN CERTIFICAR |
| Windows | Programas y archivos efectivamente abiertos/creados, multimedia, trayecto voz->agente->resultado, evidencia verificable | SIN CERTIFICAR |
| Conversación | Micrófono, TTS, escucha libre/manual, interrupción natural, latencia y ausencia de respuestas inventadas | SIN CERTIFICAR |
| Android | Instalación en teléfono real, HTTPS privado, permisos, controles, suspensión/reanudación; APK/funciones nativas solo cuando exista su implementación | SIN CERTIFICAR |
| SKY Teléfono | Número propietario verificado, llamada/SMS en destino consentido, estado final de proveedor/SIM, Jitsi efectivo, bloqueos y costos | SIN CERTIFICAR |
| Skills e integraciones | Manifiesto por skill, licencia, autorización, cuenta conectada, llamada API real, resultado observado y revocación | SIN CERTIFICAR |
| Seguridad y continuidad | Acceso denegado sin token/PIN/MFA, paradas, datos privados, recuperación sin doble ejecución, backup restaurado | SIN CERTIFICAR |

**Criterio estricto de liberación:** todas las filas completas con evidencia
de hardware/proveedor verificada, seguimiento de errores y validación humana.
Los porcentajes de CI, catálogos de skills y probes de lectura NO reemplazan
esa evidencia. No publicar "100% operativo" basándose en flags o documentación.

## Mejoras de código de esta fase

- `factcheck_engine.py`: no toma menciones a OMS/UNESCO/INIDE como
  corroboración. Los cálculos comprobados con CAS conservan su ruta propia.
- `windows_controller.py`: Linux/macOS no devuelven una falsa evidencia
  positiva mediante el verificador Windows.
- `sky_phone.py`: declara correctamente la transferencia nativa existente;
  no supone llamada ni SMS completados.
- `sky_aula_assessment.py`, `academy_api.py`, `hud.js`: pesos editables
  de conocer/hacer/ser en API y HUD; validados para que sumen 100; el docente
  continúa aprobando toda calificación final.
- `sky_integral_operational_check.py`: diagnóstico ejecutable, autenticado
  sobre API local y Crossref real bajo opción explícita. Nunca genera cargos.
- Pruebas de regresión en CI para que estos cambios no reviertan.

## Trabajo adicional imprescindible, no implementado en esta fase

1. **Motor aplicado:** consolidar planificación, ejecución, observación,
   reintentos idempotentes, memoria entre dispositivos y recuperación
   persistente de ciclos con autorización por operación.
2. **Investigación confiable:** recuperar texto completo legalmente disponible,
   comprobar la correspondencia cita-DOI-documento, revisar contradicciones y
   fechas; no afirmar que el título/metadato prueba el resultado del estudio.
3. **Docencia global:** biblioteca curricular verificada por país/institución,
   adaptación pedagógica con evidencias, accesibilidad, simuladores GLB
   por disciplina y evaluación longitudinal consentida.
4. **Android nativo:** crear, compilar, firmar, instalar y probar aplicación con
   módulo de permisos nativos y vínculo seguro con SKY CORE. Sin Android SDK,
   teléfono y aceptación del usuario no puede certificarse aquí.
5. **Comunicaciones entrantes y directas:** backend de telefonía oficial,
   callbacks firmados, estados de entrega, límites económicos, roles Android
   apropiados para filtrado/llamadas y pruebas con números reales consentidos.
6. **MCP/OAuth:** conectores configurados y probados individualmente
   (Google, GitHub, correo, etc.), alcance mínimo, revocación y costo observado.
7. **GitHub:** proteger la rama `main` con rulesets/reviews/CI obligatorio y
   verificar que no existan rutas de bypass innecesarias.
8. **Calidad:** pruebas sobre Windows + Android, cobertura E2E, disponibilidad,
   tasa de tareas verificadas, p95 de latencia, error STT/TTS, costos y
   recuperación de desastres, con criterios SLO específicos.

## Documentación oficial de plataformas

- Android ACTION_DIAL vs ACTION_CALL: https://developer.android.com/guide/components/intents-common
- Android CallScreeningService: https://developer.android.com/reference/android/telecom/CallScreeningService
- Twilio Voice Calls API: https://www.twilio.com/docs/voice/api/call-resource
- YouTube Data API Search: https://developers.google.com/youtube/v3/docs/search/list

**Política de seguridad:** nunca introducir secretos en repositorios, en
consultas de IA o en pruebas públicas; las operaciones de pago y control de
dispositivos necesitan autorización explícita y evidencia física.
