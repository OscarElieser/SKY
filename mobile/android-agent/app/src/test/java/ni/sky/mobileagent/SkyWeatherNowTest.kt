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
    @Test fun separatesFutureRequests() {
        assertTrue(SkyWeatherNow.requestsFuture("Clima mañana en Estelí"))
        assertFalse(SkyWeatherNow.requestsFuture("Clima hoy en Estelí"))
    }
}
