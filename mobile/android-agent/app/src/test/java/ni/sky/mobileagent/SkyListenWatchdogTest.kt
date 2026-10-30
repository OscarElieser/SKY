package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyListenWatchdogTest {
    @Test fun recoveryRequiresActiveStalledRecognizer() {
        val threshold = SkyListenWatchdog.MAX_CYCLE_MS
        assertFalse(SkyListenWatchdog.needsRecovery(true, true, false, threshold - 1))
        assertTrue(SkyListenWatchdog.needsRecovery(true, true, false, threshold))
        assertTrue(SkyListenWatchdog.needsRecovery(true, true, false, threshold + 10000))
    }

    @Test fun neverRestartsMicrophoneWhenOffOrPausedForSpeech() {
        val elapsed = SkyListenWatchdog.MAX_CYCLE_MS * 2
        assertFalse(SkyListenWatchdog.needsRecovery(false, true, false, elapsed))
        assertFalse(SkyListenWatchdog.needsRecovery(true, false, false, elapsed))
        assertFalse(SkyListenWatchdog.needsRecovery(true, true, true, elapsed))
    }
}
