package ni.sky.mobileagent

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SkyContextPlannerTest {
    private val turns = listOf(
        SkyContextPlanner.Turn(1, "Rúbrica de docencia",
            "Criterios y niveles de evaluación", "Gemini · chat"),
        SkyContextPlanner.Turn(2, "Abre YouTube", "Lo abrí", "Gemini · chat"),
        SkyContextPlanner.Turn(3, "Recuerda que vivo en Managua",
            "Anotado", "Gemini · chat"),
        SkyContextPlanner.Turn(4, "Explica clases",
            "Las clases tienen objetivos", "Groq · Llama"),
        SkyContextPlanner.Turn(5, "Mi API Key",
            "api_key=privada", "Gemini · chat"),
        SkyContextPlanner.Turn(6, "¿Qué es un esquema?",
            "Un organizador gráfico", "Gemini · chat")
    )
    @Test fun noConsentMeansZeroArchivedData() {
        assertTrue(SkyContextPlanner.select("clases",turns,false,12,10000).isEmpty())
    }
    @Test fun excludesMemoryActionsAndSecrets() {
        val ids=SkyContextPlanner.select("rúbrica",turns,true,10,10000).map { it.id }
        assertEquals(listOf(1L,4L,6L), ids)
    }
    @Test fun olderRelevantTurnSurvivesRecentTail() {
        val more=turns+(7L..17L).map { n ->
            SkyContextPlanner.Turn(n,"Tema $n","Respuesta $n","Gemini")
        }
        val ids=SkyContextPlanner.select("Necesito rúbrica de docencia",
            more,true,7,12000).map{it.id}
        assertTrue(ids.contains(1L))
        assertEquals(ids.sorted(),ids)
    }
    @Test fun limitsPairCountAndContextSize() {
        val many=(1L..12L).map { n ->
            SkyContextPlanner.Turn(n,"Asunto $n",
                "A".repeat(3000),"Gemini")
        }
        val rows=SkyContextPlanner.select("Asunto",many,true,5,4000)
        assertTrue(rows.size<=5)
        assertTrue(rows.sumOf{it.question.length+it.answer.length}<=4000)
        assertTrue(rows.all{it.answer.length<=1800})
    }
    @Test fun neverUsesFileUploadsAsConversationMemory() {
        assertFalse(SkyContextPlanner.eligible(SkyContextPlanner.Turn(9,
            "Revisa imagen","Descripción privada","Gemini · archivo visual")))
    }
}
