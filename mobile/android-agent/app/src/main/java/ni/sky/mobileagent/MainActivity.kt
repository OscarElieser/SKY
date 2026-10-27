package ni.sky.mobileagent

import android.app.Activity
import android.app.AlertDialog
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.text.InputType
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import org.json.JSONObject
import java.util.concurrent.Executors

/**
 * Android Agent: no hay automatización encubierta. Solo recibe solicitudes
 * cuando está visible y requiere permisos por app y confirmación por comando.
 */
class MainActivity : Activity() {
    private val executor = Executors.newSingleThreadExecutor()
    private val handler = Handler(Looper.getMainLooper())
    private lateinit var tokens: PrivateTokenStore
    private lateinit var serverInput: EditText
    private lateinit var deviceInput: EditText
    private lateinit var codeInput: EditText
    private lateinit var status: TextView
    @Volatile private var pendingCommand: String? = null
    @Volatile private var polling = false
    private var visible = false
    private val apps = linkedMapOf(
        "youtube" to Pair("YouTube", "com.google.android.youtube"),
        "chrome" to Pair("Chrome", "com.android.chrome"),
        "whatsapp" to Pair("WhatsApp", "com.whatsapp"),
        "gmail" to Pair("Gmail", "com.google.android.gm")
    )
    private val permissions by lazy { getSharedPreferences("sky_mobile_allowed_apps", MODE_PRIVATE) }

    private fun description(value: String) = TextView(this).apply {
        text = value
        textSize = 16f
        setPadding(8, 12, 8, 12)
    }
    private fun input(placeholder: String, secret: Boolean = false) = EditText(this).apply {
        hint = placeholder
        setSingleLine(true)
        inputType = if (secret) InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
                    else InputType.TYPE_CLASS_TEXT
    }
    private fun actionButton(value: String, action: () -> Unit) = Button(this).apply {
        text = value
        setOnClickListener { action() }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        tokens = PrivateTokenStore(this)
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 24, 24, 24)
        }
        val scroll = ScrollView(this)
        scroll.addView(content)
        setContentView(scroll)
        content.addView(description("SKY MOBILE AGENT — control bajo tu autorización"))
        content.addView(description("Permisos por aplicación. Cada orden requiere un toque de confirmación."))
        serverInput = input("Servidor HTTPS privado de SKY")
        serverInput.setText(tokens.server())
        deviceInput = input("Nombre del teléfono")
        deviceInput.setText("Mi Android")
        codeInput = input("Código temporal de SKY", true)
        content.addView(serverInput)
        content.addView(deviceInput)
        content.addView(codeInput)
        content.addView(actionButton("Vincular teléfono") { pair() })
        content.addView(actionButton("Revocar acceso") { revoke() })
        status = description(if (tokens.token().isEmpty()) "Sin vincular" else "Vinculado: consultas habilitadas al abrir esta pantalla")
        content.addView(status)
        content.addView(description("Aplicaciones permitidas (ninguna activa por defecto):"))
        for ((id, item) in apps) {
            content.addView(CheckBox(this).apply {
                text = "Permitir " + item.first
                isChecked = permissions.getBoolean(id, false)
                setOnCheckedChangeListener { _, granted ->
                    permissions.edit().putBoolean(id, granted).apply()
                }
            })
        }
        content.addView(actionButton("Consultar órdenes ahora") { poll() })
        content.addView(actionButton("Estado de mi servidor SKY") { checkHomeStatus() })
        content.addView(description("SKY consulta cada 6 segundos mientras la app está visible. Esta versión no funciona con pantalla bloqueada."))
    }

    override fun onResume() {
        super.onResume()
        visible = true
        handler.post(pollLoop)
    }
    override fun onPause() {
        visible = false
        handler.removeCallbacks(pollLoop)
        super.onPause()
    }
    override fun onDestroy() {
        handler.removeCallbacks(pollLoop)
        executor.shutdown()
        super.onDestroy()
    }

    private val pollLoop = object : Runnable {
        override fun run() {
            if (!visible) return
            poll()
            handler.postDelayed(this, 6000)
        }
    }
    private fun execute(background: () -> Unit) {
        executor.execute {
            try { background() }
            catch (exc: Exception) { setStatus("Error de SKY: " + (exc.message ?: "Conexión fallida")) }
        }
    }
    private fun setStatus(value: String) = runOnUiThread { status.text = value }

    private fun pair() {
        if (tokens.deviceId().isNotEmpty()) {
            setStatus("Revocá el teléfono anterior antes de volver a vincularlo.")
            return
        }
        val server = serverInput.text.toString()
        val label = deviceInput.text.toString().trim()
        val code = codeInput.text.toString().trim()
        execute {
            val result = SkyNetwork.request(server, "/api/sky/mobile-agent/pair/complete",
                "POST", data = JSONObject().put("code", code).put("label", label))
            tokens.save(SkyNetwork.validateServer(server),
                result.getString("device_id"), result.getString("token"))
            runOnUiThread { codeInput.setText("") }
            setStatus("Vinculado: " + label + ". Elegí aplicaciones permitidas.")
        }
    }

    private fun poll() {
        val id = tokens.deviceId()
        val token = tokens.token()
        if (id.isEmpty() || token.isEmpty() || pendingCommand != null || polling) return
        polling = true
        execute {
            try {
                val response = SkyNetwork.request(tokens.server(),
                    "/api/sky/mobile-agent/devices/" + id + "/next", "GET", token)
                val command = response.optJSONObject("command") ?: return@execute
                pendingCommand = command.getString("id")
                runOnUiThread { approve(command) }
            } finally {
                polling = false
            }
        }
    }

    private fun approve(command: JSONObject) {
        val id = command.optString("id")
        val target = command.optString("target")
        val app = apps[target]
        if (!visible || command.optString("action") != "launch_app" ||
            app == null || !permissions.getBoolean(target, false)) {
            finish(id, "REJECTED", "No está permitida esta aplicación")
            return
        }
        AlertDialog.Builder(this)
            .setTitle("SKY solicita abrir " + app.first)
            .setMessage("¿Querés abrir " + app.first + "? La autorización vale solo para esta orden.")
            .setPositiveButton("Permitir una vez") { _, _ ->
                val intent = packageManager.getLaunchIntentForPackage(app.second)
                if (intent == null) {
                    finish(id, "FAILED", "Aplicación no instalada o no visible")
                } else {
                    try {
                        startActivity(intent)
                        finish(id, "SENT", "Android recibió la orden, sin verificación de carga")
                    } catch (_: Exception) {
                        finish(id, "FAILED", "Android rechazó la apertura")
                    }
                }
            }
            .setNegativeButton("Denegar") { _, _ -> finish(id, "REJECTED", "Solicitud denegada") }
            .setOnCancelListener { finish(id, "REJECTED", "Solicitud cancelada") }
            .show()
    }

    private fun finish(command: String, state: String, detail: String) {
        val id = tokens.deviceId()
        val token = tokens.token()
        execute {
            try {
                SkyNetwork.request(tokens.server(),
                    "/api/sky/mobile-agent/devices/" + id + "/commands/" + command + "/complete",
                    "POST", token, JSONObject().put("state", state).put("message", detail))
                setStatus(state + ": " + detail)
            } finally {
                pendingCommand = null
            }
        }
    }

    private fun revoke() {
        val id = tokens.deviceId()
        if (id.isEmpty()) { setStatus("Este teléfono no está vinculado."); return }
        AlertDialog.Builder(this).setTitle("Revocar acceso de SKY")
            .setMessage("Se invalidará el token de este teléfono en el servidor. ¿Continuar?")
            .setPositiveButton("Revocar") { _, _ ->
                execute {
                    SkyNetwork.request(tokens.server(),
                        "/api/sky/mobile-agent/devices/" + id + "/revoke-self",
                        "POST", tokens.token(), JSONObject())
                    tokens.clear()
                    setStatus("Acceso revocado. El teléfono quedó desconectado.")
                }
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }
}
