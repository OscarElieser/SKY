package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyAcademicResearchTest {
    @Test fun handlesExplicitAcademicQueries() {
        assertTrue(SkyAcademicResearch.explicit("SKY busca artículos científicos sobre IA educativa"))
        assertTrue(SkyAcademicResearch.explicit("busca papers sobre atención causal"))
        assertEquals("aprendizaje automático",
            SkyAcademicResearch.term("SKY, busca investigaciones sobre aprendizaje automático"))
        assertFalse(SkyAcademicResearch.explicit("crea una tesis"))
        assertFalse(SkyAcademicResearch.explicit("noticias de hoy"))
    }
    @Test fun refusesSecretsInPublicSearch() {
        assertThrows(IllegalArgumentException::class.java) {
            SkyAcademicResearch.term("busca papers sobre mi contraseña privada")
        }
    }
}
