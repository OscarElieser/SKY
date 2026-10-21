"""Modo de escucha voluntaria con palabra de activación (Vosk local).

Requisitos opcionales: pip install vosk sounddevice pyttsx3
Descargar modelo Vosk ES, extraerlo y arrancar:
python sky_manos_libres.py --model ./modelos/vosk-model-es

La voz no ejecuta nunca acciones remotas sin consentimiento desde el panel.
"""
from __future__ import annotations
import argparse, json, os, queue, sys, re
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent/'.env')
from neural_core.dispositivos import interpret_command, norm
from neural_core.voz_inbox import add_inbox
from neural_core.assistant import responder
from neural_core.providers import choose_provider

WAKE_WORDS=('sky','esquai','es kay','es cai','escai')


def text_after_wake(text):
    normalized=norm(text)
    for word in WAKE_WORDS:
        match=re.search(r'(?<!\w)'+re.escape(word)+r'(?!\w)',normalized)
        if match:
            return text[match.end():].strip(' ,.:;!?¿¡')
    return None


def main():
    parser=argparse.ArgumentParser(description='Escucha privada con Vosk; activa con “SKY”.')
    parser.add_argument('--model',required=True,help='Carpeta descargada del modelo Vosk de español')
    parser.add_argument('--rate',type=int,default=16000)
    parser.add_argument('--execute-safe',action='store_true',help='Autoriza abrir sitios HTTPS y apps permitidas en el equipo local al oír SKY.')
    args=parser.parse_args()
    if not Path(args.model).is_dir():
        sys.exit('No existe el modelo Vosk de español. Descargá uno y pasá --model carpeta.')
    try:
        import sounddevice as sd
        from vosk import Model, KaldiRecognizer
    except ImportError:
        sys.exit('Instalá dependencias opcionales: pip install vosk sounddevice pyttsx3')
    try:
        import pyttsx3
        tts=pyttsx3.init()
    except Exception:
        tts=None
    audio=queue.Queue(maxsize=50)
    speaking=False
    def callback(indata, frames, time, status):
        if speaking: return
        try: audio.put_nowait(bytes(indata))
        except queue.Full: pass
    def create_stream_and_recognizer():
        input_devices = [None]
        try:
            for idx, d in enumerate(sd.query_devices()):
                if d.get('max_input_channels', 0) > 0:
                    input_devices.append(idx)
        except Exception:
            pass

        for dev_id in input_devices:
            dev_sr = None
            if dev_id is not None:
                try:
                    dev_sr = int(sd.query_devices(dev_id).get('default_samplerate', 0))
                except Exception:
                    pass
            rates = [r for r in [args.rate, dev_sr, 48000, 44100, 16000] if r]
            for candidate_rate in rates:
                try:
                    st = sd.RawInputStream(device=dev_id, samplerate=candidate_rate, blocksize=8000, dtype='int16', channels=1, callback=callback)
                    st.start()
                    rec = KaldiRecognizer(Model(args.model), candidate_rate)
                    return st, rec
                except Exception:
                    continue
        rec = KaldiRecognizer(Model(args.model), args.rate)
        st = sd.RawInputStream(samplerate=args.rate, blocksize=8000, dtype='int16', channels=1, callback=callback)
        return st, rec

    stream, recognizer = create_stream_and_recognizer()
    print('SKY: micrófono activo; decí “SKY” antes de la pregunta. Ctrl+C para finalizar.')
    print('La voz se reconoce localmente con Vosk; el texto consulta al proveedor SKY que configuraste.')
    history=[]
    def say(message):
        nonlocal speaking
        print('SKY-IA:',message)
        if tts:
            speaking=True
            try:
                tts.say(message[:1000]); tts.runAndWait()
            finally:
                speaking=False
                while not audio.empty():
                    try: audio.get_nowait()
                    except queue.Empty: break

    def sync_state(data):
        try:
            st_path = Path(__file__).resolve().parent / 'local_data' / 'sky_session_state.json'
            st_path.parent.mkdir(parents=True, exist_ok=True)
            existing = {}
            if st_path.exists():
                try: existing = json.loads(st_path.read_text(encoding='utf-8'))
                except Exception: pass
            existing.update(data)
            st_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception:
            pass

    import time
    SESSION_TIMEOUT = 25.0
    active_until = 0.0
    sync_state({'hands_free_listening': True, 'last_seen': time.time(), 'status': 'ready'})

    try:
        with stream:
            while True:
                buffer=audio.get()
                if not recognizer.AcceptWaveform(buffer): continue
                result=json.loads(recognizer.Result()).get('text','').strip()
                if not result: continue
                now = time.time()
                command = text_after_wake(result)

                if command is not None:
                    # Palabra clave "SKY" detectada -> Abrir ventana conversacional de 25s
                    active_until = now + SESSION_TIMEOUT
                    sync_state({'session_active': True, 'active_until': active_until, 'last_wake': now})
                elif now < active_until:
                    # Sesión conversacional continua activa: no requiere repetir "SKY"
                    command = result.strip(' ,.:;!?¿¡')
                    active_until = now + SESSION_TIMEOUT
                else:
                    sync_state({'session_active': False})
                    continue

                if not command:
                    say('Te escucho. Indicame qué necesitás.')
                    continue

                # Comprobar orden de cierre de sesión de escucha
                clean_cmd = norm(command)
                if any(phrase in clean_cmd for phrase in ('deja de escuchar', 'para de escuchar', 'silencio', 'descansa', 'cerrar sesion', 'apagate')):
                    active_until = 0.0
                    sync_state({'session_active': False, 'status': 'idle'})
                    say('Entendido, detengo la escucha continua. Decí SKY cuando me necesites.')
                    continue

                print('Escuchado:',command)
                sync_state({'last_command': command, 'timestamp': now})
                intent=interpret_command(command)
                if intent:
                    from neural_core.sky_voice_actions import SAFE_ACTIONS
                    if args.execute_safe and intent.get('action') in SAFE_ACTIONS:
                        from neural_core.sky_voice_actions import execute_safe_local
                        try:
                            msg_resp = execute_safe_local(intent)
                            say(msg_resp)
                        except (ValueError, RuntimeError, OSError) as exc:
                            say('No se pudo ejecutar la orden. Revisá que el agente local esté activo y autorizado.')
                            print('Detalle:',str(exc))
                    else:
                        add_inbox(command,intent)
                        say('Preparé la orden. Abrí la sección SKY del panel para confirmarla.')
                    continue
                provider,modelo=choose_provider(os.getenv('SKY_VOICE_PROVIDER','auto'), 'SKY voz')
                try:
                    answer,_=responder(command,'SKY voz local',history,modelo,proveedor=provider)
                    history.extend([{'role':'user','content':command},{'role':'assistant','content':answer}])
                    history=history[-10:]
                    say(answer)
                except Exception as exc:
                    say('No pude completar esta consulta. Revisá la conexión y la configuración de Gemini u Ollama.')
                    print('Detalle:',str(exc))
    except KeyboardInterrupt:
        sync_state({'hands_free_listening': False, 'session_active': False, 'status': 'stopped'})
        print('Micrófono desactivado. SKY-IA finalizado.')

if __name__=='__main__': main()
