"""Deterministic SKY answer-quality contracts; never claims model inference."""
from neural_core.sky_answer_quality import classify_task, system_prompt


def test_real_thesis_prompt_gets_academic_and_file_delivery_guidance():
    thesis = ("Ayúdame a escribir una tesis en Informática Educativa sobre "
              "inteligencia artificial y estado de ánimo emocional. "
              "Diseña metodología, marco teórico y un documento Word.")
    labels = classify_task(thesis)
    assert "academic" in labels
    assert "deliverable" in labels
    system = system_prompt(thesis)
    assert "No inventes DOI" in system
    assert "nunca declares creado" in system
    assert "no navega por Internet" in system


def test_science_workflow_includes_units_steps_and_reproducibility():
    prompt = "Explica paso a paso ecuaciones de Física, Química y Matemáticas"
    labels = classify_task(prompt)
    assert "science" in labels
    assert "procedimientos paso a paso" in system_prompt(prompt)
    assert "consistencia dimensional" in system_prompt(prompt)


def test_programming_requires_real_test_evidence():
    text = system_prompt("Corrige error de Kotlin y sube al GitHub")
    assert "compilaciones o GitHub Actions sin evidencia" in text
    assert "No prometas tareas que no has ejecutado" in text


def test_academic_time_does_not_turn_into_weather_task():
    instructions = ("Tiempo disponible seis meses para mi investigación "
                    "del clima emocional universitario")
    labels = classify_task(instructions)
    assert "academic" in labels
    assert "live" not in labels
    assert "La respuesta del clima" not in system_prompt(instructions)


def test_current_information_requires_a_real_source():
    assert "live" in classify_task("¿Qué noticias hay hoy?")
    assert "no lo declares actualizado" in system_prompt("¿Qué noticias hay hoy?")


def test_plain_chat_stays_simple_without_fake_tools():
    result = system_prompt("Hola SKY, ¿qué tal?")
    assert "no guarda archivos" in result
    assert "No inventes herramientas" in result
    assert "Para trabajos académicos" not in result
