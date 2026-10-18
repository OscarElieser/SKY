# SKY IA v9.2 — Experience & Reliability / Project Hub

**Concepción y visión de SKY IA: Oscar Elieser Chamorro Guzmán.**

La versión v9.2 incorpora **continuidad real entre módulos**. Mantiene los componentes
existentes (metaverso 3D, comunidad, voz, Neural Core, múltiples proveedores IA,
Office Studio, BAQUEANO Control Center, seguridad local, sensores, planes y diseño).
El nuevo Project Hub agrupa trabajo que ya puede crear SKY en proyectos privados.

## Instalación y arranque

Recomendado: Python 3.11 o 3.12. Requiere espacio de disco e Internet para instalar
las dependencias iniciales. Después, las operaciones locales del Project Hub no
necesitan suscripción ni proveedor IA.

- **Windows:** extraer el ZIP y ejecutar `INICIAR_SKY_V9_WINDOWS.bat`.
- **Linux / macOS:** `bash iniciar_sky_v9_linux_mac.sh`.
- **Servidor SKY:** `http://127.0.0.1:8765/studio`.
- Primera ejecución: la clave maestra se crea en `local_data/sky_api_token.txt`.
  Usarla en SKY Studio, sin compartirla ni subirla a repositorios públicos.
- Para verificar las instalaciones: `python sky_preflight.py --json`.
- Para repetir pruebas: `python -m pytest -q` (instalar `pytest` y `httpx` si faltan).

**La clave maestra da acceso administrativo a datos y artefactos locales.** No usar
estas rutas como si fueran las cuentas de los visitantes de la red social.

## Flujo integrado de SKY

1. En **SKY Studio → Project Hub**, crear un proyecto con nombre y objetivo.
2. Seleccionar el proyecto activo en la lista.
3. Escribir el objetivo; SKY local identifica roles y prepara un plan. El texto de
   modelos externos se genera únicamente si el usuario selecciona un proveedor.
4. Desde **Entregables**, crear un documento Word/Excel/PPT/PDF, diseño editable,
   mundo procedimental o nota. Confirmar la ejecución.
5. SKY vincula la tarea al proyecto. Desde su panel se ve el estado y los archivos.
6. Para asociar un mundo, diseño o tarea anterior, ingresar su ID y usar **Vincular**.
7. Las conversaciones se guardan *solo* si está seleccionado un proyecto y activado
   **Guardar conversación**. Se pueden consultar y eliminar.
8. **Descargar proyecto ZIP** incluye resultados reales, documento Office, diseño
   HTML + especificación JSON, mundo JSON + GLB si la exportación está disponible,
   y `proyecto.json` con metadatos. No incluye claves, chat ni notas privadas.

La vinculación no mueve ni borra el archivo original. Una referencia a un elemento
eliminado puede aparecer como `no_disponible`.

## Privacidad y contexto

- Los proyectos se almacenan en `local_data/sky_projects.sqlite3` mediante SQLite.
- El dueño elige explícitamente si manda la descripción del proyecto, sus títulos
  o mensajes anteriores a OpenAI, Anthropic, Gemini u otro modelo.
- El **guardado local** de una conversación es diferente de **compartirla** con
  un proveedor externo. Ambas opciones son independientes.
- No se guardan conversaciones si no hay un proyecto seleccionado y la casilla
  está desmarcada.
- El chat local no invoca herramientas de forma autónoma; las creaciones tienen
  confirmación previa y resultados verificables.
- Todo el panel de proyectos requiere `X-SKY-KEY`.
- Cada ZIP exporta únicamente los resultados vinculados a ese proyecto y
  omite notas privadas y chats. Revisar su contenido antes de compartirlo.

## Actualizar desde v9.1 sin perder datos

1. Hacer copia de seguridad de la carpeta anterior `local_data/` y del `.env`.
2. Descomprimir el nuevo paquete en una **carpeta separada**.
3. Copiar `local_data/` al nuevo proyecto **solo con SKY v9.1 detenido**.
4. Copiar y revisar el `.env` únicamente en tu equipo, sin incluirlo en el ZIP.
5. Ejecutar el diagnóstico y las pruebas; confirmar que aparece el historial.
6. Si hay conflictos entre cambios propios del código v9.1 y los archivos v9.2,
   revisar el diff; no sobrescribir cambios locales a ciegas.

La base `sky_projects.sqlite3` se crea al abrir un proyecto por primera vez.
Las versiones antiguas no tenían Project Hub, por lo que los artefactos existentes
podrán **vincularse** manualmente por ID en esta versión.

## Alcance validado y pendientes

- **131 pruebas automatizadas superadas**, incluidas las 120 heredadas.
- Flujo navegador con Chromium y backend FastAPI de pruebas: inicio de sesión,
  creación de proyecto, chat local, creación visual y guardado enlazado;
  sin errores JavaScript observados.
- HTTP local Uvicorn: ruta `/studio` responde; APIs protegidas probadas con TestClient.
- El entorno bloquea la visita directa de Chromium a localhost; la prueba visual
  pasó con un transporte controlado que ejecutó las rutas FastAPI reales.
- **No** probamos los proveedores externos con credenciales, micrófonos físicos,
  grandes volúmenes concurrentes, ni un despliegue público. No afirmamos SLA.
- No se modificó ni desplegó BAQUEANO en producción.

La v9.2 es una versión local integrada, no una red social pública terminada ni una
AGI capaz de realizar cualquier tarea sin conectores, permisos o recursos.

Consulta [`SKY_PROJECT_HUB_API.md`](SKY_PROJECT_HUB_API.md) para las nuevas rutas.
