package ni.sky.mobileagent

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class SkyMobileIntentRouterTest {
    @Test fun conversationPanelViaVoice() {
        val command = SkyMobileIntentRouter.route("SKY, abre panel de conversación")
        assertEquals(SkyMobileIntentRouter.Action.Kind.OPEN_CHAT, command?.kind)
    }

    @Test fun conversationPanelViaText() {
        val command = SkyMobileIntentRouter.route("Mostrame el chat")
        assertEquals(SkyMobileIntentRouter.Action.Kind.OPEN_CHAT, command?.kind)
    }

    @Test fun documentModuleOnlyWhenRequested() {
        val command = SkyMobileIntentRouter.route("SKY activa módulo de documentos")
        assertEquals(SkyMobileIntentRouter.Action.Kind.OPEN_MODULE, command?.kind)
        assertEquals("documentos", command?.module)
    }

    @Test fun classroomAndProgrammingPanels() {
        assertEquals("docente", SkyMobileIntentRouter.route("Abre SKY Docente")?.module)
        assertEquals("codigo", SkyMobileIntentRouter.route("Abrí programación")?.module)
    }

    @Test fun closingPanel() {
        assertEquals(SkyMobileIntentRouter.Action.Kind.CLOSE_PANEL,
            SkyMobileIntentRouter.route("SKY cierra panel")?.kind)
    }

    @Test fun normalPromptsMustNotTriggerUiActions() {
        assertNull(SkyMobileIntentRouter.route("Redacta un documento de planificación"))
        assertNull(SkyMobileIntentRouter.route("Explícame programación en Python"))
        assertNull(SkyMobileIntentRouter.route("Investiga aplicaciones educativas"))
        assertNull(SkyMobileIntentRouter.route("abre una investigación sobre robótica"))
    }
}
