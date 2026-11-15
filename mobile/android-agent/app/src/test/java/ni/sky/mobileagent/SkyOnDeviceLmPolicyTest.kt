package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

/**
 * No requiere descargar pesos; la inferencia real se comprueba por separado
 * en teléfono con un .litertlm importado y su hash reconocido.
 */
class SkyOnDeviceLmPolicyTest {
    @Test fun rejectsEmptyHugePromptsAndBogusModelSizes() {
        assertFalse(SkyOnDeviceLm.acceptedPrompt(""))
        assertFalse(SkyOnDeviceLm.acceptedPrompt(" ".repeat(300)))
        assertTrue(SkyOnDeviceLm.acceptedPrompt("Explicá qué es una variable en Kotlin"))
        assertFalse(SkyOnDeviceLm.acceptedPrompt("a".repeat(SkyOnDeviceLm.PROMPT_MAX + 1)))
        assertFalse(SkyOnDeviceLm.acceptedSize(10L))
        assertFalse(SkyOnDeviceLm.acceptedSize(SkyOnDeviceLm.MAX_BYTES + 1))
        assertTrue(SkyOnDeviceLm.acceptedSize(600L * 1024 * 1024))
    }

    @Test fun sha256IsDeterministicAndAuditable() {
        assertEquals(
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            SkyOnDeviceLm.sha256("abc".toByteArray())
        )
        assertTrue(SkyOnDeviceLm.MODEL_FILE_NAME.endsWith(".litertlm"))
    }

    @Test fun localModeNeverRequiresRemoteAi() {
        assertFalse(SkyConversationMode.mayUseRemoteAi(
            SkyConversationMode.select(localOnly = true)))
        assertTrue(SkyConversationMode.offlineMessage().contains(".litertlm"))
        val status = SkyConversationMode.engineStatus(
            ownApiPaired = false, geminiKeyReady = false,
            groqKeyReady = false, localOnDeviceLlmReady = true)
        assertTrue(status.contains("archivo importado; ejecución sin validar"))
        assertTrue(status.contains("Claude y Grok: adaptadores Android no integrados"))
    }
}
