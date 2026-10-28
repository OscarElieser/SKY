package ni.sky.mobileagent

import java.util.Locale
import kotlin.math.roundToInt

/** Creator-supplied analytics from official exports; never claim API sync. */
object SkySocialMetrics {
    data class Record(
        val platform: String, val post: String,
        val views: Long, val likes: Long, val comments: Long,
        val shares: Long, val followers: Long, val date: String = ""
    ) {
        fun engagementRate(): Double =
            if (views <= 0L) 0.0 else (likes + comments + shares).toDouble() * 100.0 / views
    }

    private val aliases = mapOf(
        "platform" to listOf("platform", "plataforma", "red", "network"),
        "post" to listOf("post", "publicacion", "publication", "video", "title", "titulo", "contenido"),
        "views" to listOf("views", "vistas", "reproducciones", "plays", "visualizaciones"),
        "likes" to listOf("likes", "megusta", "megustas", "reacciones"),
        "comments" to listOf("comments", "comentarios"),
        "shares" to listOf("shares", "compartidos", "reposts"),
        "followers" to listOf("followers", "seguidores", "suscriptores"),
        "date" to listOf("date", "fecha", "dia")
    )
    private fun normalized(raw: String): String = java.text.Normalizer
        .normalize(raw.lowercase(Locale.ROOT).trim(), java.text.Normalizer.Form.NFD)
        .replace(Regex("\\p{M}+"), "").replace(Regex("[^a-z0-9]"), "")

    private fun csvCells(line: String): List<String> {
        val out = ArrayList<String>()
        val part = StringBuilder()
        var quoted = false
        var pos = 0
        while (pos < line.length) {
            val ch = line[pos]
            if (ch == '"' && quoted && pos + 1 < line.length && line[pos + 1] == '"') {
                part.append('"')
                pos++
            } else if (ch == '"') quoted = !quoted
            else if (ch == ',' && !quoted) {
                out.add(part.toString().trim())
                part.setLength(0)
            } else part.append(ch)
            pos++
        }
        out.add(part.toString().trim())
        return out
    }
    private fun number(raw: String): Long {
        val clean = raw.trim().replace(" ", "").replace(".", "").replace(",", "")
        if (clean.isBlank()) return 0L
        require(clean.length <= 14 && clean.all { it.isDigit() }) { "Cifra no válida." }
        return clean.toLong()
    }

    fun parseCsv(text: String): List<Record> {
        require(text.length <= 600_000) { "El archivo es demasiado grande." }
        val lines = text.removePrefix("\uFEFF").lineSequence()
            .filter { it.isNotBlank() }.take(202).toList()
        require(lines.size in 2..201) { "Se necesita encabezado y al menos una publicación." }
        val headers = csvCells(lines.first()).map(::normalized)
        fun column(name: String): Int = headers.indexOfFirst { it in aliases.getValue(name) }
        require(column("platform") >= 0 && column("post") >= 0 && column("views") >= 0) {
            "El CSV necesita columnas Plataforma, Publicacion y Vistas."
        }
        return lines.drop(1).mapIndexed { index, line ->
            val cells = csvCells(line)
            fun get(name: String): String = cells.getOrNull(column(name)).orEmpty()
            val source = get("platform").take(40)
            val post = get("post").take(120)
            require(source.isNotBlank() && post.isNotBlank()) {
                "Fila " + (index + 2) + ": falta plataforma o publicación."
            }
            Record(source, post, number(get("views")), number(get("likes")),
                number(get("comments")), number(get("shares")),
                number(get("followers")), get("date").take(20))
        }
    }

    fun analysis(records: List<Record>): String {
        if (records.isEmpty()) return "No hay métricas. Importá un CSV de tus estadísticas oficiales."
        val top = records.maxWithOrNull(compareBy<Record> { it.engagementRate() }.thenBy { it.views })!!
        val views = records.sumOf { it.views }
        val likes = records.sumOf { it.likes }
        val rate = if (views == 0L) 0.0 else
            records.sumOf { it.likes + it.comments + it.shares } * 100.0 / views
        val rounded = (rate * 100.0).roundToInt() / 100.0
        val topRate = (top.engagementRate() * 100.0).roundToInt() / 100.0
        return "Origen: importación del usuario (NO sincronizado por API). " +
            "Publicaciones: " + records.size + ". Vistas: " + views +
            ". Me gusta: " + likes + ". Interacción/vistas: " + rounded + "%. " +
            "Mejor publicación por interacción: " + top.post + " (" + top.platform +
            "), " + topRate + "%. Revisá retención y guardados en las apps oficiales."
    }
}
