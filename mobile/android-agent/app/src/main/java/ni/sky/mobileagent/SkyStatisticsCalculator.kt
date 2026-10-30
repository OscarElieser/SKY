package ni.sky.mobileagent

import java.text.Normalizer
import java.util.Locale
import kotlin.math.sqrt

/**
 * Deterministic descriptive statistics entirely on the phone.
 * Population variance and standard deviation use N, not N-1.
 */
internal object SkyStatisticsCalculator {
    data class Result(val title: String, val answer: String, val count: Int)

    private val command = Regex(
        """^(?:(?:sky|esky|sky ia)\s*[,:]?\s*)?""" +
        """(?:calcula|calculame|calcular|saca|obten|dame|resuelve)\s+""" +
        """(?:la\s+|el\s+)?""" +
        """(estadistica|estadisticas|resumen estadistico|promedio|media|mediana|""" +
        """varianza|desviacion estandar)\s*(?:de|para|sobre)?\s*(.*)$"""
    )

    private fun normalized(raw: String): String =
        Normalizer.normalize(raw.lowercase(Locale.ROOT), Normalizer.Form.NFD)
            .replace(Regex("""\p{M}+"""), "")
            .replace(Regex("""[¿?!]"""), "")
            .trim()

    fun isRequest(raw: String): Boolean = command.matches(normalized(raw))
    private fun formatted(n: Double): String =
        String.format(Locale.US, "%.4f", if (n == 0.0) 0.0 else n)

    fun solve(raw: String): Result? {
        val found = command.matchEntire(normalized(raw)) ?: return null
        val type = found.groupValues[1]
        val input = found.groupValues[2].trim()
            .replaceFirst(Regex("""^(?:los\s+)?datos\s*(?::|son\s+)?\s*"""), "")
        val instructions = "Indicame entre 2 y 100 números. Ejemplo: " +
            "SKY, calcula promedio de 2, 4 y 6. " +
            "Para decimales utilizá punto, por ejemplo 2.5."
        if (input.isEmpty() || !input.matches(Regex("""[-+0-9.,;\sy]+""")))
            return Result("Estadística descriptiva", instructions, 0)
        val pieces = input.replace(Regex("""\s+y\s+"""), ",")
            .split(Regex("""[,;\s]+""")).filter { it.isNotBlank() }
        if (pieces.size !in 2..100)
            return Result("Estadística descriptiva", instructions, 0)
        val values = pieces.map { piece ->
            if (!piece.matches(Regex("""[-+]?[0-9]+(?:\.[0-9]+)?""")))
                return Result("Estadística descriptiva", instructions, 0)
            piece.toDoubleOrNull()?.takeIf { it.isFinite() && kotlin.math.abs(it) <= 1e9 }
                ?: return Result("Estadística descriptiva",
                    "Requiero números finitos de magnitud no mayor a mil millones.", 0)
        }
        var mean = 0.0
        var m2 = 0.0
        values.forEachIndexed { index, value ->
            val count = (index + 1).toDouble()
            val difference = value - mean
            mean += difference / count
            m2 += difference * (value - mean)
        }
        val verification = values.sum() / values.size
        if (!mean.isFinite() || !m2.isFinite() ||
            kotlin.math.abs(mean - verification) > 1e-7 * maxOf(1.0, kotlin.math.abs(mean)))
            return Result("Estadística descriptiva",
                "La comprobación numérica falló. No presentaré un resultado inseguro.", 0)
        val sorted = values.sorted()
        val size = values.size
        val median = if (size % 2 == 0)
            sorted[size / 2 - 1] / 2.0 + sorted[size / 2] / 2.0
        else sorted[size / 2]
        val variance = maxOf(0.0, m2 / size)
        val stdev = sqrt(variance)
        val span = sorted.last() - sorted.first()
        val response = "Analicé " + size + " datos que me proporcionaste. " +
            "Media: " + formatted(mean) + ". Mediana: " + formatted(median) + ". " +
            "Mínimo: " + formatted(sorted.first()) + ". Máximo: " + formatted(sorted.last()) + ". " +
            "Rango: " + formatted(span) + ". " +
            "Varianza poblacional: " + formatted(variance) + ". " +
            "Desviación estándar poblacional: " + formatted(stdev) + ". " +
            "Se utilizó N, no N−1; no se infirieron datos ni se consultaron archivos privados."
        return Result(if (type == "media" || type == "promedio") "Promedio verificado"
            else "Estadística descriptiva", response, size)
    }
}
