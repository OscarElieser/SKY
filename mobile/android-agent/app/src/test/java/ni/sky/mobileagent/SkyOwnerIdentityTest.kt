package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyOwnerIdentityTest {
    @Test fun recognizesDirectIdentityQuestions() {
        assertTrue(SkyOwnerIdentity.isQuestion("SKY, ¿quién soy yo?"))
        assertTrue(SkyOwnerIdentity.isQuestion("Cómo me llamo"))
        assertTrue(SkyOwnerIdentity.isQuestion("¿A qué me dedico?"))
        assertFalse(SkyOwnerIdentity.isQuestion("¿Quién es Albert Einstein?"))
    }
    @Test fun ownerIdentityNeverInvented() {
        assertTrue(SkyOwnerIdentity.summarize("").contains("Todavía no tengo"))
        assertTrue(SkyOwnerIdentity.summarize("- Me llamo Oscar\n- Soy docente")
            .contains("Soy docente"))
        assertFalse(SkyOwnerIdentity.summarize("").contains("Oscar"))
    }
    @Test fun selfFactsRequireExplicitPhrase() {
        assertTrue(SkyOwnerIdentity.isExplicitPersonalFact("Me llamo Oscar"))
        assertTrue(SkyOwnerIdentity.isExplicitPersonalFact("Soy docente"))
        assertFalse(SkyOwnerIdentity.isExplicitPersonalFact("La tierra gira"))
    }
    @Test fun wikipediaSearchRequiresPublicFactualText() {
        assertTrue(SkyPublicResearch.explicit("SKY busca en Wikipedia redes neuronales"))
        assertTrue(SkyPublicResearch.encyclopedic("Qué es un transformador"))
        assertFalse(SkyPublicResearch.encyclopedic("Qué hora es en Managua"))
        assertEquals("redes neuronales",
            SkyPublicResearch.term("SKY, busca en Wikipedia redes neuronales"))
        assertThrows(IllegalArgumentException::class.java) {
            SkyPublicResearch.term("busca en wikipedia mi contraseña secreta")
        }
    }
}
