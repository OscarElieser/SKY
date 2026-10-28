package ni.sky.mobileagent

import java.text.Normalizer
import java.util.Locale

/**
 * Direct controls for an active music player and the Android lock screen.
 * Speech and typed commands are interpreted without requiring "SKY".
 * No permissions, credentials or background listening are granted here.
 */
object SkyQuickCommand {
    enum class Action {
        NEXT, PREVIOUS, RESTART, VOLUME_UP, VOLUME_DOWN,
        PAUSE, PLAY, REQUEST_UNLOCK
    }

    private fun clean(raw: String): String = Normalizer
        .normalize(raw.lowercase(Locale.ROOT), Normalizer.Form.NFD)
        .replace(Regex("\\p{M}+"), "")
        .replace(Regex("[^a-z0-9 ]"), " ")
        .replace(Regex("\\s+"), " ")
        .trim()
        .replace(Regex("^(?:oye |hey |ey )?sky\\s*"), "")
        .trim()

    fun parse(raw: String): Action? {
        if (raw.length !in 3..160 || '\n' in raw) return null
        val command = clean(raw)
        return when (command) {
            "siguiente", "siguiente cancion", "la siguiente", "pon la siguiente",
            "pasa a la siguiente", "cambia de cancion", "cambia de musica",
            "cambia la musica", "otra cancion", "pon otra cancion",
            "adelanta a la siguiente" -> Action.NEXT

            "atras", "anterior", "la anterior", "cancion anterior",
            "pon la anterior", "regresa a la anterior", "vuelve a la anterior",
            "retrocede una cancion" -> Action.PREVIOUS

            "repite", "repeti", "repitela", "repite la cancion", "repite esta",
            "desde el principio", "reinicia la cancion", "ponla otra vez" -> Action.RESTART

            "sube", "sube volumen", "sube el volumen", "subi el volumen",
            "mas volumen", "un poco mas alto", "sube la musica",
            "subele volumen" -> Action.VOLUME_UP

            "baja", "baja volumen", "baja el volumen", "bajale volumen",
            "menos volumen", "un poco mas bajo", "baja la musica",
            "bajale a la musica" -> Action.VOLUME_DOWN

            "para", "para la musica", "para la cancion", "para de reproducir",
            "deten la musica", "deten la cancion", "detente", "pausa",
            "pausa la musica", "pausa la cancion", "detene la musica" -> Action.PAUSE

            "continua", "continua la musica", "reanuda", "reanuda la musica",
            "sigue con la musica", "dale play", "dale reproducir" -> Action.PLAY

            "activa el telefono", "enciende el telefono", "enciende la pantalla",
            "activa la pantalla", "despierta el telefono",
            "muestra desbloqueo", "desbloquea el telefono",
            "quiero desbloquear el telefono" -> Action.REQUEST_UNLOCK

            else -> null
        }
    }
}
