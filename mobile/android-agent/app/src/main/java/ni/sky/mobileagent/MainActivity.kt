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
    // La red de chat nunca debe esperar detrás de los sondeos del agente ni
    // de operaciones creativas largas. Cada canal conserva su orden interno.
    private val executor = Executors.newSingleThreadExecutor()
    private val chatExecutor = Executors.newSingleThreadExecutor()
    private val pollingExecutor = Executors.newSingleThreadExecutor()
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
    private lateinit var musicLauncher: SkyMusicLauncher
    private lateinit var quickActions: SkyQuickActions
    private lateinit var replyStudio: SkyReplyStudio
    @Volatile private var replyPending = false
    private val photoRequest = 1622
    private lateinit var installedApps: SkyInstalledApps
    private lateinit var socialStudio: SkySocialStudio
    private lateinit var socialAccounts: SkySocialAccounts
    private lateinit var socialMetrics: SkySocialMetricsPanel
    @Volatile private var socialPending = false
    @Volatile private var videoPending = false
    private lateinit var companionController: SkyCompanionController
    private lateinit var cloudConsent: CheckBox
    private lateinit var privateConsent: CheckBox
    private val chatHistory = JSONArray()
    @Volatile private var chatPending = false
    @Volatile private var voiceReplyOnFace = false
    @Volatile private var pendingCommand: String? = null
    @Volatile private var polling = false
    private var visible = false
    private var showOptionalWindowsLink = false
    private val handsFreePrefs by lazy { getSharedPreferences("sky_voice_settings", MODE_PRIVATE) }
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
        window.navigationBarColor = android.graphics.Color.rgb(7, 11, 32)
        if (android.os.Build.VERSION.SDK_INT >= 29) {
            window.isNavigationBarContrastEnforced = false
        }
        tokens = PrivateTokenStore(this)
        voicePanel = SkyEyeVoicePanel(this) { transcript ->
            if (!processQuickCommand(transcript) &&
                !processMusicCommand(transcript) &&
                !processReplyCommand(transcript) &&
                !processCreatorCommand(transcript) &&
                !processMessagingCommand(transcript) &&
                !processLocalPanelCommand(transcript, spoken = true) &&
                !processCompanionCommand(transcript) &&
                !processDailyCommand(transcript)) {
                // Keep the animated face visible during spoken conversation.
                voiceReplyOnFace = true
                chatInput.setText(transcript)
                if (!tokens.cloudEnabled() && tokens.chatToken().isEmpty()) {
                    voiceReplyOnFace = false
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
        voicePanel.onSpeechStarted = { SkyHandsFreeService.pauseForReply() }
        voicePanel.onSpeechFinished = { SkyHandsFreeService.resumeAfterReply() }
        home = SkyMobileHome(
            this, voicePanel,
            onSend = { voiceReplyOnFace = false; sendChat() },
            onSettings = { showSettings() },
            onChatAccess = { showSettings() },
            onDiagnostics = { checkHomeStatus() },
            onStopHandsFree = { setHandsFreeEnabled(false) }
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
        socialStudio = SkySocialStudio(this,
            feedback = { message ->
                home.showMessage(message)
                if (voicePanel.isVoiceEnabled()) voicePanel.speakReply(message)
            },
            renderVideo = { script -> generateCreativeVideo(script) }
        )
        socialAccounts = SkySocialAccounts(
            this, getSharedPreferences("sky_public_social_profiles", MODE_PRIVATE),
            chooseImport = { socialAccounts.chooseJson() },
            createContent = { platform ->
                socialStudio.showCreatorMenu(initialPlatform = platform) {
                    request -> createSocialContent(request)
                }
            },
            feedback = { message -> home.showMessage(message) }
        )
        socialMetrics = SkySocialMetricsPanel(
            this, getSharedPreferences("sky_social_metrics", MODE_PRIVATE),
            onImportClick = { socialMetrics.chooseCsv() },
            feedback = { message -> home.showMessage(message) }
        )
        musicLauncher = SkyMusicLauncher(
            this, getSharedPreferences("sky_mobile_music", MODE_PRIVATE)
        ) { message ->
            home.showMessage(message)
            if (voicePanel.isVoiceEnabled()) voicePanel.speakReply(message)
        }
        quickActions = SkyQuickActions(this) { message ->
            // Music commands must not talk over and interrupt the playing track.
            home.showMessage(message)
        }
        replyStudio = SkyReplyStudio(
            this, getSharedPreferences("sky_reply_contacts", MODE_PRIVATE)
        ) { message ->
            home.showMessage(message)
            if (voicePanel.isVoiceEnabled()) voicePanel.speakReply(message)
        }
        companionController = SkyCompanionController { message ->
            voicePanel.express(message)
            home.showMessage(message)
            voicePanel.speakReply(message)
        }
        setContentView(home.root)
        handler.post { acceptPendingVoiceIntent(intent) }
        home.root.setOnApplyWindowInsetsListener { _, insets ->
            val bottom = if (android.os.Build.VERSION.SDK_INT >= 30) {
                insets.getInsets(android.view.WindowInsets.Type.navigationBars()).bottom
            } else @Suppress("DEPRECATION") insets.systemWindowInsetBottom
            home.applyNavigationInset(bottom)
            insets
        }
        home.root.requestApplyInsets()
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
            "Chat: " + if (tokens.cloudEnabled()) "Gemini Android activo" else
                if (tokens.chatToken().isNotEmpty()) "Token almacenado" else "Sin autorizar",
            "Conversación fluida: " + if (voicePanel.isConversationModeEnabled()) "Activada" else "Desactivada"
        ).joinToString("\n")
        AlertDialog.Builder(this)
            .setTitle("SKY · Autodiagnóstico Android")
            .setMessage(lines + "\n\n" +
                "Este chequeo verifica capacidades locales, no prueba conexiones remotas " +
                "ni garantiza que una alarma haya sonado o un mensaje se haya enviado.")
            .setPositiveButton("Cerrar", null)
            .show()
    }

    /**
     * Media buttons and system volume require no repetition of the wake word.
     * Only works while the SKY UI can hear an explicitly authorized voice turn.
     */
    private fun processQuickCommand(message: String): Boolean {
        val command = SkyQuickCommand.parse(message) ?: return false
        quickActions.execute(command)
        return true
    }

    /** Music command works without a wake word. Android controls actual playback. */
    private fun processMusicCommand(message: String): Boolean {
        val request = SkyMusicCommand.parse(message) ?: return false
        musicLauncher.play(request)
        return true
    }

    /** Context is supplied by the user and only approved contacts are eligible. */
    private fun processReplyCommand(message: String): Boolean {
        val request = SkyContextReply.parse(message) ?: return false
        if (!replyStudio.isApproved(request.contact)) {
            home.showMessage("Todavía no autorizaste a «" + request.contact +
                "». Abrí Ajustes → Respuestas por contacto.")
            return true
        }
        createReplyDraft(request)
        return true
    }

    private fun createReplyDraft(request: SkyContextReply.Request) {
        if (!replyStudio.isApproved(request.contact)) {
            home.showMessage("Ese contacto no está autorizado en SKY.")
            return
        }
        if (!tokens.cloudEnabled()) {
            home.showMessage("Activá Gemini en Ajustes para proponer respuestas naturales.")
            return
        }
        if (replyPending) {
            home.showMessage("Estoy preparando otro borrador de respuesta.")
            return
        }
        replyPending = true
        voicePanel.showThinking()
        execute {
            try {
                val draft = SkyPhoneCloud.reply(tokens.personalCloudKey(),
                    SkyContextReply.prompt(request.contact, request.incoming), JSONArray())
                runOnUiThread {
                    if (!isFinishing) {
                        voicePanel.speakReply("Tengo una respuesta para " +
                            request.contact + ". Revisala antes de enviarla.")
                        replyStudio.preview(request, draft)
                    }
                }
            } catch (_: Exception) {
                runOnUiThread {
                    home.showMessage("No pude preparar esa respuesta. Revisá tu conexión con Gemini.")
                    voicePanel.showError("Error al preparar la respuesta.")
                }
            } finally { replyPending = false }
        }
    }

    /** Camera is never running without the user opening Android's camera app. */
    @Suppress("DEPRECATION")
    private fun startCameraReflection() {
        if (!tokens.cloudEnabled()) {
            home.showMessage("Activá Gemini en Ajustes para comentar una foto voluntaria.")
            return
        }
        AlertDialog.Builder(this)
            .setTitle("SKY · Un momento frente a la cámara")
            .setMessage("Abriremos la cámara del teléfono para una sola foto. " +
                "Después podrás elegir si la enviás a Gemini. " +
                "SKY no puede saber cómo te sentís por tu rostro: te preguntará.")
            .setPositiveButton("Abrir cámara") { _, _ ->
                try {
                    startActivityForResult(android.content.Intent(
                        android.provider.MediaStore.ACTION_IMAGE_CAPTURE), photoRequest)
                } catch (_: Exception) {
                    home.showMessage("No hay una cámara compatible disponible.")
                }
            }
            .setNegativeButton("Cancelar", null).show()
    }

    @Deprecated("Uses the Android camera thumbnail; no image is stored.")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: android.content.Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == 1640) {
            if (resultCode == RESULT_OK) {
                data?.data?.let { source -> socialMetrics.importCsv(source) }
            }
            return
        }
        if (requestCode == 1655) {
            if (resultCode == RESULT_OK) {
                data?.data?.let { source -> socialAccounts.importJson(source) }
            }
            return
        }
        if (requestCode != photoRequest || resultCode != RESULT_OK) return
        @Suppress("DEPRECATION")
        val bitmap = data?.extras?.get("data") as? android.graphics.Bitmap
        if (bitmap == null) {
            home.showMessage("La cámara no devolvió una fotografía. No se envió nada.")
            return
        }
        val output = java.io.ByteArrayOutputStream()
        bitmap.compress(android.graphics.Bitmap.CompressFormat.JPEG, 74, output)
        val bytes = output.toByteArray()
        if (bytes.size > 360_000) {
            home.showMessage("La foto es demasiado grande; no se envió nada.")
            return
        }
        AlertDialog.Builder(this)
            .setTitle("¿Compartir esta foto una sola vez?")
            .setMessage("La imagen se enviará a Google Gemini únicamente si lo autorizás. " +
                "SKY comentará elementos visibles y te preguntará cómo estás, " +
                "sin diagnosticar emociones o salud mental. La app no guardará la foto.")
            .setPositiveButton("Analizar con Gemini") { _, _ ->
                voicePanel.showThinking()
                execute {
                    try {
                        val response = SkyPhoneCloud.reflectOnPhoto(tokens.personalCloudKey(), bytes)
                        runOnUiThread {
                            home.showMessage(response)
                            voicePanel.speakReply(response)
                        }
                    } catch (_: Exception) {
                        runOnUiThread {
                            home.showMessage("No pude revisar la foto con Gemini.")
                            voicePanel.showError("No se pudo analizar la imagen.")
                        }
                    }
                }
            }
            .setNegativeButton("No enviar", null).show()
    }

    /**
     * 10-second on-device silent H.264 animation. No external cloud for render.
     * Exported only to the Android application selected by the user.
     */
    private fun generateCreativeVideo(script: String) {
        if (videoPending) {
            home.showMessage("El video anterior todavía se está generando.")
            return
        }
        AlertDialog.Builder(this)
            .setTitle("SKY · Video vertical")
            .setMessage("Generaré un MP4 de 10 segundos con cinco escenas de texto " +
                "animado, sin música ni voz. Se crea en este teléfono. " +
                "Podés añadir fotos, voz y música autorizada desde el editor " +
                "de la red social. ¿Continuamos?")
            .setPositiveButton("Crear MP4") { _, _ ->
                videoPending = true
                home.showMessage("Creando un video vertical en el teléfono…")
                execute {
                    try {
                        val file = SkyVerticalVideo.generate(applicationContext, script)
                        runOnUiThread {
                            videoPending = false
                            AlertDialog.Builder(this)
                                .setTitle("Video MP4 generado")
                                .setMessage("SKY creó un video vertical sin audio, " +
                                    "de " + file.length() + " bytes. " +
                                    "Elegí una app para revisarlo y editarlo " +
                                    "antes de publicar. No se publicó automáticamente.")
                                .setPositiveButton("Compartir video") { _, _ ->
                                    val uri = SkyGeneratedVideoProvider.uri()
                                    val share = android.content.Intent(
                                        android.content.Intent.ACTION_SEND).apply {
                                        type = "video/mp4"
                                        putExtra(android.content.Intent.EXTRA_STREAM, uri)
                                        clipData = android.content.ClipData.newUri(
                                            contentResolver, "SKY video", uri)
                                        addFlags(android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION)
                                    }
                                    try {
                                        startActivity(android.content.Intent.createChooser(
                                            share, "Compartir o editar video SKY"))
                                    } catch (_: Exception) {
                                        home.showMessage("No hay apps compatibles con video MP4.")
                                    }
                                }
                                .setNegativeButton("Cerrar", null).show()
                        }
                    } catch (error: Exception) {
                        runOnUiThread {
                            videoPending = false
                            home.showMessage("No pude crear el MP4 en este teléfono. " +
                                "Revisá el espacio disponible y el codificador H.264. " +
                                (error.message ?: "Error de renderizado."))
                        }
                    }
                }
            }
            .setNegativeButton("Cancelar", null).show()
    }

    /** Original social content, never automatic likes, followers or publishing. */
    private fun processCreatorCommand(message: String): Boolean {
        val request = SkySocialCommand.parse(message) ?: return false
        createSocialContent(request)
        return true
    }

    private fun createSocialContent(request: SkySocialCommand.Request) {
        if (socialPending) {
            home.showMessage("SKY ya está preparando un borrador creativo.")
            return
        }
        if (!tokens.cloudEnabled()) {
            home.showMessage("Activá Gemini en Ajustes para generar contenido original.")
            showSettings()
            return
        }
        socialPending = true
        voicePanel.showThinking()
        execute {
            try {
                val text = SkyPhoneCloud.reply(tokens.personalCloudKey(),
                    SkySocialCommand.prompt(request), JSONArray())
                runOnUiThread {
                    if (!isFinishing) {
                        voicePanel.speakReply("Tengo una propuesta para " + request.platform +
                            ". Revisá y editá el borrador antes de compartirlo.")
                        socialStudio.showPreview(request, text)
                    }
                }
            } catch (_: Exception) {
                runOnUiThread {
                    home.showMessage("No pude generar el borrador. Revisá internet, Gemini " +
                        "y volvé a intentarlo.")
                    voicePanel.showError("No pude preparar el contenido.")
                }
            } finally {
                socialPending = false
            }
        }
    }

    /** Explicit WhatsApp commands are local actions, not generic Gemini chat. */
    private fun processMessagingCommand(message: String): Boolean {
        val draft = SkyMessagingIntent.parse(message) ?: return false
        dailyActions.prepareWhatsApp(draft)
        return true
    }

    private fun processCompanionCommand(message: String): Boolean {
        val normalized = message.trim().lowercase(java.util.Locale.ROOT)
            .replace(Regex("""^sky[ ,.:!]*"""), "")
        if (normalized in setOf("mirame", "mírame", "quiero que me veas",
                "como me veo", "cómo me veo", "abrí la cámara", "abre la cámara")) {
            startCameraReflection()
            return true
        }
        return companionController.handle(message)
    }

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
            content.addView(description("Prueba privada de SKY Android con Gemini. " +
                "Tu clave se cifra en el teléfono y NO se agrega a la APK. " +
                "Puede generar consumo o costos. No distribuir públicamente este modo."))
            val personalKey = input("Clave de Gemini AI Studio", true)
            val permission = CheckBox(this).apply {
                text = "Autorizo enviar mis mensajes y el contexto reciente a Google Gemini. " +
                    "Entiendo que puedo desactivar SKY Cloud y borrar la clave."
            }
            content.addView(description("En AI Studio elegí «Copiar clave». " +
                "No copies el nombre ni el número del proyecto. Nunca compartás tu clave."))
            content.addView(personalKey)
            content.addView(actionButton("PEGAR CLAVE COPIADA") {
                val clipboard = getSystemService(CLIPBOARD_SERVICE) as? android.content.ClipboardManager
                val clip = clipboard?.primaryClip
                val raw = if (clip != null && clip.itemCount > 0) {
                    clip.getItemAt(0).coerceToText(this)?.toString().orEmpty()
                } else ""
                val normalized = SkyPhoneCloud.normalizePersonalKey(raw)
                val problem = SkyPhoneCloud.personalKeyProblem(raw)
                if (problem != null) {
                    AlertDialog.Builder(this)
                        .setTitle("No se detectó una clave Gemini válida")
                        .setMessage(problem)
                        .setPositiveButton("Entendido", null).show()
                } else {
                    personalKey.setText(normalized)
                    personalKey.setSelection(normalized.length)
                    setStatus("Clave pegada de forma segura. Ahora verificá con Google.")
                }
            })
            content.addView(permission)
            content.addView(actionButton("Abrir Google AI Studio para obtener clave") {
                startActivity(android.content.Intent(android.content.Intent.ACTION_VIEW,
                    android.net.Uri.parse("https://aistudio.google.com/apikey")))
            })
            lateinit var activationButton: Button
            activationButton = actionButton("VERIFICAR CLAVE Y ACTIVAR SKY") {
                val value = SkyPhoneCloud.normalizePersonalKey(personalKey.text.toString())
                val problem = SkyPhoneCloud.personalKeyProblem(value)
                if (!permission.isChecked) {
                    AlertDialog.Builder(this)
                        .setTitle("Consentimiento necesario")
                        .setMessage("Primero autorizá el envío de mensajes y contexto a Gemini.")
                        .setPositiveButton("Entendido", null).show()
                } else if (problem != null) {
                    AlertDialog.Builder(this)
                        .setTitle("Comprobación de seguridad de la clave")
                        .setMessage(problem)
                        .setPositiveButton("Entendido", null).show()
                } else {
                    activationButton.isEnabled = false
                    activationButton.text = "Comprobando conexión con Gemini…"
                    execute {
                        // Only Google verifies the key; no key is logged or sent to SKY Windows.
                        try {
                            SkyPhoneCloud.reply(value, "Respondé solamente: lista.", JSONArray())
                            runOnUiThread {
                                if (isFinishing) return@runOnUiThread
                                tokens.savePersonalCloudKey(value)
                                personalKey.setText("")
                                refreshConnection()
                                settingsDialog?.dismiss()
                                AlertDialog.Builder(this)
                                    .setTitle("SKY Android activada")
                                    .setMessage("Conexión con Gemini verificada. Ya podés conversar " +
                                        "por texto o voz sin SKY Windows.")
                                    .setPositiveButton("Comenzar") { _, _ -> home.openChat() }
                                    .show()
                            }
                        } catch (error: Exception) {
                            val message = when (error) {
                                is IllegalStateException -> error.message
                                    ?: "Gemini no aceptó la solicitud."
                                is java.net.UnknownHostException ->
                                    "No se pudo encontrar Google. Revisá tu conexión a internet."
                                is java.net.SocketTimeoutException ->
                                    "La conexión tardó demasiado. Intentá de nuevo."
                                is javax.net.ssl.SSLException ->
                                    "Falló la conexión HTTPS. Revisá fecha, red y certificados de Android."
                                else -> "No fue posible verificar Gemini. Revisá la conexión e intentá de nuevo."
                            }
                            runOnUiThread {
                                if (isFinishing) return@runOnUiThread
                                activationButton.isEnabled = true
                                activationButton.text = "VERIFICAR CLAVE Y ACTIVAR SKY"
                                AlertDialog.Builder(this)
                                    .setTitle("SKY aún no está activada")
                                    .setMessage(message)
                                    .setPositiveButton("Entendido", null).show()
                            }
                        }
                    }
                }
            }
            content.addView(activationButton)
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
        content.addView(actionButton("CONTROL MUSICAL · SIGUIENTE / ATRÁS / VOLUMEN") {
            val labels = arrayOf("Siguiente canción", "Canción anterior",
                "Repetir / reiniciar pista", "Subir volumen", "Bajar volumen",
                "Pausar", "Reanudar", "Mostrar desbloqueo seguro")
            val commands = arrayOf(
                SkyQuickCommand.Action.NEXT, SkyQuickCommand.Action.PREVIOUS,
                SkyQuickCommand.Action.RESTART, SkyQuickCommand.Action.VOLUME_UP,
                SkyQuickCommand.Action.VOLUME_DOWN, SkyQuickCommand.Action.PAUSE,
                SkyQuickCommand.Action.PLAY, SkyQuickCommand.Action.REQUEST_UNLOCK)
            AlertDialog.Builder(this)
                .setTitle("SKY · Controles de Android")
                .setItems(labels) { _, index -> quickActions.execute(commands[index]) }
                .setNegativeButton("Cerrar", null)
                .show()
        })
        content.addView(actionButton("MÚSICA · Spotify / YouTube Music / YouTube") {
            val choices = SkyMusicCommand.Service.entries.toTypedArray()
            AlertDialog.Builder(this)
                .setTitle("Elegí tu reproductor favorito")
                .setSingleChoiceItems(choices.map(SkyMusicCommand::label).toTypedArray(),
                    choices.indexOf(musicLauncher.preferred())) { dialog, position ->
                    musicLauncher.savePreferred(choices[position])
                    dialog.dismiss()
                    home.showMessage("Ahora puedo buscar canciones en " +
                        SkyMusicCommand.label(choices[position]) +
                        ". Decime «Pon la canción ...» sin repetir SKY.")
                }
                .setNegativeButton("Cancelar", null).show()
        })
        content.addView(actionButton("RESPUESTAS NATURALES · CONTACTOS") {
            settingsDialog?.dismiss()
            replyStudio.showSettings { request -> createReplyDraft(request) }
        })
        content.addView(actionButton("Revisar / retirar contactos autorizados") {
            replyStudio.manageContacts()
        })
        content.addView(actionButton("CÁMARA OPCIONAL · ¿CÓMO ME VEO?") {
            settingsDialog?.dismiss()
            startCameraReflection()
        })
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
        content.addView(actionButton("MIS REDES · PERFIL Y ENLACES PÚBLICOS") {
            settingsDialog?.dismiss()
            socialAccounts.show()
        })
        content.addView(actionButton("MÉTRICAS REALES · IMPORTAR ESTADÍSTICAS") {
            settingsDialog?.dismiss()
            socialMetrics.show()
        })
        content.addView(actionButton("ESTUDIO CREATIVO · MIS REDES SOCIALES") {
            settingsDialog?.dismiss()
            socialStudio.showCreatorMenu { request -> createSocialContent(request) }
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
            text = "Manos libres: decir SKY para despertar (micrófono local y notificación permanente)"
            isChecked = handsFreePrefs.getBoolean("hands_free_opt_in", false)
            setOnCheckedChangeListener { _, enabled -> setHandsFreeEnabled(enabled) }
        })
        content.addView(CheckBox(this).apply {
            text = "Conversación fluida antigua (solo con la app abierta)"
            isChecked = getSharedPreferences("sky_voice_settings", MODE_PRIVATE)
                .getBoolean("fluid_opt_in", false)
            setOnCheckedChangeListener { _, enabled ->
                getSharedPreferences("sky_voice_settings", MODE_PRIVATE)
                    .edit().putBoolean("fluid_opt_in", enabled).apply()
                voicePanel.setConversationMode(enabled)
                home.showMessage(if (enabled)
                    "Conversación fluida activada. Tocá HABLAR para comenzar."
                    else "Conversación fluida desactivada.")
            }
        })
        content.addView(CheckBox(this).apply {
            text = "SKY responde con voz"
            isChecked = voicePanel.isVoiceEnabled()
            setOnCheckedChangeListener { _, enabled ->
                voicePanel.setVoiceEnabled(enabled)
                getSharedPreferences("sky_voice_settings", MODE_PRIVATE)
                    .edit().putBoolean("read_aloud", enabled).apply()
            }
        })
        content.addView(description("Manos libres requiere Android 12 o posterior y reconocimiento de voz instalado en el dispositivo. Mientras está activa se muestra una notificación para apagarla. Puede consumir batería; si Android cierra el servicio, abrí SKY para reactivarlo. Con pantalla apagada puede ajustar volumen y enviar controles multimedia. Para abrir aplicaciones, Android puede exigir desbloquear el teléfono y tocar la notificación de SKY. Las acciones sensibles siguen exigiendo aprobación."))
        val scroll = ScrollView(this).apply { addView(content) }
        settingsDialog = AlertDialog.Builder(this)
            .setView(scroll)
            .setNegativeButton("Cerrar", null)
            .create()
        settingsDialog?.show()
    }

    private fun setHandsFreeEnabled(enabled: Boolean) {
        handsFreePrefs.edit().putBoolean("hands_free_opt_in", enabled).apply()
        if (!enabled) {
            SkyHandsFreeService.stop(this)
            home.setHandsFreeActive(false)
            voicePanel.showHandsFreeState("Manos libres apagadas.")
            return
        }
        if (checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) !=
            android.content.pm.PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(android.Manifest.permission.RECORD_AUDIO), 1615)
            return
        }
        startHandsFree()
    }

    private fun startHandsFree() {
        if (android.os.Build.VERSION.SDK_INT < 31 ||
            !android.speech.SpeechRecognizer.isOnDeviceRecognitionAvailable(this)) {
            handsFreePrefs.edit().putBoolean("hands_free_opt_in", false).apply()
            home.setHandsFreeActive(false)
            voicePanel.showError("Este teléfono no tiene reconocimiento local compatible. Seguís pudiendo usar HABLAR.")
            return
        }
        try {
            startForegroundService(android.content.Intent(this, SkyHandsFreeService::class.java)
                .setAction(SkyHandsFreeService.ACTION_START))
            voicePanel.setConversationMode(false)
            home.setHandsFreeActive(true)
            voicePanel.showHandsFreeState("SKY duerme hasta que digás su nombre.")
            if (android.os.Build.VERSION.SDK_INT >= 33 &&
                checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) !=
                    android.content.pm.PackageManager.PERMISSION_GRANTED &&
                !handsFreePrefs.getBoolean("notification_permission_asked", false)) {
                handsFreePrefs.edit().putBoolean("notification_permission_asked", true).apply()
                requestPermissions(arrayOf(android.Manifest.permission.POST_NOTIFICATIONS), 1616)
            }
        } catch (_: Exception) {
            handsFreePrefs.edit().putBoolean("hands_free_opt_in", false).apply()
            home.setHandsFreeActive(false)
            voicePanel.showError("Android bloqueó el inicio del micrófono permanente.")
        }
    }

    private fun acceptPendingVoiceIntent(openIntent: android.content.Intent?) {
        val pending = openIntent?.getStringExtra(SkyHandsFreeService.EXTRA_COMMAND)
        if (!pending.isNullOrBlank() && ::voicePanel.isInitialized) {
            openIntent?.removeExtra(SkyHandsFreeService.EXTRA_COMMAND)
            voicePanel.acceptHandsFreeTranscript(pending)
        }
    }

    override fun onNewIntent(intent: android.content.Intent?) {
        super.onNewIntent(intent)
        handler.post { acceptPendingVoiceIntent(intent) }
    }

    override fun onResume() {
        super.onResume()
        visible = true
        if (::voicePanel.isInitialized) {
            voicePanel.onEnterForeground()
            voicePanel.setConversationMode(getSharedPreferences(
                "sky_voice_settings", MODE_PRIVATE).getBoolean("fluid_opt_in", false))
        }
        SkyHandsFreeService.onPhrase = { phrase ->
            if (visible && ::voicePanel.isInitialized) voicePanel.acceptHandsFreeTranscript(phrase)
        }
        SkyHandsFreeService.onWake = {
            if (visible && ::voicePanel.isInitialized) voicePanel.speakReply("¡Aquí estoy! Decime.")
        }
        SkyHandsFreeService.onStopped = {
            if (visible && ::home.isInitialized) {
                home.setHandsFreeActive(false)
                voicePanel.showError("Manos libres detenidas. Revisá permisos o idioma sin conexión.")
            }
        }
        SkyHandsFreeService.onStatus = { asleep ->
            if (visible && ::voicePanel.isInitialized) {
                voicePanel.showHandsFreeState(if (asleep) "SKY durmiendo · decí SKY" else "SKY escuchándote")
            }
        }
        if (handsFreePrefs.getBoolean("hands_free_opt_in", false) &&
            checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) ==
                android.content.pm.PackageManager.PERMISSION_GRANTED) startHandsFree()
        if (::home.isInitialized) home.setHandsFreeActive(
            handsFreePrefs.getBoolean("hands_free_opt_in", false))
        companionController.onResume()
        handler.post(pollLoop)
    }
    override fun onPause() {
        SkyHandsFreeService.onPhrase = null
        SkyHandsFreeService.onWake = null
        SkyHandsFreeService.onStatus = null
        SkyHandsFreeService.onStopped = null
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
        chatExecutor.shutdown()
        pollingExecutor.shutdown()
        super.onDestroy()
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 1615) {
            val granted = grantResults.isNotEmpty() &&
                grantResults[0] == android.content.pm.PackageManager.PERMISSION_GRANTED
            if (granted) startHandsFree()
            else {
                handsFreePrefs.edit().putBoolean("hands_free_opt_in", false).apply()
                home.setHandsFreeActive(false)
                voicePanel.showError("Sin permiso de micrófono; manos libres desactivadas.")
            }
            return
        }
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
        if (processQuickCommand(message) ||
            processMusicCommand(message) ||
            processReplyCommand(message) ||
            processCreatorCommand(message) ||
            processMessagingCommand(message) ||
            processLocalPanelCommand(message, spoken = false) ||
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
        chatExecutor.execute {
            val started = android.os.SystemClock.elapsedRealtime()
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
                    val keepFace = voiceReplyOnFace
                    voiceReplyOnFace = false
                    val elapsedMs = android.os.SystemClock.elapsedRealtime() - started
                    home.addExchange(message, answer,
                        provider + " · " + String.format(java.util.Locale.US, "%.1f s", elapsedMs / 1000.0),
                        revealPanel = !keepFace)
                    voicePanel.speakReply(answer)
                }
            } catch (error: Exception) {
                if (!mobileCloud && (error.message?.contains("HTTP 401") == true ||
                    error.message?.contains("HTTP 403") == true)) {
                    tokens.clearChat()
                    voiceReplyOnFace = false
                    runOnUiThread {
                        refreshConnection()
                        home.showMessage("La sesión de chat venció. Renovala desde Ajustes.")
                        voicePanel.showError("La conversación necesita nueva autorización.")
                    }
                } else {
                    voiceReplyOnFace = false
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
        pollingExecutor.execute {
            try {
                val response = SkyNetwork.request(tokens.server(),
                    "/api/sky/mobile-agent/devices/" + id + "/next", "GET", token)
                val command = response.optJSONObject("command") ?: return@execute
                pendingCommand = command.getString("id")
                runOnUiThread { approve(command) }
            } catch (_: Exception) {
                setStatus("SKY agente no pudo consultar nuevas órdenes.")
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
