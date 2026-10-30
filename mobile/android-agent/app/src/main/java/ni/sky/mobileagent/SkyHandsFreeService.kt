package ni.sky.mobileagent

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.SystemClock
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import java.util.Locale

/**
 * Microphone foreground service, enabled only by explicit user opt-in.
 * On-device recognizer only: never silently fall back to a cloud recognizer.
 * Android's SpeechRecognizer is NOT a hardware low-power hotword engine: the
 * system may stop it; battery use and model availability vary by device.
 */
class SkyHandsFreeService : Service() {
    companion object {
        const val ACTION_START = "ni.sky.mobileagent.HANDSFREE_START"
        const val ACTION_STOP = "ni.sky.mobileagent.HANDSFREE_STOP"
        const val EXTRA_COMMAND = "ni.sky.mobileagent.PENDING_VOICE_COMMAND"
        private const val CHANNEL = "sky_hands_free"
        private const val NOTIFICATION_ID = 4107
        private const val IDLE_MS = 45_000L
        @Volatile private var current: SkyHandsFreeService? = null
        /** No conserva voz ni transcripciones. Estado técnico de la sesión activa. */
        data class Health(val active: Boolean, val recognizing: Boolean,
                          val awake: Boolean, val lastPhraseAtMs: Long,
                          val errorCode: Int, val retries: Int)
        fun health(): Health {
            val service = current ?: return Health(false, false, false, 0, 0, 0)
            return Health(service.running, service.listening, service.awake,
                service.lastPhraseAtMs, service.lastErrorCode, service.retryCount)
        }
        @Volatile var onPhrase: ((String) -> Unit)? = null
        @Volatile var onWake: (() -> Unit)? = null
        @Volatile var onInstagramNotice: ((Int) -> Unit)? = null
        @Volatile var onStatus: ((Boolean) -> Unit)? = null
        @Volatile var onStopped: (() -> Unit)? = null
        /** Explicit text/voice control from the visible Activity, never from third-party content. */
        fun ownerPresenceCommand(command: String): Boolean {
            val service = current ?: return false
            if (!service.running || SkyVoicePresence.request(command) ==
                SkyVoicePresence.Request.NONE) return false
            service.handler.post { service.process(command) }
            return true
        }
        fun pauseForReply() { current?.handler?.post { current?.suspendForSpeech() } }
        fun resumeAfterReply() { current?.handler?.post { current?.resumeFromSpeech() } }
        fun stop(context: android.content.Context) {
            context.startService(Intent(context, SkyHandsFreeService::class.java)
                .setAction(ACTION_STOP))
        }
    }

    private val handler = Handler(Looper.getMainLooper())
    private var recognizer: SpeechRecognizer? = null
    private var tts: TextToSpeech? = null
    private var running = false
    private var listening = false
    private var awake = false
    private var presence = SkyVoicePresence.Mode.WAKE_ONLY
    private val voiceSettings by lazy { getSharedPreferences("sky_voice_settings", MODE_PRIVATE) }
    private var speechSuspended = false
    private var retryCount = 0
    private var lastCycle = 0L
    private var lastPhraseAtMs = 0L
    private var lastErrorCode = 0
    private var pendingBackgroundCommand: String? = null
    private var pendingExpiresAt = 0L
    private val nextListen = Runnable { arm() }
    private val fallAsleep = Runnable {
        awake = false
        onStatus?.invoke(true)
        notifyState(if (presence == SkyVoicePresence.Mode.SLEEP_LOCKED)
            "SKY dormida por orden · decí SKY despierta"
            else "SKY en espera · decí SKY")
    }
    private val safetyResume = Runnable { resumeFromSpeech() }
    private val instagramChecking = java.util.concurrent.atomic.AtomicBoolean(false)
    private val instagramPoll = object : Runnable {
        override fun run() {
            if (!running) return
            if (SkyInstagramAlerts.enabled(this@SkyHandsFreeService) &&
                SkyInstagramAlerts.paired(this@SkyHandsFreeService) &&
                instagramChecking.compareAndSet(false, true)) {
                Thread {
                    val update = runCatching {
                        SkyInstagramAlerts.observe(this@SkyHandsFreeService,
                            SkyInstagramAlerts.fetch(this@SkyHandsFreeService))
                    }.getOrNull()
                    handler.post {
                        instagramChecking.set(false)
                        if (running && update != null && update.newCount > 0 &&
                            SkyInstagramAlerts.enabled(this@SkyHandsFreeService)) {
                            SkyInstagramAlerts.notifyNew(this@SkyHandsFreeService,
                                update.newCount)
                            val cb = onInstagramNotice
                            if (cb != null) cb.invoke(update.newCount)
                            else if (presence != SkyVoicePresence.Mode.SLEEP_LOCKED &&
                                voiceSettings.getBoolean("read_aloud", true)) {
                                val notice = if (update.newCount == 1)
                                    "Te llegó un mensaje nuevo de Instagram. Podés pedirme que lo lea."
                                else "Te llegaron " + update.newCount +
                                    " mensajes de Instagram. Pedime que los revise."
                                say(notice)
                            }
                        }
                    }
                }.start()
            }
            handler.postDelayed(this, 60_000L)
        }
    }


    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        current = this
        (getSystemService(NOTIFICATION_SERVICE) as NotificationManager).createNotificationChannel(
            NotificationChannel(CHANNEL, "SKY manos libres", NotificationManager.IMPORTANCE_LOW)
        )
        tts = TextToSpeech(this) { status ->
            if (status == TextToSpeech.SUCCESS) {
                tts?.language = Locale("es", "NI")
            }
        }
        tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onStart(utteranceId: String?) {}
            override fun onDone(utteranceId: String?) { handler.post { resumeFromSpeech() } }
            override fun onError(utteranceId: String?) { handler.post { resumeFromSpeech() } }
        })
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            getSharedPreferences("sky_voice_settings", MODE_PRIVATE)
                .edit().putBoolean("hands_free_opt_in", false).apply()
            stopSelf()
            return START_NOT_STICKY
        }
        if (running) return START_NOT_STICKY
        try {
            if (Build.VERSION.SDK_INT >= 29) {
                startForeground(NOTIFICATION_ID, notification("SKY durmiendo · decí SKY"),
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE)
            } else startForeground(NOTIFICATION_ID, notification("SKY durmiendo · decí SKY"))
        } catch (_: Exception) {
            stopSelf()
            return START_NOT_STICKY
        }
        if (Build.VERSION.SDK_INT < 31 ||
            checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED ||
            !SpeechRecognizer.isOnDeviceRecognitionAvailable(this)) {
            getSharedPreferences("sky_voice_settings", MODE_PRIVATE)
                .edit().putBoolean("hands_free_opt_in", false).apply()
            onStopped?.invoke()
            stopSelf()
            return START_NOT_STICKY
        }
        running = true
        presence = when (voiceSettings.getString("sky_presence_mode", "WAKE_ONLY")) {
            "SLEEP_LOCKED" -> SkyVoicePresence.Mode.SLEEP_LOCKED
            "ATTENTIVE" -> SkyVoicePresence.Mode.ATTENTIVE
            else -> SkyVoicePresence.Mode.WAKE_ONLY
        }
        awake = presence == SkyVoicePresence.Mode.ATTENTIVE
        notifyState(when (presence) {
            SkyVoicePresence.Mode.SLEEP_LOCKED -> "SKY dormida · decí SKY despierta"
            SkyVoicePresence.Mode.ATTENTIVE -> "SKY atenta · esperando órdenes"
            else -> "SKY en espera · decí SKY"
        })
        onStatus?.invoke(!awake)
        arm()
        handler.post(instagramPoll)
        return START_NOT_STICKY  // No unauthorized microphone auto-restart at boot.
    }

    private fun notification(description: String, command: String? = null): Notification {
        val open = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
            if (command != null) putExtra(EXTRA_COMMAND, command)
        }
        val openAction = PendingIntent.getActivity(this, 4108, open,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val stopAction = PendingIntent.getService(this, 4109,
            Intent(this, SkyHandsFreeService::class.java).setAction(ACTION_STOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        return Notification.Builder(this, CHANNEL)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentTitle("SKY IA · Manos libres")
            .setContentText(description)
            .setContentIntent(openAction)
            .setOngoing(true)
            .addAction(android.R.drawable.ic_delete, "Apagar micrófono", stopAction)
            .build()
    }

    private fun notifyState(description: String, command: String? = null) {
        (getSystemService(NOTIFICATION_SERVICE) as NotificationManager)
            .notify(NOTIFICATION_ID, notification(description, command))
    }

    private fun schedule(delayMs: Long) {
        handler.removeCallbacks(nextListen)
        if (running && !speechSuspended) handler.postDelayed(nextListen, delayMs)
    }

    private fun stopRecognizer() {
        listening = false
        val old = recognizer
        recognizer = null
        runCatching { old?.cancel() }
        runCatching { old?.destroy() }
    }

    private fun arm() {
        if (!running || speechSuspended || listening) return
        if (SystemClock.elapsedRealtime() - lastCycle < 500) {
            schedule(550)
            return
        }
        stopRecognizer()
        try {
            val engine = SpeechRecognizer.createOnDeviceSpeechRecognizer(this)
            recognizer = engine
            engine.setRecognitionListener(object : RecognitionListener {
                override fun onReadyForSpeech(params: Bundle?) {}
                override fun onBeginningOfSpeech() {}
                override fun onRmsChanged(rmsdB: Float) {}
                override fun onBufferReceived(buffer: ByteArray?) {}
                override fun onEndOfSpeech() {}
                override fun onPartialResults(partialResults: Bundle?) {}
                override fun onEvent(eventType: Int, params: Bundle?) {}

                override fun onError(error: Int) {
                    lastErrorCode = error
                    if (!listening) return
                    stopRecognizer()
                    if (!running) return
                    if (error == SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS ||
                        error == SpeechRecognizer.ERROR_LANGUAGE_NOT_SUPPORTED ||
                        error == SpeechRecognizer.ERROR_LANGUAGE_UNAVAILABLE) {
                        notifyState("Reconocimiento local no disponible. Revisá idioma y permisos.")
                        getSharedPreferences("sky_voice_settings", MODE_PRIVATE)
                            .edit().putBoolean("hands_free_opt_in", false).apply()
                        onStopped?.invoke()
                        stopSelf()
                        return
                    }
                    retryCount = (retryCount + 1).coerceAtMost(5)
                    schedule(if (error == SpeechRecognizer.ERROR_NO_MATCH ||
                        error == SpeechRecognizer.ERROR_SPEECH_TIMEOUT) 750
                        else (1000L * retryCount).coerceAtMost(5000L))
                }

                override fun onResults(results: Bundle?) {
                    if (!listening) return
                    val heard = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                        ?.firstOrNull().orEmpty()
                    stopRecognizer()
                    lastCycle = SystemClock.elapsedRealtime()
                    lastPhraseAtMs = System.currentTimeMillis()
                    lastErrorCode = 0
                    retryCount = 0
                    process(heard)
                }
            })
            val options = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                    RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, "es-NI")
                putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true)
                putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
            }
            listening = true
            engine.startListening(options)
        } catch (_: Exception) {
            stopRecognizer()
            retryCount = (retryCount + 1).coerceAtMost(5)
            schedule((1000L * retryCount).coerceAtMost(5000L))
        }
    }

    private fun resetInactivity() {
        handler.removeCallbacks(fallAsleep)
        if (awake && presence != SkyVoicePresence.Mode.ATTENTIVE)
            handler.postDelayed(fallAsleep, IDLE_MS)
    }

    private fun suspendForSpeech() {
        if (!running) return
        speechSuspended = true
        handler.removeCallbacks(nextListen)
        stopRecognizer()
        handler.removeCallbacks(safetyResume)
        handler.postDelayed(safetyResume, 20_000L)
    }

    private fun resumeFromSpeech() {
        if (!running) return
        speechSuspended = false
        handler.removeCallbacks(safetyResume)
        resetInactivity()
        schedule(850)
    }

    private fun say(message: String) {
        suspendForSpeech()
        val result = tts?.speak(SkySpokenText.prepare(message), TextToSpeech.QUEUE_FLUSH, Bundle(),
            "sky-service-" + SystemClock.uptimeMillis())
        if (result != TextToSpeech.SUCCESS) {
            handler.postDelayed({ resumeFromSpeech() }, 1500)
        }
    }

    /**
     * El servicio puede seguir activo con la pantalla apagada. Las teclas
     * multimedia son acciones Android; abrir apps requiere UI desbloqueada.
     */
    private fun handleWithoutVisibleUi(command: String) {
        if (SkyInstagramAlerts.command(command) == SkyInstagramAlerts.Command.READ) {
            val guard = getSystemService(KEYGUARD_SERVICE) as android.app.KeyguardManager
            if (guard.isDeviceLocked) {
                notifyState("Instagram · desbloqueá el teléfono para consultar", command)
                say("Por tu privacidad, desbloqueá el teléfono antes de que lea tus mensajes.")
                return
            }
            Thread {
                val answer = runCatching {
                    SkyInstagramAlerts.summary(SkyInstagramAlerts.fetch(this))
                }.getOrElse { "No pude consultar Instagram de forma segura." }
                handler.post { if (running && presence != SkyVoicePresence.Mode.SLEEP_LOCKED)
                    say(answer) }
            }.start()
            return
        }
        val quick = SkyQuickCommand.parse(command)
        if (quick != null) {
            if (quick == SkyQuickCommand.Action.REQUEST_UNLOCK) {
                notifyState("Desbloqueo seguro pendiente · tocá aquí", command)
                say("Para desbloquear el teléfono, usa tu huella o PIN de Android.")
                return
            }
            try {
                val audio = getSystemService(AUDIO_SERVICE) as android.media.AudioManager
                if (quick == SkyQuickCommand.Action.VOLUME_UP ||
                    quick == SkyQuickCommand.Action.VOLUME_DOWN) {
                    if (audio.isVolumeFixed) {
                        say("El volumen está fijado por Android.")
                    } else {
                        val direction = if (quick == SkyQuickCommand.Action.VOLUME_UP)
                            android.media.AudioManager.ADJUST_RAISE
                        else android.media.AudioManager.ADJUST_LOWER
                        audio.adjustStreamVolume(android.media.AudioManager.STREAM_MUSIC, direction, 0)
                        say("Le pedí a Android que ajuste el volumen.")
                    }
                } else {
                    val key = when (quick) {
                        SkyQuickCommand.Action.NEXT -> android.view.KeyEvent.KEYCODE_MEDIA_NEXT
                        SkyQuickCommand.Action.PREVIOUS -> android.view.KeyEvent.KEYCODE_MEDIA_PREVIOUS
                        SkyQuickCommand.Action.RESTART -> android.view.KeyEvent.KEYCODE_MEDIA_PREVIOUS
                        SkyQuickCommand.Action.PAUSE -> android.view.KeyEvent.KEYCODE_MEDIA_PAUSE
                        SkyQuickCommand.Action.PLAY -> android.view.KeyEvent.KEYCODE_MEDIA_PLAY
                        else -> null
                    }
                    if (key != null) {
                        val now = SystemClock.uptimeMillis()
                        audio.dispatchMediaKeyEvent(android.view.KeyEvent(now, now,
                            android.view.KeyEvent.ACTION_DOWN, key, 0))
                        audio.dispatchMediaKeyEvent(android.view.KeyEvent(now, now,
                            android.view.KeyEvent.ACTION_UP, key, 0))
                        say("Envié la orden al reproductor. Si no responde, revisa la aplicación.")
                    }
                }
            } catch (_: Exception) {
                say("Android no permitió controlar el reproductor en este momento.")
            }
            return
        }
        val music = SkyMusicCommand.parse(command)
        val daily = SkyDailyCommandParser.parse(command)
        if (music != null || daily is SkyDailyCommandParser.Command.OpenApp ||
            daily is SkyDailyCommandParser.Command.WebSearch) {
            notifyState("Orden pendiente · tocá para continuar", command)
            say("Te escuché. Para abrir esa aplicación, desbloquea el teléfono " +
                "y toca la notificación de SKY. La orden está preparada.")
            return
        }
        notifyState("Consulta pendiente · tocá para continuar", command)
        say("Te escuché. Abre SKY desde la notificación para continuar esa tarea.")
    }

    private fun setPresence(mode: SkyVoicePresence.Mode) {
        presence = mode
        voiceSettings.edit().putString("sky_presence_mode", mode.name).apply()
    }

    private fun process(heard: String) {
        if (!running) return
        val request = SkyVoicePresence.request(heard)
        if (request == SkyVoicePresence.Request.SLEEP) {
            pendingBackgroundCommand = null
            setPresence(SkyVoicePresence.Mode.SLEEP_LOCKED)
            awake = false
            handler.removeCallbacks(fallAsleep)
            onStatus?.invoke(true)
            notifyState("SKY dormida por tu orden · decí SKY despierta")
            say("Entendido. Me quedo dormida hasta que me digás SKY despierta.")
            return
        }
        if (presence == SkyVoicePresence.Mode.SLEEP_LOCKED &&
            request != SkyVoicePresence.Request.WAKE) {
            // Never treat unrelated sounds or a generic SKY as authorization.
            schedule(750)
            return
        }
        if (request == SkyVoicePresence.Request.CANCEL) {
            pendingBackgroundCommand = null
            say("Entendido. Cancelé esa orden.")
            return
        }
        if (request == SkyVoicePresence.Request.CONFIRM) {
            val pending = pendingBackgroundCommand
            pendingBackgroundCommand = null
            if (pending != null && SystemClock.elapsedRealtime() <= pendingExpiresAt) {
                handleWithoutVisibleUi(pending)
            } else say("No hay ninguna orden pendiente de confirmación.")
            return
        }
        if (request == SkyVoicePresence.Request.ATTEND) {
            setPresence(SkyVoicePresence.Mode.ATTENTIVE)
            awake = true
            resetInactivity()
            onStatus?.invoke(false)
            notifyState("SKY atenta · esperando tus órdenes")
            say("Te escuché. Estoy atenta a tus orientaciones. Las acciones sensibles requieren tu confirmación.")
            return
        }
        if (request == SkyVoicePresence.Request.WAKE) {
            setPresence(SkyVoicePresence.Mode.WAKE_ONLY)
            awake = true
            resetInactivity()
            onStatus?.invoke(false)
            notifyState("SKY despierta · escuchando")
            say("Aquí estoy. Te escucho.")
            return
        }
        val decision = SkyWakePhrase.decide(heard, awake)
        when (decision.kind) {
                SkyWakePhrase.Kind.IGNORE -> schedule(650)
                SkyWakePhrase.Kind.SLEEP -> {
                    setPresence(SkyVoicePresence.Mode.SLEEP_LOCKED)
                    awake = false
                    handler.removeCallbacks(fallAsleep)
                    onStatus?.invoke(true)
                    notifyState("SKY dormida · decí SKY despierta")
                    say("Entendido, quedo dormida hasta tu orden de despertar.")
                }
                SkyWakePhrase.Kind.WAKE -> {
                    if (presence == SkyVoicePresence.Mode.SLEEP_LOCKED) {
                        schedule(650)
                        return
                    }
                    awake = true
                    resetInactivity()
                    onStatus?.invoke(false)
                    notifyState("SKY está escuchándote")
                    if (onWake != null) {
                        suspendForSpeech()
                        onWake?.invoke()
                    } else say("Aquí estoy. Decime.")
                }
                SkyWakePhrase.Kind.COMMAND -> {
                    awake = true
                    resetInactivity()
                    val callback = onPhrase
                    if (callback != null) {
                        suspendForSpeech()
                        callback.invoke(decision.command)
                    } else {
                        // Audio from the environment is not proof of speaker
                        // identity: repeat and require a second explicit command
                        // before executing even low-risk background controls.
                        pendingBackgroundCommand = decision.command
                        pendingExpiresAt = SystemClock.elapsedRealtime() + 20_000L
                        notifyState("Orden escuchada · confirmación necesaria")
                        say("Escuché: " + decision.command.take(140) +
                            ". Si estás de acuerdo, decí SKY confirmo. " +
                            "Para cancelarla, decí SKY cancela.")
                    }
                }
        }
    }

    override fun onDestroy() {
        pendingBackgroundCommand = null
        running = false
        handler.removeCallbacksAndMessages(null)
        stopRecognizer()
        tts?.stop()
        tts?.shutdown()
        tts = null
        if (current === this) current = null
        super.onDestroy()
    }
}
