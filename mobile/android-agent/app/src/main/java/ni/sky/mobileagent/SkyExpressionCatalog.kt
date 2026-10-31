package ni.sky.mobileagent

import java.text.Normalizer
import java.util.Locale

/**
 * Original Spanish-language conversational content; speech-friendly and offline.
 * Explicit requests only. No model calls, permissions, background listening or user data.
 * A friendly response is never evidence that a real-world task was executed.
 */
internal object SkyExpressionCatalog {
    enum class Kind { SALUDO, DESPEDIDA, AGRADECIMIENTO, MOTIVACION, REFRAN, CHISTE, TRABALENGUAS, ADIVINANZA, REFLEXION, ESTUDIO }

    private val entries: Map<Kind, List<String>> = mapOf(
        Kind.SALUDO to listOf(
            "¡Hola! Estoy aquí y lista para ayudarte con lo que necesités.",
            "¡Buen día! ¿Qué objetivo vamos a resolver hoy?",
            "¡Qué gusto saludarte! ¿En qué proyecto trabajamos?",
            "¡Hola de nuevo! Podemos retomar una tarea o comenzar otra.",
            "¡Qué onda! Contame qué necesitás y lo organizamos.",
            "¡Buenos días! Empecemos por lo más importante.",
            "¡Buenas tardes! ¿Qué pendiente querés resolver primero?",
            "¡Buenas noches! ¿Trabajamos algo o preferís conversar?",
            "¡Un gusto escucharte! Decime cómo puedo colaborar.",
            "¡Hola! Traé tu idea y la convertimos en pasos concretos.",
            "¡Bienvenido a SKY! ¿Qué desafío tenés hoy?",
            "¡Aquí estoy! Podés hablarme o escribirme.",
            "¡Saludos! Tengo disposición para aprender de tus correcciones.",
            "¡Hola! Si es un trabajo extenso, lo dividimos sin perder el hilo.",
            "¡Buen momento para crear algo! ¿Por dónde comenzamos?",
            "¡Hey! ¿Vamos con estudio, trabajo o una charla?",
            "¡Me alegra que volvieras! ¿Qué hacemos ahora?",
            "¡Buenos días! Una prioridad clara nos ayudará a avanzar.",
            "¡Hola! Revisemos datos antes de sacar conclusiones.",
            "¡Buenas! Podemos explorar ideas o verificar resultados."
        ),
        Kind.DESPEDIDA to listOf(
            "¡Hasta luego! Conservá tus avances y seguimos cuando quieras.",
            "¡Nos vemos! Que tengás un buen día.",
            "¡Hasta pronto! Aquí estaré cuando me llamés.",
            "¡Que descansés! Los proyectos también necesitan pausas.",
            "¡Adiós por ahora! Me gustó acompañarte en esta tarea.",
            "¡Nos hablamos después! Cuidate mucho.",
            "¡Feliz noche! Mañana podemos retomar con una mente fresca.",
            "¡Que te vaya bien! Recordá guardar los cambios importantes.",
            "¡Hasta la próxima! Seguimos construyendo paso a paso.",
            "¡Buen descanso! No hace falta resolver todo hoy.",
            "¡Cerramos por ahora! Volvé cuando quieras continuar.",
            "¡Hasta mañana! Que tengas una jornada tranquila.",
            "¡Éxitos en lo que sigue! Te acompaño cuando regresés.",
            "¡Chao! Dejá tiempo para respirar y disfrutar.",
            "¡Nos despedimos por ahora! Gracias por la conversación.",
            "¡Nos vemos pronto! Mantengamos la curiosidad activa.",
            "¡Hasta luego! Revisá lo pendiente cuando estés listo.",
            "¡Que tengas una buena tarde! Seguimos después."
        ),
        Kind.AGRADECIMIENTO to listOf(
            "¡Con gusto! Me alegra que la respuesta te sirva.",
            "¡Para eso estoy! ¿Querés revisar algún detalle?",
            "¡Gracias a vos por la confianza! Seguimos cuando quieras.",
            "¡Un placer colaborar! Podemos mejorar el resultado.",
            "¡De nada! Lo importante es que te resulte útil.",
            "¡Con muchísimo gusto! ¿Hay algo que deba corregir?",
            "¡A la orden! Me gusta trabajar con objetivos claros.",
            "¡Qué bueno que te ayudó! Guardemos lo que funciona.",
            "¡No hay de qué! Podemos pasar al siguiente paso.",
            "¡Gracias por decírmelo! Toda corrección nos ayuda a afinar.",
            "¡Encantada de ayudar! ¿Verificamos el resultado final?",
            "¡Siempre con gusto! Sigamos con precisión.",
            "¡Qué amable! Te acompaño en la siguiente consulta.",
            "¡De nada! Recordá comprobar lo importante antes de usarlo."
        ),
        Kind.MOTIVACION to listOf(
            "Un proyecto grande se construye con decisiones pequeñas y constantes.",
            "Hoy no necesitás hacerlo perfecto; necesitás avanzar con criterio.",
            "Cuando una prueba falla, te está mostrando dónde fortalecer el diseño.",
            "Tu esfuerzo vale más cuando se combina con una buena estrategia.",
            "Cada problema resuelto se convierte en experiencia para el siguiente.",
            "Aprender algo nuevo es una inversión que nadie te quita.",
            "Volver a intentar con un método mejor también es progresar.",
            "El resultado importa, pero la calidad del proceso lo sostiene.",
            "No confundás rapidez con avance: la precisión ahorra tiempo.",
            "Una idea se fortalece cuando resiste preguntas difíciles.",
            "Con disciplina y descanso, las metas dejan de parecer lejanas.",
            "No necesitás saberlo todo hoy; necesitás saber qué investigar después.",
            "Dividir una meta compleja puede volverla alcanzable.",
            "Un día difícil no define el valor de tu trabajo.",
            "La creatividad crece cuando la acompañamos con práctica.",
            "Los errores documentados pueden prevenir errores futuros.",
            "Si algo parece imposible, identificá primero la parte comprobable.",
            "Tu curiosidad es una herramienta poderosa: seguí preguntando.",
            "Una mejora pequeña y verificable vale más que diez promesas.",
            "Cada nueva habilidad amplía las opciones de tu futuro.",
            "La constancia también incluye saber cuándo pedir ayuda.",
            "Que el entusiasmo te impulse y la evidencia te oriente."
        ),
        Kind.REFRAN to listOf(
            "Quien pregunta con paciencia encuentra respuestas más firmes.",
            "El dato bien revisado evita discusiones sin fundamento.",
            "Trabajo sin respaldo es cosecha expuesta al viento.",
            "Donde hay método, hasta el problema difícil encuentra camino.",
            "La palabra amable abre puertas que la prisa mantiene cerradas.",
            "Quien organiza su tiempo encuentra espacio para aprender.",
            "Mejor una prueba sincera que una promesa demasiado brillante.",
            "El conocimiento que se comparte vuelve a crecer.",
            "No por correr primero se llega con el trabajo mejor hecho.",
            "El que guarda sus avances no teme empezar de nuevo.",
            "Una pregunta a tiempo evita cien correcciones tarde.",
            "Cuando se escucha con respeto, la conversación da frutos.",
            "Quien cuida los detalles protege el resultado entero.",
            "Los grandes cambios empiezan con hábitos discretos.",
            "Más vale una fuente confirmada que diez rumores repetidos.",
            "Si la duda te visita, respondé con investigación.",
            "Donde hay colaboración, cada mano suma una solución.",
            "Un plan sin revisión es camino sin señales.",
            "Quien reconoce sus límites también conoce por dónde crecer.",
            "El error que se comprende deja de repetirse tan fácilmente."
        ),
        Kind.CHISTE to listOf(
            "¿Por qué la carpeta se fue de vacaciones? Porque tenía demasiados archivos pendientes.",
            "¿Qué dijo el teclado en la fiesta? Hoy sí voy a soltar todas las teclas.",
            "¿Por qué la impresora llegó tarde? Se quedó atascada pensando en el papel.",
            "¿Qué le dijo el algoritmo al café? Necesito una dosis de energía para iterar.",
            "¿Por qué el lápiz pidió ascenso? Porque ya tenía mucha experiencia en puntos.",
            "¿Qué hace un robot cuando pierde el ritmo? Reinicia el baile, no el sistema.",
            "¿Por qué la nube llevó paraguas? No confiaba en su pronóstico.",
            "¿Qué le dijo la hoja de cálculo al número? Contigo sí me salen las cuentas.",
            "¿Por qué la tesis fue al gimnasio? Tenía que fortalecer su marco teórico.",
            "¿Qué dijo la computadora al amanecer? Hoy arranco con buena memoria.",
            "¿Por qué el semáforo estudiaba? Quería pasar todas las materias en verde.",
            "¿Qué le dijo el libro a la mochila? Llevás mucho conocimiento encima.",
            "¿Por qué el borrador se volvió famoso? Todos hablaban de sus grandes correcciones.",
            "¿Qué le dijo el profesor al Wi-Fi? Hoy necesitamos una conexión de ideas.",
            "¿Por qué el tomate usó computadora? Para ponerse al día con la salsa de datos.",
            "¿Qué hace una regla cuando se equivoca? Vuelve a medir sus palabras.",
            "¿Por qué el código estaba tan contento? Porque finalmente encontró su función.",
            "¿Qué dijo el cursor cansado? Necesito un punto de descanso.",
            "¿Por qué la batería estaba de buen humor? Porque recibió una carga positiva.",
            "¿Qué le dijo el diccionario a la pregunta? Vamos a aclarar ese significado.",
            "¿Por qué el mapa aprobó geometría? Siempre sabía por dónde iban las líneas.",
            "¿Qué hace una calculadora en una fiesta? Suma amistades y resta preocupaciones.",
            "¿Por qué el calendario no discutía? Porque cada asunto tenía su fecha.",
            "¿Qué le dijo la lupa a la investigación? Vamos a mirar esto más de cerca."
        ),
        Kind.TRABALENGUAS to listOf(
            "Pepe prepara pocas papas, pero Pilar prepara papas para Pepe.",
            "Clara clasifica claves claras con calma y con cuidado.",
            "Seis sillas sencillas silban suaves sonidos sin cesar.",
            "Bruno borda bordes blancos bajo brillantes bombillas.",
            "Rita riega rosas rojas mientras Rosa recoge ramas.",
            "Tres técnicos trazan treinta triángulos tras la torre.",
            "Marina mide mil medidas mientras Miriam mira mapas.",
            "Cinco chicos chocan cucharas con chocolate caliente.",
            "Paula pinta puntos pequeños para Pedro y para Pilar.",
            "Luisa lee lentamente largas listas de letras lilas.",
            "Sofía sopla siete silbatos sin soltar su sombrero.",
            "Tomás toma té tibio tras terminar treinta tareas.",
            "Verónica verifica veinte versiones veloces del video.",
            "Diana dibuja dados dorados dentro de dos dibujos.",
            "Nora nombra nueve nubes nuevas en noviembre.",
            "Gabriel guarda guías grandes junto a guantes grises."
        ),
        Kind.ADIVINANZA to listOf(
            "Tengo páginas pero no camino, y guardo historias sin hablar. ¿Qué soy? Un libro.",
            "No tengo boca, pero aviso cuando llega una cita. ¿Qué soy? Una alarma.",
            "Cuanto más me usás, más aprendés; no soy libro ni maestro. ¿Qué soy? La práctica.",
            "Viajo sin pies de una pantalla a otra. ¿Qué soy? Un mensaje.",
            "Tengo teclas pero no soy piano y escribo sin lápiz. ¿Qué soy? Un teclado.",
            "Soy pequeña y redonda, y cierro una oración. ¿Qué soy? Un punto.",
            "Ordeno los días sin detener el tiempo. ¿Qué soy? Un calendario.",
            "Me consultás para orientarte, pero yo no camino. ¿Qué soy? Un mapa.",
            "Guardo ideas antes de convertirse en proyectos. ¿Qué soy? Un cuaderno.",
            "Tengo celdas sin barrotes y hago cuentas sin quejarme. ¿Qué soy? Una hoja de cálculo.",
            "Cada segundo avanzo, pero nunca doy un paso. ¿Qué soy? Un reloj.",
            "Te reflejo sin memorizar tu nombre. ¿Qué soy? Un espejo.",
            "Me enciendo al estudiar y me apago al descansar. ¿Qué soy? Una lámpara.",
            "No soy árbol, pero tengo ramas en un programa. ¿Qué soy? Una estructura de decisiones.",
            "Sin moverme marco norte, sur, este y oeste. ¿Qué soy? Una brújula.",
            "Soy la pregunta que guía un experimento sin dar la respuesta. ¿Qué soy? Una hipótesis."
        ),
        Kind.REFLEXION to listOf(
            "Escuchar antes de responder puede cambiar el rumbo de una conversación.",
            "Lo que hoy parece una dificultad mañana puede convertirse en una lección.",
            "El respeto no exige estar de acuerdo; exige tratar bien a quien piensa distinto.",
            "La tecnología aporta más cuando mejora la vida de las personas.",
            "Las mejores preguntas no siempre tienen respuestas inmediatas.",
            "Verificar una idea no la debilita: la vuelve más confiable.",
            "También es valentía reconocer cuándo necesitamos aprender algo.",
            "El descanso no es abandonar una meta; es cuidar la capacidad de alcanzarla.",
            "El conocimiento sin humildad puede cerrarnos nuevas puertas.",
            "Antes de decidir, preguntate qué información todavía falta.",
            "Una buena herramienta amplía capacidades, no reemplaza el juicio humano.",
            "El compromiso se demuestra en acciones, no solo en intenciones.",
            "Compartir un descubrimiento puede inspirar otro.",
            "Lo urgente merece atención; lo importante merece planificación."
        ),
        Kind.ESTUDIO to listOf(
            "Elegí un tema, escribí qué sabés y anotá dos dudas para investigar.",
            "Probá explicar el concepto con tus propias palabras en un minuto.",
            "Después de leer, resumí la idea principal sin mirar el texto.",
            "Usá un ejemplo de la vida real para comprobar si entendiste la teoría.",
            "Dividí la investigación en pregunta, método, fuentes y conclusiones.",
            "Si una fórmula no funciona, revisá unidades y datos antes del cálculo.",
            "Guardá versiones de tus trabajos para comparar avances.",
            "Una cita necesita fuente, autor, fecha y relación con tu argumento.",
            "Programá primero una prueba pequeña antes de construir el sistema entero.",
            "Alterná explicación, práctica y autoevaluación para aprender mejor.",
            "Al terminar una sección, escribí una pregunta que la ponga a prueba.",
            "Antes de entregar, revisá coherencia, ortografía y evidencia."
        )
    )

    val total: Int = entries.values.sumOf { it.size }

    fun count(kind: Kind): Int = entries.getValue(kind).size

    fun variants(kind: Kind): List<String> = entries.getValue(kind)

    // A deterministic rotation per category avoids repeating the same text
    // every time; it is session-only and holds no private information.
    private val positions = mutableMapOf<Kind, Int>()

    @Synchronized fun next(kind: Kind): String {
        val list = entries.getValue(kind)
        val index = positions.getOrDefault(kind, 0)
        positions[kind] = (index + 1) % list.size
        return list[index]
    }

    fun requested(raw: String): Kind? {
        val normalized = Normalizer.normalize(raw.lowercase(Locale.ROOT),
            Normalizer.Form.NFD).replace(Regex("""\p{M}+"""), "")
            .replace(Regex("""[^a-z0-9]+"""), " ")
            .replace(Regex("""\s+"""), " ").trim()
            .removePrefix("sky ").trim()
        if (normalized.length !in 2..110) return null
        return when (normalized) {
            "hola", "holi", "buenas", "buenos dias", "buenas tardes",
            "buenas noches", "hey", "hey sky", "saludos", "que onda",
            "que ondas", "hola sky", "saludame", "dame un saludo" -> Kind.SALUDO
            "adios", "hasta luego", "hasta pronto", "nos vemos", "chao",
            "me despido", "despedite", "dame una despedida",
            "buen descanso", "hasta manana" -> Kind.DESPEDIDA
            "gracias", "muchas gracias", "te agradezco", "mil gracias",
            "gracias sky", "muchisimas gracias" -> Kind.AGRADECIMIENTO
            "motivame", "dame una frase motivacional", "otra frase motivacional",
            "quiero motivacion", "frase motivacional",
            "decime algo motivador", "dime algo motivador" -> Kind.MOTIVACION
            "contame un refran", "dime un refran", "decime un refran",
            "otro refran", "un refran", "cuentame un refran" -> Kind.REFRAN
            "contame un chiste", "cuentame un chiste", "cuenta un chiste",
            "dime un chiste", "decime un chiste", "conta un chiste",
            "otro chiste", "hazme reir", "haceme reir" -> Kind.CHISTE
            "decime un trabalenguas", "dime un trabalenguas",
            "contame un trabalenguas", "un trabalenguas",
            "otro trabalenguas", "practiquemos diccion" -> Kind.TRABALENGUAS
            "una adivinanza", "otra adivinanza", "decime una adivinanza",
            "dime una adivinanza", "contame una adivinanza" -> Kind.ADIVINANZA
            "dame una reflexion", "una reflexion", "quiero reflexionar",
            "otra reflexion", "decime una reflexion" -> Kind.REFLEXION
            "un consejo de estudio", "dame un consejo de estudio",
            "consejo para estudiar", "tecnica de estudio",
            "una tecnica de estudio", "consejo academico" -> Kind.ESTUDIO
            else -> null
        }
    }
}
