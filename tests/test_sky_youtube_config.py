"""YouTube official API key visibility between PowerShell .env and SKY HUD server."""
from __future__ import annotations

from unittest.mock import patch

# La API registra el router HUD. Importarla primero evita el ciclo
# hud_api -> api -> hud_api durante la colección aislada de pytest.
from metaverse import api as _sky_api  # noqa: F401
from metaverse import hud_api


def test_api_reads_local_dotenv_even_if_process_started_before_key(monkeypatch, tmp_path):
    archivo = tmp_path / ".env"
    archivo.write_text("YOUTUBE_API_KEY=clave_ficticia_para_pruebas\n", encoding="utf-8")
    monkeypatch.setattr(hud_api, "YOUTUBE_ENV_FILE", archivo)
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    monkeypatch.delenv("SKY_LOCAL_ONLY", raising=False)
    assert hud_api._youtube_clave() == "clave_ficticia_para_pruebas"

    with patch("neural_core.sky_youtube_search.buscar_videos", return_value={
        "videos": [{"id": "abcdefghijk", "title": "Entre dos tierras", "channel": "Canal oficial"}],
        "origen": "youtube_data_api", "verificado": True,
    }) as buscar:
        resultado = hud_api.youtube("Entre dos tierras")
    buscar.assert_called_once_with("Entre dos tierras", clave="clave_ficticia_para_pruebas")
    assert resultado["embebible"] is True
    assert resultado["incrustacion_verificada"] is True
    assert "clave_ficticia_para_pruebas" not in str(resultado)


def test_youtube_explicit_runtime_key_has_precedence(monkeypatch, tmp_path):
    archivo = tmp_path / ".env"
    archivo.write_text("YOUTUBE_API_KEY=clave_de_archivo\n", encoding="utf-8")
    monkeypatch.setattr(hud_api, "YOUTUBE_ENV_FILE", archivo)
    monkeypatch.setenv("YOUTUBE_API_KEY", "clave_del_proceso")
    assert hud_api._youtube_clave() == "clave_del_proceso"


def test_youtube_no_key_has_helpful_message(monkeypatch, tmp_path):
    archivo = tmp_path / ".env"
    archivo.write_text("GEMINI_API_KEY=solo_gemini\n", encoding="utf-8")
    monkeypatch.setattr(hud_api, "YOUTUBE_ENV_FILE", archivo)
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    monkeypatch.delenv("SKY_LOCAL_ONLY", raising=False)
    assert hud_api._youtube_clave() == ""
    resultado = hud_api.youtube("Entre dos tierras")
    assert resultado["videos"] == []
    assert resultado["embebible"] is False
    assert "YOUTUBE_API_KEY" in resultado["motivo"]
