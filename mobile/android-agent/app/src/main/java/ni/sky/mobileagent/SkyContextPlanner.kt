package ni.sky.mobileagent

import java.text.Normalizer
import java.util.Locale

/** Local retrieval. Never uploads archive unless the owner authorizes that turn. */
internal object SkyContextPlanner {
    data class Turn(val id: Long, val question: String, val answer: String, val engine: String)
    private val stop = setOf("que","como","para","sobre","quiero","puedes","sky","una",
        "uno","los","las","del","con","desde","donde","cuando","por","mis","tus")

    private fun words(raw: String): Set<String> {
        val ascii = Normalizer.normalize(raw.lowercase(Locale.ROOT), Normalizer.Form.NFD)
            .replace(Regex("""\p{M}+"""), "")
        return Regex("[a-z0-9]{3,}").findAll(ascii).map { it.value }
            .filterNot { it in stop }.take(100).toSet()
    }

    /** Exclude local actions, direct memories and sensitive file contents. */
    fun eligible(turn: Turn): Boolean {
        val engine = turn.engine.lowercase(Locale.ROOT)
        if (!(engine.startsWith("gemini") || engine.startsWith("groq") ||
                    engine.startsWith("sky core")) ||
            engine.contains("archivo") || engine.contains("visual") ||
            engine.contains("multimedia")) return false
        if (turn.question.isBlank() || turn.answer.isBlank()) return false
        val question = turn.question.trim()
        val prefix = """^(?:sky[\s,.:;!?¡¿-]+)?"""
        if (Regex(prefix + """(?:recuerda|aprende)\s+que\b""",
                RegexOption.IGNORE_CASE).containsMatchIn(question)) return false
        if (Regex(prefix + """(?:abre|abrí|abri|reproduce|envía|envia|borra|elimina|llama|publica)\b""",
                RegexOption.IGNORE_CASE).containsMatchIn(question)) return false
        return !Regex("""(?i)(?:api[_ -]?key|password|contraseña|token|bearer|private[_ -]?key|cvv)\s*[:=]""")
            .containsMatchIn(turn.question + "\n" + turn.answer)
    }

    /** Recent exchanges + related older turns, time ordered, with hard size limits. */
    fun select(query: String, source: List<Turn>, authorized: Boolean,
               maxPairs: Int, maxChars: Int): List<Turn> {
        if (!authorized || maxPairs <= 0 || maxChars < 100) return emptyList()
        val cap = maxPairs.coerceIn(1, 30)
        val bytes = maxChars.coerceIn(100, 30000)
        val entries = source.filter(::eligible).sortedBy { it.id }
        val recent = entries.takeLast(minOf(3, cap)).asReversed()
        val recentIds = recent.mapTo(mutableSetOf()) { it.id }
        val queryTerms = words(query)
        val related = if (queryTerms.isEmpty()) emptyList() else
            entries.asSequence().filterNot { it.id in recentIds }
                .map { it to words(it.question).intersect(queryTerms).size }
                .filter { it.second > 0 }
                .sortedWith(compareByDescending<Pair<Turn, Int>> { it.second }
                    .thenByDescending { it.first.id })
                .map { it.first }.take(cap).toList()
        var used = 0
        val chosen = ArrayList<Turn>()
        for (entry in (recent + related).distinctBy { it.id }) {
            val compact = entry.copy(question = entry.question.take(1200),
                answer = entry.answer.take(1800))
            val size = compact.question.length + compact.answer.length
            if (used + size > bytes) continue
            chosen.add(compact)
            used += size
            if (chosen.size == cap) break
        }
        return chosen.sortedBy { it.id }
    }
}
