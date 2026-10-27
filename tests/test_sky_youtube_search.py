"""Pruebas de metadatos YouTube sin red para la búsqueda integrada de SKY."""
import json
from unittest.mock import patch

from neural_core import sky_youtube_search as yt


def _pagina(videos):
    return "<script>var ytInitialData = " + json.dumps({
        "contents": {"sectionListRenderer": {"contents": [
            {"itemSectionRenderer": {"contents": [
                {"videoRenderer": video} for video in videos
            ]}}
        ]}}
    }) + ";</script>"


def test_youtube_public_results_have_real_ids_titles_and_channels():
    pagina = _pagina([
        {"videoId": "abcdefghijk", "title": {"runs": [{"text": "Reik - "},
            {"text": "Te fuiste de aquí"}]}, "ownerText": {"runs": [{"text": "ReikVEVO"}]}},
        {"videoId": "abcdefghijk", "title": {"simpleText": "Duplicado"}},
        {"videoId": "NO", "title": {"simpleText": "Inválido"}},
        {"videoId": "lmnopqrstuv", "title": {"simpleText": "Reik - En concierto"}},
    ])
    result = yt.extraer_resultados_web(pagina)
    assert result == [
        {"id": "abcdefghijk", "title": "Reik - Te fuiste de aquí", "channel": "ReikVEVO"},
        {"id": "lmnopqrstuv", "title": "Reik - En concierto", "channel": ""}
    ]


def test_youtube_public_result_parser_rejects_missing_or_malformed_data():
    assert yt.extraer_resultados_web("YouTube bloqueó el acceso") == []
    assert yt.extraer_resultados_web("var ytInitialData = {malformed}") == []
    assert yt.extraer_resultados_web(_pagina([
        {"videoId": "11111111111", "title": {"runs": []}},
        {"videoId": "http://evil", "title": {"simpleText": "X"}},
    ])) == []


def test_youtube_api_is_preferred_and_verifies_embeddable():
    api = [{"id": "abcdefghijk", "title": "Reik - Te fuiste de aquí",
            "url": "https://www.youtube.com/watch?v=abcdefghijk"}]
    with patch("neural_core.multimedia._search_youtube_api", return_value=api) as official, \
         patch.object(yt, "buscar_web_publica") as public:
        result = yt.buscar_videos("Reik Te fuiste de aquí", clave="fake-test-key")
    assert result["verificado"] is True
    assert result["origen"] == "youtube_data_api"
    assert result["videos"][0]["id"] == "abcdefghijk"
    official.assert_called_once()
    public.assert_not_called()


def test_youtube_without_key_searches_public_page_without_substitution():
    esperado = [{"id": "abcdefghijk", "title": "Reik - Te fuiste de aquí"}]
    with patch.object(yt, "buscar_web_publica", return_value=esperado) as public:
        result = yt.buscar_videos("Reik Te fuiste de aquí")
    assert result["videos"] == esperado
    assert result["verificado"] is False
    public.assert_called_once_with("Reik Te fuiste de aquí", 6)


def test_youtube_offline_reports_error_instead_of_fake_video():
    with patch.object(yt, "buscar_web_publica", side_effect=TimeoutError):
        result = yt.buscar_videos("Reik Te fuiste de aquí")
    assert result["videos"] == []
    assert result["origen"] == "sin_resultados"
    assert "Queen" not in str(result)
    assert result["motivo"]


def test_fallback_when_api_fails():
    with patch("neural_core.multimedia._search_youtube_api", side_effect=TimeoutError), \
         patch.object(yt, "buscar_web_publica", return_value=[
             {"id": "abcdefghijk", "title": "Reik - Te fuiste de aquí"}]):
        result = yt.buscar_videos("Reik", clave="test-key")
    assert result["origen"] == "youtube_web_publica"
    assert result["verificado"] is False


def test_hud_youtube_playback_not_blocked_by_missing_api_key():
    """La ventana interna funciona aunque la búsqueda use resultados públicos."""
    from pathlib import Path

    script = (Path(__file__).resolve().parents[1] / "metaverse" / "static" / "hud.js").read_text(encoding="utf-8")
    assert "if (p.action === 'play_media' && (p.params.service || 'youtube') === 'youtube' && !p.params.path)" in script
    assert "&& S.ytApi && !p.params.path" not in script
    assert "await reproductor(p.params.query); return;" in script


def test_hud_invalid_youtube_url_is_reported_clearly():
    """Un campo vacío no debe convertirse en un video ni mostrar un error técnico sin explicación."""
    from pathlib import Path

    script = (Path(__file__).resolve().parents[1] / "metaverse" / "static" / "hud.js").read_text(encoding="utf-8")
    assert "const enlace = urlInput.value.trim();" in script
    assert "Pegá un enlace HTTPS completo de YouTube" in script


def test_hud_youtube_blocked_embed_offers_alternative_and_original():
    """La ventana interna ofrece una salida honesta sin eludir YouTube."""
    from pathlib import Path

    script = (Path(__file__).resolve().parents[1] / "metaverse" / "static" / "hud.js").read_text(encoding="utf-8")
    assert "const otro = el('button', '', 'Otro video');" in script
    assert "otro.addEventListener('click', () => controlReproductor('next'))" in script
    assert "const original = el('a', '', 'Ver en YouTube');" in script
    assert "original.href = 'https://www.youtube.com/watch?v='" in script
    assert "ytVerificado = !!r.incrustacion_verificada" in script
    assert "YouTube debe autorizar la reproducción" in script
    assert "await decir('Cargué " not in script


def test_hud_observes_real_embed_player_errors_without_guessing():
    """The official iframe API reports actual errors, not simulated availability."""
    from pathlib import Path

    script = (Path(__file__).resolve().parents[1] / "metaverse" / "static" / "hud.js").read_text(encoding="utf-8")
    assert "https://www.youtube.com/iframe_api" in script
    assert "onError: evento =>" in script
    assert "onStateChange: evento =>" in script
    assert "onAutoplayBlocked:" in script
    assert "[101, 150].includes(codigo)" in script
    assert "codigo === 153" in script
    assert "codigo === 100" in script
    assert "vigilarReproductor(iframe, v.id, barra)" in script
    assert "encodeURIComponent(window.location.origin)" in script
