package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkySocialProfileDataTest {
    @Test fun buildOnlySafePublicProfileLinks() {
        val ig = SkySocialProfileData.Profile("Instagram", "@chamorro.oscar")
        assertNull(SkySocialProfileData.validate(ig))
        assertEquals("https://www.instagram.com/chamorro.oscar/",
            SkySocialProfileData.publicUrl(ig))
        assertEquals("https://www.tiktok.com/@oscarelieser",
            SkySocialProfileData.publicUrl(
                SkySocialProfileData.Profile("TikTok", "oscarelieser")))
        assertEquals("https://www.youtube.com/@oscarelieser",
            SkySocialProfileData.publicUrl(
                SkySocialProfileData.Profile("YouTube", "@oscarelieser")))
        assertEquals("https://x.com/OSCARELIESER01",
            SkySocialProfileData.publicUrl(
                SkySocialProfileData.Profile("X", "OSCARELIESER01")))
    }

    @Test fun facebookDisplayNameDoesNotFakeProfileUrl() {
        val p = SkySocialProfileData.Profile("Facebook", "", "Oscar Elieser")
        assertNull(SkySocialProfileData.validate(p))
        assertNull(SkySocialProfileData.publicUrl(p))
    }

    @Test fun privateValuesAndDangerousUrisAreRejected() {
        assertNotNull(SkySocialProfileData.validate(
            SkySocialProfileData.Profile("Instagram", "test@example.com")))
        assertNotNull(SkySocialProfileData.validate(
            SkySocialProfileData.Profile("Threads", "https://evil.example/")))
        assertNotNull(SkySocialProfileData.validate(
            SkySocialProfileData.Profile("TikTok", "hello/a")))
        assertNotNull(SkySocialProfileData.validate(
            SkySocialProfileData.Profile("WhatsApp", "contacto")))
    }

    @Test fun noCredentialOrOAuthConnectionIsImplied() {
        val empty = SkySocialProfileData.Profile("YouTube", "")
        assertNotNull(SkySocialProfileData.validate(empty))
        assertNull(SkySocialProfileData.publicUrl(empty))
    }
}
