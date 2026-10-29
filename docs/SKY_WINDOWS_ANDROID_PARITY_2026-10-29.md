# SKY IA — Paridad funcional Windows y Android
**Auditoría de código: 29 de octubre de 2026 · Repositorio: `OscarElieser/SKY`**

## 1. Contrato de producto

**Una sola SKY, dos adaptadores nativos.** Una orden debe producir el mismo resultado **observable** cuando el sistema operativo, permisos, recursos y servicios externos lo permitan. No copiar la implementación de Windows en Android ni obligar al móvil a conectarse a una PC. Conservar modo independiente en cada equipo.

- **SKY Core (común):** intenciones, tareas, contexto conversacional, categorías de riesgo, permiso por acción, registros verificables, respuesta honesta y contratos de datos.
- **SKY Windows (Python + HUD):** automatización del escritorio, Word COM, procesos locales autorizados, Ollama/modelos instalados, gestores de archivos, captura, notificaciones, aprendizaje e infraestructura específica de PC.
- **SKY Android (Kotlin + servicios del sistema):** Activity y servicio de voz autorizado, Storage Access Framework, Intents, Keystore, permisos Android, documentos OOXML nativos, animaciones de ojos y APIs móviles compatibles.
- **SKY API / núcleo conectado, opcional:** funciones que necesiten computación remota o un dato sincronizado. Autenticación por dispositivo, consentimiento explícito, cifrado, aislamiento por propietario, límites de cuota y protección anti-repetición. No descargar memorias o claves de Windows sin permiso; sin conectividad, continuar las funciones locales.

## 2. Inventario auditado (código ≠ funcionamiento validado)

La fuente de verdad **máquina-legible**, con ruta de archivo por categoría, está en
[`shared/sky_platform_parity.json`](../shared/sky_platform_parity.json). La revisión estática contiene **26 capacidades** y estados conservadores:

| Capacidad | Windows | Android | Próxima acción |
|---|---|---|---|
| Conversación contextual | Código | Código | Prueba de respuesta y latencia con ambos proveedores |
| Memoria privada | Código | Código | Definir sincronización cifrada optativa y borrado independiente |
| Voz y manos libres | Código | Limitada | Probar bloqueo y segundo plano físicamente |
| Verificar voz del creador | No demostrada | No demostrada | Inscripción biométrica local y test de imitaciones; nunca sustituir PIN |
| Modelo LLM sin nube | Dependiente de modelo instalado | No equivalente | Evaluar modelos compatibles con RAM y consumo móvil |
| Abrir aplicaciones | Código | Código | Confirmar apertura de apps representativas por sistema |
| Operar dentro de otras apps | Limitada | Limitada | Integraciones por app, consentimiento, comprobación del resultado |
| Música específica | Limitada | Limitada | Verificación de audio real, no solo de búsquedas/intents |
| Word, Excel y PowerPoint | Código | Código | Comparar archivos OOXML editables en ambos sistemas |
| PDF | Código | Lectura parcial | Exportación PDF equivalente desde Android |
| Archivos múltiples | Código | Limitado | Matriz de tipos/tamaños y pruebas de privacidad |
| Visión y generación de imagen | Código o condicionado | Código o condicionado | Comprobar respuestas reales de proveedores y costos |
| Video | Código | Limitado | Diferenciar MP4 local, edición y video de IA |
| Investigación y docencia | Código | Limitado | Fuentes académicas y entregables docentes comparables |
| Supervisor multiagente | Código | No equivalente | Diseñar ejecutor móvil y seguimiento de subtareas |
| Aprendizaje supervisado | Código | Limitado | Misma semántica de evidencia, nunca entrenamiento fingido |
| Redes sociales | Limitado | Limitado | OAuth y APIs oficiales; aprobación antes de publicar |
| 3D | GLB/2.5D en código | Perspectiva en ojos | Modelado/exportación 3D Android pendiente |
| Alarmas y avisos | Código | Limitado | Pruebas del sistema de alarmas y notificaciones |
| Seguridad y supervisión | Código | Código | Unificar niveles de riesgo sin compartir credenciales |
| Sincronización entre equipos | No demostrada | No demostrada | No implementada todavía como función de producto |
| Diseño premium | HUD | Ojos animados | Identidad común, UX nativa para cada pantalla |

**Nunca interpretar «Código» como «probado en tu dispositivo».** Las dependencias instaladas, credenciales, cuotas, licencias, permisos, restricciones del sistema y pruebas de usuario pueden cambiar el resultado. El inventario estático marca expresamente `runtime_verified=false`.

## 3. Requisitos de igualdad (aceptación por resultado)

Cada par de implementaciones necesita pruebas con: **orden original**, intención detectada, autorización presentada, ejecución real, archivo/acción final, estado de recibo (`VERIFICADA_LOCAL`, `ENVIADA_SIN_VERIFICAR`, `FALLIDA` o `RECHAZADA`), tiempo y evidencia, sin guardar contraseñas ni conversaciones no autorizadas.

1. «SKY, crea un documento Word sobre…»: Windows y Android generan un **DOCX real** que se abre y edita. Repetir con XLSX, PPTX y PDF donde exista exportación.
2. «SKY, abre YouTube y reproduce…»: ambas deben distinguir *app abierta*, *búsqueda enviada* y *reproducción audible comprobada*. Ningún sistema puede decir «ya suena» sin prueba.
3. «SKY, guarda este dato»: mismo significado de consentimiento, fecha, título, privacidad, edición y eliminación. La sincronización cruzada queda desactivada hasta que exista el flujo de aprobación.
4. «SKY, investiga y dame fuentes»: referencias con URL real, fecha, hechos verificados y proveedor. No inventar búsquedas.
5. «SKY, duerme» / «despierta» / «estate pendiente»: mismo comportamiento solicitado, pero distintos servicios nativos y límites reales de Windows/Android.
6. «SKY, envía esto a Instagram»: borrador y aprobación real, únicamente si se habilitó OAuth con los permisos necesarios; no confundir perfil guardado con acción publicada.
7. «SKY, aprende de esta corrección»: registrar corrección autorizada y resultado; no presentar adaptación de reglas como entrenamiento de pesos del LLM.
8. «SKY, detén todo»: mecanismos propios de cada equipo que dejen inhabilitadas las acciones que puedan detenerse, y confirmación visual.

**Alto riesgo:** borrar, enviar mensajes, hacer cambios irreversibles, operar en otra cuenta o mover archivos necesitan autorización específica, independientemente de un consentimiento general previo. Un reconocimiento de palabras, wake word o confirmación verbal no acredita la identidad biométrica.

## 4. Brechas priorizadas

**P0 — Estabilidad y verdad operacional.** La APK 0.8.29 aún está sin publicación aprobada en esta revisión. La compilación anterior falló por una prueba del bloqueo de sueño; se reparó la regla para requerir «SKY despierta» y se reejecutan los controles. Existen también 5 fallas en el flujo Windows de seguridad y regresión a revisar por separado, sin desactivar pruebas ni mezclar cambios de Android en el núcleo Windows.

**P1 — Paridad real de tareas:** crear y descargar documentos, reproducir música con estado comprobable, investigar con fuentes, control de aplicaciones bajo permisos, creación multimedia y manejo de archivos.

**P2 — Núcleo compartido opcional:** contrato de tareas/acciones/respuestas, identificación de capacidad por plataforma, selección del ejecutor (local Windows/local Android/API), evidencia, reintentos acotados y observabilidad. El teléfono **no depende** de Windows y viceversa.

**P3 — Capacidades todavía no equivalentes:** supervisor de subagentes en Android, modelo local compatible, PDF completo, creación 3D exportable, sincronización cifrada optativa y verificación biométrica de hablante con pruebas anti-suplantación.

## 5. Control de cambios

- Fuente auditable: `shared/sky_platform_parity.json`.
- Prueba automática: `tests/test_sky_platform_parity.py` valida cobertura del inventario, rutas de código, clasificación honesta y brechas críticas. **Es prueba estática**, no end-to-end.
- Evitar eliminar módulos existentes. Separar adaptadores nativos por plataforma; actualizar el inventario al añadir una capacidad y acompañarlo de pruebas de ejecución.
- Antes de afirmar igualdad completa: CI Windows, CI Android 15/16 y pruebas en hardware Windows y Samsung, con resultados reproducibles, deben aprobar.

_Objetivo: mismas funciones útiles, personalidades y políticas de confianza; implementaciones, límites y permisos distintos._
