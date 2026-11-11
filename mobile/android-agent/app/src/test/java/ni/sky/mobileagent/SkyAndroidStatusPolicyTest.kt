package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyAndroidStatusPolicyTest {
    @Test fun historicalPairingIsNotAnOnlineConnection() {
        assertEquals(
            "Funciones locales disponibles · IA generativa sin configurar",
            SkyAndroidStatusPolicy.engineStatus(
                privateApiSelected = false, privateChatConfigured = true,
                externalModelConfigured = false
            )
        )
        assertEquals(
            "API privada configurada · conexión sin verificar",
            SkyAndroidStatusPolicy.engineStatus(true, true, false)
        )
        assertEquals(
            "API privada pendiente · autorización necesaria",
            SkyAndroidStatusPolicy.engineStatus(true, false, true)
        )
        assertEquals(
            "IA externa configurada · conexión sin verificar",
            SkyAndroidStatusPolicy.engineStatus(false, false, true)
        )
    }

    @Test fun voicePresenceNeverClaimsSleepingWhenAttentive() {
        assertEquals("SKY ATENTA · SERVICIO ACTIVO",
            SkyAndroidStatusPolicy.voiceCaption(true, "ATTENTIVE"))
        assertEquals("SKY DORMIDA · DECÍ SKY DESPIERTA",
            SkyAndroidStatusPolicy.voiceCaption(true, "SLEEP_LOCKED"))
        assertEquals("SKY EN ESPERA · DECÍ SKY",
            SkyAndroidStatusPolicy.voiceCaption(true, "WAKE_ONLY"))
        assertTrue(SkyAndroidStatusPolicy.voiceCaption(false, "ATTENTIVE")
            .startsWith("SKY LISTA"))
    }

    @Test fun microphoneStartIsNotProofRecognizerIsReady() {
        assertFalse(SkyAndroidStatusPolicy.recognizerPrepared(
            active = true, startRequested = true,
            readyCallback = false, speechSuspended = false))
        assertFalse(SkyAndroidStatusPolicy.recognizerPrepared(
            active = true, startRequested = true,
            readyCallback = true, speechSuspended = true))
        assertFalse(SkyAndroidStatusPolicy.recognizerPrepared(
            active = false, startRequested = true,
            readyCallback = true, speechSuspended = false))
        assertFalse(SkyAndroidStatusPolicy.recognizerPrepared(
            active = true, startRequested = false,
            readyCallback = true, speechSuspended = false))
        assertTrue(SkyAndroidStatusPolicy.recognizerPrepared(
            active = true, startRequested = true,
            readyCallback = true, speechSuspended = false))
    }

    @Test fun canceledRecognizerCannotChangeStateOrExecuteCommands() {
        assertFalse(SkyAndroidStatusPolicy.acceptRecognitionCallback(
            active = true, listening = true,
            sameEngine = false, speechSuspended = false))
        assertFalse(SkyAndroidStatusPolicy.acceptRecognitionCallback(
            active = true, listening = false,
            sameEngine = true, speechSuspended = false))
        assertFalse(SkyAndroidStatusPolicy.acceptRecognitionCallback(
            active = true, listening = true,
            sameEngine = true, speechSuspended = true))
        assertFalse(SkyAndroidStatusPolicy.acceptRecognitionCallback(
            active = false, listening = true,
            sameEngine = true, speechSuspended = false))
        assertTrue(SkyAndroidStatusPolicy.acceptRecognitionCallback(
            active = true, listening = true,
            sameEngine = true, speechSuspended = false))
    }

}
