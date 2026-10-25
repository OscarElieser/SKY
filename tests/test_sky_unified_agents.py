"""Pruebas del núcleo único SKY + subagentes consultivos sin efectos externos."""
import json

import pytest
from neural_core import sky_unified_agents as team


REQUEST = "Investiga y analiza las opciones de arquitectura, compara alternativas para un sistema educativo."
PLAN = {"agents": [
    {"name": "Arquitectura", "objective": "Analizar arquitectura y riesgos del sistema educativo."},
    {"name": "Docencia", "objective": "Evaluar la utilidad pedagógica y las necesidades de formación."},
]}


@pytest.fixture(autouse=True)
def enabled(monkeypatch):
    monkeypatch.setenv("SKY_UNIFIED_AGENTS_ENABLED", "1")
    monkeypatch.setenv("SKY_METRICAS", "0")


def test_no_usa_agentes_para_saludos_o_comandos_de_pc():
    assert not team.eligible("Hola SKY")
    assert not team.eligible("Abre Word, investiga y analiza cómo programar un formulario.")
    assert not team.eligible("Corrige el archivo, analiza y optimiza el proyecto en GitHub.")
    assert not team.eligible("Genera un PDF, investiga y diseña una guía.")
    assert team.eligible(REQUEST)
    assert team.eligible(REQUEST, mode="voz")


def test_subagentes_y_respuesta_original_de_sky(monkeypatch):
    calls = []
    monkeypatch.setattr(team, "_backend", lambda preferred="auto": ("ollama", "test-model"))
    def fake_ask(provider, model, system, prompt, max_tokens):
        calls.append((provider, model, system, prompt, max_tokens))
        if len(calls) == 1:
            return json.dumps(PLAN, ensure_ascii=False)
        if len(calls) == 2:
            return "Arquitectura: separar dominio, datos y API; riesgo de dependencias."
        if len(calls) == 3:
            return "Docencia: alinear materiales con objetivos y evaluar aprendizaje."
        return "SKY: integraremos arquitectura modular y evaluación continua."
    monkeypatch.setattr(team, "_ask", fake_ask)
    result = team.maybe_answer(REQUEST, [{"role": "user", "content": "Necesito un curso."}])
    assert result["mensaje"] == "SKY: integraremos arquitectura modular y evaluación continua."
    assert result["proveedor"] == "sky-unified"
    assert result["motor_cognitivo"] == "ollama"
    assert len(result["subagentes"]) == 2
    assert result["ejecucion_externa"] is False
    assert len(calls) == 4  # plan + dos especialistas + SKY sintetiza
    assert all(s[0] == "ollama" for s in calls)
    assert '"findings"' in calls[-1][3]


def test_plan_json_con_validacion_estricta():
    assert len(team._agents_from_plan(PLAN)) == 2
    with pytest.raises(ValueError):
        team._agents_from_plan({"agents": []})
    with pytest.raises(ValueError):
        team._agents_from_plan({"agents": PLAN["agents"] * 3})
    with pytest.raises(ValueError):
        team._agents_from_plan({"agents": [PLAN["agents"][0]] * 2})
    with pytest.raises(ValueError):
        team._agents_from_plan({"agents": [
            {"name": "__import__('os').system('foo')", "objective": "Ejecutar cualquier orden del sistema."},
            PLAN["agents"][1],
        ]})


def test_falla_sin_inventar_una_respuesta(monkeypatch):
    monkeypatch.setattr(team, "_backend", lambda preferred="auto": ("ollama", "test-model"))
    monkeypatch.setattr(team, "_ask", lambda *args, **kwargs: "No es un JSON")
    assert team.maybe_answer(REQUEST) is None


def test_falla_por_especialista_sin_simular_resultados(monkeypatch):
    monkeypatch.setattr(team, "_backend", lambda preferred="auto": ("ollama", "test-model"))
    calls = []
    def flaky(*args):
        calls.append(1)
        return json.dumps(PLAN) if len(calls) == 1 else ""
    monkeypatch.setattr(team, "_ask", flaky)
    assert team.maybe_answer(REQUEST) is None


def test_desactivado_retorna_a_sky_original(monkeypatch):
    monkeypatch.setenv("SKY_UNIFIED_AGENTS_ENABLED", "0")
    monkeypatch.setattr(team, "_ask", lambda *a, **k: pytest.fail("No debe llamar al modelo"))
    assert team.maybe_answer(REQUEST) is None


def test_openjarvis_solo_motor_interno_local(monkeypatch):
    from neural_core import providers
    monkeypatch.setenv("SKY_OPENJARVIS_ENABLED", "1")
    monkeypatch.setenv("SKY_OPENJARVIS_MODEL", "localmodel")
    monkeypatch.delenv("SKY_LOCAL_ONLY", raising=False)
    assert team._backend() == ("openjarvis", "localmodel")
    monkeypatch.setenv("SKY_LOCAL_ONLY", "1")
    assert team._backend()[0] == "ollama"
    monkeypatch.delenv("SKY_LOCAL_ONLY")
    assert team._backend("ollama")[0] == "ollama"
    assert team._backend("openjarvis")[0] == "openjarvis"


def test_el_asistente_conserva_su_entrypoint_y_evita_doble_consulta(monkeypatch):
    from neural_core import sky_asistente_personal as assistant
    monkeypatch.setattr(assistant, "preparar", lambda text: text)
    monkeypatch.setattr(assistant, "reglas", lambda text: None)
    monkeypatch.setattr(team, "maybe_answer", lambda *args, **kwargs: {
        "tipo": "respuesta", "mensaje": "Respuesta generada.", "proveedor": "sky-unified"})
    monkeypatch.setattr(assistant, "usar_cerebro", lambda *_: pytest.fail("No debe llamar dos veces al cerebro"))
    result = assistant.atender(REQUEST)
    assert result["mensaje"] == "Respuesta generada."


def test_capacidades_explicitamente_sin_ejecucion_no_autorizada():
    status = team.capability_status()
    assert status["orchestrator"] == "SKY"
    assert status["auto_actions"] is False
    assert status["auto_messages"] is False
    assert status["persistent_workflows"].startswith("sky_subagents")


def test_json_fenced_aceptado_solo_si_es_valido():
    text = "```json\n" + json.dumps(PLAN, ensure_ascii=False) + "\n```"
    assert team._structured(text) == PLAN
    with pytest.raises(ValueError):
        team._structured("Una respuesta, no JSON")


def test_no_cambia_el_proveedor_explicito_de_nube(monkeypatch):
    monkeypatch.setattr(team, "_ask", lambda *args: pytest.fail("No deben ejecutarse agentes en secreto"))
    assert team.maybe_answer(REQUEST, preferred="anthropic") is None


def test_startup_unificado_no_instala_ni_ejecuta_si_esta_desactivado(monkeypatch):
    from neural_core import sky_openjarvis_boot
    monkeypatch.setenv("SKY_OPENJARVIS_ENABLED", "0")
    monkeypatch.setenv("SKY_OPENJARVIS_AUTOSTART", "1")
    assert sky_openjarvis_boot.launch_spec() is None


def test_startup_unificado_exige_instalacion_separada_y_sin_sync(monkeypatch, tmp_path):
    from neural_core import sky_openjarvis_boot
    monkeypatch.setenv("SKY_OPENJARVIS_ENABLED", "1")
    monkeypatch.setenv("SKY_OPENJARVIS_MODEL", "modelo-local")
    monkeypatch.setenv("SKY_OPENJARVIS_AUTOSTART", "1")
    monkeypatch.setenv("SKY_OPENJARVIS_HOME", str(tmp_path))
    monkeypatch.delenv("SKY_LOCAL_ONLY", raising=False)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='openjarvis'\n")
    monkeypatch.setattr(sky_openjarvis_boot.shutil, "which", lambda name: "/usr/bin/uv")
    spec = sky_openjarvis_boot.launch_spec()
    args, _ = spec
    assert "--no-sync" in args and "--agent" in args and "simple" in args
    assert "--host" in args and "127.0.0.1" in args
    assert args[0] == "/usr/bin/uv"
