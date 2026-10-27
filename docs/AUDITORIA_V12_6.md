# Auditoría SKY v12.6: arranque, supervisor, voz, PIN y persistencia

- **Fecha:** 26/10/2026
- **Rama de trabajo:** `sky-v12.6-fiabilidad`
- **Punto de partida:** `main` en `e910f990984ac5865ceeb93c05b238f03c41d624`. Incluye SENTINEL v12.5 y los PR de voz #53–#55. No había cambios locales sin guardar.
- **Alcance:** arranque, supervisor, API, agente de Windows, HUD, voz manos libres, proveedores, permisos, persistencia, módulos, integraciones y pruebas.
- **Instrucciones del repositorio:** el repositorio no tiene `AGENTS.md`, `CLAUDE.md` ni `CONTRIBUTING`. Las carpetas `.agents/skills/*` son guías de redacción y no aplican a este trabajo. Se siguieron las reglas del prompt: rama de mejora, sin borrar archivos del dueño, ampliar la API propia y no instalar librerías nuevas.

> Las referencias `archivo:línea` apuntan al commit inicial `e910f99`, salvo indicación contraria. «Probado» significa que hay pruebas automáticas que pasan o una comprobación en vivo en este entorno Linux. **Nada de esto se ejecutó todavía en Windows, con micrófono ni con modelos reales:** la lista de pruebas pendientes está al final.

---

## 1. Verificación de los seis puntos de la revisión estática previa

| # | Punto | ¿Seguía presente? | Hallazgo |
|---|---|---|---|
| 1 | `iniciar_sky_autonomo.py` anuncia servicios activos sin comprobar su preparación | **Sí** | H5 |
| 2 | `check_system_status` puede presentar la API como online tras fallar la salud | **Sí** | H6 |
| 3 | Un nuevo arranque puede finalizar instancias anteriores | **Sí**, y además dos supervisores se peleaban por los puertos | H1 |
| 4 | El supervisor detecta salidas, pero hay que revisar bloqueos, recuperación y registros | **Sí**: sin detección de cuelgues, con espera fija que bloqueaba el ciclo y sin registros | H8 |
| 5 | `sky_manos_libres.py` necesita autenticación antes de procesar órdenes | **Sí**: ejecutaba sin PIN ni sesión. Lo mismo pasaba con WhatsApp, Streamlit y el agente | H2 |
| 6 | La persistencia JSON de sesión necesita concurrencia y escrituras atómicas | **Sí**, en tres archivos distintos | H4 |

---

## 2. Hallazgos

Prioridad: **P0** = arranque, autorización o pérdida de datos · **P1** = estabilidad de voz, salud, recuperación o latencia · **P2** = registro de módulos y experiencia.

### H1 · P0 · Alta: un segundo arranque cerraba la instancia sana y duplicaba procesos
- **Dónde:** `iniciar_sky_autonomo.py:276-287` (cierre con `taskkill /F /T` del PID que ocupa el puerto), `:382` (el supervisor anterior reinicia lo que le cerraron) y `agente_dispositivo.py:452` (el agente busca otro puerto libre si 8766 está ocupado).
- **Cómo reproducirlo:** iniciar SKY dos veces (por ejemplo, el inicio con Windows más un doble clic en `SKY_INICIAR.bat`). El segundo supervisor mata la API y el agente del primero. El primero los vuelve a lanzar (hasta 5 veces por hora) y los dos supervisores se pelean el puerto 8765. Mientras tanto puede quedar un segundo agente en 8767.
- **Causa:** no existía un candado de instancia única. La única protección (`es_servicio_sky`) evitaba matar *otros programas*, pero cualquier proceso de SKY se mataba.
- **Corrección:** candado del sistema operativo durante toda la vida del supervisor (`neural_core/sky_archivo_seguro.CandadoInstancia`, en `~/.neuralt/sky_supervisor.lock`; el sistema lo libera si el proceso muere). El segundo arranque avisa, abre la interfaz y termina sin tocar nada. Si hay un SKY sano de antes sin supervisor, **se adopta** sin reiniciarlo. Sólo se cierran procesos propios, verificados por PID, hora de creación y línea de comandos registrados en `~/.neuralt/sky_supervisor.json`.
- **Prueba:** `test_arrancar_dos_veces_no_duplica_ni_interrumpe`, `test_adopta_un_sky_sano_sin_reiniciarlo` y `test_no_cierra_otra_instancia_de_sky_que_no_inicio`. **En vivo:** segundo arranque → «SKY ya está en ejecución». Los PID del agente y de la API siguieron iguales y no se duplicó ningún proceso.

### H2 · P0 · Alta: el PIN no protegía la voz, WhatsApp, Streamlit ni el agente
- **Dónde:** `sky_manos_libres.py:146` (ejecuta con el agente apenas reconoce «SKY…»), `neural_core/sky_whatsapp.py:374` (llama al asistente directamente), `app.py:45` (Streamlit usa el núcleo sin API) y `agente_dispositivo.py:385` (ejecuta con sólo el token).
- **Cómo reproducirlo:** con PIN configurado y el HUD bloqueado, alguien cerca del micrófono dice «SKY, subí el volumen» y la acción se ejecuta. Lo mismo pasa con el panel Streamlit abierto en `:8501`.
- **Causa:** SENTINEL v12.5 sólo retenía la llave en la interfaz del navegador. Los demás canales no pasan por la API y no consultaban ningún estado de sesión.
- **Corrección:** hay **una sola sesión del dueño**, compartida por todos los procesos, dentro del módulo de identidad que ya existía (`sentinel_identidad.estado_sesion`, `bloquear_sesion`, `desbloquear_sesion`). No se creó un sistema de autorización paralelo. Con PIN configurado:
  - SKY **arranca bloqueada** y pregunta «¿Cuál es tu PIN?».
  - La API responde **423** salvo salud, desbloqueo, consulta y bloqueo de la sesión y **parada de emergencia** (`metaverse/sentinel.py`).
  - El **agente** rechaza acciones (423), salvo tareas programadas automáticas de nivel 1, como avisos.
  - La **voz** sólo acepta el PIN y la parada.
  - **WhatsApp** no ejecuta nada, y el PIN no se pide por chat.
  - **Streamlit** pide el mismo PIN.
  - Si el archivo de sesión no se puede leer, la sesión se considera **bloqueada** (falla cerrado). Desbloquear **no cambia** la política por dispositivo ni por herramienta.
- **Prueba:** `test_api_bloqueada_responde_423_salvo_desbloqueo_y_emergencia`, `test_agente_rechaza_acciones_con_la_sesion_bloqueada`, `test_voz_local_no_llama_al_agente_con_la_sesion_bloqueada`, `test_whatsapp_no_ejecuta_con_la_sesion_bloqueada`, `test_puerta_de_voz_pregunta_el_pin_y_no_registra_nada` y `test_desbloquear_conserva_permisos_por_dispositivo_y_herramienta`. **En vivo, con Chromium y la API real:** API bloqueada → 423 · PIN incorrecto → sigue en 423 · PIN correcto → 200 · «SKY, bloquéate» escrito → 423 · parada con la sesión bloqueada → 200.

### H3 · P0 · Alta: el token del agente se imprimía y terminaría en los registros
- **Dónde:** `agente_dispositivo.py:482` (`print('Token para emparejar …', secret)`).
- **Riesgo:** al redirigir la salida a archivos de registro (necesario para el arranque sin consola), la credencial del dispositivo quedaba escrita en disco.
- **Corrección:** el token sólo se muestra en una consola interactiva o con `--mostrar-token`. Además, el diagnóstico oculta cualquier cadena de 32 o más caracteres alfanuméricos al citar registros.
- **Prueba:** `test_detener_sin_instancia_y_registros_sin_tokens`. **En vivo:** `grep "Token para emparejar" local_data/logs/agent.log` → 0 coincidencias.

### H4 · P0 · Media-alta: escrituras JSON no atómicas y sin candado entre procesos
- **Dónde:**
  - `sky_manos_libres.py:196`: lee, modifica y escribe con `write_text`, sin candado.
  - `neural_core/voice_coordinator.py:273`: `write_text` no atómico.
  - `voice_coordinator.py:83`: **escribía el estado inicial al importarse**, así que cada vez que la API o Streamlit importaban el módulo borraban el estado real de la escucha.
  - `neural_core/sentinel_identidad.py:48`: temporal con nombre fijo, y `:26`, candado sólo de hilos: dos procesos podían contar dos PIN fallidos como uno.
- **Riesgo:** un lector podía ver JSON a medio escribir y concluir «la escucha está apagada». También se perdían actualizaciones y se debilitaba el límite de intentos del PIN.
- **Corrección:** `neural_core/sky_archivo_seguro.py`:
  - `escribir_json`: temporal único en el mismo directorio, `fsync` y `os.replace`, con reintentos ante bloqueos breves de Windows.
  - `bloqueo`: candado entre procesos con `msvcrt` en Windows y `fcntl` en POSIX.
  - `actualizar_json`: combina las dos cosas para leer, modificar y escribir.
  - Se aplicó a la sesión de voz, al coordinador y a SENTINEL. El coordinador ya no escribe al importarse.
- **Prueba:** `test_actualizacion_json_entre_procesos_sin_perder_cambios`: 3 procesos × 150 incrementos = **450 exactos y 0 lecturas inválidas**. También `test_coordinador_de_voz_no_pisa_el_estado_ni_guarda_frases`.

### H5 · P0 · Media: el arranque anunciaba «todos los servicios activos» sin comprobarlo
- **Dónde:** `iniciar_sky_autonomo.py:362`. Antes de ese mensaje sólo se esperaba que el puerto 8765 abriera (`:352`).
- **Corrección:** cada servicio tiene ahora dos comprobaciones: *preparación* (readiness) y *vida* (liveness).
  - La API agrega `GET /api/health/listo`, que prueba la memoria SQLite, la seguridad y los KPIs sin exponer datos.
  - El agente se comprueba con `GET /status` y su token.
  - La voz, con el latido real del hilo del micrófono.
  - El mensaje final cuenta sólo lo preparado, y lo que no lo está aparece con su causa.
- **Prueba en vivo:**
  ```
  [SKY] ✓ agent preparado (0.8 s): responde
  [SKY] ✓ api preparado (1.4 s): lista
  [SKY] Listo: 2 de 2 servicios preparados y supervisados.
  ```

### H6 · P0 · Media: `--status` mostraba la API «online» aunque la salud fallara
- **Dónde:** `iniciar_sky_autonomo.py:156`: ante cualquier error informaba `"online (sin endpoint /sky)"`.
- **Corrección:** si la salud falla o no es de SKY, el estado es `error: …`. Si falla la preparación, es `degradado: …`. Se agregaron `problemas` (causa y pasos concretos), el estado del supervisor y el de la sesión.
- **Prueba:** `test_estado_no_presenta_la_api_online_si_la_salud_falla` (un servidor que responde 500 ya no aparece como online y el chat por texto figura como no disponible).

### H7 · P0 · Media: arrancar SKY podía mandar mensajes externos
- **Dónde:** `metaverse/api.py:72`: los recordatorios vencidos mientras SKY estaba apagada salían todos juntos por WhatsApp y como notificación al arrancar. `api.py:84`: la vigilancia de KPIs empezaba en 0, así que corría en el primer ciclo y podía avisar por WhatsApp. La actualización de temas consultaba internet al arrancar.
- **Corrección:**
  - Los recordatorios con más de `SKY_RECORDATORIO_TOLERANCIA_MIN` minutos de atraso (30 por defecto) quedan en el HUD como «Perdido mientras SKY estaba apagada», sin avisos externos.
  - La primera revisión de KPIs es a los 5 minutos y la de temas, a la hora.
  - Las rutinas programadas por el dueño siguen corriendo en su ventana de 30 minutos, igual que antes.
- **Prueba:** `test_recordatorios_vencidos_con_sky_apagada_no_salen_por_whatsapp`.

### H8 · P1 · Media: supervisor sin detección de cuelgues ni registros, con espera que bloqueaba el ciclo
- **Dónde:**
  - `iniciar_sky_autonomo.py:385`: `time.sleep(3)` dentro del ciclo detenía la supervisión de todo.
  - `:382`: después de 5 reinicios, el servicio quedaba muerto para siempre.
  - `:369`: los hijos heredaban la consola y no había registros.
  - `:205`: el inicio con Windows usaba `python.exe`, que abre una consola: cerrarla mataba SKY.
  - `stop_all` forzaba el cierre en 2 segundos.
- **Corrección:**
  - Reinicios programados sin bloquear el ciclo, con **espera progresiva de 2, 4, 8, 16 y 32 s**, como máximo 5 por hora. Después reintenta cada 30 minutos.
  - Las **fallas permanentes no se reintentan en bucle**: el código 2 significa que falta configuración o una dependencia, y el código 3, que falta el micrófono (reintento cada 5 minutos).
  - Se detectan **cuelgues** tras 90 s sin respuesta con el proceso vivo.
  - **Registros rotativos** en `local_data/logs/*.log` (2 MB × 3 copias), además de `supervisor.log`.
  - Se quitó el registro de accesos de uvicorn, porque las rutas pueden incluir tus consultas.
  - Cierre limpio con CTRL+BREAK en Windows o SIGTERM, 8 s de espera antes de forzar, y `--stop`, que pide el cierre por archivo sin matar nada por puerto.
  - Inicio con Windows mediante **`pythonw.exe`**, sin ventana que se pueda cerrar sin querer.
- **Prueba:** `test_recupera_un_servicio_caido_con_espera_progresiva_y_limite`, `test_falla_permanente_no_se_reintenta_en_bucle`, `test_colgado_se_distingue_de_lento` e `test_inicio_con_windows_sin_consola`. **En vivo:** con `kill -9` a la API, volvió a responder en **3,6 s** («Reiniciando 'api' (1/5 esta hora)»). `--stop` dejó **0 procesos**.

### H9 · P1 · Media: la salud de la API podía fallar sólo porque el modelo estaba ocupado
- **Dónde:** `metaverse/api.py:318`. La función `health` era síncrona y corría en el grupo de hilos de FastAPI. Si varias inferencias lentas ocupaban todos los hilos, la salud dejaba de responder y un supervisor con detección de cuelgues habría reiniciado SKY en plena respuesta.
- **Corrección:** `health` ahora es `async` y la atiende el bucle de eventos. La voz late desde el hilo del micrófono, no desde el del modelo. Así, una inferencia lenta no se confunde con un cuelgue.
- **Prueba:** `test_salud_asincrona_y_preparacion` y `test_colgado_se_distingue_de_lento` (60 s sin respuesta → «degradado» sin reinicio; 95 s → «colgado» y reinicio).

### H10 · P1 · Media: `get_pid_using_port` podía devolver el PID equivocado
- **Dónde:** `iniciar_sky_autonomo.py:82`: aceptaba líneas que no eran `LISTENING` (clientes o `TIME_WAIT`).
- **Corrección:** sólo acepta la línea `LISTENING` del puerto local. Además, el PID ya no basta para cerrar un proceso (ver H1).

### H11 · P1 · Media (privacidad): se registraban frases y respuestas sin necesidad
- **Dónde:**
  - `sky_manos_libres.py:318-319`: imprimía y guardaba en disco lo reconocido (`last_command`).
  - `voice_coordinator.py:63`: persistía lo que dijiste y lo que respondió SKY.
  - `neural_core/sky_voice_queue.py:193`: imprimía cada respuesta.
  - El registro de accesos de uvicorn guardaba rutas con consultas.
- **Corrección:** en disco quedan sólo marcas de tiempo y estados. En una consola interactiva se sigue viendo todo; en los registros, sólo la longitud (`SKY_VOZ_DEPURAR=1` lo habilita para depurar). **El PIN hablado nunca se imprime, guarda ni envía a la IA:** la puerta de voz lo procesa antes de cualquier registro.

### H12 · P1 · Media (resultados reales): decía «Listo» sin evidencia
- **Dónde:** `sky_manos_libres.py:154` (`'Listo.' if hecho.get('ok', True)`) y `neural_core/sky_rutinas.py:478` (marcaba «ok» cualquier respuesta que no fuera error).
- **Corrección:** `describir_resultado` distingue cinco casos: **verificada** (el agente comprobó el efecto), **enviada** («Envié la orden. No pude comprobar el resultado.»), **pendiente** (espera confirmación), **bloqueada** (falta el PIN) y **fallida**. Los KPIs de voz cuentan acciones verificadas y acciones sin comprobar por separado.
- **Prueba:** `test_distingue_verificada_enviada_pendiente_y_bloqueada`.

### H13 · P1 · Baja-media (latencia): faster-whisper se cargaba de nuevo en cada transcripción
- **Dónde:** `neural_core/sky_stt_local.py:113` creaba `WhisperModel(...)` en cada llamada.
- **Corrección:** el modelo se carga una sola vez, bajo demanda o al activarlo, y se puede liberar.
- **Pendiente honesto:** el HUD y WhatsApp transcriben con `sky_stt_isolated_v106`, que **por diseño** abre un proceso aislado por pedido y carga el modelo cada vez. Ese aislamiento es una decisión de seguridad anterior. Medir su costo en tu PC y, si hace falta, pasar a un trabajador aislado persistente queda propuesto, no implementado.

### H14 · P1 · Baja (arranque): la API cargaba trimesh y scipy aunque nadie exportara 3D
- **Medición:** `python -X importtime -c "import metaverse.api"` → `metaverse.export3d` aportaba **1,71 s** de los 3,98 s de importación.
- **Corrección:** el exportador GLB se importa al exportar el primer mundo. **En vivo:** la API quedó lista en 1,4 s, incluido el arranque de uvicorn.
- **Prueba:** `test_la_api_no_carga_motores_pesados_al_importarse` (ni trimesh, torch, faster-whisper, diffusers, vosk ni transformers al importar la API).

### H15 · P1 · Baja: órdenes de voz duplicadas
- **Dónde:** `neural_core/sky_voice_queue.py:120`: `submit` no descartaba repeticiones.
- **Corrección:** una orden idéntica dentro de 3 s no se vuelve a ejecutar. La cola sigue acotada (1 activa y 2 en espera).
- **Prueba:** `test_cola_de_voz_no_duplica_ordenes`.

### H16 · P2: no había registro de módulos en tiempo de ejecución
- **Situación:** existían catálogos estáticos (`sky_integraciones`, `sky_extension_hub`, `sky_capability_inventory`), pero ninguno decía si un motor estaba cargado, cargando o roto, ni permitía activarlo.
- **Corrección:** `neural_core/sky_modulos.py`, que **reutiliza** las 26 integraciones existentes y el estado que publica el supervisor. Tiene seis estados: disponible, no configurado, cargando, activo, degradado y error. Para cada módulo dice **qué falta exactamente**: variable de `.env`, paquete o modelo.
  - Los motores pesados (faster-whisper, el modelo elegido en Ollama, exportación 3D y adaptador LoRA) se cargan **sólo cuando los pedís**, con límite de concurrencia (1) y de memoria (RAM del módulo más 1 GB de reserva).
  - Si un módulo falla, queda en «error» y el resto sigue funcionando.
  - **Nunca cambia tu modelo**: precarga `OLLAMA_MODEL`, sin pasar a uno menor.
  - Se accede por voz o texto («estado de los módulos», «activá el reconocimiento local», «qué le falta a WhatsApp»), por la API (`/api/hud/modulos…`) y por la ventana «Módulos» del HUD.
- **Prueba:** `test_activar_un_modulo_no_carga_los_demas`, `test_modulo_que_falla_no_detiene_a_los_demas`, `test_limites_de_memoria_y_concurrencia`, `test_informa_exactamente_que_falta` y `test_ordenes_de_modulos_por_voz_o_texto`. **En vivo:** ventana «Módulos de SKY» con el estado real de este entorno.

### H17 · P2 · Baja: respaldos y parches sueltos en el repositorio
- `neural_core/*.respaldo*`, `neural_core/sky_stt_local_nuevo.py`, `SKY_PARChe_PROCESANDO_20261026.py`, `sky_pr52_reconcile_local.py`, `APLICAR_SKY_LATENCIA_VOZ.py` y `prueba_sky.wav`.
- **No se tocaron**, porque son archivos tuyos. Se recomienda revisarlos y moverlos a `history/` en un cambio aparte.

### H18 · P2 · Baja: el modo elegido en Streamlit no llega a la escucha manos libres
- `app.py:1605` cambia el modo del coordinador **de su propio proceso**. La voz corre en otro proceso y no lo lee. **Pendiente:** no se cambió, para no modificar el contrato del coordinador.

---

## 3. Capacidades y su estado real

| Capacidad | Estado | Evidencia |
|---|---|---|
| Una sola instancia; un segundo arranque no interrumpe | **Implementada y probada** | Pruebas + en vivo (PID sin cambios) |
| Adoptar un SKY sano previo sin reiniciarlo | **Implementada y probada** | Prueba con procesos reales |
| Preparación por servicio antes de anunciar «listo» | **Implementada y probada** | En vivo: agente 0,8 s y API 1,4 s |
| Recuperación con espera progresiva y límites | **Implementada y probada** | Pruebas + en vivo con `kill -9` → 3,6 s |
| Detección de cuelgues sin confundirlos con inferencia lenta | **Implementada y probada** (lógica) | Prueba con proceso vivo que no responde |
| Cierre limpio y `--stop` | **Implementada y probada en Linux** | En vivo: 0 procesos. Windows (CTRL+BREAK) sin validar |
| Registros rotativos sin tokens ni consultas | **Implementada y probada** | Prueba + `grep` en vivo |
| Diagnóstico con causa y pasos (`--status`) | **Implementada y probada** | Prueba + en vivo |
| Inicio automático en tu sesión de Windows sin consola | **Implementada sin validación real** | Genera el `.bat` con `pythonw.exe`; no se ejecutó en Windows |
| SKY sigue funcionando al cerrar el navegador o el HUD | **Implementada y probada** | En vivo: Chromium cerrado → `/api/health` 200 |
| Sesión con PIN compartida (API, HUD, agente, WhatsApp, Streamlit, voz) | **Implementada y probada** (salvo voz y Streamlit reales) | Pruebas + HUD real en Chromium |
| PIN escrito en el HUD | **Implementada y probada** | En vivo con Chromium |
| PIN hablado (dígito por dígito, local) | **Implementada sin validación real** | Lógica probada; Vosk y micrófono reales no disponibles |
| Bloquear de nuevo por voz o texto | **Implementada y probada** (texto); voz sin validación real | En vivo con texto en el HUD |
| Intentos limitados, espera progresiva, bloqueo de 15 min y recuperación local | **Implementada y probada** | Pruebas con reloj controlado |
| Tareas programadas con la sesión bloqueada | **Implementada y probada** | Pruebas del agente (ver §4) |
| Registro de módulos con estados reales y qué falta | **Implementada y probada** | Pruebas + ventana en vivo |
| Carga bajo demanda de faster-whisper, Ollama y LoRA | **Implementada sin validación real** | Los cargadores son los reales; los modelos no están en este entorno |
| Latencia por etapa de la voz manos libres en los KPIs | **Implementada sin validación real** | Sin micrófono no hay mediciones reales todavía |
| Identificar quién habla | **No implementada** | Conocer el PIN no identifica a la persona (§5) |
| PIN hablado en el HUD del navegador | **No implementada a propósito** | El dictado del navegador puede enviar el audio a terceros; en el HUD el PIN se escribe |

---

## 4. Qué puede ejecutarse con la sesión bloqueada

| Tarea | ¿Corre bloqueada? | Por qué |
|---|---|---|
| Parada de emergencia (voz, HUD, API y WhatsApp) | **Sí, siempre** | Detener nunca debe requerir PIN |
| Recordatorios y alarmas: aviso en el HUD | Sí | Sólo informan; el HUD bloqueado no los muestra hasta el PIN |
| Recordatorios: notificación de escritorio y WhatsApp **al dueño** | Sí | Ya los autorizaste; la notificación es nivel 1 y automática |
| Pasos informativos de rutinas (saludo, agenda, noticias, KPIs, borradores pendientes) | Sí | No actúan sobre tus equipos |
| Pasos de rutinas que actúan sobre el equipo | **Sólo si son de nivel 1 y automáticos** en tu política (por ejemplo, volumen o música) | El agente lo vuelve a comprobar (`X-SKY-ORIGEN: programada`) |
| Acciones que requieren confirmación o de nivel 2 o 3 | **No**: quedan «esperando tu PIN» | Lo sensible no corre sin vos |
| Órdenes por voz, HUD, WhatsApp o Streamlit | **No** | Esperan el PIN |

La cabecera `X-SKY-ORIGEN` sólo la puede mandar quien ya tiene el token del agente. Es una restricción adicional, no una prueba de identidad.

---

## 5. Límites honestos de la autenticación por PIN hablado

- **Conocer el PIN no verifica la identidad de quien habla.** Si alguien te escucha decirlo, o lo graba, puede repetirlo. Por eso lo crítico (nivel 3, correos y cerraduras) **sigue pidiendo confirmación en la pantalla** además de la sesión.
- Decilo cuando estés solo, o escribilo en el HUD. Cambialo con `python sky_pin.py configurar` si sospechás que lo oyeron.
- Se guarda sólo un verificador **scrypt** (n=2¹⁴, r=8, p=1) con sal aleatoria de 16 bytes en `~/.neuralt/sentinel.json` (permisos 0600). Nunca aparece en código, commits, ejemplos, registros ni en esta documentación.
- La **recuperación local** (`python sky_pin.py restablecer`) la puede usar cualquiera con acceso a tu sesión de Windows. Protegé tu cuenta de Windows con contraseña o Windows Hello.
- **Desde el celular no se puede desbloquear.** Igual que en SENTINEL v12.5, `POST /api/sentinel/desbloquear` sólo acepta conexiones del propio equipo. Si SKY está bloqueada (por ejemplo, después de reiniciar la PC), el acceso remoto con la llave responde 423 hasta que digas o escribas el PIN en la PC.
- Quien tenga acceso de lectura a tu carpeta de usuario puede leer la llave de la API y el token del agente. La sesión con PIN no protege contra eso. El cifrado en reposo sigue pendiente (SENTINEL, fases 4 y 5).

---

## 6. Resultados de pruebas

| Conjunto | Resultado |
|---|---|
| Nuevas pruebas v12.6 (`tests/test_sky_v12_6_fiabilidad.py`) | **36 de 36** |
| Suite completa, base (`main` e910f99) | 1216 aprobadas · 30 fallidas · 3 omitidas |
| Suite completa con v12.6 | **1252 aprobadas · 30 fallidas · 3 omitidas** |
| Fallas nuevas respecto de la base | **0** |

- **Comprobación de que las pruebas detectan errores:** desactivar a propósito la barrera de la API, la del agente o la espera progresiva hace fallar 3 de las pruebas nuevas.
- **Las 30 fallas de la base son del entorno, no de SKY:** pruebas que necesitan Docker, compiladores (gcc, g++, tsc), Flutter, validadores HTML y CSS, MarkItDown o ejecutables MCP instalados. Son las mismas antes y después, una por una.
- **Pruebas existentes modificadas:**
  - `test_sky_v12_5_sentinel.py`: dos rutas públicas nuevas y «bloquéate», que ahora también bloquea la API.
  - `test_sky_mcp_hub.py`: simula una sesión abierta.
  - Cinco dobles de prueba de `ejecutar_local_si_autorizado` aceptan el nuevo parámetro opcional `origen`.
  - `test_skill_ejecuta_lo_autorizado` usa un resultado `VERIFIED`, porque una acción sin evidencia ya no cuenta como «ok».

---

## 7. Pruebas pendientes en tu PC (no hay simulación que las reemplace)

1. **Inicio con Windows:** `python iniciar_sky_autonomo.py --install-startup`, cerrar sesión y volver a entrar. Esperado: no aparece ninguna consola; en `local_data\logs\supervisor.log` figuran «✓ agent» y «✓ api»; SKY dice «¿Cuál es tu PIN?».
2. **PIN hablado:** con micrófono, decí los dígitos de a uno. Probá uno incorrecto (debe responder «PIN incorrecto. Te quedan 4 intentos.») y después el correcto.
3. **Eco:** mientras SKY habla, que no se ejecute nada de lo que ella misma dice.
4. **Cierre limpio en Windows:** `python iniciar_sky_autonomo.py --stop`. Esperado: «SKY se detuvo limpiamente» y nada en el puerto 8765.
5. **Recuperación:** en el Administrador de tareas, finalizá el proceso `python … uvicorn`. Esperado: vuelve en menos de 10 s y queda «Reiniciando 'api' (1/5 esta hora)» en el registro.
6. **Sin micrófono:** desconectalo e iniciá SKY. Esperado: `--status` muestra la voz con la causa «no hay micrófono disponible; reintento en 5 minutos».
7. **Módulos reales:** «SKY, activá el reconocimiento local» y «SKY, activá el modelo local». Medí el tiempo en la ventana «Módulos» o en los KPIs (`modulo_*`).
8. **Latencia real por etapa:** después de un día de uso, pedí «mostrame tu rendimiento de hoy» y revisá `voz.manos_libres` en los KPIs.
