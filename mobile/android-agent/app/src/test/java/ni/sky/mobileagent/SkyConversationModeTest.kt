package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyConversationModeTest {
    @Test fun explicitLocalModeNeverAuthorizesExternalAi() {
        assertEquals(SkyConversationMode.Mode.LOCAL_TOOLS,
            SkyConversationMode.select(localOnly = true))
        assertFalse(SkyConversationMode.mayUseRemoteAi(
            SkyConversationMode.select(localOnly = true)))
        assertTrue(SkyConversationMode.mayUseRemoteAi(
            SkyConversationMode.select(localOnly = false)))
    }

    @Test fun noCloudModeMustBeHonestAboutUnimplementedLlm() {
        val explanation = SkyConversationMode.offlineMessage()
        assertTrue(explanation.contains("NO hay un modelo generativo completo"))
        assertTrue(explanation.contains("Conservé tu texto"))
        assertTrue(explanation.contains("sin enviarlo ni borrarlo"))
    }

    @Test fun statusDistinguishesConfiguredFromProvenWorking() {
        val none = SkyConversationMode.engineStatus(false, false, false)
        assertTrue(none.contains("Modelo generativo dentro del teléfono: no integrado todavía"))
        assertTrue(none.contains("Claude y Grok: adaptadores Android no integrados"))
        val configured = SkyConversationMode.engineStatus(true, true, true)
        assertTrue(configured.contains("emparejada; verificar"))
        assertTrue(configured.contains("cuota por verificar"))
        assertFalse(configured.contains("Claude y Grok: disponibles"))
    }

    @Test fun diagnosticCannotTurnOnDangerousRemotePath() {
        assertFalse(SkyConversationMode.mayUseRemoteAi(SkyConversationMode.Mode.LOCAL_TOOLS))
        assertEquals("sky_conversation_mode", SkyConversationMode.PREFS)
    }
}
