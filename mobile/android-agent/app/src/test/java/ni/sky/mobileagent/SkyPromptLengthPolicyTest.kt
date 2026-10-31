package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyPromptLengthPolicyTest {
    @Test fun fullNormalPromptIsPreservedAtBoundary() {
        val prompt = "P".repeat(SkyPromptLengthPolicy.NORMAL_MAX)
        assertEquals(prompt, SkyPromptLengthPolicy.compose(prompt, "optional", false))
    }

    @Test fun optionalContextIsReducedBeforeUserInstructions() {
        val prompt = "Evaluá cada requisito: " + "N".repeat(3600)
        val context = "system hints " + "X".repeat(2500)
        val output = SkyPromptLengthPolicy.compose(prompt, context, false)
        assertNotNull(output)
        assertTrue(output!!.endsWith(prompt))
        assertEquals(SkyPromptLengthPolicy.NORMAL_MAX, output.length)
    }

    @Test fun oversizedNormalPromptIsRejectedRatherThanSilentlyTruncated() {
        val prompt = "Estudio ".repeat(900)
        assertNull(SkyPromptLengthPolicy.compose(prompt, "", false))
        assertEquals("Estudio ".repeat(900), prompt) // original data stays intact
    }

    @Test fun deepModeAcceptsLongTextAndRejectsExcess() {
        val prompt = "A".repeat(15000)
        assertEquals(prompt, SkyPromptLengthPolicy.compose(prompt, "", true))
        assertNull(SkyPromptLengthPolicy.compose("B".repeat(16001), "", true))
    }

    @Test fun privateSkyAccepts32KWithoutExpandingExternalDeepMode() {
        val privatePrompt = "Consulta académica: " + "R".repeat(31980)
        assertEquals(privatePrompt, SkyPromptLengthPolicy.compose(
            privatePrompt, "contenido auxiliar", deep = true, ownApi = true))
        assertNull(SkyPromptLengthPolicy.compose(privatePrompt, "", deep = true))
        assertNull(SkyPromptLengthPolicy.compose("Z".repeat(32001), "", true, true))
        assertEquals(16000, SkyPromptLengthPolicy.limit(true))
        assertEquals(32000, SkyPromptLengthPolicy.limit(true, ownApi = true))
    }

    @Test fun blankTextNeverStartsNetworkRequest() {
        assertNull(SkyPromptLengthPolicy.compose("", "", true))
        assertNull(SkyPromptLengthPolicy.compose("  ", "", false))
    }
}
