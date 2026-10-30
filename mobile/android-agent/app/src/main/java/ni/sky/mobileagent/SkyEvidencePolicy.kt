package ni.sky.mobileagent

import java.net.URI
import java.util.Locale

/**
 * Evidence audit. Links are evidence candidates, not an oracle of truth.
 * This module does not pretend to have read, dated or independently fact-
 * checked a document unless a retrieval tool actually did so.
 */
internal object SkyEvidencePolicy {
    data class Assessment(val sites: Int, val links: Int,
                          val level: String, val explanation: String)

    fun needsVerification(request: String): Boolean {
        val text = " " + SkyAndroidCognition.normalize(request) + " "
        val phrases = listOf(" busca en google ", " busca en internet ",
            " verifica ", " verificame ", " corroborar ", " es verdad ",
            " es cierto ", " es falso ", " fake news ", " desinformacion ",
            " comprueba ", " confirmame ", " que paso ", " ultimas noticias ",
            " noticia de hoy ", " datos actuales ", " cifras oficiales ",
            " fuentes confiables ", " ley vigente ", " reglamento actual ",
            " cual es el precio ", " cuanto cuesta hoy ", " que se sabe ",
            " investiga en internet ", " consulta fuentes ",
            " es real que ", " evidencia cientifica ", " estudios recientes ")
        return phrases.any { text.contains(it) }
    }

    fun assess(sources: List<SkyPhoneCloud.Source>): Assessment {
        val domains = sources.mapNotNull { item ->
            try {
                val u = URI(item.url)
                if (!u.scheme.equals("https", true) || u.userInfo != null ||
                    u.port != -1) null
                else u.host?.lowercase(Locale.ROOT)
                    ?.removePrefix("www.")?.takeIf {
                        it.contains('.') && !it.endsWith(".local")
                    }
            } catch (_: Exception) { null }
        }
        val independentSites = domains.toSet().size
        return when {
            independentSites >= 2 -> Assessment(independentSites, domains.size,
                "VARIAS_FUENTES", "Se recibieron enlaces de " + independentSites +
                " sitios distintos. La coincidencia de dominios NO demuestra " +
                "que todas las afirmaciones sean verdaderas; comprobá contenido, " +
                "fecha, autor y fuente primaria.")
            independentSites == 1 -> Assessment(1, domains.size,
                "UNA_FUENTE", "La búsqueda devolvió enlaces verificables de un " +
                "solo sitio. Hay que corroborar afirmaciones importantes " +
                "con una fuente independiente.")
            else -> Assessment(0, 0, "SIN_FUENTE",
                "No se recibieron fuentes HTTPS verificables. " +
                "No presentes datos cambiantes como confirmados.")
        }
    }

    fun qualify(answer: String, sources: List<SkyPhoneCloud.Source>): String {
        val report = assess(sources)
        return answer.trim() + "\n\nVerificación de fuentes: " +
            report.explanation
    }
}
