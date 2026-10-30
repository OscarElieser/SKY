package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyExpertRolesTest {
    @Test fun registryHasAllIndependentFamilies() {
        assertEquals(33, SkyExpertRoles.roles.size)
        assertEquals((1..33).toList(), SkyExpertRoles.roles.map { it.id })
    }
    @Test fun detectsRequestedDomainsWithoutButtons() {
        assertEquals(10, SkyExpertRoles.detect("analiza una radiografía").first().id)
        assertEquals(2, SkyExpertRoles.detect("ayuda con Flutter y ciberseguridad").first().id)
        assertEquals(25, SkyExpertRoles.detect("criptografía post cuántica").first().id)
        assertEquals(33, SkyExpertRoles.detect("estilometría forense").first().id)
    }
    @Test fun doesNotImplyPhysicalControlOrGrantAnyPermissions() {
        assertTrue(SkyExpertRoles.guidance("control de brazo robótico")
            .contains("autorización"))
        assertEquals("", SkyExpertRoles.guidance("Hola SKY"))
    }
}
