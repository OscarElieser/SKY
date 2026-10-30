package ni.sky.mobileagent

/**
 * Limpieza exclusiva de la copia enviada al motor TextToSpeech.
 * Nunca cambia la respuesta del chat, el historial ni las órdenes Android.
 */
object SkySpokenText {
    /** Spoken math is a separate, best-effort interpretation of on-screen math. */
    private fun sayFormula(raw: String): String {
        var text = raw.trim()
        text = text.replace(Regex("""\\(?:text|mathrm|operatorname)\{([^{}]*)\}"""), "$1")
            .replace(Regex("""\\(?:mathbf|mathit)\{([^{}]*)\}"""), "$1")
            .replace(Regex("""_\{([^{}]*)\}"""), " subíndice $1")
            .replace(Regex("""\^\{([^{}]*)\}"""), " elevado a $1")
            .replace(Regex("""_([a-zA-Z0-9])"""), " subíndice $1")
            .replace(Regex("""\^([a-zA-Z0-9])"""), " elevado a $1")
            .replace(Regex("""\\(?:dfrac|tfrac|frac)\{([^{}]*)\}\{([^{}]*)\}"""),
                "$1 dividido entre $2")
            .replace(Regex("""\\sqrt\{([^{}]*)\}"""), "raíz cuadrada de $1")
        val ops = mapOf(
            "\\rightleftharpoons" to " en equilibrio con ",
            "\\leftrightarrow" to " en equilibrio con ",
            "\\rightarrow" to " produce ",
            "\\to" to " produce ",
            "\\approx" to " aproximadamente igual a ",
            "\\times" to " por ", "\\cdot" to " por ",
            "\\pm" to " más o menos ", "\\leq" to " menor o igual que ",
            "\\geq" to " mayor o igual que ", "\\neq" to " diferente de ",
            "\\alpha" to " alfa ", "\\beta" to " beta ", "\\gamma" to " gamma ",
            "\\Delta" to " delta ", "\\pi" to " pi "
        )
        for ((latex, spoken) in ops) text = text.replace(latex, spoken)
        return text.replace("=", " es igual a ")
            .replace("+", " más ").replace("*", " por ")
            .replace(Regex("""\\[a-zA-Z]+"""), " ")
            .replace(Regex("""[{}\\\[\]]"""), " ")
            .replace(Regex("""\s+"""), " ").trim()
    }

    fun prepare(raw: String): String {
        if (raw.isBlank()) return ""
        return raw
            .replace(Regex("""```[\s\S]*?```"""), " Código disponible en pantalla. ")
            .replace(Regex("""\\\[([\s\S]*?)\\\]""")) { sayFormula(it.groupValues[1]) }
            .replace(Regex("""\\\(([\s\S]*?)\\\)""")) { sayFormula(it.groupValues[1]) }
            .replace(Regex("""\$\$([\s\S]*?)\$\$""")) { sayFormula(it.groupValues[1]) }
            .replace(Regex("""\[([^\]\n]{1,150})\]\(https?://[^)\s]+\)"""), "$1")
            .replace(Regex("""https?://\S+"""), " un enlace ")
            .replace(Regex("""(?m)^\s{0,3}#{1,6}\s+"""), "")
            .replace(Regex("""(?m)^\s*(?:[-*•]|\d+[.)])\s+"""), "")
            .replace(Regex("""\n\s*\n+"""), ". ")
            .replace("\n", ". ")
            .replace(Regex("""\*\*|__|~~|[`#*_>|~{}\[\]<>«»]"""), " ")
            .replace(Regex("""[¿¡]"""), "")
            .replace(Regex("""[\p{So}\p{Sk}]"""), " ")
            .replace(Regex("""\s+([,.!?;:])"""), "$1")
            .replace(Regex("""\s+"""), " ")
            .replace(Regex("""(?:\.\s*){2,}"""), ". ")
            .trim()
    }
}
