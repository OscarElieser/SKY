package ni.sky.mobileagent

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.concurrent.CancellationException

class SkyFileCancelTokenTest {
    @Test fun cancellationIsExplicitAndIdempotent() {
        val token = SkyGeminiFiles.CancelToken()
        assertFalse(token.isCancelled())
        token.check()
        token.cancel()
        token.cancel()
        assertTrue(token.isCancelled())
        try {
            token.check()
            throw AssertionError("Se esperaba CancellationException")
        } catch (_: CancellationException) {
            // La cancelación del usuario se propaga sin perder su selección.
        }
    }
}
