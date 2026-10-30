package ni.sky.mobileagent

import android.content.Context
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Real Android SharedPreferences and in-process routing tests.
 * No microphone or biometric ownership is claimed here.
 */
@RunWith(AndroidJUnit4::class)
class SkyVoiceSessionRuntimeTest {
    @Test fun explicitSleepLockPersistsAndCannotWakeWithGenericSky() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val prefs = context.getSharedPreferences("sky_voice_settings", Context.MODE_PRIVATE)
        val old = prefs.getString("sky_presence_mode", null)
        try {
            assertTrue(prefs.edit().putString("sky_presence_mode", "SLEEP_LOCKED").commit())
            val reopened = context.getSharedPreferences("sky_voice_settings", Context.MODE_PRIVATE)
            val mode = SkyVoicePresence.Mode.valueOf(
                reopened.getString("sky_presence_mode", "WAKE_ONLY")!!)
            assertEquals(SkyVoicePresence.Mode.SLEEP_LOCKED, mode)
            assertFalse(SkyVoicePresence.permits(mode, "SKY"))
            assertFalse(SkyVoicePresence.permits(mode, "SKY abre WhatsApp"))
            assertFalse(SkyVoicePresence.permits(mode, "SKY confirmo"))
            assertTrue(SkyVoicePresence.permits(mode, "SKY despierta"))
        } finally {
            val edit = prefs.edit()
            if (old == null) edit.remove("sky_presence_mode")
            else edit.putString("sky_presence_mode", old)
            edit.commit()
        }
    }

    @Test fun lateRecognizerAndTtsCallbacksHaveNoAuthority() {
        val recognizer = SkyRecognitionEpoch()
        val first = recognizer.begin()
        recognizer.invalidate()
        val next = recognizer.begin()
        assertFalse(recognizer.accepts(first, true))
        assertTrue(recognizer.accepts(next, true))

        val tts = SkySpeechTurnGuard()
        val spoken = tts.begin()
        tts.invalidate()
        assertFalse(tts.finish(spoken))
    }
}
