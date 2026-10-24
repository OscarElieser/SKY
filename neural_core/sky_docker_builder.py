"""SKY Developer: compile, run and test only in explicitly authorized Docker containers.

Security boundary: no host shell, no user-supplied commands/images, no bind mounts,
no inherited secrets, no network, read-only filesystem, constrained tmpfs and UID.
Docker containers are defense in depth, not a guarantee against hostile code.
The owner must opt in and maintain Docker/rootless security independently.
"""
from __future__ import annotations

import io
import os
import re
import secrets
import shutil
import subprocess
import tarfile
import threading
import time
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Mapping

from .sky_programming_capabilities import resolve_language

# Images are selected by SKY, not by user input. Pre-pull explicitly before use.
# The host resolves each tag to a local image ID; runtime never pulls an image.
@dataclass(frozen=True)
class Profile:
    image: str
    entry: str
    compile: str
    run: str
    test: str | None = None
    suffixes: tuple[str, ...] = ()

PROFILES: dict[str, Profile] = {
    "Python": Profile("python:3.12-alpine", "main.py",
                      "python3 -m py_compile main.py", "python3 main.py",
                      "python3 -m unittest discover -s tests -p 'test_*.py' -v",
                      (".py",)),
    "JavaScript": Profile("node:22-alpine", "main.js",
                          "node --check main.js", "node main.js",
                          "node --test tests/*.test.js", (".js", ".json")),
    "TypeScript": Profile("sky-typescript:5.7.3", "main.ts",
                          "tsc --noEmit --pretty false --target es2022 --module commonjs main.ts",
                          "tsc --pretty false --target es2022 --module commonjs --outDir /work/build main.ts && node /work/build/main.js",
                          None, (".ts", ".json")),
    "C": Profile("gcc:14-bookworm", "main.c",
                 "gcc -std=c11 -Wall -Wextra -o /work/skyapp main.c",
                 "/work/skyapp", None, (".c", ".h")),
    "C++": Profile("gcc:14-bookworm", "main.cpp",
                   "g++ -std=c++17 -Wall -Wextra -o /work/skyapp main.cpp",
                   "/work/skyapp", None, (".cpp", ".hpp", ".h", ".cc")),
    "Go": Profile("golang:1.24-alpine", "main.go",
                  "go build -o /work/skyapp main.go", "/work/skyapp", None, (".go",)),
    "Rust": Profile("rust:1.85-slim", "main.rs",
                    "rustc --edition=2021 main.rs -o /work/skyapp",
                    "/work/skyapp", None, (".rs",)),
    "Java": Profile("eclipse-temurin:21-jdk", "Main.java",
                    "javac -d /work Main.java", "java -cp /work Main",
                    None, (".java",)),
    "PHP": Profile("php:8.3-cli-alpine", "main.php", "php -l main.php", "php main.php",
                   None, (".php",)),
    "Ruby": Profile("ruby:3.3-alpine", "main.rb", "ruby -c main.rb", "ruby main.rb",
                    None, (".rb",)),
    "Bash": Profile("bash:5.2", "main.sh", "bash -n main.sh", "bash main.sh",
                    None, (".sh",)),
}

_MAX_FILE_COUNT = 16
_MAX_SOURCE_BYTES = 96_000
_MAX_OUTPUT_BYTES = 12_000
_ACTIVE = threading.BoundedSemaphore(value=2)
_IMAGE_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
_SAFE_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,89}$")


class RunnerInvalid(ValueError):
    pass


class RunnerUnavailable(RuntimeError):
    pass


def _allowed() -> bool:
    return os.getenv("SKY_CODE_RUNNER_ENABLED") == "1" and os.getenv(
        "SKY_CODE_RUNNER_CONTAINER_ACK") == "1"


def _local_docker_environment() -> dict[str, str]:
    """Environment is strictly non-secret; disallow Docker remote sockets."""
    host = os.getenv("DOCKER_HOST", "")
    if host and not host.startswith(("unix://", "npipe://")):
        raise RunnerUnavailable("El ejecutor no acepta Docker remoto ni conexiones TCP.")
    if os.getenv("DOCKER_CONTEXT", "").strip():
        raise RunnerUnavailable("Desactivá DOCKER_CONTEXT; SKY no acepta contextos Docker remotos.")
    # Keep Windows binary discovery functional, never forward cloud/API tokens.
    result: dict[str, str] = {"PATH": os.environ.get("PATH", "")}
    if os.name == "nt":
        for key in ("SystemRoot", "WINDIR", "PATHEXT"):
            if os.environ.get(key):
                result[key] = os.environ[key]
    if host:
        result["DOCKER_HOST"] = host
    return result


def _docker_path() -> str:
    path = shutil.which("docker")
    if not path:
        raise RunnerUnavailable("Docker CLI no está instalado o no está en PATH.")
    return path


def _local_image_id(docker: str, image: str, env: dict[str, str]) -> str:
    try:
        completed = subprocess.run(
            [docker, "image", "inspect", "--format", "{{.Id}}", image],
            capture_output=True, timeout=5, env=env, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RunnerUnavailable("No se pudo consultar Docker local.") from exc
    image_id = completed.stdout.decode("ascii", errors="replace").strip()
    if completed.returncode or not _IMAGE_ID.fullmatch(image_id):
        raise RunnerUnavailable(
            f"Imagen de compilación no instalada localmente: {image}. "
            "El propietario debe descargarla o construirla explícitamente."
        )
    return image_id


def _source_archive(language: str, files: Mapping[str, str]) -> tuple[bytes, bool]:
    profile = PROFILES[language]
    if not isinstance(files, dict) or not 1 <= len(files) <= _MAX_FILE_COUNT:
        raise RunnerInvalid("Indicá de 1 a 16 archivos de código.")
    if profile.entry not in files:
        raise RunnerInvalid(f"Falta el archivo principal obligatorio: {profile.entry}")
    total = 0
    validated: dict[str, bytes] = {}
    for name, value in files.items():
        if not isinstance(name, str) or len(name) > 160 or not isinstance(value, str):
            raise RunnerInvalid("Ruta o contenido de archivo no válido.")
        if "\\" in name or ":" in name or "//" in name or "\x00" in name:
            raise RunnerInvalid("Las rutas deben ser relativas, POSIX y sin caracteres especiales.")
        parts = PurePosixPath(name).parts
        if not 1 <= len(parts) <= 3 or any(not _SAFE_NAME.fullmatch(p) for p in parts):
            raise RunnerInvalid("Ruta de archivo no permitida.")
        if parts[0] not in ("tests",) and len(parts) != 1:
            raise RunnerInvalid("Se permiten archivos raíz y la carpeta tests/ solamente.")
        if len(parts) > 1 and parts[0] != "tests":
            raise RunnerInvalid("Directorio no permitido.")
        if parts[0] == "tests" and len(parts) != 2:
            raise RunnerInvalid("Las pruebas deben estar en tests/archivo.")
        if not name.endswith(profile.suffixes):
            raise RunnerInvalid(f"Extensión no admitida para {language}: {name}")
        if parts[0] == "tests":
            if language == "Python" and not re.fullmatch(r"test_[a-zA-Z0-9_-]+\.py", parts[1]):
                raise RunnerInvalid("Las pruebas Python deben llamarse tests/test_*.py.")
            if language == "JavaScript" and not re.fullmatch(r"[a-zA-Z0-9_-]+\.test\.js", parts[1]):
                raise RunnerInvalid("Las pruebas JavaScript deben llamarse tests/*.test.js.")
        try:
            raw = value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise RunnerInvalid("Los archivos deben ser texto UTF-8.") from exc
        if b"\x00" in raw or len(raw) > 60_000:
            raise RunnerInvalid("Archivo inválido o demasiado grande.")
        total += len(raw)
        validated[name] = raw
    if total > _MAX_SOURCE_BYTES:
        raise RunnerInvalid("El proyecto supera 96 KB de código.")
    needs_test = any(name.startswith("tests/") for name in validated)
    if needs_test and not profile.test:
        raise RunnerInvalid("Este lenguaje aún no dispone de perfil de pruebas separadas.")
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        if needs_test:
            folder = tarfile.TarInfo("tests")
            folder.type = tarfile.DIRTYPE
            folder.mode = 0o700
            tar.addfile(folder)
        for name, raw in validated.items():
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime = len(raw), 0o600, 0
            tar.addfile(info, io.BytesIO(raw))
    return archive.getvalue(), needs_test


def _docker_args(docker: str, image_id: str, name: str, command: str) -> list[str]:
    # All CLI arguments and scripts come from static profiles; never compose user code.
    return [
        docker, "run", "--rm", "--name", name, "-i", "--pull", "never",
        "--network", "none", "--ipc", "none", "--read-only",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--pids-limit", "64", "--memory", "768m", "--cpus", "1",
        "--user", "65534:65534", "--workdir", "/work",
        "--tmpfs", "/work:rw,nosuid,nodev,size=128m,mode=1777",
        "--tmpfs", "/tmp:rw,nosuid,nodev,size=32m,mode=1777",
        "--env", "HOME=/work", "--env", "TMPDIR=/work",
        "--env", "GOCACHE=/work/.go-cache", "--env", "GOTOOLCHAIN=local",
        "--env", "GOPROXY=off", "--env", "GOSUMDB=off",
        "--env", "DOTNET_CLI_TELEMETRY_OPTOUT=1",
        "--entrypoint", "sh", image_id, "-eu", "-c",
        "umask 077; tar -xf - -C /work; " + command,
    ]


def _execute(docker: str, image_id: str, archive: bytes, command: str,
             env: dict[str, str], timeout: int) -> dict[str, Any]:
    name = "sky-dev-" + secrets.token_hex(8)
    started = time.monotonic()
    try:
        # Consume stdout/stderr incrementally. communicate(capture_output=True)
        # can exhaust host RAM when untrusted code prints unbounded output.
        proc = subprocess.Popen(
            _docker_args(docker, image_id, name, command),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=env,
        )
        captured = {"stdout": bytearray(), "stderr": bytearray()}
        lengths = {"stdout": 0, "stderr": 0}

        def drain(which: str, pipe) -> None:
            while True:
                chunk = pipe.read(8192)
                if not chunk:
                    break
                lengths[which] += len(chunk)
                remaining = _MAX_OUTPUT_BYTES - len(captured[which])
                if remaining > 0:
                    captured[which].extend(chunk[:remaining])

        def feed() -> None:
            try:
                if proc.stdin:
                    proc.stdin.write(archive)
                    proc.stdin.flush()
            except (BrokenPipeError, OSError, ValueError):
                pass
            finally:
                if proc.stdin:
                    try:
                        proc.stdin.close()
                    except OSError:
                        pass

        reader_out = threading.Thread(target=drain, args=("stdout", proc.stdout), daemon=True)
        reader_err = threading.Thread(target=drain, args=("stderr", proc.stderr), daemon=True)
        writer = threading.Thread(target=feed, daemon=True)
        reader_out.start()
        reader_err.start()
        writer.start()
        expired = False
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            expired = True
            proc.kill()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
        for thread in (writer, reader_out, reader_err):
            thread.join(timeout=2)
        return {
            "verified": (not expired and proc.returncode == 0),
            "exit_code": None if expired else proc.returncode,
            "stdout": captured["stdout"].decode("utf-8", "replace"),
            "stderr": captured["stderr"].decode("utf-8", "replace"),
            "duration_ms": round((time.monotonic() - started) * 1000),
            "timed_out": expired,
            "output_truncated": any(lengths[k] > _MAX_OUTPUT_BYTES
                                    for k in ("stdout", "stderr")),
        }
    except OSError as exc:
        raise RunnerUnavailable("No se pudo iniciar Docker CLI.") from exc
    finally:
        # Killed docker CLI need not kill the daemon-side container; remove by
        # unpredictable SKY-owned name. This never touches any other container.
        try:
            subprocess.run([docker, "rm", "-f", name], capture_output=True,
                           timeout=4, env=env, check=False)
        except (OSError, subprocess.TimeoutExpired):
            pass


def catalogue() -> dict[str, Any]:
    return {
        "ok": True, "enabled": _allowed(),
        "supported": [{"language": key, "image": value.image, "main_file": value.entry,
                       "separate_test_profile": value.test is not None}
                      for key, value in PROFILES.items()],
        "mode": "opt_in_local_docker_offline_container",
        "automatic_image_download": False,
        "all_53_languages_compilable": False,
        "host_files_exposed": False,
        "full_untrusted_code_isolation_guaranteed": False,
    }


def build(language: str, files: dict[str, str], *, approved: bool = False,
          expected_stdout: str | None = None, timeout_seconds: int = 15) -> dict[str, Any]:
    """Execute code on configured Docker host only; no direct host execution."""
    if not _allowed():
        raise RunnerUnavailable(
            "SKY Developer Runner desactivado: habilitalo y aceptá explícitamente el riesgo de contenedores."
        )
    canonical = resolve_language(language)
    if canonical not in PROFILES:
        raise RunnerInvalid("Este lenguaje no tiene todavía un ejecutor Docker verificado.")
    if approved is not True:
        raise PermissionError("Se requiere autorización explícita del propietario para compilar o ejecutar.")
    if type(timeout_seconds) is not int or not 3 <= timeout_seconds <= 25:
        raise RunnerInvalid("El tiempo límite debe estar entre 3 y 25 segundos.")
    if expected_stdout is not None and (
        not isinstance(expected_stdout, str) or len(expected_stdout) > 2000
    ):
        raise RunnerInvalid("Salida esperada demasiado grande.")
    archive, has_tests = _source_archive(canonical, files)
    if not _ACTIVE.acquire(blocking=False):
        raise RunnerUnavailable("Ya hay dos trabajos ejecutándose; volvé a intentarlo.")
    try:
        profile = PROFILES[canonical]
        env = _local_docker_environment()
        docker = _docker_path()
        image_id = _local_image_id(docker, profile.image, env)
        # Compilation and execution are separately observed. A failing run does
        # not retroactively turn a successful compile into a fictitious failure.
        compile_step = _execute(docker, image_id, archive, profile.compile, env,
                                timeout_seconds)
        if not compile_step["verified"]:
            return {
                "ok": False, "language": canonical, "image_id": image_id,
                "compile": compile_step, "run": None, "tests": None,
                "status": "compile_failed", "code_executed": True,
                "offline": True, "host_execution": False,
            }
        run_command = profile.compile + "; " + profile.run if profile.run.startswith(
            "/work/"
        ) or profile.run.startswith("java ") or canonical == "TypeScript" else profile.run
        run_step = _execute(docker, image_id, archive, run_command, env,
                            timeout_seconds)
        if expected_stdout is not None:
            run_step["expected_stdout_matched"] = run_step["stdout"].strip() == expected_stdout.strip()
        tests = None
        if has_tests and profile.test:
            tests = _execute(docker, image_id, archive, profile.test, env, timeout_seconds)
        success = (run_step["verified"] and
                   (expected_stdout is None or run_step["expected_stdout_matched"]) and
                   (tests is None or tests["verified"]))
        return {
            "ok": success, "language": canonical, "image_id": image_id,
            "compile": compile_step, "run": run_step, "tests": tests,
            "status": "verified" if success else "run_or_tests_failed",
            "code_executed": True, "offline": True, "host_execution": False,
            "execution_verified_by_cli": True, "human_end_to_end_certified": False,
        }
    finally:
        _ACTIVE.release()
