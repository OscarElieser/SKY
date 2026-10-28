"""Modo de escucha voluntaria con palabra de activación (Vosk local).

Requisitos opcionales: pip install vosk sounddevice pyttsx3
Descargar modelo Vosk ES, extraerlo y arrancar:
python sky_manos_libres.py --model ./modelos/vosk-model-es

La voz sólo ejecuta al instante las capacidades que el dueño marcó como automáticas
(agente_dispositivo.py --auto ...); el resto queda pendiente de confirmación en /asistente.

v12.6: con PIN configurado, la escucha arranca preguntando «¿Cuál es tu PIN?» y no obedece nada (salvo la parada
de emergencia) hasta que la sesión del dueño se abra. El PIN se reconoce localmente y nunca se imprime ni se guarda.
«SKY, bloquéate» vuelve a bloquear todo SKY. Cada etapa del turno queda medida en los KPIs de voz.
"""
from __future__ import annotations
import argparse, json, os, queue, sys, re, time
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent/'.env')
from neural_core.dispositivos import norm
from neural_core.sky_asistente_personal import (interpretar as interpret_command, ejecutar_local_si_autorizado,
                                               describir_resultado)
from neural_core.sentinel_identidad import pin_configurado as _pin_configurado
from neural_core.voz_inbox import add_inbox
from neural_core.assistant import responder
from neural_core.providers import choose_provider
from neural_core.sky_voice_queue import VoiceWorkQueue, wake_during_speech, parada_emergencia_voz
from neural_core.sky_voz_sesion import PuertaVoz
from neural_core.sky_archivo_seguro import actualizar_json
from neural_core import sky_metricas

WAKE_WORDS=('sky','esquai','es kay','es cai','escai')

# This mode is opt-in: ambient speech is *never* treated as a command by
# default. Even when enabled, require a direct imperative/question, or an
# already-active conversational follow-up. Device permissions still apply.
DIRECTED_START = re.compile(
    r'^(?:hola|buenas|oye|mira|necesito|quiero|ayudame|explicame|'
    r'abre|abri|abrir|mostra|muestra|mostrar|crea|crear|redacta|redactame|'
    r'escribe|escribi|prepara|preparame|guarda|guardar|busca|buscar|'
    r'reproduce|pausa|continua|reanuda|baja|sube|silencia|'
    r'cierra|cerra|cerrar|lee|leeme|dime|decime|pon|pone|'
    r'como|que|cual|cuanto|cuando|donde|por que|para que|'
    r'quiero saber|puedes|podes|podrias|podrias ayudarme)\b'
)


def is_directed_speech(text: str) -> bool:
    return bool(DIRECTED_START.match(norm(str(text or '')).strip()))


def _privado() -> bool:
    """Sin consola (inicio con Windows → registros en archivo) no se escriben las frases reconocidas."""
    if os.getenv('SKY_VOZ_DEPURAR', '0') == '1':
        return False
    try:
        return not (sys.stdout is not None and sys.stdout.isatty())
    except (AttributeError, ValueError):
        return True


def _medir(nombre: str, inicio: float, ok: bool = True, detalle: str = '') -> None:
    sky_metricas.registrar('voz', nombre, ok, (time.perf_counter() - inicio) * 1000, origen='manos_libres', detalle=detalle)


def text_after_wake(text):
    normalized=norm(text)
    for word in WAKE_WORDS:
        match=re.search(r'(?<!\w)'+re.escape(word)+r'(?!\w)',normalized)
        if match:
            return text[match.end():].strip(' ,.:;!?¿¡')
    return None


def main():
    default_model = Path(__file__).resolve().parent / 'modelos' / 'vosk-model-es'
    model_exists = default_model.is_dir()
    parser=argparse.ArgumentParser(description='Escucha privada con Vosk; activa con “SKY”.')
    parser.add_argument('--model', default=str(default_model) if model_exists else None,
                        required=False, help='Carpeta descargada del modelo Vosk de español')
    parser.add_argument('--rate',type=int,default=16000)
    parser.add_argument('--input-device',default=os.getenv('SKY_MICROPHONE_DEVICE',''),
                        help='Índice o nombre del micrófono; consultá --list-input-devices.')
    parser.add_argument('--list-input-devices',action='store_true',
                        help='Lista entradas de audio sin cargar el modelo Vosk.')
    parser.add_argument('--execute-safe',action='store_true',
                        default=os.getenv('SKY_EXECUTE_SAFE', '1') in ('1', 'true', 'yes'),
                        help='Ejecuta solo capacidades automáticas autorizadas por el dueño.')
    listen_group = parser.add_mutually_exclusive_group()
    listen_group.add_argument('--no-wake-word', action='store_true',
                              help='Habilita escucha natural sin decir SKY, por decisión del propietario.')
    listen_group.add_argument('--require-wake', action='store_true',
                              help='Exige SKY incluso si la opción de escucha natural está configurada.')
    args=parser.parse_args()
    if args.list_input_devices:
        try:
            import sounddevice as sd
            from neural_core.sky_audio_devices import input_summary
            for item in input_summary(sd.query_devices()):
                print(f"{item['index']}: {item['name']}")
        except Exception as exc:
            print('No pude listar micrófonos:', type(exc).__name__)
        return
    allow_wordless = not args.require_wake and (
        args.no_wake_word or os.getenv('SKY_VOICE_ALWAYS_LISTEN', '0').lower()
        in ('1', 'true', 'yes'))
    wordless_active = allow_wordless
    # v12.6: códigos de salida que el supervisor entiende: 2 = falta configuración (no reintentar en bucle),
    # 3 = no hay micrófono (reintentar cada 5 minutos).
    if not args.model or not Path(args.model).is_dir():
        print('NO_CONFIGURADO: no existe el modelo Vosk de español. Descargá uno y pasá --model carpeta.', file=sys.stderr)
        sys.exit(2)
    try:
        import sounddevice as sd
        from vosk import Model, KaldiRecognizer
    except (ImportError, OSError) as exc:
        print(f'NO_CONFIGURADO: falta una dependencia de voz ({type(exc).__name__}: {str(exc)[:120]}). '
              'Instalá: pip install vosk sounddevice pyttsx3', file=sys.stderr)
        sys.exit(2)
    audio=queue.Queue(maxsize=50)
    voice_runtime = None
    last_audio = 0.0
    def callback(indata, frames, time_info, status):
        nonlocal last_audio
        # El callback del micrófono nunca espera a Ollama ni a pyttsx3.
        last_audio = time.time()
        speaking_at_capture = bool(voice_runtime and voice_runtime.speaking)
        try: audio.put_nowait((speaking_at_capture, bytes(indata)))
        except queue.Full: pass
    def create_stream_and_recognizer():
        # Sólo un modelo Vosk, incluso al probar múltiples tasas de muestreo.
        from neural_core.sky_audio_devices import candidate_inputs
        try:
            devices = sd.query_devices()
            default_input = sd.default.device[0]
            inputs = candidate_inputs(devices, default_input, args.input_device)
        except ValueError as exc:
            print('NO_CONFIGURADO: micrófono seleccionado no disponible: ' + str(exc), file=sys.stderr)
            sys.exit(3)
        except Exception as exc:
            print('Sin entradas de micrófono:', type(exc).__name__, file=sys.stderr)
            sys.exit(3)
        if not inputs:
            print('No hay micrófonos reconocidos.', file=sys.stderr)
            sys.exit(3)
        vosk_model = Model(args.model)
        failures = []
        for dev_id, name in inputs:
            try:
                dev_sr = int(devices[dev_id].get('default_samplerate', 0))
            except (TypeError, ValueError):
                dev_sr = 0
            rates = list(dict.fromkeys(r for r in (args.rate, dev_sr, 48000, 44100, 16000) if r))
            for candidate_rate in rates:
                st = None
                try:
                    st = sd.RawInputStream(device=dev_id,samplerate=candidate_rate,
                        blocksize=8000,dtype='int16',channels=1,callback=callback)
                    st.start()
                    rec = KaldiRecognizer(vosk_model, candidate_rate)
                    print(f'SKY micrófono: {name} (índice {dev_id}, {candidate_rate} Hz)',flush=True)
                    return st,rec
                except Exception as exc:
                    failures.append((dev_id,candidate_rate,type(exc).__name__))
                    if st is not None:
                        try: st.close()
                        except Exception: pass
        print('No se pudo abrir el micrófono:',failures[:8],file=sys.stderr)
        sys.exit(3)

    try:
        stream, recognizer = create_stream_and_recognizer()
    except Exception as exc:
        print(f'SIN_MICROFONO: no pude abrir ningún micrófono ({type(exc).__name__}: {str(exc)[:160]}). '
              'Conectalo o habilitalo en Configuración > Privacidad > Micrófono.', file=sys.stderr)
        sys.exit(3)
    if allow_wordless:
        print('SKY: escucha natural activada por el dueño; acepto órdenes directas sin decir “SKY”.')
        print('Para pausar: “pausa la conversación”; para volver: “reanuda la conversación”.')
    else:
        print('SKY: micrófono activo; decí “SKY” antes de la pregunta. Ctrl+C para finalizar.')
    print('La voz se reconoce localmente con Vosk; el texto consulta al proveedor SKY que configuraste.')
    from neural_core.voice_coordinator import coordinador_voz, VoiceState, InteractionMode

    history = []
    def process_command(command):
        """Ejecutado por un solo trabajador; nunca bloquea el micrófono."""
        nonlocal history
        if puerta.bloqueada():   # la sesión pudo bloquearse mientras la orden esperaba en la cola
            voice_runtime.say('SKY se bloqueó antes de ejecutar la orden. ¿Cuál es tu PIN?')
            return
        turno = time.perf_counter()
        # Acciones del HUD: no se ejecutan en el navegador de Windows.
        from neural_core.sky_hud_window_requests import parse_window_request, publish as publish_window
        ventana_hud = parse_window_request(command)
        if ventana_hud:
            try:
                publish_window(ventana_hud)
                voice_runtime.say("Preparé la ventana solicitada dentro de SKY. Verificala en el HUD.")
            except Exception as exc:
                print("SKY: error de ventana HUD:", type(exc).__name__, str(exc)[:120])
                voice_runtime.say("No pude preparar la ventana del HUD.")
            return
        # Las solicitudes de módulos usan el mismo catálogo que HUD, sin invocar Ollama.
        # El navegador autenticado recoge el evento y abre únicamente el módulo pedido.
        from neural_core.sky_module_registry import match_activation, publish_activation
        modulo_pedido = match_activation(command)
        if modulo_pedido:
            try:
                publish_activation(modulo_pedido["id"])
                voice_runtime.say(
                    "Preparé el módulo " + modulo_pedido["title"] +
                    ". Se abrirá en el HUD principal si está conectado."
                )
            except Exception as exc:
                print("SKY: error activando módulo:", type(exc).__name__, str(exc)[:120])
                voice_runtime.say("No pude preparar ese módulo. Revisá el registro de SKY.")
            return
        coordinador_voz.set_state(VoiceState.PROCESANDO)
        from neural_core import sky_hermes
        if sky_hermes._ORDEN.match(sky_hermes._norm(command)):
            # v12.6: Hermes como consultor; su respuesta es sólo texto y nunca se ejecuta.
            voice_runtime.say('Le pregunto a Hermes; puede tardar un poco.')
            t = time.perf_counter()
            r = sky_hermes.interpretar(command)
            _medir('ml_modelo', t, bool(r), 'hermes')
            if r and not voice_runtime.current_turn_cancelled:
                coordinador_voz.record_turn(command, r['mensaje'])
                voice_runtime.say(r['mensaje'])
            _medir('ml_turno', turno, bool(r), 'hermes')
            return
        t = time.perf_counter()
        intent = interpret_command(command)
        _medir('ml_interpretar', t)
        if voice_runtime.current_turn_cancelled:
            return
        if intent:
            coordinador_voz.set_state(VoiceState.EJECUTANDO_HERRAMIENTA)
            hecho = None
            t = time.perf_counter()
            if args.execute_safe:
                try:
                    hecho = ejecutar_local_si_autorizado(intent)
                except Exception as exc:
                    hecho = {'ok': False, 'message': 'No se pudo ejecutar la orden. Revisá el agente local.'}
                    print('Detalle:', type(exc).__name__, str(exc)[:160])
            estado, frase = describir_resultado(hecho)
            _medir('ml_ejecutar', t, estado in ('verificada', 'enviada', 'pendiente'), estado)
            if voice_runtime.current_turn_cancelled:
                return
            if hecho is None:
                add_inbox(command, intent)
                mensaje = 'Preparé la orden: ' + intent.get('description', 'acción') + '. Confirmala en el panel de SKY.'
            else:
                # v12.6: «Listo» sólo si el agente comprobó el efecto; si no, se dice que se envió sin comprobar.
                mensaje = frase
            coordinador_voz.record_turn(command, mensaje)
            t = time.perf_counter()
            voice_runtime.say(mensaje)
            _medir('ml_tts', t)
            _medir('ml_turno', turno, estado != 'fallida', 'accion:' + estado)
            return
        # Respuesta hablada PROGRESIVA opt-in para preguntas públicas aisladas:
        # Ollama local, sin historial ni herramientas; todas las demás órdenes
        # siguen en el flujo habitual con permisos, memoria y confirmación.
        from neural_core.sky_voice_stream_local import eligible as voz_rapida_apta, speak_stream
        if voz_rapida_apta(command, history):
            t = time.perf_counter()
            try:
                silencio_inicial = voice_runtime.speech_interrupt_epoch
                resultado = speak_stream(
                    command,
                    voice_runtime.say,
                    cancelled=lambda: (
                        voice_runtime.current_turn_cancelled or
                        voice_runtime.speech_interrupt_epoch != silencio_inicial
                    ),
                )
                if resultado.first_tts_s is not None:
                    # Primer ENVÍO al TTS, no se presume primer sonido audible.
                    sky_metricas.registrar(
                        'voz', 'ml_primer_tts', True,
                        resultado.first_tts_s * 1000,
                        origen='manos_libres', detalle='ollama_local_progresivo',
                    )
                _medir('ml_voz_progresiva', t, resultado.ok, resultado.error or 'ollama')
                if voice_runtime.current_turn_cancelled or resultado.error == 'cancelled':
                    return
                if resultado.ok:
                    history.extend([
                        {'role': 'user', 'content': command},
                        {'role': 'assistant', 'content': resultado.text},
                    ])
                    history = history[-10:]
                    coordinador_voz.record_turn(command, resultado.text)
                    _medir('ml_turno', turno, True, 'conversacion_progresiva')
                else:
                    # No reintentar de forma oculta después de una respuesta
                    # parcial: evitar duplicar voz y solicitudes cloud.
                    voice_runtime.say('No pude completar la respuesta local.')
                    _medir('ml_turno', turno, False, 'conversacion_progresiva')
            except Exception as exc:
                print('SKY: error de voz progresiva:', type(exc).__name__)
                _medir('ml_voz_progresiva', t, False, type(exc).__name__)
                if not voice_runtime.current_turn_cancelled:
                    voice_runtime.say('No pude completar la consulta local.')
            return

        try:
            t = time.perf_counter()
            provider, modelo = choose_provider(os.getenv('SKY_VOICE_PROVIDER', 'auto'), 'SKY voz')
            answer, _ = responder(command, 'SKY voz local', history, modelo, proveedor=provider)
            _medir('ml_modelo', t, True, str(provider)[:40])
            if voice_runtime.current_turn_cancelled:
                return
            history.extend([{'role': 'user', 'content': command}, {'role': 'assistant', 'content': answer}])
            history = history[-10:]
            coordinador_voz.record_turn(command, answer)
            t = time.perf_counter()
            voice_runtime.say(answer)
            _medir('ml_tts', t)
            _medir('ml_turno', turno, True, 'conversacion')
        except Exception as exc:
            print('Detalle:', type(exc).__name__, str(exc)[:160])
            _medir('ml_modelo', t, False, type(exc).__name__)
            _medir('ml_turno', turno, False, 'conversacion')
            if not voice_runtime.current_turn_cancelled:
                voice_runtime.say('No pude completar esta consulta. Revisá Ollama o el proveedor de IA.')

    puerta = PuertaVoz()
    voice_runtime = VoiceWorkQueue(
        process_command,
        rate_factory=lambda: int(180 * coordinador_voz.get_speech_rate()),
        speech_state=coordinador_voz.set_speaking,
    )
    voice_runtime.start()

    def say(message):
        """Encolar respuesta, sin bloquear el hilo que reconoce la voz."""
        if not voice_runtime.announce(message):
            print('SKY: cola de voz llena; omitida notificación:', str(message)[:100])

    def sync_state(data):
        # v12.6: escritura atómica con candado entre procesos (antes un lector podía ver JSON a medio escribir y
        # creer que la escucha estaba apagada). Nunca se guardan frases: sólo marcas de tiempo y estados.
        try:
            st_path = Path(__file__).resolve().parent / 'local_data' / 'sky_session_state.json'
            def mezclar(existente):
                existente = existente if isinstance(existente, dict) else {}
                existente.pop('last_command', None)
                existente.update(data)
                existente['pid'] = os.getpid()
                return existente
            actualizar_json(st_path, mezclar, {}, indent=2)
        except Exception:
            pass

    SESSION_TIMEOUT = 35.0
    active_until = 0.0
    sync_state({'hands_free_listening': True, 'wordless_owner_enabled': allow_wordless,
                'wordless_active': wordless_active, 'last_audio': last_audio,
                'last_seen': time.time(), 'status': 'ready', 'coordinator_state': VoiceState.ESPERANDO_ACTIVACION.value})

    saludo = puerta.saludo_inicial()
    if saludo:
        say(saludo)
    elif not puerta.bloqueada() and not _pin_configurado():
        print('AVISO: SKY no tiene PIN. Cualquiera cerca del micrófono puede darle órdenes. '
              'Configuralo con: python sky_pin.py configurar')
    sync_state({'sesion_bloqueada': puerta.bloqueada()})

    ultimo_latido = time.monotonic()
    ultima_transicion_tts = voice_runtime.speech_epoch
    try:
        with stream:
            while True:
                # Timeout para poder verificar la escucha incluso durante silencio.
                # El latido refleja el consumo REAL del audio por este proceso.
                try:
                    packet = audio.get(timeout=1.0)
                except queue.Empty:
                    packet = None
                # Cuando cambia la reproducción de SKY, descartar fonemas de
                # eco pendientes antes de aceptar órdenes nuevas.
                epoch = voice_runtime.speech_epoch
                if epoch != ultima_transicion_tts:
                    recognizer.Reset()
                    ultima_transicion_tts = epoch
                    while not audio.empty():
                        try: audio.get_nowait()
                        except queue.Empty: break
                    packet = None
                if time.monotonic() - ultimo_latido >= 5:
                    sync_state({'last_seen': time.time(), 'last_audio': last_audio, 'sesion_bloqueada': puerta.bloqueada(),
                                'hands_free_listening': True, 'wordless_active': wordless_active,
                                'status': 'paused' if coordinador_voz.get_state() == VoiceState.PAUSADO else 'ready'})
                    ultimo_latido = time.monotonic()
                if packet is None:
                    continue
                audio_durante_tts, buffer = packet
                if not recognizer.AcceptWaveform(buffer): continue
                result=json.loads(recognizer.Result()).get('text','').strip()
                if not result: continue

                # La parada de emergencia NO espera a que Ollama termine.
                # Durante TTS se exige el prefijo SKY para evitar falsos
                # positivos del audio de salida.
                durante_tts = audio_durante_tts or voice_runtime.speaking
                if parada_emergencia_voz(result, exigir_activacion=durante_tts):
                    from neural_core.sky_asistente_personal import parada
                    alerta = parada("sky para todo")
                    if alerta:
                        voice_runtime.cancel_pending()
                        voice_runtime.interrupt_speech()
                        active_until = 0.0
                        wordless_active = False
                        coordinador_voz.pause_session()
                        sync_state({'session_active': False, 'status': 'paused',
                                    'wordless_active': False,
                                    'coordinator_state': VoiceState.PAUSADO.value})
                        say(alerta['mensaje'])
                    continue

                # Para evitar autoejecuciones por eco: durante TTS sólo se
                # permite pedir silencio con "SKY ..."; nunca ejecutar acciones.
                if durante_tts:
                    if wake_during_speech(result):
                        voice_runtime.interrupt_speech()
                        print('SKY: interrumpiendo voz; repetí la orden cuando termine.')
                    continue

                # v12.6 — sesión del dueño: bloqueada, sólo se procesa el PIN (localmente y sin registrar nada).
                control = puerta.evaluar(result, text_after_wake(result))
                if control is not None:
                    result = None
                    recognizer.Reset()
                    if control['desbloqueada']:
                        active_until = time.time() + SESSION_TIMEOUT
                        coordinador_voz.activate_session()
                    sync_state({'sesion_bloqueada': control['bloqueada'], 'last_wake': time.time()})
                    if control['decir']:
                        say(control['decir'])
                    continue

                # Verificar si el usuario está en modo C (texto) y no solicitó reactivar voz
                current_mode = coordinador_voz.get_mode()
                clean_raw = norm(result)
                if current_mode == InteractionMode.MODO_C_TEXTO:
                    if not any(w in clean_raw for w in ('volve a hablarme', 'activa la conversacion', 'modo voz', 'hablame')):
                        continue
                    else:
                        coordinador_voz.set_mode(InteractionMode.MODO_A_NATURAL)

                now = time.time()
                command = text_after_wake(result)

                if command is not None:
                    # Palabra clave "SKY" detectada -> Activar sesión continua
                    active_until = now + SESSION_TIMEOUT
                    coordinador_voz.activate_session()
                    sync_state({'session_active': True, 'active_until': active_until, 'last_wake': now, 'coordinator_state': VoiceState.ESCUCHANDO.value})
                elif (coordinador_voz.is_in_follow_up_window() or (now < active_until)
                      or (wordless_active and is_directed_speech(result))
                      or (allow_wordless and re.fullmatch(
                          r'(?:reanuda|reactiva|continua) (?:la conversacion|a escuchar)',
                          clean_raw))):
                    # In owner-enabled natural mode, a direct instruction can
                    # start a session without requiring the wake word.
                    command = result.strip(' ,.:;!?¿¡')
                    active_until = now + SESSION_TIMEOUT
                    coordinador_voz.activate_session()
                else:
                    sync_state({'session_active': False, 'coordinator_state': VoiceState.ESPERANDO_ACTIVACION.value})
                    continue

                if not command:
                    say('Te escucho. Indicame qué necesitás.')
                    continue

                # Comprobar orden de cierre o pausa de conversación
                clean_cmd = norm(command)
                v_ctrl = coordinador_voz.check_voice_control_command(clean_cmd)
                if v_ctrl:
                    subact = v_ctrl.get('subaction')
                    msg = v_ctrl.get('message', 'Comando recibido.')
                    if subact in ('pause_session', 'end_session'):
                        active_until = 0.0
                        wordless_active = False
                        sync_state({'session_active': False, 'status': 'paused' if subact == 'pause_session' else 'idle',
                                    'wordless_active': wordless_active, 'coordinator_state': coordinador_voz.get_state().value})
                    elif subact in ('resume_session', 'activate_natural'):
                        wordless_active = allow_wordless
                        sync_state({'wordless_active': wordless_active, 'status': 'ready'})
                    say(msg)
                    continue

                bloqueo = puerta.bloquear_por_voz(command)
                if bloqueo:
                    voice_runtime.cancel_pending()
                    active_until = 0.0
                    sync_state({'sesion_bloqueada': puerta.bloqueada(), 'session_active': False})
                    say(bloqueo['decir'])
                    continue

                print('Escuchado:', f'{len(command)} caracteres' if _privado() else command)
                sync_state({'last_command_at': now, 'timestamp': now, 'coordinator_state': VoiceState.PROCESANDO.value})
                if not voice_runtime.submit(command):
                    # Nunca ejecutar una acción concurrentemente ni perder el límite
                    # de seguridad de la cola: se solicita repetir cuando libere.
                    print('SKY: cola de voz ocupada. Repetí tu solicitud en unos momentos.')
    except KeyboardInterrupt:
        coordinador_voz.set_state(VoiceState.ESPERANDO_ACTIVACION)
        print('Micrófono desactivado. SKY-IA finalizado.')
    finally:
        voice_runtime.stop()
        sync_state({'hands_free_listening': False, 'session_active': False, 'status': 'stopped',
                    'wordless_active': False, 'coordinator_state': VoiceState.ESPERANDO_ACTIVACION.value})

def _start_single_instance() -> None:
    # Prevenir dos capturas Vosk del mismo micrófono antes de cargar el modelo.
    from neural_core.sky_voice_single_instance import single_voice_instance
    with single_voice_instance() as acquired:
        if not acquired:
            print('SKY: ya existe una escucha Vosk activa; no abriré otro micrófono.',flush=True)
            sys.exit(42)
        main()


if __name__=='__main__': _start_single_instance()
