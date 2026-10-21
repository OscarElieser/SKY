"""Las notas sólo se editan dentro del espacio privado y con permiso explícito."""
import pytest
from neural_core import sky_notes_local as notes
from neural_core.dispositivos import interpret_command


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    root = tmp_path / "notes"
    root.mkdir()
    monkeypatch.setattr(notes, "notes_root", lambda: root)
    monkeypatch.setenv("SKY_NOTES_ENABLED", "1")
    return root


def test_notas_crear_agregar_y_papelera(sandbox):
    with pytest.raises(PermissionError, match="Confirmación"):
        notes.run_note_action("note_create", {"name": "reunion", "content": "Agenda"})
    assert notes.run_note_action("note_create", {"name": "reunion", "content": "Agenda", "confirmed": True})["ok"]
    assert (sandbox / "reunion.txt").read_text(encoding="utf-8") == "Agenda\n"
    with pytest.raises(ValueError, match="ya existe"):
        notes.run_note_action("note_create", {"name": "reunion", "content": "Otra", "confirmed": True})
    notes.run_note_action("note_append", {"name": "reunion", "content": "Acuerdos", "confirmed": True})
    assert (sandbox / "reunion.txt").read_text(encoding="utf-8") == "Agenda\nAcuerdos\n"
    notes.run_note_action("note_trash", {"name": "reunion", "confirmed": True})
    assert not (sandbox / "reunion.txt").exists()
    assert len(list((sandbox / ".trash").glob("reunion-*.txt"))) == 1


@pytest.mark.parametrize("name", ["../otros", "/etc/passwd", "hola.txt", "x" * 65, "a\\b"])
def test_notas_rechazan_traversal(sandbox, name):
    with pytest.raises(ValueError):
        notes.run_note_action("note_create", {"name": name, "content": "algo", "confirmed": True})


def test_notas_rechazan_symlinks(sandbox, tmp_path):
    external = tmp_path / "outside.txt"
    external.write_text("privado")
    try:
        (sandbox / "escape.txt").symlink_to(external)
    except (OSError, NotImplementedError):
        pytest.skip("Sistema sin soporte para symlinks.")
    with pytest.raises(ValueError):
        notes.run_note_action("note_append", {"name": "escape", "content": "x", "confirmed": True})
    assert external.read_text() == "privado"


def test_notas_apagadas_por_defecto(sandbox, monkeypatch):
    monkeypatch.delenv("SKY_NOTES_ENABLED")
    with pytest.raises(PermissionError):
        notes.run_note_action("note_create", {"name": "prueba", "content": "x", "confirmed": True})


@pytest.mark.parametrize("phrase, action, name", [
    ("sky, crea una nota agenda que diga reunión lunes", "note_create", "agenda"),
    ("agrega a la nota agenda el texto nuevo acuerdo", "note_append", "agenda"),
    ("elimina la nota agenda", "note_trash", "agenda"),
])
def test_interpreta_notas_que_exigen_confirmacion(phrase, action, name):
    order = interpret_command(phrase)
    assert order["action"] == action
    assert order["params"]["name"] == name
    assert "confirmed" not in order["params"]
