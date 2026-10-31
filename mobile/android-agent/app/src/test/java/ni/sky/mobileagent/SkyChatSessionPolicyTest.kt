package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyChatSessionPolicyTest {
    @Test fun newChatStartsAfterLatestPersistedExchange() {
        val cutoff = SkyChatSessionPolicy.newBoundary(41L)
        assertEquals(41L, cutoff)
        assertFalse(SkyChatSessionPolicy.visible(40L, cutoff))
        assertFalse(SkyChatSessionPolicy.visible(41L, cutoff))
        assertTrue(SkyChatSessionPolicy.visible(42L, cutoff))
    }

    @Test fun initialSessionCanDisplayExistingHistory() {
        assertTrue(SkyChatSessionPolicy.visible(1L, 0L))
        assertTrue(SkyChatSessionPolicy.visible(200L, 0L))
        assertEquals(0L, SkyChatSessionPolicy.newBoundary(null))
    }

    @Test fun negativeSavedBoundaryDoesNotHideArchive() {
        assertEquals(0L, SkyChatSessionPolicy.newBoundary(-25L))
        assertTrue(SkyChatSessionPolicy.visible(1L, -12L))
    }
}
