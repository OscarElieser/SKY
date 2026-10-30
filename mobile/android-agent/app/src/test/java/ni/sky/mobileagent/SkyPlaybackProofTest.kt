package ni.sky.mobileagent

import android.media.session.PlaybackState
import org.junit.Assert.*
import org.junit.Test

/** Pure offline tests: no notifications, accounts, microphone or network. */
class SkyPlaybackProofTest {
    @Test fun onlyExactAuthorizedPlayerAndPlayingStateCountAsVerification() {
        val spotify = "com.spotify.music"
        assertTrue(SkyPlaybackProofRules.verified(
            "November Rain", "November Rain", spotify, spotify, PlaybackState.STATE_PLAYING))
        assertFalse(SkyPlaybackProofRules.verified(
            "November Rain", "November Rain", spotify, spotify, PlaybackState.STATE_PAUSED))
        assertFalse(SkyPlaybackProofRules.verified(
            "November Rain", "November Rain", spotify, "com.google.android.youtube",
            PlaybackState.STATE_PLAYING))
        assertFalse(SkyPlaybackProofRules.verified(
            "November Rain", "November Rain", "com.unknown.app", "com.unknown.app",
            PlaybackState.STATE_PLAYING))
    }

    @Test fun noRandomSongOrMisleadingPartialMatches() {
        assertFalse(SkyPlaybackProofRules.sameTrack("November Rain", "November"))
        assertFalse(SkyPlaybackProofRules.sameTrack("November Rain", "Sweet Child O Mine"))
        assertFalse(SkyPlaybackProofRules.sameTrack("A", "A"))
        assertTrue(SkyPlaybackProofRules.sameTrack("November Rain de Guns N Roses",
            "November Rain"))
        assertTrue(SkyPlaybackProofRules.sameTrack("Canción Bonita", "Cancion Bonita"))
        assertFalse(SkyPlaybackProofRules.sameTrack("Imagine Dragons", "Imagine"))
    }

    @Test fun neverReadsOtherPackages() {
        assertEquals(3, SkyPlaybackProofRules.players.size)
        assertFalse("com.whatsapp" in SkyPlaybackProofRules.players)
        assertFalse("com.google.android.gm" in SkyPlaybackProofRules.players)
    }
}
