package ni.sky.mobileagent

import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

/**
 * Semantic Scholar search: adapted from SKY Windows research connectors.
 * Queries real public scholarly metadata. Does not assert peer review,
 * full-text access, scientific consensus or current completeness.
 */
internal object SkyAcademicResearch {
    data class Result(val summary: String, val sources: List<SkyPhoneCloud.Source>)

    fun explicit(raw: String): Boolean {
        val s = SkyAndroidCognition.normalize(raw).removePrefix("sky ").trim()
        return s.startsWith("busca articulos cientificos sobre ") ||
            s.startsWith("busca investigaciones sobre ") ||
            s.startsWith("busca papers sobre ") ||
            s.startsWith("investiga estudios cientificos sobre ") ||
            s.startsWith("consulta semantic scholar sobre ")
    }

    fun term(raw: String): String {
        val clean = raw.trim().replaceFirst(Regex(
            "^(?:sky\\s*[,.:;!?¡¿]*\\s*)?(?:busca\\s+art[ií]culos\\s+cient[ií]ficos\\s+sobre|" +
            "busca\\s+investigaciones\\s+sobre|busca\\s+papers\\s+sobre|" +
            "investiga\\s+estudios\\s+cient[ií]ficos\\s+sobre|" +
            "consulta\\s+semantic\\s+scholar\\s+sobre)\\s+",
            RegexOption.IGNORE_CASE), "").trim(' ', '.', '?', '¿')
        require(clean.length in 3..170 && '\n' !in clean &&
            !Regex("(?i)(contraseña|clave api|password|token)").containsMatchIn(clean)) {
            "Decime un tema de investigación público y específico."
        }
        return clean
    }

    /** HTTPS public metadata only; runs on SKY's chat background executor. */
    fun search(raw: String): Result {
        val topic = term(raw)
        val address = "https://api.semanticscholar.org/graph/v1/paper/search?" +
            "query=" + URLEncoder.encode(topic, "UTF-8") +
            "&limit=3&fields=title,year,authors,abstract,url"
        val connection = URL(address).openConnection() as HttpURLConnection
        try {
            connection.requestMethod = "GET"
            connection.connectTimeout = 8000
            connection.readTimeout = 15000
            connection.instanceFollowRedirects = false
            connection.setRequestProperty("Accept", "application/json")
            connection.setRequestProperty("User-Agent",
                "SKY-IA-Android/0.8.35 (https://github.com/OscarElieser/SKY)")
            val status = connection.responseCode
            if (status == 429) error("La fuente académica alcanzó su cuota; intentá más tarde.")
            if (status !in 200..299) error("Semantic Scholar respondió HTTP " + status)
            val body = connection.inputStream.bufferedReader(Charsets.UTF_8).use {
                it.readText().take(180001)
            }
            require(body.length <= 180000) { "La respuesta académica excedió el límite." }
            val data = JSONObject(body).optJSONArray("data")
                ?: error("Semantic Scholar no devolvió estudios.")
            val sources = mutableListOf<SkyPhoneCloud.Source>()
            val descriptions = mutableListOf<String>()
            for (i in 0 until minOf(3, data.length())) {
                val paper = data.optJSONObject(i) ?: continue
                val title = paper.optString("title").trim().take(200)
                val id = paper.optString("paperId")
                if (title.isBlank() || !id.matches(Regex("[A-Fa-f0-9]{40}"))) continue
                val url = "https://www.semanticscholar.org/paper/" + id
                val year = paper.optInt("year", 0).takeIf { it in 1800..2100 }
                    ?.toString() ?: "año no informado"
                val names = paper.optJSONArray("authors")
                val authors = (0 until minOf(3, names?.length() ?: 0)).mapNotNull { j ->
                    names?.optJSONObject(j)?.optString("name")?.trim()?.takeIf { it.isNotBlank() }
                }.joinToString(", ")
                val abstract = paper.optString("abstract")
                    .replace(Regex("\\s+"), " ").trim().take(330)
                descriptions.add((i + 1).toString() + ". " + title +
                    " (" + year + ")" + if (authors.isBlank()) "" else ". Autores: " + authors +
                    if (abstract.isBlank()) ". Resumen no disponible." else ". Resumen: " + abstract)
                sources.add(SkyPhoneCloud.Source(title, url))
            }
            require(sources.isNotEmpty()) { "No se encontraron publicaciones verificables para ese tema." }
            return Result("Encontré " + sources.size + " publicaciones registradas sobre " +
                topic + " en Semantic Scholar:\n\n" +
                descriptions.joinToString("\n\n") +
                "\n\nSon metadatos académicos reales; revisá cada artículo antes de " +
                "citarlo y comprobá su revisión por pares.", sources)
        } finally { connection.disconnect() }
    }
}
