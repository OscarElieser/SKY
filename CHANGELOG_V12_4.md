# SKY IA v12.4: catálogo de habilidades, SKY Skill Builder, integraciones y creación multimedia

**Dirección conceptual:** Oscar Elieser Chamorro Guzmán.
Rama `sky-v12.4`, que parte de `sky-v12.3`. Se integra con un Pull Request revisado por el dueño.

SKY sigue siendo **una sola inteligencia**, con su voz, memoria, API e identidad. Lo que crece es su **catálogo de habilidades**. Las capacidades de otras plataformas se usan **sólo a través de sus APIs oficiales** y cuando tenés sus claves.

## SKY SKILL BUILDER (`neural_core/sky_skill_builder.py`)

1. **Detecta necesidades.** Cuando le pedís algo para lo que no tiene herramienta («calcula…», «convierte…», «organiza…»), guarda la frase normalizada y cuántas veces la pediste. «qué habilidades me faltan» te las muestra.
2. **Propone.** «diseña una habilidad para convertir dólares a córdobas»: la IA que tengas (Ollama, Claude, GPT o Gemini) redacta el manifiesto, el código y las pruebas. Si falla, se le devuelve el error y lo intenta una vez más.
3. **Revisión estática** del código, sin ejecutarlo:
   - sólo puede importar módulos puros de la biblioteca estándar (math, json, re, datetime…);
   - nada de `os`, `subprocess`, red, archivos, `eval`, `exec`, `getattr`, ni atributos que empiecen con `_`;
   - nada de formatos que lleguen a atributos internos;
   - máximo 20 000 caracteres.
4. **Pruebas en un proceso aislado** (`neural_core/sky_sandbox_runner.py`):
   - `python -I -S` con entorno mínimo y en una carpeta temporal;
   - los *builtins* recortados y un `__import__` con lista cerrada;
   - límites de memoria (384 MB) y CPU en Linux/macOS, y tiempo máximo en todos los sistemas;
   - la salida se valida (texto y hasta 5 órdenes).
5. **Aprobación del dueño, sólo en el HUD** (*Módulos → Habilidades*):
   - ves el código, las pruebas y los permisos, y marcás los que concedés;
   - al aprobar se vuelve a probar;
   - por voz se puede desactivar, **nunca aprobar**.
6. **Uso:**
   - «cuántos córdobas son 20 dólares» activa la habilidad instalada;
   - SKY descarga **sólo** las fuentes https de los dominios que aprobaste y se las pasa ya descargadas;
   - el código corre aislado;
   - las órdenes que devuelve pasan por **tus mismos permisos y confirmaciones**, y sólo si concediste `acciones`.

**Garantías:**
- Las habilidades no instalan paquetes, no tocan el núcleo de SKY y no heredan permisos.
- Cada versión nueva vuelve a revisión, y las anteriores quedan guardadas para auditar o volver atrás.
- Si alguien modifica el archivo instalado, SKY se niega a ejecutarlo.
- Todo queda en `~/.neuralt/builder/auditoria.jsonl`.

## Habilidades nativas (`neural_core/sky_habilidades.py`)

| Habilidad | Qué hace |
|---|---|
| **sky-travel** | «planifica un viaje a Granada de 3 días con 200 dólares»: presupuesto por rubro y día, clima previsto (Open-Meteo), cambio de moneda (open.er-api.com) e itinerario. El plan queda guardado en su base de conocimiento |
| **sky-business-manager** | Proyectos con tareas, fechas, responsables, avance y atrasos |
| **sky-smart-home** | «estado de la casa» con Home Assistant, además de las órdenes que ya existían |
| **sky-self-monitor** | «recomiéndame mejoras», basado en KPIs, objetivos incumplidos y necesidades detectadas |
| **sky-security** | «haz una auditoría de seguridad»: perfil de permisos, capacidades de riesgo, automáticas indebidas, permisos de `.env`, accesos sin llave, WhatsApp, habilidades instaladas y uso de la nube |
| **sky-music** | Canción original con letra, estructura, acordes y estilo, guardada en `~/.neuralt/creaciones/musica` |
| **sky-creative** | Imágenes con la **API de OpenAI** o **Adobe Firefly Services** y presentaciones con la **API de Gamma**, que avisa con el enlace cuando termina |

- Se activan y desactivan por voz o en el panel. *Seguridad* y *Automonitoreo* no se pueden apagar.
- Las órdenes de proyectos aceptan:
  - «crea el proyecto Tienda online»;
  - «agrega la tarea diseñar el logo al proyecto tienda online para el viernes a cargo de Ana»;
  - «cómo va el proyecto…» y «qué tareas están atrasadas».

## Centro de integraciones (`neural_core/sky_integraciones.py`)

20 plataformas, cada una con su vía de acceso (API, OAuth, MCP, local, agente o sin API pública), lo que necesita, su estado real y una nota honesta. Ejemplos:

- **ChatGPT Plus, Claude Pro y Gemini Advanced no incluyen sus APIs**, que se pagan aparte.
- **Suno no tiene API pública.** Sólo explora un programa de socios, así que SKY escribe la canción y vos la pegás en la plataforma.
- **Canva y Google Calendar/Drive** necesitan OAuth, pendiente en SKY.
- **Firefly** necesita credenciales de Firefly Services.
- **Gamma** necesita un plan Pro o superior.

## Interfaz

- **Módulos → Habilidades** muestra:
  - el Skill Builder, con el pedido, las necesidades detectadas y las propuestas con código, pruebas, permisos y los botones Aprobar, Desactivar y Eliminar;
  - las habilidades nativas;
  - la tabla de integraciones.
- Las imágenes generadas se ven en el chat del HUD. Se sirven por `GET /api/hud/creaciones/{tipo}/{archivo}`, con la llave del dueño y validación del nombre.

## Otros

- **CI:** la instalación de `ffmpeg` por apt ahora tiene un límite de 5 minutos y, si no responde, usa `static-ffmpeg`. La revisión v10.5 se había cancelado tres veces por apt colgado.

## Evidencia y límites

- **716 pruebas aprobadas, 0 fallidas** en el entorno de revisión. 31 son nuevas en `tests/test_sky_v12_4_habilidades.py`, con el proceso aislado real y las APIs simuladas. Incluyen:
  - 10 intentos de código malicioso rechazados por la revisión;
  - un bucle infinito cortado por tiempo;
  - un `import os` bloqueado en tiempo de ejecución;
  - un archivo instalado modificado que SKY se niega a ejecutar.
- **No probado contra OpenAI, Adobe, Gamma, Open-Meteo ni open.er-api.com reales**: este entorno no tiene acceso a esas APIs. Los formatos siguen su documentación oficial.
- El aislamiento es por proceso, sin contenedor del sistema operativo. En Windows no hay límite de memoria por proceso, sólo de tiempo.
- La calidad de las habilidades que propone el Builder depende del modelo de IA. Por eso nada se instala sin pasar las pruebas y sin tu aprobación.
