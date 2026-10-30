package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyStatisticsCalculatorTest {
    @Test fun checksThreeValuePopulationResults() {
        val result = SkyStatisticsCalculator.solve("SKY, calcula promedio de 2, 4 y 6")
        assertNotNull(result)
        assertEquals(3, result!!.count)
        assertTrue(result.answer.contains("Media: 4.0000"))
        assertTrue(result.answer.contains("Mediana: 4.0000"))
        assertTrue(result.answer.contains("Varianza poblacional: 2.6667"))
        assertTrue(result.answer.contains("Desviación estándar poblacional: 1.6330"))
    }
    @Test fun handlesDecimalAndNegativeValues() {
        val result = SkyStatisticsCalculator.solve("Calcula la mediana de -2, 3.5, 7, 12")
        assertEquals(4, result!!.count)
        assertTrue(result.answer.contains("Mediana: 5.2500"))
    }
    @Test fun rejectsMissingOrAmbiguousDataWithoutHallucination() {
        assertEquals(0, SkyStatisticsCalculator.solve("calcula promedio de")!!.count)
        assertEquals(0, SkyStatisticsCalculator.solve("calcula media de 5")!!.count)
        assertEquals(0, SkyStatisticsCalculator.solve("calcula media de 2, cinco, 6")!!.count)
        assertNull(SkyStatisticsCalculator.solve("SKY, reproduce una canción"))
    }
    @Test fun constantDataHaveZeroVariance() {
        val r = SkyStatisticsCalculator.solve("calcula varianza de 5, 5, 5")
        assertTrue(r!!.answer.contains("Varianza poblacional: 0.0000"))
    }
}
