"""SKY v10.6: offline STT in a bounded child process.

This is process separation, NOT an OS security sandbox. Run the worker in a
low-privilege container before allowing untrusted audio on a public server.
The model is never downloaded and audio is never sent to a remote provider.
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from . import sky_stt_local as base
from .sky_languages import normalize

WORKER_TIMEOUT = 100
MAX_RESPONSE_BYTES = 256 * 1024


def capabilities() -> dict:
    status = base.capabilities()
    return {**status, 'process_isolated': True, 'os_sandboxed': False,
            'real_model_validated': False, 'timeout_seconds': WORKER_TIMEOUT}


def isolated_transcribe(audio: bytes, *, filename: str = 'audio.wav',
                        language: str | None = None) -> dict:
    if not base.capabilities()['available']:
        raise RuntimeError('Reconocimiento no disponible: instalá faster-whisper y un modelo local')
    code = normalize(language, strict=True).split('-')[0] if language else None
    # Decode and verify the duration BEFORE starting the model worker.
    pcm = base._pcm_mono_16khz(audio, filename)
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='sky_stt_job_') as directory:
        src = Path(directory) / 'audio.wav'
        src.write_bytes(pcm)
        os.chmod(src, 0o600)
        # Minimal environment: never forward SKY_KEY, OAuth tokens or remote AI keys.
        allowed = ('PATH', 'SYSTEMROOT', 'WINDIR', 'HOME', 'USERPROFILE', 'TMP',
                   'TEMP', 'LD_LIBRARY_PATH', 'VIRTUAL_ENV', 'LANG')
        env = {key: os.environ[key] for key in allowed if key in os.environ}
        env.update({'SKY_STT_MODEL_DIR': str(base.model_directory()),
                    'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
                    'HF_DATASETS_OFFLINE': '1', 'PYTHONPATH': str(root)})
        command = [sys.executable, '-m', 'neural_core.sky_stt_worker_v106',
                   '--file', str(src)]
        if code:
            command.extend(['--language', code])
        try:
            proc = subprocess.run(command, env=env, cwd=root, capture_output=True,
                                  check=False, timeout=WORKER_TIMEOUT)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError('Transcripción cancelada por superar el tiempo límite') from exc
        if proc.returncode:
            # Don't leak worker stderr or local path details into the HTTP response.
            raise RuntimeError('Falló el motor local de reconocimiento de voz')
        if not proc.stdout or len(proc.stdout) > MAX_RESPONSE_BYTES:
            raise RuntimeError('Respuesta de transcripción no válida')
        try:
            result = json.loads(proc.stdout)
        except (ValueError, UnicodeDecodeError) as exc:
            raise RuntimeError('Respuesta de transcripción ilegible') from exc
        if not isinstance(result, dict) or not isinstance(result.get('text'), str):
            raise RuntimeError('Respuesta de transcripción incorrecta')
        result['process_isolated'] = True
        result['offline'] = True
        return result
