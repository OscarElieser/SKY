package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

/** Pure regression tests; media loudness cannot be measured on a CI emulator. */
class SkyMusicAudioCheckTest {
    @Test fun zeroMultimediaLevelIsDetectedWithoutAssumingPlaybackIsAudible() {
        val state = SkyMusicAudioCheck.Snapshot(0, 15, false, false)
        assertTrue(state.silentBySystemSettings)
        assertEquals(SkyMusicAudioRules.State.ZERO_VOLUME, state.state)
        assertTrue(state.guidance().contains("cero"))
        assertTrue(state.evidence().contains("audio audible no medido"))
    }

    @Test fun mutedFlagWinsEvenIfStreamLevelIsNonzero() {
        val state = SkyMusicAudioCheck.Snapshot(6, 15, true, false)
        assertTrue(state.silentBySystemSettings)
        assertEquals(SkyMusicAudioRules.State.MUTED, state.state)
        assertTrue(state.guidance().contains("silenciado"))
    }

    @Test fun positiveVolumeDoesNotProveSpeakerOutput() {
        val state = SkyMusicAudioCheck.Snapshot(8, 15, false, false)
        assertFalse(state.silentBySystemSettings)
        assertEquals(SkyMusicAudioRules.State.LEVEL_PRESENT, state.state)
        assertTrue(state.guidance().contains("Bluetooth"))
        assertTrue(state.evidence().contains("audio audible no medido"))
    }

    @Test fun unavailableAudioManagerIsNotLabeledAsSilence() {
        val state = SkyMusicAudioCheck.Snapshot(null, null, null, null)
        assertFalse(state.silentBySystemSettings)
        assertEquals(SkyMusicAudioRules.State.UNAVAILABLE, state.state)
        assertTrue(state.guidance().contains("No pude"))
    }
}
