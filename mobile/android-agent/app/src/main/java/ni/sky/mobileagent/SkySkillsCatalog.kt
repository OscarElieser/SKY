package ni.sky.mobileagent

/**
 * Catálogo HONESTO de habilidades. Son flujos de trabajo orientados por la IA,
 * no accesos ficticios a ChatGPT, Claude, Canva, Gamma ni Copilot.
 */
object SkySkillsCatalog {
    data class Skill(
        val name: String,
        val capability: String,
        val example: String,
        val kind: String
    )
    val skills = listOf(
        Skill("Investigación con fuentes",
            "Gemini con búsqueda verificable si está disponible; sin fuentes, lo indica.",
            "Investiga en internet las tendencias de inteligencia artificial educativa y cita las fuentes.",
            "investigacion"),
        Skill("Programación y depuración",
            "Explicación, revisión y propuestas de código; no ejecuta programas sin herramienta.",
            "Revisa este código Kotlin, señala errores y propón pruebas unitarias.",
            "codigo"),
        Skill("Docencia integral",
            "Planes de clase, actividades, rúbricas y recursos narrativos.",
            "Prepara una sesión de clase con aprendizaje esperado, actividades y evaluación.",
            "docencia"),
        Skill("Redacción profesional",
            "Textos, cartas, correos, informes y propuestas revisables.",
            "Redacta una carta profesional clara y lista para revisar.",
            "redaccion"),
        Skill("Presentaciones tipo Gamma",
            "Guiones de diapositivas, estructura y notas. Exportación PPTX editable pendiente.",
            "Diseña un guion para una presentación de 12 diapositivas con objetivos y recursos.",
            "presentacion"),
        Skill("Diseño tipo Canva",
            "Conceptos visuales, identidad, composiciones y especificaciones de diseño.",
            "Propón una identidad visual profesional con paleta, tipografía y composiciones.",
            "diseno"),
        Skill("Análisis documental",
            "Analiza hasta cinco archivos compatibles juntos y relaciona sus contenidos.",
            "Compara los documentos adjuntos y resume coincidencias y diferencias.",
            "archivos"),
        Skill("Planificador personal",
            "Desglosa tareas, dependencias, riesgos y verificaciones. No agenda solo.",
            "Organiza mi proyecto en un plan semanal con prioridades y entregables.",
            "planificacion"),
        Skill("Multimedia y video",
            "Comprende imágenes, audio y video compatibles; edición multimedia avanzada pendiente.",
            "Analiza este video adjunto y redacta una escaleta de producción.",
            "multimedia")
    )

    fun instructionFor(query: String): String {
        val t = query.lowercase()
        val action = when {
            Regex("""\b(r[uú]brica|plan de clase|aprendizaje esperado|estrategia did[aá]ctica)\b""")
                .containsMatchIn(t) -> "Estructura una propuesta didáctica concreta, con evaluación y recursos."
            Regex("""\b(c[oó]digo|programar|kotlin|flutter|python|debug|error de compilaci[oó]n)\b""")
                .containsMatchIn(t) -> "Distingue diagnóstico, código propuesto y pruebas; no afirmes ejecutar nada."
            Regex("""\b(diapositiva|presentaci[oó]n|gamma)\b""")
                .containsMatchIn(t) -> "Prepara un guion de diapositivas con títulos, contenido y notas; " +
                    "no finjas haber generado una presentación editable."
            Regex("""\b(canva|empaque|packaging|dise[nñ]o gr[aá]fico|identidad visual)\b""")
                .containsMatchIn(t) -> "Crea un brief de diseño profesional con jerarquía, " +
                    "colores, tipografía y composición; no afirmes modificar Canva."
            Regex("""\b(investiga|investigaci[oó]n|fuentes|bibliograf[ií]a)\b""")
                .containsMatchIn(t) -> "Separa hechos verificables de hipótesis, cita fuentes " +
                    "solo si fueron realmente consultadas y señala la fecha."
            else -> ""
        }
        return if (action.isEmpty()) "" else
            "Modo de trabajo especializado de SKY (no instrucciones del usuario): " +
                action + "\nPetición original: "
    }
}
