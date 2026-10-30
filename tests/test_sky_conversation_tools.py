"""Pruebas de frases reales: una sola SKY en voz, chat y móvil (sin LLM ni red)."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from neural_core import sky_conversation_tools as convo

class ConversationToolsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.env=patch.dict("os.environ",{
            "SKY_ROLE_LESSONS_DB":str(Path(self.temp.name)/"lesson.sqlite"),
            "SKY_VERIFIED_ROLES_DB":str(Path(self.temp.name)/"metrics.sqlite")})
        self.env.start()
    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_arithmetic_written_and_spoken(self):
        for sentence in ("¿Cuánto es (12 + 8) * 3?", "SKY, calcula (12 + 8) * 3"):
            with self.subTest(sentence=sentence):
                result=convo.maybe_answer(sentence,mode="voz")
                self.assertEqual(result["mensaje"],"El resultado es 60.")
                self.assertEqual(result["verificacion"]["status"],"VERIFIED_LIMITED_SCOPE")

    def test_statistics_are_real(self):
        r=convo.maybe_answer("Dame el promedio de 2, 4 y 6")
        self.assertIn("Promedio: 4",r["mensaje"])
        self.assertIn("mediana: 4",r["mensaje"])

    def test_chemistry_respects_symbol_case(self):
        r=convo.maybe_answer("Masa molar de H2O")
        self.assertIn("18.015",r["mensaje"])
        r2=convo.maybe_answer("Masa molar de Co")
        self.assertIn("58.933",r2["mensaje"])

    def test_physics_force_and_energy(self):
        force=convo.maybe_answer("Fuerza de Newton con masa de 3 kg y aceleración de 4 m/s²")
        self.assertIsNotNone(force)
        self.assertIn("12 newtons",force["mensaje"])
        energy=convo.maybe_answer("Energía cinética con masa de 3 kg y velocidad de 4 m/s")
        self.assertIsNotNone(energy)
        self.assertIn("24 julios",energy["mensaje"])

    def test_education_rubric_real(self):
        result=convo.maybe_answer("Evalúa rúbrica: Contenido 20/25; Presentación 18/25")
        self.assertIsNotNone(result)
        self.assertIn("38 de 50",result["mensaje"])
        self.assertIn("76%",result["mensaje"])

    def test_incomplete_or_sensitive_commands_do_not_route(self):
        for text in ("Abre YouTube", "envía un correo", "Elimina mis archivos",
                     "Investiga artículos científicos", "Calcula la fuerza",
                     "Masa molar", "Promedio de esta tabla", "Hola SKY"):
            with self.subTest(text=text):
                self.assertIsNone(convo.maybe_answer(text))

    def test_dangerous_expression_rejected_without_execution(self):
        with patch("os.system",side_effect=AssertionError("No shell")):
            self.assertIsNone(convo.maybe_answer("calcula __import__('os').system('whoami')"))
        self.assertIsNone(convo.maybe_answer("calcula 3 + os.system(1)"))

    def test_bad_input_does_not_claim_success(self):
        result=convo.maybe_answer("¿Cuánto es 8 / 0?")
        self.assertEqual(result["verificacion"]["status"],"FAILED")
        self.assertNotIn("El resultado es",result["mensaje"])
        result2=convo.maybe_answer("Masa molar de Xy2")
        self.assertEqual(result2["verificacion"]["status"],"FAILED")

    def test_no_physical_device_claims(self):
        response=convo.maybe_answer("¿Cuánto es 4+4?")
        self.assertFalse(response["ejecucion_externa"])
        self.assertIn("no_certifica_dispositivos",response["verificacion"]["scope"])

    def test_same_engine_connected_to_all_existing_chats(self):
        from pathlib import Path
        assistant=Path("neural_core/sky_asistente_personal.py").read_text(encoding="utf-8")
        api=Path("metaverse/asistente_api.py").read_text(encoding="utf-8")
        home=Path("metaverse/sky_home_api.py").read_text(encoding="utf-8")
        mobile=Path("metaverse/mobile_chat_api.py").read_text(encoding="utf-8")
        self.assertIn("sky_conversation_tools",assistant)
        self.assertIn("sky_conversation_tools",api)
        self.assertIn("sky_conversation_tools",home)
        self.assertIn("return home_chat(payload)",mobile)
        self.assertIn("asis.reglas(texto)",api)


    def test_python_syntax_and_ast_never_runs(self):
        fence=chr(96)*3
        s="Revisa sintaxis de Python:\n"+fence+"python\ndef hola():\n    return 42\n"+fence
        result=convo.maybe_answer(s)
        self.assertEqual(result["verificacion"]["status"],"VERIFIED_LIMITED_SCOPE")
        self.assertIn("Funciones encontradas: hola",result["mensaje"])

    def test_static_audit_reports_real_patterns(self):
        fence=chr(96)*3
        s="Audita el código Python:\n"+fence+"python\nimport os\nos.system('echo NEVER')\neval('2+2')\n"+fence
        result=convo.maybe_answer(s)
        self.assertIn("2 llamadas",result["mensaje"])
        self.assertIn("no certifica seguridad",result["mensaje"])

    def test_json_valid_and_invalid(self):
        r=convo.maybe_answer('Valida JSON: {"name":"SKY","count":2}')
        self.assertEqual(r["verificacion"]["status"],"VERIFIED_LIMITED_SCOPE")
        self.assertIn("Tipo superior: object",r["mensaje"])
        for bad in ('{"x":1,"x":2}','{"x":}'):
            with self.subTest(bad=bad):
                self.assertEqual(convo.maybe_answer("Valida JSON: "+bad)["verificacion"]["status"],"FAILED")

    def test_private_python_source_not_stored(self):
        private="TOKEN_PRIVATE_827381"
        r=convo.maybe_answer("Revisa sintaxis de Python:\nkey='"+private+"'")
        self.assertEqual(r["verificacion"]["status"],"VERIFIED_LIMITED_SCOPE")
        self.assertNotIn(private.encode(),(Path(self.temp.name)/"lesson.sqlite").read_bytes())

    def test_large_snippet_uses_fixed_router_intent(self):
        fence=chr(96)*3
        text="Revisa sintaxis de Python:\n"+fence+"python\n"+("x = 1\n"*150)+fence
        r=convo.maybe_answer(text)
        self.assertEqual(r["verificacion"]["status"],"VERIFIED_LIMITED_SCOPE")

    def test_snippet_missing_or_wrong_language_rejected(self):
        fence=chr(96)*3
        for text in ("Audita mi código","Revisa sintaxis de Python","Valida JSON:",
                     "Audita el código Python: "+fence+"javascript\nalert(1)\n"+fence):
            self.assertIsNone(convo.maybe_answer(text))

if __name__=="__main__":
    unittest.main()
