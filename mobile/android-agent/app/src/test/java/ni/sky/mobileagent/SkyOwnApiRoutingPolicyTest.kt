package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyOwnApiRoutingPolicyTest {
    @Test fun ownerEnabledPairedApiUsesServerWithoutProviderQuota() {
        assertTrue(SkyOwnApiRoutingPolicy.usePrivateApi(
            optedIn = true, pairedChatToken = true,
            explicitGeminiMode = false, verifiedWebRequired = false,
            promptChars = 500))
    }

    @Test fun noSilentActivationOrSendingWhenNotPaired() {
        assertFalse(SkyOwnApiRoutingPolicy.usePrivateApi(
            optedIn = false, pairedChatToken = true,
            explicitGeminiMode = false, verifiedWebRequired = false,
            promptChars = 150))
        assertFalse(SkyOwnApiRoutingPolicy.usePrivateApi(
            optedIn = true, pairedChatToken = false,
            explicitGeminiMode = false, verifiedWebRequired = false,
            promptChars = 150))
        assertTrue(SkyOwnApiRoutingPolicy.canPromptForSetup(true, false))
    }

    @Test fun providerAndEvidenceIntentAreNotBypassed() {
        assertFalse(SkyOwnApiRoutingPolicy.usePrivateApi(
            true, true, true, false, 300))
        assertFalse(SkyOwnApiRoutingPolicy.usePrivateApi(
            true, true, false, true, 300))
    }

    @Test fun serverTextLimitNeverSilentlyTruncates() {
        assertTrue(SkyOwnApiRoutingPolicy.usePrivateApi(
            true, true, false, false, 4000))
        assertFalse(SkyOwnApiRoutingPolicy.usePrivateApi(
            true, true, false, false, 4001))
        assertFalse(SkyOwnApiRoutingPolicy.usePrivateApi(
            true, true, false, false, 0))
    }
}
