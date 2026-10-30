package ni.sky.mobileagent

/**
 * Declarative registry for 33 interdisciplinary expertise families.
 * Routing an intent into a role is NOT a promise of specialist-grade output,
 * access to sensors, third-party apps, laboratories or a trained domain model.
 * The UI remains a single voice/text conversation.
 */
internal object SkyExpertRoles {
    data class Role(val id: Int, val label: String, val signals: List<String>,
                    val safeguards: String)

    val roles: List<Role> = listOf(
        Role(1, "Asistencia y productividad personal", listOf("agenda", "calendario", "tareas diarias", "recordatorio", "tutor personal", "traducir"), "Planifica tareas, enseña y traduce con contexto. No afirmes haber creado un evento sin recibo de la herramienta."),
        Role(2, "Desarrollo de software y sistemas", listOf("programar", "depurar codigo", "flutter", "devops", "ciberseguridad", "base de datos", "sql"), "Entrega código y pruebas ejecutables; operaciones, pruebas de penetración y cambios de producción exigen autorización y acceso real."),
        Role(3, "Creación y producción multimedia", listOf("diseno grafico", "logo", "video", "composicion musical", "videojuego", "storyboard", "campana publicitaria"), "Diseña propuestas originales y salidas exportables cuando exista un motor autorizado. No afirmes haber generado archivos si no los verificaste."),
        Role(4, "Analítica y negocios", listOf("analisis de datos", "proyeccion financiera", "estudio de mercado", "atencion al cliente", "procesos industriales"), "Usa datos y métodos reproducibles. Separa proyecciones de resultados comprobados."),
        Role(5, "Ciencia e innovación", listOf("bioinformatica", "investigacion cientifica", "ensayo experimental", "simulacion cientifica"), "Distingue hipótesis, datos, límites de simulación y resultados reproducibles."),
        Role(6, "Derecho, ética y gobernanza", listOf("contrato legal", "jurisprudencia", "cumplimiento normativo", "sesgo algoritmico", "mediacion de conflicto"), "Cita legislación vigente y jurisdicción; no reemplaces asesoría profesional ni inventes precedentes."),
        Role(7, "Ciencias de frontera", listOf("astrofisica", "exoplaneta", "paleontologia", "arqueologia", "meteorologia avanzada"), "Consulta datos y publicaciones especializados. No inventes precisión ni hallazgos."),
        Role(8, "Robótica e ingeniería física", listOf("robotica", "dron", "brazo robotico", "red inteligente", "nanotecnologia"), "Solo asesora y simula sin dispositivos conectados. Toda acción física exige interbloqueos, telemetría y autorización."),
        Role(9, "Compañía y habilidades sociales", listOf("soledad", "entrevista de trabajo", "habilidades blandas", "negociacion laboral", "apoyo emocional"), "Ofrece acompañamiento respetuoso sin fingir ser humano ni diagnosticar emociones."),
        Role(10, "Salud y biotecnología", listOf("radiografia", "resonancia magnetica", "imagen medica", "medicina personalizada", "ensayo clinico"), "Explica información médica con incertidumbre y evidencia; no diagnostiques ni prescribas tratamientos sin supervisión clínica."),
        Role(11, "Entretenimiento interactivo", listOf("direccion de cine", "doble digital", "mundo procedural", "npc", "metaverso"), "Diseña producciones y prototipos verificables. Respeta derechos de imagen y autor."),
        Role(12, "Agricultura y ambiente", listOf("agricultura de precision", "riego por satelite", "huella de carbono", "reforestacion", "ecosistema"), "Recomienda según medidas y contexto regional; no inventes lecturas de sensores."),
        Role(13, "Prospectiva y políticas públicas", listOf("prospectiva", "tendencias macro", "politica publica", "escenario a 20 anos"), "Presenta escenarios con supuestos, no como predicciones certeras."),
        Role(14, "Gastronomía y fermentación", listOf("chef molecular", "fermentacion", "ciencia de alimentos", "ingenieria de sabores"), "Incluye inocuidad y medidas fiables; no asegures condiciones de lotes sin sensores."),
        Role(15, "Exploración aeroespacial", listOf("trayectoria orbital", "sonda espacial", "rover planetario", "mision espacial"), "Usa modelos orbitales verificados y distingue simulación de operación de misión."),
        Role(16, "Lingüística y cultura", listOf("lengua indigena", "lengua amenazada", "fonetica historica", "lengua muerta"), "Separa reconstrucciones lingüísticas de registros auténticos y respeta comunidades culturales."),
        Role(17, "Moda y diseño industrial", listOf("alta costura", "patron textil", "ergonomia", "diseno industrial", "confeccion"), "Entrega medidas, patrones y tolerancias verificables, sin afirmar pruebas físicas inexistentes."),
        Role(18, "Crisis y protección civil", listOf("desastre natural", "evacuacion", "flujo de multitudes", "incendio forestal"), "Prioriza avisos oficiales y seguridad. No asumas disponibilidad de rutas o recursos sin comprobación."),
        Role(19, "Oceanografía submarina", listOf("oceanografia", "submarino autonomo", "bioacustica marina", "ballenas"), "Analiza datos de sensores reales o presenta la simulación como tal."),
        Role(20, "Neurotecnología", listOf("interfaz cerebro computadora", "eeg", "neurotecnologia", "psicofisiologia"), "No inferir identidad, salud ni emociones desde sensores sin metodología validada."),
        Role(21, "Arquitectura y urbanismo", listOf("arquitectura sostenible", "microclima urbano", "material de construccion", "urbanismo"), "Verifica normas locales y cálculo estructural profesional antes de ejecutar diseños."),
        Role(22, "Deporte y biomecánica", listOf("biomecanica", "rendimiento deportivo", "entrenamiento tactico", "futbol"), "Distingue medición de video real de orientación general, con seguridad física."),
        Role(23, "Numismática y tasación", listOf("numismatica", "filatelia", "tasacion historica", "autenticacion de arte"), "Busca ventas comparables y evidencia; no certifiques autenticidad sin examen experto."),
        Role(24, "Filosofía y pensamiento crítico", listOf("socrates", "filosofia", "falacia", "epistemologia", "etica aplicada"), "Identifica premisas, sesgos y argumentos; no presenta opiniones como hechos."),
        Role(25, "Criptografía y economía de riesgo", listOf("criptografia post cuantica", "resistencia criptografica", "cisne negro", "mercado caotico"), "Diferencia modelos de escenarios, evita prometer seguridad absoluta."),
        Role(26, "Geología y sismología", listOf("sismologia", "actividad volcanica", "yacimiento mineral", "geologia"), "Usa servicios oficiales para alertas; no predigas fechas de sismos o erupciones."),
        Role(27, "Espeleología y cavernas", listOf("espeleologia", "caverna", "cenote", "cueva subterranea"), "Usa mapas reales y reconoce peligros físicos de exploración."),
        Role(28, "Museografía y patrimonio", listOf("museografia", "museo inmersivo", "conservacion de arte", "humedad de pinturas"), "Diseña experiencias y planes de conservación sin atribuir mediciones inexistentes."),
        Role(29, "Viticultura y enología", listOf("viticultura", "barrica", "maduracion de vino", "vinedo"), "Distingue predicción de lecturas de vendimia y controles sanitarios."),
        Role(30, "Entomología", listOf("entomologia", "abejas", "polinizacion", "termitas", "plagas de insectos"), "Propone monitoreo ecológico responsable, no inventa detecciones bioacústicas."),
        Role(31, "Zoología y conservación", listOf("zoologia", "corredor biologico", "animal silvestre", "especie amenazada"), "Valida especies y contexto, sin exponer ubicaciones sensibles de fauna."),
        Role(32, "Astronomía de alta energía", listOf("rayos gamma", "ondas gravitacionales", "grb", "colision de agujeros negros"), "Exige datos instrumentales reproducibles y alertas oficiales."),
        Role(33, "Peritaje lingüístico y acústico", listOf("estilometria forense", "voz forense", "deepfake de voz", "autoria de texto"), "No identifiques concluyentemente personas ni autorías con evidencia ambigua; explica confiabilidad y límites.")
    )
    init {
        require(roles.size == 33 && roles.map { it.id }.toSet().size == 33)
    }

    fun detect(request: String, maxRoles: Int = 2): List<Role> {
        val normalized = " " + SkyAndroidCognition.normalize(request) + " "
        return roles.map { role ->
            val score = role.signals.sumOf { term ->
                val marker = " " + SkyAndroidCognition.normalize(term) + " "
                if (normalized.contains(marker)) 1 + marker.count { it == ' ' } else 0
            }
            role to score
        }.filter { it.second > 0 }
            .sortedWith(compareByDescending<Pair<Role,Int>> { it.second }
                .thenBy { it.first.id })
            .take(maxRoles.coerceIn(1, 3)).map { it.first }
    }

    /** Advisory instructions only. Never routes to device actions. */
    fun guidance(request: String): String {
        val matched = detect(request)
        if (matched.isEmpty()) return ""
        return "ESPECIALIDADES CONSULTIVAS ACTIVADAS (sin permisos de ejecución):\n" +
            matched.joinToString("\n") {
                "Rol " + it.id + " · " + it.label + ": " + it.safeguards
            } + "\n"
    }
}
