"""Pruebas aisladas de cálculo científico y rúbricas."""
import unittest
from neural_core.sky_verified_science import ScienceInputError, mecanica_si, masa_molar, evaluar_rubrica, review

class ScienceTests(unittest.TestCase):
    def test_motion(self):
        args={"modelo":"aceleracion_constante","velocidad_inicial_m_s":2,
              "aceleracion_m_s2":3,"tiempo_s":4}
        val=mecanica_si(args)
        self.assertEqual((val["velocidad_final_m_s"],val["desplazamiento_m"]),(14,32))
        self.assertTrue(review("fisica","mecanica_si",args,val)["passed"])
    def test_energy_and_force(self):
        self.assertEqual(mecanica_si({"modelo":"energia_cinetica","masa_kg":3,
                                      "velocidad_m_s":4})["energia_j"],24)
        self.assertEqual(mecanica_si({"modelo":"segunda_ley_newton","masa_kg":2,
                                      "aceleracion_m_s2":6})["fuerza_n"],12)
    def test_physics_rejects_nonfinite_values(self):
        with self.assertRaises(ScienceInputError):
            mecanica_si({"modelo":"energia_cinetica","masa_kg":2,"velocidad_m_s":float("inf")})
    def test_chemical_formula_and_nested_parentheses(self):
        self.assertAlmostEqual(masa_molar({"formula":"H2O"})["masa_molar_g_mol"],18.015)
        self.assertEqual(masa_molar({"formula":"Ca(OH)2"})["elementos"],{"Ca":1,"H":2,"O":2})
        self.assertEqual(masa_molar({"formula":"Fe2(SO4)3"})["elementos"],{"Fe":2,"O":12,"S":3})
    def test_invalid_chemistry_rejected(self):
        for formula in ("Xy2","H0","C9999","Na Cl","Mg(OH","Ca()2"):
            with self.subTest(formula=formula),self.assertRaises(ScienceInputError):
                masa_molar({"formula":formula})
    def test_rubric_real_score(self):
        args={"criterios":[{"nombre":"Contenido","maximo":60,"obtenido":54},
                          {"nombre":"Presentación","maximo":40,"obtenido":36}]}
        result=evaluar_rubrica(args)
        self.assertEqual(result["porcentaje"],90)
        self.assertEqual(result["nivel_referencial"],"logrado")
        self.assertTrue(review("educacion","evaluar_rubrica",args,result)["passed"])
        result["porcentaje"]=95
        self.assertFalse(review("educacion","evaluar_rubrica",args,result)["passed"])
    def test_invalid_rubric_scores_rejected(self):
        for item in (
            {"criterios":[{"nombre":"Conocimiento","maximo":20,"obtenido":22}]},
            {"criterios":[{"nombre":"Contenido","maximo":True,"obtenido":1}]},
            {"criterios":[{"nombre":"Contenido","maximo":20,"obtenido":12},
                         {"nombre":"contenido","maximo":10,"obtenido":9}]},
        ):
            with self.assertRaises(ScienceInputError): evaluar_rubrica(item)
    def test_detects_corrupt_mass(self):
        args={"formula":"H2O"}
        result=masa_molar(args)
        result["masa_molar_g_mol"]+=10
        self.assertFalse(review("quimica","masa_molar",args,result)["passed"])

if __name__=="__main__":
    unittest.main()
