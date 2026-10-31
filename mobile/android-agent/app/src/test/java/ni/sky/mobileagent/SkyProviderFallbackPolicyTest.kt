package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyProviderFallbackPolicyTest {
    @Test fun normalTextCanUseOnlyTheAlreadyAuthorizedGroqProvider() {
        assertTrue(SkyProviderFallbackPolicy.canUseGroq(true, false, false, 2200))
        assertFalse(SkyProviderFallbackPolicy.canUseGroq(false, false, false, 2200))
    }

    @Test fun neverDowngradeExplicitGeminiOrLiveSourceVerification() {
        assertFalse(SkyProviderFallbackPolicy.canUseGroq(true, true, false, 1200))
        assertFalse(SkyProviderFallbackPolicy.canUseGroq(true, false, true, 1200))
    }

    @Test fun doNotSilentlyTruncateLongPromptDuringFallback() {
        assertTrue(SkyProviderFallbackPolicy.canUseGroq(true, false, false, 4000))
        assertFalse(SkyProviderFallbackPolicy.canUseGroq(true, false, false, 4001))
        assertFalse(SkyProviderFallbackPolicy.canUseGroq(true, false, false, 0))
    }
}
