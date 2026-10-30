package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

/** TTS callbacks can arrive late, out of order or twice. */
class SkySpeechTurnGuardTest {
    @Test fun oldReplyNeverResumesMicrophoneDuringNewReply() {
        val gate = SkySpeechTurnGuard()
        val old = gate.begin()
        val current = gate.begin()
        assertNotEquals(old, current)
        assertFalse(gate.finish(old))
        assertTrue(gate.finish(current))
        assertFalse(gate.finish(current)) // duplicate callback must not resume again
    }

    @Test fun externalSpeechPauseInvalidatesPriorCallbacks() {
        val gate = SkySpeechTurnGuard()
        val first = gate.begin()
        gate.invalidate()
        assertFalse(gate.finish(first))
        val next = gate.begin()
        assertFalse(gate.finish(first))
        assertTrue(gate.finish(next))
    }

    @Test fun invalidOrMissingTtsIdNeverEndsCurrentSpeech() {
        val gate = SkySpeechTurnGuard()
        val active = gate.begin()
        assertFalse(gate.finish(null))
        assertFalse(gate.finish("sky-service-999999"))
        assertTrue(gate.finish(active))
    }
}
