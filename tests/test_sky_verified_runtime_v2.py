"""Pruebas de orquestación y reintentos seguros, sin servicios externos."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from neural_core import sky_verified_roles as roles

class RuntimeV2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict("os.environ", {"SKY_VERIFIED_ROLES_DB": str(Path(self.temp.name) / "db.sqlite")})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_physics_to_math_cross_role(self):
        out = roles.run_plan([
            {"id":"force","role":"fisica","tool":"mecanica_si",
             "args":{"modelo":"segunda_ley_newton","masa_kg":3,"aceleracion_m_s2":4}},
            {"id":"times","role":"matematicas","tool":"calcular",
             "depends_on":"force","args":{"expression":"fuerza_n * 2"}},
        ])
        self.assertEqual(out["status"],"VERIFIED_LIMITED_SCOPE")
        self.assertEqual(out["steps"][1]["result"]["value"],24)

    def test_chemistry_to_math_cross_role(self):
        result=roles.run_plan([
            {"id":"water","role":"quimica","tool":"masa_molar","args":{"formula":"H2O"}},
            {"id":"two","role":"matematicas","tool":"calcular",
             "depends_on":"water","args":{"expression":"masa_molar_g_mol * 2"}}
        ])
        self.assertAlmostEqual(result["steps"][1]["result"]["value"],36.03,places=2)

    def test_education_actual_score(self):
        result=roles.run_plan([{"id":"rubric","role":"educacion","tool":"evaluar_rubrica",
            "args":{"criterios":[{"nombre":"Contenido","maximo":80,"obtenido":70},
                                 {"nombre":"Presentación","maximo":20,"obtenido":20}]}}])
        self.assertEqual(result["steps"][0]["result"]["total_obtenido"],90)
        self.assertEqual(result["steps"][0]["attempts"],1)

    def test_reviewer_recovers_single_inconsistent_calculation(self):
        original=roles.EXECUTORS[("datos","resumen")]
        calls=[]
        def flaky(args,prev):
            calls.append(1)
            result=original(args,prev)
            if len(calls)==1:
                result["mean"]=99
            return result
        with patch.dict(roles.EXECUTORS, {("datos","resumen"):flaky}):
            out=roles.run_plan([{"id":"stats","role":"datos","tool":"resumen",
                                 "args":{"values":[1,2,3]}}])
        self.assertEqual(len(calls),2)
        self.assertEqual(out["status"],"VERIFIED_LIMITED_SCOPE")
        self.assertEqual(out["steps"][0]["attempts"],2)
        self.assertEqual(out["steps"][0]["correction"],"repeated_after_mismatch")
        self.assertEqual(out["steps"][0]["result"]["mean"],2)

    def test_reviewer_fails_closed_after_two_mismatches(self):
        calls=[]
        def broken(args,prev):
            calls.append(1)
            return {"count":3,"mean":999,"minimum":1,"maximum":3,"median":2}
        with patch.dict(roles.EXECUTORS,{("datos","resumen"):broken}):
            out=roles.run_plan([
                {"id":"stats","role":"datos","tool":"resumen","args":{"values":[1,2,3]}},
                {"id":"calc","role":"matematicas","tool":"calcular",
                 "depends_on":"stats","args":{"expression":"mean+1"}}
            ])
        self.assertEqual(len(calls),2)
        self.assertEqual(out["status"],"FAILED")
        self.assertEqual(out["completed_steps"],1)
        self.assertEqual(out["steps"][0]["attempts"],2)

    def test_catalogue_identifies_actual_tools(self):
        rows={x["id"]:x for x in roles.catalogue()["roles"]}
        for role,tool in (("fisica","mecanica_si"),("quimica","masa_molar"),
                          ("educacion","evaluar_rubrica")):
            self.assertIn(tool,rows[role]["tools"])
            self.assertEqual(rows[role]["execution"],"read_only_tools")
        self.assertEqual(rows["viajes"]["execution"],"catalogue_only")

if __name__=="__main__":
    unittest.main()
