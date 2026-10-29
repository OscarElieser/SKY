package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyVoicePresenceTest {
    @Test fun sleepIsPersistentPolicyNotAVisualEmotionTimer() {
        assertEquals(SkyVoicePresence.Request.SLEEP,
            SkyVoicePresence.request("SKY duerme"))
        assertEquals(SkyVoicePresence.Request.SLEEP,
            SkyVoicePresence.request("SKY dormí"))
        assertFalse(SkyVoicePresence.permits(SkyVoicePresence.Mode.SLEEP_LOCKED,
            "SKY abre YouTube"))
        assertFalse(SkyVoicePresence.permits(SkyVoicePresence.Mode.SLEEP_LOCKED,
            "SKY"))
        assertTrue(SkyVoicePresence.permits(SkyVoicePresence.Mode.SLEEP_LOCKED,
            "SKY despierta"))
    }

    @Test fun attentiveInstructionsRequireExplicitSkyAndDoNotAuthorizeIdentity() {
        assertEquals(SkyVoicePresence.Request.ATTEND,
            SkyVoicePresence.request("SKY estate pendiente a mis orientaciones"))
        assertEquals(SkyVoicePresence.Request.ATTEND,
            SkyVoicePresence.request("SKY escucha y ejecuta"))
        assertEquals(SkyVoicePresence.Request.WAKE,
            SkyVoicePresence.request("SKY despierta"))
        assertEquals(SkyVoicePresence.Request.CONFIRM,
            SkyVoicePresence.request("SKY confirmo"))
        assertEquals(SkyVoicePresence.Request.CANCEL,
            SkyVoicePresence.request("SKY cancela"))
        assertEquals(SkyVoicePresence.Request.NONE,
            SkyVoicePresence.request("Alguien en la televisión confirmó la orden"))
        assertEquals(SkyVoicePresence.Request.NONE,
            SkyVoicePresence.request("Un video dice que SKY escucha y ejecuta"))
        assertEquals(SkyVoicePresence.Request.NONE,
            SkyVoicePresence.request("Quiero hablar sobre sueños y descansar"))
    }
}
