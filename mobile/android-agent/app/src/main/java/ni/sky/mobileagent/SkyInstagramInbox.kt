package ni.sky.mobileagent

import android.app.Activity
import android.app.AlertDialog
import android.graphics.Color
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import java.net.HttpURLConnection
import java.net.URL
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale
import java.util.concurrent.atomic.AtomicBoolean
import org.json.JSONArray
import org.json.JSONObject

/**
 * Read-only Instagram inbox backed by real verified Meta webhook events.
 * Requires an already-paired Android credential; never uses an owner key or Meta token.
 * Server currently provides the latest 50 events and no read/unread status.
 */
internal class SkyInstagramInbox(
    private val host: Activity,
    private val deviceCredential: String
) {
    private val endpoint =
        "https://jojzuaeqmjgnqikpnfxk.supabase.co/functions/v1/sky-instagram"
    private val ui = Handler(Looper.getMainLooper())
    private val open = AtomicBoolean(false)
    private val loading = AtomicBoolean(false)
    private lateinit var status: TextView
    private lateinit var contents: LinearLayout
    private var dialog: AlertDialog? = null
    private fun dp(value: Int) = SkyPremiumUi.dp(host, value)

    private val refresh = object : Runnable {
        override fun run() {
            if (!open.get()) return
            if (dialog?.isShowing == true) load()
            ui.postDelayed(this, 30_000L)
        }
    }

    fun show() {
        if (deviceCredential.isBlank()) return
        val shell = LinearLayout(host).apply {
            orientation = LinearLayout.VERTICAL
            background = SkyPremiumUi.shape(host, SkyPremiumUi.background, 22)
            setPadding(dp(16), dp(17), dp(16), dp(14))
        }
        shell.addView(SkyPremiumUi.label(host, "◈  SKY · INSTAGRAM", 12f,
            SkyPremiumUi.cyan, true))
        shell.addView(SkyPremiumUi.label(host, "Bandeja privada", 23f,
            SkyPremiumUi.white, true))
        shell.addView(SkyPremiumUi.label(host,
            "Mensajes reales recibidos por Meta · Solo lectura", 12f,
            SkyPremiumUi.muted))
        val toolbar = LinearLayout(host).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(0, dp(13), 0, dp(11))
        }
        val refreshButton = SkyPremiumUi.label(host, "↻  Actualizar", 14f,
            SkyPremiumUi.cyan, true).apply {
            background = SkyPremiumUi.shape(host, SkyPremiumUi.elevated, 14)
            setPadding(dp(13), dp(10), dp(13), dp(10))
            isClickable = true
            isFocusable = true
            contentDescription = "Actualizar mensajes de Instagram"
            setOnClickListener { load() }
        }
        toolbar.addView(refreshButton)
        toolbar.addView(SkyPremiumUi.label(host, "  Cada 30 segundos", 11f,
            SkyPremiumUi.muted))
        shell.addView(toolbar)
        status = SkyPremiumUi.label(host, "Conectando con SKY…", 13f,
            SkyPremiumUi.muted)
        shell.addView(status)
        contents = LinearLayout(host).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, dp(9), 0, dp(6))
        }
        shell.addView(ScrollView(host).apply {
            isFillViewport = true
            isVerticalScrollBarEnabled = false
            addView(contents)
        }, LinearLayout.LayoutParams(-1, 0, 1f))
        shell.addView(SkyPremiumUi.label(host,
            "Solo los últimos 50 eventos del servidor. " +
                "Meta no informa aquí si un mensaje fue leído. " +
                "SKY no envía respuestas desde esta bandeja.", 11f,
            SkyPremiumUi.muted))
        val close = SkyPremiumUi.label(host, "Cerrar bandeja", 15f,
            SkyPremiumUi.white, true).apply {
            gravity = Gravity.CENTER
            background = SkyPremiumUi.shape(host, SkyPremiumUi.elevated, 14)
            setPadding(dp(14), dp(12), dp(14), dp(12))
            isClickable = true
            isFocusable = true
            setOnClickListener { dialog?.dismiss() }
        }
        shell.addView(close, LinearLayout.LayoutParams(-1, -2).apply {
            topMargin = dp(12)
        })
        dialog = AlertDialog.Builder(host).setView(shell).create().also { shown ->
            shown.setOnDismissListener {
                open.set(false)
                ui.removeCallbacks(refresh)
            }
            open.set(true)
            SkyPremiumUi.showDialog(host, shown, 0.87)
        }
        load()
        ui.postDelayed(refresh, 30_000L)
    }

    private fun getJson(path: String): JSONObject {
        require(path == "/mobile-profile" || path == "/mobile-events")
        val connection = URL(endpoint + path).openConnection() as HttpURLConnection
        try {
            connection.requestMethod = "GET"
            connection.connectTimeout = 8_000
            connection.readTimeout = 10_000
            connection.instanceFollowRedirects = false
            connection.setRequestProperty("Accept", "application/json")
            connection.setRequestProperty("Cache-Control", "no-store")
            connection.setRequestProperty("Authorization", "Bearer " + deviceCredential)
            val statusCode = connection.responseCode
            if (statusCode == 401 || statusCode == 403)
                error("Acceso del teléfono vencido. Volvé a vincularlo desde Conexión segura.")
            if (statusCode !in 200..299)
                error("El servidor no respondió correctamente (HTTP " + statusCode + ").")
            val text = connection.inputStream.bufferedReader(Charsets.UTF_8).use {
                it.readText().take(700_001)
            }
            require(text.length <= 700_000) { "La respuesta excede el límite de seguridad." }
            return JSONObject(text)
        } finally {
            connection.disconnect()
        }
    }

    private fun load() {
        if (!open.get() || !loading.compareAndSet(false, true)) return
        status.text = "Consultando mensajes auténticos…"
        Thread {
            val response = runCatching {
                val identity = getJson("/mobile-profile")
                if (!identity.optBoolean("token_valid") ||
                    !identity.optBoolean("profile_verified")) {
                    error("La identidad de Instagram no está verificada. " +
                        "Usá primero «Verificar identidad real con Meta».")
                }
                val profileId = identity.optString("profile_id")
                require(profileId.matches(Regex("[0-9]{5,30}"))) {
                    "Meta no devolvió un identificador de perfil válido."
                }
                val handle = identity.optString("username").take(30)
                val payload = getJson("/mobile-events")
                val events = payload.optJSONArray("events") ?: JSONArray()
                val messages = (0 until events.length()).mapNotNull { index ->
                    events.optJSONObject(index)
                }.filter {
                    it.optString("event_type") == "message" &&
                        SkyInstagramInboxRules.belongsToProfile(
                            profileId, it.optString("ig_account_id")) &&
                        SkyInstagramInboxRules.isIncoming(
                            profileId, it.optString("actor_id"))
                }
                Pair(handle, messages)
            }
            host.runOnUiThread {
                loading.set(false)
                if (!open.get() || host.isFinishing) return@runOnUiThread
                response.onSuccess { (handle, messages) -> render(handle, messages) }
                    .onFailure {
                        status.text = "No se pudo actualizar la bandeja."
                        if (contents.childCount == 0) {
                            contents.addView(SkyPremiumUi.label(host,
                                it.message ?: "Revisá la conexión o la autorización.",
                                14f, SkyPremiumUi.white))
                        }
                    }
            }
        }.start()
    }

    private fun render(handle: String, messages: List<JSONObject>) {
        contents.removeAllViews()
        status.text = "@" + handle + "  ·  " + messages.size +
            (if (messages.size == 1) " mensaje" else " mensajes") +
            "  ·  Solo recepción"
        if (messages.isEmpty()) {
            contents.addView(SkyPremiumUi.label(host,
                "Todavía no hay mensajes recibidos en el historial del webhook. " +
                    "Enviá un mensaje desde otra cuenta y tocá Actualizar.",
                14f, SkyPremiumUi.white))
            return
        }
        val bySender = LinkedHashMap<String, MutableList<JSONObject>>()
        messages.forEach { event ->
            val sender = event.optString("actor_id")
            bySender.getOrPut(sender) { mutableListOf() }.add(event)
        }
        bySender.forEach { (sender, thread) ->
            val latest = thread.first()
            val summary = SkyInstagramInboxRules.preview(
                latest.optString("message_text"))
            val label = SkyInstagramInboxRules.senderLabel(sender)
            val card = LinearLayout(host).apply {
                orientation = LinearLayout.VERTICAL
                background = SkyPremiumUi.shape(host, SkyPremiumUi.card, 17)
                setPadding(dp(15), dp(13), dp(15), dp(13))
                isClickable = true
                isFocusable = true
                contentDescription = "Abrir conversación de " + label
                setOnClickListener { showThread(label, thread) }
            }
            card.addView(SkyPremiumUi.label(host,
                "✉  " + label + "  ·  " + thread.size, 15f,
                SkyPremiumUi.white, true))
            card.addView(SkyPremiumUi.label(host, summary, 13f,
                SkyPremiumUi.muted).apply { maxLines = 2 })
            card.addView(SkyPremiumUi.label(host,
                "Recibido: " + localTime(latest.optString("received_at")),
                11f, SkyPremiumUi.cyan))
            contents.addView(card, LinearLayout.LayoutParams(-1, -2).apply {
                bottomMargin = dp(10)
            })
        }
    }

    private fun showThread(sender: String, thread: List<JSONObject>) {
        if (!open.get()) return
        val body = LinearLayout(host).apply {
            orientation = LinearLayout.VERTICAL
            background = SkyPremiumUi.shape(host, SkyPremiumUi.background, 16)
            setPadding(dp(15), dp(15), dp(15), dp(15))
        }
        thread.asReversed().forEach { event ->
            val box = LinearLayout(host).apply {
                orientation = LinearLayout.VERTICAL
                background = SkyPremiumUi.shape(host, SkyPremiumUi.card, 15)
                setPadding(dp(12), dp(10), dp(12), dp(10))
            }
            box.addView(SkyPremiumUi.label(host,
                SkyInstagramInboxRules.preview(
                    event.optString("message_text"), 1800), 14f, SkyPremiumUi.white))
            box.addView(SkyPremiumUi.label(host,
                "Recibido en SKY: " + localTime(event.optString("received_at")),
                11f, SkyPremiumUi.cyan))
            body.addView(box, LinearLayout.LayoutParams(-1, -2).apply {
                bottomMargin = dp(9)
            })
        }
        AlertDialog.Builder(host)
            .setTitle(sender + " · Instagram")
            .setView(ScrollView(host).apply { addView(body) })
            .setPositiveButton("Cerrar", null)
            .show()
    }

    private fun localTime(value: String): String = try {
        OffsetDateTime.parse(value).atZoneSameInstant(ZoneId.systemDefault())
            .format(DateTimeFormatter.ofPattern("dd/MM/yyyy · HH:mm",
                Locale("es", "NI")))
    } catch (_: Exception) {
        "hora no disponible"
    }
}
