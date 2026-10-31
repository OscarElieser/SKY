package ni.sky.mobileagent

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class SkyWeatherNowTest {
    @Test fun acceptsNamedLocation() {
        assertEquals("Managua, Nicaragua", SkyWeatherNow.requestedCity("¿Cómo está el clima en Managua, Nicaragua?"))
        assertEquals("León", SkyWeatherNow.requestedCity("temperatura en León"))
    }
    @Test fun doesNotAssumeLocation() {
        assertNull(SkyWeatherNow.requestedCity("¿Cómo está el clima?"))
        assertTrue(SkyWeatherNow.isWeatherQuery("¿Qué clima hace hoy?"))
        assertFalse(SkyWeatherNow.isWeatherQuery("Abrí YouTube"))
    }
    @Test fun thesisDurationMustNotBeMisclassifiedAsMeteorologicalWeather() {
        val thesis = "Adopta la identidad de un comité académico. " +
            "Licenciatura en Informática Educativa, inteligencia artificial y " +
            "estado de ánimo emocional en educación técnica y universitaria. " +
            "Tiempo disponibles 6 meses. Redacta los capítulos en Word."
        assertFalse(SkyWeatherNow.isWeatherQuery(thesis))
        assertFalse(SkyWeatherNow.isWeatherQuery(
            "Necesito tiempo disponible para entregar una tesis de 350 páginas"))
        assertFalse(SkyWeatherNow.isWeatherQuery(
            "Investiga el clima emocional en educación superior"))
        assertFalse(SkyWeatherNow.isWeatherQuery("Clima emocional en educación universitaria"))
        assertFalse(SkyWeatherNow.isWeatherQuery("Temperatura emocional del aula"))
        assertFalse(SkyWeatherNow.isWeatherQuery(
            "El clima de aula puede influir en el rendimiento académico"))
        assertFalse(SkyWeatherNow.isWeatherQuery(
            "Mide temperatura emocional y variables afectivas de estudiantes"))
        assertFalse(SkyWeatherNow.isWeatherQuery(
            "Diseña el plan de estudios y estima el tiempo de investigación"))
    }

    @Test fun actualWeatherQueriesStillWork() {
        assertTrue(SkyWeatherNow.isWeatherQuery("Clima mañana en Estelí"))
        assertTrue(SkyWeatherNow.isWeatherQuery("temperatura en León"))
        assertTrue(SkyWeatherNow.isWeatherQuery("¿Cómo está el clima en Managua?"))
        assertTrue(SkyWeatherNow.isWeatherQuery("¿Qué tiempo hace en Granada?"))
        assertTrue(SkyWeatherNow.isWeatherQuery("SKY, por favor dime el clima en Managua"))
    }

    @Test fun separatesFutureRequests() {
        assertTrue(SkyWeatherNow.requestsFuture("Clima mañana en Estelí"))
        assertFalse(SkyWeatherNow.requestsFuture("Clima hoy en Estelí"))
    }
}
