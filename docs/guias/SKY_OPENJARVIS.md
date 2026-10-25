# SKY IA + OpenJarvis (integración opcional)

## Regla principal

**SKY es el sistema principal.** OpenJarvis se conecta como motor adicional
de respuesta textual; no reemplaza la API FastAPI de SKY, voz, HUD, memoria,
permisos, control de Windows, docencia ni dispositivos.

- Por defecto está **DESACTIVADO**.
- No pertenece a la selección automática de motores, y no hay cambio
  silencioso a otro proveedor si OpenJarvis falla.
- Las peticiones salen de SKY únicamente a `http://127.0.0.1:<puerto>/v1/chat/completions`.
- El puerto es configurable; la IP no. No se permite redireccionar ni usar
  proxy HTTP para ese destino.
- No se comparten tokens de SKY, comandos, permisos ni herramientas con el
  servidor OpenJarvis. Los mensajes de texto elegidos sí se envían al servidor
  OpenJarvis configurado.
- Antes de cada conversación SKY exige que `GET /v1/info` informe
  `agent=simple` y un motor local permitido; ante agentes con herramientas
  o motores de nube, **rechaza la conexión**. No se soportan versiones del
  servidor que no ofrezcan dicho endpoint.
- OpenJarvis, como servidor separado, puede tener sus propias herramientas o
  motores de nube. **Debe arrancar con `--agent simple` y un backend local**:
  no otorgarle herramientas de ejecución, archivos, navegador ni credenciales.
  SKY no controla los complementos que alguien instale dentro de OpenJarvis.
- El modo estricto `SKY_LOCAL_ONLY=1` sigue usando solo Ollama como antes.
  No se modifica esta garantía hasta verificar un modo local estricto también
  en el proceso separado.

## Preparación en Windows (instalación separada)

Antes de instalar, hacer respaldo del entorno SKY y verificar espacio,
Python, Git, conectividad y documentación vigente de OpenJarvis:

- Código: https://github.com/open-jarvis/OpenJarvis
- Servidor: https://open-jarvis.github.io/OpenJarvis/deployment/api-server/
- Instalación: https://open-jarvis.github.io/OpenJarvis/getting-started/installation/

Usar **otra carpeta** para OpenJarvis, nunca instalarlo en `SKY/.venv`.
Ejemplo en PowerShell si tenés `git` y `uv` disponibles:

```powershell
cd $HOME
git clone https://github.com/open-jarvis/OpenJarvis.git
cd OpenJarvis
uv sync --extra server
```

Ollama debe estar ejecutándose y el modelo ya descargado. Consultá
`ollama list` para elegir un modelo existente (ejemplo: `qwen2.5:7b`).
En otra terminal:

```powershell
cd $HOME\OpenJarvis
uv run jarvis serve --host 127.0.0.1 --port 8000 --engine ollama --model qwen2.5:7b --agent simple
```

Usar un puerto distinto si el 8000 ya está ocupado. Nunca usar
`--host 0.0.0.0` para este puente local, especialmente sin autenticación.

Comprobar sin enviar prompts:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/v1/info
Invoke-RestMethod http://127.0.0.1:8000/v1/models
```

## Conectar a SKY sin modificar la instalación principal

En el **.env local de SKY** (no subirlo a GitHub):

```dotenv
SKY_OPENJARVIS_ENABLED=1
SKY_OPENJARVIS_MODEL=qwen2.5:7b
SKY_OPENJARVIS_PORT=8000
```

`SKY_OPENJARVIS_MODEL` debe coincidir con el identificador devuelto por
`/v1/models`. Reiniciá solo el proceso de SKY que cargue ese archivo.

En el selector **Motor de IA** de SKY elegí **OpenJarvis local (opcional)**.
`auto` seguirá usando la lógica actual de SKY. Una conversación por
OpenJarvis no da permiso para abrir apps, modificar archivos ni ejecutar código.

### Comprobación local

Desde la carpeta SKY:

```powershell
.venv\Scripts\python.exe -m neural_core.sky_openjarvis
.venv\Scripts\python.exe sky_diagnostico.py
.venv\Scripts\python.exe -m pytest -q tests/test_sky_openjarvis_integration.py
```

El estado debe indicar `healthy: true` y `model_available: true`.
Las pruebas unitarias son simuladas y **no prueban** que OpenJarvis esté
instalado, ni el rendimiento, ni el control de dispositivos reales.

SKY registra la latencia, éxito y tokens si el servidor los informa en su
base propia de KPI (`sky_metricas`), sin guardar texto de las conversaciones.
OpenJarvis también tiene telemetría local independiente; no se sincronizan
ni mezclan memorias o bases de datos.

## Desconectar o recuperar SKY

Cambiar `SKY_OPENJARVIS_ENABLED=0`, reiniciar SKY y volver a seleccionar
`auto` u `ollama`. SKY no depende del proceso OpenJarvis para arrancar.
Si OpenJarvis falla durante una llamada, SKY informa el error, no afirma
éxito ni cambia automáticamente a un motor de nube.

## Alcance explícito

Esta fase integra un **proveedor real de chat** con protocolo HTTP, selector,
diagnóstico y KPI. No instala OpenJarvis en computadoras del usuario, no
integra sus agentes de herramientas ni fusiona memoria, y no demuestra
funcionamiento de hardware. La integración de agentes con acciones requerirá
un puente de permisos aprobado por SKY SENTINEL y pruebas adicionales.
