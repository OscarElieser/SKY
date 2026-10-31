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
 * cuando está visible. La confianza local de apertura es revocable y nunca\n * autoriza sin confirmación acciones destructivas o tareas remotas.
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
    private var requestedMusicAfterPermission: SkyMusicCommand.Request? = null
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
    private lateinit var archive: SkyConversationArchive
    private lateinit var longTermMemory: SkyLongTermMemory
    private lateinit var adaptiveMemory: SkyAdaptiveMemory
    private lateinit var actionEvidence: SkyActionEvidence
    private val verifiedLearning by lazy { SkyVerifiedLearning(this) }
    private val knowledgeSources by lazy { SkyAndroidKnowledgeSources(this) }
    private val cognitionPrefs by lazy { getSharedPreferences("sky_android_cognition", MODE_PRIVATE) }
    private fun cognitionEnabled(): Boolean = cognitionPrefs.getBoolean("enabled", true)
    private val attachmentRequest = 1666
    private val profileImportRequest = 1667
    private val historyExportRequest = 1668
    private val responseExportRequest = 1669
    private val nativeOfficeExportRequest = 1670
    private val vectorExportRequest = 1671
    private val generatedImageSaveRequest = 1672
    private val generatedVideoSaveRequest = 1673
    private var generatedImageToSave: SkyGeneratedImage.Result? = null
    private var generatedVideoToSave: java.io.File? = null
    @Volatile private var imageGenerationPending = false
    private var vectorExportPending: SkyConversationArchive.Entry? = null
    private var nativeOfficeExportPending:
        Pair<SkyConversationArchive.Entry, SkyNativeOfficeExport.Format>? = null
    private var responseExportPending: Pair<SkyConversationArchive.Entry, SkyResponseExport.Format>? = null
    private val selectedAttachments = mutableListOf<SkyAttachmentBatch.Item>()
    @Volatile private var pendingFileCancel: SkyGeminiFiles.CancelToken? = null
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
    // The proactive Instagram check never sends messages or instructions to an LLM.
    private val instagramChecking = java.util.concurrent.atomic.AtomicBoolean(false)
    private var instagramReviewOfferUntil = 0L
    private var instagramDraftOfferUntil = 0L
    private data class InstagramDraftConsent(
        val incoming: String, val eventKey: String,
        val senderId: String, val expiresAt: Long
    )
    private var instagramDraftConsent: InstagramDraftConsent? = null
    private var instagramLastDraft: String? = null
    private var instagramLastDraftEventKey: String? = null
    private var instagramLastDraftRecipient: String? = null
    private var instagramLastDraftUntil = 0L
    private val instagramDraftBusy = java.util.concurrent.atomic.AtomicBoolean(false)

    private fun instagramDeviceUnlocked(): Boolean =
        !(getSystemService(KEYGUARD_SERVICE) as android.app.KeyguardManager).isDeviceLocked

    private fun instagramSay(message: String) {
        if (::home.isInitialized) home.showMessage(message)
        if (::voicePanel.isInitialized && voicePanel.isVoiceEnabled() &&
            instagramDeviceUnlocked()) voicePanel.speakReply(message)
    }

    /** Read-only source event. This stage never sends a DM. */
    private fun proposeInstagramReply() {
        if (!instagramDeviceUnlocked()) {
            instagramSay("Desbloqueá el teléfono antes de revisar mensajes privados.")
            return
        }
        if (!SkyInstagramAlerts.paired(this)) {
            instagramSay("Primero vinculá tu cuenta de Instagram con SKY.")
            return
        }
        if (!instagramDraftBusy.compareAndSet(false, true)) {
            instagramSay("Estoy revisando el mensaje anterior.")
            return
        }
        instagramSay("Voy a consultar tu último mensaje real de Instagram.")
        Thread {
            val incoming = runCatching {
                val snapshot = SkyInstagramAlerts.fetch(this)
                snapshot.messages.firstOrNull {
                    it.body.isNotBlank() &&
                        it.body != "Mensaje sin texto o contenido multimedia"
                } ?: error("No hay mensajes recientes con texto para responder.")
            }
            runOnUiThread {
                instagramDraftBusy.set(false)
                if (isFinishing || !visible) return@runOnUiThread
                incoming.onSuccess { msg ->
                    if (!instagramDeviceUnlocked()) {
                        instagramSay("Desbloqueá el teléfono para revisar el mensaje.")
                        return@onSuccess
                    }
                    instagramLastDraft = null
                    instagramLastDraftEventKey = null
                    instagramLastDraftRecipient = null
                    instagramDraftConsent = InstagramDraftConsent(
                        msg.body, msg.key, msg.sender,
                        android.os.SystemClock.elapsedRealtime() + 120_000L)
                    if (!tokens.groqEnabled() && !tokens.cloudEnabled()) {
                        generateLocalInstagramDraft(instagramDraftConsent!!)
                    } else {
                        instagramSay("El último mensaje dice: " +
                            SkyInstagramInboxRules.preview(msg.body, 220) +
                            ". Puedo redactar la respuesta con " +
                            (if (tokens.groqEnabled()) "Groq" else "Gemini") +
                            " si autorizás compartir ese texto, " +
                            "o prepararla localmente sin compartirlo. " +
                            "Decime «sí autorizo» o «no, hacelo local».")
                    }
                }.onFailure {
                    instagramSay("No pude recuperar un mensaje de Instagram válido: " +
                        (it.message ?: "fallo de conexión") + ".")
                }
            }
        }.start()
    }

    /** Offline fallback, without API tokens or sharing private DM content. */
    private fun generateLocalInstagramDraft(approval: InstagramDraftConsent) {
        instagramDraftConsent = null
        if (!instagramDeviceUnlocked()) {
            instagramSay("Desbloqueá el teléfono para revisar tu respuesta.")
            return
        }
        val result = runCatching {
            SkyInstagramReplyPlanner.propose(approval.eventKey,
                approval.senderId, approval.incoming,
                android.os.SystemClock.elapsedRealtime())
        }
        result.onSuccess { draft ->
            instagramLastDraft = draft.text
            instagramLastDraftEventKey = approval.eventKey
            instagramLastDraftRecipient = approval.senderId
            instagramLastDraftUntil =
                android.os.SystemClock.elapsedRealtime() + 300_000L
            instagramSay("Preparé una respuesta privada, sin compartir tu mensaje " +
                "con ninguna IA externa. " + SkyInstagramReplyPlanner.readback(draft) +
                " Si estás de acuerdo con este texto exacto, decime «sí, envíala».")
        }.onFailure {
            instagramSay("No pude validar el mensaje original para crear el borrador: " +
                (it.message ?: "falta el identificador del evento") + ".")
        }
    }

    private fun generateInstagramDraft(approval: InstagramDraftConsent) {
        instagramDraftConsent = null
        if (!instagramDeviceUnlocked()) {
            instagramSay("Desbloqueá el teléfono para generar la respuesta.")
            return
        }
        if (!instagramDraftBusy.compareAndSet(false, true)) return
        instagramSay("Estoy preparando un borrador. No enviaré ningún mensaje.")
        Thread {
            val candidate = runCatching {
                SkyInstagramDraftFlow.cleanDraft(
                    generateMobileText(SkyInstagramDraftFlow.prompt(approval.incoming)))
            }
            runOnUiThread {
                instagramDraftBusy.set(false)
                if (isFinishing || !visible) return@runOnUiThread
                candidate.onSuccess { proposed ->
                    if (!instagramDeviceUnlocked()) {
                        instagramSay("Desbloqueá el teléfono para revisar la respuesta.")
                        return@onSuccess
                    }
                    instagramLastDraft = proposed
                    instagramLastDraftEventKey = approval.eventKey
                    instagramLastDraftRecipient = approval.senderId
                    instagramLastDraftUntil =
                        android.os.SystemClock.elapsedRealtime() + 300_000L
                    instagramSay("Te propongo esta respuesta, todavía sin enviar: " +
                        proposed + ". Podés decirme copia la respuesta. " +
                        "Si estás de acuerdo con este texto, decime «sí, envíala».")
                }.onFailure {
                    instagramSay("La IA no produjo un borrador seguro: " +
                        (it.message ?: "error del proveedor") + ".")
                }
            }
        }.start()
    }


    /**
     * Owner's explicit "envíala" authorizes one exact draft for one webhook event.
     * Server checks Meta scope, recipient and <=24h window, and stores only text hash.
     * No automatic retry on a network timeout, preventing accidental duplicate DMs.
     */
    private fun sendApprovedInstagramReply() {
        if (!instagramDeviceUnlocked()) {
            instagramSay("Por seguridad desbloqueá el teléfono antes de enviar.")
            return
        }
        val message = instagramLastDraft?.trim()
        val eventKey = instagramLastDraftEventKey
        val recipient = instagramLastDraftRecipient
        val now = android.os.SystemClock.elapsedRealtime()
        if (message.isNullOrBlank() || eventKey.isNullOrBlank() ||
            recipient.isNullOrBlank() || now >= instagramLastDraftUntil) {
            instagramLastDraft = null
            instagramLastDraftEventKey = null
            instagramLastDraftRecipient = null
            instagramSay("El borrador ya no está disponible. Pedime que lo prepare de nuevo.")
            return
        }
        if (!instagramDraftBusy.compareAndSet(false, true)) {
            instagramSay("Estoy realizando otra operación de Instagram.")
            return
        }
        instagramSay("Estoy comprobando el permiso y el destinatario en Meta. " +
            "Solo confirmaré un envío si recibo su comprobante.")
        Thread {
            var consumed = false
            val result = runCatching {
                val prepared = SkyInstagramAlerts.prepareReply(this, eventKey, message)
                if (!prepared.canConfirm)
                    "El borrador sigue disponible, pero el envío real todavía no está " +
                    "habilitado. Podés copiarlo desde SKY. No envié nada."
                else {
                    // Keep only opaque approval ID; no private DM text stored on device.
                    getSharedPreferences("sky_instagram_receipts_v1", MODE_PRIVATE).edit()
                        .putString("last_approval_id", prepared.approvalId).commit()
                    // Burn local approval before the one-and-only Meta send attempt.
                    consumed = true
                    val receipt = SkyInstagramAlerts.confirmReply(this, prepared, message)
                    if (receipt.sent)
                        "Meta confirmó que envié tu respuesta a " + prepared.recipientLabel +
                        ". Comprobante: " + receipt.messageId
                    else "Meta no confirmó el envío. Estado: " + receipt.status +
                        ". No voy a repetirlo automáticamente."
                }
            }.getOrElse { error ->
                val reason = error.message.orEmpty()
                if ("supervised_send_not_enabled" in reason)
                    "Tu respuesta sigue lista como borrador, pero el envío directo " +
                    "todavía está deshabilitado en el servidor de SKY. " +
                    "Podés decir «copia la respuesta» y enviarla manualmente."
                else "No pude verificar el envío: " +
                    (error.message ?: "problema de conexión") +
                    ". No voy a repetirlo automáticamente."
            }
            runOnUiThread {
                if (consumed) {
                    instagramLastDraft = null
                    instagramLastDraftEventKey = null
                    instagramLastDraftRecipient = null
                    instagramLastDraftUntil = 0L
                }
                instagramDraftBusy.set(false)
                if (!isFinishing && visible) instagramSay(result)
            }
        }.start()
    }


    /** Ask for evidence of the last attempt; never sends a second message. */
    private fun checkInstagramReplyReceipt() {
        if (!instagramDeviceUnlocked()) {
            instagramSay("Desbloqueá el teléfono para consultar el comprobante de Instagram.")
            return
        }
        val id = getSharedPreferences("sky_instagram_receipts_v1", MODE_PRIVATE)
            .getString("last_approval_id", "").orEmpty()
        if (id.isBlank()) {
            instagramSay("SKY no registra ningún intento de envío autorizado en este teléfono.")
            return
        }
        if (!instagramDraftBusy.compareAndSet(false, true)) return
        instagramSay("Estoy verificando el último envío. No repetiré el mensaje.")
        Thread {
            val response = runCatching {
                val receipt = SkyInstagramAlerts.replyStatus(this, id)
                if (receipt.sent)
                    "Meta confirmó el último envío. Comprobante: " + receipt.messageId
                else "El último intento figura como «" + receipt.status +
                    "». No significa que se haya enviado; no lo repetiré."
            }.getOrElse {
                "No pude consultar el comprobante. No enviaré nada de nuevo."
            }
            runOnUiThread {
                instagramDraftBusy.set(false)
                if (!isFinishing && visible) instagramSay(response)
            }
        }.start()
    }

    private fun checkInstagramSendReadiness() {
        if (!SkyInstagramAlerts.paired(this)) {
            instagramSay("Primero vinculá Instagram con SKY.")
            return
        }
        if (!instagramDraftBusy.compareAndSet(false, true)) {
            instagramSay("Estoy terminando una consulta anterior de Instagram.")
            return
        }
        instagramSay("Voy a comprobar los permisos reales de respuesta en Meta.")
        Thread {
            val result = runCatching { SkyInstagramAlerts.sendReadiness(this) }
            runOnUiThread {
                instagramDraftBusy.set(false)
                if (isFinishing || !visible) return@runOnUiThread
                instagramSay(result.getOrElse {
                    "No se pudo comprobar el envío en Meta: " +
                        (it.message ?: "error de conexión") +
                        ". La lectura de mensajes sigue separada."
                })
            }
        }.start()
    }

    /** Handles only explicit owner intents and a one-time, short-lived approval. */
    private fun processInstagramDraft(message: String): Boolean {
        val now = android.os.SystemClock.elapsedRealtime()
        val waiting = instagramDraftConsent
        if (waiting != null) {
            if (now >= waiting.expiresAt) {
                instagramDraftConsent = null
            } else {
                when (SkyInstagramDraftFlow.approval(message)) {
                    SkyInstagramDraftFlow.Approval.YES -> {
                        generateInstagramDraft(waiting)
                        return true
                    }
                    SkyInstagramDraftFlow.Approval.NO -> {
                        generateLocalInstagramDraft(waiting)
                        return true
                    }
                    SkyInstagramDraftFlow.Approval.NONE -> Unit
                }
            }
        }
        val requestedRevision = SkyInstagramReplyPlanner.revisedText(message)
        if (requestedRevision != null && instagramLastDraft != null &&
            instagramDeviceUnlocked() && now < instagramLastDraftUntil) {
            instagramLastDraft = requestedRevision
            instagramSay("Actualicé tu borrador: " + requestedRevision +
                ". No se ha enviado. Podés decir «sí, envíala» si autorizás este texto exacto.")
            return true
        }
        if (instagramDraftOfferUntil > now) {
            when (SkyInstagramDraftFlow.approval(message)) {
                SkyInstagramDraftFlow.Approval.YES -> {
                    instagramDraftOfferUntil = 0L
                    proposeInstagramReply()
                    return true
                }
                SkyInstagramDraftFlow.Approval.NO -> {
                    instagramDraftOfferUntil = 0L
                    instagramSay("Está bien, no prepararé ninguna respuesta ahora.")
                    return true
                }
                SkyInstagramDraftFlow.Approval.NONE -> Unit
            }
        }
        return when (SkyInstagramDraftFlow.command(message)) {
            SkyInstagramDraftFlow.Command.PREPARE -> {
                proposeInstagramReply()
                true
            }
            SkyInstagramDraftFlow.Command.CHECK_SEND -> {
                checkInstagramSendReadiness()
                true
            }
            SkyInstagramDraftFlow.Command.COPY -> {
                val draft = instagramLastDraft?.takeIf {
                    instagramDeviceUnlocked() && now < instagramLastDraftUntil
                }
                if (draft == null) instagramSay(
                    "Todavía no hay un borrador vigente para copiar.")
                else {
                    val clipboard = getSystemService(CLIPBOARD_SERVICE) as android.content.ClipboardManager
                    val clip = android.content.ClipData.newPlainText(
                        "Borrador SKY Instagram", draft)
                    if (android.os.Build.VERSION.SDK_INT >= 33) {
                        clip.description.extras = android.os.PersistableBundle().apply {
                            putBoolean(android.content.ClipDescription.EXTRA_IS_SENSITIVE, true)
                        }
                    }
                    clipboard.setPrimaryClip(clip)
                    instagramSay("Copié la respuesta al portapapeles. " +
                        "Podés pegarla en Instagram y enviarla cuando la revisés.")
                }
                true
            }
            SkyInstagramDraftFlow.Command.SEND_REQUEST -> {
                sendApprovedInstagramReply()
                true
            }
            SkyInstagramDraftFlow.Command.STATUS -> {
                checkInstagramReplyReceipt()
                true
            }
            SkyInstagramDraftFlow.Command.NONE -> false
        }
    }


    private val instagramPoll = object : Runnable {
        override fun run() {
            if (!visible) return
            if (!SkyHandsFreeService.health().active) checkInstagramAlerts()
            handler.postDelayed(this, 45_000L)
        }
    }

    private fun checkInstagramAlerts() {
        if (!visible || !SkyInstagramAlerts.enabled(this) ||
            !SkyInstagramAlerts.paired(this) ||
            !instagramChecking.compareAndSet(false, true)) return
        Thread {
            val result = runCatching {
                val snapshot = SkyInstagramAlerts.fetch(this)
                SkyInstagramAlerts.observe(this, snapshot)
            }
            runOnUiThread {
                instagramChecking.set(false)
                if (!visible || isFinishing) return@runOnUiThread
                result.getOrNull()?.let { update ->
                    if (update.newCount > 0 && SkyInstagramAlerts.enabled(this)) {
                        SkyInstagramAlerts.notifyNew(this, update.newCount)
                        instagramNotice(update.newCount)
                    }
                }
            }
        }.start()
    }

    private fun instagramNotice(count: Int) {
        if (count < 1 || !SkyInstagramAlerts.enabled(this)) return
        instagramReviewOfferUntil = android.os.SystemClock.elapsedRealtime() + 120_000L
        val notice = if (count == 1)
            "Te llegó un mensaje nuevo de Instagram. ¿Lo revisamos?"
        else "Te llegaron " + count + " mensajes de Instagram. ¿Los revisamos?"
        if (::home.isInitialized) home.showMessage(notice)
        if (::voicePanel.isInitialized && voicePanel.isVoiceEnabled()) voicePanel.speakReply(notice)
    }

    private fun readInstagramNow() {
        if (!instagramDeviceUnlocked()) {
            instagramSay("Desbloqueá el teléfono para consultar mensajes privados.")
            return
        }
        if (!SkyInstagramAlerts.paired(this)) {
            val message = "Necesito que vinculés Instagram una vez desde Conexión segura."
            home.showMessage(message)
            if (voicePanel.isVoiceEnabled()) voicePanel.speakReply(message)
            return
        }
        home.showMessage("SKY está revisando tus mensajes reales de Instagram.")
        Thread {
            val response = runCatching { SkyInstagramAlerts.fetch(this) }
            runOnUiThread {
                if (isFinishing || !visible) return@runOnUiThread
                if (!instagramDeviceUnlocked()) {
                    instagramSay("Desbloqueá el teléfono para revisar tus mensajes.")
                    return@runOnUiThread
                }
                response.onSuccess { snapshot ->
                    val hasMessages = snapshot.messages.isNotEmpty()
                    instagramDraftOfferUntil = if (hasMessages)
                        android.os.SystemClock.elapsedRealtime() + 120_000L else 0L
                    val summary = SkyInstagramAlerts.summary(snapshot) +
                        if (hasMessages) " ¿Querés que prepare una respuesta al último mensaje?"
                        else ""
                    instagramSay(summary)
                }.onFailure {
                    instagramSay("No pude consultar Instagram: " +
                        (it.message ?: "error de conexión"))
                }
            }
        }.start()
    }

    private fun processInstagramCommand(message: String): Boolean {
        if (processInstagramDraft(message)) return true
        val now = android.os.SystemClock.elapsedRealtime()
        if (instagramReviewOfferUntil > now) {
            when (SkyInstagramDialogue.answer(message)) {
                SkyInstagramDialogue.Answer.YES -> {
                    instagramReviewOfferUntil = 0L
                    readInstagramNow()
                    return true
                }
                SkyInstagramDialogue.Answer.NO -> {
                    instagramReviewOfferUntil = 0L
                    val answer = "Está bien, no los revisaré ahora. Me avisás cuando querás."
                    home.showMessage(answer)
                    if (voicePanel.isVoiceEnabled()) voicePanel.speakReply(answer)
                    return true
                }
                SkyInstagramDialogue.Answer.NONE -> Unit
            }
        }
        return when (SkyInstagramAlerts.command(message)) {
            SkyInstagramAlerts.Command.NONE -> false
            SkyInstagramAlerts.Command.READ -> {
                readInstagramNow()
                true
            }
            SkyInstagramAlerts.Command.ENABLE -> {
                SkyInstagramAlerts.setEnabled(this, true)
                val answer = "Listo. Voy a avisarte cuando reciba nuevos mensajes " +
                    "mientras SKY esté funcionando."
                home.showMessage(answer)
                if (voicePanel.isVoiceEnabled()) voicePanel.speakReply(answer)
                true
            }
            SkyInstagramAlerts.Command.DISABLE -> {
                SkyInstagramAlerts.setEnabled(this, false)
                val answer = "Desactivé los avisos automáticos de Instagram."
                home.showMessage(answer)
                if (voicePanel.isVoiceEnabled()) voicePanel.speakReply(answer)
                true
            }
        }
    }


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
    private var historyBrowserDialog: AlertDialog? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // FLAG_FULLSCREEN prevents adjustResize from moving the chat composer
        // on many keyboards. Android 15/16 use explicit system/IME insets.
        window.clearFlags(android.view.WindowManager.LayoutParams.FLAG_FULLSCREEN)
        window.setSoftInputMode(
            android.view.WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE or
                android.view.WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_HIDDEN
        )
        if (android.os.Build.VERSION.SDK_INT >= 30) {
            window.setDecorFitsSystemWindows(false)
        }
        window.statusBarColor = android.graphics.Color.rgb(7, 11, 32)
        window.navigationBarColor = android.graphics.Color.rgb(7, 11, 32)
        if (android.os.Build.VERSION.SDK_INT >= 29) {
            window.isNavigationBarContrastEnforced = false
        }
        tokens = PrivateTokenStore(this)
        archive = SkyConversationArchive(this)
        longTermMemory = SkyLongTermMemory(this)
        adaptiveMemory = SkyAdaptiveMemory(this)
        actionEvidence = SkyActionEvidence(this)
        voicePanel = SkyEyeVoicePanel(this) { transcript ->
            if (!processPresenceCommand(transcript) &&
                !processQuickCommand(transcript) &&
                !processMusicCommand(transcript) &&
                !processExpressionCommand(transcript) &&
                !processReplyCommand(transcript) &&
                !processCreatorCommand(transcript) &&
                !processMessagingCommand(transcript) &&
                !processInstagramCommand(transcript) &&
                !processOwnerQuestion(transcript) &&
                !processOwnerProfileImport(transcript) &&
                !processScientificCalculation(transcript) &&
                !processStatisticsCalculation(transcript) &&
                !processQuadraticCalculation(transcript) &&
                !processLocalPanelCommand(transcript, spoken = true) &&
                !processCompanionCommand(transcript) &&
                !processDailyCommand(transcript, spoken = true)) {
                // Keep the animated face visible during spoken conversation.
                voiceReplyOnFace = true
                chatInput.setText(transcript)
                if (!tokens.cloudEnabled() && !tokens.groqEnabled() &&
                    tokens.chatToken().isEmpty() &&
                    !SkyLocalConversation.handles(transcript) &&
                    SkyAdaptiveMemory.correctionFromCommand(transcript) == null &&
                    (SkyAdaptiveMemory.ineligibleReason(transcript) != null ||
                        adaptiveMemory.find(transcript) == null) &&
                    SkyAndroidCognition.explicitFact(transcript) == null &&
                    !SkyWeatherNow.isWeatherQuery(transcript) &&
                    !SkyScientificCalculator.isRequest(transcript) &&
                    !SkyStatisticsCalculator.isRequest(transcript) &&
                    !SkyQuadraticSolver.isRequest(transcript) &&
                    !SkyPublicResearch.explicit(transcript) &&
                    !SkyPublicResearch.encyclopedic(transcript) &&
                    !SkyAcademicResearch.explicit(transcript) &&
                    !SkyPublicNews.explicit(transcript) &&
                    !(cognitionEnabled() && (SkyAndroidCognition.memoryQuestion(transcript) ||
                        SkyAndroidCognition.historyQuestion(transcript)))) {
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
            onNewChat = { askNewChat() },
            onSettings = { showSettings() },
            onChatAccess = { showSettings() },
            onAttach = { chooseChatAttachment() },
            onRemoveAttachment = { manageSelectedAttachments() },
            onCancelUpload = {
                pendingFileCancel?.cancel()
                home.showUploadProgress("Cancelando cuando termine el fragmento actual...")
            },
            onHistory = { showHistoryBrowser() },
            onTeach = { showLearningDialog() },
            archive = archive,
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
        installedApps.onReceipt = { action, state, detail, operationId ->
            runCatching {
                actionEvidence.record(action, state, detail, operationId)
                verifiedLearning.observe(action, state)
            }
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
        dailyActions.onReceipt = { action, state, detail ->
            runCatching {
                actionEvidence.record(action, state, detail)
                verifiedLearning.observe(action, state)
            }
        }
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
            this, getSharedPreferences("sky_mobile_music", MODE_PRIVATE),
            tell = { message ->
                // Spoken feedback can seize media audio focus and interrupt songs.
                home.showMessage(message)
            },
            onNeedMusicPermission = { request -> showMusicControlDisclosure(request) }
        )
        musicLauncher.onReceipt = { action, state, detail, operationId ->
            runCatching {
                actionEvidence.record(action, state, detail, operationId)
                verifiedLearning.observe(action, state)
            }
        }
        quickActions = SkyQuickActions(this) { message ->
            // Music commands must not talk over and interrupt the playing track.
            home.showMessage(message)
        }
        quickActions.onReceipt = { action, state, detail ->
            runCatching {
                actionEvidence.record(action, state, detail)
                verifiedLearning.observe(action, state)
            }
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
            if (android.os.Build.VERSION.SDK_INT >= 30) {
                val top = insets.getInsets(android.view.WindowInsets.Type.statusBars()).top
                val navigation = insets.getInsets(android.view.WindowInsets.Type.navigationBars()).bottom
                val keyboardVisible = insets.isVisible(android.view.WindowInsets.Type.ime())
                val keyboard = insets.getInsets(android.view.WindowInsets.Type.ime()).bottom
                home.applyWindowInsets(top, if (keyboardVisible) maxOf(navigation, keyboard)
                    else navigation, keyboardVisible)
            } else {
                // On API 26–29 the platform handles these bars and resizes the
                // activity itself when the keyboard is displayed.
                home.applyWindowInsets(0, 0, false)
            }
            insets
        }
        home.root.requestApplyInsets()
        refreshConnection()
        if (tokens.token().isEmpty() && !tokens.cloudEnabled() && !tokens.groqEnabled()) {
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
        val model = "${android.os.Build.MANUFACTURER} ${android.os.Build.MODEL}"
        val version = runCatching { pm.getPackageInfo(packageName, 0).versionName }
            .getOrDefault("desconocida")
        val accessibilityInstalled = runCatching {
            @Suppress("DEPRECATION")
            val packageInfo = pm.getPackageInfo(packageName,
                android.content.pm.PackageManager.GET_SERVICES)
            packageInfo.services?.any {
                it.permission == android.Manifest.permission.BIND_ACCESSIBILITY_SERVICE
            } == true
        }.getOrDefault(false)
        val micAllowed = checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) ==
            android.content.pm.PackageManager.PERMISSION_GRANTED
        val notificationsAllowed = android.os.Build.VERSION.SDK_INT < 33 ||
            checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) ==
                android.content.pm.PackageManager.PERMISSION_GRANTED
        val speechAvailable = android.speech.SpeechRecognizer.isRecognitionAvailable(this)
        val offlineSpeech = android.os.Build.VERSION.SDK_INT >= 31 &&
            android.speech.SpeechRecognizer.isOnDeviceRecognitionAvailable(this)
        val notes = runCatching {
            org.json.JSONArray(getSharedPreferences("sky_private_notes", MODE_PRIVATE)
                .getString("sky_notes_v1", "[]")).length()
        }.getOrDefault(0)
        val players = listOf(
            "YouTube Music" to "com.google.android.apps.youtube.music",
            "YouTube" to "com.google.android.youtube",
            "Spotify" to "com.spotify.music"
        ).map { (name, pkg) ->
            val installed = pm.getLaunchIntentForPackage(pkg) != null
            val intent = android.content.Intent(
                android.provider.MediaStore.INTENT_ACTION_MEDIA_PLAY_FROM_SEARCH
            ).setPackage(pkg)
            val acceptsIntent = installed && intent.resolveActivity(pm) != null
            "$name: " + when {
                !installed -> "no detectada"
                acceptsIntent -> "instalada · acepta orden musical de Android"
                else -> "instalada · no declara orden musical compatible"
            }
        }
        val unlocked = !(getSystemService(KEYGUARD_SERVICE) as
            android.app.KeyguardManager).isKeyguardLocked
        val voiceHealth = SkyHandsFreeService.health()
        val musicAudio = SkyMusicAudioCheck.read(this)
        val lastVoice = if (voiceHealth.lastPhraseAtMs <= 0L) "sin registro" else
            java.text.SimpleDateFormat("dd/MM/yyyy HH:mm:ss",
                java.util.Locale("es", "NI")).format(
                    java.util.Date(voiceHealth.lastPhraseAtMs))
        val lines = listOf(
            "SKY IA: $version · paquete estándar",
            "Equipo: $model",
            "Android: ${android.os.Build.VERSION.RELEASE} · API ${android.os.Build.VERSION.SDK_INT}",
            "Pantalla desbloqueada: " + if (unlocked) "Sí" else "No",
            "Servicio de accesibilidad en esta APK: " +
                if (accessibilityInstalled) "SÍ · REVISAR" else "No (esperado)",
            "Micrófono autorizado: " + if (micAllowed) "Sí" else "No",
            "Notificaciones autorizadas: " + if (notificationsAllowed) "Sí" else "No",
            "Reconocimiento de voz: " + if (speechAvailable) "Disponible" else "No disponible",
            "Reconocimiento local sin nube: " + if (offlineSpeech) "Disponible" else "No disponible",
            "Servicio manos libres vivo: " + if (voiceHealth.active) "Sí" else "No",
            "Presencia solicitada: " + (handsFreePrefs.getString("sky_presence_mode",
                "WAKE_ONLY") ?: "WAKE_ONLY"),
            "Identificación biométrica de voz: NO DISPONIBLE (no confundir voz a texto con voz del propietario)",
            "Confirmación de órdenes fuera de pantalla: SKY confirmo / SKY cancela",
            "Reconocedor escuchando: " + if (voiceHealth.recognizing) "Sí" else "No",
            "Última frase detectada: $lastVoice",
            "Último error de reconocimiento: ${voiceHealth.errorCode} · reintentos ${voiceHealth.retries}",
            "Voz de SKY: " + if (voicePanel.isSpeechEngineReady()) "Lista" else "Pendiente",
            "Audio multimedia: " + musicAudio.evidence(),
            "Audio: " + musicAudio.guidance(),
            "Apps visibles para abrir: ${installedApps.discover().size}",
            "Notas privadas guardadas: $notes",
            "Groq: " + if (tokens.groqEnabled()) "Configurado (conexión no comprobada)"
                else "No configurado",
            "Gemini: " + if (tokens.cloudEnabled()) "Configurado (conexión no comprobada)"
                else "No configurado",
            "Manos libres: " + if (handsFreePrefs.getBoolean("hands_free_opt_in", false))
                "Activado" else "Desactivado",
            "--- Reproductores ---"
        ).joinToString("\n") + "\n" + players.joinToString("\n") +
            "\n\nEl reproductor puede rechazar una orden aunque esté instalado. " +
            "Play Protect verifica las APK fuera de SKY; esta pantalla no certifica " +
            "la seguridad, no comprueba el audio ni prueba automáticamente servicios remotos."
        AlertDialog.Builder(this)
            .setTitle("SKY · Diagnóstico del Galaxy")
            .setMessage(lines)
            .setNeutralButton("Copiar diagnóstico") { _, _ ->
                val clipboard = getSystemService(CLIPBOARD_SERVICE) as
                    android.content.ClipboardManager
                clipboard.setPrimaryClip(
                    android.content.ClipData.newPlainText("Diagnóstico SKY Android", lines)
                )
                android.widget.Toast.makeText(this,
                    "Diagnóstico copiado sin claves ni identificadores privados.",
                    android.widget.Toast.LENGTH_SHORT).show()
            }
            .setNegativeButton("Control de volumen") { _, _ ->
                SkyMusicAudioCheck.showVolumePanel(this)
            }
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

    /** Perform requested playful expression locally, without using cloud quota. */
    private fun processExpressionCommand(message: String): Boolean {
        val expression = SkyExpressionCommand.parse(message) ?: return false
        val feedback = voicePanel.chooseExpression(expression)
        home.showMessage(feedback)
        if (voicePanel.isVoiceEnabled()) voicePanel.speakReply("Mira, esta es mi expresión.")
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

    /** Private text tasks use Groq first; Gemini is a consented fallback. */
    private fun generateMobileText(prompt: String): String {
        val history = JSONArray()
        if (tokens.groqEnabled()) {
            try {
                return SkyGroqCloud.reply(tokens.groqKey(), prompt, history)
            } catch (error: Exception) {
                if (!tokens.cloudEnabled()) throw error
            }
        }
        if (tokens.cloudEnabled()) {
            return SkyPhoneCloud.reply(tokens.personalCloudKey(), prompt, history)
        }
        throw IllegalStateException("Configurá Groq o Gemini en Ajustes.")
    }

    private fun createReplyDraft(request: SkyContextReply.Request) {
        if (!replyStudio.isApproved(request.contact)) {
            home.showMessage("Ese contacto no está autorizado en SKY.")
            return
        }
        if (!tokens.groqEnabled() && !tokens.cloudEnabled()) {
            home.showMessage("Activá Groq gratis o Gemini en Ajustes para preparar respuestas.")
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
                val draft = generateMobileText(
                    SkyContextReply.prompt(request.contact, request.incoming))
                runOnUiThread {
                    if (!isFinishing) {
                        voicePanel.speakReply("Tengo una respuesta para " +
                            request.contact + ". Revisala antes de enviarla.")
                        replyStudio.preview(request, draft)
                    }
                }
            } catch (_: Exception) {
                runOnUiThread {
                    home.showMessage("No pude preparar esa respuesta. Revisá Groq/Gemini y tu conexión.")
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

    private fun showSkillsCatalog() {
        val labels = SkySkillsCatalog.skills.map {
            it.name + "\n" + it.capability
        }.toTypedArray()
        AlertDialog.Builder(this)
            .setTitle("Habilidades de SKY IA · funciones verificables")
            .setItems(labels) { _, index ->
                val selected = SkySkillsCatalog.skills[index]
                home.openChat()
                chatInput.setText(selected.example)
                chatInput.setSelection(chatInput.text.length)
                home.showMessage("Podés editar esta solicitud y enviarla. " +
                    "SKY no abre por sí misma Canva, Gamma, Claude ni Copilot.")
            }
            .setNegativeButton("Cerrar", null)
            .show()
    }

    private fun chooseChatAttachment() {
        val picker = android.content.Intent(android.content.Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(android.content.Intent.CATEGORY_OPENABLE)
            type = "*/*"
            putExtra(android.content.Intent.EXTRA_ALLOW_MULTIPLE, true)
        }
        runCatching { startActivityForResult(picker, attachmentRequest) }
            .onFailure { home.showMessage("Android no pudo abrir el selector de archivos.") }
    }

    private fun refreshSelectedAttachments() {
        home.setAttachmentLabel(
            if (selectedAttachments.isEmpty()) null
            else selectedAttachments.joinToString(" · ") {
                it.name.take(42) + " (" + it.sizeMb() + " MB)"
            }
        )
    }

    private fun manageSelectedAttachments() {
        if (selectedAttachments.isEmpty()) return
        val files = selectedAttachments.toList()
        val titles = files.map { "Ver vista previa: " + it.name.take(60) } +
            files.map { "Quitar: " + it.name.take(60) } +
            "Quitar todos los adjuntos"
        AlertDialog.Builder(this)
            .setTitle("Archivos · gestionar y visualizar")
            .setItems(titles.toTypedArray()) { _, position ->
                when {
                    position < files.size -> showSelectedAttachmentPreview(files[position])
                    position < files.size * 2 -> {
                        selectedAttachments.removeAll { it.uri == files[position - files.size].uri }
                        refreshSelectedAttachments()
                    }
                    else -> { selectedAttachments.clear(); refreshSelectedAttachments() }
                }
            }
            .setNegativeButton("Cerrar", null)
            .show()
    }

    /** Preview local first; no upload, consent, microphone or external app. */
    private fun showSelectedAttachmentPreview(item: SkyAttachmentBatch.Item) {
        home.showMessage("Preparando una vista previa privada de " + item.name.take(45) + "...")
        execute {
            val preview = runCatching { SkyAttachmentPreview.read(contentResolver, item) }
            runOnUiThread {
                if (isFinishing || selectedAttachments.none { it.uri == item.uri }) return@runOnUiThread
                val body = LinearLayout(this).apply {
                    orientation = LinearLayout.VERTICAL
                    setPadding(28, 14, 28, 14)
                }
                val total = selectedAttachments.size
                body.addView(TextView(this).apply {
                    text = "ARCHIVOS SELECCIONADOS (" + total + ")\n" +
                        selectedAttachments.joinToString("\n") { "• " + it.name.take(65) }
                    textSize = 13f
                    setTextColor(android.graphics.Color.rgb(164, 219, 255))
                })
                var previewOpen = true
                var ownedPreviewBitmap: android.graphics.Bitmap? = null
                var previewImage: android.widget.ImageView? = null
                preview.onSuccess { result ->
                    if (result.bitmap != null) {
                        ownedPreviewBitmap = result.bitmap
                        val image = android.widget.ImageView(this@MainActivity).apply {
                            setImageBitmap(result.bitmap)
                            adjustViewBounds = true
                            maxHeight = (resources.displayMetrics.density * 330).toInt()
                            scaleType = android.widget.ImageView.ScaleType.FIT_CENTER
                            contentDescription = result.label
                        }
                        previewImage = image
                        body.addView(image, LinearLayout.LayoutParams(-1, -2))
                        if (result.pageCount > 1) {
                            val controls = LinearLayout(this@MainActivity).apply {
                                orientation = LinearLayout.HORIZONTAL
                                gravity = android.view.Gravity.CENTER_VERTICAL
                            }
                            var currentPage = result.pageIndex
                            var loadingPage = false
                            val counter = TextView(this@MainActivity).apply {
                                text = "Página 1 de " + result.pageCount
                                textSize = 13f
                                setTextColor(android.graphics.Color.WHITE)
                                gravity = android.view.Gravity.CENTER
                            }
                            val previous = Button(this@MainActivity).apply {
                                text = "Anterior"
                                isEnabled = false
                            }
                            val next = Button(this@MainActivity).apply {
                                text = "Siguiente"
                            }
                            fun updateControls() {
                                previous.isEnabled = !loadingPage && currentPage > 0
                                next.isEnabled = !loadingPage && currentPage < result.pageCount - 1
                            }
                            fun navigate(delta: Int) {
                                val requested = currentPage + delta
                                if (loadingPage || requested !in 0 until result.pageCount) return
                                loadingPage = true
                                updateControls()
                                executor.execute {
                                    val page = runCatching {
                                        SkyAttachmentPreview.readPdfPage(
                                            contentResolver, item, requested)
                                    }
                                    runOnUiThread {
                                        if (isFinishing || !previewOpen) {
                                            page.getOrNull()?.bitmap?.recycle()
                                            return@runOnUiThread
                                        }
                                        page.onSuccess { loaded ->
                                            val previousBitmap = ownedPreviewBitmap
                                            image.setImageBitmap(loaded.bitmap)
                                            ownedPreviewBitmap = loaded.bitmap
                                            if (previousBitmap !== loaded.bitmap) {
                                                previousBitmap?.recycle()
                                            }
                                            image.contentDescription = loaded.label
                                            currentPage = requested
                                            counter.text = "Página " + (currentPage + 1) +
                                                " de " + result.pageCount
                                        }.onFailure { error ->
                                            counter.text = "No se pudo leer la página: " +
                                                (error.message ?: "error de lectura")
                                        }
                                        loadingPage = false
                                        updateControls()
                                    }
                                }
                            }
                            previous.setOnClickListener { navigate(-1) }
                            next.setOnClickListener { navigate(1) }
                            controls.addView(previous, LinearLayout.LayoutParams(0, -2, 1f))
                            controls.addView(counter, LinearLayout.LayoutParams(0, -2, 1f))
                            controls.addView(next, LinearLayout.LayoutParams(0, -2, 1f))
                            body.addView(controls)
                        }
                    }
                    body.addView(TextView(this).apply {
                        text = result.label + "\n\n" + result.details.take(5700)
                        setTextColor(android.graphics.Color.WHITE)
                        textSize = 14f
                        setTextIsSelectable(true)
                        setPadding(0, 14, 0, 14)
                    })
                }.onFailure { error ->
                    body.addView(TextView(this).apply {
                        text = "La vista previa local no está disponible: " +
                            (error.message ?: "formato o permisos no compatibles") +
                            "\nEl archivo sigue seleccionado; aún no se envió a la nube."
                        setTextColor(android.graphics.Color.WHITE)
                        textSize = 14f
                    })
                }
                body.addView(TextView(this).apply {
                    text = "\n¿Qué querés que haga SKY con este archivo? Podés pedir " +
                        "resumir, explicar, resolver, extraer datos, comparar o revisar errores. " +
                        "La vista previa es parcial; la lectura completa depende del formato y del proveedor."
                    textSize = 14f
                    setTextColor(android.graphics.Color.rgb(185, 228, 250))
                })
                val instruction = EditText(this).apply {
                    hint = "Escribí tu instrucción para SKY..."
                    setText(chatInput.text.toString())
                    inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE
                    minLines = 2
                    maxLines = 5
                    setTextColor(android.graphics.Color.WHITE)
                    setHintTextColor(android.graphics.Color.LTGRAY)
                }
                body.addView(instruction)
                val scroller = ScrollView(this).apply { addView(body) }
                val previewDialog = AlertDialog.Builder(this)
                    .setTitle("SKY · Vista previa privada")
                    .setView(scroller)
                    .setPositiveButton("Preparar consulta") { _, _ ->
                        val task = instruction.text.toString().trim()
                        if (task.isNotEmpty()) {
                            chatInput.setText(task)
                            chatInput.setSelection(chatInput.text.length)
                        }
                        home.openChat()
                        home.showMessage("Tus archivos están listos. " +
                            "Enviá la consulta cuando quieras; SKY pedirá autorización " +
                            "antes de compartirlos con Gemini.")
                    }
                    .setNeutralButton("Otro archivo") { _, _ -> manageSelectedAttachments() }
                    .setNegativeButton("Ahora no", null)
                    .create()
                previewDialog.setOnDismissListener {
                    previewOpen = false
                    previewImage?.setImageBitmap(null)
                    ownedPreviewBitmap?.recycle()
                    ownedPreviewBitmap = null
                }
                previewDialog.show()
            }
        }
    }

    private fun chooseOwnerProfileImport() {
        val picker = android.content.Intent(android.content.Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(android.content.Intent.CATEGORY_OPENABLE)
            type = "*/*"
        }
        startActivityForResult(picker, profileImportRequest)
    }

    private fun showOwnerProfile() {
        val editor = EditText(this).apply {
            setText(SkyOwnerContext.read(this@MainActivity))
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE
            setMinLines(6)
            setMaxLines(14)
            filters = arrayOf(InputFilter.LengthFilter(SkyOwnerContext.MAX_CHARS))
            setPadding(24, 24, 24, 24)
            hint = "Quién soy, trabajo, proyectos, preferencias y objetivos. Sin contraseñas."
        }
        AlertDialog.Builder(this)
            .setTitle("Mi perfil · memoria personal local")
            .setMessage("Podés editar o importar USER.md desde SKY Windows. " +
                "El perfil queda en este teléfono y solo se envía a un modelo remoto " +
                "cuando marcás autorización de datos privados para la consulta.")
            .setView(editor)
            .setPositiveButton("Guardar") { _, _ ->
                runCatching { SkyOwnerContext.save(this, editor.text.toString()) }
                    .onSuccess { home.showMessage("Perfil personal guardado en este teléfono.") }
                    .onFailure { home.showMessage(it.message ?: "No pude guardar el perfil.") }
            }
            .setNeutralButton("Importar USER.md") { _, _ -> chooseOwnerProfileImport() }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    private fun confirmOwnerImport(prepared: String) {
        AlertDialog.Builder(this)
            .setTitle("Revisar perfil importado de Windows")
            .setMessage("Vista previa:\n\n" + prepared.take(850) +
                if (prepared.length > 850) "\n…\n\nConfirmá cómo guardar esta información." else
                    "\n\nConfirmá cómo guardar esta información.")
            .setPositiveButton("Fusionar sin duplicar") { _, _ ->
                runCatching { SkyOwnerContext.merge(this, prepared) }
                    .onSuccess { home.showMessage("Perfil fusionado: $it caracteres.") }
                    .onFailure { home.showMessage(it.message ?: "No fue posible fusionar el perfil.") }
            }
            .setNeutralButton("Reemplazar perfil") { _, _ ->
                runCatching { SkyOwnerContext.save(this, prepared) }
                    .onSuccess { home.showMessage("Perfil reemplazado con confirmación.") }
                    .onFailure { home.showMessage(it.message ?: "No se reemplazó el perfil.") }
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    /** Aprender solo de una respuesta que el dueño revisó: no de cualquier web o chat. */
    /** Prueba HTTPS REAL desde el teléfono. No usa conversaciones privadas. */
    private fun testGeminiModelsOnDevice() {
        if (!tokens.cloudEnabled()) {
            home.showMessage("Primero configurá y verificá tu clave Gemini desde Ajustes.")
            return
        }
        AlertDialog.Builder(this)
            .setTitle("SKY · Diagnóstico REAL de modelos")
            .setMessage("SKY enviará tres consultas de prueba SIN información personal " +
                "a Google Gemini (económico, Flash y profundo). " +
                "Puede consumir cuota; las respuestas y errores quedarán registrados " +
                "localmente como prueba de conexión, NO como prueba de razonamiento correcto. " +
                "No es una validación del micrófono ni del control de aplicaciones.")
            .setPositiveButton("Probar los tres modelos") { _, _ ->
                home.showMessage("Comprobando las API de Gemini desde este teléfono...")
                executor.execute {
                    val commands = listOf(
                        "Modo económico: Respondé únicamente la palabra LISTA.",
                        "Modo flash: Respondé únicamente la palabra LISTA.",
                        "Modo profundo: Respondé únicamente la palabra LISTA."
                    )
                    val results = mutableListOf<String>()
                    for (command in commands) {
                        val selected = SkyGeminiModes.select(command)
                        val started = android.os.SystemClock.elapsedRealtime()
                        val result = runCatching {
                            SkyPhoneCloud.reply(tokens.personalCloudKey(), command, JSONArray())
                        }
                        val elapsed = android.os.SystemClock.elapsedRealtime() - started
                        if (result.isSuccess && !result.getOrNull().isNullOrBlank()) {
                            runCatching { actionEvidence.record(
                                "Gemini · " + selected.model, "RECEIVED_RESPONSE",
                                "Respuesta HTTP válida y no vacía, duración: " + elapsed +
                                    " ms. Calidad de respuesta no verificada."
                            ) }
                            results.add(selected.model + ": respondió (" + elapsed + " ms)")
                        } else {
                            val reason = result.exceptionOrNull()?.message.orEmpty().take(190)
                                .ifBlank { "Sin respuesta de texto" }
                            runCatching { actionEvidence.record(
                                "Gemini · " + selected.model, "FAILED", reason
                            ) }
                            results.add(selected.model + ": ERROR · " + reason)
                        }
                    }
                    runOnUiThread {
                        if (isFinishing || isDestroyed) return@runOnUiThread
                        AlertDialog.Builder(this)
                            .setTitle("Resultados reales · Gemini")
                            .setMessage(results.joinToString("\n\n") +
                                "\n\nRevisá también Ajustes → Evidencias. " +
                                "Esta prueba no certifica la app completa.")
                            .setPositiveButton("Entendido", null).show()
                    }
                }
            }
            .setNegativeButton("Cancelar", null).show()
    }

    private fun showLearningDialog() {
        // Evitar enseñar una respuesta local de "recuerda que..." o acción.
        val entry = archive.recent(40).lastOrNull { saved ->
            SkyAdaptiveMemory.ineligibleReason(saved.question) == null &&
                !saved.engine.startsWith("SKY · memoria", ignoreCase = true)
        }
        if (entry == null) {
            home.showMessage("Primero conversá con SKY para corregir una respuesta.")
            return
        }
        val restriction = SkyAdaptiveMemory.ineligibleReason(entry.question)
        if (restriction != null) {
            AlertDialog.Builder(this)
                .setTitle("Esta respuesta no se puede memorizar automáticamente")
                .setMessage(restriction + "\n\nSKY no guardará acciones ni datos que pueden quedar desactualizados.")
                .setPositiveButton("Entendido", null).show()
            return
        }
        val editor = EditText(this).apply {
            setText(entry.answer)
            setSelection(text.length)
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE
            minLines = 3
            maxLines = 10
            filters = arrayOf(InputFilter.LengthFilter(8000))
            setPadding(28, 20, 28, 20)
        }
        AlertDialog.Builder(this)
            .setTitle("Enseñarle una respuesta correcta a SKY")
            .setMessage("Consulta original: " + entry.question.take(240) +
                "\n\nRevisá o corregí la respuesta. SKY la reutilizará LOCALMENTE " +
                "solo cuando vuelvas a hacer esa misma pregunta. No entrena pesos ni " +
                "envía correcciones sin permiso.")
            .setView(editor)
            .setPositiveButton("Guardar corrección") { _, _ ->
                runCatching { adaptiveMemory.teach(entry.question, editor.text.toString()) }
                    .onSuccess {
                        home.showMessage("Corrección aprendida y comprobada en memoria local.")
                        voicePanel.express("¡Qué bien! Gracias por enseñarme una respuesta.")
                    }
                    .onFailure { home.showMessage(it.message ?: "No se guardó la corrección.") }
            }
            .setNegativeButton("Cancelar", null).show()
    }

    private fun showLearnedResponses() {
        val learned = adaptiveMemory.recent(80)
        if (learned.isEmpty()) {
            home.showMessage("Aún no hay respuestas corregidas. Abrí Conversación → Enseñar.")
            return
        }
        val labels = learned.map { it.question.take(90) + " · usada " + it.used + " vez/veces" }
        AlertDialog.Builder(this)
            .setTitle("SKY · Respuestas aprendidas localmente")
            .setItems(labels.toTypedArray()) { _, index ->
                val item = learned[index]
                AlertDialog.Builder(this)
                    .setTitle(item.question.take(100))
                    .setMessage(item.answer.take(1500) +
                        "\n\nSolo se reutiliza para la misma pregunta; " +
                        "nunca como prueba de una acción en Android.")
                    .setPositiveButton("Entendido", null)
                    .setNeutralButton("Eliminar") { _, _ ->
                        if (adaptiveMemory.delete(item.id))
                            home.showMessage("Corrección eliminada del teléfono.")
                    }.show()
            }
            .setNegativeButton("Cerrar", null).show()
    }

    private fun reviewMemoryLines() {
        val saved = longTermMemory.recent(150)
        val profile = SkyOwnerContext.memoryLines(this)
        if (saved.isEmpty() && profile.isEmpty()) {
            home.showMessage("Todavía no hay recuerdos personales guardados.")
            return
        }
        val labels = saved.map { "Memoria larga · " + it.text.take(95) } +
            profile.map { "Perfil · " + it.take(95) }
        AlertDialog.Builder(this)
            .setTitle("Memoria personal · consultar o eliminar")
            .setItems(labels.toTypedArray()) { _, index ->
                val inDatabase = index < saved.size
                val detail = if (inDatabase) saved[index].text else profile[index - saved.size]
                AlertDialog.Builder(this)
                    .setTitle("Quitar este dato de SKY Android")
                    .setMessage(detail + "\n\nLa eliminación no afecta otras copias ni SKY Windows.")
                    .setPositiveButton("Eliminar este dato") { _, _ ->
                        val removed = if (inDatabase) longTermMemory.delete(saved[index].id)
                            else SkyOwnerContext.removeLine(this, detail)
                        home.showMessage(if (removed) "Recuerdo eliminado del teléfono."
                            else "No encontré ese recuerdo.")
                    }
                    .setNegativeButton("Cancelar", null)
                    .show()
            }
            .setNegativeButton("Cerrar", null).show()
    }

    /** Historial premium local: los datos no salen del teléfono. */
    private fun showHistoryBrowser(query: String = "", beforeId: Long? = null) {
        historyBrowserDialog?.dismiss()
        settingsDialog?.dismiss()
        historyBrowserDialog = SkyPremiumHistory(
            this, archive,
            onOpenChat = { entry -> home.openSavedExchange(entry) },
            onExportEntry = { entry -> chooseResponseExport(entry) },
            onExportAll = { confirmHistoryExport() },
            onHistoryChanged = { home.reloadHistory() }
        ).show(query, beforeId)
    }

    private fun chooseResponseExport(entry: SkyConversationArchive.Entry) {
        val textFormats = SkyResponseExport.Format.values()
        val officeFormats = SkyNativeOfficeExport.Format.values()
        val choices = textFormats.map { it.label } + officeFormats.map { it.label } +
            listOf("Infografía SVG vectorial editable")
        AlertDialog.Builder(this)
            .setTitle("Guardar respuesta de SKY")
            .setMessage("Elegí un formato editable. Word y PowerPoint son archivos " +
                "Office Open XML auténticos: texto y formas editables. Las diapositivas " +
                "se organizan por secciones. El SVG contiene hasta cuatro ideas en " +
                "objetos vectoriales editables. Revisá los datos antes de compartir.")
            .setItems(choices.toTypedArray()) { _, option ->
                val isVector = option == textFormats.size + officeFormats.size
                val isOffice = option >= textFormats.size && !isVector
                val mime: String
                val name: String
                val code: Int
                if (isVector) {
                    vectorExportPending = entry
                    mime = SkyVectorExport.MIME
                    name = SkyVectorExport.filename(entry)
                    code = vectorExportRequest
                } else if (isOffice) {
                    val format = officeFormats[option - textFormats.size]
                    nativeOfficeExportPending = entry to format
                    mime = format.mime
                    name = SkyNativeOfficeExport.filename(entry, format)
                    code = nativeOfficeExportRequest
                } else {
                    val format = textFormats[option]
                    responseExportPending = entry to format
                    mime = format.mime
                    name = SkyResponseExport.filename(entry, format)
                    code = responseExportRequest
                }
                val intent = android.content.Intent(
                    android.content.Intent.ACTION_CREATE_DOCUMENT
                ).apply {
                    addCategory(android.content.Intent.CATEGORY_OPENABLE)
                    type = mime
                    putExtra(android.content.Intent.EXTRA_TITLE, name)
                }
                runCatching { startActivityForResult(intent, code) }
                    .onFailure {
                        if (isVector) vectorExportPending = null
                        else if (isOffice) nativeOfficeExportPending = null
                        else responseExportPending = null
                        home.showMessage("Android no abrió el destino de guardado.")
                    }
            }
            .setNegativeButton("Cancelar", null).show()
    }

    /** Generate an actual editable DOCX from a completed local reply. */
    private fun startWordExport(entry: SkyConversationArchive.Entry) {
        nativeOfficeExportPending = entry to SkyNativeOfficeExport.Format.WORD
        val intent = android.content.Intent(android.content.Intent.ACTION_CREATE_DOCUMENT).apply {
            addCategory(android.content.Intent.CATEGORY_OPENABLE)
            type = SkyNativeOfficeExport.Format.WORD.mime
            putExtra(android.content.Intent.EXTRA_TITLE,
                SkyNativeOfficeExport.filename(entry, SkyNativeOfficeExport.Format.WORD))
        }
        runCatching { startActivityForResult(intent, nativeOfficeExportRequest) }
            .onFailure {
                nativeOfficeExportPending = null
                home.showMessage("Android no permitió elegir dónde guardar el Word.")
            }
    }

    private fun chooseExistingWordForExport() {
        // Present the source clearly: a prior "cómo guardar" answer must not
        // silently replace the requested document with unrelated instructions.
        val entries = archive.recent(30).asReversed()
            .filter { it.answer.isNotBlank() }.take(20)
        if (entries.isEmpty()) {
            home.showMessage("Todavía no hay respuestas para convertir en Word.")
            return
        }
        if (entries.size == 1) {
            startWordExport(entries.first())
            return
        }
        val titles = entries.map { it.title + " · " + it.localTime() }.toTypedArray()
        AlertDialog.Builder(this)
            .setTitle("¿Cuál respuesta querés guardar en Word?")
            .setMessage("SKY creará un documento DOCX editable de la respuesta que elijás, " +
                "sin copiar y pegar ni enviar el contenido a otro servidor.")
            .setItems(titles) { _, index -> startWordExport(entries[index]) }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    private fun exportLatestResponse() {
        val entry = archive.recent(1).lastOrNull()
        if (entry == null) home.showMessage("Todavía no hay consultas guardadas.")
        else chooseResponseExport(entry)
    }

    private fun confirmHistoryExport() {
        AlertDialog.Builder(this)
            .setTitle("Exportar historial de SKY")
            .setMessage("El archivo JSON contendrá consultas, respuestas y fechas. " +
                "Puede incluir información personal. Se guardará donde vos elijás, " +
                "sin subirlo automáticamente a internet. Protegelo antes de compartirlo.")
            .setPositiveButton("Elegir destino") { _, _ ->
                val filename = "SKY-Historial-" +
                    java.time.LocalDate.now().toString() + ".json"
                val intent = android.content.Intent(android.content.Intent.ACTION_CREATE_DOCUMENT).apply {
                    addCategory(android.content.Intent.CATEGORY_OPENABLE)
                    type = "application/json"
                    putExtra(android.content.Intent.EXTRA_TITLE, filename)
                }
                runCatching { startActivityForResult(intent, historyExportRequest) }
                    .onFailure { home.showMessage("Android no pudo abrir el guardado de archivos.") }
            }
            .setNegativeButton("Cancelar", null).show()
    }

    @Deprecated("Uses the Android camera thumbnail; no image is stored.")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: android.content.Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == attachmentRequest) {
            if (resultCode == RESULT_OK && data != null) {
                val chosen = mutableListOf<android.net.Uri>()
                data.clipData?.let { clip ->
                    for (index in 0 until clip.itemCount) {
                        clip.getItemAt(index).uri?.let { chosen.add(it) }
                    }
                }
                data.data?.let { chosen.add(it) }
                val unique = chosen.distinctBy { it.toString() }
                val existing = selectedAttachments.toList()
                execute {
                    runCatching {
                        require(unique.isNotEmpty()) { "No seleccionaste ningún archivo." }
                        require(unique.size + existing.size <= SkyAttachmentBatch.MAX_FILES ||
                            unique.any { uri -> existing.any { it.uri == uri } }) {
                            "Máximo cinco archivos por consulta."
                        }
                        val added = unique.map { uri ->
                            SkyAttachmentBatch.readMetadata(contentResolver, uri)
                        }
                        SkyAttachmentBatch.validate(existing, added)
                    }.onSuccess { result -> runOnUiThread {
                        selectedAttachments.clear()
                        selectedAttachments.addAll(result)
                        refreshSelectedAttachments()
                        home.openChat()
                        // Primero visualizar el archivo y preguntar el objetivo.
                        // El envío sigue separado y con autorización expresa.
                        showSelectedAttachmentPreview(result.last())
                    } }.onFailure { error -> runOnUiThread {
                        home.showMessage(error.message ?: "No pude preparar la selección.")
                    } }
                }
            }
            return
        }
        if (requestCode == profileImportRequest) {
            if (resultCode == RESULT_OK && data?.data != null) {
                val uri = data.data!!
                execute {
                    runCatching {
                        val imported = contentResolver.openInputStream(uri)?.bufferedReader(Charsets.UTF_8)
                            ?.use { it.readText().take(30_001) }
                            ?: throw IllegalArgumentException("Android no pudo abrir USER.md.")
                        SkyOwnerContext.parseWindows(imported)
                    }.onSuccess { prepared -> runOnUiThread {
                        confirmOwnerImport(prepared)
                    } }.onFailure { error -> runOnUiThread {
                        home.showMessage(error.message ?: "No pude importar el perfil.")
                    } }
                }
            }
            return
        }
        if (requestCode == generatedImageSaveRequest) {
            val image = generatedImageToSave
            generatedImageToSave = null
            if (resultCode == RESULT_OK && data?.data != null && image != null) {
                val uri = data.data!!
                execute {
                    runCatching {
                        contentResolver.openOutputStream(uri, "w")?.use {
                            it.write(image.bytes)
                        } ?: throw IllegalStateException("No se pudo guardar la imagen.")
                    }.onSuccess { runOnUiThread {
                        home.showMessage("Imagen de IA real guardada en el destino seleccionado.")
                    } }.onFailure { error -> runOnUiThread {
                        home.showMessage(error.message ?: "Falló el guardado de imagen.")
                    } }
                }
            }
            return
        }
        if (requestCode == generatedVideoSaveRequest) {
            val file = generatedVideoToSave
            if (resultCode == RESULT_OK && data?.data != null && file != null) {
                val uri = data.data!!
                execute {
                    runCatching {
                        require(file.isFile && file.length() > 1024) {
                            "El MP4 aún no existe o está incompleto."
                        }
                        contentResolver.openOutputStream(uri, "w")?.use { output ->
                            file.inputStream().use { input -> input.copyTo(output) }
                        } ?: throw IllegalStateException("No se pudo guardar el MP4.")
                    }.onSuccess { runOnUiThread {
                        home.showMessage("Video MP4 real guardado correctamente.")
                    } }.onFailure { error -> runOnUiThread {
                        home.showMessage(error.message ?: "No pude guardar el MP4.")
                    } }
                }
            }
            return
        }
        if (requestCode == vectorExportRequest) {
            val selected = vectorExportPending
            vectorExportPending = null
            if (resultCode == RESULT_OK && data?.data != null && selected != null) {
                val uri = data.data!!
                execute {
                    runCatching {
                        val file = contentResolver.openOutputStream(uri, "w")
                            ?: throw IllegalArgumentException("No se pudo crear el SVG.")
                        file.use { SkyVectorExport.write(it, selected) }
                    }.onSuccess { runOnUiThread {
                        home.showMessage("Infografía SVG editable guardada. " +
                            "Contiene un máximo de cuatro ideas de la respuesta.")
                    } }.onFailure { error -> runOnUiThread {
                        home.showMessage(error.message ?: "No pude exportar el SVG.")
                    } }
                }
            }
            return
        }
        if (requestCode == nativeOfficeExportRequest) {
            val pending = nativeOfficeExportPending
            nativeOfficeExportPending = null
            if (resultCode == RESULT_OK && data?.data != null && pending != null) {
                val uri = data.data!!
                execute {
                    runCatching {
                        val stream = contentResolver.openOutputStream(uri, "w")
                            ?: throw IllegalArgumentException("Android no permitió crear el archivo.")
                        stream.use {
                            SkyNativeOfficeExport.write(it, pending.first, pending.second)
                        }
                    }.onSuccess { runOnUiThread {
                        home.showMessage("Documento " + pending.second.extension.uppercase() +
                            " guardado. Abrilo en Word, PowerPoint o un editor compatible.")
                    } }.onFailure { error -> runOnUiThread {
                        home.showMessage("No se pudo crear el archivo Office: " +
                            (error.message ?: "error de exportación"))
                    } }
                }
            }
            return
        }
        if (requestCode == responseExportRequest) {
            val pending = responseExportPending
            responseExportPending = null
            if (resultCode == RESULT_OK && data?.data != null && pending != null) {
                val uri = data.data!!
                execute {
                    runCatching {
                        val output = contentResolver.openOutputStream(uri, "w")
                            ?: throw IllegalArgumentException("No pude crear el documento.")
                        output.use { SkyResponseExport.write(it, pending.first, pending.second) }
                    }.onSuccess { size -> runOnUiThread {
                        home.showMessage("Respuesta guardada: " + size + " bytes.")
                    } }.onFailure { error -> runOnUiThread {
                        home.showMessage(error.message ?: "No pude guardar la respuesta.")
                    } }
                }
            }
            return
        }
        if (requestCode == historyExportRequest) {
            if (resultCode == RESULT_OK && data?.data != null) {
                val uri = data.data!!
                execute {
                    runCatching {
                        val output = contentResolver.openOutputStream(uri, "w")
                            ?: throw IllegalArgumentException("No pude crear el archivo.")
                        output.use { archive.writeJson(it) }
                    }.onSuccess { count -> runOnUiThread {
                        home.showMessage("Exportación terminada: $count consultas guardadas.")
                    } }.onFailure { error -> runOnUiThread {
                        home.showMessage(error.message ?: "No pude exportar el historial.")
                    } }
                }
            }
            return
        }
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
    private fun startRealImageGeneration() {
        if (!tokens.cloudEnabled()) {
            home.showMessage("La generación real de imágenes necesita una clave Gemini en Ajustes.")
            return
        }
        if (imageGenerationPending) {
            home.showMessage("SKY está creando otra imagen. Terminá esa consulta primero.")
            return
        }
        val field = EditText(this).apply {
            hint = "Ejemplo: Ilustración editorial profesional de un volcán de Nicaragua al amanecer"
            minLines = 3
            maxLines = 6
            setText(archive.recent(1).lastOrNull()?.question?.take(220).orEmpty())
        }
        val ratios = listOf("1:1", "16:9", "9:16", "4:3", "3:4")
        AlertDialog.Builder(this)
            .setTitle("SKY · Imagen generada con IA real")
            .setView(field)
            .setMessage("Utilizaré el modelo de imágenes Gemini Nano Banana 2.1. " +
                "La descripción se enviará a Google solamente si autorizás esta consulta. " +
                "Puede consumir cuota o facturación del proyecto y no estar habilitado en tu clave. " +
                "No crearé una plantilla como sustituto si el proveedor falla.")
            .setPositiveButton("Elegir proporción") { _, _ ->
                val prompt = field.text.toString()
                if (prompt.trim().length !in 12..1500) {
                    home.showMessage("Describí la imagen con 12 a 1500 caracteres.")
                } else {
                    AlertDialog.Builder(this)
                        .setTitle("Proporción de imagen")
                        .setItems(ratios.toTypedArray()) { _, choice ->
                            confirmRealImage(prompt, ratios[choice])
                        }
                        .setNegativeButton("Cancelar", null).show()
                }
            }
            .setNegativeButton("Cancelar", null).show()
    }

    private fun confirmRealImage(prompt: String, ratio: String) {
        val normalized = prompt.trim()
        if (normalized.length !in 12..1500) {
            home.showMessage("Describí la imagen con 12 a 1500 caracteres.")
            return
        }
        AlertDialog.Builder(this)
            .setTitle("Autorizar una imagen de IA")
            .setMessage("Modelo: Gemini Nano Banana 2.1 · proporción " + ratio +
                ". Google procesará la descripción. La API puede consumir cuota o dinero. " +
                "No se generará nada ni se enviará información hasta tu autorización.")
            .setPositiveButton("Generar imagen") { _, _ ->
                if (imageGenerationPending) return@setPositiveButton
                imageGenerationPending = true
                home.showMessage("Solicitando imagen auténtica al modelo Gemini...")
                execute {
                    try {
                        val result = SkyGeneratedImage.generate(
                            tokens.personalCloudKey(), normalized, ratio)
                        runOnUiThread {
                            imageGenerationPending = false
                            val bitmap = android.graphics.BitmapFactory.decodeByteArray(
                                result.bytes, 0, result.bytes.size)
                            if (bitmap == null) {
                                home.showMessage("Gemini respondió, pero Android no decodificó la imagen.")
                            } else {
                                val preview = android.widget.ImageView(this).apply {
                                    setImageBitmap(bitmap)
                                    adjustViewBounds = true
                                    setPadding(20, 16, 20, 16)
                                    contentDescription = "Imagen original generada con Gemini"
                                }
                                AlertDialog.Builder(this)
                                    .setTitle("Imagen creada por " + result.model)
                                    .setView(preview)
                                    .setPositiveButton("Guardar imagen") { _, _ ->
                                        generatedImageToSave = result
                                        val extension = when (result.mime) {
                                            "image/jpeg" -> "jpg"
                                            "image/webp" -> "webp"
                                            else -> "png"
                                        }
                                        val intent = android.content.Intent(
                                            android.content.Intent.ACTION_CREATE_DOCUMENT).apply {
                                            addCategory(android.content.Intent.CATEGORY_OPENABLE)
                                            type = result.mime
                                            putExtra(android.content.Intent.EXTRA_TITLE,
                                                "SKY-Imagen-IA." + extension)
                                        }
                                        runCatching { startActivityForResult(
                                            intent, generatedImageSaveRequest) }
                                            .onFailure {
                                                generatedImageToSave = null
                                                home.showMessage("No pude abrir el destino de imagen.")
                                            }
                                    }
                                    .setNegativeButton("Descartar", null)
                                    .show()
                            }
                        }
                    } catch (e: Exception) {
                        runOnUiThread {
                            imageGenerationPending = false
                            home.showMessage(e.message ?: "El generador de IA no devolvió imagen.")
                        }
                    }
                }
            }
            .setNegativeButton("Cancelar", null).show()
    }

    private fun startPaidAiVideoCreation() {
        if (!tokens.cloudEnabled()) {
            home.showMessage("Necesitás una clave Gemini con facturación activada para video de IA.")
            return
        }
        if (videoPending) {
            home.showMessage("Ya hay otro video en proceso.")
            return
        }
        val editor = EditText(this).apply {
            hint = "Ejemplo: Toma cinematográfica de un lago de Nicaragua al amanecer, dron lento, con sonido ambiente."
            minLines = 4
            maxLines = 8
        }
        AlertDialog.Builder(this)
            .setTitle("SKY · Generación de video IA de pago")
            .setView(editor)
            .setMessage("Modelo Gemini Omni Flash 1.1. El video se genera realmente " +
                "con IA y puede incluir audio. La API no dispone de nivel gratuito. " +
                "No se enviará ningún trabajo ni se cobrará sin tu autorización.")
            .setPositiveButton("Revisar costo") { _, _ ->
                val prompt = editor.text.toString().trim()
                if (prompt.length !in 20..1400) {
                    home.showMessage("Describí una escena de 20 a 1400 caracteres.")
                } else {
                    AlertDialog.Builder(this)
                        .setTitle("Autorización expresa · API de pago")
                        .setMessage("Google cobra por generación de video. " +
                            "Como referencia oficial, 720p ronda US$0.10 por segundo, " +
                            "más costos de entrada; el precio real y 360p pueden variar. " +
                            "El clip generado dura entre 3 y 10 segundos. " +
                            "SKY no controla la facturación de tu proyecto Google. " +
                            "La operación NO se enviará sin que elijás «Autorizar».")
                        .setPositiveButton("Autorizar video de pago") { _, _ ->
                            videoPending = true
                            home.showMessage("Solicitando video auténtico a Gemini Omni Flash...")
                            execute {
                                try {
                                    val file = SkyAiVideo.create(
                                        applicationContext, tokens.personalCloudKey(),
                                        prompt, "9:16")
                                    runOnUiThread {
                                        videoPending = false
                                        generatedVideoToSave = file
                                        AlertDialog.Builder(this)
                                            .setTitle("Video generado con IA auténtica")
                                            .setMessage("Gemini entregó un MP4 y Android comprobó " +
                                                "que contiene una pista de video. " +
                                                "Tamaño: " + file.length() +
                                                " bytes. Guardalo para revisarlo antes de compartir.")
                                            .setPositiveButton("Guardar MP4 IA") { _, _ ->
                                                val intent = android.content.Intent(
                                                    android.content.Intent.ACTION_CREATE_DOCUMENT).apply {
                                                    addCategory(android.content.Intent.CATEGORY_OPENABLE)
                                                    type = "video/mp4"
                                                    putExtra(android.content.Intent.EXTRA_TITLE,
                                                        "SKY-Video-IA.mp4")
                                                }
                                                runCatching { startActivityForResult(
                                                    intent, generatedVideoSaveRequest) }
                                                    .onFailure { home.showMessage(
                                                        "No pude abrir el destino del MP4.") }
                                            }
                                            .setNegativeButton("Cerrar", null).show()
                                    }
                                } catch (error: Exception) {
                                    runOnUiThread {
                                        videoPending = false
                                        home.showMessage(error.message ?:
                                            "Gemini no devolvió un video real.")
                                    }
                                }
                            }
                        }
                        .setNegativeButton("Cancelar sin consumir", null).show()
                }
            }
            .setNegativeButton("Cancelar", null).show()
    }

    private fun startNativeVideoEditor() {
        val previous = archive.recent(1).lastOrNull()?.answer.orEmpty()
        val editor = EditText(this).apply {
            hint = "Escribí un guion para cinco escenas de texto animado."
            setText(previous.take(1800))
            minLines = 5
            maxLines = 11
        }
        AlertDialog.Builder(this)
            .setTitle("SKY · Crear un MP4 real")
            .setMessage("Video local H.264, vertical, 10 segundos, escenas con texto " +
                "animado y sin audio. No es video cinematográfico generado por IA.")
            .setView(editor)
            .setPositiveButton("Renderizar MP4") { _, _ ->
                val script = editor.text.toString().trim()
                if (script.length < 12) home.showMessage("Ingresá un guion de al menos 12 caracteres.")
                else generateCreativeVideo(script)
            }
            .setNegativeButton("Cancelar", null).show()
    }

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
                            generatedVideoToSave = file
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
                                .setNeutralButton("Guardar MP4") { _, _ ->
                                    val intent = android.content.Intent(
                                        android.content.Intent.ACTION_CREATE_DOCUMENT).apply {
                                        addCategory(android.content.Intent.CATEGORY_OPENABLE)
                                        type = "video/mp4"
                                        putExtra(android.content.Intent.EXTRA_TITLE,
                                            "SKY-Video-Animado.mp4")
                                    }
                                    runCatching { startActivityForResult(
                                        intent, generatedVideoSaveRequest) }
                                        .onFailure { home.showMessage(
                                            "No pude abrir el guardado del video.") }
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
        if (!tokens.cloudEnabled() && !tokens.groqEnabled()) {
            home.showMessage("Configurá Groq gratis o Gemini para crear contenido.")
            showSettings()
            return
        }
        socialPending = true
        voicePanel.showThinking()
        execute {
            try {
                val text = generateMobileText(SkySocialCommand.prompt(request))
                runOnUiThread {
                    if (!isFinishing) {
                        voicePanel.speakReply("Tengo una propuesta para " + request.platform +
                            ". Revisá y editá el borrador antes de compartirlo.")
                        socialStudio.showPreview(request, text)
                    }
                }
            } catch (_: Exception) {
                runOnUiThread {
                    home.showMessage("No pude generar el borrador. Revisá Groq/Gemini, " +
                        "tu conexión y volvé a intentarlo.")
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
    private fun processDailyCommand(message: String, spoken: Boolean): Boolean {
        val command = SkyDailyCommandParser.parse(message) ?: return false
        // Este punto recibe solamente texto escrito o transcripción de voz
        // iniciados por el propietario; jamás una respuesta del LLM.
        val origin = if (spoken) SkyActionTrustBoundary.Origin.OWNER_SPOKEN
            else SkyActionTrustBoundary.Origin.OWNER_TYPED
        dailyActions.run(command, origin)
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
        home.setConnection(tokens.token().isNotEmpty(), tokens.chatToken().isNotEmpty(),
            tokens.cloudEnabled() || tokens.groqEnabled())
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
        content.addView(SkyPremiumUi.section(this, "Motor",
            "SKY Automático · motor propio y respaldo supervisado", "⚡"))
        content.addView(description("SKY Android · Ajustes y permisos"))
        content.addView(description("MODO INDEPENDIENTE · No necesitás Windows ni una PC para " +
            "usar las funciones locales del teléfono. El cerebro Ollama del servidor es opcional."))
        content.addView(CheckBox(this).apply {
            text = "SKY Automático · priorizar nuestra API sin elegir modelos"
            isChecked = getSharedPreferences("sky_own_api", MODE_PRIVATE)
                .getBoolean("prefer_self_hosted_ollama",
                    tokens.deviceId().isNotBlank() &&
                        tokens.chatToken().isNotBlank() &&
                        tokens.server().isNotBlank())
            setOnCheckedChangeListener { _, enabled ->
                getSharedPreferences("sky_own_api", MODE_PRIVATE).edit()
                    .putBoolean("prefer_self_hosted_ollama", enabled).apply()
                home.showMessage(if (enabled)
                    "SKY Automático elegirá Ollama primero. Requiere chat HTTPS " +
                        "emparejado. No enviará datos a proveedores externos sin permiso."
                    else "Priorización automática desactivada. Se conservan las conexiones.")
            }
        })
        content.addView(actionButton("AJUSTE AVANZADO · FIJAR PROVEEDOR") {
            val names = arrayOf("SKY Automático (recomendado · modelo propio primero)",
                "Ollama (modelo propio · principal)",
                "Gemini (integración existente · cuotas externas)",
                "OpenRouter (modelos gratuitos limitados)",
                "Mistral (cuotas externas)",
                "Groq (cuotas externas)",
                "Cloudflare Workers AI (cuotas externas)")
            val prefs = getSharedPreferences("sky_own_api", MODE_PRIVATE)
            val selected = SkyOwnApiRoutingPolicy.chosenProvider(
                prefs.getString("sky_server_provider", "sky_auto"))
            val chosenIndex = SkyOwnApiRoutingPolicy.SERVER_PROVIDERS.indexOf(selected)
            AlertDialog.Builder(this)
                .setTitle("SKY API · Proveedor autorizado")
                .setMessage("Ollama trabaja en nuestro servidor. Los demás requieren " +
                    "claves en el servidor y consentimiento de nube y datos " +
                    "para cada consulta. No son ilimitados ni siempre gratuitos.")
                .setSingleChoiceItems(names, chosenIndex) { dialog, which ->
                    val provider = SkyOwnApiRoutingPolicy.SERVER_PROVIDERS[which]
                    prefs.edit().putString("sky_server_provider", provider)
                        .putBoolean("automatic_routing", provider == "sky_auto").apply()
                    home.showMessage("Modo de SKY API: $provider. " +
                        "Las autorizaciones externas se respetan.")
                    dialog.dismiss()
                }
                .setNegativeButton("Cancelar", null)
                .show()
        })
        content.addView(CheckBox(this).apply {
            text = "Autorizar respaldo automático de texto con IA externa"
            val prefs = getSharedPreferences("sky_own_api", MODE_PRIVATE)
            isChecked = prefs.getBoolean("automatic_external_backup", false)
            setOnCheckedChangeListener { _, enabled ->
                if (!enabled) {
                    prefs.edit().putBoolean("automatic_external_backup", false).apply()
                } else {
                    AlertDialog.Builder(this@MainActivity)
                        .setTitle("Autorización de proveedores externos")
                        .setMessage("Si Ollama no puede responder, SKY podrá enviar " +
                            "automáticamente el texto y contexto de tus consultas " +
                            "(incluidos datos privados) a los proveedores " +
                            "habilitados por el servidor. Esto consume sus cuotas y " +
                            "está sujeto a sus políticas de datos. " +
                            "Puedes revocar este permiso en cualquier momento. " +
                            "¿Autorizas el respaldo externo?")
                        .setPositiveButton("Sí, autorizo") { _, _ ->
                            prefs.edit().putBoolean("automatic_external_backup", true).apply()
                            home.showMessage("Respaldo externo autorizado. " +
                                "Ollama sigue siendo prioritario.")
                        }
                        .setNegativeButton("Solo modelo propio") { _, _ ->
                            isChecked = false
                        }
                        .setOnCancelListener { isChecked = false }
                        .show()
                }
            }
        })
        content.addView(description("La autorización externa es opcional; " +
            "viene desactivada. Ollama funciona sin ella. " +
            "Las solicitudes de información actual requieren fuentes verificadas."))
        content.addView(description("Sin claves externas en la APK: SKY usa el token " +
            "de chat limitado y HTTPS. Esta opción NO instala Ollama en el Samsung, " +
            "NO habilita modelos que no existan en el servidor y NO sustituye " +
            "investigación web verificada ni modos Gemini elegidos explícitamente."))
        content.addView(description(if (tokens.deviceId().isNotBlank() &&
                tokens.chatToken().isNotBlank() && tokens.server().isNotBlank())
            "SKY API: chat emparejado; disponibilidad del modelo sin comprobar."
            else "SKY API: todavía falta el enlace y autorización del chat privado."))
        content.addView(actionButton("CONFIGURAR / COMPROBAR SKY API") {
            val did = tokens.deviceId()
            val chatToken = tokens.chatToken()
            val endpoint = tokens.server()
            if (did.isBlank() || chatToken.isBlank() || endpoint.isBlank()) {
                showOptionalWindowsLink = true
                settingsDialog?.dismiss()
                showSettings()
                home.showMessage("Primero vinculá tu teléfono y autorizá el chat " +
                    "privado de SKY. Se requiere un servidor HTTPS real.")
            } else {
                execute {
                    try {
                        val result = SkyNetwork.requestChat(endpoint,
                            "/api/sky/mobile-chat/status", chatToken,
                            JSONObject().put("device_id", did))
                        val ollama = result.optBoolean("local_ollama_ready", false)
                        runOnUiThread {
                            if (!isFinishing) AlertDialog.Builder(this)
                                .setTitle("SKY API · Comprobación real")
                                .setMessage(if (ollama)
                                    "El servidor confirmó un modelo Ollama instalado " +
                                        "y accesible por loopback. Falta probar la " +
                                        "respuesta completa y su rendimiento."
                                    else "La API respondió, pero el modelo Ollama " +
                                        "configurado no está disponible. Revisá " +
                                        "Ollama y el modelo en el servidor.")
                                .setPositiveButton("Entendido", null)
                                .show()
                        }
                    } catch (error: Exception) {
                        runOnUiThread {
                            if (!isFinishing) AlertDialog.Builder(this)
                                .setTitle("SKY API no comprobada")
                                .setMessage(error.message?.take(300)
                                    ?: "No fue posible verificar el servidor.")
                                .setPositiveButton("Entendido", null).show()
                        }
                    }
                }
            }
        })
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
                                handler.postDelayed({ showHandsFreeFirstRun() }, 1200L)
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
        content.addView(description("GROQ GRATIS · MODO PRINCIPAL DE CONVERSACIÓN"))
        content.addView(description("GroqCloud ofrece modelos rápidos en un plan gratuito con límites. " +
            "Usaremos Groq para conversaciones normales si lo configurás. " +
            "Gemini quedará disponible para consultas web verificadas o como alternativa. " +
            "Tu clave permanece cifrada en este teléfono; nunca se sube a GitHub."))
        if (tokens.groqEnabled()) {
            content.addView(description("Groq está configurado y tiene prioridad en el chat normal."))
            content.addView(actionButton("Quitar clave de Groq") {
                tokens.clearGroqKey()
                refreshConnection()
                settingsDialog?.dismiss()
                showSettings()
            })
        } else {
            val groqInput = input("Pegá tu clave de GroqCloud", true)
            content.addView(groqInput)
            content.addView(actionButton("PEGAR CLAVE GROQ COPIADA") {
                val clipboard = getSystemService(CLIPBOARD_SERVICE) as?
                    android.content.ClipboardManager
                val clip = clipboard?.primaryClip
                val raw = if (clip != null && clip.itemCount > 0)
                    clip.getItemAt(0).coerceToText(this)?.toString().orEmpty() else ""
                val problem = SkyGroqCloud.keyProblem(raw)
                if (problem != null) {
                    AlertDialog.Builder(this).setTitle("Clave Groq no reconocida")
                        .setMessage(problem).setPositiveButton("Entendido", null).show()
                } else {
                    val value = SkyPhoneCloud.normalizePersonalKey(raw)
                    groqInput.setText(value)
                    groqInput.setSelection(value.length)
                    home.showMessage("Clave Groq copiada. Activala para verificar conexión.")
                }
            })
            val groqConsent = CheckBox(this).apply {
                text = "Autorizo enviar mis preguntas y el contexto reciente a Groq. " +
                    "Comprendo que el servicio tiene límites gratuitos y puedo quitar la clave."
            }
            content.addView(groqConsent)
            content.addView(actionButton("Crear o copiar clave gratuita de Groq") {
                startActivity(android.content.Intent(android.content.Intent.ACTION_VIEW,
                    android.net.Uri.parse("https://console.groq.com/keys")))
            })
            lateinit var groqButton: Button
            groqButton = actionButton("COMPROBAR Y ACTIVAR GROQ") {
                val raw = groqInput.text.toString()
                val key = SkyPhoneCloud.normalizePersonalKey(raw)
                val problem = SkyGroqCloud.keyProblem(raw)
                if (!groqConsent.isChecked) {
                    AlertDialog.Builder(this).setTitle("Autorización necesaria")
                        .setMessage("Autorizá el envío de mensajes a Groq antes de activarlo.")
                        .setPositiveButton("Entendido", null).show()
                } else if (problem != null) {
                    AlertDialog.Builder(this).setTitle("Clave de Groq")
                        .setMessage(problem)
                        .setPositiveButton("Entendido", null).show()
                } else {
                    groqButton.isEnabled = false
                    groqButton.text = "Comprobando Groq…"
                    execute {
                        try {
                            SkyGroqCloud.reply(key, "Responde solo: lista.", JSONArray())
                            runOnUiThread {
                                if (isFinishing) return@runOnUiThread
                                tokens.saveGroqKey(key)
                                groqInput.setText("")
                                refreshConnection()
                                settingsDialog?.dismiss()
                                handler.postDelayed({ showHandsFreeFirstRun() }, 1200L)
                                AlertDialog.Builder(this)
                                    .setTitle("Groq conectado")
                                    .setMessage("SKY puede conversar usando Groq. " +
                                        "Las consultas actuales necesitarán fuentes web verificadas.")
                                    .setPositiveButton("Conversar") { _, _ -> home.openChat() }
                                    .show()
                            }
                        } catch (error: Exception) {
                            runOnUiThread {
                                if (isFinishing) return@runOnUiThread
                                groqButton.isEnabled = true
                                groqButton.text = "COMPROBAR Y ACTIVAR GROQ"
                                AlertDialog.Builder(this)
                                    .setTitle("No se pudo activar Groq")
                                    .setMessage(error.message?.take(240)
                                        ?: "Revisá la clave o tu conexión a internet.")
                                    .setPositiveButton("Entendido", null).show()
                            }
                        }
                    }
                }
            }
            content.addView(groqButton)
        }
        content.addView(SkyPremiumUi.section(this, "Privacidad",
            "Permisos individuales · No compartas datos sin autorización", "◈"))
        content.addView(CheckBox(this).apply {
            text = "Autorizar nube para el próximo mensaje e historial"
            isChecked = home.cloudConsent.isChecked
            setOnCheckedChangeListener { _, enabled ->
                home.cloudConsent.isChecked = enabled
            }
        })
        content.addView(CheckBox(this).apply {
            text = "Incluir mis datos privados solo en la próxima consulta"
            isChecked = home.privateConsent.isChecked
            setOnCheckedChangeListener { _, enabled ->
                home.privateConsent.isChecked = enabled
            }
        })
        content.addView(description("Los permisos anteriores son de un solo uso: " +
            "SKY los desmarca después de cada consulta. " +
            "No permitás el envío si el contenido incluye secretos personales."))

        content.addView(SkyPremiumUi.section(this, "Acceso",
            "Control supervisado de aplicaciones y conexión opcional", "◉"))
        content.addView(description(
            "Una sola autorización local para abrir las aplicaciones actuales y futuras " +
            "cuando vos lo pidás. No autoriza automáticamente editar, borrar ni " +
            "ejecutar órdenes de SKY Windows."
        ))
        content.addView(actionButton(if (installedApps.supervisedControlEnabled())
            "● CONTROL SUPERVISADO ACTIVO · REVISAR / REVOCAR"
            else "ACEPTO · ACTIVAR CONTROL SUPERVISADO") {
            settingsDialog?.dismiss()
            installedApps.showControlAuthorization()
        })
        content.addView(actionButton("Ver mis aplicaciones instaladas") {
            settingsDialog?.dismiss()
            installedApps.showCatalog()
        })
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
            content.addView(description("Aplicaciones permitidas para órdenes remotas de Windows. " +
                "Requieren autorización individual adicional."))
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
            content.addView(description(
                "Para órdenes locales de apertura y preparación de mensajes, " +
                "usá el control supervisado de arriba. Los envíos y las acciones " +
                "delicadas siguen requiriendo confirmación."
            ))
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
        if (BuildConfig.ENABLE_TEXT_ASSIST) {
            // Only the separate, non-distributed experimental build exposes
            // sensitive AccessibilityService authorization.
            content.addView(actionButton("CONTROL MUSICAL ASISTIDO · AUTORIZACIÓN") {
                showMusicControlDisclosure(SkyMusicCommand.Request(
                    "november rain", musicLauncher.preferred()))
            })
            content.addView(actionButton("Desactivar control musical asistido") {
                getSharedPreferences("sky_music_access", MODE_PRIVATE)
                    .edit().putBoolean("consent", false).apply()
                requestedMusicAfterPermission = null
                SkyMusicControlService.cancelPending()
                home.showMessage("Control musical asistido desactivado. " +
                    "Podés apagar el servicio desde Accesibilidad de Android.")
            })
        } else {
            content.addView(description("La versión estándar usa controles multimedia " +
                "oficiales de Android. No solicita Accesibilidad ni puede tocar botones " +
                "dentro de otras apps. Algunas canciones necesitarán una acción " +
                "dentro del reproductor."))
        }
        content.addView(actionButton("VERIFICACIÓN MUSICAL · ESTADO Y PERMISOS") {
            if (!BuildConfig.ENABLE_TEXT_ASSIST) {
                AlertDialog.Builder(this)
                    .setTitle("SKY · Instalación estándar protegida")
                    .setMessage("Para evitar solicitar acceso amplio a las notificaciones, " +
                        "esta versión no incorpora ese servicio. SKY puede abrir el " +
                        "reproductor y solicitar la canción, pero no afirma " +
                        "reproducción comprobada sin evidencia. Se conservan las " +
                        "funciones de chat, voz, archivos y órdenes permitidas. " +
                        "La verificación mediante sesiones de otras aplicaciones " +
                        "solo existe en una variante experimental no distribuida.")
                    .setPositiveButton("Entendido", null).show()
                return@actionButton
            }
            val enabled = SkyPlaybackProof.available(this)
            if (enabled) {
                AlertDialog.Builder(this)
                    .setTitle("SKY · Verificación musical activa")
                    .setMessage("Android permite comprobar solamente el título y el " +
                        "estado de reproducción de YouTube, YouTube Music y Spotify. " +
                        "SKY no guarda notificaciones ni mensajes. Podés revocar el " +
                        "permiso desde Ajustes de Android.")
                    .setPositiveButton("Abrir ajustes del permiso") { _, _ ->
                        startActivity(android.content.Intent(
                            android.provider.Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
                    }
                    .setNegativeButton("Cerrar", null).show()
            } else {
                AlertDialog.Builder(this)
                    .setTitle("Verificación real de música · Permiso opcional")
                    .setMessage("Para saber si Spotify o YouTube realmente reproduce " +
                        "la canción pedida, Android exige autorización de acceso a " +
                        "notificaciones. El permiso del sistema es amplio: técnicamente " +
                        "podría permitir leer notificaciones de otras aplicaciones. " +
                        "SKY solo consulta sesiones multimedia autorizadas y no " +
                        "lee, almacena ni envía notificaciones.\n\n" +
                        "Activá únicamente «SKY · Verificar reproducción musical» " +
                        "si aceptás ese acceso. Se puede revocar cuando querás. " +
                        "Sin permiso, SKY seguirá enviando órdenes y declarará " +
                        "honestamente que no pudo verificar la reproducción.")
                    .setPositiveButton("Elegir en Ajustes de Android") { _, _ ->
                        runCatching {
                            startActivity(android.content.Intent(
                                android.provider.Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
                        }.onFailure {
                            home.showMessage("No pude abrir Ajustes de notificaciones.")
                        }
                    }
                    .setNegativeButton("No autorizar", null).show()
            }
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
        content.addView(SkyPremiumUi.section(this, "Creatividad",
            "Documentos, multimedia y herramientas sociales", "✦"))
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
        content.addView(actionButton("IMÁGENES IA · GENERAR CON GEMINI Y GUARDAR") {
            settingsDialog?.dismiss()
            startRealImageGeneration()
        })
        content.addView(actionButton("VIDEOS IA · GEMINI OMNI FLASH (API DE PAGO)") {
            settingsDialog?.dismiss()
            startPaidAiVideoCreation()
        })
        content.addView(actionButton("VIDEOS · RENDERIZAR MP4 LOCAL Y GUARDAR") {
            settingsDialog?.dismiss()
            startNativeVideoEditor()
        })
        content.addView(actionButton("ESTUDIO CREATIVO · MIS REDES SOCIALES") {
            settingsDialog?.dismiss()
            socialStudio.showCreatorMenu { request -> createSocialContent(request) }
        })
        content.addView(SkyPremiumUi.section(this, "Memoria",
            "Aprendizaje supervisado y recuerdos del teléfono", "◇"))
        content.addView(actionButton("Enseñar a SKY una respuesta corregida") {
            settingsDialog?.dismiss()
            showLearningDialog()
        })
        content.addView(CheckBox(this).apply {
            text = "NÚCLEO COGNITIVO ANDROID · respuestas guiadas y recuerdos locales"
            isChecked = cognitionEnabled()
            setOnCheckedChangeListener { _, enabled ->
                cognitionPrefs.edit().putBoolean("enabled", enabled).apply()
                home.showMessage(if (enabled) "Núcleo cognitivo activado en este teléfono."
                    else "Núcleo cognitivo desactivado. El chat y los controles siguen disponibles.")
            }
        })
        content.addView(actionButton("APRENDIZAJE COMPROBADO · RESULTADOS Y REINICIO") {
            val records = verifiedLearning.report()
            val evidence = records.joinToString("\n") { item ->
                val confidence = if (item.examples == 0) "sin pruebas" else
                    String.format(java.util.Locale.US, "%.0f%%", item.probability * 100.0)
                item.category + ": " + item.verified + " verificadas, " +
                    item.failures + " fallidas · indicador " + confidence
            }
            AlertDialog.Builder(this)
                .setTitle("SKY Android · Aprendizaje por resultados")
                .setMessage("Estos indicadores se ajustan solo ante acciones locales " +
                    "verificadas o fallidas. Una orden enviada no es un éxito. " +
                    "No es entrenamiento del modelo de lenguaje y nunca otorga permisos.\n\n" +
                    evidence)
                .setPositiveButton("Cerrar", null)
                .setNeutralButton("Reiniciar aprendizaje") { _, _ ->
                    AlertDialog.Builder(this)
                        .setTitle("Reiniciar indicadores aprendidos")
                        .setMessage("¿Borrar únicamente los pesos y contadores orientativos? " +
                            "No modifica historial, permisos ni recuerdos.")
                        .setPositiveButton("Reiniciar") { _, _ ->
                            verifiedLearning.clear()
                            home.showMessage("Indicadores de aprendizaje reiniciados.")
                        }
                        .setNegativeButton("Cancelar", null).show()
                }.show()
        })
        content.addView(actionButton("NÚCLEO COGNITIVO · FUNCIONES Y PRIVACIDAD") {
            AlertDialog.Builder(this).setTitle("SKY Android · Núcleo cognitivo")
                .setMessage(SkyAndroidCognition.description())
                .setPositiveButton("Entendido", null).show()
        })
        content.addView(SkyPremiumUi.section(this, "Herramientas",
            "Modos avanzados y archivos editables", "▣"))
        content.addView(actionButton("MODELOS GEMINI · RÁPIDO / EQUILIBRADO / PROFUNDO") {
            val options = arrayOf(
                "Económico · 3.5 Flash-Lite · consultas rápidas",
                "Equilibrado · 3.8 Flash · análisis",
                "Profundo · 3.1 Pro Preview · mayor uso de cuota"
            )
            val commands = arrayOf("Modo económico: ", "Modo flash: ", "Modo profundo: ")
            AlertDialog.Builder(this).setTitle("Elegí el modelo de ESTA consulta")
                .setMessage("El modo se elige por mensaje. No modifica el modelo por defecto, " +
                    "ni autoriza cargos o envíos privados automáticamente. " +
                    "El acceso depende de tu clave y cuota Gemini.")
                .setItems(options) { _, index ->
                    val current = SkyGeminiModes.select(chatInput.text.toString()).prompt
                    chatInput.setText(commands[index] + current.take(15500))
                    chatInput.setSelection(chatInput.text.length)
                    settingsDialog?.dismiss()
                    home.openChat()
                }
                .setNegativeButton("Cancelar", null).show()
        })
        content.addView(actionButton("HABILIDADES IA · INVESTIGAR / PROGRAMAR / DISEÑAR / PRESENTAR") {
            settingsDialog?.dismiss()
            showSkillsCatalog()
        })
        content.addView(actionButton("MI PERFIL PERSONAL · EDITAR / IMPORTAR DE WINDOWS") {
            settingsDialog?.dismiss()
            showOwnerProfile()
        })
        content.addView(actionButton("CREAR · EXCEL / WORD / PPTX / SVG / MD / HTML") {
            settingsDialog?.dismiss()
            exportLatestResponse()
        })
        content.addView(actionButton("RESUMEN DE EJECUCIÓN · RESULTADOS COMPROBADOS") {
            val measure = actionEvidence.summary()
            AlertDialog.Builder(this)
                .setTitle("SKY · Control de calidad real")
                .setMessage(
                    "Registros locales: " + measure.total +
                    "\nAcciones verificadas: " + measure.verified +
                    "\nÓrdenes enviadas sin comprobar: " + measure.sentUnverified +
                    "\nFallos: " + measure.failed +
                    "\nRechazos: " + measure.rejected +
                    "\nRespuestas remotas recibidas: " + measure.remoteResponse +
                    "\nEstados no identificados: " + measure.unknown +
                    "\n\nSolo se declara éxito cuando SKY comprueba un efecto " +
                    "observable, como un cambio de volumen o una nota guardada y releída. " +
                    "Abrir otra app o enviar teclas multimedia NO demuestra que la tarea terminó." +
                    "\n\nLos conteos son locales a este teléfono. No equivalen a métricas " +
                    "de servidores ni a resultados en otras aplicaciones."
                )
                .setPositiveButton("Cerrar", null)
                .show()
        })
        content.addView(actionButton("EVIDENCIAS · ÓRDENES Y RESULTADOS REALES") {
            val entries = actionEvidence.recent(40)
            if (entries.isEmpty()) {
                AlertDialog.Builder(this).setTitle("SKY · Ejecución verificable")
                    .setMessage("Todavía no hay acciones registradas en este teléfono.")
                    .setPositiveButton("Cerrar", null).show()
            } else {
                val labels = entries.map { it.status + " · " + it.action }.toTypedArray()
                AlertDialog.Builder(this).setTitle("SKY · Evidencias locales")
                    .setMessage("ENVIADA_SIN_VERIFICAR significa que Android recibió la orden, " +
                        "no que la tarea se completó. VERIFICADA_LOCAL solo registra cambios " +
                        "comprobados dentro del almacenamiento de SKY.")
                    .setItems(labels) { _, index ->
                        val receipt = entries[index]
                        AlertDialog.Builder(this).setTitle(receipt.status)
                            .setMessage(receipt.action + "\n\n" + receipt.detail +
                                "\n\nFecha: " + java.text.SimpleDateFormat(
                                    "dd/MM/yyyy HH:mm", java.util.Locale("es","NI"))
                                    .format(java.util.Date(receipt.createdAt)))
                            .setPositiveButton("Cerrar", null).show()
                    }
                    .setNeutralButton("Borrar evidencias") { _, _ ->
                        AlertDialog.Builder(this).setTitle("Eliminar evidencias locales")
                            .setMessage("Borrar este registro no revierte las acciones realizadas.")
                            .setPositiveButton("Eliminar") { _, _ ->
                                actionEvidence.deleteAll()
                                home.showMessage("Se borraron las evidencias locales.")
                            }
                            .setNegativeButton("Cancelar", null).show()
                    }
                    .setNegativeButton("Cerrar", null).show()
            }
        })
        content.addView(SkyPremiumUi.section(this, "Historial",
            "Buscar, filtrar, renombrar, guardar y exportar", "◷"))
        content.addView(actionButton("HISTORIAL · BUSCAR Y EXPORTAR CONSULTAS") {
            settingsDialog?.dismiss()
            showHistoryBrowser()
        })
        content.addView(actionButton("FUENTES APRENDIDAS · VER Y BORRAR REFERENCIAS") {
            val entries = knowledgeSources.recent(15)
            if (entries.isEmpty()) {
                AlertDialog.Builder(this)
                    .setTitle("SKY · Fuentes de investigación")
                    .setMessage("Todavía no hay referencias web guardadas en este teléfono. " +
                        "Se agregan únicamente enlaces que devuelva una búsqueda con fuentes.")
                    .setPositiveButton("Cerrar", null).show()
            } else {
                val labels = entries.map { it.localDate() + " · " + it.title.take(65) }.toTypedArray()
                AlertDialog.Builder(this)
                    .setTitle("Fuentes consultadas · solo metadatos")
                    .setItems(labels) { _, index ->
                        val entry = entries[index]
                        AlertDialog.Builder(this)
                            .setTitle(entry.title)
                            .setMessage(entry.url + "\n\nGuardada: " + entry.localDate() +
                                "\nEsto NO confirma el contenido completo del sitio.")
                            .setPositiveButton("Entendido", null).show()
                    }
                    .setNeutralButton("Borrar fuentes") { _, _ ->
                        AlertDialog.Builder(this)
                            .setTitle("Eliminar solo referencias web")
                            .setMessage("Se borrarán los enlaces guardados en este teléfono. " +
                                "No se eliminarán tu historial ni tus recuerdos personales.")
                            .setPositiveButton("Eliminar") { _, _ ->
                                knowledgeSources.clearAll()
                                home.showMessage("Se borraron las referencias web locales.")
                            }
                            .setNegativeButton("Cancelar", null).show()
                    }
                    .setNegativeButton("Cerrar", null).show()
            }
        })
        content.addView(SkyPremiumUi.section(this, "Diagnóstico",
            "Comprobaciones reales, errores y aplicaciones disponibles", "◌"))
        content.addView(actionButton("DIAGNÓSTICO REAL · PROBAR GEMINI EN ESTE TELÉFONO") {
            settingsDialog?.dismiss()
            testGeminiModelsOnDevice()
        })
        content.addView(actionButton("APRENDIZAJE REAL · MIS RESPUESTAS CORREGIDAS") {
            settingsDialog?.dismiss()
            showLearnedResponses()
        })
        content.addView(actionButton("MI MEMORIA · REVISAR Y BORRAR UN DATO") {
            settingsDialog?.dismiss()
            reviewMemoryLines()
        })
        content.addView(actionButton("HISTORIAL · BORRAR CONSULTAS DEL TELÉFONO") {
            AlertDialog.Builder(this)
                .setTitle("Borrar historial local")
                .setMessage("Se eliminarán todas las consultas guardadas en Android. " +
                    "No afecta el historial de SKY Windows ni tu perfil personal.")
                .setPositiveButton("Borrar") { _, _ ->
                    home.clearHistory()
                    while (chatHistory.length() > 0) chatHistory.remove(0)
                    home.showMessage("Historial local borrado.")
                }
                .setNegativeButton("Cancelar", null)
                .show()
        })
        content.addView(actionButton("Mis aplicaciones instaladas") {
            settingsDialog?.dismiss()
            installedApps.showCatalog()
        })
        content.addView(actionButton("SEGURIDAD · FIRMA Y PROTECCIONES") {
            AlertDialog.Builder(this)
                .setTitle("SKY IA · Seguridad de esta instalación")
                .setMessage(SkyAndroidSecurityReport.status(this))
                .setPositiveButton("Cerrar", null)
                .show()
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
        content.addView(SkyPremiumUi.section(this, "Voz",
            "Manos libres, conversación fluida y lectura natural", "♫"))
        content.addView(CheckBox(this).apply {
            text = "Escucha sin tocar: decí SKY (micrófono local autorizado y notificación)"
            isChecked = handsFreePrefs.getBoolean("hands_free_opt_in", false)
            setOnCheckedChangeListener { _, enabled -> setHandsFreeEnabled(enabled) }
        })
        content.addView(CheckBox(this).apply {
            text = "Escuchar automáticamente al abrir SKY (conversación en pantalla)"
            isChecked = getSharedPreferences("sky_voice_settings", MODE_PRIVATE)
                .getBoolean("fluid_opt_in", false)
            setOnCheckedChangeListener { _, enabled ->
                getSharedPreferences("sky_voice_settings", MODE_PRIVATE)
                    .edit().putBoolean("fluid_opt_in", enabled).apply()
                voicePanel.setConversationMode(enabled)
                home.showMessage(if (enabled)
                    "Escucha automática activada mientras SKY esté visible y Android lo permita."
                    else "Escucha automática desactivada.")
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
        content.addView(description("PRESENCIA CONTROLADA · La voz de SKY permanece disponible " +
            "mientras Android mantenga vivo el servicio autorizado. " +
            "Dormir impide ejecutar órdenes hasta escuchar la frase exacta SKY despierta."))
        content.addView(actionButton("DORMIR · Solo despertar con mi orden") {
            processPresenceCommand("SKY duerme")
            updatePresenceVisual()
        })
        content.addView(actionButton("ESTAR ATENTA · Escuchar mis orientaciones") {
            processPresenceCommand("SKY estate pendiente de mis orientaciones")
            updatePresenceVisual()
        })
        content.addView(actionButton("DESPERTAR · Volver a escuchar") {
            processPresenceCommand("SKY despierta")
            updatePresenceVisual()
        })
        content.addView(description("IDENTIDAD DEL CREADOR · Sin verificación biométrica de " +
            "voz habilitada. El reconocimiento de palabras NO reconoce a su dueño. " +
            "Mientras se incorpora un verificador de hablante local confiable, " +
            "las acciones fuera de pantalla requieren una segunda confirmación " +
            "SKY confirmo y las sensibles mantienen los controles de Android."))
        content.addView(description("Android 16 puede detener la captura en segundo plano. " +
            "SKY usa reconocimiento local y una notificación permanente; " +
            "no puede garantizar escuchar siempre con el teléfono bloqueado. " +
            "Podés apagar el micrófono desde la notificación cuando querás."))
        val premium = SkyPremiumUi.settingsShell(this, content) {
            settingsDialog?.dismiss()
        }
        settingsDialog = AlertDialog.Builder(this)
            .setView(premium)
            .create()
        settingsDialog?.let { SkyPremiumUi.showDialog(this, it, 0.92) }
    }

    private fun showMusicControlDisclosure(request: SkyMusicCommand.Request) {
        if (!BuildConfig.ENABLE_TEXT_ASSIST) {
            musicLauncher.playViaAndroidIntent(request)
            return
        }
        requestedMusicAfterPermission = request
        val provider = SkyMusicCommand.label(request.service ?: musicLauncher.preferred())
        AlertDialog.Builder(this)
            .setTitle("SKY · Reproducción musical sin tocar")
            .setMessage(
                "Querés escuchar «${request.query}» en $provider. Para buscar el título " +
                "y seleccionar la canción sin tocar botones, SKY necesita el servicio opcional " +
                "«SKY · Control musical asistido» en Accesibilidad de Android.\n\n" +
                "Si lo autorizás, SKY verá temporalmente los nombres de botones y canciones " +
                "que aparecen en YouTube Music, YouTube y Spotify, y podrá tocar el resultado " +
                "que coincida con tu orden. No lee mensajes, no opera otras aplicaciones, " +
                "no recopila pantallas ni envía datos de estas aplicaciones a servidores. " +
                "La orden caduca automáticamente tras 35 segundos. Podés desactivar " +
                "el permiso cuando querás. Android puede solicitar desbloqueo."
            )
            .setPositiveButton("Autorizar control musical") { _, _ ->
                getSharedPreferences("sky_music_access", MODE_PRIVATE)
                    .edit().putBoolean("consent", true).apply()
                startActivity(android.content.Intent(
                    android.provider.Settings.ACTION_ACCESSIBILITY_SETTINGS))
                home.showMessage("En Accesibilidad, activá «SKY · Control musical asistido» " +
                    "y regresá a SKY. La canción se buscará al volver.")
            }
            .setNeutralButton("Probar reproducción estándar") { _, _ ->
                requestedMusicAfterPermission = null
                musicLauncher.playViaAndroidIntent(request)
            }
            .setNegativeButton("Cancelar") { _, _ ->
                requestedMusicAfterPermission = null
                home.showMessage("Cancelé la reproducción. No activé el control musical.")
            }
            .show()
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

    private fun processPresenceCommand(message: String): Boolean {
        if (SkyVoicePresence.request(message) == SkyVoicePresence.Request.NONE) return false
        if (!SkyHandsFreeService.ownerPresenceCommand(message)) {
            home.showMessage("Activá manos libres en Voz para que SKY pueda permanecer atenta " +
                "a la palabra de activación. El micrófono requiere tu permiso.")
            return true
        }
        // The service gives the audible confirmation and persists the requested mode.
        return true
    }

    private fun updatePresenceVisual() {
        if (!::voicePanel.isInitialized || !handsFreePrefs.getBoolean("hands_free_opt_in", false))
            return
        val label = when (handsFreePrefs.getString("sky_presence_mode", "WAKE_ONLY")) {
            "SLEEP_LOCKED" -> "SKY dormida por orden · decí SKY despierta"
            "ATTENTIVE" -> "SKY atenta a tus orientaciones"
            else -> "SKY en espera · decí SKY"
        }
        voicePanel.showHandsFreeState(label)
    }

    private fun showHandsFreeFirstRun() {
        // Surface the revised no-touch choice once to installations that
        // dismissed the previous dialog; never silently enable the microphone.
        if (handsFreePrefs.getBoolean("hands_free_prompt_shown_v0842", false) ||
            handsFreePrefs.getBoolean("hands_free_opt_in", false) ||
            !visible || isFinishing || settingsDialog?.isShowing == true) return
        handsFreePrefs.edit().putBoolean("hands_free_prompt_shown_v0842", true).apply()
        AlertDialog.Builder(this)
            .setTitle("SKY · Activación por voz")
            .setMessage("¿Querés activar SKY manos libres? Escuchará la palabra «SKY» " +
                "con reconocimiento local disponible, mostrará una notificación " +
                "permanente y se dormirá entre órdenes. El micrófono consume batería " +
                "y Android 16 puede limitarlo cuando el teléfono está bloqueado. " +
                "No reconoce de forma biométrica quién está hablando: responde a " +
                "las palabras que escucha. Podés apagarlo desde la notificación " +
                "o Ajustes de SKY.")
            .setPositiveButton("Activar manos libres") { _, _ -> setHandsFreeEnabled(true) }
            .setNegativeButton("Ahora no") { _, _ ->
                home.showMessage("Manos libres desactivadas. Podés activarlas desde Ajustes → Voz.")
            }
            .show()
    }

    private fun startHandsFree() {
        if (SkyHandsFreeService.health().active) {
            home.setHandsFreeActive(true)
            updatePresenceVisual()
            return
        }
        if (android.os.Build.VERSION.SDK_INT < 31 ||
            !android.speech.SpeechRecognizer.isOnDeviceRecognitionAvailable(this)) {
            handsFreePrefs.edit().putBoolean("hands_free_opt_in", false).apply()
            home.setHandsFreeActive(false)
            voicePanel.showError("El reconocimiento local continuo no está disponible. " +
                "Podés tocar los ojos para un turno de voz mientras la app está abierta.")
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
        if (openIntent?.getBooleanExtra(SkyInstagramAlerts.EXTRA_READ, false) == true) {
            openIntent.removeExtra(SkyInstagramAlerts.EXTRA_READ)
            readInstagramNow()
        }
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
        if (SkyMusicControlService.enabled()) {
            val request = requestedMusicAfterPermission
            if (request != null && ::musicLauncher.isInitialized) {
                requestedMusicAfterPermission = null
                handler.postDelayed({ if (!isFinishing) musicLauncher.play(request) }, 450L)
            }
        }
        if (::voicePanel.isInitialized) {
            voicePanel.onEnterForeground()
            voicePanel.setConversationMode(getSharedPreferences(
                "sky_voice_settings", MODE_PRIVATE).getBoolean("fluid_opt_in", false))
        }
        SkyHandsFreeService.onInstagramNotice = { count ->
            if (visible) instagramNotice(count)
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
        updatePresenceVisual()
        handler.postDelayed({ showHandsFreeFirstRun() }, 1100L)
        companionController.onResume()
        handler.post(pollLoop)
        handler.post(instagramPoll)
        if (SkyInstagramAlerts.paired(this) && SkyInstagramAlerts.enabled(this) &&
            android.os.Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) !=
                android.content.pm.PackageManager.PERMISSION_GRANTED &&
            !handsFreePrefs.getBoolean("instagram_notification_permission_asked", false)) {
            handsFreePrefs.edit().putBoolean("instagram_notification_permission_asked", true).apply()
            requestPermissions(arrayOf(android.Manifest.permission.POST_NOTIFICATIONS), 1625)
        }
    }
    override fun onPause() {
        SkyHandsFreeService.onPhrase = null
        SkyHandsFreeService.onInstagramNotice = null
        SkyHandsFreeService.onWake = null
        SkyHandsFreeService.onStatus = null
        SkyHandsFreeService.onStopped = null
        visible = false
        if (::companionController.isInitialized) companionController.onPause()
        if (::voicePanel.isInitialized) voicePanel.onPausePanel()
        handler.removeCallbacks(pollLoop)
        handler.removeCallbacks(instagramPoll)
        super.onPause()
    }
    override fun onDestroy() {
        if (::musicLauncher.isInitialized) musicLauncher.close()
        handler.removeCallbacks(instagramPoll)
        handler.removeCallbacks(pollLoop)
        if (::voicePanel.isInitialized) voicePanel.close()
        if (::companionController.isInitialized) companionController.close()
        executor.shutdown()
        chatExecutor.shutdown()
        pollingExecutor.shutdown()
        if (::actionEvidence.isInitialized) actionEvidence.close()
        if (::adaptiveMemory.isInitialized) adaptiveMemory.close()
        if (::longTermMemory.isInitialized) longTermMemory.close()
        if (::archive.isInitialized) archive.close()
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
        if (tokens.groqEnabled() || tokens.cloudEnabled()) {
            setStatus("SKY Android independiente · " +
                (if (tokens.groqEnabled()) "Groq activo" else "Gemini activo") +
                ". Windows no es necesario.")
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

    private fun askNewChat() {
        if (chatPending || pendingFileCancel != null) {
            home.showMessage("SKY sigue procesando una consulta. Terminá o cancelá esa operación antes de abrir otro chat.")
            return
        }
        if (chatInput.text.isNotBlank() || selectedAttachments.isNotEmpty()) {
            AlertDialog.Builder(this)
                .setTitle("SKY · Nueva conversación")
                .setMessage("Se limpiarán la pantalla y el borrador actual. Las conversaciones guardadas en Historial no se eliminarán. ¿Continuar?")
                .setPositiveButton("Nuevo chat") { _, _ -> startNewChat() }
                .setNegativeButton("Conservar borrador", null)
                .show()
        } else startNewChat()
    }

    private fun startNewChat() {
        if (chatPending || pendingFileCancel != null) return
        // Only the private current-session boundary is updated; never delete
        // any saved conversations or overwrite the user's archival records.
        val newestSavedId = SkyChatSessionPolicy.newBoundary(archive.recent(1).lastOrNull()?.id)
        getSharedPreferences("sky_chat_session", MODE_PRIVATE).edit()
            .putLong("after_id", newestSavedId).apply()
        while (chatHistory.length() > 0) chatHistory.remove(0)
        selectedAttachments.clear()
        refreshSelectedAttachments()
        voiceReplyOnFace = false
        home.startNewChat(newestSavedId)
    }

    private fun sendChat() {
        val selected = selectedAttachments.toList()
        val query = chatInput.text.toString().trim()
        if (selected.isEmpty()) {
            sendChatText(query)
            return
        }
        if (chatPending) return
        if (!tokens.cloudEnabled()) {
            home.showMessage("Configurá Gemini en Ajustes para analizar varios archivos de hasta 100 MB.")
            return
        }
        // No adivinar la tarea: cada archivo debe procesarse para un objetivo indicado
        // por el usuario. La vista previa sigue siendo local y no envía datos.
        if (query.isBlank()) {
            home.showMessage("¿Qué querés que haga con estos archivos? " +
                "Escribí una instrucción antes de autorizar el análisis.")
            showSelectedAttachmentPreview(selected.last())
            return
        }
        val instruction = query
        val names = selected.joinToString("\n") {
            "• " + it.name.take(65) + " (" + it.sizeMb() + " MB)"
        }
        AlertDialog.Builder(this)
            .setTitle("Enviar " + selected.size + " archivo(s) a Gemini")
            .setMessage(names + "\n\nSky cargará los archivos compatibles a Gemini " +
                "solo después de esta autorización. La API puede conservarlos hasta " +
                "48 horas; SKY solicitará borrarlos al terminar, incluso si falla el análisis. " +
                "No hay garantía de borrado inmediato si se corta la conexión. " +
                "Máximo 100 MB por archivo, 300 MB combinados; PDF hasta 50 MB. " +
                "No enviés contraseñas ni documentos privados sin revisarlos primero.")
            .setPositiveButton("Autorizar una vez") { _, _ ->
                selectedAttachments.clear()
                refreshSelectedAttachments()
                sendAttachmentBatch(instruction, selected)
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    private fun sendAttachmentBatch(instruction: String, selected: List<SkyAttachmentBatch.Item>) {
        if (chatPending) return
        chatPending = true
        val cancel = SkyGeminiFiles.CancelToken()
        pendingFileCancel = cancel
        val label = selected.joinToString(", ") { it.name.take(45) }
        val question = (instruction + "\n[Archivos: " + label + "]").take(3900)
        home.beginSending(question)
        home.showUploadProgress("Preparando " + selected.size + " archivo(s)...")
        voicePanel.showThinking()
        chatExecutor.execute {
            try {
                val answer = SkyGeminiFiles.analyze(this, tokens.personalCloudKey(),
                    selected, instruction, cancel) { progress ->
                    runOnUiThread { if (pendingFileCancel === cancel)
                        home.showUploadProgress(progress) }
                }
                runOnUiThread {
                    home.addExchange(question, answer, "Gemini · análisis de archivos")
                    voicePanel.express(answer)
                    voicePanel.speakReply(answer)
                }
            } catch (error: Exception) {
                runOnUiThread {
                    if (selectedAttachments.isEmpty()) {
                        selectedAttachments.addAll(selected)
                        refreshSelectedAttachments()
                    }
                    val reason = if (error is java.util.concurrent.CancellationException)
                        "Cancelaste el envío. Podés editar o quitar los archivos y reintentar."
                    else error.message ?: "No pude analizar los archivos."
                    home.failSending(reason, instruction)
                    if (error !is java.util.concurrent.CancellationException)
                        voicePanel.showError("Falló la lectura o el análisis de los adjuntos.")
                }
            } finally {
                chatPending = false
                pendingFileCancel = null
                runOnUiThread { home.showUploadProgress(null) }
            }
        }
    }

    private fun sendVisualAttachment(instruction: String, attachment: SkyAttachmentReader.Attachment) {
        val jpeg = attachment.jpeg ?: return
        if (chatPending) return
        chatPending = true
        val question = instruction + " [Adjunto: " + attachment.filename + "]"
        home.beginSending(question)
        voicePanel.showThinking()
        chatExecutor.execute {
            try {
                val answer = SkyPhoneCloud.analyzeVisualAttachment(
                    tokens.personalCloudKey(), jpeg, attachment.filename, instruction)
                runOnUiThread {
                    home.addExchange(question, answer, "Gemini · archivo visual")
                    voicePanel.express(answer)
                    voicePanel.speakReply(answer)
                }
            } catch (error: Exception) {
                runOnUiThread {
                    home.failSending(error.message ?: "No pude analizar este archivo.", instruction)
                    voicePanel.showError("Falló el análisis del archivo.")
                }
            } finally {
                chatPending = false
            }
        }
    }

    private fun sendMediaAttachment(instruction: String, attachment: SkyAttachmentReader.Attachment) {
        val data = attachment.media ?: return
        if (chatPending) return
        chatPending = true
        val question = instruction + " [Adjunto: " + attachment.filename + "]"
        home.beginSending(question)
        voicePanel.showThinking()
        chatExecutor.execute {
            try {
                val answer = SkyPhoneCloud.analyzeMediaAttachment(
                    tokens.personalCloudKey(), data, attachment.mime, attachment.filename, instruction)
                runOnUiThread {
                    home.addExchange(question, answer, "Gemini · archivo multimedia")
                    voicePanel.express(answer)
                    voicePanel.speakReply(answer)
                }
            } catch (error: Exception) {
                runOnUiThread {
                    home.failSending(error.message ?: "No pude analizar el archivo.", instruction)
                    voicePanel.showError("No pude procesar el archivo multimedia.")
                }
            } finally {
                chatPending = false
            }
        }
    }

    private fun requestLiveWeather(question: String, city: String) {
        if (chatPending) return
        chatPending = true
        home.beginSending(question)
        voicePanel.showThinking()
        chatExecutor.execute {
            try {
                val live = SkyWeatherNow.current(city)
                runOnUiThread {
                    home.addExchange(question, live.text, "Open-Meteo · clima actual",
                        sources = listOf(SkyPhoneCloud.Source("Open-Meteo · datos actuales", live.sourceUrl)))
                    voicePanel.speakReply(live.text)
                }
            } catch (error: Exception) {
                runOnUiThread {
                    home.failSending(error.message ?: "El clima no está disponible.", question)
                    voicePanel.showError("No pude verificar el clima en internet.")
                }
            } finally {
                chatPending = false
            }
        }
    }

    /** Google News publishes syndicated headlines, not fact-check certification. */
    private fun requestNewsHeadlines(question: String) {
        if (chatPending) {
            home.showMessage("Voy a terminar primero la consulta anterior.")
            return
        }
        chatPending = true
        home.beginSending(question)
        voicePanel.showThinking()
        chatExecutor.execute {
            try {
                val news = SkyPublicNews.fetch(question)
                runOnUiThread {
                    if (isFinishing) return@runOnUiThread
                    home.addExchange(question, news.answer,
                        "Google Noticias · titulares recibidos", sources = news.sources)
                    voicePanel.speakReply(news.answer)
                }
            } catch (error: Exception) {
                runOnUiThread {
                    if (isFinishing) return@runOnUiThread
                    home.failSending("Google Noticias no entregó titulares verificables: " +
                        (error.message ?: "fuente temporalmente no disponible"), question)
                }
            } finally { chatPending = false }
        }
    }

    /** Real scholarly source from Windows research parity; no fake bibliography. */
    private fun requestAcademicResearch(question: String) {
        if (chatPending) {
            home.showMessage("Estoy terminando otra consulta. Volvé a pedírmelo después.")
            return
        }
        chatPending = true
        home.beginSending(question)
        voicePanel.showThinking()
        chatExecutor.execute {
            try {
                val papers = SkyAcademicResearch.search(question)
                runOnUiThread {
                    if (isFinishing) return@runOnUiThread
                    home.addExchange(question, papers.summary,
                        "Semantic Scholar · publicaciones verificables",
                        sources = papers.sources)
                    voicePanel.speakReply(papers.summary)
                }
            } catch (error: Exception) {
                runOnUiThread {
                    if (isFinishing) return@runOnUiThread
                    home.failSending("Consulta académica: " +
                        (error.message ?: "fuente académica no disponible") +
                        ". No inventé bibliografía.", question)
                }
            } finally {
                chatPending = false
            }
        }
    }

    /** Exact algebraic roots, including complex roots; never inferred from an LLM. */
    private fun processQuadraticCalculation(message: String): Boolean {
        val result = SkyQuadraticSolver.solve(message) ?: return false
        val keepFace = voiceReplyOnFace
        voiceReplyOnFace = false
        home.addExchange(message, result.answer,
            "SKY · álgebra verificable", revealPanel = !keepFace)
        if (voicePanel.isVoiceEnabled()) voicePanel.speakReply(result.answer)
        return true
    }

    /** Deterministic statistics run locally on supplied numbers, without cloud access. */
    private fun processStatisticsCalculation(message: String): Boolean {
        val result = SkyStatisticsCalculator.solve(message) ?: return false
        val keepFace = voiceReplyOnFace
        voiceReplyOnFace = false
        home.addExchange(message, result.answer,
            "SKY · estadística local · " + result.title, revealPanel = !keepFace)
        if (voicePanel.isVoiceEnabled()) voicePanel.speakReply(result.answer)
        return true
    }

    /** Verified local calculations never ask an LLM to invent numeric output. */
    private fun processScientificCalculation(message: String): Boolean {
        val result = SkyScientificCalculator.solve(message) ?: return false
        val keepFace = voiceReplyOnFace
        voiceReplyOnFace = false
        home.addExchange(message, result.answer,
            "SKY · calculadora científica · " + result.title,
            revealPanel = !keepFace)
        if (voicePanel.isVoiceEnabled()) voicePanel.speakReply(result.answer)
        return true
    }

    /** Android file selector requires a user action and reveals no hidden files. */
    private fun processOwnerProfileImport(message: String): Boolean {
        if (!SkyOwnerProfileIntent.requestsImport(message)) return false
        home.showMessage("Elegí tu archivo personal. Lo revisaré y solo lo guardaré " +
            "si confirmás la importación; la copia interna quedará cifrada.")
        chooseOwnerProfileImport()
        return true
    }

    /** Single-turn owner identity from local data only; never GitHub or third parties. */
    private fun processOwnerQuestion(message: String): Boolean {
        if (!SkyOwnerIdentity.isQuestion(message)) return false
        val reply = SkyOwnerIdentity.summarize(SkyOwnerContext.read(this))
        if (::home.isInitialized) {
            val face = voiceReplyOnFace
            voiceReplyOnFace = false
            home.addExchange(message, reply, "SKY · identidad privada del teléfono",
                revealPanel = !face)
        }
        if (::voicePanel.isInitialized && voicePanel.isVoiceEnabled())
            voicePanel.speakReply(reply)
        return true
    }

    /** Real public source inside SKY, not an invented search or browser redirect. */
    private fun requestPublicResearch(question: String) {
        if (chatPending) {
            home.showMessage("Termino la consulta anterior antes de investigar otra.")
            return
        }
        chatPending = true
        home.beginSending(question)
        voicePanel.showThinking()
        chatExecutor.execute {
            try {
                val result = SkyPublicResearch.find(question)
                runOnUiThread {
                    if (isFinishing) return@runOnUiThread
                    home.addExchange(question, result.answer, "Wikipedia · fuente consultada",
                        sources = listOf(SkyPhoneCloud.Source(result.sourceTitle,
                            result.sourceUrl)))
                    voicePanel.speakReply(result.answer)
                }
            } catch (error: Exception) {
                val fallback = if (tokens.groqEnabled() &&
                    !SkyPhoneCloud.requiresLiveVerification(question)) {
                    runCatching { SkyGroqCloud.reply(tokens.groqKey(),
                        question, JSONArray()) }.getOrNull()
                } else null
                runOnUiThread {
                    if (isFinishing) return@runOnUiThread
                    if (!fallback.isNullOrBlank()) {
                        val reply = fallback + "\n\nRespuesta general de Groq, sin verificación web."
                        home.addExchange(question, reply, "Groq · respuesta de respaldo")
                        voicePanel.speakReply(reply)
                    } else {
                        val reason = error.message ?: "La fuente no respondió."
                        home.failSending("Wikipedia: " + reason +
                            " Podés probar con un tema más específico o activar Gemini " +
                            "para búsquedas actuales con fuentes.", question)
                    }
                }
            } finally {
                chatPending = false
            }
        }
    }

    private fun localCognitionRecall(message: String): Boolean {
        if (!cognitionEnabled()) return false
        val answer = when {
            SkyAndroidCognition.memoryQuestion(message) -> {
                SkyAndroidCognition.localMemoryAnswer(message,
                    (longTermMemory.relevant(message, 8).map { "- " + it.text } +
                        SkyOwnerContext.memoryLines(this)).distinct().take(20))
            }
            SkyAndroidCognition.historyQuestion(message) -> {
                val terms = SkyAndroidCognition.searchTerms(message)
                val found = if (terms.isEmpty()) emptyList() else archive.page(terms.first(), limit = 4)
                SkyAndroidCognition.localHistoryAnswer(found.map {
                    it.localTime() + " · " + it.title + " · " + it.answer.take(85)
                }, terms.isNotEmpty())
            }
            else -> return false
        }
        chatInput.setText("")
        val keepFace = voiceReplyOnFace
        voiceReplyOnFace = false
        home.addExchange(message, answer, "SKY · memoria privada local",
            revealPanel = !keepFace)
        voicePanel.speakReply(answer)
        return true
    }

    private fun previewSafeFileProposal(message: String): Boolean {
        val proposal = SkySafeFileConversation.prepare(message) ?: return false
        val operationId = java.util.UUID.randomUUID().toString()
        val description = "Operación: " + proposal.operation + "\\nArchivo: " +
            proposal.filename + "\\n\\nDetalle propuesto:\\n" +
            proposal.detail.take(1100) +
            "\\n\\nSolo se preparó una vista previa. No se ha modificado ningún archivo."
        val evidence = SkyActionEvidence(this)
        runCatching { evidence.record("archivo_" + proposal.operation, "PREPARADA",
            "Vista previa local; sin ejecución", operationId) }
        android.app.AlertDialog.Builder(this)
            .setTitle("SKY · Vista previa segura")
            .setMessage(description.replace("\\n", "\n"))
            .setNegativeButton("Cancelar") { _, _ ->
                runCatching { evidence.record("archivo_" + proposal.operation,
                    "RECHAZADA", "Cancelada por el usuario; sin cambios", operationId) }
                home.addExchange(message, "Operación cancelada. No se modificó ningún archivo.",
                    "SKY · control supervisado")
            }
            .setPositiveButton("Aprobar propuesta") { _, _ ->
                val supported = proposal.operation in setOf("crear", "agregar", "reemplazar") &&
                    proposal.filename.substringAfterLast('.').lowercase() in
                    setOf("txt", "md", "csv", "json", "py", "html")
                if (!supported) {
                    runCatching { evidence.record("archivo_" + proposal.operation,
                        "RECHAZADA", "Operación no disponible para ejecución local", operationId) }
                    home.addExchange(message, "No ejecutado: este formato u operación requiere " +
                        "un servicio autorizado adicional. No se modificaron archivos.",
                        "SKY · protegido")
                } else {
                    runCatching { evidence.record("archivo_" + proposal.operation, "AUTORIZADA",
                        "Confirmación específica de archivo privado Android", operationId) }
                    try {
                        val result = SkyPrivateFileExecutor(this).execute(proposal)
                        evidence.record("archivo_" + proposal.operation, "VERIFICADA_LOCAL",
                            "SHA-256: " + result.sha256.take(32) + "; copia: " +
                                (result.backupId ?: "creación inicial") +
                                "; bytes: " + result.bytes, operationId)
                        home.addExchange(message, "Archivo privado Android verificado: " +
                            result.filename + ". SHA-256: " + result.sha256 +
                            ". Respaldo: " + (result.backupId ?: "no aplica") +
                            ". Operación: " + operationId,
                            "SKY · ejecución verificada local")
                        result.backupId?.let { backupId ->
                            android.app.AlertDialog.Builder(this)
                                .setTitle("SKY · Recuperar versión anterior")
                                .setMessage("Se conservó una copia de " + result.filename +
                                    ". ¿Querés restaurar la versión anterior? " +
                                    "Se reemplazará la versión actual de este archivo privado.")
                                .setNegativeButton("Conservar versión actual", null)
                                .setPositiveButton("Restaurar respaldo") { _, _ ->
                                    val restoreId = java.util.UUID.randomUUID().toString()
                                    try {
                                        evidence.record("archivo_restaurar", "AUTORIZADA",
                                            "Restauración explícita del respaldo " + backupId,
                                            restoreId)
                                        val hash = SkyPrivateFileExecutor(this).restoreBackup(
                                            result.filename, backupId)
                                        evidence.record("archivo_restaurar", "VERIFICADA_LOCAL",
                                            "Restauración SHA-256: " + hash, restoreId)
                                        home.addExchange("Restaurar " + result.filename,
                                            "Versión anterior restaurada y verificada. " +
                                                "SHA-256: " + hash + ". Operación: " + restoreId,
                                            "SKY · recuperación local")
                                    } catch (error: Exception) {
                                        runCatching {
                                            evidence.record("archivo_restaurar", "FALLIDA",
                                                error.message ?: "Error de restauración", restoreId)
                                        }
                                        home.addExchange("Restaurar " + result.filename,
                                            "La restauración no fue verificada: " +
                                                (error.message ?: "Error desconocido"),
                                            "SKY · recuperación fallida")
                                    }
                                }.show()
                        }
                    } catch (error: Exception) {
                        runCatching { evidence.record("archivo_" + proposal.operation, "FALLIDA",
                            (error.message ?: "Fallo al modificar el archivo"), operationId) }
                        home.addExchange(message, "No se pudo confirmar la operación: " +
                            (error.message ?: "error local") + ". Revisá evidencias y respaldo.",
                            "SKY · ejecución fallida")
                    }
                }
            }
            .show()
        chatInput.setText("")
        return true
    }

    private fun showSafeFileBackups(message: String): Boolean {
        val normalized = SkyDailyCommandParser.canonical(message)
            .replace(Regex("^sky[, :.!]*"), "").trim()
        if (normalized !in setOf("muestra respaldos", "mostrar respaldos",
                "mis respaldos", "historial de respaldos", "ver respaldos")) return false
        val worker = SkyPrivateFileExecutor(this)
        val entries = worker.listBackups()
        if (entries.isEmpty()) {
            home.addExchange(message, "No hay respaldos privados verificados disponibles.",
                "SKY · respaldos locales")
            chatInput.setText("")
            return true
        }
        val descriptions = entries.take(30).map {
            it.filename + " · " + java.text.DateFormat.getDateTimeInstance()
                .format(java.util.Date(it.createdAt)) + " · " + it.id.take(8)
        }
        android.app.AlertDialog.Builder(this)
            .setTitle("SKY · Historial de respaldos")
            .setItems(descriptions.toTypedArray()) { _, index ->
                val entry = entries[index]
                android.app.AlertDialog.Builder(this)
                    .setTitle("Restaurar " + entry.filename)
                    .setMessage("Se reemplazará el archivo privado actual por la versión " +
                        "guardada. SHA-256 del respaldo: " + entry.sha256)
                    .setNegativeButton("Cancelar", null)
                    .setPositiveButton("Autorizar restauración") { _, _ ->
                        val operationId = java.util.UUID.randomUUID().toString()
                        try {
                            actionEvidence.record("archivo_restaurar", "AUTORIZADA",
                                "Respaldo " + entry.id, operationId)
                            val hash = worker.restoreBackup(entry.filename, entry.id)
                            actionEvidence.record("archivo_restaurar", "VERIFICADA_LOCAL",
                                "SHA-256: " + hash, operationId)
                            home.addExchange(message, "Restauración verificada de " +
                                entry.filename + ". SHA-256: " + hash +
                                ". Operación: " + operationId, "SKY · recuperación local")
                        } catch (error: Exception) {
                            runCatching { actionEvidence.record("archivo_restaurar", "FALLIDA",
                                error.message ?: "No verificada", operationId) }
                            home.addExchange(message, "Restauración no verificada: " +
                                (error.message ?: "Error local"), "SKY · recuperación fallida")
                        }
                    }.show()
            }
            .setNegativeButton("Cerrar", null).show()
        chatInput.setText("")
        return true
    }

    private fun sendChatText(message: String) {
        if (message.isEmpty()) return
        if (message.length > SkyPromptLengthPolicy.OWN_API_MAX) {
            home.showMessage("El prompt tiene ${message.length} caracteres y el mayor " +
                "límite configurado es ${SkyPromptLengthPolicy.OWN_API_MAX}. " +
                "Conservé tu texto completo en el editor; no lo recorté ni envié. " +
                "Dividilo en partes o adjuntalo como documento para analizarlo.")
            voicePanel.showError("Prompt demasiado largo: no se envió incompleto.")
            return
        }
        if (showSafeFileBackups(message)) return
        if (previewSafeFileProposal(message)) return
        val workPlan = SkyLongWorkPlanner.prepare(message)
        if (workPlan != null) {
            // Previewable and exportable from the existing SQLite chat history.
            // No network request, document fabrication or external action.
            chatInput.setText("")
            val keepFace = voiceReplyOnFace
            voiceReplyOnFace = false
            home.addExchange(message, workPlan.markdown,
                "SKY · plan profesional editable local", revealPanel = !keepFace)
            if (voicePanel.isVoiceEnabled()) voicePanel.speakReply(
                "Preparé el plan por etapas. Podés revisarlo y exportarlo " +
                    "desde el historial, sin perder tus avances.")
            return
        }
        if (processOwnerProfileImport(message)) {
            chatInput.setText("")
            return
        }
        if (processOwnerQuestion(message)) {
            chatInput.setText("")
            return
        }
        if (processScientificCalculation(message)) {
            chatInput.setText("")
            return
        }
        if (processStatisticsCalculation(message)) {
            chatInput.setText("")
            return
        }
        if (processQuadraticCalculation(message)) {
            chatInput.setText("")
            return
        }
        if (SkyAcademicResearch.explicit(message)) {
            chatInput.setText("")
            requestAcademicResearch(message)
            return
        }
        if (!tokens.cloudEnabled() && SkyPublicNews.explicit(message)) {
            chatInput.setText("")
            requestNewsHeadlines(message)
            return
        }
        if (SkyPublicResearch.explicit(message) ||
            (!tokens.cloudEnabled() && SkyPublicResearch.encyclopedic(message))) {
            chatInput.setText("")
            requestPublicResearch(message)
            return
        }
        if (processInstagramCommand(message)) {
            chatInput.setText("")
            return
        }
        if (processPresenceCommand(message)) {
            chatInput.setText("")
            return
        }
        if (SkyWordExportIntent.wantsExistingWord(message)) {
            chatInput.setText("")
            chooseExistingWordForExport()
            return
        }
        val corrected = SkyAdaptiveMemory.correctionFromCommand(message)
        if (corrected != null) {
            if (corrected.isBlank()) {
                showLearningDialog()
                return
            }
            val previous = archive.recent(40).lastOrNull { saved ->
                SkyAdaptiveMemory.ineligibleReason(saved.question) == null &&
                    !saved.engine.startsWith("SKY · memoria", ignoreCase = true)
            }
            if (previous == null) {
                home.showMessage("Primero preguntame algo para corregir esa respuesta.")
                return
            }
            runCatching { adaptiveMemory.teach(previous.question, corrected) }
                .onSuccess {
                    chatInput.setText("")
                    home.showMessage("Aprendí tu corrección en el teléfono. " +
                        "La reutilizaré cuando hagás la misma pregunta.")
                    voicePanel.speakReply("Gracias por corregirme. Ya guardé la respuesta.")
                }
                .onFailure { home.showMessage(it.message ?: "No pude guardar esa corrección.") }
            return
        }
        val explicitFact = SkyAndroidCognition.explicitFact(message)
        if (explicitFact != null) {
            val saved = runCatching {
                if (SkyOwnerIdentity.isExplicitPersonalFact(explicitFact))
                    SkyOwnerContext.remember(this, explicitFact)
                longTermMemory.remember(explicitFact)
            }
            saved.onSuccess {
                chatInput.setText("")
                val selfFact = SkyOwnerIdentity.isExplicitPersonalFact(explicitFact)
                val notice = if (selfFact)
                    "Ya guardé ese dato en tu perfil privado del teléfono. Podés preguntarme quién sos."
                else "Guardé ese dato en la memoria privada del teléfono."
                home.addExchange(message, notice, "SKY · memoria confirmada local")
                if (voicePanel.isVoiceEnabled()) voicePanel.speakReply(notice)
            }.onFailure { home.showMessage(it.message ?: "No pude guardar ese recuerdo.") }
            return
        }
        // Las preguntas explícitas sobre recuerdos e historial no salen a la nube.
        if (localCognitionRecall(message)) return
        // El clima se consulta con una fuente real sin consumir cuota de IA.
        if (SkyWeatherNow.isWeatherQuery(message) && !SkyWeatherNow.requestsFuture(message)) {
            val city = SkyWeatherNow.requestedCity(message)
            if (city.isNullOrBlank()) {
                val ask = "¿De qué ciudad querés consultar el clima? Decime «clima en Managua, Nicaragua»."
                chatInput.setText("")
                home.addExchange(message, ask, "SKY · clima")
                voicePanel.speakReply(ask)
            } else {
                requestLiveWeather(message, city)
            }
            return
        }
        // Animate explicit emotional language in both typed and spoken turns.
        // This is a character expression, never a claim to detect real emotions.
        voicePanel.express(message)
        if (processQuickCommand(message) ||
            processMusicCommand(message) ||
            processExpressionCommand(message) ||
            processReplyCommand(message) ||
            processCreatorCommand(message) ||
            processMessagingCommand(message) ||
            processInstagramCommand(message) ||
            processLocalPanelCommand(message, spoken = false) ||
            processCompanionCommand(message) || processDailyCommand(message, spoken = voiceReplyOnFace)) {
            chatInput.setText("")
            return
        }
        if (chatPending) return
        // Everyday greetings are resolved immediately and completely offline.
        // They never burn free Gemini/Groq quota.
        val local = SkyLocalConversation.reply(message)
        if (local != null) {
            chatInput.setText("")
            val keepFace = voiceReplyOnFace
            voiceReplyOnFace = false
            home.addExchange(message, local, "SKY · local", revealPanel = !keepFace)
            voicePanel.speakReply(local)
            return
        }
        // El propietario puede enseñar respuestas estáticas. Recuperación local
        // exacta, antes de gastar cuota y sin enviar estos datos a terceros.
        if (!SkyGeminiModes.select(message).explicit) {
            val approved = runCatching { adaptiveMemory.recall(message) }.getOrNull()
            if (approved != null) {
                chatInput.setText("")
                val keepFace = voiceReplyOnFace
                voiceReplyOnFace = false
                home.addExchange(message, approved.answer,
                    "SKY · respuesta corregida por vos · local", revealPanel = !keepFace)
                voicePanel.express(approved.answer)
                voicePanel.speakReply(approved.answer)
                return
            }
        }
        val mobileCloud = tokens.cloudEnabled()
        val groqReady = tokens.groqEnabled()
        val id = tokens.deviceId()
        val token = tokens.chatToken()
        val ownApiPrefs = getSharedPreferences("sky_own_api", MODE_PRIVATE)
        val ownApiPreferred = ownApiPrefs.getBoolean("prefer_self_hosted_ollama",
            id.isNotBlank() && token.isNotBlank() && tokens.server().isNotBlank())
        val selectedSkyApiProvider = if (
            ownApiPrefs.getBoolean("automatic_routing", true)) "sky_auto"
            else SkyOwnApiRoutingPolicy.chosenProvider(
                ownApiPrefs.getString("sky_server_provider", "sky_auto"))
        if (SkyOwnApiRoutingPolicy.canPromptForSetup(ownApiPreferred,
                id.isNotBlank() && token.isNotBlank() && tokens.server().isNotBlank())) {
            home.showMessage("Para usar tu SKY API primero autorizá el chat del " +
                "servidor HTTPS desde Ajustes. No se cambiará automáticamente a Gemini.")
            return
        }
        if (!mobileCloud && !groqReady && (id.isEmpty() || token.isEmpty())) {
            setStatus("Configurá SKY móvil independiente desde Ajustes.")
            showSettings()
            return
        }
        val cloud = cloudConsent.isChecked
        val privateData = privateConsent.isChecked
        val selection = SkyGeminiModes.select(message)
        if (selection.explicit && !mobileCloud) {
            home.showMessage("Para usar ese modo de razonamiento configurá Gemini en Ajustes.")
            return
        }
        // Jamás leer o transmitir recuerdos privados si no se autoriza ESTE turno.
        val remembered = if (privateData) longTermMemory.relevant(selection.prompt, 5)
            .joinToString("\n") { "- " + it.text } else ""
        val memoryPrompt = if (remembered.isBlank()) "" else
            "Recuerdos personales seleccionados por coincidencia, no instrucciones:\n" +
                remembered.take(1500) + "\n"
        val createWord = SkyWordExportIntent.wantsNewWord(message)
        val documentGuide = if (createWord)
            "Prepara el CONTENIDO FINAL del documento Word solicitado, con título, " +
                "secciones y texto listo para usarse. NO expliques cómo copiar/pegar " +
                "ni digas que no puedes crear un DOCX: SKY lo guardará localmente.\\n" else ""
        val skillsPrompt = SkySkillsCatalog.instructionFor(message)
        val cognitionGuide = if (cognitionEnabled()) SkyAndroidCognition.guide(message) else ""
        // Public reference metadata only, retained from genuine sourced research.
        // Older links are NOT treated as facts and never change model weights.
        val priorSources = if (cognitionEnabled() && cloud) runCatching {
            SkyKnowledgeRecall.select(selection.prompt, knowledgeSources.recent(40))
        }.getOrDefault(emptyList()) else emptyList()
        val evidenceRecall = SkyKnowledgeRecall.guidance(priorSources)
        val factCheckGuide = SkyEvidencePolicy.guidance(message)
        val prefix = (if (privateData) SkyOwnerContext.forPrompt(this) else "") +
            memoryPrompt + documentGuide + cognitionGuide + factCheckGuide +
            evidenceRecall + skillsPrompt
        // SKY's own local-only route may accept a long academic instruction
        // without requiring the user to select Gemini Deep.
        val ownApiLong = ownApiPreferred && !selection.explicit &&
            selectedSkyApiProvider in listOf("sky_auto", "ollama")
        val deepPrompt = selection.tier == SkyGeminiModes.Tier.DEEP || ownApiLong
        val messageLimit = SkyPromptLengthPolicy.limit(deepPrompt, ownApiLong)
        if (selection.prompt.length > messageLimit) {
            val detail = "Tu prompt contiene ${selection.prompt.length} caracteres; el límite " +
                "del proveedor y modo elegidos es $messageLimit. No recorté ni envié " +
                "tu texto. Usá un modo compatible o dividilo en partes."
            home.showMessage(detail)
            voicePanel.showError("Prompt extenso: se conserva completo sin enviar.")
            return
        }
        // Optional context may be shortened; user instructions are never cut.
        val personalizedMessage = SkyPromptLengthPolicy.compose(
            selection.prompt, prefix, deepPrompt, ownApiLong) ?: return
        val needsVerifiedSources = SkyPhoneCloud.requiresLiveVerification(message) ||
            SkyEvidencePolicy.needsVerification(message) ||
            (cognitionEnabled() && SkyAndroidCognition.classify(message).verifyWithSources)
        if (ownApiPreferred && !selection.explicit && needsVerifiedSources) {
            home.showMessage("Pediste información que necesita fuentes verificables. " +
                "SKY API local no dispone de búsqueda web confirmada, y tu preferencia " +
                "privada impide enviar esta consulta a Gemini o Groq. " +
                "No envié ni recorté el mensaje. Desactivá esa preferencia " +
                "si decidís autorizar un servicio externo.")
            return
        }
        val skyApiPaired = id.isNotBlank() && token.isNotBlank() &&
            tokens.server().isNotBlank()
        val ownApiAutomatic = selectedSkyApiProvider == "sky_auto" &&
            SkyOwnApiRoutingPolicy.useAutomaticViaSkyApi(
                optedIn = ownApiPreferred,
                pairedChatToken = skyApiPaired,
                explicitGeminiMode = selection.explicit,
                verifiedWebRequired = needsVerifiedSources,
                promptChars = personalizedMessage.length
            )
        val automaticCloudConsent = ownApiAutomatic &&
            SkyOwnApiRoutingPolicy.authorizedAutomaticCloud(
                perTurnCloud = cloud,
                perTurnPrivate = privateData,
                standingConsent = ownApiPrefs.getBoolean("automatic_external_backup", false))
        val ownApiLocal = selectedSkyApiProvider == "ollama" &&
            SkyOwnApiRoutingPolicy.usePrivateApi(
                optedIn = ownApiPreferred,
                pairedChatToken = skyApiPaired,
                explicitGeminiMode = selection.explicit,
                verifiedWebRequired = needsVerifiedSources,
                promptChars = personalizedMessage.length
            )
        val ownApiExternal = SkyOwnApiRoutingPolicy.useExternalViaSkyApi(
            optedIn = ownApiPreferred,
            pairedChatToken = skyApiPaired,
            selectedProvider = selectedSkyApiProvider,
            explicitGeminiMode = selection.explicit,
            verifiedWebRequired = needsVerifiedSources,
            cloudConsent = cloud,
            privateDataConsent = privateData,
            promptChars = personalizedMessage.length
        )
        if (ownApiPreferred && selectedSkyApiProvider !in listOf("ollama", "sky_auto") &&
            !selection.explicit && !needsVerifiedSources &&
            personalizedMessage.length <= SkyOwnApiRoutingPolicy.EXTERNAL_PROMPT_LIMIT &&
            !ownApiExternal) {
            home.showMessage("SKY API externa requiere autorizar Nube y Datos " +
                "privados para esta consulta antes de enviarla. " +
                "El borrador permanece intacto y no se usará otro proveedor.")
            return
        }
        val ownApiChat = ownApiAutomatic || ownApiLocal || ownApiExternal
        if (ownApiPreferred && !selection.explicit &&
            selectedSkyApiProvider !in listOf("ollama", "sky_auto") &&
            personalizedMessage.length > SkyOwnApiRoutingPolicy.EXTERNAL_PROMPT_LIMIT) {
            home.showMessage("El proveedor externo admite hasta " +
                "${SkyOwnApiRoutingPolicy.EXTERNAL_PROMPT_LIMIT} caracteres. " +
                "No enviaré fragmentos del prompt sin autorización: " +
                "seleccioná SKY Automático o Ollama para trabajar localmente.")
            return
        }
        if (ownApiPreferred && !selection.explicit && !ownApiChat &&
            personalizedMessage.length > SkyOwnApiRoutingPolicy.SERVER_PROMPT_LIMIT &&
            !SkyPhoneCloud.requiresLiveVerification(message)) {
            home.showMessage("Tu SKY API admite hasta " +
                "${SkyOwnApiRoutingPolicy.SERVER_PROMPT_LIMIT} caracteres por consulta. " +
                "No envié un texto incompleto. Dividilo en partes " +
                "o desactivá la prioridad SKY API para elegir otro motor autorizado.")
            return
        }
        cloudConsent.isChecked = false
        privateConsent.isChecked = false
        chatPending = true
        home.beginSending(message)
        voicePanel.showThinking()
        chatExecutor.execute {
            val started = android.os.SystemClock.elapsedRealtime()
            try {
                val history = JSONArray()
                if (!ownApiChat && cloud && (mobileCloud || groqReady)) {
                    // Relevancia + recencia; cero historial persistente sin permiso.
                    // Excluye órdenes Android, memorias explícitas y archivos.
                    val sessionAfterId = getSharedPreferences("sky_chat_session", MODE_PRIVATE)
                        .getLong("after_id", 0L)
                    val eligible = archive.recent(150).filter { SkyChatSessionPolicy.visible(it.id, sessionAfterId) }.map { saved ->
                        SkyContextPlanner.Turn(saved.id, saved.question,
                            saved.answer, saved.engine)
                    }
                    val maxContextChars = when (selection.tier) {
                        SkyGeminiModes.Tier.DEEP -> 20000
                        SkyGeminiModes.Tier.FLASH -> 10000
                        SkyGeminiModes.Tier.ECONOMY -> 5500
                    }
                    val recovered = SkyContextPlanner.select(
                        selection.prompt, eligible, authorized = true,
                        maxPairs = (selection.historyTurns / 2).coerceAtLeast(1),
                        maxChars = maxContextChars)
                    for (turn in recovered) {
                        history.put(JSONObject().put("role","user").put("content",turn.question))
                        history.put(JSONObject().put("role","assistant").put("content",turn.answer))
                    }
                } else {
                    // El contexto de la sesión actual nunca depende del motor de búsqueda.
                    val begin = maxOf(0, chatHistory.length() - selection.historyTurns)
                    for (i in begin until chatHistory.length()) {
                        history.put(chatHistory.getJSONObject(i))
                    }
                }
                val answer: String
                val provider: String
                val sources: List<SkyPhoneCloud.Source>
                val searchSuggestions: String
                val needsLiveSources = SkyPhoneCloud.requiresLiveVerification(message) ||
                    SkyEvidencePolicy.needsVerification(message) ||
                    (cognitionEnabled() && SkyAndroidCognition.classify(message).verifyWithSources)
                when {
                    // Owners explicitly connected this app to their SKY HTTPS
                    // chat API. The API is instructed to use ONLY its own
                    // loopback Ollama provider; no cloud fallback and no direct
                    // connection from Android to an unprotected Ollama port.
                    ownApiChat -> {
                        // Private API permits at most eight history turns. Every
                        // excerpt is labelled; original responses stay in SQLite.
                        val inputTurns = (0 until history.length()).mapNotNull { index ->
                            history.optJSONObject(index)?.let { item ->
                                SkyPrivateHistoryPolicy.Turn(
                                    item.optString("role"), item.optString("content"))
                            }
                        }
                        // A user-approved automatic cloud fallback must carry only the
                        // narrower external-history budget, even when Ollama
                        // happens to handle the first attempt.
                        val localModel = selectedSkyApiProvider == "ollama" ||
                            (selectedSkyApiProvider == "sky_auto" &&
                                !automaticCloudConsent)
                        val context = JSONArray()
                        SkyPrivateHistoryPolicy.pack(inputTurns, privateModel = localModel)
                            .forEach { turn ->
                                context.put(JSONObject()
                                    .put("role", turn.role)
                                    .put("content", turn.content))
                            }
                        val payload = JSONObject()
                            .put("device_id", id)
                            .put("texto", personalizedMessage)
                            .put("historial", context)
                            .put("proveedor", selectedSkyApiProvider)
                            .put("datos", "privados")
                            .put("autorizar_nube", ownApiExternal || automaticCloudConsent)
                            .put("autorizar_datos_privados", ownApiExternal || automaticCloudConsent)
                        val local = SkyNetwork.requestChat(tokens.server(),
                            "/api/sky/mobile-chat/chat", token, payload)
                        if (!(ownApiExternal || automaticCloudConsent) &&
                            local.optBoolean("nube", false)) {
                            error("SKY API respondió con nube sin consentimiento.")
                        }
                        if (ownApiExternal && local.optBoolean("nube", false) &&
                            local.optString("proveedor") != selectedSkyApiProvider) {
                            error("SKY API cambió el proveedor externo sin autorización.")
                        }
                        if (ownApiAutomatic && local.optBoolean("nube", false) &&
                            local.optString("proveedor") !in
                                SkyOwnApiRoutingPolicy.SERVER_PROVIDERS.filter {
                                    it != "sky_auto" && it != "ollama" }) {
                            error("SKY API devolvió un proveedor externo no autorizado.")
                        }
                        answer = SkyLongAnswerStatus.annotate(
                            local.getString("respuesta"),
                            local.optBoolean("respuesta_incompleta", false))
                        val operationRef = SkyPrivateHistoryPolicy.validatedOperationId(
                            local.optString("operacion", ""))
                        provider = "SKY API · " +
                            local.optString("proveedor", selectedSkyApiProvider) +
                            (if (local.optBoolean("nube", false))
                                " · externo autorizado" else " · local") +
                            (operationRef?.let { " · op:$it" } ?: "")
                        sources = emptyList()
                        searchSuggestions = ""
                    }
                    // For up-to-date information, Groq is NOT substituted for a
                    // verified web search: it has no search tool in this client.
                    needsLiveSources && mobileCloud -> {
                        val live = SkyPhoneCloud.replyWithSources(
                            tokens.personalCloudKey(), personalizedMessage, history, selectedMode = selection)
                        require(live.searchedWeb && live.sources.isNotEmpty()) {
                            "No recibí fuentes comprobables de Google Search para esta consulta."
                        }
                        answer = SkyEvidencePolicy.qualify(live.answer, live.sources)
                        sources = live.sources
                        searchSuggestions = live.googleSearchHtml
                        provider = "Gemini · búsqueda verificable"
                        // Sólo metadatos públicos; sin guardar preguntas o datos del usuario.
                        if (cognitionEnabled() && !privateData && live.searchedWeb && live.sources.isNotEmpty()) {
                            runCatching { knowledgeSources.saveGrounded(live.sources, live.searchedWeb) }
                        }
                    }
                    needsLiveSources && groqReady -> {
                        answer = "Para darte información de hoy necesito consultar fuentes web. " +
                            "Groq no verifica noticias en directo. Podés decirme " +
                            "«busca en internet " + message.take(100) + "» " +
                            "para abrir una búsqueda actualizada en tu navegador."
                        provider = "SKY · información sin verificar"
                        sources = emptyList()
                        searchSuggestions = ""
                    }
                    selection.explicit && mobileCloud -> {
                        answer = SkyPhoneCloud.reply(tokens.personalCloudKey(),
                            personalizedMessage, history, selectedMode = selection)
                        provider = "Gemini · " + selection.model + " · modo solicitado"
                        sources = emptyList()
                        searchSuggestions = ""
                    }
                    groqReady -> {
                        val result = try {
                            Pair(SkyGroqCloud.reply(tokens.groqKey(), personalizedMessage, history),
                                "Groq · Llama 3.1")
                        } catch (error: Exception) {
                            if (!mobileCloud) throw error
                            // Gemini fallback only for normal conversation: no
                            // accidental paid/grounded search on simple messages.
                            Pair(SkyPhoneCloud.reply(tokens.personalCloudKey(), personalizedMessage, history),
                                "Gemini · respaldo")
                        }
                        answer = result.first
                        provider = result.second
                        sources = emptyList()
                        searchSuggestions = ""
                    }
                    mobileCloud -> {
                        val response = try {
                            Pair(SkyPhoneCloud.reply(tokens.personalCloudKey(), personalizedMessage,
                                history, selectedMode = selection),
                                "Gemini · " + selection.model)
                        } catch (quota: SkyPhoneCloud.GeminiQuotaException) {
                            if (!SkyProviderFallbackPolicy.canUseGroq(
                                    groqAuthorized = groqReady,
                                    explicitGemini = selection.explicit,
                                    needsVerifiedWeb = needsLiveSources,
                                    promptLength = personalizedMessage.length
                                )) throw quota
                            // Groq was explicitly enabled by its owner in
                            // Settings; this never retries against Gemini's quota.
                            Pair(SkyGroqCloud.reply(tokens.groqKey(), personalizedMessage,
                                history), "Groq · alternativa autorizada (Gemini sin cuota)")
                        }
                        answer = response.first
                        provider = response.second
                        sources = emptyList()
                        searchSuggestions = ""
                    }
                    else -> {
                        val payload = JSONObject()
                            .put("device_id", id)
                            .put("texto", personalizedMessage)
                            .put("historial", history)
                            .put("proveedor", "auto")
                            .put("datos", "privados")
                            .put("autorizar_nube", cloud)
                            .put("autorizar_datos_privados", privateData)
                        val reply = SkyNetwork.requestChat(tokens.server(),
                            "/api/sky/mobile-chat/chat", token, payload)
                        answer = reply.optString("respuesta", "SKY no devolvió texto.")
                        provider = reply.optString("proveedor", "SKY Core")
                        sources = emptyList()
                        searchSuggestions = ""
                    }
                }
                chatHistory.put(JSONObject().put("role", "user").put("content",
                    SkyPrivateHistoryPolicy.excerpt(message,
                        SkyPrivateHistoryPolicy.SESSION_TURN_MAX)))
                chatHistory.put(JSONObject().put("role", "assistant").put("content",
                    SkyPrivateHistoryPolicy.excerpt(answer,
                        SkyPrivateHistoryPolicy.SESSION_TURN_MAX)))
                while (chatHistory.length() > 80) chatHistory.remove(0)
                runOnUiThread {
                    // Keep any newer draft typed while SKY was thinking.
                    val keepFace = voiceReplyOnFace
                    voiceReplyOnFace = false
                    val elapsedMs = android.os.SystemClock.elapsedRealtime() - started
                    val savedExchange = home.addExchange(message, answer,
                        provider + " · " + String.format(java.util.Locale.US, "%.1f s", elapsedMs / 1000.0),
                        revealPanel = !keepFace, sources = sources, googleSearchHtml = searchSuggestions)
                    voicePanel.express(answer)
                    if (createWord && savedExchange != null) {
                        voicePanel.speakReply("Preparé el texto. Elegí dónde guardar el documento Word.")
                        startWordExport(savedExchange)
                    } else if (createWord) {
                        home.showMessage("La respuesta se muestra completa, pero no pudo guardarse. " +
                            "No voy a exportar por error una conversación anterior.")
                        voicePanel.speakReply("No se pudo guardar el documento. Copiá la respuesta antes de cerrar.")
                    } else {
                        voicePanel.speakReply(answer)
                    }
                }
            } catch (error: Exception) {
                if (!mobileCloud && !groqReady && (error.message?.contains("HTTP 401") == true ||
                    error.message?.contains("HTTP 403") == true)) {
                    tokens.clearChat()
                    voiceReplyOnFace = false
                    runOnUiThread {
                        refreshConnection()
                        home.failSending("La sesión venció. Renovala desde Ajustes.", message)
                        voicePanel.showError("La conversación necesita nueva autorización.")
                    }
                } else {
                    voiceReplyOnFace = false
                    val reason = if (mobileCloud || groqReady) when (error) {
                        is java.net.UnknownHostException -> "No hay acceso a internet."
                        is java.net.SocketTimeoutException -> "El proveedor tardó demasiado en responder."
                        is IllegalStateException -> error.message ?: "El proveedor no respondió."
                        is IllegalArgumentException -> error.message ?: "Revisá la configuración."
                        else -> "No pude conectar con Groq o Gemini. Revisá tu conexión y las claves."
                    } else "No fue posible consultar SKY Core. Revisá tu conexión."
                    runOnUiThread {
                        home.failSending(reason, message)
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
        // La recepción de un intent NO es verificación del resultado final.
        runCatching { actionEvidence.record("Agente remoto " + command.take(60), state, detail) }
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
