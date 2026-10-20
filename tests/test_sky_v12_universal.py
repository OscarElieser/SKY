"""Tests para SKY IA Universal v12.0:
Universal Intelligence Engine, FactCheck Engine, Smart Memory y Benchmark.
"""
import pytest
from fastapi.testclient import TestClient
from neural_core.sky_universal_engine import SkyUniversalEngine, OperationMode, AcademicLevel, GLOBAL_SOURCES_REGISTRY
from neural_core.factcheck_engine import SkyFactCheckEngine, VerificationStatus
from neural_core.smart_memory import SmartMemoryManager
from neural_core.eval_benchmark import ejecutar_evaluacion_benchmark
from metaverse.api import app

client = TestClient(app)


# ==============================================================================
# 1. PRUEBAS UNIVERSAL INTELLIGENCE ENGINE
# ==============================================================================
def test_universal_engine_clasificacion_modos():
    plan_dev = SkyUniversalEngine.clasificar_intencion("Escribe un script en python con fastapi y tests", "Programación")
    assert plan_dev.modo == OperationMode.DEV
    assert plan_dev.requiere_codigo is True

    plan_res = SkyUniversalEngine.clasificar_intencion("Investiga las estadísticas del censo de población", "Estadística")
    assert plan_res.modo == OperationMode.RESEARCH
    assert plan_res.requiere_investigacion is True

    plan_deep = SkyUniversalEngine.clasificar_intencion("Explica a fondo la teoría de la relatividad general para doctorado", "Física")
    assert plan_deep.modo == OperationMode.DEEP
    assert plan_deep.nivel_academico == AcademicLevel.DOCTORADO


def test_universal_engine_enrutamiento_fuentes_globales():
    # Salud
    plan_salud = SkyUniversalEngine.clasificar_intencion("¿Cuáles son los síntomas de la malaria?", "Salud")
    assert plan_salud.disciplina == "salud"
    entidades_salud = [f.entidad for f in plan_salud.fuentes_recomendadas]
    assert any("OMS" in e for e in entidades_salud)

    # Economía
    plan_econ = SkyUniversalEngine.clasificar_intencion("Tasa de inflación y perspectivas del PIB", "Economía")
    assert plan_econ.disciplina == "economia"
    entidades_econ = [f.entidad for f in plan_econ.fuentes_recomendadas]
    assert any("Banco Mundial" in e or "FMI" in e for e in entidades_econ)

    # Demografía
    plan_demo = SkyUniversalEngine.clasificar_intencion("Censo poblacional de Nicaragua", "Demografía")
    assert plan_demo.disciplina == "estadistica"
    entidades_demo = [f.entidad for f in plan_demo.fuentes_recomendadas]
    assert any("INIDE" in e for e in entidades_demo)


def test_universal_engine_directivas_formato():
    plan = SkyUniversalEngine.clasificar_intencion("¿Cuáles son las vacunas aprobadas?", "Salud")
    directivas = SkyUniversalEngine.directivas_universales(plan)
    assert "SKY UNIVERSAL INTELLIGENCE ENGINE" in directivas
    assert "APA (7ª EDICIÓN)" in directivas
    assert "ADVERTENCIA MÉDICA INFORMATIVA" in directivas


# ==============================================================================
# 2. PRUEBAS FACTCHECK ENGINE
# ==============================================================================
def test_factcheck_calculo_correcto():
    texto = "En esta operación matemática se verifica que 12 + 15 = 27 según las reglas elementales."
    report = SkyFactCheckEngine.auditar_respuesta(texto)
    assert report.total_afirmaciones >= 1
    assert report.contradictorias == 0
    assert report.es_consistente is True
    assert len(report.calculos_verificados) >= 1
    assert report.calculos_verificados[0]["valido"] is True


def test_factcheck_calculo_erroneo_detectado():
    texto = "Es sabido que 10 * 5 = 60 en cualquier cálculo."
    report = SkyFactCheckEngine.auditar_respuesta(texto)
    assert report.contradictorias >= 1
    assert report.es_consistente is False
    assert "ALERTA CRÍTICA" in (report.advertencia_incertidumbre or "")


def test_factcheck_afirmacion_no_comprobada():
    texto = "El 87.5% de las personas prefieren este producto desconocido."
    report = SkyFactCheckEngine.auditar_respuesta(texto)
    assert report.no_comprobadas >= 1
    assert report.advertencia_incertidumbre is not None


# ==============================================================================
# 3. PRUEBAS SMART MEMORY
# ==============================================================================
def test_smart_memory_crud_and_privacy(tmp_path):
    storage_file = tmp_path / "test_memory.json"
    mem_mgr = SmartMemoryManager(storage_path=storage_file)

    # Guardar
    entry1 = mem_mgr.guardar_memoria("proyecto", "nombre_app", "SKY IA v12", usuario_id="u1", es_privado=True)
    entry2 = mem_mgr.guardar_memoria("preferencia", "nivel_academico", "universitario", usuario_id="u1", es_privado=False)

    assert entry1.clave == "nombre_app"
    assert entry2.clave == "nivel_academico"

    # Consultar
    todas = mem_mgr.consultar_memorias(usuario_id="u1", incluir_privadas=True)
    assert len(todas) == 2

    publicas_solo = mem_mgr.consultar_memorias(usuario_id="u1", incluir_privadas=False)
    assert len(publicas_solo) == 1
    assert publicas_solo[0].clave == "nivel_academico"

    # Exportar
    json_exp = mem_mgr.exportar_memorias_json("u1")
    assert "SKY IA v12" in json_exp

    # Eliminar
    ok_del = mem_mgr.eliminar_memoria(entry1.id, usuario_id="u1")
    assert ok_del is True
    assert len(mem_mgr.consultar_memorias(usuario_id="u1")) == 1


# ==============================================================================
# 4. PRUEBAS BENCHMARK
# ==============================================================================
def test_evaluacion_benchmark_score():
    res = ejecutar_evaluacion_benchmark()
    assert res["total_preguntas"] >= 8
    assert res["tasa_exactitud_pct"] >= 95.0
    assert res["metricas"]["exactitud_matematica_pct"] == 100.0
    assert res["metricas"]["citas_inexistentes"] == 0


# ==============================================================================
# 5. PRUEBAS DE ENDPOINTS REST v12.0
# ==============================================================================
def test_api_universal_plan():
    res = client.post("/api/universal/plan", json={"prompt": "Desarrolla un módulo de FastAPI con tests", "area": "Programación"})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["modo"] == "dev"
    assert data["requiere_codigo"] is True
    assert len(data["pasos"]) > 0


def test_api_universal_factcheck():
    res = client.post("/api/universal/factcheck", json={"texto": "Demostramos que 7 * 8 = 56 con exactitud."})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["es_consistente"] is True
    assert len(data["calculos_verificados"]) >= 1


def test_api_universal_sources():
    res = client.get("/api/universal/sources?disciplina=salud")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert len(data["sources"]) >= 3
    assert any("who.int" in s["url"] or "paho.org" in s["url"] for s in data["sources"])


def test_api_universal_memory_and_benchmark():
    # Save memory
    res_save = client.post("/api/universal/memory/save", json={
        "categoria": "preferencia",
        "clave": "idioma_reportes",
        "valor": "Español profesional",
        "usuario_id": "test_user"
    })
    assert res_save.status_code == 200
    assert res_save.json()["ok"] is True

    # List memories
    res_list = client.get("/api/universal/memory/list?usuario_id=test_user")
    assert res_list.status_code == 200
    assert res_list.json()["total"] >= 1

    # Export memories
    res_exp = client.get("/api/universal/memory/export?usuario_id=test_user")
    assert res_exp.status_code == 200
    assert "attachment" in res_exp.headers.get("content-disposition", "")

    # Benchmark
    res_bench = client.get("/api/universal/benchmark")
    assert res_bench.status_code == 200
    data_bench = res_bench.json()
    assert data_bench["ok"] is True
    assert data_bench["tasa_exactitud_pct"] >= 95.0
