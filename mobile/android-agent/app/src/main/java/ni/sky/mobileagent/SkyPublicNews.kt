package ni.sky.mobileagent

import android.util.Xml
import org.xmlpull.v1.XmlPullParser
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

/**
 * Limited news fallback when Gemini Search isn't available. Retrieves actual
 * syndicated headlines from Google News over HTTPS; does NOT assert headline
 * truth or claim to read independent full articles.
 */
internal object SkyPublicNews {
    data class Headline(val title: String, val url: String, val publisher: String,
                        val publicationDate: String)
    data class Result(val answer: String, val sources: List<SkyPhoneCloud.Source>)

    fun explicit(raw: String): Boolean {
        val s = SkyAndroidCognition.normalize(raw).removePrefix("sky ").trim()
        return s.startsWith("noticias de ") ||
            s.startsWith("ultimas noticias") ||
            s.startsWith("busca noticias") ||
            s.startsWith("noticias recientes") ||
            s.startsWith("que paso hoy") ||
            s.startsWith("titulares de ")
    }

    fun topic(raw: String): String {
        val s = SkyAndroidCognition.normalize(raw)
            .removePrefix("sky ").trim()
            .replaceFirst(Regex("^(ultimas noticias|noticias recientes|" +
                "busca noticias|noticias de|titulares de|que paso hoy)\\s*(de|sobre)?\\s*"), "")
            .trim()
        val topic = s.ifBlank { "Nicaragua" }
        require(topic.length in 3..140 && !Regex(
            "(?i)password|contrasena|token|clave api|mi telefono|mi correo"
        ).containsMatchIn(topic)) {
            "La búsqueda de noticias debe referirse a información pública."
        }
        return topic
    }

    fun fetch(request: String): Result {
        val query = topic(request)
        val endpoint = "https://news.google.com/rss/search?q=" +
            URLEncoder.encode(query, "UTF-8") +
            "&hl=es-419&gl=NI&ceid=NI:es-419"
        val connection = URL(endpoint).openConnection() as HttpURLConnection
        try {
            connection.connectTimeout = 9000
            connection.readTimeout = 13000
            connection.instanceFollowRedirects = false
            connection.setRequestProperty("Accept", "application/rss+xml, application/xml")
            connection.setRequestProperty("User-Agent", "SKY-IA-Android/1.0")
            val status = connection.responseCode
            if (status !in 200..299) error("Google Noticias no respondió (HTTP $status)")
            val xml = connection.inputStream.bufferedReader(Charsets.UTF_8).use {
                it.readText().take(200001)
            }
            require(xml.length <= 200000) { "Los titulares exceden el límite de seguridad." }
            val parser = Xml.newPullParser()
            parser.setInput(xml.reader())
            var inside = false
            var field = ""
            var title = ""
            var link = ""
            var publisher = ""
            var published = ""
            val headlines = mutableListOf<Headline>()
            var event = parser.eventType
            while (event != XmlPullParser.END_DOCUMENT && headlines.size < 5) {
                when (event) {
                    XmlPullParser.START_TAG -> {
                        field = parser.name.lowercase()
                        if (field == "item") {
                            inside = true
                            title = ""
                            link = ""
                            publisher = ""
                            published = ""
                        }
                    }
                    XmlPullParser.TEXT -> if (inside) {
                        val value = parser.text.trim().take(500)
                        when(field) {
                            "title" -> title += value
                            "link" -> link += value
                            "source" -> publisher += value
                            "pubdate" -> published += value
                        }
                    }
                    XmlPullParser.END_TAG -> {
                        if (parser.name.equals("item", true)) {
                            inside = false
                            if (title.isNotBlank() &&
                                link.startsWith("https://news.google.com/")) {
                                headlines.add(Headline(title.take(230), link.take(1200),
                                    publisher.take(90), published.take(90)))
                            }
                        }
                        field = ""
                    }
                }
                event = parser.next()
            }
            require(headlines.isNotEmpty()) {
                "Google Noticias no devolvió titulares que pudiera verificar como enlaces."
            }
            val detail = headlines.mapIndexed { i, h ->
                (i + 1).toString() + ". " + h.title +
                    (if (h.publisher.isBlank()) "" else " — " + h.publisher) +
                    (if (h.publicationDate.isBlank()) "" else " (" + h.publicationDate + ")")
            }.joinToString("\n\n")
            return Result("Google Noticias muestra estos titulares sobre $query:\n\n" +
                detail + "\n\nEstos son titulares publicados por terceros, " +
                "no hechos que SKY haya verificado. Antes de afirmar que una noticia es " +
                "verdadera, contrastá fuente primaria, fecha y fuentes independientes.",
                headlines.map { SkyPhoneCloud.Source(it.title, it.url) })
        } finally { connection.disconnect() }
    }
}
