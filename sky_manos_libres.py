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
    recognizer=KaldiRecognizer(Model(args.model),args.rate)
    print('SKY: micrófono activo; decí “SKY” antes de la pregunta. Ctrl+C para finalizar.')
    print('La voz se reconoce localmente con Vosk; el texto consulta al proveedor SKY que configuraste.')
    history=[]
    def say(message):
        nonlocal speaking
        print('SKY:',message)
        if tts:
            speaking=True
            try:
                tts.say(message[:1000]); tts.runAndWait()
            finally:
                speaking=False
                while not audio.empty():
                    try: audio.get_nowait()
                    except queue.Empty: break
    try:
        with sd.RawInputStream(samplerate=args.rate,blocksize=8000,dtype='int16',channels=1,callback=callback):
            while True:
                buffer=audio.get()
                if not recognizer.AcceptWaveform(buffer): continue
                result=json.loads(recognizer.Result()).get('text','').strip()
                if not result: continue
                command=text_after_wake(result)
                if command is None: continue
                if not command:
                    say('Te escucho. Decí SKY seguido de lo que necesitás.');continue
                print('Escuchado:',command)
                intent=interpret_command(command)
                if intent:
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
        print('Micrófono desactivado. SKY finalizado.')

if __name__=='__main__': main()
