package ni.sky.mobileagent

import android.app.Activity
import android.app.AlertDialog
import android.content.ActivityNotFoundException
import android.content.Intent
import android.content.SharedPreferences
import android.provider.AlarmClock
import org.json.JSONArray
import org.json.JSONObject

/**
 * Acciones personales explícitas. La UI del Reloj y de mensajería conserva
 * su propia confirmación. No hay escritura oculta ni envío silencioso.
 */
class SkyAndroidActions(
    private val host: Activity,
    private val prefs: SharedPreferences,
    private val allowed: SharedPreferences,
    private val feedback: (String) -> Unit,
    private val onAccessibilityHelp: () -> Unit,
    private val installedApps: SkyInstalledApps
) {
    private val apps = linkedMapOf(
        "youtube" to Pair("YouTube", "com.google.android.youtube"),
        "chrome" to Pair("Chrome", "com.android.chrome"),
        "whatsapp" to Pair("WhatsApp", "com.whatsapp"),
        "gmail" to Pair("Gmail", "com.google.android.gm")
    )

    fun run(action: SkyDailyCommandParser.Command) {
        when (action) {
            is SkyDailyCommandParser.Command.Alarm -> alarm(action)
            is SkyDailyCommandParser.Command.Timer -> timer(action.seconds)
            is SkyDailyCommandParser.Command.OpenApp -> installedApps.requestLaunch(action.app)
            SkyDailyCommandParser.Command.ShowApps -> installedApps.showCatalog()
            is SkyDailyCommandParser.Command.Note -> saveNote(action.value)
            is SkyDailyCommandParser.Command.WebSearch -> webSearch(action.query)
            is SkyDailyCommandParser.Command.Share -> share(action.app, action.value)
            SkyDailyCommandParser.Command.ShowNotes -> showNotes()
            is SkyDailyCommandParser.Command.Unsupported -> feedback(action.reason)
        }
    }

    private fun alarm(command: SkyDailyCommandParser.Command.Alarm) {
        val hh = "%02d:%02d".format(java.util.Locale.ROOT, command.hour, command.minute)
        AlertDialog.Builder(host)
            .setTitle("SKY · Alarma de Android")
            .setMessage("Solicitar una alarma al Reloj para las " + hh + ". " +
                "El Reloj administra la alarma y podría pedirte confirmación.")
            .setPositiveButton("Crear alarma") { _, _ ->
                val intent = Intent(AlarmClock.ACTION_SET_ALARM).apply {
                    putExtra(AlarmClock.EXTRA_HOUR, command.hour)
                    putExtra(AlarmClock.EXTRA_MINUTES, command.minute)
                    putExtra(AlarmClock.EXTRA_MESSAGE, command.label)
                    putExtra(AlarmClock.EXTRA_SKIP_UI, false)
                }
                launch(intent,
                    "Envié al Reloj la solicitud para las " + hh + ". Verificá que quede configurada.")
            }
            .setNegativeButton("Cancelar") { _, _ -> feedback("No se creó ninguna alarma.") }
            .show()
    }

    private fun timer(seconds: Int) {
        AlertDialog.Builder(host)
            .setTitle("SKY · Temporizador")
            .setMessage("Solicitar al Reloj un temporizador de " + seconds +
                " segundos. Verificá que el Reloj lo inicie.")
            .setPositiveButton("Iniciar") { _, _ ->
                val intent = Intent(AlarmClock.ACTION_SET_TIMER).apply {
                    putExtra(AlarmClock.EXTRA_LENGTH, seconds)
                    putExtra(AlarmClock.EXTRA_MESSAGE, "Temporizador SKY")
                    putExtra(AlarmClock.EXTRA_SKIP_UI, false)
                }
                launch(intent, "Solicité al Reloj el temporizador. Revisá su estado en Android.")
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    private fun webSearch(query: String) {
        val uri = android.net.Uri.parse("https://www.google.com/search?q=" +
            android.net.Uri.encode(query))
        val intent = Intent(Intent.ACTION_VIEW, uri)
        launch(intent, "Abrí en el navegador una búsqueda de: " + query.take(90))
    }

    private fun saveNote(value: String) {
        val clean = value.trim().take(1000)
        if (clean.isEmpty()) return feedback("No hay texto para guardar.")
        val key = "sky_notes_v1"
        val existing = runCatching { JSONArray(prefs.getString(key, "[]")) }
            .getOrDefault(JSONArray())
        existing.put(JSONObject().put("created_at", System.currentTimeMillis()).put("text", clean))
        // Retener como máximo cien notas privadas.
        val limited = JSONArray()
        for (i in maxOf(0, existing.length() - 100) until existing.length()) {
            limited.put(existing.getJSONObject(i))
        }
        if (prefs.edit().putString(key, limited.toString()).commit()) {
            feedback("Nota guardada en SKY. Decí «SKY, mostrame mis notas» para verla.")
        } else feedback("No se pudo confirmar que la nota quedara guardada.")
    }

    private fun showNotes() {
        val array = runCatching { JSONArray(prefs.getString("sky_notes_v1", "[]")) }
            .getOrDefault(JSONArray())
        if (array.length() == 0) return feedback("Todavía no tenés notas guardadas.")
        val summary = (maxOf(0, array.length() - 12) until array.length()).map { i ->
            "• " + array.optJSONObject(i)?.optString("text", "").orEmpty()
        }.joinToString("\n\n")
        AlertDialog.Builder(host)
            .setTitle("SKY · Mis notas (" + array.length() + ")")
            .setMessage(summary)
            .setPositiveButton("Cerrar", null)
            .show()
        feedback("Encontré " + array.length() + " notas privadas en el teléfono.")
    }

    private fun share(id: String, text: String) {
        val details = apps[id]
        if (details == null) {
            installedApps.requestShare(id, text)
            return
        }
        if (!allowed.getBoolean(id, false)) {
            feedback("Autorizá " + details.first + " desde Ajustes antes de compartir.")
            return
        }
        val shareDialog = AlertDialog.Builder(host)
            .setTitle("SKY · Preparar en " + details.first)
            .setMessage("SKY compartirá el texto con esta aplicación. " +
                "No enviará mensajes por su cuenta.\n\n" + text.take(250))
            .setPositiveButton("Continuar") { _, _ ->
                val intent = Intent(Intent.ACTION_SEND).apply {
                    type = "text/plain"
                    setPackage(details.second)
                    putExtra(Intent.EXTRA_TEXT, text)
                }
                launch(intent, "Texto compartido con " + details.first +
                    ". Revisá y confirmá el envío allí.")
            }
        if (BuildConfig.ENABLE_TEXT_ASSIST) {
            shareDialog.setNeutralButton("Escribir en campo") { _, _ ->
                if (!SkyTextAssistService.enabled() ||
                    !host.getSharedPreferences("sky_assistive_text",
                        android.content.Context.MODE_PRIVATE)
                        .getBoolean("consent", false)) {
                    onAccessibilityHelp()
                } else {
                    val app = host.packageManager.getLaunchIntentForPackage(details.second)
                    if (app == null) {
                        feedback("No se encontró " + details.first + " en este teléfono.")
                    } else if (SkyTextAssistService.arm(details.second, text)) {
                        launch(app, "Abrí " + details.first +
                            ". Tocá un campo de texto vacío en 45 segundos. " +
                            "SKY escribirá allí, pero no enviará el mensaje.")
                    } else feedback("Escritura asistida no disponible. Revisá sus permisos.")
                }
            }
        }
        shareDialog.setNegativeButton("Cancelar", null).show()
    }

    private fun launch(intent: Intent, message: String) {
        try {
            host.startActivity(intent)
            feedback(message)
        } catch (_: ActivityNotFoundException) {
            feedback("No se encontró una aplicación Android compatible.")
        } catch (_: SecurityException) {
            feedback("Android bloqueó la acción por falta de autorización.")
        } catch (_: Exception) {
            feedback("No se pudo iniciar la acción solicitada.")
        }
    }
}
