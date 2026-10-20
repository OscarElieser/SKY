# SKY IA Universal v9.1 — Integración y estabilidad

**Visión, concepción y dirección del proyecto:** Oscar Elieser Chamorro Guzmán.  
**Origen:** SKY IA v9.0 Experience Orchestrator. **Este paquete conserva los módulos y archivos de v9.0** y aplica una actualización incremental comprobable.

## Cambios reales de v9.1

- Nuevo **Centro de Integración** visible en `/studio`: consulta dependencias de Python y verifica mediante `PRAGMA quick_check` la integridad de las bases SQLite existentes, sin modificarlas.
- Nuevo endpoint **autenticado** `GET /api/sky/integrations`. No expone rutas, contraseñas, nombres de archivos de usuario ni secretos. Distingue `ready`, `degraded` y `attention_required`.
- Nueva utilidad local `python sky_preflight.py` (admite `--json`) para comprobar componentes antes de iniciar SKY; también integrada en los lanzadores Windows, Linux y macOS.
- Corrección del **Visual Creator**: al cambiar una instrucción, título, plantilla, color o dictado de voz se invalida la vista previa previa. Guardar diseño exige una vista previa vigente y congela explícitamente su estructura, secciones y descripción, evitando exportar otra versión por accidente.
- Servidor identifica `9.1.0` en el API y el panel.
- Cuatro nuevas pruebas de integración cubren autenticación, comprobación de solo lectura, fallo de SQLite, flujo conjunto de memoria + mundo + diseño + PowerPoint y presencia de controles UI.

## Instalación local

1. Instalar **Python 3.11 o 3.12**.
2. Descomprimir el archivo ZIP completo (no ejecutar Python dentro de ZIP).
3. Ejecutar **`INICIAR_SKY_V9_WINDOWS.bat`** en Windows o `bash iniciar_sky_v9_linux_mac.sh` en Linux/macOS.
4. Abrir `http://127.0.0.1:8765/studio` y usar la clave privada que se crea en `local_data/sky_api_token.txt`.
5. Después de iniciar sesión, entrar en **Diagnóstico integrado** → **Comprobar módulos**.

También puede utilizarse manualmente:

```bash
python -m pip install -r requirements_studio.txt
python sky_preflight.py
python -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765
```

**Este programa opera localmente y no publica SKY ni BAQUEANO en Internet.** Para herramientas IA externas hacen falta las claves propias. Para el panel Streamlit heredado, utilizar `INICIAR_WINDOWS.bat` y sus otras dependencias documentadas.

## Pruebas y validación

```bash
python -m pip install pytest httpx
python -m pytest -q
python -m compileall -q neural_core metaverse
node --check metaverse/static/studio.js
```

**Resultados de esta entrega:** 120 pruebas automatizadas superadas; `uvicorn` iniciado en localhost y consultado por HTTP real con una clave de prueba; endpoint de integración autenticado; sintaxis JavaScript comprobada. Las bases de prueba se crearon en directorios temporales.

**Pendiente de validar:** pantalla visual en el navegador definitivo, micrófono/cámara, conectores IA con claves reales, despliegue público, concurrencia a gran escala, seguridad empresarial y resiliencia ante fallo de servidor. Un diagnóstico `ready` **no** certifica todos esos aspectos.

## Conservación del proyecto

- Se conservan las API de mundos, metaverso social, Workbench y Office Studio.
- No se altera el repositorio GitHub de BAQUEANO ni sus datos en producción.
- No se incluyen tokens reales, historial privado ni bases con usuarios reales.
- Se mantienen los archivos técnicos y documentos de autoría originales.

## Evolución posterior recomendada

1. **Calidad de integración:** contratos API versionados, pruebas de navegador y backups restaurables.
2. **Infraestructura pública:** PostgreSQL, Redis, TURN, HTTPS, observabilidad, escalado y auditorías.
3. **Creación inmersiva:** escenas 3D editables avanzadas, animación, multimedia y economía de creadores con pagos verificados.

**Criterio operativo:** solo se considera implementada una capacidad cuando existen código, prueba y evidencia del resultado. Nunca mostrar métricas de producción inventadas.
