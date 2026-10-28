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
            "embeddable": True, "url": "https://www.youtube.com/watch?v=abcdefghijk"}]
    with patch("neural_core.multimedia._search_youtube_api", return_value=api) as official, \
         patch.object(yt, "buscar_web_publica") as public:
        result = yt.buscar_videos("Reik Te fuiste de aquí", clave="fake-test-key")
    assert result["verificado"] is True
    assert result["origen"] == "youtube_data_api"
    assert result["videos"][0]["id"] == "abcdefghijk"
    official.assert_called_once()
    public.assert_not_called()


def test_without_key_never_scrapes_youtube():
    with patch.object(yt, "buscar_web_publica") as legacy:
        resultado = yt.buscar_videos("Heroes del Silencio Entre dos tierras")
    assert resultado["videos"] == []
    assert resultado["origen"] == "sin_api_oficial"
    assert "YOUTUBE_API_KEY" in resultado["motivo"]
    legacy.assert_not_called()


def test_official_api_failure_never_falls_back_to_scraping():
    with patch("neural_core.multimedia._search_youtube_api", side_effect=TimeoutError), \
         patch.object(yt, "buscar_web_publica") as legacy:
        resultado = yt.buscar_videos("Heroes del Silencio", clave="test-key")
    assert resultado["videos"] == []
    assert resultado["origen"] == "error_api_oficial"
    legacy.assert_not_called()


def test_youtube_official_search_filters_non_embeddable_videos():
    import io
    from urllib.parse import urlparse, parse_qs
    from neural_core.multimedia import _search_youtube_api
    import neural_core.multimedia as multimedia

    urls = []
    def mock_request(req, timeout=7):
        urls.append(req.full_url)
        if "/search?" in req.full_url:
            data = {"items": [
                {"id": {"videoId": "abcdefghijk"}},
                {"id": {"videoId": "lmnopqrstuv"}},
                {"id": {"videoId": "0123456789A"}},
                {"id": {"videoId": "QWERTY12345"}},
            ]}
        else:
            data = {"items": [
                {"id": "abcdefghijk", "status": {"embeddable": True, "privacyStatus": "public"},
                 "snippet": {"title": "Canción oficial", "channelTitle": "Artista"}},
                {"id": "lmnopqrstuv", "status": {"embeddable": False, "privacyStatus": "public"},
                 "snippet": {"title": "No incrustable"}},
                {"id": "0123456789A", "status": {"embeddable": True, "privacyStatus": "private"},
                 "snippet": {"title": "Video privado"}},
                {"id": "QWERTY12345", "status": {"embeddable": True, "privacyStatus": "public"},
                 "contentDetails": {"regionRestriction": {"blocked": ["NI"]}},
                 "snippet": {"title": "Bloqueado en Nicaragua"}},
            ]}
        return io.BytesIO(json.dumps(data).encode("utf-8"))

    with patch.object(multimedia.request, "urlopen", side_effect=mock_request), \
         patch.dict("os.environ", {"SKY_YOUTUBE_REGION": "NI"}):
        resultado = _search_youtube_api("Canción oficial", "test-key")

    assert [x["id"] for x in resultado] == ["abcdefghijk"]
    assert resultado[0]["channel"] == "Artista"
    assert "videoEmbeddable=true" in urls[0]
    assert "/videos?" in urls[1]
    assert parse_qs(urlparse(urls[1]).query)["part"] == ["status,snippet,contentDetails"]


def test_youtube_api_skips_when_no_key():
    from neural_core.multimedia import _search_youtube_api
    import neural_core.multimedia as multimedia
    with patch.object(multimedia.request, "urlopen") as remote:
        assert _search_youtube_api("Canción", "") == []
        remote.assert_not_called()


def test_hud_youtube_playback_not_blocked_by_missing_api_key():
    """La ventana interna funciona aunque la búsqueda use resultados públicos."""
    from pathlib import Path

    script = (Path(__file__).resolve().parents[1] / "metaverse" / "static" / "hud.js").read_text(encoding="utf-8")
    assert "if (p.action === 'play_media' && (p.params.service || 'youtube') === 'youtube' && !p.params.path)" in script
    assert "&& S.ytApi && !p.params.path" not in script
    assert "await reproductor(p.params.query, ['mini', 'normal', 'max', 'fullscreen', 'minimized'].includes(p.params.mode)" in script


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

def test_hud_yt_blocked_iframe_shows_official_fallback_without_fake_success():
    """If YouTube denies framing without an IFrame API error, users are not trapped."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    script = (root / "metaverse/static/hud.js").read_text(encoding="utf-8")
    css = (root / "metaverse/static/hud.css").read_text(encoding="utf-8")
    assert "function avisoIntegracionYT(videoId, mensaje)" in script
    assert "if (sesion !== ytSesion || ytReproduccionConfirmada" in script
    assert "}, 12000);" in script
    assert "YouTube está preparado, pero no confirmó reproducción" in script
    assert "El reproductor de YouTube no respondió dentro de SKY" in script
    assert "const original = el('a', 'btn', 'Ver directamente en YouTube');" in script
    assert "original.target = '_blank'; original.rel = 'noopener noreferrer';" in script
    assert "ytReproduccionConfirmada = true" in script
    assert "cancelarVigilanciaYT();" in script
    assert "onError: evento =>" in script
    assert "YouTube puede permitir verlo directamente" in script
    assert ".win .sky-youtube-warning{" in css
    # We never fetch protected streams, hide player permissions or bypass the owner.
    assert "youtube.com/watch?v=" in script


def test_youtube_blocked_player_offers_clickable_links_in_chat_too():
    """La ventana del chat puede estar al frente aunque el iframe quede bloqueado."""
    from pathlib import Path
    script = (Path(__file__).resolve().parents[1] / "metaverse/static/hud.js").read_text(encoding="utf-8")
    assert "ytAvisosChat = new Set()" in script
    assert "const tarjeta = addCard('YouTube no confirmó la reproducción', mensaje);" in script
    assert "const ver = el('a', 'btn', 'Abrir video original');" in script
    assert "ver.target = '_blank'; ver.rel = 'noopener noreferrer';" in script
    assert "otroChat.addEventListener('click', () => {" in script
    assert "ytIntentos.has(v.id)" in script
    assert "reproduccion_confirmada" not in script  # La API de búsqueda no confirma reproducción.


def test_player_automatic_fallback_has_no_bypass():
    from pathlib import Path
    script = (Path(__file__).resolve().parents[1] / "metaverse" / "static" / "hud.js").read_text(encoding="utf-8")
    assert "const YT = 'https://www.youtube.com';" in script
    assert "ytIntentos = new Set()" in script
    assert "[5, 100, 101, 150].includes(codigo)" in script
    assert "!ytIntentos.has(v.id)" in script
    assert "siguiente >= 0" in script
    assert "codigo === 153" in script
    assert "Ver en YouTube" in script


def test_legacy_youtube_resolver_never_fakes_unrelated_video():
    import neural_core.multimedia as multimedia
    with patch.dict("os.environ", {"YOUTUBE_API_KEY": "", "GOOGLE_API_KEY": ""}), \
         patch.object(multimedia.request, "urlopen") as remote:
        resultado = multimedia.resolve_youtube_video("Heroes del Silencio Entre dos tierras")
    assert resultado["embeddable"] is False
    assert resultado["video_id"] == ""
    assert resultado["candidates"] == []
    assert resultado["source"] == "youtube_api_required"
    assert "youtube.com/results?search_query=" in resultado["url"]
    remote.assert_not_called()


def test_legacy_youtube_resolver_only_returns_verified_api_candidates():
    import neural_core.multimedia as multimedia
    candidatos = [{
        "id": "abcdefghijk", "title": "Video autorizado",
        "channel": "Canal oficial", "embeddable": True,
        "url": "https://www.youtube.com/watch?v=abcdefghijk",
    }]
    with patch.dict("os.environ", {"YOUTUBE_API_KEY": "test-key"}), \
         patch.object(multimedia, "_search_youtube_api", return_value=candidatos) as buscar, \
         patch.object(multimedia.request, "urlopen") as remote:
        resultado = multimedia.resolve_youtube_video("Video autorizado")
    assert resultado["embeddable"] is True
    assert resultado["source"] == "youtube_api_v3"
    assert resultado["video_id"] == "abcdefghijk"
    buscar.assert_called_once()
    remote.assert_not_called()


def test_public_scraper_compatibility_is_disabled():
    import neural_core.sky_youtube_search as yt
    with patch.object(yt, "urlopen") as remote:
        assert yt.buscar_web_publica("una cancion") == []
        remote.assert_not_called()


def test_youtube_miniwindow_has_official_minimum_and_user_playback():
    """Small SKY floating players retain room for YouTube controls and manual playback."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    css = (root / "metaverse/static/hud.css").read_text(encoding="utf-8")
    script = (root / "metaverse/static/hud.js").read_text(encoding="utf-8")
    assert '.sky-cinematic .win[data-id="player"].mini{' in css
    assert 'height:min(365px, calc(100vh - 88px))' in css
    assert 'min-height: min(270px, calc(100vh - 142px))' in css
    assert "const iniciar = el('button', 'sky-youtube-play', '▶ Reproducir');" in script
    assert "iniciar.addEventListener('click', () => {" in script
    assert "ytCmd('playVideo')" in script
    assert "onReady: () => {" in script
    assert "ytPlayerListo = true;" in script
    assert "ytPlayer[func](...args)" in script
    assert "YouTube confirmó la reproducción." in script
    assert "ytReproduccionConfirmada = true;" in script
