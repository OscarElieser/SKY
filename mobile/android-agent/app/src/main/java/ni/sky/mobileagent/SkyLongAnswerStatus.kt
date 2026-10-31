package ni.sky.mobileagent

/**
 * A local inference answer can legitimately stop at the model's token budget.
 * Never present it as a complete academic solution in that case.
 */
internal object SkyLongAnswerStatus {
    fun annotate(answer: String, incomplete: Boolean): String =
        if (incomplete) answer + "\n\nSKY: La respuesta alcanzó el límite de " +
            "generación del modelo. Podés solicitar que continúe desde el último apartado." 
        else answer
}
