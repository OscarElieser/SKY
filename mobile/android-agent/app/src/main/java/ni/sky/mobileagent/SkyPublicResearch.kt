package ni.sky.mobileagent

import android.net.Uri
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

/**
 * Native internet research for encyclopedic facts. The fixed Wikimedia host
 * is intentionally not an unrestricted browser, scraper or action executor.
 * The source is displayed and no personal profile or credentials are sent.
 * Wikipedia is NOT a news API and cannot certify rapidly changing facts.
 */
internal object SkyPublicResearch {
    data class Result(val answer: String, val sourceUrl: String, val sourceTitle: String)
    fun explicit(raw: String): Boolean {
        val s = SkyAndroidCognition.normalize(raw)
        return s.startsWith("busca en wikipedia ") ||
            s.startsWith("sky busca en wikipedia ") ||
            s.startsWith("consulta wikipedia ") ||
            s.startsWith("sky consulta wikipedia ")
    }
    fun encyclopedic(raw: String): Boolean {
        val s = SkyAndroidCognition.normalize(raw)
            .replace(Regex("^(?:sky ia |sky )"), "")
        return s.startsWith("que es ") || s.startsWith("quien fue ") ||
            s.startsWith("que significa ") || s.startsWith("historia de ") ||
            s.startsWith("explicame que es ")
    }
    fun term(raw: String): String {
        val withoutWake = raw.trim().replaceFirst(
            Regex("^(?:(?:hola|oye)\\s+)?(?:sky\\s+ia|sky)\\s*[,.:;!?¡¿-]*\\s*",
                RegexOption.IGNORE_CASE), "")
        val result = withoutWake.replaceFirst(Regex(
            "^(?:busca\\s+en\\s+wikipedia|consulta\\s+wikipedia|" +
            "explicame\\s+que\\s+es|qué\\s+es|que\\s+es|quién\\s+fue|" +
            "quien\\s+fue|qué\\s+significa|que\\s+significa|historia\\s+de)\\s+",
            RegexOption.IGNORE_CASE), "")
            .trim(' ', '.', '¿', '?', '¡', '!')
        require(result.length in 3..160 && !result.contains('\n') &&
            !Regex("(?i)(contraseña|clave api|token|password|mi cuenta|mi correo|mi numero|mi número)").containsMatchIn(result)) {
            "Esa consulta no es apropiada para un buscador público."
        }
        return result
    }
    /** Blocking HTTPS request; call only on the private chat executor. */
    fun find(raw: String): Result {
        val query = term(raw)
        val endpoint = "https://es.wikipedia.org/w/api.php?" +
            "action=query&generator=search&gsrnamespace=0&gsrlimit=3" +
            "&gsrsearch=" + URLEncoder.encode(query, "UTF-8") +
            "&prop=extracts&exintro=1&explaintext=1&exsentences=3" +
            "&format=json&formatversion=2"
        val conn = URL(endpoint).openConnection() as HttpURLConnection
        try {
            conn.requestMethod = "GET"
            conn.instanceFollowRedirects = false
            conn.connectTimeout = 8000
            conn.readTimeout = 13000
            conn.setRequestProperty("Accept", "application/json")
            conn.setRequestProperty("User-Agent",
                "SKY-IA-Android/0.8.35 (https://github.com/OscarElieser/SKY)")
            val code = conn.responseCode
            if (code !in 200..299) error("Wikipedia respondió HTTP " + code)
            val body = conn.inputStream.bufferedReader(Charsets.UTF_8).use {
                it.readText().take(160001)
            }
            require(body.length <= 160000) { "Respuesta de Wikipedia demasiado extensa." }
            val pages = JSONObject(body).optJSONObject("query")?.optJSONArray("pages")
            val matches = (0 until (pages?.length() ?: 0)).mapNotNull { i ->
                pages?.optJSONObject(i)
            }.filter { !it.optString("extract").isNullOrBlank() && it.optInt("ns", -1) == 0 }
            val page = matches.minByOrNull { it.optInt("index", 999) }
                ?: error("Wikipedia no encontró un artículo explicativo suficiente.")
            val title = page.optString("title").take(180)
            val extract = page.optString("extract")
                .replace(Regex("\\s+"), " ").trim().take(1100)
            require(title.isNotBlank() && extract.length > 40) {
                "La fuente no devolvió información suficiente."
            }
            val url = "https://es.wikipedia.org/wiki/" + Uri.encode(title.replace(' ', '_'))
            return Result("$title. $extract\n\nFuente consultada: Wikipedia en español. " +
                "Es una referencia enciclopédica, no una verificación de noticias recientes.",
                url, title)
        } finally { conn.disconnect() }
    }
}
