package ni.sky.mobileagent

import android.content.Context
import android.content.SharedPreferences
import kotlin.math.exp
import kotlin.math.ln

/**
 * Adaptación local pequeña a partir de recibos de acciones VERIFICADAS.
 *
 * Esto NO reentrena un Transformer ni concede permisos. Ajusta una predicción
 * logística por categoría de operación. Las solicitudes enviadas (SENT)
 * no son éxitos y jamás actualizan pesos. No guarda órdenes ni datos personales.
 */
class SkyVerifiedLearning(context: Context) {
    private val prefs = context.applicationContext.getSharedPreferences(
        "sky_verified_learning_v1", Context.MODE_PRIVATE
    )

    data class Summary(val category: String, val probability: Double,
                       val examples: Int, val verified: Int, val failures: Int)

    @Synchronized
    fun observe(action: String, status: String): Boolean {
        val outcome = outcome(status) ?: return false
        val category = category(action)
        val count = prefs.getInt("${category}_examples", 0)
        // No desbordar el almacenamiento ni ajustar excesivamente un único patrón.
        if (count >= 10_000) return false
        val weight = prefs.getFloat("${category}_weight", 0f).toDouble()
        val adjusted = train(weight, outcome, 0.08)
        prefs.edit()
            .putFloat("${category}_weight", adjusted.toFloat())
            .putInt("${category}_examples", count + 1)
            .putInt("${category}_verified",
                prefs.getInt("${category}_verified", 0) + if (outcome) 1 else 0)
            .putInt("${category}_failures",
                prefs.getInt("${category}_failures", 0) + if (outcome) 0 else 1)
            .apply()
        return true
    }

    fun report(): List<Summary> = CATEGORIES.map { name ->
        Summary(name, sigmoid(prefs.getFloat("${name}_weight", 0f).toDouble()),
            prefs.getInt("${name}_examples", 0),
            prefs.getInt("${name}_verified", 0),
            prefs.getInt("${name}_failures", 0))
    }

    @Synchronized
    fun clear() { prefs.edit().clear().apply() }

    companion object {
        val CATEGORIES = listOf("notas", "aplicaciones", "musica", "alarmas",
            "mensajeria", "otras")
        /** Recibos no verificados no son ejemplos válidos. */
        fun outcome(status: String): Boolean? = when (status.uppercase()) {
            "VERIFIED_LOCAL", "VERIFICADA_LOCAL" -> true
            "FAILED", "FALLIDA" -> false
            else -> null
        }

        fun category(action: String): String {
            val name = SkyAndroidCognition.normalize(action)
            return when {
                "nota" in name -> "notas"
                "musica" in name || "reprodu" in name -> "musica"
                "alarma" in name || "reloj" in name || "temporizador" in name -> "alarmas"
                "whatsapp" in name || "mensaje" in name || "compart" in name -> "mensajeria"
                "abrir" in name || "aplicacion" in name -> "aplicaciones"
                else -> "otras"
            }
        }

        fun sigmoid(value: Double): Double {
            val x = value.coerceIn(-15.0, 15.0)
            return 1.0 / (1.0 + exp(-x))
        }

        /** Paso acotado del descenso de gradiente; modelo de una sola neurona. */
        fun train(weight: Double, success: Boolean, rate: Double = 0.08): Double {
            require(rate in 0.0..0.2)
            val label = if (success) 1.0 else 0.0
            return (weight.coerceIn(-5.0, 5.0) +
                rate * (label - sigmoid(weight))).coerceIn(-5.0, 5.0)
        }
    }
}
