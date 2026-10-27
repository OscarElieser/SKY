"""Manifiesto maestro: sin instalar modelos, paquetes ni usar red."""
from pathlib import Path
import subprocess
import sys

from scripts import sky_dependencias_todas as deps

ROOT = Path(__file__).resolve().parents[1]


def test_incluye_todos_los_requisitos_declarados():
    master = ROOT / "requirements_sky_all.txt"
    content = master.read_text(encoding="utf-8")
    for name in (
        "requirements.txt",
        "requirements_social.txt",
        "requirements_office.txt",
        "requirements_studio.txt",
        "requirements_production.txt",
        "requirements_connectivity_optional.txt",
        "requirements_mcp_optional.txt",
        "requirements_sky_optional_integrations.txt",
        "requirements_markitdown_optional.txt",
        "requirements_sky_training.txt",
    ):
        assert f"-r {name}" in content
    assert "faster-whisper" in content and "vosk" in content
    assert "sounddevice" in content and "pyttsx3" in content
    assert "pywin32" in content and "pytest" in content
    assert "requirements_verified_v110.txt" in content  # baseline pinned deliberately not installed
    resolved = deps.leer_manifest(master)
    assert len(resolved) >= 50
    assert any(line.startswith("markitdown[") for line in resolved)
    assert any(line.startswith("crewai") for line in resolved)
    assert any(line.startswith("peft") for line in resolved)


def test_recursion_deduplicada_e_impide_rutas_externas(tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("-r b.txt\npip>=1\n", encoding="utf-8")
    b.write_text("-r a.txt\npytest>=1\n", encoding="utf-8")
    assert deps.leer_manifest(a) == ["pytest>=1", "pip>=1"]
    a.write_text("-r ../exterior.txt\n", encoding="utf-8")
    try:
        deps.leer_manifest(a)
        assert False, "Se aceptó una ruta fuera de la raíz."
    except ValueError:
        pass


def test_auditar_distribuciones_sin_descargas(tmp_path, monkeypatch):
    manifest = tmp_path / "requirements.txt"
    manifest.write_text('pip>=10\ninventado>=2\npip>=10; python_version < "3.0"\n', encoding="utf-8")
    def fake_version(name):
        if name == "inventado":
            raise deps.metadata.PackageNotFoundError(name)
        return "25.0.1"
    monkeypatch.setattr(deps.metadata, "version", fake_version)
    result = deps.inventario(manifest)
    assert result["faltantes"] == ["inventado>=2"]
    assert result["instalados"] == 1
    assert not result["completo_verificable"]


def test_extras_se_reportan_no_se_inventan(tmp_path, monkeypatch):
    file = tmp_path / "requirements.txt"
    file.write_text("markitdown[pdf,docx]>=0.1\n", encoding="utf-8")
    monkeypatch.setattr(deps.metadata, "version", lambda name: "0.1.9")
    result = deps.inventario(file)
    assert result["extras_sin_verificar"]
    assert not result["completo_verificable"]
    assert deps.main(["--manifest", str(file)]) == 2


def test_cli_python_disponible(tmp_path):
    manifest = tmp_path / "requirements.txt"
    manifest.write_text("pip>=1\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/sky_dependencias_todas.py"),
         "--manifest", str(manifest)],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert '"completo_verificable": true' in result.stdout


def test_instalador_orquesta_sin_eliminar_instalacion():
    script = (ROOT / "INSTALAR_DEPENDENCIAS_SKY.ps1").read_text(encoding="utf-8")
    assert 'requirements_sky_all.txt' in script
    assert 'requirements.txt' in script
    assert 'if (-not (Test-Path -LiteralPath $PythonVenv))' in script
    assert '& $PythonVenv -m pip install --disable-pip-version-check -r $Manifest' in script
    assert '& $PythonVenv -m pip check' in script
    assert 'npm' in script and 'flutter pub get' in script
    assert 'Google.AndroidStudio' in script and 'Tailscale.Tailscale' in script
    assert '$ModeloOllama' in script
    assert 'Remove-Item .venv' not in script
    assert 'git reset --hard' not in script
    assert '$env:SKY_API_KEY' not in script
