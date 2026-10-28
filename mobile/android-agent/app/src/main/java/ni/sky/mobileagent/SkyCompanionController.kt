package ni.sky.mobileagent

import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import android.os.Handler
import android.os.Looper
import kotlin.math.PI
import kotlin.math.sin

/**
 * Acompañamiento opt-in: pequeñas frases originales y un silbido sintetizado.
 * La voz es únicamente EN PRIMER PLANO; se detiene al salir de la aplicación.
 */
class SkyCompanionController(private val say: (String) -> Unit) {
    val brain = SkyCompanionBrain()
    private val handler = Handler(Looper.getMainLooper())
    private var foreground = false
    private var checkIns = 0
    private var lastWhistle = 0L

    private val prompt = object : Runnable {
        override fun run() {
            if (!foreground || brain.mode == SkyCompanionBrain.Mode.OFF) return
            if (checkIns >= 6) return // evita hablar indefinidamente sin interacción
            checkIns++
            brain.nextCheckIn()?.let(say)
            handler.postDelayed(this, 4 * 60 * 1000L)
        }
    }

    fun handle(text: String): Boolean {
        val reply = brain.answer(text) ?: return false
        handler.removeCallbacks(prompt)
        checkIns = 0
        if (reply.whistle) {
            whistle()
            handler.postDelayed({ if (foreground) say(reply.spoken) }, 1100L)
        } else {
            say(reply.spoken)
        }
        if (foreground && brain.mode != SkyCompanionBrain.Mode.OFF) {
            handler.postDelayed(prompt, 4 * 60 * 1000L)
        }
        return true
    }

    fun onResume() {
        foreground = true
        if (brain.mode != SkyCompanionBrain.Mode.OFF) {
            handler.removeCallbacks(prompt)
            handler.postDelayed(prompt, 4 * 60 * 1000L)
        }
    }

    fun onPause() {
        foreground = false
        handler.removeCallbacks(prompt)
    }

    fun close() = onPause()

    private fun whistle() {
        val now = android.os.SystemClock.elapsedRealtime()
        if (now - lastWhistle < 2500L) return
        lastWhistle = now
        // Sonido original: sintetizador de seno, no grabaciones ni música ajena.
        Thread({
            val sampleRate = 22050
            val pitches = doubleArrayOf(784.0, 988.0, 880.0, 1175.0)
            val notes = 0.18
            val pause = 0.045
            val totalSamples = ((notes + pause) * pitches.size * sampleRate).toInt()
            val samples = ShortArray(totalSamples)
            for (i in samples.indices) {
                val t = i.toDouble() / sampleRate
                val cycle = (t / (notes + pause)).toInt()
                if (cycle !in pitches.indices) continue
                val pos = t % (notes + pause)
                if (pos >= notes) continue
                val fadeIn = (pos / 0.025).coerceIn(0.0, 1.0)
                val fadeOut = ((notes - pos) / 0.035).coerceIn(0.0, 1.0)
                val envelope = minOf(fadeIn, fadeOut)
                samples[i] = (sin(2 * PI * pitches[cycle] * pos) * envelope *
                    9500.0).toInt().toShort()
            }
            var track: AudioTrack? = null
            try {
                track = AudioTrack.Builder()
                    .setAudioAttributes(AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_ASSISTANCE_SONIFICATION)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION).build())
                    .setAudioFormat(AudioFormat.Builder()
                        .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                        .setSampleRate(sampleRate)
                        .setChannelMask(AudioFormat.CHANNEL_OUT_MONO).build())
                    .setBufferSizeInBytes(samples.size * 2)
                    .setTransferMode(AudioTrack.MODE_STATIC)
                    .build()
                if (track.write(samples, 0, samples.size) > 0) {
                    track.play()
                    Thread.sleep(((notes + pause) * pitches.size * 1000 + 120).toLong())
                    track.stop()
                }
            } catch (_: Exception) {
                // Sin salida de audio, continuar con la conversación por voz.
            } finally {
                track?.release()
            }
        }, "sky-original-whistle").start()
    }
}
