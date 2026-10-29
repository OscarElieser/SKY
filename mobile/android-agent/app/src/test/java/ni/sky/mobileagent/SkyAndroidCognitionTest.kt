package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

/** Pruebas locales: no usa red, micrófono, GPS, APK ni datos personales. */
class SkyAndroidCognitionTest {
    @Test fun classifiesAcademicAndSoftwareWork() {
        assertEquals("docente", SkyAndroidCognition.classify(
            "Diseñame una rúbrica de evaluación para mis estudiantes").role)
        assertEquals("programador", SkyAndroidCognition.classify(
            "Ayudame a depurar mi proyecto Flutter").role)
        assertEquals("investigador", SkyAndroidCognition.classify(
            "Investigación científica con fuentes").role)
    }

    @Test fun recognizesLiveInformationAndAvoidsActionClaims() {
        assertTrue(SkyAndroidCognition.classify(
            "Investiga en internet las últimas noticias").verifyWithSources)
        val command = SkyAndroidCognition.classify("Abre YouTube y reproduce música")
        assertEquals("agente_android", command.role)
        assertTrue(command.actionProposedOnly)
        assertFalse(command.verifyWithSources)
        assertTrue(SkyAndroidCognition.guide("Abre YouTube").contains("No afirmes"))
    }

    @Test fun memoryRecallIsLocalAndExplicit() {
        assertTrue(SkyAndroidCognition.memoryQuestion("SKY, ¿qué recuerdas de mí?"))
        assertTrue(SkyAndroidCognition.memoryQuestion("¿Qué recuerdas sobre Flutter?"))
        assertFalse(SkyAndroidCognition.memoryQuestion("Recuerda que mañana tengo clases"))
        val facts = listOf("- Tengo un proyecto Flutter", "- Mi perro se llama Luna")
        val relevant = SkyAndroidCognition.localMemoryAnswer(
            "¿Qué recuerdas sobre Flutter?", facts)
        assertTrue(relevant.contains("proyecto Flutter"))
        assertFalse(relevant.contains("Mi perro"))
        val generic = SkyAndroidCognition.localMemoryAnswer("¿Qué sabes de mí?", facts)
        assertTrue(generic.contains("Mi perro"))
    }

    @Test fun emptyAndMissingMemoriesDoNotBecomeHallucinations() {
        val none = SkyAndroidCognition.localMemoryAnswer("¿Qué recuerdas de mí?", emptyList())
        assertTrue(none.contains("no hay recuerdos"))
        val notFound = SkyAndroidCognition.localMemoryAnswer(
            "¿Qué recuerdas sobre Excel?", listOf("- Proyecto Flutter"))
        assertTrue(notFound.contains("No encontré"))
    }

    @Test fun historyRecallIsOnlyExplicit() {
        assertTrue(SkyAndroidCognition.historyQuestion(
            "¿Qué hablamos sobre el proyecto BAQUEANO?"))
        assertFalse(SkyAndroidCognition.historyQuestion(
            "Explicame qué es una red neuronal"))
        val context = SkyAndroidCognition.localHistoryAnswer(
            listOf("28/10/2026 · IA neuronal"), searched = true)
        assertTrue(context.contains("28/10/2026"))
        assertTrue(SkyAndroidCognition.localHistoryAnswer(
            emptyList(), searched = true).contains("No encontré"))
    }

    @Test fun promptDoesNotIncludeProfileOrInventActions() {
        val instructions = SkyAndroidCognition.guide(
            "Investiga las novedades de Flutter")
        assertTrue(instructions.contains("fuentes verificables"))
        assertTrue(instructions.contains("español de Nicaragua"))
        assertFalse(instructions.contains("SKY_NEURAL_MEMORY_KEY"))
        assertFalse(instructions.contains("He ejecutado"))
    }

    @Test fun canNormalizeNicaraguanSpanish() {
        assertEquals("que alegria", SkyAndroidCognition.normalize("¡QUÉ alegría!"))
        assertTrue(SkyAndroidCognition.searchTerms(
            "¿Qué hablamos sobre el proyecto BAQUEANO?").contains("baqueano"))
    }

    @Test fun storesOnlyPlausiblePublicHttpsReferences() {
        assertTrue(SkyAndroidKnowledgeSources.publicSourceUrl(
            "https://www.nasa.gov/news/example"))
        assertFalse(SkyAndroidKnowledgeSources.publicSourceUrl(
            "http://www.nasa.gov/insecure"))
        assertFalse(SkyAndroidKnowledgeSources.publicSourceUrl(
            "https://localhost/admin"))
        assertFalse(SkyAndroidKnowledgeSources.publicSourceUrl(
            "https://192.168.1.10/secret"))
        assertFalse(SkyAndroidKnowledgeSources.publicSourceUrl(
            "https://person:pass@example.org/private"))
        assertFalse(SkyAndroidKnowledgeSources.publicSourceUrl(
            "javascript:alert(1)"))
    }

    @Test fun descriptionsDoNotClaimModelTraining() {
        assertTrue(SkyAndroidCognition.description().contains(
            "No entrena pesos neuronales"))
        assertTrue(SkyAndroidCognition.description().contains(
            "no se envían a la nube"))
    }
}
