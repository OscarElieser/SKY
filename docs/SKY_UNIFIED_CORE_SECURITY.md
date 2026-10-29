# SKY IA — Una sola identidad, dos entornos seguros

**Estado: integración inicial de política compartida · 29/10/2026. No es una migración de bases de datos ni una sincronización entre dispositivos.**

## Qué se ha integrado realmente

- `shared/sky_platform_parity.json`: auditoría de 26 capacidades, con sus pruebas pendientes.
- `shared/sky_core_contract_v1.json`: contrato compartido de SKY Core, con 21 intenciones autorizables, orígenes de confianza, niveles de riesgo y estados de evidencias.
- `neural_core/sky_core_contract.py`: lector y verificador de política para SKY Windows.
- `mobile/android-agent/app/src/main/assets/sky_core_contract_v1.json` + `SkyCoreContract.kt`: copia versionada consumida por SKY Android de forma nativa. Las pruebas exigen **igualdad byte por byte** entre ambas políticas.
- La función `requiere_confirmacion` de Windows usa el contrato para reforzar confirmaciones en notas, documentos, ventanas y operaciones sociales. En Android, guardar una nota requiere una aprobación específica antes de su escritura.
- Pruebas Python de orígenes de confianza, denegación por defecto, evidencias y permisos; pruebas instrumentadas Android 15/16 del contrato.

**SKY seguirá siendo una sola asistente como producto**, con experiencia y reglas coherentes; **no** una única aplicación binaria ni un proceso Windows obligado a estar encendido para que funcione Android.

## Mismo contrato, dos ejecutores nativos

| Regla | Windows | Android |
|---|---|---|
| Intenciones y autorizaciones | Contrato común Python | Contrato común Kotlin y JSON |
| Ejecutor de acciones | Agente local, política por dispositivo y Windows APIs | Activity, Intent, Storage Access Framework y permisos Android |
| Contraseñas y llaves | Fuera del repositorio | Android Keystore y preferencias protegidas |
| Historial y memoria | Datos propios del usuario en Windows | Datos privados del teléfono |
| Control del sistema | Ventanas y aplicaciones con autorización | Aplicaciones e Intents según el sistema y pantalla bloqueada |
| Tareas que necesitan nube | Bajo aprobación y credenciales de cada equipo | Bajo aprobación y credenciales de cada equipo |

Ninguna clave privada o permiso se sincroniza automáticamente entre equipos. El contrato **no** implementa todavía una autenticación remota ni el intercambio de archivos, memorias, chats o tareas. Esas funciones requerirán un protocolo seguro optativo, consentimiento, autenticación fuerte, aislamiento por propietario, cifrado, expiración y controles contra repetición; no exponer directamente el puerto del agente Windows a internet.

## Modelo de riesgo obligatorio

- **Bajo:** conversación, lectura pública, crear borradores y abrir interfaces según permisos. Nunca constituye éxito sin comprobación de resultados.
- **Medio:** guardar/modificar datos, editar archivos y ventanas, compartir borradores; aprobación concreta de cada acción.
- **Alto:** eliminar archivos, publicar, enviar mensajes o correos, pagos, cambiar permisos o controlar equipos remotos; además de la aprobación por acción requiere confirmación **desde una interfaz local confiable**. El reconocimiento de voz no equivale a identidad biométrica.
- **Prohibido:** órdenes arbitrarias de shell, vulnerar el bloqueo de pantalla, desactivar Play Protect o los controles de seguridad y extraer secretos.
- **Origen no confiable:** texto devuelto por IA, documentos, páginas web, mensajes de terceros y servidores remotos. No ejecutan acciones ni conceden permisos.
- **Denegar lo desconocido:** un contrato ausente, corrupto, con esquema desconocido o una acción no clasificada no habilita una tarea.
- **Evidencia:** `ENVIADA_SIN_VERIFICAR` nunca se contabiliza como `VERIFICADA_LOCAL`.

Los controles existentes del sistema operativo siguen activos. Un `allowed` del contrato significa **elegible bajo esta política**, no que la acción fue completada, que el usuario está autenticado o que una aplicación de terceros permite operar su interfaz.

## Migración sin perder lo construido

1. No renombrar paquetes Android, sobrescribir bases de datos, eliminar módulos Windows ni mover llaves de firma.
2. Agregar capacidades de SKY Core como interfaces/adaptadores progresivos, manteniendo rutas y configuraciones actuales hasta tener pruebas de regresión.
3. Incorporar en ambas plataformas el mismo vocabulario de capacidades y riesgos; registrar recibos verificables, latencia y errores de forma privada.
4. Comparar salidas DOCX/XLSX/PPTX, voz, control de aplicaciones y consultas con pruebas reales en ambos equipos.
5. Sólo añadir sincronización voluntaria después de pasar auditoría de autenticación, cifrado y políticas de borrado; no exigir conexión a Windows para el uso de Android.
6. No entregar una nueva APK hasta que compilen las variantes, aprueben las pruebas y se confirme el certificado de firma esperado.

## Estado y límites

La política común y su adopción inicial **no** implican paridad de todas las funcionalidades: memoria sincronizada, modelos LLM locales en Android, agentes equivalentes, edición completa de apps de terceros, verificación biométrica de voz y reproducción musical confirmada siguen pendientes. Cada capacidad debe registrarse como código, validación automática y validación en dispositivo real por separado.

Ver [matriz de capacidades](../shared/sky_platform_parity.json) y [auditoría de paridad](SKY_WINDOWS_ANDROID_PARITY_2026-10-29.md).
