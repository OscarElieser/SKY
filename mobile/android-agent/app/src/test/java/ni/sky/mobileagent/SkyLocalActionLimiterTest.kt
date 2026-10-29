package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyLocalActionLimiterTest {
    @Test fun preventsDuplicateCommandsInsideWindowAndAllowsAfterward() {
        var clock = 1000L
        val limiter = SkyLocalActionLimiter(nowMs = { clock })
        assertTrue(limiter.allow("launch:com.google.android.youtube"))
        clock += 100L
        assertFalse(limiter.allow("launch:com.google.android.youtube"))
        clock += 1500L
        assertTrue(limiter.allow("launch:com.google.android.youtube"))
    }

    @Test fun blocksBurstAndRecoversAfterMinute() {
        var clock = 5L
        val limiter = SkyLocalActionLimiter(nowMs = { clock }, maxPerMinute = 3)
        assertTrue(limiter.allow("launch:first"))
        assertTrue(limiter.allow("launch:second"))
        assertTrue(limiter.allow("launch:third"))
        assertFalse(limiter.allow("launch:fourth"))
        clock += 60_000L
        assertTrue(limiter.allow("launch:fourth"))
    }

    @Test fun rejectsBlankAndOversizedActions() {
        val limiter = SkyLocalActionLimiter()
        assertFalse(limiter.allow(""))
        assertFalse(limiter.allow(" ".repeat(200)))
        assertFalse(limiter.allow("a".repeat(181)))
    }

    @Test fun refusesAnotherBurstWithoutMutatingPreviousConsent() {
        val limiter = SkyLocalActionLimiter(maxPerMinute = 1)
        assertTrue(limiter.allow("launch:app1"))
        assertFalse(limiter.allow("launch:app2"))
        // Las autorizaciones persistentes se administran en SkySupervisedControl,
        // nunca por este limitador.
    }
}
