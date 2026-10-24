# SKY IA v12.2: aprendizaje continuo, conocimiento de internet, KPIs reales y parada de emergencia

**Dirección conceptual:** Oscar Elieser Chamorro Guzmán.
Rama `sky-v12.2`: se integra a `main` con un Pull Request revisado por el dueño (prompt maestro §2).

## Aprendizaje continuo (`neural_core/sky_aprendizaje.py`)

- **Atajos aprendidos.** Cuando el cerebro local entiende una frase nueva y la acción **sale bien**, SKY guarda esa frase. La próxima vez la resuelve al instante, sin consultar al modelo. Se aprende tanto si la acción se ejecutó sola como si la confirmaste en el HUD.
  - «no, eso no era» deshace el último atajo y queda registrado en `sky_evolution`.
  - Un atajo sin uso durante 90 días caduca.
  - No se aprenden órdenes cuyo contenido cambia cada vez (notas, texto, portapapeles).
- **Órdenes enseñadas:** «cuando diga *modo cine*, pon el video en pantalla completa». «olvida la orden modo cine» la quita.
- **Memoria personal:**
  - «recuerda que mi equipo es el Real Madrid», «qué sabes de mí», «corrige que mi equipo es…», «olvida que…».
  - **Nunca guarda** contraseñas, claves, PIN, tokens ni datos de tarjetas.
  - El cerebro recibe estos datos como contexto.
- **Exportar y borrar memoria:** `GET /api/hud/memoria` y `DELETE /api/hud/memoria/{id}`. Cada dato viene clasificado:
  - *hecho confirmado*: lo dijiste vos;
  - *preferencia inferida*: un atajo aprendido;
  - *obsoleto*: un atajo que caducó.

## Se alimenta de internet

- «aprende sobre energía solar» o «investiga sobre Rubén Darío»:
  - lee el artículo de Wikipedia en español y los titulares recientes de Google News;
  - lo guarda en la base de conocimiento local con fuente y fecha;
  - te resume lo principal;
  - el cerebro usa ese conocimiento cuando le preguntás sobre el tema.
- «sigue el tema Real Madrid»: una vez por día lee las novedades, las guarda y te avisa. «deja de seguir…» lo quita. «noticias de…» lee los titulares al momento.
- **Seguridad:** lo que viene de internet se guarda y se pasa al modelo como **datos de referencia**, con la indicación explícita de no seguir instrucciones que aparezcan ahí.
- `SKY_INTERNET=0` hace que SKY nunca salga a internet.
- **SymPy** ya está en `requirements.txt`. Las 13 pruebas de matemática simbólica que fallaban por falta de esa librería ahora pasan, y se agregaron a la CI.

## Centro de KPIs con mediciones reales (`neural_core/sky_metricas.py`)

Base local `~/.neuralt/sky_metricas.sqlite3`, que guarda 30 días. **No guarda** textos de mensajes, parámetros, tokens de acceso, IPs ni contenido de archivos.

| Qué | De dónde sale el dato |
|---|---|
| Cada petición `/api/*`: ruta (sin IDs), código y ms | middleware de la API |
| Cada mensaje al asistente: vía (reglas, atajo aprendido, cerebro, IA) y ms | `/api/asistente/mensaje` y `/stream` |
| Cada acción en un equipo: completada o fallida, con el motivo | `dispositivos.call_device`; cubre la API, la voz manos libres y las rutinas |
| Órdenes a Home Assistant | `/api/asistente/casa` y las órdenes automáticas |
| Disponibilidad del agente | consultas de estado, una muestra por minuto; los fallos se guardan siempre |
| Cerebro local: ms y tokens | lo que informa Ollama (`eval_count`) |
| Voz: tiempo hasta la primera palabra, interrupciones, errores de micrófono o reproducción | el HUD (`POST /api/hud/kpi/evento`, con una lista cerrada de nombres) |
| Reconocimiento y síntesis: latencia y errores | rutas `/stt/transcribe` y `/api/hud/tts` |
| Seguridad: operaciones autorizadas y rechazadas, accesos sin llave (401), prohibidos (403), confirmaciones pendientes | respuestas reales |
| Arranques del servicio y paradas de emergencia | arranque de la API |
| CPU, RAM, disco y tamaño de la base de KPIs | `psutil` (opcional) y `shutil` |

- Latencias p50, p95, p99 y promedio.
- **Objetivos de servicio (SLO) configurables** en `.env` (`SKY_SLO_*`). Cada objetivo se marca como cumplido, no cumplido o *sin datos*; nunca se rellena con valores inventados.
- **Detección automática**, comparando el día con los 7 anteriores:
  - una ruta más lenta que lo normal (o con p95 por encima de 3 s);
  - errores 5xx de 10 % o más;
  - 25 % o más de acciones fallidas;
  - la misma acción fallando 3 veces seguidas;
  - el agente sin responder;
  - el cerebro lento;
  - muchas respuestas con error.
- Cada 5 minutos SKY revisa sus indicadores y **te avisa una sola vez por día** de cada problema nuevo.
- **Por voz o texto:**
  - «SKY, mostrame tu rendimiento de hoy, cuántas tareas completaste y cuáles fallaron» responde con números reales y abre el panel.
  - «analizá tu rendimiento y decime qué está fallando» o «¿por qué estás respondiendo lento?» dan un diagnóstico basado sólo en evidencia: problemas, objetivos incumplidos, CPU, RAM y disco.
  - «tu rendimiento de la semana».
- **Panel de rendimiento como módulo interno.** Se abre a pedido (por voz o desde *Módulos → Rendimiento*) en una ventana holográfica y no agrega botones a la pantalla principal. Muestra:
  - tarjetas de tareas, mensajes, API, agente y equipo;
  - problemas detectados;
  - tareas por hora;
  - tareas fallidas con el motivo;
  - desglose por tipo de tarea, por vía de resolución y rutas lentas;
  - lo aprendido, con la opción de olvidar cada atajo.

  Se actualiza cada 20 s mientras está abierto. «cerrá el panel» lo cierra.

## Seguridad: niveles de riesgo y parada de emergencia

- **Niveles de riesgo** (prompt maestro §9): 1 bajo, 2 moderado y 3 alto. Cada propuesta muestra su nivel en el HUD. El nivel 3 (borrar notas, publicar, enviar correos, abrir cerraduras o cortinas) **siempre** pide confirmación por acción, aunque la capacidad esté marcada como automática.
- **Parada de emergencia** (§15):
  - «SKY, para todo», «detente», «emergencia» o «cancela todo» la activan al instante y cortan la voz.
  - El agente rechaza cualquier acción (salvo consultar estado) mientras exista `~/.neuralt/sky_parada.json`.
  - También se bloquean Home Assistant, el envío de correos y las acciones automáticas de las rutinas.
  - **Para reanudar hace falta un clic** del dueño (tarjeta «Reanudar» o `DELETE /api/asistente/emergencia`); por voz sólo se puede pedir.
  - «reanuda» sigue controlando la música.

## Otros

- «mostrame los archivos» abre tus documentos.
- «cerrá el panel» cierra la ventana holográfica de arriba, no una ventana del escritorio.
- El instalador elige `qwen2.5:14b` en equipos con 30 GB de RAM o más.
- Nuevas rutas:
  - `GET /api/hud/kpi?periodo=hoy|semana`
  - `POST /api/hud/kpi/evento`
  - `GET /api/hud/aprendizaje` y `DELETE /api/hud/aprendizaje/atajos/{frase}`
  - `GET` y `DELETE /api/hud/memoria[/{id}]`
  - `GET`, `POST` y `DELETE /api/asistente/emergencia`

  `POST /api/asistente/ejecutar` y `/casa` aceptan `frase` opcional, para aprender al confirmar. Las respuestas traen `nivel_riesgo` y `ms`.

## Evidencia y límites

- **653 pruebas aprobadas, 0 fallidas** en el entorno de revisión. Hay 38 pruebas nuevas en `tests/test_sky_v12_2_aprendizaje_kpi.py`, con la red simulada.
- Probado en Chromium contra la API real, en escritorio (1440×900) y celular (390×844):
  - la pregunta de rendimiento devuelve los números registrados y abre el panel;
  - «cerrá el panel» lo cierra;
  - el diagnóstico cita los problemas medidos;
  - sin errores de consola.
- **No probado en un Windows real** (agente, Ollama, Piper y micrófono), ni con Wikipedia o Google News reales: el entorno de revisión no tiene acceso a esos sitios, así que se usaron dobles de prueba.
- Los costos de proveedores en la nube **no se miden todavía**: esos clientes no devuelven el conteo de tokens a SKY. El panel lo dice en lugar de mostrar un número.
- El aprendizaje **no reentrena el modelo ni modifica su propio código**. Guarda atajos, datos y conocimiento consultables, que podés revisar, exportar y borrar.
