# SKY IA — Validación de latencia y escucha natural (26/10/2026)

## Hallazgos reales del Windows del propietario

Estos números provienen de pruebas manuales, **antes de aplicar esta rama**:

| Prueba | Resultado |
| --- | --- |
| `ollama run qwen2.5:7b` — saludo | 5.485 s |
| `sky_cerebro.decidir("hola sky", [], "voz")` | 5.8 s |
| `sky_asistente_personal.reglas("hola sky")` | ~0 s |
| `/api/asistente/stream`, primer evento | 11.796 s |
| Respuesta interna informada por `/stream` | 21 ms |
| `/docs` | 9–26 ms |
| `/static/hud.js` (última serie) | 7–17 ms |
| `/api/health` (última serie) | 1.477–1.481 s |
| Escritura individual SQLite KPIs | 1.455 s |
| Escritura individual SQLite telemetría | 0.017 s |
| Uso RAM y capacidad de disco ocupada | 88.3% RAM; 95.9% disco |

**Hipótesis principal:** la escritura sincrónica de métricas en middleware puede sumar latencia a peticiones HTTP. Los datos no demuestran que sea la única causa. Esta rama retira las escrituras SQLite del camino crítico y conserva ambos destinos de registros, con un contador de descartes si la cola se satura.

## Archivos propuestos

- `neural_core/sky_http_metrics_queue.py`: cola de métricas acotada.
- `metaverse/api.py`: registra sin esperar SQLite; intenta drenar al apagar.
- `sky_manos_libres.py`: escucha continua sin palabra clave **solo opt-in** mediante `SKY_VOICE_ALWAYS_LISTEN=1` o `--no-wake-word`; conserva permisos del agente y detección del usuario. Una frase ambiental parecida a una orden puede ser mal interpretada: probar solo en un entorno controlado.
- `metaverse/static/hud.js`: con CONV habilitado y escucha activa, permite comandos sin prefijo «SKY» usando STT local y reconoce «abrí panel de chat de SKY».
- `tests/test_sky_latency_and_wordless_voice.py`: regresiones enfocadas en espera no bloqueante y reconocimiento.
- `scripts/APLICAR_SKY_LATENCIA_VOZ.py`: aplicación reversible y respaldos para carpetas Windows sin `.git`.
- `.github/workflows/sky-v106-global-readiness.yml`: ejecuta las pruebas nuevas y sintaxis del HUD.

## Aplicación local, conservadora

Con SKY cerrado, desde la **raíz** de la instalación:

```powershell
& .\.venv\Scripts\python.exe .\scripts\APLICAR_SKY_LATENCIA_VOZ.py
& .\.venv\Scripts\python.exe .\scripts\APLICAR_SKY_LATENCIA_VOZ.py --aplicar
```

Requiere Git instalado y accesible desde PowerShell; no requiere que la carpeta SKY contenga `.git`. La primera orden comprueba aplicabilidad y **no modifica nada**. Si los archivos de Windows divergen del parche, se detiene sin sobrescribir cambios.

Para probar solo esta sesión (opcional y con consentimiento):

```powershell
$env:SKY_VOICE_ALWAYS_LISTEN = "1"
.\SKY_INICIAR.bat
```

No activar a la vez varias capturas del mismo micrófono; verificar el estado del coordinador antes de hablar. El modo manual y el modo que exige «SKY» permanecen disponibles. El modo sin palabra clave no autoriza operaciones peligrosas y no es prueba de reconocimiento de hablante.

## Validación posterior obligatoria

1. Medir `/docs`, `/api/health`, `/static/hud.js` al menos diez veces en Windows antes/después con `requests.Session(trust_env=False)`; registrar p50 y p95.
2. Comprobar persistencia de registros SQLite y `queue_status()` bajo carga moderada.
3. Probar 20 órdenes por micrófono Logitech y también cinco frases ambientales; exigir ausencia de ejecución accidental.
4. Probar pausa, reanudación y micrófono ocupado o desconectado.
5. Comprobar que «abrí Word» abre Word realmente con política permitida.
6. Comprobar «abrí el panel de chat de SKY» en el HUD. Cuando el HUD está cerrado, aún no existe una garantía de notificación de ventana desde el servicio Vosk: requiere fase posterior.
7. **No afirmar que «abrí Word y redactá un informe» está terminada**. El planificador de varias acciones debe integrar creación, almacenamiento y verificación de documentos.
8. Mantener `main` intacto hasta pruebas locales y CI específicas.

## Límites conocidos

- Los procesos actuales de Windows y las aplicaciones no pueden certificarse desde GitHub Actions.
- Una cola acotada evita bloquear HTTP, pero puede descartar métricas si SQLite se atasca; el contador permite observarlo.
- La voz sin palabra clave debe activarse expresamente y puede captar conversaciones ajenas.
- Con 95.9 % del disco ocupado no es prudente lanzar entrenamiento LoRA ni instalar motores adicionales sin recuperar espacio.
