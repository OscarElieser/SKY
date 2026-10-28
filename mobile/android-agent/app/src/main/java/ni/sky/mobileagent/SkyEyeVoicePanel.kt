package ni.sky.mobileagent

import android.Manifest
import android.app.Activity
import android.content.pm.PackageManager
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.os.Bundle
import android.os.SystemClock
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.content.Intent
import android.view.View
import android.widget.Button
import android.widget.CheckBox
import android.widget.LinearLayout
import android.widget.TextView
import java.util.Locale
import kotlin.math.min
import kotlin.math.sin

/**
 * Ojo e interacción de voz para el chat existente de SKY.
 *
 * La escucha es explícita: un toque, un turno de reconocimiento.
 * No instala escucha permanente ni obtiene control adicional del teléfono.
 * El reconocedor del sistema puede usar servidores externos según su proveedor.
 */
class SkyEyeVoicePanel(
    private val host: Activity,
    private val onTranscript: (String) -> Unit
) : LinearLayout(host) {
    companion object {
        const val MICROPHONE_REQUEST = 1614
    }

    private enum class EyeMode { IDLE, LISTENING, THINKING, SPEAKING, ERROR }

    private val eye = SkyFriendlyEyesView(host)
    private val message = TextView(host)
    private val readAloud = CheckBox(host)
    private var recognizer: SpeechRecognizer? = null
    private var speechEngine: TextToSpeech? = null
    private var speechReady = false
    private var listening = false

    init {
        orientation = VERTICAL
        setBackgroundColor(Color.rgb(247, 245, 255))
        setPadding(dp(16), dp(12), dp(16), dp(14))
        addView(TextView(host).apply {
            text = "SKY  •  ASISTENTE DE VOZ"
            textSize = 18f
            setTextColor(Color.rgb(51, 59, 104))
            gravity = android.view.Gravity.CENTER
        })
        addView(eye, LayoutParams(LayoutParams.MATCH_PARENT, dp(220)))
        eye.setOnClickListener {
            val reaction = eye.nextEmotion()
            message.text = reaction
            if (readAloud.isChecked && !listening && !chatPending) {
                speakReply(reaction)
            }
        }
        addView(TextView(host).apply {
            text = "Tocá los ojitos de SKY para descubrir sus gestos ✨"
            textSize = 12f
            setTextColor(Color.rgb(103, 89, 164))
            gravity = android.view.Gravity.CENTER
        })
        addView(message.apply {
            text = "SKY lista. Tocá «Hablar con SKY»."
            textSize = 15f
            setTextColor(Color.rgb(74, 84, 139))
            gravity = android.view.Gravity.CENTER
            setPadding(0, 0, 0, dp(8))
        })
        val controls = LinearLayout(host).apply { orientation = HORIZONTAL }
        controls.addView(Button(host).apply {
            text = "Hablar con SKY"
            setOnClickListener { listen() }
        }, LayoutParams(0, LayoutParams.WRAP_CONTENT, 1f))
        controls.addView(Button(host).apply {
            text = "Detener"
            setOnClickListener { stop() }
        }, LayoutParams(0, LayoutParams.WRAP_CONTENT, 1f))
        addView(controls)
        addView(readAloud.apply {
            text = "SKY responde con voz"
            setTextColor(Color.WHITE)
            isChecked = true
        })
        addView(TextView(host).apply {
            text = "El micrófono solo se activa al tocar Hablar. La voz depende del motor instalado en Android."
            textSize = 12f
            setTextColor(Color.rgb(110, 113, 150))
        })

        speechEngine = TextToSpeech(host) { state ->
            if (state == TextToSpeech.SUCCESS) {
                val result = speechEngine?.setLanguage(Locale("es", "NI"))
                    ?: TextToSpeech.LANG_NOT_SUPPORTED
                if (result == TextToSpeech.LANG_MISSING_DATA ||
                    result == TextToSpeech.LANG_NOT_SUPPORTED) {
                    speechEngine?.language = Locale("es", "ES")
                }
                speechEngine?.setSpeechRate(0.97f)
                speechEngine?.setPitch(1.0f)
                speechReady = true
            } else {
                host.runOnUiThread { setMode(EyeMode.ERROR, "Voz no disponible en Android.") }
            }
        }
        speechEngine?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onStart(utteranceId: String) {
                host.runOnUiThread { setMode(EyeMode.SPEAKING, "SKY está hablando…") }
            }
            override fun onDone(utteranceId: String) {
                host.runOnUiThread { setMode(EyeMode.IDLE, "SKY lista para escucharte.") }
            }
            override fun onError(utteranceId: String) {
                host.runOnUiThread { setMode(EyeMode.ERROR, "No fue posible reproducir la voz.") }
            }
        })
    }

    private fun dp(value: Int) = (value * resources.displayMetrics.density + 0.5f).toInt()

    private fun setMode(mode: EyeMode, label: String) {
        eye.mode = mode.name
        message.text = label
    }

    fun showThinking() = setMode(EyeMode.THINKING, "SKY está preparando su respuesta…")

    fun showError(label: String) = setMode(EyeMode.ERROR, label)

    fun speakReply(text: String) {
        if (!readAloud.isChecked) {
            setMode(EyeMode.IDLE, "Respuesta disponible en el chat.")
            return
        }
        if (!speechReady) {
            setMode(EyeMode.IDLE, "Respuesta recibida. El motor de voz no está listo.")
            return
        }
        // El motor TTS de Android acepta una cantidad limitada de caracteres por turno.
        val clean = text.trim().take(min(3500, TextToSpeech.getMaxSpeechInputLength() - 1))
        if (clean.isBlank()) {
            setMode(EyeMode.IDLE, "Respuesta vacía.")
            return
        }
        val result = speechEngine?.speak(
            clean,
            TextToSpeech.QUEUE_FLUSH,
            Bundle(),
            "sky-eye-" + SystemClock.uptimeMillis()
        )
        if (result != TextToSpeech.SUCCESS) {
            setMode(EyeMode.ERROR, "Android no pudo iniciar la voz.")
        }
    }

    fun listen() {
        if (host.checkSelfPermission(Manifest.permission.RECORD_AUDIO) !=
            PackageManager.PERMISSION_GRANTED) {
            host.requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), MICROPHONE_REQUEST)
            return
        }
        if (listening) return
        if (!SpeechRecognizer.isRecognitionAvailable(host)) {
            setMode(EyeMode.ERROR, "No hay reconocimiento de voz disponible en este teléfono.")
            return
        }
        speechEngine?.stop()
        recognizer?.destroy()
        recognizer = null
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "es-NI")
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
        }
        try {
            val engine = SpeechRecognizer.createSpeechRecognizer(host)
            recognizer = engine
            engine.setRecognitionListener(object : RecognitionListener {
                override fun onReadyForSpeech(params: Bundle?) {
                    setMode(EyeMode.LISTENING, "Te escucho…")
                }
                override fun onBeginningOfSpeech() {
                    setMode(EyeMode.LISTENING, "Escuchando tu voz…")
                }
                override fun onRmsChanged(rmsdB: Float) {
                    eye.amplitude = ((rmsdB + 2f) / 13f).coerceIn(0f, 1f)
                }
                override fun onBufferReceived(buffer: ByteArray?) {}
                override fun onEndOfSpeech() {
                    setMode(EyeMode.THINKING, "Interpretando lo que dijiste…")
                }
                override fun onError(error: Int) {
                    listening = false
                    setMode(EyeMode.ERROR, "No pude escucharte bien. Tocá Hablar para intentar otra vez.")
                }
                override fun onResults(results: Bundle?) {
                    listening = false
                    val heard = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                        ?.firstOrNull()?.trim().orEmpty()
                    if (heard.isEmpty()) {
                        setMode(EyeMode.IDLE, "No detecté palabras. Intentá otra vez.")
                    } else {
                        eye.reactTo(heard)
                        showThinking()
                        onTranscript(heard)
                    }
                }
                override fun onPartialResults(partialResults: Bundle?) {
                    val partial = partialResults
                        ?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                        ?.firstOrNull().orEmpty()
                    if (partial.isNotBlank()) {
                        setMode(EyeMode.LISTENING, "Te escucho: " + partial.take(85))
                    }
                }
                override fun onEvent(eventType: Int, params: Bundle?) {}
            })
            listening = true
            setMode(EyeMode.LISTENING, "Activando micrófono…")
            engine.startListening(intent)
        } catch (_: Exception) {
            listening = false
            recognizer?.destroy()
            recognizer = null
            setMode(EyeMode.ERROR, "No se pudo activar el reconocimiento de voz.")
        }
    }

    fun onMicrophonePermissionResult(granted: Boolean) {
        if (granted) listen()
        else setMode(EyeMode.ERROR, "Sin permiso de micrófono. Podés continuar escribiendo.")
    }

    fun stop() {
        listening = false
        recognizer?.cancel()
        speechEngine?.stop()
        setMode(EyeMode.IDLE, "Voz detenida. SKY lista.")
    }

    fun onPausePanel() {
        if (listening) {
            listening = false
            recognizer?.cancel()
            setMode(EyeMode.IDLE, "Escucha detenida al salir de la aplicación.")
        }
    }

    fun close() {
        recognizer?.destroy()
        recognizer = null
        speechEngine?.stop()
        speechEngine?.shutdown()
        speechEngine = null
        speechReady = false
    }

    private class SkyEyeView(host: Activity) : View(host) {
        var mode: EyeMode = EyeMode.IDLE
            set(value) { field = value; invalidate() }
        var amplitude = 0f
        private val pen = Paint(Paint.ANTI_ALIAS_FLAG)
        init { contentDescription = "Ojo animado de SKY que indica su estado de voz" }

        override fun onDraw(canvas: Canvas) {
            super.onDraw(canvas)
            val cx = width / 2f
            val cy = height / 2f
            val radius = min(width, height) * 0.245f
            val seconds = SystemClock.uptimeMillis() / 1000.0
            val pulse = ((sin(seconds * 2.7) + 1.0) / 2.0).toFloat()
            val core = when (mode) {
                EyeMode.LISTENING -> Color.rgb(51, 239, 220)
                EyeMode.THINKING -> Color.rgb(153, 151, 255)
                EyeMode.SPEAKING -> Color.rgb(53, 220, 255)
                EyeMode.ERROR -> Color.rgb(255, 122, 127)
                EyeMode.IDLE -> Color.rgb(33, 178, 255)
            }
            for (index in 3 downTo 0) {
                pen.style = Paint.Style.STROKE
                pen.strokeWidth = 2f + index
                pen.color = core
                pen.alpha = (35 + (3 - index) * 25 + pulse * 20).toInt().coerceIn(0, 255)
                canvas.drawCircle(cx, cy, radius + index * 17f + pulse * 4f, pen)
            }
            pen.style = Paint.Style.FILL
            pen.color = core
            pen.alpha = 45
            canvas.drawCircle(cx, cy, radius * (0.79f + pulse * 0.05f), pen)
            pen.alpha = 255
            pen.color = Color.rgb(9, 25, 52)
            canvas.drawCircle(cx, cy, radius * 0.65f, pen)
            pen.color = core
            canvas.drawCircle(cx, cy, radius * (0.42f + (if (mode == EyeMode.LISTENING) amplitude * 0.1f else pulse * 0.02f)), pen)
            pen.color = Color.WHITE
            pen.alpha = 175
            canvas.drawCircle(cx - radius * 0.13f, cy - radius * 0.13f, radius * 0.105f, pen)
            postInvalidateDelayed(65)
        }
    }
}
