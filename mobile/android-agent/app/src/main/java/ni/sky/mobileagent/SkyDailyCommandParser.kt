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
        data class Note(val value: String) : Command()
        object ShowNotes : Command()
        data class Share(val app: String, val value: String) : Command()
        data class Unsupported(val reason: String) : Command()
    }

    fun canonical(raw: String) = Normalizer
        .normalize(raw.lowercase(Locale.ROOT), Normalizer.Form.NFD)
        .replace(Regex("\\p{M}+"), "")
        .trim()

    fun parse(raw: String): Command? {
        if (raw.length > 2000) return null
        val clean = canonical(raw).replace(Regex("\\s+"), " ")
            .replace(Regex("^sky[ ,.:!]+"), "").trim()
        if (clean.isEmpty()) return null
        // Evitar tomar frases explicativas largas como órdenes autorizadas.
        val action = clean.substringBefore("\n").trim()
        if (action.length > 350) return null

        val windowsTarget = Regex("\\b(?:en (?:mi |la )?(?:windows|pc|computadora|ordenador))\\b")
            .containsMatchIn(action)
        if (windowsTarget) {
            return Command.Unsupported("Este comando corresponde al agente de Windows. " +
                "La app Android aún no tiene permiso para ejecutar herramientas remotas del PC.")
        }

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
        val appWords = linkedMapOf(
            "youtube" to "youtube", "chrome" to "chrome",
            "whatsapp" to "whatsapp", "gmail" to "gmail"
        )
        val open = Regex("^(?:abre|abrir|abri|abreme|inicia|iniciar|lanza|lanzar) (?:la |el |aplicacion |app )?(youtube|chrome|whatsapp|gmail)(?: en (?:mi )?(?:telefono|celular|android))?\\.?$")
            .matchEntire(action)
        if (open != null) return Command.OpenApp(appWords.getValue(open.groupValues[1]))
        val notes = Regex("^(?:mostra|muestra|mostrar|mostrame|ensena|abre|abrir|ver) (?:mis |las )?(?:notas|apuntes|anotaciones)$")
        if (notes.matches(action)) return Command.ShowNotes
        val note = Regex("^(?:anota|anotar|apunta|apuntar|guarda (?:una )?nota|toma nota(?: de)?|recuerda que)[: ,]+(.+)$")
            .matchEntire(action)
        if (note != null) {
            val value = raw.trim().replace(Regex("(?i)^sky[ ,.:!]+"), "")
                .replace(Regex("(?i)^(?:anota|anotar|apunta|apuntar|guarda (?:una )?nota|toma nota(?: de)?|recuerda que)[: ,]+"), "")
                .trim().take(1000)
            if (value.isNotBlank()) return Command.Note(value)
        }
        val share = Regex("^(?:comparte|compartir|prepara|preparar|escribe|escribir) (?:en |por |para )?(whatsapp|gmail)[: ,]+(.+)$")
            .matchEntire(action)
        if (share != null) {
            val prefix = Regex("(?i)^(?:sky[ ,.:!]+)?(?:comparte|compartir|prepara|preparar|escribe|escribir)\\s+(?:(?:en|por|para)\\s+)?(?:whatsapp|gmail)[: ,]+")
            val message = raw.trim().replace(prefix, "").trim().take(1000)
            if (message.isNotBlank()) return Command.Share(share.groupValues[1], message)
        }
        return null
    }
}
