package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

/** No SpeechRecognizer or microphone is required for deterministic lifecycle tests. */
class SkyRecognitionEpochTest {
    @Test fun lateResultFromCancelledRecognizerNeverReplacesNewCycle() {
        val guard = SkyRecognitionEpoch()
        val first = guard.begin()
        assertTrue(guard.accepts(first, true))
        guard.invalidate() // cancel/destroy first listener
        assertFalse(guard.accepts(first, true))
        val second = guard.begin()
        assertFalse(guard.accepts(first, true))
        assertTrue(guard.accepts(second, true))
    }

    @Test fun staleErrorAfterRearmCannotChangeCurrentSession() {
        val guard = SkyRecognitionEpoch()
        val old = guard.begin()
        guard.invalidate()
        val next = guard.begin()
        assertFalse(guard.accepts(old, true))
        assertTrue(guard.accepts(next, true))
        assertFalse(guard.accepts(next, false))
    }

    @Test fun stoppingAndRestartingTheServiceRetiresAllPriorCallbacks() {
        val guard = SkyRecognitionEpoch()
        val first = guard.begin()
        guard.invalidate()
        guard.invalidate()
        val restarted = guard.begin()
        assertNotEquals(first, restarted)
        assertFalse(guard.accepts(first, true))
        assertTrue(guard.accepts(restarted, true))
        guard.invalidate()
        assertFalse(guard.accepts(restarted, true))
    }
}
