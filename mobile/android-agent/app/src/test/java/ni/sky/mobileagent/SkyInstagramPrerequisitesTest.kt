package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyInstagramPrerequisitesTest {
    @Test fun personalInstagramCannotAuthorizeProfessionalAPI() {
        assertFalse(SkyInstagramPrerequisites.eligible(SkyInstagramPrerequisites.Type.PERSONAL))
        assertFalse(SkyInstagramPrerequisites.eligible(SkyInstagramPrerequisites.Type.UNKNOWN))
        assertTrue(SkyInstagramPrerequisites.checklist(
            SkyInstagramPrerequisites.Type.PERSONAL, false, false)
            .contains("personales"))
    }

    @Test fun creatorIsEligibleButNotConnectedWithoutMetaAndBackend() {
        assertTrue(SkyInstagramPrerequisites.eligible(SkyInstagramPrerequisites.Type.CREATOR))
        assertTrue(SkyInstagramPrerequisites.checklist(
            SkyInstagramPrerequisites.Type.CREATOR, false, false).contains("Meta"))
        assertTrue(SkyInstagramPrerequisites.checklist(
            SkyInstagramPrerequisites.Type.CREATOR, true, false).contains("HTTPS"))
        assertTrue(SkyInstagramPrerequisites.checklist(
            SkyInstagramPrerequisites.Type.CREATOR, true, true).contains("falta"))
    }

    @Test fun minimalScopesAndOfficialDevelopersLink() {
        assertTrue(SkyInstagramPrerequisites.analyticsScopes.contains(
            "instagram_business_manage_insights"))
        assertTrue(SkyInstagramPrerequisites.publishingScopes.contains(
            "instagram_business_content_publish"))
        assertEquals("https://developers.facebook.com/apps/",
            SkyInstagramPrerequisites.META_DEVELOPERS)
    }
}
