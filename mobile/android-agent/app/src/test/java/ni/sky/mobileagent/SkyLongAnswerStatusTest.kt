package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyLongAnswerStatusTest {
    @Test fun completeAnswerIsKeptExactly() {
        assertEquals("Cálculo terminado", SkyLongAnswerStatus.annotate(
            "Cálculo terminado", incomplete = false))
    }

    @Test fun incompleteAnswerIsClearlyLabelledWithoutDiscardingText() {
        val original = "Sección de resultados"
        val result = SkyLongAnswerStatus.annotate(original, incomplete = true)
        assertTrue(result.startsWith(original))
        assertTrue(result.contains("límite de generación"))
        assertTrue(result.contains("continúe"))
    }
}
