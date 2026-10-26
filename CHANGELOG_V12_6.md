# SKY v12.6: fiabilidad verificable

Rama: `sky-v12.6-fiabilidad`, desde `main` en `e910f99`. La auditoría completa, con archivo, línea, evidencia y pruebas, está en [docs/AUDITORIA_V12_6.md](docs/AUDITORIA_V12_6.md). Las instrucciones en PowerShell están en [docs/guias/SKY_WINDOWS_V12_6.md](docs/guias/SKY_WINDOWS_V12_6.md).

## P0: arranque, autorización y pérdida de datos
- **Una sola instancia.** Un segundo arranque ya no cierra la instancia sana: avisa y termina. Si encuentra un SKY sano previo sin supervisor, lo adopta. Sólo administra procesos propios, verificados por PID, hora de creación y línea de comandos.
- **Sesión del dueño compartida por todos los canales.** Con PIN configurado, SKY arranca bloqueada y pregunta «¿Cuál es tu PIN?». Bloqueada:
  - la API responde 423, salvo salud, desbloqueo y parada de emergencia;
  - el agente, la voz manos libres, WhatsApp y Streamlit no ejecutan nada.
  - Se desbloquea con el PIN hablado (dígito por dígito, procesado localmente) o escrito.
  - Se vuelve a bloquear por voz, texto, botón o consola.
  - Hay espera progresiva entre intentos, bloqueo de 15 minutos y recuperación local.
  - Falla cerrado: si no puede leer el estado de la sesión, la considera bloqueada.
  - Los permisos por dispositivo y herramienta no cambian.
- **El token del agente ya no se imprime en los registros.**
- **Escrituras JSON atómicas con candado entre procesos** (`neural_core/sky_archivo_seguro.py`) para la sesión de voz, el coordinador de voz y SENTINEL. El coordinador ya no pisa el estado al importarse.
- **«Listo» sólo cuando está preparado:** cada servicio tiene comprobación de preparación y de vida. Se agregó `GET /api/health/listo`.
- **`--status` honesto:** si la salud falla, ya no dice «online». Incluye causa y pasos concretos.
- **Arrancar no manda mensajes:** los recordatorios vencidos con SKY apagada quedan en el HUD. Las alertas de KPIs y la actualización de temas no corren al arrancar.

## P1: estabilidad, recuperación, voz y latencia
- **Supervisor:**
  - reinicios sin bloquear el ciclo, con espera progresiva (2, 4, 8, 16 y 32 s), como máximo 5 por hora y después cada 30 minutos;
  - las fallas permanentes no se reintentan en bucle (código 2: falta configuración; 3: sin micrófono);
  - detecta cuelgues a los 90 s sin respuesta con el proceso vivo;
  - registros rotativos en `local_data/logs`;
  - cierre limpio (CTRL+BREAK o SIGTERM) y `--stop`;
  - inicio con Windows mediante `pythonw.exe`, sin consola que cerrar por error.
- **`/api/health` asíncrona:** una inferencia lenta ya no parece un cuelgue.
- **Voz manos libres:**
  - puerta de sesión antes de interpretar;
  - órdenes duplicadas descartadas (ventana de 3 s);
  - frases y respuestas fuera de los registros salvo en una consola interactiva;
  - latencia por etapa (interpretación, agente, modelo, voz y turno) en los KPIs;
  - acciones verificadas separadas de las enviadas sin comprobar.
- **Resultados reales:** se distingue entre verificada, enviada sin comprobar, pendiente, bloqueada y fallida, en la voz y en las rutinas.
- **Latencia:**
  - faster-whisper se carga una vez y no en cada transcripción (dentro del proceso);
  - la API ya no importa trimesh ni scipy al arrancar. Esa importación costaba 1,7 s medidos.
- `get_pid_using_port` sólo acepta la línea `LISTENING` del puerto.
- uvicorn corre sin registro de accesos, porque las rutas pueden llevar tus consultas.

## P2: módulos y experiencia
- **Registro de módulos** (`neural_core/sky_modulos.py`), que reutiliza las 26 integraciones y el estado del supervisor:
  - estados disponible, no configurado, cargando, activo, degradado y error, con lo que falta exactamente;
  - carga bajo demanda con límite de memoria y concurrencia; si un módulo falla, no afecta al resto;
  - se usa por voz o texto, por la API (`/api/hud/modulos`) y desde la ventana «Módulos» del HUD.
- `sky_pin.py`: configurar, estado, bloquear, desbloquear y restablecer, sin aceptar el PIN como argumento.
- `SKY_INICIAR.bat`: opciones **P** (PIN) y **S** (detener). El instalador ofrece configurar el PIN.
- Variables nuevas en `.env.example`: `SKY_SESION_MAX_HORAS`, `SKY_MODULOS_CONCURRENCIA`, `SKY_MODULOS_RESERVA_MB`, `SKY_OLLAMA_RAM_MB`, `SKY_OLLAMA_KEEP_ALIVE`, `SKY_RECORDATORIO_TOLERANCIA_MIN`, `SKY_VOZ_DEPURAR`, `SKY_SUPERVISOR_DIR` y `SKY_LOG_DIR`.

## Compatibilidad
- Se conservan las rutas, las opciones de línea de comandos y las funciones públicas del lanzador:
  - `is_port_in_use`, `es_servicio_sky`, `get_pid_using_port`, `kill_process_by_pid`, `clean_port_conflicts`, `check_system_status`, `manage_windows_startup` y `SkySupervisor`;
  - `call_device` y `ejecutar_local_si_autorizado`, que sólo suman un parámetro opcional `origen`.
- Cambios de comportamiento a propósito:
  - con PIN configurado, la llave sola ya no alcanza mientras la sesión esté bloqueada (423);
  - `--kill-ports` sólo cierra procesos propios huérfanos;
  - en las rutinas, una acción `enviada` sin verificación ya no se informa como `ok`.
- Sin dependencias nuevas.

## Pruebas
- 36 pruebas nuevas en `tests/test_sky_v12_6_fiabilidad.py`; también se ejecutan en el flujo de CI de seguridad.
- Suite completa: 1252 aprobadas, 30 fallidas y 3 omitidas. Las 30 fallas son las mismas de `main` y dependen del entorno (Docker, compiladores, MarkItDown, MCP).
- Validación en vivo en Linux con Chromium:
  - segundo arranque sin duplicar procesos;
  - recuperación de la API en 3,6 s tras `kill -9`;
  - flujo de PIN en el HUD (423, PIN incorrecto, PIN correcto, «bloquéate» y parada);
  - el núcleo sigue activo tras cerrar el navegador;
  - `--stop` deja 0 procesos.
- **Pendiente en Windows con micrófono:** ver la sección 7 de la auditoría.
