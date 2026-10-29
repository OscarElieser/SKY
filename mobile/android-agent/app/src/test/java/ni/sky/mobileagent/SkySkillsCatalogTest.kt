package ni.sky.mobileagent

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SkySkillsCatalogTest {
    @Test fun keepsCapabilityDescriptionsHonest() {
        // Evitar un número desactualizado cuando se añaden capacidades reales:
        // la regresión debe comprobar cada habilidad, sus límites y nombres únicos.
        assertEquals(11, SkySkillsCatalog.skills.size)
        assertEquals(SkySkillsCatalog.skills.size,
            SkySkillsCatalog.skills.map { it.name }.toSet().size)
        assertTrue(SkySkillsCatalog.skills.any { it.name.contains("Canva") &&
            it.capability.contains("sin conexión con Canva") })
        assertTrue(SkySkillsCatalog.skills.any { it.name.contains("Gamma") &&
            it.capability.contains("sin edición en Gamma") })
        assertTrue(SkySkillsCatalog.skills.any { it.name == "Excel editable" &&
            it.capability.contains("XLSX") })
        assertTrue(SkySkillsCatalog.skills.any { it.name == "Imagen IA real" &&
            it.capability.contains("clave y cuota necesarias") })
        assertTrue(SkySkillsCatalog.skills.any { it.name == "Multimedia y video" &&
            it.capability.contains("pendiente") })
    }

    @Test fun routingMentionsUnverifiedExports() {
        val prompt = SkySkillsCatalog.instructionFor("Crea una presentación de diapositivas")
        assertTrue(prompt.contains("no finjas"))
        assertFalse(SkySkillsCatalog.instructionFor("Buenos días").isNotBlank())
    }
}
