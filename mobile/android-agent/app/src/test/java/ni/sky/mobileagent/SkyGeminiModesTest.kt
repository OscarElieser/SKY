package ni.sky.mobileagent

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

/** Sin credenciales, conexión a Google ni archivos privados. */
class SkyGeminiModesTest {
    @Test fun existingChatRemainsOnEconomyMode() {
        val selection = SkyGeminiModes.select("Hola SKY, contame un chiste")
        assertEquals(SkyGeminiModes.ECONOMY_MODEL, selection.model)
        assertEquals("Hola SKY, contame un chiste", selection.prompt)
        assertEquals(8, selection.historyTurns)
    }

    @Test fun explicitDeepReasoningIsOptInAndHasMoreContext() {
        val selection = SkyGeminiModes.select("SKY, modo profundo: Analizá este código y explicalo.")
        assertEquals(SkyGeminiModes.DEEP_MODEL, selection.model)
        assertEquals("Analizá este código y explicalo.", selection.prompt)
        assertEquals(30, selection.historyTurns)
        assertTrue(selection.answerChars > SkyGeminiModes.select("Hola").answerChars)
    }

    @Test fun flashModeAndEconomyModeAreExplicit() {
        val fast = SkyGeminiModes.select("Modo flash: Explicá este PDF")
        assertEquals(SkyGeminiModes.FLASH_MODEL, fast.model)
        assertEquals("Explicá este PDF", fast.prompt)
        val economic = SkyGeminiModes.select("Modo económico: Hola")
        assertEquals(SkyGeminiModes.ECONOMY_MODEL, economic.model)
        assertEquals("Hola", economic.prompt)
    }

    @Test fun naturalMentionDoesNotTriggerCostlyModel() {
        assertEquals(SkyGeminiModes.ECONOMY_MODEL,
            SkyGeminiModes.select("¿Qué significa modo profundo?").model)
        assertEquals(SkyGeminiModes.ECONOMY_MODEL,
            SkyGeminiModes.select("modo profundo: ").model)
    }

    @Test fun modelEndpointIsStrictlyAllowlisted() {
        assertTrue(SkyGeminiModes.endpointFor(SkyGeminiModes.FLASH_MODEL)
            .endsWith("/gemini-3.8-flash:generateContent"))
        try {
            SkyGeminiModes.endpointFor("https://otro-servidor/")
            fail("No debe aceptar URLs personalizadas")
        } catch (_: IllegalArgumentException) {
            // esperado
        }
    }
}
