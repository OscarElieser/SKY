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
    var onReceipt: ((String, String, String) -> Unit)? = null
    private fun receipt(action: String, status: String, detail: String) {
        onReceipt?.invoke(action, status, detail)
    }
    private val apps = linkedMapOf(
        "youtube" to Pair("YouTube", "com.google.android.youtube"),
        "chrome" to Pair("Chrome", "com.android.chrome"),
        "whatsapp" to Pair("WhatsApp", "com.whatsapp"),
        "gmail" to Pair("Gmail", "com.google.android.gm")
    )

    private val supervisedControl = SkySupervisedControl(host)

    /** La confianza local no sustituye la confirmación de cada envío. */
    private fun localAppAuthorized(id: String): Boolean =
        allowed.getBoolean(id, false) ||
            supervisedControl.isAuthorized()

    /**
     * Prepare a real WhatsApp composer. SKY never presses Send or reads chats.
     * The user chooses the recipient and confirms the message in WhatsApp.
     */
    fun prepareWhatsApp(draft: SkyMessagingIntent.Draft) {
        if (!localAppAuthorized("whatsapp")) {
            feedback("Activá el control supervisado en Configuración de SKY para continuar.")
            return
        }
        val text = SkyMessagingIntent.preparedText(draft)
        AlertDialog.Builder(host)
            .setTitle("SKY · Mensaje para " + draft.recipient)
            .setMessage("Voy a preparar este texto en WhatsApp:\n\n" + text +
                "\n\nEn WhatsApp seleccioná el chat de «" + draft.recipient +
                "» y confirmá el envío. SKY no lo enviará automáticamente.")
            .setPositiveButton("ABRIR WHATSAPP") { _, _ ->
                val intent = Intent(Intent.ACTION_SEND).apply {
                    type = "text/plain"
                    setPackage("com.whatsapp")
                    putExtra(Intent.EXTRA_TEXT, text)
                }
                launch(intent, "Abrí WhatsApp con tu mensaje preparado. " +
                    "Elegí el destinatario y pulsá Enviar si estás de acuerdo.")
            }
            .setNegativeButton("Cancelar") { _, _ ->
                receipt("Preparar WhatsApp", "REJECTED", "El propietario canceló la preparación")
                feedback("No preparé ningún mensaje en WhatsApp.")
            }
            .show()
    }

    fun run(action: SkyDailyCommandParser.Command, origin: SkyActionTrustBoundary.Origin) {
        if (!SkyActionTrustBoundary.allowsLocalCommand(origin)) {
            receipt("Comando Android", "REJECTED",
                "Origen no autorizado; los datos externos y respuestas IA no son órdenes")
            feedback("Por seguridad solo ejecuto acciones que vos me ordenés directamente.")
            return
        }
        when (action) {
            is SkyDailyCommandParser.Command.Alarm -> alarm(action)
            is SkyDailyCommandParser.Command.Timer -> timer(action.seconds)
            is SkyDailyCommandParser.Command.OpenApp -> installedApps.requestLaunch(action.app)
            SkyDailyCommandParser.Command.ShowApps -> installedApps.showCatalog()
            SkyDailyCommandParser.Command.Capabilities -> explainCapabilities()
            is SkyDailyCommandParser.Command.Note -> confirmNote(action.value, origin)
            is SkyDailyCommandParser.Command.WebSearch -> webSearch(action.query)
            is SkyDailyCommandParser.Command.Share -> share(action.app, action.value)
            SkyDailyCommandParser.Command.ShowNotes -> showNotes()
            is SkyDailyCommandParser.Command.Unsupported -> feedback(action.reason)
        }
    }

    private fun explainCapabilities() {
        val count = runCatching { installedApps.discover().size }.getOrDefault(0)
        feedback(
            "Puedo abrir las aplicaciones instaladas en tu teléfono cuando Android " +
                "lo permita; detecto $count aplicaciones con acceso de inicio. " +
                "Probá «abre Netflix», «abrí Word», «mostrame mis aplicaciones» " +
                "o «pon una canción en Spotify». " +
                "También puedo solicitar alarmas, guardar notas, preparar textos " +
                "para compartir y controlar la música. " +
                "Para noticias e información actual puedo consultar Google con internet. " +
                "Todavía no puedo navegar ni escribir libremente dentro de todas " +
                "las aplicaciones o confirmar una reproducción sin comprobarla. " +
                "Algunas acciones exigen desbloqueo, autorización o un paso tuyo."
        )
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
            .setNegativeButton("Cancelar") { _, _ ->
                receipt("Temporizador Android", "REJECTED", "El propietario canceló el temporizador")
                feedback("No solicité ningún temporizador.")
            }
            .show()
    }

    private fun webSearch(query: String) {
        val uri = android.net.Uri.parse("https://www.google.com/search?q=" +
            android.net.Uri.encode(query))
        val intent = Intent(Intent.ACTION_VIEW, uri)
        launch(intent, "Abrí en el navegador una búsqueda de: " + query.take(90))
    }

    /**
     * A note changes private on-device data. Unlike a general one-time app
     * consent, every saved note needs a specific confirmation. The shared SKY
     * policy only validates intent; Android still performs the actual write.
     */
    private fun confirmNote(value: String, origin: SkyActionTrustBoundary.Origin) {
        val originName = when (origin) {
            SkyActionTrustBoundary.Origin.OWNER_TYPED -> "owner_typed"
            SkyActionTrustBoundary.Origin.OWNER_SPOKEN -> "owner_spoken"
            else -> "untrusted"
        }
        val pending = SkyCoreContract.inspect(host, "file_write", originName,
            platformPermission = true)
        if (pending.reason != "per_action_approval") {
            receipt("Guardar nota local", "REJECTED", "Política SKY impidió el guardado")
            feedback("Esta acción no está autorizada. No se guardó la nota.")
            return
        }
        AlertDialog.Builder(host)
            .setTitle("SKY · Confirmar nota privada")
            .setMessage("¿Querés guardar esta nota en tu teléfono?\\n\\n" +
                value.trim().take(250))
            .setPositiveButton("GUARDAR") { _, _ ->
                val decision = SkyCoreContract.inspect(host, "file_write", originName,
                    perActionApproved = true, platformPermission = true)
                if (decision.allowed) saveNote(value)
                else {
                    receipt("Guardar nota local", "REJECTED",
                        "No se concedió autorización válida para esta nota")
                    feedback("Por seguridad no guardé la nota.")
                }
            }
            .setNegativeButton("Cancelar") { _, _ ->
                receipt("Guardar nota local", "REJECTED", "El propietario canceló la nota")
            }
            .show()
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
        val committed = prefs.edit().putString(key, limited.toString()).commit()
        // La escritura confirmada no basta: releer el último valor almacenado.
        val readBack = if (committed) runCatching {
            val saved = JSONArray(prefs.getString(key, "[]"))
            saved.length() > 0 &&
                saved.optJSONObject(saved.length() - 1)?.optString("text") == clean
        }.getOrDefault(false) else false
        if (readBack) {
            receipt("Guardar nota local", "VERIFIED_LOCAL",
                "La última nota se releyó desde almacenamiento local de SKY")
            feedback("Nota guardada y comprobada en SKY. Decí «SKY, mostrame mis notas» para verla.")
        } else {
            receipt("Guardar nota local", "FAILED", "Guardado no confirmado tras releer almacenamiento")
            feedback("No pude comprobar que la nota quedara guardada. Revisá el almacenamiento.")
        }
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
        if (!localAppAuthorized(id)) {
            feedback("Activá el control supervisado de SKY en Configuración antes de compartir.")
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
        shareDialog.setNegativeButton("Cancelar") { _, _ ->
            receipt("Preparar texto para compartir", "REJECTED", "El propietario canceló la preparación")
            feedback("No compartí ningún texto.")
        }.show()
    }

    private fun launch(intent: Intent, message: String) {
        try {
            host.startActivity(intent)
            receipt("Intent Android " + intent.action.orEmpty(), "SENT",
                "Android aceptó la solicitud; resultado final requiere verificación")
            feedback(message)
        } catch (_: ActivityNotFoundException) {
            receipt("Intent Android " + intent.action.orEmpty(), "FAILED", "Aplicación no encontrada")
            feedback("No se encontró una aplicación Android compatible.")
        } catch (_: SecurityException) {
            receipt("Intent Android " + intent.action.orEmpty(), "FAILED", "Permiso denegado")
            feedback("Android bloqueó la acción por falta de autorización.")
        } catch (_: Exception) {
            receipt("Intent Android " + intent.action.orEmpty(), "FAILED", "No se inició la acción")
            feedback("No se pudo iniciar la acción solicitada.")
        }
    }
}
