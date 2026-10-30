"""Evidencias para router conservador y HUD de fiabilidad."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from neural_core import sky_role_router as router
from neural_core import sky_role_lessons as memory

class RouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.env=patch.dict("os.environ",{"SKY_ROLE_LESSONS_DB":str(Path(self.tmp.name)/"a.db"),
                  "SKY_VERIFIED_ROLES_DB":str(Path(self.tmp.name)/"b.db")})
        self.env.start()
    def tearDown(self):
        self.env.stop();self.tmp.cleanup()
    def test_eight_roles(self):
        items={"fuerza":"fisica","masa molar":"quimica","rúbrica":"educacion",
               "promedio":"datos","sintaxis de Python":"programacion",
               "audita el código":"ciberseguridad","publicaciones académicas":"investigacion",
               "cuánto es 3+4":"matematicas"}
        for text,expected in items.items():
            self.assertEqual(router.recommend(text)["role"],expected)
    def test_ambiguous_and_unknown_not_executed(self):
        for text in ("masa molar y rúbrica","abrí YouTube y reproduce"):
            self.assertFalse(router.dispatch(text,{})["executed"])
    def test_math_real(self):
        r=router.dispatch("cuánto es 7*5",{"expression":"7*5"})
        self.assertEqual(r["status"],"VERIFIED_LIMITED_SCOPE")
        self.assertEqual(r["execution"]["steps"][0]["result"]["value"],35)
    def test_physics_real(self):
        r=router.dispatch("fuerza",{"modelo":"segunda_ley_newton","masa_kg":3,"aceleracion_m_s2":4})
        self.assertEqual(r["execution"]["steps"][0]["result"]["fuerza_n"],12)
    def test_research_without_permission_does_not_search(self):
        r=router.dispatch("publicaciones académicas",{"query":"education"})
        self.assertEqual(r["status"],"FAILED")
        self.assertFalse(r["selection"]["network_allowed"])
    def test_reliability_block_on_frequent_failures(self):
        for _ in range(4):memory.record("matematicas","calcular","FAILED",issue="verification_mismatch")
        memory.record("matematicas","calcular","VERIFIED_LIMITED_SCOPE")
        with patch("neural_core.sky_role_router.execution.run_plan",
                   side_effect=AssertionError("no dispatch")):
            out=router.dispatch("cuánto es 2+1",{"expression":"2+1"})
        self.assertEqual(out["status"],"REQUIRES_REVIEW")
        self.assertFalse(out["executed"])
    def test_cold_start_and_metrics(self):
        d=router.dashboard()
        self.assertGreaterEqual(d["registered_tools"],8)
        self.assertEqual(d["observations"],0)
        self.assertFalse(d["physical_device_verified"])
    def test_secret_not_stored(self):
        secret="SENSITIVE_TOKEN_444"
        router.dispatch("sintaxis de python",{"source":"x='"+secret+"'"})
        self.assertNotIn(secret.encode(),(Path(self.tmp.name)/"a.db").read_bytes())
    def test_ui_and_authenticated_api(self):
        hud=Path("metaverse/static/hud.js").read_text()
        html=Path("metaverse/static/hud.html").read_text()
        api=Path("metaverse/sky_verified_roles_api.py").read_text()
        self.assertIn("abrirPanelRoles",hud)
        self.assertIn("btn-role-health",html)
        self.assertIn('"/dispatch"',api)
        self.assertIn('dependencies=[Depends(require_key)]',api)

if __name__=="__main__":unittest.main()
