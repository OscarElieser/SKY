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
        assertEquals("ok", SkyMobileProviderPolicy.runSelected(
            "gemini", useGroq = { error("Groq must not run") }, useGemini = { "ok" }))
    }
    @Test fun failedSelectedGroqNeverContactsGemini() {
        val invoked = mutableListOf<String>()
        try {
            SkyMobileProviderPolicy.runSelected(
                route = "groq",
                useGroq = {
                    invoked += "groq"
                    throw IllegalStateException("HTTP 429")
                },
                useGemini = {
                    invoked += "gemini"
                    "would be a hidden fallback"
                })
            fail("The original Groq failure must propagate")
        } catch (error: IllegalStateException) {
            assertEquals("HTTP 429", error.message)
        }
        assertEquals(listOf("groq"), invoked)
    }

    @Test fun failedSelectedGeminiNeverContactsGroq() {
        val invoked = mutableListOf<String>()
        try {
            SkyMobileProviderPolicy.runSelected(
                route = "gemini",
                useGroq = {
                    invoked += "groq"
                    "would be a hidden fallback"
                },
                useGemini = {
                    invoked += "gemini"
                    throw IllegalStateException("network offline")
                })
            fail("The original Gemini failure must propagate")
        } catch (error: IllegalStateException) {
            assertEquals("network offline", error.message)
        }
        assertEquals(listOf("gemini"), invoked)
    }

    @Test fun unselectedRouteCallsNoCloudProvider() {
        val invoked = mutableListOf<String>()
        try {
            SkyMobileProviderPolicy.runSelected(
                route = null,
                useGroq = { invoked += "groq"; "bad" },
                useGemini = { invoked += "gemini"; "bad" })
            fail("Missing route must not contact cloud")
        } catch (_: IllegalStateException) {
            assertTrue(invoked.isEmpty())
        }
    }

}
