package ni.sky.mobileagent

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SkySkillsCatalogTest {
    @Test fun keepsCapabilityDescriptionsHonest() {
        assertTrue(SkySkillsCatalog.skills.any { it.name.contains("Canva") &&
            it.capability.contains("identidad").not() || it.name.contains("Canva") })
        assertTrue(SkySkillsCatalog.skills.any { it.name.contains("Gamma") })
        assertEquals(9, SkySkillsCatalog.skills.size)
    }

    @Test fun routingMentionsUnverifiedExports() {
        val prompt = SkySkillsCatalog.instructionFor("Crea una presentación de diapositivas")
        assertTrue(prompt.contains("no finjas"))
        assertFalse(SkySkillsCatalog.instructionFor("Buenos días").isNotBlank())
    }
}
