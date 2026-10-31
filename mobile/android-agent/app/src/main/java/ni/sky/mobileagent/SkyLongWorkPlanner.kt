package ni.sky.mobileagent

import java.text.Normalizer
import java.util.Locale
import java.util.UUID

/**
 * Produces a real editable Markdown work-plan artifact, NOT a fictitious thesis,
 * research finding, compiled application or finished deliverable.
 *
 * Explicit command only. Model generation, source verification and compilation
 * require separately authorized executors and their own evidence.
 */
internal object SkyLongWorkPlanner {
    enum class Kind { TESIS, INVESTIGACION, PROGRAMACION }
    data class Plan(val kind: Kind, val topic: String, val markdown: String,
                    val operationId: String)

    fun prepare(raw: String): Plan? {
        val clean = raw.trim().replaceFirst(
            Regex("""^sky\s*[,.:;!?¡¿-]*\s*""", RegexOption.IGNORE_CASE), "")
        val match = Regex(
            """^(?:planifica|prepara un plan para|crea un plan para)\s+""" +
                """(?:una?\s+)?(tesis|investigaci[oó]n|proyecto de programaci[oó]n)\s+""" +
                """(?:sobre|de|para)\s+(.+)$""",
            setOf(RegexOption.DOT_MATCHES_ALL, RegexOption.IGNORE_CASE)
        ).matchEntire(clean) ?: return null
        val normalizedKind = Normalizer.normalize(match.groupValues[1]
            .lowercase(Locale.ROOT), Normalizer.Form.NFD)
            .replace(Regex("""\p{M}+"""), "")
        val kind = when (normalizedKind) {
            "tesis" -> Kind.TESIS
            "investigacion" -> Kind.INVESTIGACION
            else -> Kind.PROGRAMACION
        }
        // Keep the exact topic, accents and all internal "de/sobre" phrases.
        val topic = match.groupValues[2].trim().replace(Regex("""\s+"""), " ")
        if (topic.length !in 5..600) return null
        val sections = when (kind) {
            Kind.TESIS -> listOf("Delimitación del problema y preguntas",
                "Estado del arte y fuentes primarias",
                "Objetivos, hipótesis y marco conceptual",
                "Diseño metodológico y criterios éticos",
                "Instrumentos, muestra y procedimiento",
                "Resultados y análisis (solo datos comprobados)",
                "Discusión, limitaciones y conclusiones",
                "Referencias verificadas y anexos")
            Kind.INVESTIGACION -> listOf("Problema y alcance",
                "Búsqueda y evaluación de evidencia",
                "Marco conceptual y términos",
                "Método de recolección y análisis",
                "Contraste de fuentes y contraejemplos",
                "Hallazgos respaldados por evidencias",
                "Limitaciones, conclusiones y recomendaciones")
            Kind.PROGRAMACION -> listOf("Requisitos funcionales y no funcionales",
                "Arquitectura, amenazas y dependencias",
                "Contratos de interfaces y modelos de datos",
                "Implementación incremental en control de versiones",
                "Pruebas unitarias, integración y rendimiento",
                "Seguridad, observabilidad y recuperación",
                "Documentación de despliegue y entregables")
        }
        val operationId = UUID.randomUUID().toString()
        return Plan(kind, topic, buildString {
            append("# Plan de trabajo SKY IA\n\n")
            append("**Operación local:** ").append(operationId).append("\n")
            append("**Modalidad:** ").append(kind.name.lowercase(Locale.ROOT)).append("\n")
            append("**Tema:** ").append(topic).append("\n\n")
            append("> Este documento es un plan editable, no un trabajo final. ")
            append("Las fuentes, los resultados y las ejecuciones deben comprobarse.\n\n")
            append("## Etapas verificables\n\n")
            sections.forEachIndexed { index, name ->
                append("### ").append(index + 1).append(". ").append(name).append("\n")
                append("- [ ] Definir entregable y criterios de aceptación.\n")
                append("- [ ] Obtener o producir evidencia autorizada.\n")
                append("- [ ] Revisar exactitud, seguridad y coherencia.\n")
                append("- [ ] Guardar versión y evidencia del resultado.\n\n")
            }
            append("## Control de calidad\n\n")
            append("- [ ] No inventar datos, bibliografía, ejecuciones ni resultados.\n")
            append("- [ ] Identificar archivos y fuentes originales, con fecha.\n")
            append("- [ ] Respetar privacidad, autoría y permisos específicos.\n")
            append("- [ ] Documentar tareas completas, pendientes y limitaciones.\n")
            append("- [ ] Exportar la versión revisada y conservar historial.\n\n")
            append("## Continuación\n\n")
            append("Solicitá elaborar la etapa correspondiente. Los textos extensos ")
            append("se trabajan por partes y se integran tras verificar cada sección.\n")
        }, operationId)
    }
}
