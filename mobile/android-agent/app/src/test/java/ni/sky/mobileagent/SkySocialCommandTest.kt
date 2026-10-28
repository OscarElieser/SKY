package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkySocialCommandTest {
    @Test fun facelessTikTokIsPlannedCorrectly() {
        val request = SkySocialCommand.parse(
            "SKY, prepará un video viral para TikTok sobre rincones de Nicaragua sin mostrar mi cara"
        )
        assertNotNull(request)
        assertEquals("TikTok", request!!.platform)
        assertEquals("rincones de Nicaragua sin mostrar mi cara", request.topic)
        assertTrue(request.faceless)
        assertEquals(SkySocialCommand.Kind.POST, request.kind)
    }

    @Test fun organicInstagramWeek() {
        val request = SkySocialCommand.parse(
            "SKY dame un calendario de 7 días para Instagram sobre diseño gráfico"
        )
        assertNotNull(request)
        assertEquals(SkySocialCommand.Kind.WEEKLY_PLAN, request!!.kind)
        assertEquals("Instagram", request.platform)
        val prompt = SkySocialCommand.prompt(request)
        assertTrue(prompt.contains("7 días"))
        assertTrue(prompt.contains("crecimiento orgánico"))
        assertTrue(prompt.contains("no mostrar el rostro"))
    }

    @Test fun noMisroutingOfOtherCommandsOrPrivateMessages() {
        assertNull(SkySocialCommand.parse("SKY abre Instagram"))
        assertNull(SkySocialCommand.parse("SKY manda un mensaje a María por WhatsApp: Hola"))
        assertNull(SkySocialCommand.parse("SKY pon una alarma a las 7"))
        assertNull(SkySocialCommand.parse("SKY contame un chiste"))
    }

    @Test fun explicitCameraPreferenceMustBeRespected() {
        assertTrue(SkySocialCommand.parse(
            "SKY haceme un reel para Facebook sobre comida sin mostrar mi cara")!!.faceless)
        assertFalse(SkySocialCommand.parse(
            "SKY haceme un reel para Facebook sobre comida, quiero mostrar mi cara")!!.faceless)
    }

    @Test fun shortTextDoesNotQualify() {
        assertNull(SkySocialCommand.parse(""))
        assertNull(SkySocialCommand.parse("Instagram"))
    }
}
