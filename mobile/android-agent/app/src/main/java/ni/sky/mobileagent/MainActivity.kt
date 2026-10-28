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
    private lateinit var dailyActions: SkyAndroidActions
    private lateinit var installedApps: SkyInstalledApps
    private lateinit var companionController: SkyCompanionController
    private lateinit var cloudConsent: CheckBox
    private lateinit var privateConsent: CheckBox
    private val chatHistory = JSONArray()
    @Volatile private var chatPending = false
    @Volatile private var pendingCommand: String? = null
    @Volatile private var polling = false
    private var visible = false
    private var showOptionalWindowsLink = false
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

    private lateinit var home: SkyMobileHome
    private var settingsDialog: AlertDialog? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.setFlags(
            android.view.WindowManager.LayoutParams.FLAG_FULLSCREEN,
            android.view.WindowManager.LayoutParams.FLAG_FULLSCREEN
        )
        window.setSoftInputMode(android.view.WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE)
        tokens = PrivateTokenStore(this)
        voicePanel = SkyEyeVoicePanel(this) { transcript ->
            if (!processLocalPanelCommand(transcript, spoken = true) &&
                !processCompanionCommand(transcript) &&
                !processDailyCommand(transcript)) {
                home.openChat()
                chatInput.setText(transcript)
                if (!tokens.cloudEnabled() && tokens.chatToken().isEmpty()) {
                    voicePanel.showError("Activá el chat seguro en Ajustes.")
                    home.showMessage("Activá el chat desde Ajustes para conversar.")
                } else {
                    sendChat()
                }
            }
        }
        voicePanel.setVoiceEnabled(
            getSharedPreferences("sky_voice_settings", MODE_PRIVATE)
                .getBoolean("read_aloud", true)
        )
        home = SkyMobileHome(
            this, voicePanel,
            onSend = { sendChat() },
            onSettings = { showSettings() },
            onChatAccess = { showSettings() },
            onDiagnostics = { checkHomeStatus() }
        )
        status = home.status
        chatInput = home.chatInput
        chatOutput = home.chatOutput
        cloudConsent = home.cloudConsent
        privateConsent = home.privateConsent
        installedApps = SkyInstalledApps(this) { feedback ->
            home.showMessage(feedback)
            if (!isFinishing && voicePanel.isVoiceEnabled()) voicePanel.speakReply(feedback)
        }
        dailyActions = SkyAndroidActions(
            this,
            getSharedPreferences("sky_private_notes", MODE_PRIVATE),
            permissions,
            feedback = { feedback ->
                home.showMessage(feedback)
                if (!isFinishing && voicePanel.isVoiceEnabled()) voicePanel.speakReply(feedback)
            },
            onAccessibilityHelp = { showTextAssistDisclosure() },
            installedApps = installedApps
        )
        companionController = SkyCompanionController { message ->
            voicePanel.express(message)
            home.showMessage(message)
            voicePanel.speakReply(message)
        }
        setContentView(home.root)
        refreshConnection()
        if (tokens.token().isEmpty() && !tokens.cloudEnabled()) {
            home.root.post { if (!isFinishing) showSettings() }
        }
    }

    /**
     * Divulgación explícita de accesibilidad. No habilita permisos de forma
     * oculta y no permite ejecución de planes autónomos del modelo.
     */
    private fun showTextAssistDisclosure() {
        AlertDialog.Builder(this)
            .setTitle("SKY · Escritura asistida opcional")
            .setMessage(
                "Si aceptás, Android permitirá a SKY detectar cuándo enfocás " +
                "un campo de texto en WhatsApp o Gmail para escribir SOLO el " +
                "texto que vos solicitaste y aprobaste.\n\n" +
                "SKY no lee conversaciones completas, no registra textos " +
                "de otras apps, no escribe contraseñas y NUNCA toca Enviar. " +
                "La solicitud vence en 45 segundos y requiere un campo vacío.\n\n" +
                "Podés desactivar este permiso cuando quieras en " +
                "Ajustes de Android > Accesibilidad."
            )
            .setPositiveButton("Acepto y abrir ajustes") { _, _ ->
                getSharedPreferences("sky_assistive_text", MODE_PRIVATE)
                    .edit().putBoolean("consent", true).apply()
                try {
                    startActivity(android.content.Intent(
                        android.provider.Settings.ACTION_ACCESSIBILITY_SETTINGS
                    ))
                } catch (_: Exception) {
                    home.showMessage("No pude abrir Ajustes de Accesibilidad.")
                }
            }
            .setNegativeButton("No aceptar", null)
            .show()
    }

    /** Comprobaciones de capacidad local; no confundir con ejecución validada. */
    private fun showDeviceDiagnostics() {
        val pm = packageManager
        val mic = checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) ==
            android.content.pm.PackageManager.PERMISSION_GRANTED
        val recognize = android.speech.SpeechRecognizer.isRecognitionAvailable(this)
        val clock = android.content.Intent(android.provider.AlarmClock.ACTION_SET_ALARM)
            .resolveActivity(pm) != null
        val notes = runCatching {
            org.json.JSONArray(getSharedPreferences("sky_private_notes", MODE_PRIVATE)
                .getString("sky_notes_v1", "[]")).length()
        }.getOrDefault(0)
        val lines = listOf(
            "Android: " + android.os.Build.VERSION.RELEASE,
            "Micrófono autorizado: " + if (mic) "Sí" else "No",
            "Reconocedor de voz disponible: " + if (recognize) "Sí" else "No",
            "Motor de voz listo: " + if (voicePanel.isSpeechEngineReady()) "Sí" else "No",
            "Reloj compatible con alarmas: " + if (clock) "Detectado" else "No detectado",
            "Notas guardadas: " + notes,
            "Aplicaciones abribles visibles: " + installedApps.discover().size,
            "Escritura asistida conectada: " +
                if (SkyTextAssistService.enabled()) "Sí" else "No",
            "Vinculación SKY Core: " + if (tokens.token().isNotEmpty()) "Configurada" else "Pendiente",
            "Chat: " + if (tokens.chatToken().isNotEmpty()) "Token almacenado" else "Sin autorizar"
        ).joinToString("\n")
        AlertDialog.Builder(this)
            .setTitle("SKY · Autodiagnóstico Android")
            .setMessage(lines + "\n\n" +
                "Este chequeo verifica capacidades locales, no prueba conexiones remotas " +
                "ni garantiza que una alarma haya sonado o un mensaje se haya enviado.")
            .setPositiveButton("Cerrar", null)
            .show()
    }

    private fun processCompanionCommand(message: String): Boolean =
        companionController.handle(message)

    /** Acción autorizada del teléfono, incluso si SKY Core está desconectado. */
    private fun processDailyCommand(message: String): Boolean {
        val command = SkyDailyCommandParser.parse(message) ?: return false
        dailyActions.run(command)
        return true
    }

    /** Las órdenes de interfaz se ejecutan localmente, incluso sin SKY Core. */
    private fun processLocalPanelCommand(message: String, spoken: Boolean): Boolean {
        val route = SkyMobileIntentRouter.route(message) ?: return false
        val feedback = when (route.kind) {
            SkyMobileIntentRouter.Action.Kind.OPEN_CHAT -> {
                home.openChat()
                "Abrí el panel de conversación."
            }
            SkyMobileIntentRouter.Action.Kind.OPEN_MODULE -> {
                home.openModule(route.module)
                "Abrí el panel solicitado. Decime qué querés hacer."
            }
            SkyMobileIntentRouter.Action.Kind.CLOSE_PANEL -> {
                home.closePanel()
                "Listo. Volvimos a la pantalla de SKY."
            }
        }
        if (spoken) voicePanel.speakReply(feedback)
        return true
    }

    @Deprecated("Usamos la navegación local de los paneles de SKY")
    override fun onBackPressed() {
        if (::home.isInitialized && home.isPanelOpen()) {
            home.closePanel()
        } else {
            super.onBackPressed()
        }
    }

    private fun refreshConnection() {
        home.setConnection(tokens.token().isNotEmpty(), tokens.chatToken().isNotEmpty(), tokens.cloudEnabled())
    }

    /** La vinculación solo se muestra si aún no existe un token válido. */
    private fun showSettings() {
        if (isFinishing) return
        settingsDialog?.dismiss()
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(30, 18, 30, 18)
        }
        val linked = tokens.token().isNotEmpty() && tokens.deviceId().isNotEmpty()
        content.addView(description("SKY Android · Ajustes y permisos"))
        content.addView(description("MODO INDEPENDIENTE · No necesitás Windows, Tailscale ni código de vinculación."))
        if (tokens.cloudEnabled()) {
            content.addView(description("SKY móvil está activada. Conversa con Gemini por internet. " +
                "La voz, los ojos y las acciones locales funcionan independientemente del PC."))
            content.addView(actionButton("Desactivar nube y borrar mi clave") {
                tokens.clearPersonalCloudKey()
                refreshConnection()
                settingsDialog?.dismiss()
                showSettings()
            })
        } else {
            content.addView(description("Prueba personal: necesitás tu propia clave Gemini API. " +
                "La clave queda cifrada con Android Keystore, pero las claves utilizadas desde " +
                "un cliente móvil pueden extraerse en un teléfono comprometido. " +
                "No utilizar esta modalidad en una APK distribuida al público. " +
                "Tu uso puede consumir cuota o generar costos en Google."))
            val personalKey = input("Clave personal de Gemini API", true)
            val permission = CheckBox(this).apply {
                text = "Autorizo enviar mis mensajes y el contexto reciente a Google Gemini. " +
                    "Entiendo que puedo desactivar SKY Cloud y borrar la clave."
            }
            content.addView(personalKey)
            content.addView(permission)
            content.addView(actionButton("Abrir Google AI Studio para obtener clave") {
                startActivity(android.content.Intent(android.content.Intent.ACTION_VIEW,
                    android.net.Uri.parse("https://aistudio.google.com/apikey")))
            })
            content.addView(actionButton("ACTIVAR SKY ANDROID INDEPENDIENTE") {
                val value = personalKey.text.toString().trim()
                if (!permission.isChecked) {
                    setStatus("Primero autorizá el envío de mensajes a Gemini.")
                } else if (!SkyPhoneCloud.validPersonalKey(value)) {
                    setStatus("Ingresá una clave personal válida de Gemini API.")
                } else {
                    tokens.savePersonalCloudKey(value)
                    personalKey.setText("")
                    refreshConnection()
                    settingsDialog?.dismiss()
                    showSettings()
                }
            })
        }
        content.addView(actionButton(if (showOptionalWindowsLink || linked)
            "Ocultar conexión Windows (opcional)" else "Conexión Windows (opcional)") {
            showOptionalWindowsLink = !showOptionalWindowsLink
            showSettings()
        })
        if (!linked && showOptionalWindowsLink) {
            content.addView(description("Conectá el celular con tu SKY Core mediante HTTPS privado."))
            serverInput = input("URL HTTPS privada de SKY")
            serverInput.setText(tokens.server())
            deviceInput = input("Nombre del teléfono")
            deviceInput.setText("Mi Android")
            codeInput = input("Código temporal de vinculación", true)
            content.addView(serverInput)
            content.addView(deviceInput)
            content.addView(codeInput)
            content.addView(actionButton("Vincular teléfono") { pair() })
        } else if (showOptionalWindowsLink && linked) {
            content.addView(description("Dispositivo vinculado. Las claves permanecen protegidas."))
            if (tokens.chatToken().isEmpty()) {
                content.addView(description("Chat: necesita autorización independiente del propietario."))
                chatCodeInput = input("Código temporal del chat", true)
                content.addView(chatCodeInput)
                content.addView(actionButton("Activar chat por 24 horas") { pairChat() })
            } else {
                content.addView(description("Chat autorizado. Renovalo cuando venza su sesión."))
            }
            content.addView(description("Aplicaciones permitidas"))
            for ((id, item) in apps) {
                content.addView(CheckBox(this).apply {
                    text = "Permitir " + item.first
                    isChecked = permissions.getBoolean(id, false)
                    setOnCheckedChangeListener { _, granted ->
                        permissions.edit().putBoolean(id, granted).apply()
                    }
                })
            }
            content.addView(actionButton("Consultar órdenes") { poll() })
            content.addView(actionButton("Estado del servidor") { checkHomeStatus() })
            content.addView(actionButton("Revocar acceso del teléfono") { revoke() })
        }
        if (!linked) {
            content.addView(description("Aplicaciones locales autorizadas"))
            for ((id, item) in apps) {
                content.addView(CheckBox(this).apply {
                    text = "Permitir " + item.first
                    isChecked = permissions.getBoolean(id, false)
                    setOnCheckedChangeListener { _, granted ->
                        permissions.edit().putBoolean(id, granted).apply()
                    }
                })
            }
        }
        content.addView(actionButton("Modo acompañante y diversión") {
            val labels = arrayOf(
                "Acompañame", "Voy caminando", "Voy en bus",
                "Contame un chiste", "Silba", "Detener modo acompañante"
            )
            val commands = arrayOf(
                "SKY acompañame", "SKY voy caminando", "SKY voy en bus",
                "SKY contame un chiste", "SKY silba",
                "SKY desactiva modo acompañante"
            )
            AlertDialog.Builder(this).setTitle("SKY · Tu compañera")
                .setItems(labels) { _, index ->
                    companionController.handle(commands[index])
                }
                .setNegativeButton("Cerrar", null).show()
        })
        content.addView(actionButton("Mis aplicaciones instaladas") {
            settingsDialog?.dismiss()
            installedApps.showCatalog()
        })
        content.addView(actionButton("Autodiagnóstico Android") {
            showDeviceDiagnostics()
        })
        if (BuildConfig.ENABLE_TEXT_ASSIST) {
            content.addView(actionButton("Escritura asistida en WhatsApp/Gmail") {
                showTextAssistDisclosure()
            })
        }
        if (BuildConfig.ENABLE_TEXT_ASSIST &&
            getSharedPreferences("sky_assistive_text", MODE_PRIVATE)
                .getBoolean("consent", false)) {
            content.addView(actionButton("Desactivar escritura asistida") {
                getSharedPreferences("sky_assistive_text", MODE_PRIVATE)
                    .edit().putBoolean("consent", false).apply()
                SkyTextAssistService.cancelPending()
                home.showMessage("Escritura asistida desactivada en SKY. " +
                    "También podés apagar el servicio desde Ajustes de Android.")
            })
        }
        content.addView(CheckBox(this).apply {
            text = "SKY responde con voz"
            isChecked = voicePanel.isVoiceEnabled()
            setOnCheckedChangeListener { _, enabled ->
                voicePanel.setVoiceEnabled(enabled)
                getSharedPreferences("sky_voice_settings", MODE_PRIVATE)
                    .edit().putBoolean("read_aloud", enabled).apply()
            }
        })
        content.addView(description("SKY solicita el micrófono solo al hablar y requiere confirmación para abrir otras aplicaciones."))
        val scroll = ScrollView(this).apply { addView(content) }
        settingsDialog = AlertDialog.Builder(this)
            .setView(scroll)
            .setNegativeButton("Cerrar", null)
            .create()
        settingsDialog?.show()
    }

    override fun onResume() {
        super.onResume()
        visible = true
        companionController.onResume()
        handler.post(pollLoop)
    }
    override fun onPause() {
        visible = false
        if (::companionController.isInitialized) companionController.onPause()
        if (::voicePanel.isInitialized) voicePanel.onPausePanel()
        handler.removeCallbacks(pollLoop)
        super.onPause()
    }
    override fun onDestroy() {
        handler.removeCallbacks(pollLoop)
        if (::voicePanel.isInitialized) voicePanel.close()
        if (::companionController.isInitialized) companionController.close()
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
    private fun setStatus(value: String) = runOnUiThread {
        if (::home.isInitialized) home.showMessage(value)
        else status.text = value
    }

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
            runOnUiThread {
                codeInput.setText("")
                settingsDialog?.dismiss()
                refreshConnection()
                showSettings()
            }
            setStatus("Teléfono vinculado. SKY está preparada.")
        }
    }

    private fun checkHomeStatus() {
        val id = tokens.deviceId()
        val token = tokens.token()
        if (tokens.cloudEnabled()) {
            setStatus("SKY Android independiente · Gemini configurado. Windows no es necesario.")
            return
        }
        if (id.isEmpty() || token.isEmpty()) {
            setStatus("Configurá SKY móvil desde Ajustes o vinculá Windows opcionalmente.")
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
            runOnUiThread {
                chatCodeInput.setText("")
                settingsDialog?.dismiss()
                refreshConnection()
            }
            setStatus("Chat autorizado. ¡Ya podés conversar con SKY!")
        }
    }

    private fun sendChat() {
        val message = chatInput.text.toString().trim()
        if (message.isEmpty()) return
        if (processLocalPanelCommand(message, spoken = false) ||
            processCompanionCommand(message) || processDailyCommand(message)) {
            chatInput.setText("")
            return
        }
        if (chatPending) return
        val mobileCloud = tokens.cloudEnabled()
        val id = tokens.deviceId()
        val token = tokens.chatToken()
        if (!mobileCloud && (id.isEmpty() || token.isEmpty())) {
            setStatus("Configurá SKY móvil independiente desde Ajustes.")
            showSettings()
            return
        }
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
                val answer: String
                val provider: String
                if (mobileCloud) {
                    // Requiere consentimiento explícito al activar modo móvil en Ajustes.
                    // No requiere ni solicita llaves ni módulos de Windows.
                    answer = SkyPhoneCloud.reply(tokens.personalCloudKey(), message, history)
                    provider = "Gemini · SKY Android"
                } else {
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
                    answer = reply.optString("respuesta", "SKY no devolvió texto.")
                    provider = reply.optString("proveedor", "SKY Core")
                }
                chatHistory.put(JSONObject().put("role", "user").put("content", message))
                chatHistory.put(JSONObject().put("role", "assistant").put("content", answer.take(2000)))
                while (chatHistory.length() > 8) chatHistory.remove(0)
                runOnUiThread {
                    chatInput.setText("")
                    home.addExchange(message, answer, provider)
                    voicePanel.speakReply(answer)
                }
            } catch (error: Exception) {
                if (!mobileCloud && (error.message?.contains("HTTP 401") == true ||
                    error.message?.contains("HTTP 403") == true)) {
                    tokens.clearChat()
                    runOnUiThread {
                        refreshConnection()
                        home.showMessage("La sesión de chat venció. Renovala desde Ajustes.")
                        voicePanel.showError("La conversación necesita nueva autorización.")
                    }
                } else {
                    val reason = if (mobileCloud) when (error) {
                        is java.net.UnknownHostException -> "No hay acceso a internet."
                        is java.net.SocketTimeoutException -> "Gemini tardó demasiado en responder."
                        is IllegalStateException -> error.message ?: "Gemini no respondió."
                        is IllegalArgumentException -> error.message ?: "Revisá la configuración."
                        else -> "No se pudo conectar con Gemini. Revisá tu internet y tu clave."
                    } else "No fue posible consultar SKY Core. Revisá tu conexión."
                    runOnUiThread {
                        home.showMessage(reason)
                        voicePanel.showError("No pude responder. Revisá el estado y volvé a intentar.")
                    }
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
                    runOnUiThread { refreshConnection() }
                    setStatus("Acceso revocado. Volvé a Ajustes para conectar.")
                }
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }
}
