"""SKY Developer Docker build: authorization, source validation and strict container controls."""
from __future__ import annotations

import io
import os
import tarfile

import pytest
from fastapi.testclient import TestClient

from neural_core import sky_docker_builder as runner


def test_supported_compilers_are_explicitly_allowlisted():
    catalogue = runner.catalogue()
    languages = {x["language"] for x in catalogue["supported"]}
    assert {"Python", "JavaScript", "TypeScript", "C", "C++",
            "Rust", "Go", "Java", "PHP", "Ruby", "Bash"}.issubset(languages)
    assert catalogue["all_53_languages_compilable"] is False
    assert catalogue["automatic_image_download"] is False
    assert catalogue["full_untrusted_code_isolation_guaranteed"] is False


def test_no_execution_by_default(monkeypatch):
    monkeypatch.delenv("SKY_CODE_RUNNER_ENABLED", raising=False)
    monkeypatch.delenv("SKY_CODE_RUNNER_CONTAINER_ACK", raising=False)
    with pytest.raises(runner.RunnerUnavailable):
        runner.build("Python", {"main.py": "print(1)"}, approved=True)


def test_explicit_consent_is_required(monkeypatch):
    monkeypatch.setenv("SKY_CODE_RUNNER_ENABLED", "1")
    monkeypatch.setenv("SKY_CODE_RUNNER_CONTAINER_ACK", "1")
    with pytest.raises(PermissionError):
        runner.build("Python", {"main.py": "print(1)"}, approved=False)


@pytest.mark.parametrize("files", [
    {"main.py": "print(1)", "../secret.py": "print(1)"},
    {"main.py": "print(1)", "C:\\temp\\file.py": "print(1)"},
    {"main.py": "print(1)", "/home/user/file.py": "print(1)"},
    {"main.py": "print(1)", "tests/../evil.py": "print(1)"},
    {"main.py": "print(1)", "Dockerfile": "FROM busybox"},
    {"main.py": "print(1)", "tests/arbitrary.py": "print(1)"},
    {"main.py": "print(1)", "main.txt": "print(1)"},
    {"other.py": "print(1)"},
])
def test_disallowed_files_rejected(files):
    with pytest.raises(runner.RunnerInvalid):
        runner._source_archive("Python", files)


def test_archive_has_only_regular_files_and_owner_created_directory():
    archive, test_requested = runner._source_archive("Python", {
        "main.py": "def sum2(a,b): return a+b\n",
        "tests/test_main.py": "import unittest\n",
    })
    assert test_requested is True
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tar:
        names = tar.getnames()
        assert set(names) == {"tests", "main.py", "tests/test_main.py"}
        assert tar.getmember("tests").isdir()
        for name in ("main.py", "tests/test_main.py"):
            assert tar.getmember(name).isfile()
            assert tar.getmember(name).mode == 0o600
            assert not tar.getmember(name).issym()


def test_local_only_docker_environment(monkeypatch):
    monkeypatch.setenv("DOCKER_HOST", "tcp://untrusted.example:2376")
    with pytest.raises(runner.RunnerUnavailable):
        runner._local_docker_environment()
    monkeypatch.delenv("DOCKER_HOST", raising=False)
    monkeypatch.setenv("DOCKER_CONTEXT", "production")
    with pytest.raises(runner.RunnerUnavailable):
        runner._local_docker_environment()
    monkeypatch.delenv("DOCKER_CONTEXT", raising=False)
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "do-not-forward-this")
    data = runner._local_docker_environment()
    assert "AWS_SECRET_ACCESS_KEY" not in data


def test_static_docker_command_disables_network_and_sensitive_host_access():
    args = runner._docker_args("docker", "sha256:" + "a"*64, "sky-dev-safe", "python3 main.py")
    assert "--network" in args and args[args.index("--network") + 1] == "none"
    assert "--read-only" in args
    assert "--cap-drop" in args and "ALL" in args
    assert "--user" in args and "65534:65534" in args
    assert "--pull" in args and "never" in args
    assert "--pids-limit" in args
    assert "--memory" in args and "--cpus" in args
    assert "-v" not in args and "--mount" not in args
    assert "python3 main.py" == args[-1].split("; ")[-1]
    assert "AWS_SECRET_ACCESS_KEY" not in " ".join(args)


def test_compile_fail_is_not_reported_as_success(monkeypatch):
    monkeypatch.setenv("SKY_CODE_RUNNER_ENABLED", "1")
    monkeypatch.setenv("SKY_CODE_RUNNER_CONTAINER_ACK", "1")
    monkeypatch.setattr(runner, "_docker_path", lambda: "docker")
    monkeypatch.setattr(runner, "_local_image_id", lambda *a: "sha256:" + "b"*64)
    monkeypatch.setattr(runner, "_execute", lambda *a: {
        "verified": False, "exit_code": 1, "stdout": "", "stderr": "SyntaxError",
        "timed_out": False,
    })
    r = runner.build("Python", {"main.py": "invalid!"}, approved=True)
    assert r["ok"] is False
    assert r["status"] == "compile_failed"
    assert r["run"] is None


def test_wrong_expected_output_is_not_verified(monkeypatch):
    monkeypatch.setenv("SKY_CODE_RUNNER_ENABLED", "1")
    monkeypatch.setenv("SKY_CODE_RUNNER_CONTAINER_ACK", "1")
    monkeypatch.setattr(runner, "_docker_path", lambda: "docker")
    monkeypatch.setattr(runner, "_local_image_id", lambda *a: "sha256:" + "b"*64)
    monkeypatch.setattr(runner, "_execute", lambda *a: {
        "verified": True, "exit_code": 0, "stdout": "7\n",
        "stderr": "", "timed_out": False,
    })
    r = runner.build("Python", {"main.py": "print(7)"}, approved=True,
                     expected_stdout="42")
    assert r["ok"] is False
    assert r["run"]["expected_stdout_matched"] is False


def test_api_requires_pin_and_opt_in_not_only_login(monkeypatch):
    from metaverse.api import app, api_token
    from neural_core import sentinel_identidad as identity
    monkeypatch.setenv("SKY_API_KEY", "sky-code-runner-test-private-key-2026")
    monkeypatch.setattr(identity, "pin_configurado", lambda: False)
    with TestClient(app) as client:
        no_auth = client.get("/api/developer/build/capabilities")
        assert no_auth.status_code in (401, 403)
        headers = {"X-SKY-KEY": api_token()}
        ok = client.get("/api/developer/build/capabilities", headers=headers)
        assert ok.status_code == 200
        assert ok.json()["mode"] == "opt_in_local_docker_offline_container"
        execute = client.post("/api/developer/build/execute", headers=headers, json={
            "language": "Python", "files": {"main.py": "print('ok')"}, "approved": True,
        })
        assert execute.status_code == 403
        assert "PIN" in execute.text
