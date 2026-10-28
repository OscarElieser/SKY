package ni.sky.mobileagent

import android.app.Activity
import android.app.AlertDialog
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.text.InputFilter
import android.text.InputType
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import org.json.JSONArray
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
    private lateinit var chatCodeInput: EditText
    private lateinit var chatInput: EditText
    private lateinit var chatOutput: TextView
    private lateinit var voicePanel: SkyEyeVoicePanel
    private lateinit var cloudConsent: CheckBox
    private lateinit var privateConsent: CheckBox
    private val chatHistory = JSONArray()
    @Volatile private var chatPending = false
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
        voicePanel = SkyEyeVoicePanel(this) { transcript ->
            chatInput.setText(transcript)
            if (tokens.chatToken().isEmpty()) {
                voicePanel.showError("Para hablar con SKY primero activá el chat autorizado.")
            } else {
                sendChat()
            }
        }
        content.addView(voicePanel)
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
        content.addView(description("SKY CHAT — texto. Requiere permiso separado del propietario."))
        chatCodeInput = input("Código temporal de chat autorizado por el dueño", true)
        content.addView(chatCodeInput)
        content.addView(actionButton("Activar chat por 24 horas") { pairChat() })
        chatInput = EditText(this).apply {
            hint = "Escribí a SKY..."
            setSingleLine(false)
            minLines = 2
            maxLines = 5
            filters = arrayOf(InputFilter.LengthFilter(4000))
        }
        content.addView(chatInput)
        cloudConsent = CheckBox(this).apply {
            text = "Permito usar la nube para ESTE mensaje (incluye historial enviado)"
            isChecked = false
        }
        privateConsent = CheckBox(this).apply {
            text = "Permito transmitir datos privados de ESTE mensaje e historial a la nube"
            isChecked = false
        }
        content.addView(cloudConsent)
        content.addView(privateConsent)
        content.addView(actionButton("Enviar mensaje a SKY") { sendChat() })
        chatOutput = description("Chat limitado a texto. No controla dispositivos ni accede a archivos.")
        content.addView(chatOutput)
        content.addView(description("SKY consulta cada 6 segundos mientras la app está visible. Esta versión no funciona con pantalla bloqueada."))
    }

    override fun onResume() {
        super.onResume()
        visible = true
        handler.post(pollLoop)
    }
    override fun onPause() {
        visible = false
        if (::voicePanel.isInitialized) voicePanel.onPausePanel()
        handler.removeCallbacks(pollLoop)
        super.onPause()
    }
    override fun onDestroy() {
        handler.removeCallbacks(pollLoop)
        if (::voicePanel.isInitialized) voicePanel.close()
        executor.shutdown()
        super.onDestroy()
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == SkyEyeVoicePanel.MICROPHONE_REQUEST &&
            ::voicePanel.isInitialized) {
            voicePanel.onMicrophonePermissionResult(
                grantResults.isNotEmpty() &&
                    grantResults[0] == android.content.pm.PackageManager.PERMISSION_GRANTED
            )
        }
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
            catch (exc: Exception) {
                setStatus("Error de SKY: " + (exc.message ?: "Conexión fallida"))
                runOnUiThread {
                    if (::voicePanel.isInitialized) voicePanel.showError("Falló la conexión con SKY.")
                }
            }
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

    private fun checkHomeStatus() {
        val id = tokens.deviceId()
        val token = tokens.token()
        if (id.isEmpty() || token.isEmpty()) {
            setStatus("Vinculá este teléfono antes de consultar el servidor SKY.")
            return
        }
        execute {
            val reply = SkyNetwork.request(
                tokens.server(),
                "/api/sky/mobile-agent/devices/" + id + "/home-status",
                "GET", token
            )
            val local = if (reply.optBoolean("local_ollama_ready")) "Ollama disponible" else "Ollama no disponible"
            val cloud = if (reply.optBoolean("cloud_configured")) "nube configurada" else "nube sin configurar"
            val mode = if (reply.optBoolean("local_only")) "solo local" else "híbrido permitido"
            setStatus("Servidor SKY conectado. " + local + " · " + cloud + " · modo " + mode +
                ". Este agente aún no tiene permiso de chat.")
        }
    }

    private fun pairChat() {
        val id = tokens.deviceId()
        val agentToken = tokens.token()
        val code = chatCodeInput.text.toString().trim()
        if (id.isEmpty() || agentToken.isEmpty()) {
            setStatus("Primero vinculá el agente Android con SKY.")
            return
        }
        if (code.isEmpty()) {
            setStatus("Generá el código de chat desde el servidor con sesión de propietario y MFA.")
            return
        }
        execute {
            val result = SkyNetwork.requestChat(tokens.server(), "/api/sky/mobile-chat/pair",
                agentToken, JSONObject().put("device_id", id).put("code", code))
            tokens.saveChat(result.getString("token"))
            runOnUiThread { chatCodeInput.setText("") }
            setStatus("Chat autorizado durante 24 horas. No incluye control de dispositivos.")
        }
    }

    private fun sendChat() {
        val id = tokens.deviceId()
        val token = tokens.chatToken()
        val message = chatInput.text.toString().trim()
        if (id.isEmpty() || token.isEmpty()) {
            setStatus("Antes de conversar activá el chat con autorización del propietario.")
            return
        }
        if (message.isEmpty() || chatPending) return
        // Each request requires fresh opt-in; checkboxes are reset immediately.
        val cloud = cloudConsent.isChecked
        val privateData = privateConsent.isChecked
        cloudConsent.isChecked = false
        privateConsent.isChecked = false
        chatPending = true
        voicePanel.showThinking()
        execute {
            try {
                val history = JSONArray()
                val begin = maxOf(0, chatHistory.length() - 8)
                for (i in begin until chatHistory.length()) {
                    history.put(chatHistory.getJSONObject(i))
                }
                val payload = JSONObject()
                    .put("device_id", id)
                    .put("texto", message)
                    .put("historial", history)
                    .put("proveedor", "auto")
                    .put("datos", "privados")
                    .put("autorizar_nube", cloud)
                    .put("autorizar_datos_privados", privateData)
                val reply = SkyNetwork.requestChat(tokens.server(), "/api/sky/mobile-chat/chat",
                    token, payload)
                val answer = reply.optString("respuesta", "SKY no devolvió texto.")
                chatHistory.put(JSONObject().put("role", "user").put("content", message))
                chatHistory.put(JSONObject().put("role", "assistant").put("content", answer.take(2000)))
                while (chatHistory.length() > 8) chatHistory.remove(0)
                runOnUiThread {
                    chatInput.setText("")
                    chatOutput.text = "SKY: " + answer + "\nMotor: " +
                        reply.optString("proveedor", "desconocido")
                    voicePanel.speakReply(answer)
                }
            } finally {
                chatPending = false
            }
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
