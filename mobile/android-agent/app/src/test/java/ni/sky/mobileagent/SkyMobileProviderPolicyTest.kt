package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyMobileProviderPolicyTest {
    @Test fun automaticSelectionUsesOnlyConfiguredRouteAtStart() {
        assertEquals("groq", SkyMobileProviderPolicy.choose(
            "auto", groqConfigured = true, geminiConfigured = true,
            explicitGemini = false, verifiedWebRequired = false))
        assertEquals("gemini", SkyMobileProviderPolicy.choose(
            "auto", groqConfigured = false, geminiConfigured = true,
            explicitGemini = false, verifiedWebRequired = false))
        assertNull(SkyMobileProviderPolicy.choose(
            "auto", groqConfigured = false, geminiConfigured = false,
            explicitGemini = false, verifiedWebRequired = false))
    }

    @Test fun explicitlySelectedProviderCannotSilentlyUseAnotherKey() {
        assertNull(SkyMobileProviderPolicy.choose(
            "groq", groqConfigured = false, geminiConfigured = true,
            explicitGemini = false, verifiedWebRequired = false))
        assertNull(SkyMobileProviderPolicy.choose(
            "gemini", groqConfigured = true, geminiConfigured = false,
            explicitGemini = false, verifiedWebRequired = false))
        assertEquals("gemini", SkyMobileProviderPolicy.choose(
            "gemini", groqConfigured = true, geminiConfigured = true,
            explicitGemini = false, verifiedWebRequired = false))
        assertEquals("groq", SkyMobileProviderPolicy.choose(
            "groq", groqConfigured = true, geminiConfigured = true,
            explicitGemini = false, verifiedWebRequired = false))
    }

    @Test fun explicitGeminiAndVerifiedSourcesNeverUseUnverifiedGroq() {
        assertEquals("gemini", SkyMobileProviderPolicy.choose(
            "groq", groqConfigured = true, geminiConfigured = true,
            explicitGemini = true, verifiedWebRequired = false))
        assertEquals("gemini", SkyMobileProviderPolicy.choose(
            "groq", groqConfigured = true, geminiConfigured = true,
            explicitGemini = false, verifiedWebRequired = true))
        assertNull(SkyMobileProviderPolicy.choose(
            "groq", groqConfigured = true, geminiConfigured = false,
            explicitGemini = false, verifiedWebRequired = true))
        assertNull(SkyMobileProviderPolicy.choose(
            "auto", groqConfigured = true, geminiConfigured = false,
            explicitGemini = true, verifiedWebRequired = false))
    }

    @Test fun invalidPreferenceIsSafeAndNetworkFallbackIsAlwaysRejected() {
        assertEquals("auto", SkyMobileProviderPolicy.preference("other"))
        assertEquals("auto", SkyMobileProviderPolicy.preference(null))
        assertEquals("groq", SkyMobileProviderPolicy.preference("groq"))
        assertFalse(SkyMobileProviderPolicy.allowRetryOnAnotherProvider())
    }
}
