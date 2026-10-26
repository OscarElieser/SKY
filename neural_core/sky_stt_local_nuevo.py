"""Private, offline voice recognition with a USER-INSTALLED faster-whisper model.

No download, no network calls, no implicit fallback to external providers.
The model must already exist in SKY_STT_MODEL_DIR. Availability is truthful.
"""
from __future__ import annotations
import io
import math
import os
import shutil
import subprocess
import tempfile
import threading
import wave
from pathlib import Path
from .sky_languages import normalize

MAX_INPUT_BYTES = 10 * 1024 * 1024
MAX_SECONDS = 60
_LOCK = threading.Lock()


def model_directory() -> Path | None:
    raw = os.environ.get('SKY_STT_MODEL_DIR', '').strip()
    if not raw:
        return None
    candidate = Path(raw).expanduser()
    if candidate.is_symlink() or not candidate.is_dir():
        return None
    return candidate.resolve()


def capabilities() -> dict:
    try:
        import faster_whisper  # noqa: F401
        installed = True
    except ImportError:
        installed = False
    directory = model_directory()
    valid = bool(directory and (directory / 'model.bin').is_file() and (directory / 'config.json').is_file())
    return {'available': installed and valid, 'engine': 'faster-whisper',
            'installed': installed, 'model_present': valid,
            'model_path_is_local': bool(directory), 'network_access': False,
            'max_audio_seconds': MAX_SECONDS, 'max_upload_bytes': MAX_INPUT_BYTES,
            'real_transcription_tested': False}


def _pcm_mono_16khz(audio: bytes, filename: str = 'audio.wav') -> bytes:
    if not isinstance(audio, bytes) or not audio or len(audio) > MAX_INPUT_BYTES:
        raise ValueError('Audio vacío o demasiado grande')
    # Users may submit WAV or compressed audio; ffmpeg is an isolated executable.
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        raise RuntimeError('FFmpeg es necesario para normalizar el audio')
    suffix = Path(filename).suffix.lower()
    if suffix not in {'.wav', '.mp3', '.ogg', '.flac', '.m4a', '.webm', '.mp4'}:
        raise ValueError('Formato de audio no admitido')
    with tempfile.TemporaryDirectory(prefix='sky_local_stt_') as temporary:
        inp = Path(temporary) / ('source' + suffix)
        out = Path(temporary) / 'converted.wav'
        inp.write_bytes(audio)
        ffprobe = shutil.which('ffprobe')
        if not ffprobe:
            raise RuntimeError('FFprobe es necesario para comprobar la duración')
        duration = subprocess.run([ffprobe, '-v', 'error', '-show_entries', 'format=duration',
                                   '-of', 'default=noprint_wrappers=1:nokey=1', str(inp)],
                                  capture_output=True, text=True, timeout=15, check=False)
        # Browser MediaRecorder WebM/Opus blobs may omit container duration.
        # A missing metadata duration is not proof that the audio is invalid.
        # Always verify decoded PCM length; never accept an unverified input.
        reported_seconds = None
        if duration.returncode == 0:
            try:
                candidate = float(duration.stdout.strip())
                if math.isfinite(candidate) and candidate > 0:
                    reported_seconds = candidate
            except ValueError:
                pass
        if reported_seconds is not None and reported_seconds > MAX_SECONDS:
            raise ValueError('Audio excede el máximo de 60 segundos o está vacío')
        args = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
                '-i', str(inp), '-t', str(MAX_SECONDS + 1), '-vn', '-ac', '1', '-ar', '16000',
                '-acodec', 'pcm_s16le', str(out)]
        try:
            proc = subprocess.run(args, capture_output=True, timeout=25, check=False)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError('Se agotó el tiempo para preparar el audio') from exc
        if proc.returncode or not out.exists() or out.stat().st_size > (MAX_SECONDS + 1) * 32000 + 10000:
            raise ValueError('El audio no pudo decodificarse')
        with wave.open(str(out), 'rb') as wav:
            seconds = wav.getnframes() / wav.getframerate()
            if not 0 < seconds <= MAX_SECONDS:
                raise ValueError('Duración de audio no permitida')
        return out.read_bytes()


def transcribe(audio: bytes, *, filename: str = 'audio.wav', language: str | None = None) -> dict:
    status = capabilities()
    if not status['available']:
        raise RuntimeError('Instalá faster-whisper y un modelo local autorizado antes de transcribir')
    # Language is optional: model attempts detection; no fake inferred transcript.
    locale = normalize(language, strict=True).split('-')[0] if language else None
    if not _LOCK.acquire(blocking=False):
        raise RuntimeError('El reconocedor local está ocupado; probá de nuevo')
    try:
        pcm = _pcm_mono_16khz(audio, filename)
        from faster_whisper import WhisperModel
        from numpy import frombuffer, float32, int16
        with wave.open(io.BytesIO(pcm), 'rb') as wav:
            samples = wav.readframes(wav.getnframes())
        signal = frombuffer(samples, dtype=int16).astype(float32) / 32768.0
        # `local_files_only` prevents implicit download even if path is invalid.
        model = WhisperModel(str(model_directory()), device='cpu', compute_type='int8',
                             local_files_only=True, cpu_threads=2, num_workers=1)
        segments, info = model.transcribe(signal, language=locale, beam_size=2,
                                          vad_filter=True, condition_on_previous_text=False)
        rows = [{'start': round(s.start, 3), 'end': round(s.end, 3), 'text': s.text.strip()}
                for s in segments if s.text.strip()]
        return {'text': ' '.join(s['text'] for s in rows), 'segments': rows,
                'detected_language': info.language, 'engine': 'faster-whisper',
                'offline': True, 'model_directory_local': True,
                'audio_seconds': round(len(signal) / 16000, 3)}
    finally:
        _LOCK.release()
