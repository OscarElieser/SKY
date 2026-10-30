package ni.sky.mobileagent

import java.text.Normalizer
import java.util.Locale
import kotlin.math.sqrt
import kotlin.math.abs

/**
 * Solves ax²+bx+c=0 locally with checked, explicitly supplied coefficients.
 * No AI inference or code execution. Supports complex roots and stable real roots.
 */
internal object SkyQuadraticSolver {
    data class Result(val answer: String, val solved: Boolean)
    private val start = Regex(
        """^(?:(?:sky ia|sky)\s*[,;:]?\s*)?""" +
        """(?:resuelve|resolveme|calcula|soluciona)\s+""" +
        """(?:la\s+)?(?:ecuacion cuadratica|ecuacion de segundo grado)\s*(.*)$"""
    )
    private val coefficient = Regex("""\b([abc])\s*=?\s*([-+]?[0-9]+(?:[.,][0-9]+)?)\b""")
    private fun normalized(s: String): String =
        Normalizer.normalize(s.lowercase(Locale.ROOT), Normalizer.Form.NFD)
            .replace(Regex("""\p{M}+"""), "").replace(Regex("""[¿?!]"""), "").trim()
    private fun fmt(n: Double) = String.format(Locale.US, "%.5f", if (n==0.0) 0.0 else n)

    fun isRequest(raw: String): Boolean = start.matches(normalized(raw))

    fun solve(raw: String): Result? {
        val tail = start.matchEntire(normalized(raw))?.groupValues?.get(1) ?: return null
        val help = "Necesito los tres coeficientes de ax² + bx + c = 0. " +
            "Ejemplo: SKY, resuelve ecuación cuadrática a=1 b=-3 c=2."
        if (!tail.matches(Regex("""[abc0-9=+\-.,;\s]+""")))
            return Result(help, false)
        val matches = coefficient.findAll(tail).toList()
        if (matches.size != 3 || matches.map { it.groupValues[1] }.toSet() != setOf("a","b","c") ||
            tail.replace(coefficient, "").replace(Regex("""[,;\s]"""), "").isNotEmpty())
            return Result(help, false)
        val values = matches.associate {
            it.groupValues[1] to it.groupValues[2].replace(',', '.').toDoubleOrNull()
        }
        val a = values["a"]?.takeIf { it.isFinite() && abs(it) <= 1e6 }
        val b = values["b"]?.takeIf { it.isFinite() && abs(it) <= 1e6 }
        val c = values["c"]?.takeIf { it.isFinite() && abs(it) <= 1e6 }
        if (a == null || b == null || c == null || a == 0.0)
            return Result("a debe ser distinto de cero y los tres coeficientes " +
                "deben ser números finitos de magnitud máxima un millón.", false)
        val discriminant = b*b - 4*a*c
        if (!discriminant.isFinite()) return Result("Los datos exceden la precisión numérica.", false)
        val prefix = "Resolví ax² + bx + c = 0 con a=" + fmt(a) +
            ", b=" + fmt(b) + ", c=" + fmt(c) +
            ". Discriminante: " + fmt(discriminant) + ". "
        val response = when {
            discriminant < 0.0 -> {
                val real = -b / (2*a)
                val imaginary = sqrt(-discriminant) / (2*abs(a))
                prefix + "No hay raíces reales. Raíces complejas: " +
                    fmt(real) + " ± " + fmt(imaginary) + "i."
            }
            discriminant == 0.0 -> prefix + "Raíz real doble: x=" + fmt(-b/(2*a)) + "."
            else -> {
                val q = -0.5 * (b + (if (b >= 0.0) 1.0 else -1.0) * sqrt(discriminant))
                val roots = if (q == 0.0) listOf(0.0, 0.0)
                    else listOf(q/a, c/q).sorted()
                prefix + "Raíces reales: x₁=" + fmt(roots[0]) + ", x₂=" + fmt(roots[1]) + "."
            }
        }
        return Result(response + " Cálculo matemático local, sin consulta a modelos externos.", true)
    }
}
