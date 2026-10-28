"""Verifica texto de voz sin borrar información escrita ni datos numéricos."""
import unittest

from neural_core.sky_spoken_text import preparar_voz
from neural_core import sky_cerebro


class TestSkyNaturalVoiceText(unittest.TestCase):
    def test_markdown_bullets_are_not_read_as_sign_names(self):
        written = "# Resumen\n- **Primero:** las plantas usan luz.\n- Segundo: producen oxígeno."
        spoken = preparar_voz(written)
        self.assertNotIn("#", spoken)
        self.assertNotIn("*", spoken)
        self.assertNotIn("- ", spoken)
        self.assertIn("Primero: las plantas usan luz.", spoken)
        self.assertIn("Segundo: producen oxígeno.", spoken)
        self.assertEqual(written, "# Resumen\n- **Primero:** las plantas usan luz.\n- Segundo: producen oxígeno.")

    def test_decimals_and_ordinary_punctuation_are_preserved(self):
        spoken = preparar_voz("¿Cuánto vale? ¡Claro! 3,14 y 1.500 córdobas.")
        self.assertIn("3,14", spoken)
        self.assertIn("1.500", spoken)
        self.assertIn("?", spoken)
        self.assertNotIn("¿", spoken)
        self.assertNotIn("¡", spoken)

    def test_link_keeps_label_but_hides_url(self):
        spoken = preparar_voz("Lee [la guía](https://example.test/instrucciones) y revisa https://x.test/p")
        self.assertIn("la guía", spoken)
        self.assertIn("un enlace", spoken)
        self.assertNotIn("https", spoken)

    def test_code_is_not_spoken(self):
        spoken = preparar_voz("Prueba:\n```python\nprint('secreto')\n```\nListo.")
        self.assertIn("Código disponible en pantalla.", spoken)
        self.assertNotIn("print", spoken)
        self.assertNotIn("secreto", spoken)

    def test_preserve_accents_without_emojis(self):
        self.assertIn("Nicaragua", preparar_voz("¡Hola! 😊 Nicaragua"))
        self.assertNotIn("😊", preparar_voz("¡Hola! 😊 Nicaragua"))

    def test_nicaraguan_tuteo_in_core_prompts(self):
        self.assertIn("tú", sky_cerebro.SISTEMA)
        self.assertIn("nicaragüense", sky_cerebro.SISTEMA)
        self.assertIn("tú", sky_cerebro.SISTEMA_LOCAL_BREVE)


if __name__ == "__main__":
    unittest.main()
