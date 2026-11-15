package ni.sky.mobileagent

import java.text.Normalizer
import java.util.Locale

/**
 * Comandos locales explícitos, limitados y deterministas.
 * Nunca ejecuta herramientas a partir de las respuestas de un modelo.
 */
object SkyDailyCommandParser {
    sealed class Command {
        data class Alarm(val hour: Int, val minute: Int, val label: String) : Command()
        data class Timer(val seconds: Int) : Command()
        data class OpenApp(val app: String) : Command()
        data class Reminder(val request: SkyReminderCommand.Request) : Command()
        data class Dial(val target: String) : Command()
        data class ComposeSms(val recipient: String, val body: String) : Command()
        data class Navigate(val destination: String) : Command()
        data class OpenSetting(val section: DeviceSetting) : Command()
        object ShowApps : Command()
        object Capabilities : Command()
        data class Note(val value: String) : Command()
        data class WebSearch(val query: String) : Command()
        object ShowNotes : Command()
        data class Share(val app: String, val value: String) : Command()
        data class Unsupported(val reason: String) : Command()
    }

    enum class DeviceSetting { GENERAL, WIFI, BLUETOOTH, DISPLAY, SOUND, BATTERY }

    fun canonical(raw: String) = Normalizer
        .normalize(raw.lowercase(Locale.ROOT), Normalizer.Form.NFD)
        .replace(Regex("\\p{M}+"), "")
        .trim()

    fun parse(raw: String): Command? {
        if (raw.length > 2000) return null
        val clean = canonical(raw).replace(Regex("\\s+"), " ")
            .replace(Regex("^sky[ ,.:!]+"), "").trim()
            .trimStart('¿', '¡', ' ', ',', ':')
            .trimEnd('?', '!', '.', ' ')
        if (clean.isEmpty()) return null
        // Answer real device capabilities locally, based on installed apps,
        // rather than allowing the LLM to invent a categorical refusal.
        val capabilityWords = Regex("""\b(?:funciones|funcionalidades|capacidades|habilidades|puedes hacer|puede hacer|podes hacer|que haces|que sabes hacer|que controlas|que aplicaciones puedes|que apps puedes|en que me ayudas)\b""")
        if (capabilityWords.containsMatchIn(clean) &&
            (clean.startsWith("que ") || clean.startsWith("dime ") ||
                clean.startsWith("decime ") || clean.startsWith("cuales ") ||
                clean.startsWith("cual ") || clean.startsWith("sky ") ||
                clean.startsWith("muestra ") || clean.startsWith("explica "))) {
            return Command.Capabilities
        }
        // Evitar tomar frases explicativas largas como órdenes autorizadas.
        val action = clean.substringBefore("\n").trim()
        if (action.length > 350) return null

        val windowsTarget = Regex("\\b(?:en (?:mi |la )?(?:windows|pc|computadora|ordenador))\\b")
            .containsMatchIn(action)
        if (windowsTarget) {
            return Command.Unsupported("Este comando corresponde al agente de Windows. " +
                "La app Android aún no tiene permiso para ejecutar herramientas remotas del PC.")
        }

        // Funciones estilo Siri/Bixby: solo órdenes explícitas del usuario.
        // No hay permisos de llamadas, SMS ni contactos: Android conserva la acción final.
        val original = raw.trim()
            .replace(Regex("(?i)^(?:oye |hey |ey )?sky[ ,.:!]+"), "")
            .trimStart('¿', '¡', ' ', ',', ':').trim()
        val sms = Regex(
            """^(?:env[ií]a|enviar|manda|mandar|redacta|redactar|prepara|preparar)\s+(?:un\s+)?(?:sms|mensaje(?:\s+de\s+texto)?)\s+(?:a|al|para)\s+(.{1,80}?)\s+(?:que\s+diga|con\s+el\s+texto|diciendo)\s+(.{1,600})$""",
            RegexOption.IGNORE_CASE
        ).matchEntire(original)
        if (sms != null) {
            val recipient = sms.groupValues[1].trim()
            val message = sms.groupValues[2].trim()
            if (recipient.isNotEmpty() && message.isNotEmpty() &&
                !Regex("""\b(?:luego|despues|elimina|borra|paga|instala)\b""")
                    .containsMatchIn(canonical(recipient))) {
                return Command.ComposeSms(recipient, message)
            }
        }
        val dial = Regex(
            """^(?:llama|llamar|marca|marcar|telefonea|telefonear)\s+(?:(?:a|al|a mi|al numero|al numero de)\s+)?(.{2,80})$"""
        ).matchEntire(action)
        if (dial != null) {
            val target = dial.groupValues[1].trim()
            if (!Regex("""\b(?:y luego|y despues|elimina|borra|instala|paga)\b""")
                    .containsMatchIn(target)) return Command.Dial(target)
        }
        val direction = Regex(
            """^(?:llevame a|navega a|guiame a|indicame como llegar a|como llego a|muestrame la ruta a|ruta a)\s+(.{2,130})$"""
        ).matchEntire(action)
        if (direction != null) {
            val place = direction.groupValues[1].trim()
            if (!Regex("""\b(?:y luego|y despues|elimina|borra|instala|paga)\b""")
                    .containsMatchIn(place)) return Command.Navigate(place)
        }
        val settings = Regex(
            """^(?:abre|abrir|muestra|mostrar|ve a|entra a|entra en|configura|configurar)\s+(?:(?:los|las|la|el)\s+)?(?:ajustes|configuracion)(?:\s+(?:(?:del|de|de la|para)\s+)?(wifi|wi fi|bluetooth|pantalla|sonido|volumen|bateria))?$"""
        ).matchEntire(action)
        val toggle = Regex(
            """^(?:activa|activar|enciende|encender|desactiva|desactivar|apaga|apagar)\s+(?:(?:el|la)\s+)?(wifi|wi fi|bluetooth)$"""
        ).matchEntire(action)
        val settingName = settings?.groupValues?.get(1).orEmpty()
            .ifBlank { toggle?.groupValues?.get(1).orEmpty() }
        if (settings != null || toggle != null) {
            val section = when (settingName) {
                "wifi", "wi fi" -> DeviceSetting.WIFI
                "bluetooth" -> DeviceSetting.BLUETOOTH
                "pantalla" -> DeviceSetting.DISPLAY
                "sonido", "volumen" -> DeviceSetting.SOUND
                "bateria" -> DeviceSetting.BATTERY
                else -> DeviceSetting.GENERAL
            }
            return Command.OpenSetting(section)
        }

        // Fecha completa: se prepara en Calendario y el propietario confirma el evento.
        SkyReminderCommand.parse(raw)?.let { return Command.Reminder(it) }

        val timer = Regex("^(?:(?:pon|pone|ponme|crea|crear|activa|activar|configura|programa) (?:un |el )?)?(?:temporizador|timer|cuenta regresiva)(?: de| para)? (\\d{1,4}) (segundos?|minutos?|horas?)$")
            .matchEntire(action)
        if (timer != null) {
            val n = timer.groupValues[1].toIntOrNull() ?: return null
            val unit = timer.groupValues[2]
            val seconds = when {
                unit.startsWith("segundo") -> n
                unit.startsWith("minuto") -> n * 60
                else -> n * 3600
            }
            if (seconds !in 1..86400) return Command.Unsupported(
                "El temporizador debe durar entre 1 segundo y 24 horas.")
            return Command.Timer(seconds)
        }

        val alarmStarts = Regex("^(?:pon|ponme|crea|crear|activa|activar|configura|configurar|programa|programar|establece|establecer) (?:una |la )?alarma\\b")
            .containsMatchIn(action)
        val clock = Regex("^(?:pon|ponme|crea|crear|activa|activar|configura|configurar|programa|programar|establece|establecer) (?:una |la )?alarma(?: para)? (.*)$")
            .matchEntire(action)
        if (clock != null) {
            val argument = clock.groupValues[1]
            // Soporta "a las 5", "5:30 pm", "5 de la mañana", "a las 17:45".
            val time = Regex("(?:^|\\s)(?:a las? )?(\\d{1,2})(?::(\\d{2}))?\\s*(a\\.?m\\.?|p\\.?m\\.?|de la manana|de la tarde|de la noche)?(?:\\s|$)")
                .find(argument) ?: return Command.Unsupported("Indicá una hora válida para la alarma, por ejemplo 05:30.")
            val h0 = time.groupValues[1].toIntOrNull() ?: return null
            val minute = time.groupValues[2].ifBlank { "0" }.toIntOrNull() ?: return null
            if (minute !in 0..59 || h0 !in 0..23) return Command.Unsupported("La hora de la alarma no es válida.")
            val period = time.groupValues[3].replace(".", "")
            val isAm = period == "am" || period == "de la manana"
            val isPm = period == "pm" || period == "de la tarde" || period == "de la noche"
            if ((isAm || isPm) && h0 !in 1..12) return Command.Unsupported("Usá 1 a 12 con AM/PM.")
            val hour = if (isAm || isPm) {
                (h0 % 12) + if (isPm) 12 else 0
            } else h0
            val label = argument.replaceRange(time.range, " ").trim()
                .replace(Regex("^(?:manana|hoy|para|a las?)\\s*"), "")
                .take(70).ifBlank { "Alarma SKY" }
            // AlarmClock solo admite hora/minuto, no fecha; jamás prometer
            // que "mañana" será respetado si el usuario especifica fecha.
            val dateWords = argument.replace("de la manana", "").trim()
            if (Regex("\\b(manana|pasado manana|lunes|martes|miercoles|jueves|viernes|sabado|domingo)\\b")
                    .containsMatchIn(dateWords)) {
                return Command.Unsupported("El Reloj recibe hora y minutos; SKY no puede " +
                    "garantizar una fecha específica con esta interfaz. Abrí el Reloj " +
                    "para seleccionar el día exacto.")
            }
            return Command.Alarm(hour, minute, label)
        }
        if (alarmStarts) return Command.Unsupported(
            "Decime la hora de la alarma, por ejemplo: SKY pon una alarma a las 5:30.")
        val search = Regex("^(?:busca|buscar|buscame|investiga|investigar) (?:en (?:google|internet|la web))[: ,]+(.+)$")
            .matchEntire(action)
        if (search != null) {
            val q = search.groupValues[1].trim().take(220)
            if (q.isNotBlank()) return Command.WebSearch(q)
        }
        val appWords = linkedMapOf(
            "youtube" to "youtube", "chrome" to "chrome",
            "whatsapp" to "whatsapp", "gmail" to "gmail"
        )
        val open = Regex("^(?:abre|abrir|abri|abrime|abreme|inicia|iniciar|lanza|lanzar) (?:la |el |aplicacion |app )?(youtube|chrome|whatsapp|gmail)(?: en (?:mi )?(?:telefono|celular|android))?\\.?$")
            .matchEntire(action)
        if (open != null) return Command.OpenApp(appWords.getValue(open.groupValues[1]))
        // Descubrimiento dinámico: nuevas apps sin actualizar esta lista.
        if (Regex("^(?:(?:muestra|mostra|mostrame|ensena|ver|lista|listar) (?:mis |las |todas las )?(?:aplicaciones|apps)|(?:abre|abrir) (?:el )?(?:catalogo|lista) de (?:aplicaciones|apps))$").matches(action)) {
            return Command.ShowApps
        }
        val notes = Regex("^(?:mostra|muestra|mostrar|mostrame|ensena|abre|abrir|ver) (?:mis |las )?(?:notas|apuntes|anotaciones)$")
        if (notes.matches(action)) return Command.ShowNotes
        // El nombre proviene del teléfono, NO de un catálogo fijo.
        val genericLaunch = Regex(
            "^(?:(?:abre|abrir|abri|abrime|abreme|inicia|iniciar|lanza|lanzar)" +
            "|(?:(?:quiero que|necesito que|puedes|podrias|podes|por favor) )" +
            "(?:me )?(?:abras|abres|abrir|abre)) " +
            "(?:(?:la|el|mi|una|un) )?(?:(?:aplicacion|app|juego) (?:de )?)?" +
            "([a-z0-9][a-z0-9 .+&-]{0,79}?)" +
            "(?: en (?:mi )?(?:telefono|celular|android))?[.!?]*$"
        ).matchEntire(action)
        if (genericLaunch != null) {
            val name = genericLaunch.groupValues[1].trim()
            // Una cadena compuesta no es una orden simple de apertura.
            // Evita convertir instrucciones incrustadas en un nombre de app.
            if (Regex("""\b(?:y|luego|despues|tambien)\s+(?:borra|borrar|elimina|eliminar|envia|enviar|escribe|escribir|modifica|modificar|instala|instalar|desinstala|desinstalar|paga|pagar|ejecuta|ejecutar)\b""")
                    .containsMatchIn(name)) return null
            if (name !in setOf("panel", "chat", "conversacion", "modulo",
                    "ajustes", "mis notas", "todas las aplicaciones", "aplicaciones")) {
                return Command.OpenApp(name)
            }
        }
        val note = Regex("^(?:anota|anotar|apunta|apuntar|guarda (?:una )?nota|toma nota(?: de)?|recuerda que)[: ,]+(.+)$")
            .matchEntire(action)
        if (note != null) {
            val value = raw.trim().replace(Regex("(?i)^sky[ ,.:!]+"), "")
                .replace(Regex("(?i)^(?:anota|anotar|apunta|apuntar|guarda (?:una )?nota|toma nota(?: de)?|recuerda que)[: ,]+"), "")
                .trim().take(1000)
            if (value.isNotBlank()) return Command.Note(value)
        }
        val share = Regex("^(?:comparte|compartir|prepara|preparar|escribe|escribir) (?:en |por |para )?([a-z0-9][a-z0-9 ]{0,70}?): (.{1,1000})$")
            .matchEntire(action)
        if (share != null) {
            val prefix = Regex("(?i)^(?:sky[ ,.:!]+)?(?:comparte|compartir|prepara|preparar|escribe|escribir)\\s+(?:(?:en|por|para)\\s+)?[a-z0-9][a-z0-9 ]{0,70}?:\\s*")
            val message = raw.trim().replace(prefix, "").trim().take(1000)
            if (message.isNotBlank()) return Command.Share(share.groupValues[1].trim(), message)
        }
        return null
    }
}
