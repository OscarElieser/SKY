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
    @Test fun localOllamaRemainsDefaultWhenNoOptionalServerProviderSelected() {
        assertEquals("ollama", SkyOwnApiRoutingPolicy.chosenProvider(null))
        assertEquals("ollama", SkyOwnApiRoutingPolicy.chosenProvider("unknown"))
        assertTrue("ollama" in SkyOwnApiRoutingPolicy.SERVER_PROVIDERS)
    }

    @Test fun optionalServerProvidersRequireBothPerMessagePermissions() {
        for (name in listOf("gemini", "openrouter", "mistral", "groq", "cloudflare")) {
            assertTrue(SkyOwnApiRoutingPolicy.useExternalViaSkyApi(
                true, true, name, false, false, true, true, 800))
            assertFalse(SkyOwnApiRoutingPolicy.useExternalViaSkyApi(
                true, true, name, false, false, false, true, 800))
            assertFalse(SkyOwnApiRoutingPolicy.useExternalViaSkyApi(
                true, true, name, false, false, true, false, 800))
            assertFalse(SkyOwnApiRoutingPolicy.useExternalViaSkyApi(
                false, true, name, false, false, true, true, 800))
            assertFalse(SkyOwnApiRoutingPolicy.useExternalViaSkyApi(
                true, false, name, false, false, true, true, 800))
        }
    }

    @Test fun noHiddenFallbackToCloudOrUnverifiedSearch() {
        assertFalse(SkyOwnApiRoutingPolicy.useExternalViaSkyApi(
            true, true, "ollama", false, false, true, true, 100))
        assertFalse(SkyOwnApiRoutingPolicy.useExternalViaSkyApi(
            true, true, "external-untrusted", false, false, true, true, 100))
        assertFalse(SkyOwnApiRoutingPolicy.useExternalViaSkyApi(
            true, true, "openrouter", true, false, true, true, 100))
        assertFalse(SkyOwnApiRoutingPolicy.useExternalViaSkyApi(
            true, true, "cloudflare", false, true, true, true, 100))
        assertFalse(SkyOwnApiRoutingPolicy.useExternalViaSkyApi(
            true, true, "groq", false, false, true, true, 4001))
    }

}
