"""Regresiones de evidencia real, comprobación de dispositivo y telefonía.

Las pruebas automáticas no sustituyen las comprobaciones físicas en Windows/Android.
"""
from __future__ import annotations

import pytest

from neural_core.factcheck_engine import SkyFactCheckEngine, VerificationStatus
from neural_core import sky_phone, windows_controller


@pytest.mark.parametrize("afirmacion", [
    "Según la OMS, el 87% de la población tiene este resultado.",
    "La UNESCO publicó que 99% de docentes aprobaron la capacitación.",
    "NASA confirmó que 70% de las observaciones fueron positivas.",
    "El INIDE informa que 200 estudiantes aprobaron este examen.",
])
def test_nombrar_institucion_no_verifica_dato(afirmacion):
    hallazgos = SkyFactCheckEngine.extraer_afirmaciones(afirmacion)
    assert hallazgos
    assert all(x.estado == VerificationStatus.NO_COMPROBADA for x in hallazgos)
    assert all(x.fuente_corroborante is None for x in hallazgos)


def test_lista_de_fuentes_no_implica_cotejo_real():
    informe = SkyFactCheckEngine.auditar_respuesta(
        "La UNESCO determinó que el 75% de las escuelas obtuvo resultados perfectos.",
        fuentes_disponibles=["https://www.unesco.org/"],
    )
    assert informe.respaldadas == 0
    assert informe.no_comprobadas == 1
    assert informe.advertencia_incertidumbre


@pytest.mark.parametrize("plataforma", ["Linux", "Darwin"])
def test_verificador_no_inventa_prueba_fisica_en_otro_sistema(monkeypatch, plataforma):
    monkeypatch.setattr(windows_controller.platform, "system", lambda: plataforma)

    def prohibido():
        raise AssertionError("No se debe usar un detector de ventanas Windows en otra plataforma")

    monkeypatch.setattr(windows_controller, "list_user_windows", prohibido)
    observation = windows_controller.verify_window_or_process(["word"], pid=12345)
    assert observation["verified"] is False
    assert observation["method"] == "unsupported_platform"


def test_telefono_nativo_no_finge_que_llamo_o_envio_sms(tmp_path, monkeypatch):
    monkeypatch.setattr(sky_phone, "STORE", tmp_path / "sky_phone_test.json")
    number = "+50588889999"
    check = sky_phone.native_destination(number)
    assert check["allowed"] is True
    assert check["destination"] == number
    assert check["native_os_user_action_required"] is True
    assert check["call_completed"] is False
    assert check["message_sent"] is False

    sky_phone.set_block(number, blocked=True, approved=True)
    with pytest.raises(sky_phone.PhoneInvalid, match="bloqueado"):
        sky_phone.native_destination(number)


def test_catalogo_no_confunde_telefonia_nativa_con_llamada_finalizada():
    caps = sky_phone.capabilities()
    assert "explicit user tap" in caps["native_dialer_sms"]
    assert caps["inbound"] == "not implemented"
