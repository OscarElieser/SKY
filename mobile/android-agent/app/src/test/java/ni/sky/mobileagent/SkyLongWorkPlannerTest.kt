package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyLongWorkPlannerTest {
    @Test fun explicitAcademicPlanCreatesRealMarkdownTemplate() {
        val plan = SkyLongWorkPlanner.prepare(
            "SKY, planifica una tesis sobre inteligencia artificial educativa")
        assertNotNull(plan)
        assertEquals(SkyLongWorkPlanner.Kind.TESIS, plan!!.kind)
        assertEquals("inteligencia artificial educativa", plan.topic)
        assertTrue(plan.markdown.startsWith("# Plan de trabajo SKY IA"))
        assertTrue(plan.markdown.contains("## Control de calidad"))
        assertTrue(plan.markdown.contains("Referencias verificadas"))
        assertTrue(plan.markdown.contains("- [ ]"))
    }

    @Test fun researchAndProgrammingPlansHaveDistinctSections() {
        val research = SkyLongWorkPlanner.prepare(
            "Prepara un plan para investigación sobre hábitos de lectura escolar")
        val code = SkyLongWorkPlanner.prepare(
            "Crea un plan para proyecto de programación de una aplicación educativa")
        assertEquals(SkyLongWorkPlanner.Kind.INVESTIGACION, research?.kind)
        assertEquals(SkyLongWorkPlanner.Kind.PROGRAMACION, code?.kind)
        assertTrue(code!!.markdown.contains("Pruebas unitarias"))
        assertTrue(research!!.markdown.contains("Contraste de fuentes"))
    }

    @Test fun neverInterceptActualThesisOrCodeGeneration() {
        assertNull(SkyLongWorkPlanner.prepare(
            "Redacta una tesis sobre inteligencia artificial educativa"))
        assertNull(SkyLongWorkPlanner.prepare(
            "Implementa un programa de inventario en Kotlin"))
        assertNull(SkyLongWorkPlanner.prepare(
            "Planifica una tesis sobre " + "x".repeat(1000)))
        assertNull(SkyLongWorkPlanner.prepare("hola"))
    }

    @Test fun generatedPlanDoesNotClaimActualResearchOrCompilation() {
        val plan = SkyLongWorkPlanner.prepare(
            "Planifica una tesis sobre didáctica y aprendizaje")!!
        assertTrue(plan.markdown.contains("no un trabajo final"))
        assertTrue(plan.markdown.contains("no inventar", ignoreCase = true))
        assertFalse(plan.markdown.contains("se ejecutó el código"))
    }
}
