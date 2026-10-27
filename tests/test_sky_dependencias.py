"""El chequeo de dependencias no descarga paquetes ni cambia la instalación."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from scripts import sky_dependencias as checker


def test_requisitos_satisfechos(monkeypatch):
    monkeypatch.setattr(checker.metadata, "version", lambda name: {
        "numpy": "2.1.1", "pip": "25.0.1"
    }[name])
    result = checker.revisar(["numpy>=1.26,<3", "pip>=25"])
    assert result["completo"]
    assert result["comprobados"] == 2
    assert not result["faltantes"] and not result["incompatibles"]


def test_faltantes_y_versiones_invalidas(monkeypatch):
    def find_version(name):
        if name == "falta":
            raise checker.metadata.PackageNotFoundError(name)
        return "1.0.0"
    monkeypatch.setattr(checker.metadata, "version", find_version)
    result = checker.revisar(["falta>=2", "numpy>=2", "numpy>=0.5"])
    assert not result["completo"]
    assert result["faltantes"] == ["falta>=2"]
    assert result["incompatibles"] == [{"requisito": "numpy>=2", "instalado": "1.0.0"}]


def test_ignorar_comentarios_marcadores_e_invalidos(monkeypatch):
    monkeypatch.setattr(checker.metadata, "version", lambda name: "1.0")
    result = checker.revisar([
        "# version actual", "", "pip>=1 # comentario local",
        'numpy>=2; python_version < "3.0"',
    ])
    assert result["completo"]
    assert result["comprobados"] == 1
    assert result["omitidos"] == ["numpy"]
    unsupported = checker.revisar(["-r extra.txt", "numpy[vision]>=1"])
    assert not unsupported["completo"] and len(unsupported["errores"]) == 2


def test_cli_solo_lectura(monkeypatch, tmp_path, capsys):
    source = tmp_path / "requirements.txt"
    source.write_text("pip>=1\n", encoding="utf-8")
    assert checker.main(["--requirements", str(source), "--json"]) == 0
    assert '"completo": true' in capsys.readouterr().out


def test_instalador_respeta_entorno_y_modo_sin_voz():
    script = (Path(__file__).resolve().parents[1] / "instalar_sky.ps1").read_text(encoding="utf-8")
    assert "if (Test-Path $venvPy)" in script
    assert "if ($SoloVerificarDependencias)" in script
    assert "if (-not $SinVoz)" in script
    assert "$auditor --requirements" in script
    assert "if ($estadoRequisitos -eq 1)" in script
    assert "-m pip install --upgrade pip --quiet" not in script
    assert "Remove-Item .venv" not in script
    assert "Remove-Item .env" not in script
    assert "if ($SoloDependencias)" in script


def test_verificador_funciona_con_python_del_runner():
    result = subprocess.run(
        [sys.executable, "scripts/sky_dependencias.py", "--paquetes", "pip", "--json"],
        cwd=Path(__file__).resolve().parents[1],
        text=True, capture_output=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert '"completo": true' in result.stdout
