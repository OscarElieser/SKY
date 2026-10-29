package ni.sky.mobileagent

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class SkyLongTermMemoryTest {
    private val facts = listOf(
        SkyLongTermMemory.Fact(1,"Prefiero ejemplos de docencia y rúbricas",100L,"owner_explicit"),
        SkyLongTermMemory.Fact(2,"Estoy desarrollando una aplicación Android",200L,"owner_explicit"),
        SkyLongTermMemory.Fact(3,"Mis clases de docencia usan prácticas con estudiantes",300L,"owner_explicit")
    )
    @Test fun accentsAndStopwordsDoNotBreakRetrieval() {
        assertEquals(listOf(3L, 1L), SkyLongTermMemory.rank(
            "¿Qué recuerdas sobre docencia?",facts).map { it.id })
    }
    @Test fun unrelatedMemoriesAreNotSent() {
        assertTrue(SkyLongTermMemory.rank("meteoritos neptuno",facts).isEmpty())
    }
    @Test fun retrievalIsBounded() {
        assertEquals(1,SkyLongTermMemory.rank("android",facts,1).size)
    }
}
