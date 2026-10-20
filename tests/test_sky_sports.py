"""Pruebas offline del módulo SKY Sports: no requieren internet ni claves."""
import unittest
from unittest.mock import patch
from io import BytesIO
from neural_core.sky_sports import (
    orden_ver_madrid, descripcion_partido, plataforma_oficial,
    pronostico_simple, SportsDataError, agenda_fecha,
)

from neural_core.sky_sports_ui import _embed_autorizado


def fixture(casa, fuera, goles_casa, goles_fuera):
    return {"status": "FINISHED",
            "homeTeam": {"id": casa}, "awayTeam": {"id": fuera},
            "score": {"fullTime": {"home": goles_casa, "away": goles_fuera}}}


class TestSportsCenter(unittest.TestCase):
    def test_orden_voluntaria(self):
        self.assertTrue(orden_ver_madrid("SKY, muéstrame partido en vivo de Madrid"))
        self.assertTrue(orden_ver_madrid("Ponme el partido del Real Madrid en directo"))
        for frase in ["Dime el resultado del Madrid", "Predice el partido del Madrid",
                      "Muéstrame partido en vivo de Barcelona",
                      "El Madrid juega hoy", "¿Qué pasó en el partido de Madrid?"]:
            self.assertFalse(orden_ver_madrid(frase))

    def test_operadores_oficiales(self):
        self.assertEqual(plataforma_oficial({"competition": {"code": "PD"}})[1],
                         "https://vix.com/")
        self.assertEqual(plataforma_oficial({"competition": {"code": "CL"}})[1],
                         "https://www.espn.com/")

    def test_formato_hora_nicaragua(self):
        m = {"utcDate": "2026-10-25T20:00:00Z", "status": "SCHEDULED",
             "homeTeam": {"name": "FC Barcelona"}, "awayTeam": {"name": "Real Madrid CF"}}
        texto = descripcion_partido(m)
        self.assertIn("Nicaragua", texto)
        self.assertIn("02:00 PM", texto)

    def test_pronostico_probabilidades(self):
        upcoming = {"homeTeam": {"id": 86}, "awayTeam": {"id": 81}}
        local = [fixture(86, 70+i, 2, 1) for i in range(6)]
        visita = [fixture(81, 90+i, 1, 1) for i in range(6)]
        p = pronostico_simple(upcoming, local, visita)
        self.assertAlmostEqual(p["local"] + p["empate"] + p["visitante"], 100, delta=0.11)
        self.assertGreater(p["local"], p["visitante"])
        self.assertEqual(p["muestra_local"], 6)

    def test_no_inventar_prediccion_si_falta_muestra(self):
        upcoming = {"homeTeam": {"id": 86}, "awayTeam": {"id": 81}}
        with self.assertRaises(SportsDataError):
            pronostico_simple(upcoming, [fixture(86, 70, 2, 1)], [])


    def test_agenda_fecha_validation(self):
        with self.assertRaises(ValueError):
            agenda_fecha("2026-02-30")

    def test_agenda_real_api_mocked(self):
        data = b'{"matches":[{"utcDate":"2026-10-19T20:00:00Z","id":2},{"utcDate":"2026-10-19T18:00:00Z","id":1}]}'
        with patch.dict("os.environ", {"SKY_FOOTBALL_DATA_TOKEN": "test-token"}):
            with patch("neural_core.sky_sports.urlopen", return_value=BytesIO(data)) as mocked:
                matches = agenda_fecha("2026-10-19")
        self.assertEqual([x["id"] for x in matches], [1, 2])
        self.assertIn("/matches?dateFrom=2026-10-19", mocked.call_args.args[0].full_url)
        self.assertNotIn("en-vivo", mocked.call_args.args[0].full_url)

    def test_no_reproductor_sin_origen_autorizado(self):
        with patch.dict("os.environ", {
            "SKY_SPORTS_EMBED_URL": "https://example.com/video",
            "SKY_SPORTS_ALLOWED_EMBED_HOSTS": "oficial.example"
        }):
            self.assertIsNone(_embed_autorizado())

    def test_reproductor_solo_origen_exacto(self):
        with patch.dict("os.environ", {
            "SKY_SPORTS_EMBED_URL": "https://oficial.example/player",
            "SKY_SPORTS_ALLOWED_EMBED_HOSTS": "oficial.example",
        }):
            self.assertEqual(_embed_autorizado(), "https://oficial.example/player")
        with patch.dict("os.environ", {
            "SKY_SPORTS_EMBED_URL": "https://oficial.example.bad.example/player",
            "SKY_SPORTS_ALLOWED_EMBED_HOSTS": "oficial.example",
        }):
            self.assertIsNone(_embed_autorizado())



if __name__ == "__main__":
    unittest.main()
