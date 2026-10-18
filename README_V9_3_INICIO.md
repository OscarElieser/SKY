# SKY IA Universal v9.3 — Focus & Autonomous Workflows

**Concepción y visión de SKY IA: Oscar Elieser Chamorro Guzmán.**

Esta versión actualiza directamente SKY v9.2: mantiene sus módulos y reorganiza **la pantalla de inicio** para que el usuario vea una conversación y pocas opciones. Las capacidades completas quedan dentro de «Espacios» y los módulos existentes. Además incorpora automatizaciones persistentes en SQLite que usan exclusivamente herramientas locales permitidas y previamente aprobadas.

## Instalación en tu computadora

1. Instalá **Python 3.11 o 3.12** (recomendado). La instalación inicial requiere conexión para bajar dependencias si no las tenés.
2. Descomprimí el ZIP completo en una carpeta nueva.
3. Windows: ejecutá `INICIAR_SKY_V9_WINDOWS.bat`. Linux/macOS: `bash iniciar_sky_v9_linux_mac.sh`.
4. Abrí **http://127.0.0.1:8765/** o **http://127.0.0.1:8765/sky**. A diferencia de v9.2, esta es la portada mínima.
5. En **Acceso privado**, introducí la clave maestra SKY. Si no existe `SKY_API_KEY` en tu `.env`, el sistema genera una clave privada en `local_data/sky_api_token.txt` al arrancar.
6. Para cuentas de visitantes, utilizá el acceso de usuario con la cuenta creada mediante invitación desde la Comunidad SKY.

| Pantalla | Ruta | Acceso |
|---|---|---|
| Inicio mínimo SKY | `/` o `/sky` | Público; las conversaciones requieren sesión |
| Comunidad | `/community` | Cuenta personal por invitación |
| Metaverso 3D | `/world` | Edición por clave administrativa; comunidad en `/community` |
| Espacio de trabajo avanzado | `/studio` | Clave maestra |
| Office Studio | `/office` | Generación por clave maestra |
| Flujos automatizados | `/flows` | Clave maestra |
| Centro privado BAQUEANO | `/owner/baqueano` | Verificación de clave maestra, datos protegidos en servidor |
| API / OpenAPI | `/docs` | Documentación técnica; las rutas sensibles requieren autenticación |

**Importante:** la clave maestra acredita el control técnico de la instalación; **no demuestra la identidad legal de Oscar**. Para un despliegue comercial con más administradores necesitaremos un inicio de sesión de propietario verificado, segundo factor y separación de permisos administrativos. Nunca compartás esta clave con usuarios del metaverso.

## Inicio limpio, módulos internos

- Portada: logotipo, saludo, conversación, voz y botón «Espacios».
- El menú «Espacios» guarda los enlaces internos a mundos, comunidad, documentos, proyectos y API. Las herramientas avanzadas no ocupan la pantalla inicial.
- BAQUEANO **no aparece en el HTML de la portada ni para sesiones de visitantes**. Su enlace se crea dinámicamente solo después de comprobar la clave del propietario contra `/api/sky/owner/baqueano`.
- Un token de usuario de la comunidad nunca autoriza el endpoint BAQUEANO ni otros endpoints de propietario.
- Un usuario normal puede iniciar sesión con su cuenta SKY y utilizar el asistente local autorizado, sin tener acceso a los proyectos administrativos del creador.
- El chat del propietario puede elegir proveedores configurados; ninguna clave de IA se incluye en la distribución.

## Autonomous Workflow Engine: qué hace de verdad

Se implementaron servicios reales:

- **Persistencia:** SQLite `local_data/sky_workflows.sqlite3`; estados y bitácora de acciones.
- **Agentes del catálogo controlado:** `planificador`, `creador_3d`, `diseñador`, `documentalista`, `memoria`.
- **Flujos de 1 a 8 pasos**, con nombre, parámetros, proyecto opcional, fecha de ejecución y repetición por intervalos.
- **Aprobación obligatoria por el propietario** antes de cualquier ejecución. Ningún flujo nuevo arranca automáticamente.
- **Ejecución desatendida** después de la aprobación, mientras el proceso SKY esté encendido; cada paso usa el Workbench real de SKY.
- **Resultados y seguimiento:** IDs de tareas, documentos descargables, mundos creados y diseños, historial de eventos y vinculación al Project Hub.
- **Reinicio seguro:** la siguiente ejecución recupera el estado persistido. Si un efecto pudo haberse ejecutado parcialmente, SKY se detiene en `needs_review` antes de repetirlo.
- **Reintentos:** automáticos y limitados para pasos de planificación; reintentos de acciones que escriben datos exigen revisión y una nueva confirmación.
- **Cancelación:** disponible mientras no se esté ejecutando un paso; no interrumpe violentamente operaciones a mitad de escritura.
- **Respaldo:** `python sky_backup.py` incluye los archivos de flujos y proyectos si existen.

**La autonomía significa ejecución de tareas aprobadas, NO control indiscriminado.** No ejecuta pagos, transferencias, órdenes arbitrarias, ataques, cambios en BAQUEANO de producción, instalaciones o despliegues. La recurrencia que genera documentos/mundos/recuerdos tiene un intervalo mínimo de 60 minutos para reducir consumo accidental.

### Crear tu primera automatización

1. Entrá en `http://127.0.0.1:8765/flows` con tu clave privada.
2. Escribí el nombre del flujo; opcionalmente elegí un proyecto del Project Hub.
3. Añadí un paso de **Planificación** y escribí el resultado esperado.
4. Añadí un paso de **Documento** y especificá el contenido real y su formato.
5. Pulsá **Preparar flujo para aprobación**. En ese momento no se ejecuta nada.
6. Revisá los pasos y pulsá **Autorizar**. SKY empezará al llegar la hora programada.
7. Actualizá «Seguimiento y resultados» para ver el estado; descargá el archivo desde el resultado completado.

Los proveedores externos OpenAI, Gemini, Claude, etc. **no se invocan desde este motor de ejecución** sin un conector opt-in futuro; se mantienen disponibles en las funciones de conversación que ya existían.

## Migrar desde v9.2 sin perder tus datos

1. Detené por completo SKY v9.2.
2. Creá un respaldo de `local_data/`, tu configuración `.env` y los archivos de salida creados.
3. Extraé v9.3 en otra carpeta: **no mezcles versiones por sobrescritura**.
4. Copiá tu `local_data/` completo y `.env` en tu propia computadora nueva, con el servidor apagado. No los subás a GitHub, ni al chat, ni a un ZIP público.
5. Ejecutá `python sky_preflight.py --json` y comprobá que las bases de datos anteriores estén correctas. `sky_workflows.sqlite3` se crea la primera vez que se utiliza la API de flujos.
6. Ejecutá `python -m pytest -q` con `pytest` y `httpx` instalados.
7. Iniciá SKY. Tus proyectos y documentos anteriores mantienen sus IDs. El metaverso que antes estaba en `/` ahora se abre en `/world`.

## Opciones avanzadas del servidor

- Solo uso personal: `python -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765 --workers 1`.
- Desactivar temporalmente el motor automático sin borrar los trabajos: `SKY_WORKFLOWS_ENABLED=0` en el entorno del proceso; al volver a activarlo revisará los trabajos pendientes que estén vencidos.
- No se deben ejecutar múltiples trabajadores Uvicorn sin migrar WebSocket presence y la coordinación de trabajos a una arquitectura compartida.
- Para Internet público hacen falta HTTPS, rate limiting, autenticación de creador verificable, evaluación de privacidad, backups externos, pruebas de carga, colas de trabajo distribuidas, supervisión y mitigación de abuso.
- `sky_preflight.py` analiza dependencias y bases SQLite locales. No afirma certificación de hardware ni de proveedores externos.

## Validación alcanzada

- **140 pruebas automatizadas pasaron** con el entorno de desarrollo utilizado, incluyendo 131 heredadas de v9.2.
- Comprobación HTTP real de Uvicorn: creación, aprobación y ejecución en segundo plano de una tarea mediante API. Los resultados se guardaron en SQLite.
- Regresión de roles: token de visitante autenticado no puede consultar Control Center BAQUEANO ni automatizaciones privadas.
- Pruebas de DOCX generado realmente, mundos 3D enlazados, respaldo SQL, recurrencia, cancelación, recuperación y revisión de ejecución ambigua.
- Renderizado con Chromium de la portada en escritorio y móvil y del editor de flujos **con datos de prueba**. La conexión directa de Chromium a localhost estuvo bloqueada por el entorno; no se presenta esa visualización como prueba de servidor real.

SKY v9.3 **no se ha desplegado al público**, no se han modificado sistemas de producción y no se han validado proveedores de IA externos ni dispositivos físicos. No es un certificado de disponibilidad mundial.

## Archivos de referencia

- `CHANGELOG_V9_3.md` — diferencias respecto de v9.2.
- `SKY_WORKFLOW_API.md` — endpoints y permisos.
- `VALIDACION_V9_3.md` — pruebas y limitaciones.
- `ARQUITECTURA_SKY.md` y demás manuales heredados — módulos anteriores.
- `MANIFEST_SHA256_V9_3.txt` — comprobación de integridad de archivos empaquetados.

---
**SKY IA — visión y autoría conceptual: Oscar Elieser Chamorro Guzmán.** El presente texto documenta el proyecto y no sustituye el registro oficial de marca o de software.
