package ni.sky.mobileagent

import java.text.Normalizer
import java.util.Locale

/**
 * Deterministic offline SI computations. No LLM-generated numeric answer,
 * physical controls, claims of full simulation, or guesses for missing inputs.
 */
internal object SkyScientificCalculator {
    data class Result(val title: String, val answer: String)

    private fun simple(raw: String): String =
        Normalizer.normalize(raw.lowercase(Locale.ROOT), Normalizer.Form.NFD)
            .replace(Regex("""\p{M}+"""), "")

    fun isRequest(raw: String): Boolean {
        val s = SkyAndroidCognition.normalize(raw)
        val action = Regex("""\b(calcula|calculame|calcular|resuelve|cuanto vale)\b""")
            .containsMatchIn(s)
        return action && (s.contains("energia cinetica") ||
            s.contains("segunda ley de newton") || s.contains("fuerza resultante") ||
            s.contains("ley de ohm") || s.contains("tension electrica"))
    }

    private fun number(raw: String, pattern: String): Double? {
        val captured = Regex(pattern, RegexOption.IGNORE_CASE).find(raw)
            ?.groupValues?.get(1)?.replace(',', '.') ?: return null
        val value = captured.toDoubleOrNull() ?: return null
        return value.takeIf { it.isFinite() && kotlin.math.abs(it) <= 1e9 }
    }

    private fun formatted(value: Double): String =
        String.format(Locale.US, "%.3f", value)

    fun solve(raw: String): Result? {
        if (!isRequest(raw)) return null
        val s = simple(raw)
        if (s.contains("energia cinetica")) {
            val m = number(s, """\bmasa\s*(?:de\s*)?([0-9]+(?:[.,][0-9]+)?)\s*(?:kg|kilogramos?)\b""")
            val v = number(s, """\bvelocidad\s*(?:de\s*)?([0-9]+(?:[.,][0-9]+)?)\s*(?:m/s|metros?\s+por\s+segundo)\b""")
            if (m == null || v == null || m <= 0)
                return Result("Energía cinética", "Para calcularla, indicame una masa positiva en " +
                    "kilogramos y una velocidad en metros por segundo. " +
                    "Ejemplo: SKY, calcula energía cinética masa 2 kg velocidad 3 m/s.")
            val energy = 0.5 * m * v * v
            if (!energy.isFinite()) return Result("Energía cinética",
                "Los valores son demasiado grandes para calcularlos con precisión.")
            return Result("Energía cinética", "### Energía cinética\n\n" +
                "**Datos:** masa " + formatted(m) + " kg; velocidad " + formatted(v) +
                " m/s.\n\n**Fórmula:**\n\\[\nE_c = \\frac{1}{2} m v^{2}\n\\]\n\n" +
                "**Sustitución:**\n\\[\nE_c = 0.5(" + formatted(m) + ")(" +
                formatted(v) + ")^{2}\n\\]\n\n" +
                "**Resultado: " + formatted(energy) + " J**\n\n" +
                "Verificación de unidades: kg × (m/s)² = J. Cálculo local determinista.")
        }

        if (s.contains("segunda ley de newton") || s.contains("fuerza resultante")) {
            val m = number(s, """\bmasa\s*(?:de\s*)?([0-9]+(?:[.,][0-9]+)?)\s*(?:kg|kilogramos?)\b""")
            val a = number(s, """\baceleracion\s*(?:de\s*)?(-?[0-9]+(?:[.,][0-9]+)?)\s*(?:m/s2|m/s\^2|m/s²|metros?\s+por\s+segundo\s+cuadrado)(?=\s|$|[,.;!?])""")
            if (m == null || a == null || m <= 0)
                return Result("Segunda ley de Newton", "Indicame masa positiva en kg y aceleración " +
                    "en m/s². Ejemplo: SKY, calcula fuerza resultante masa 5 kg aceleración 2 m/s2.")
            val force = m * a
            if (!force.isFinite()) return Result("Segunda ley de Newton",
                "Los valores exceden la precisión del cálculo.")
            return Result("Segunda ley de Newton", "### Segunda ley de Newton\n\n" +
                "**Datos:** masa " + formatted(m) + " kg; aceleración " +
                formatted(a) + " m/s².\n\n**Fórmula:**\n\\[\nF = m \\cdot a\n\\]\n\n" +
                "**Sustitución:**\n\\[\nF = (" + formatted(m) + ")(" +
                formatted(a) + ")\n\\]\n\n" +
                "**Resultado: " + formatted(force) + " N**\n\n" +
                "Verificación dimensional: kg × m/s² = N. El signo expresa la " +
                "dirección según el eje elegido. Cálculo local determinista.")
        }

        val r = number(s, """\bresistencia\s*(?:de\s*)?([0-9]+(?:[.,][0-9]+)?)\s*(?:ohmios?|ohms?|ω|Ω)(?=\s|$|[,.;!?])""")
        val i = number(s, """\bcorriente\s*(?:de\s*)?(-?[0-9]+(?:[.,][0-9]+)?)\s*(?:amperios?|amps?|a)\b""")
        if (r == null || i == null || r < 0)
            return Result("Ley de Ohm", "Indicame resistencia en ohmios y corriente en amperios. " +
                "Ejemplo: SKY, calcula ley de Ohm resistencia 4 ohmios corriente 3 amperios.")
        val voltage = r * i
        if (!voltage.isFinite()) return Result("Ley de Ohm",
            "Los valores exceden la precisión del cálculo.")
        return Result("Ley de Ohm", "### Ley de Ohm\n\n" +
            "**Datos:** corriente " + formatted(i) + " A; resistencia " +
            formatted(r) + " Ω.\n\n**Fórmula:**\n\\[\nV = I \\cdot R\n\\]\n\n" +
            "**Sustitución:**\n\\[\nV = (" + formatted(i) + ")(" +
            formatted(r) + ")\n\\]\n\n" +
            "**Resultado: " + formatted(voltage) + " V**\n\n" +
            "Verificación dimensional: A × Ω = V. Circuito resistivo ideal. " +
            "Cálculo local determinista.")
    }
}
