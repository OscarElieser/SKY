package ni.sky.mobileagent

import java.text.Normalizer
import java.util.Locale

/** Local commands accepted with or without saying "SKY". */
object SkyMusicCommand {
    enum class Service { SPOTIFY, YOUTUBE_MUSIC, YOUTUBE }
    data class Request(val query: String, val service: Service?)

    private fun normal(text: String): String = Normalizer
        .normalize(text.lowercase(Locale.ROOT), Normalizer.Form.NFD)
        .replace(Regex("\\p{M}+"), "")
        .replace(Regex("\\s+"), " ").trim()

    private val play = Regex(
        """^(?:pon(?:me)?|pone(?:me)?|reproduce|reproducime|reproduci|reproducir|""" +
        """escucha|escuchemos|quiero escuchar|quiero oir|busca|buscame|coloca)""" +
        """\s+(?:(?:la|una)\s+)?(?:(?:cancion|musica|tema|video)\s+)?(.+)$"""
    )
    private val service = Regex("""\s+(?:en|por|desde)\s+(youtube music|youtube musica|yt music|spotify|youtube)\s*$""")
    private val startService = Regex("""^(spotify|youtube music|youtube musica|yt music|youtube)[: ,]+\s*""")

    fun parse(raw: String): Request? {
        if (raw.length !in 7..360 || raw.contains('\n')) return null
        var clean = normal(raw).replace(Regex("""^sky[ ,.:!]*\s*"""), "")
        val start = startService.find(clean)
        var picked: Service? = null
        if (start != null) {
            picked = choose(start.groupValues[1])
            clean = clean.removeRange(start.range).trim()
        }
        // Una sola orden compuesta: "Abre YouTube y reproduce la canción X".
        val launchAndPlay = Regex(
            """^(?:abre|abri|abrime|abreme|abrir|inicia|iniciar)\s+""" +
            """(?:(?:la|el)\s+)?(?:(?:app|aplicacion)\s+)?""" +
            """(youtube music|youtube musica|yt music|spotify|youtube)\s+""" +
            """(?:(?:y|para)\s+)?""" +
            """(?:pon(?:me)?|pone(?:me)?|reproduce|reproducime|reproduci|reproducir|busca|buscame|coloca)\s+""" +
            """(?:(?:la|una)\s+)?(?:(?:cancion|musica|tema|video)\s+)?(.+)$"""
        ).matchEntire(clean)
        if (launchAndPlay != null) {
            val song = launchAndPlay.groupValues[2]
                .replace(Regex("""^(?:de|del)\s+"""), "")
                .trim(' ', '.', '?', '¿', '!', '"')
            if (song.length !in 2..180 || song in setOf("musica", "cancion", "algo")) return null
            return Request(song, choose(launchAndPlay.groupValues[1]))
        }
        val result = play.matchEntire(clean) ?: return null
        var query = result.groupValues[1].trim()
        val tail = service.find(query)
        if (tail != null) {
            picked = choose(tail.groupValues[1])
            query = query.removeRange(tail.range).trim()
        } else {
            // "Reproducí en Spotify la canción..." and "pon en YouTube Music..."
            val ahead = Regex(
                """^(?:en|desde|por)\s+(youtube music|youtube musica|yt music|spotify|youtube)""" +
                """\s+(?:(?:la|una)\s+)?(?:(?:cancion|musica|tema|video)\s+)?"""
            ).find(query)
            if (ahead != null) {
                picked = choose(ahead.groupValues[1])
                query = query.removeRange(ahead.range).trim()
            }
        }
        query = query.replace(Regex("""^(?:de|del)\s+"""), "").trim(' ', '.', '?', '¿', '!', '"')
        if (query.length !in 2..180 || query in setOf("musica", "cancion", "algo", "youtube", "spotify"))
            return null
        return Request(query, picked)
    }

    private fun choose(raw: String): Service = when (raw) {
        "spotify" -> Service.SPOTIFY
        "youtube music", "youtube musica", "yt music" -> Service.YOUTUBE_MUSIC
        else -> Service.YOUTUBE
    }

    fun label(service: Service) = when (service) {
        Service.SPOTIFY -> "Spotify"
        Service.YOUTUBE_MUSIC -> "YouTube Music"
        Service.YOUTUBE -> "YouTube"
    }
}
