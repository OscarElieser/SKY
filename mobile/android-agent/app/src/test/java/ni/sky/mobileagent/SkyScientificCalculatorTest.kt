package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyScientificCalculatorTest {
    @Test fun computesKineticEnergy() {
        val result = SkyScientificCalculator.solve(
            "SKY, calcula energía cinética masa 2 kg velocidad 3 m/s")
        assertNotNull(result)
        assertTrue(result!!.answer.contains("9.000 J"))
    }

    @Test fun computesNewtonForce() {
        val result = SkyScientificCalculator.solve(
            "calcula fuerza resultante masa 5 kg aceleración 2 m/s2")
        assertTrue(result!!.answer.contains("10.000 N"))
    }

    @Test fun computesOhmsLaw() {
        val result = SkyScientificCalculator.solve(
            "calcula ley de Ohm resistencia 4 ohmios corriente 3 amperios")
        assertTrue(result!!.answer.contains("12.000 V"))
    }

    @Test fun acceptsUnicodeSquaredAccelerationFromScienceTextbook() {
        val result = SkyScientificCalculator.solve(
            "calcula fuerza resultante masa 5 kg aceleración 2 m/s²"
        )
        assertNotNull(result)
        assertTrue(result!!.answer.contains("10.000 N"))
        assertFalse(result.answer.contains("Indicame"))
    }

    @Test fun acceptsGreekOhmSymbolAndAmpereAbbreviation() {
        val result = SkyScientificCalculator.solve(
            "calcula ley de Ohm resistencia 4 Ω corriente 3 A"
        )
        assertNotNull(result)
        assertTrue(result!!.answer.contains("12.000 V"))
    }

    @Test fun correctlyPreservesNegativeAccelerationDirection() {
        val result = SkyScientificCalculator.solve(
            "calcula segunda ley de Newton masa 5 kg aceleración -2 m/s²"
        )
        assertNotNull(result)
        assertTrue(result!!.answer.contains("-10.000 N"))
    }

    @Test fun neverFabricatesMissingValues() {
        assertTrue(SkyScientificCalculator.solve(
            "calcula energía cinética masa 2 kg")!!.answer.contains("indicame"))
        assertNull(SkyScientificCalculator.solve("Hola SKY"))
        assertNull(SkyScientificCalculator.solve("abre YouTube"))
    }
}
