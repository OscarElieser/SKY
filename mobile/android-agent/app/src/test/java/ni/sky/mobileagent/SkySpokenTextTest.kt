package ni.sky.mobileagent

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SkySpokenTextTest {
    @Test fun markdownDoesNotBecomeSpokenPunctuation() {
        val written = "# Resumen\n- **Primero:** agua.\n- Segundo: oxígeno."
        val spoken = SkySpokenText.prepare(written)
        assertFalse(spoken.contains("#"))
        assertFalse(spoken.contains("*"))
        assertTrue(spoken.contains("Primero: agua."))
        assertTrue(spoken.contains("Segundo: oxígeno."))
        assertEquals("# Resumen\n- **Primero:** agua.\n- Segundo: oxígeno.", written)
    }

    @Test fun numbersAndAccentStayAccurate() {
        val spoken = SkySpokenText.prepare("¿Cuánto cuesta? ¡Son 3,14 y 1.500 córdobas! 😊")
        assertTrue(spoken.contains("3,14"))
        assertTrue(spoken.contains("1.500"))
        assertFalse(spoken.contains("😊"))
        assertFalse(spoken.contains("¿"))
        assertFalse(spoken.contains("¡"))
    }

    @Test fun markdownUrlAndCodeAreOnlyDescribed() {
        val spoken = SkySpokenText.prepare(
            "Mira [la guía](https://example.org/guia) y\n```kotlin\nprintln(123)\n```"
        )
        assertTrue(spoken.contains("la guía"))
        assertTrue(spoken.contains("Código disponible en pantalla."))
        assertFalse(spoken.contains("https"))
        assertFalse(spoken.contains("println"))
    }

    @Test fun chemicalEquilibriumAndFractionSpeakWithoutLatexNoise() {
        val spoken = SkySpokenText.prepare(
            "Constante de equilibrio:\n\\[\nK_{\\text{eq}} = " +
                "\\frac{k_{\\text{f}}}{k_{\\text{r}}}\n\\]"
        )
        assertTrue(spoken.contains("dividido entre"))
        assertTrue(spoken.contains("es igual a"))
        assertTrue(spoken.contains("subíndice"))
        assertFalse(spoken.contains("frac"))
        assertFalse(spoken.contains("\\"))
    }

    @Test fun reactionAndExponentSpeakNaturally() {
        val spoken = SkySpokenText.prepare(
            "\\(A+B\\rightleftharpoons C\\). La energía es \\(E=mc^{2}\\)."
        )
        assertTrue(spoken.contains("en equilibrio con"))
        assertTrue(spoken.contains("elevado a 2"))
        assertFalse(spoken.contains("rightleftharpoons"))
    }

    @Test fun emptySpeechHasNoContent() {
        assertEquals("", SkySpokenText.prepare("  "))
    }
}
