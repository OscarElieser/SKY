package ni.sky.mobileagent

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RectF
import android.os.SystemClock
import android.view.View
import java.util.Locale
import kotlin.math.abs
import kotlin.math.min
import kotlin.math.sin

/**
 * Mascota SKY: dos ojos de caricatura con gestos positivos, sonrisa, rubor y
 * animación suave. No usa ojos realistas, imágenes fijas ni recursos externos.
 *
 * El estado de voz proviene del panel existente. Las emociones adicionales
 * son reacciones de interfaz, no afirmaciones de sentimientos de la IA.
 */
class SkyFriendlyEyesView(context: Context) : View(context) {
    private enum class Emotion { CALM, HAPPY, CURIOUS, SURPRISED, LOVING, SLEEPY }

    var mode: String = "IDLE"
        set(value) { field = value; invalidate() }
    var amplitude: Float = 0f
        set(value) { field = value.coerceIn(0f, 1f); invalidate() }

    private val brush = Paint(Paint.ANTI_ALIAS_FLAG)
    private val line = Path()
    private val oval = RectF()
    private var emotion = Emotion.CALM
    private var until = 0L
    private var touchIndex = 0

    init {
        contentDescription = "Ojitos animados y amistosos de SKY. Tocá para cambiar su expresión."
        isClickable = true
    }

    fun nextEmotion(): String {
        val set = arrayOf(
            Emotion.HAPPY, Emotion.CURIOUS, Emotion.SURPRISED,
            Emotion.LOVING, Emotion.SLEEPY, Emotion.CALM
        )
        emotion = set[touchIndex % set.size]
        touchIndex++
        until = SystemClock.uptimeMillis() + 4200L
        invalidate()
        return when (emotion) {
            Emotion.HAPPY -> "¡Qué alegría verte! 😊"
            Emotion.CURIOUS -> "¡Qué curioso! 🤔"
            Emotion.SURPRISED -> "¡Guau! ¡Qué sorpresa! ✨"
            Emotion.LOVING -> "¡Un abrazo virtual! 💜"
            Emotion.SLEEPY -> "Mis ojitos descansan un momento… 😴"
            Emotion.CALM -> "Aquí estoy para vos. 💙"
        }
    }

    fun reactTo(text: String) {
        val t = text.trim().lowercase(Locale.ROOT)
        emotion = when {
            "te quiero" in t || "te amo" in t -> Emotion.LOVING
            "sorpresa" in t || "increíble" in t -> Emotion.SURPRISED
            "hola" in t || "gracias" in t || "buenos días" in t -> Emotion.HAPPY
            else -> return
        }
        until = SystemClock.uptimeMillis() + 3600L
        invalidate()
    }

    private fun fill(color: Int, opacity: Int = 255) {
        brush.style = Paint.Style.FILL
        brush.color = color
        brush.alpha = opacity
        brush.shader = null
    }

    private fun stroke(color: Int, width: Float) {
        brush.style = Paint.Style.STROKE
        brush.strokeCap = Paint.Cap.ROUND
        brush.strokeJoin = Paint.Join.ROUND
        brush.strokeWidth = width
        brush.color = color
        brush.alpha = 255
        brush.shader = null
    }

    private fun eye(canvas: Canvas, x: Float, y: Float, look: Float,
                    blink: Float, emotion: Emotion, accent: Int) {
        val height = when (emotion) {
            Emotion.SLEEPY -> 13f
            Emotion.SURPRISED -> 47f
            else -> 39f
        } * (1f - 0.94f * blink)
        fill(Color.rgb(187, 194, 227), 100)
        canvas.drawRoundRect(x - 42f, y - height + 3f, x + 42f,
            y + height + 5f, 30f, 30f, brush)
        fill(Color.WHITE)
        canvas.drawRoundRect(x - 42f, y - height, x + 42f,
            y + height, 32f, 32f, brush)
        if (height < 14f) {
            stroke(Color.rgb(105, 106, 165), 4f)
            canvas.drawLine(x - 22f, y, x + 22f, y, brush)
        } else {
            val pupilY = y - if (mode == "THINKING") 10f else 0f
            fill(accent)
            canvas.drawCircle(x + look, pupilY, 23f, brush)
            fill(Color.rgb(58, 73, 128))
            canvas.drawCircle(x + look, pupilY + 1f, 11f, brush)
            fill(Color.WHITE)
            canvas.drawCircle(x + look - 8f, pupilY - 9f, 6f, brush)
            canvas.drawCircle(x + look + 7f, pupilY + 7f, 3f, brush)
        }
        val eyebrowY = y - 52f - if (emotion == Emotion.SURPRISED) 6f else 0f
        line.reset()
        line.moveTo(x - 24f, eyebrowY + 4f)
        line.quadTo(x, eyebrowY - 6f, x + 24f, eyebrowY + 4f)
        stroke(Color.rgb(189, 178, 248), 4f)
        canvas.drawPath(line, brush)
    }

    private fun sparkle(canvas: Canvas, x: Float, y: Float, radius: Float, color: Int) {
        stroke(color, 3f)
        canvas.drawLine(x - radius, y, x + radius, y, brush)
        canvas.drawLine(x, y - radius, x, y + radius, brush)
        fill(color)
        canvas.drawCircle(x, y, 3f, brush)
    }

    private fun heart(canvas: Canvas, x: Float, y: Float, size: Float) {
        canvas.save()
        canvas.translate(x, y)
        canvas.scale(size, size)
        line.reset()
        line.moveTo(0f, 17f)
        line.cubicTo(-29f, 0f, -18f, -17f, 0f, -7f)
        line.cubicTo(18f, -17f, 29f, 0f, 0f, 17f)
        line.close()
        fill(Color.rgb(247, 127, 168))
        canvas.drawPath(line, brush)
        canvas.restore()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        if (width < 2 || height < 2) return
        val now = SystemClock.uptimeMillis()
        val seconds = now / 1000.0
        val pulse = ((sin(seconds * 3.0) + 1.0) * 0.5).toFloat()
        val mood = when (mode) {
            "LISTENING", "THINKING", "ERROR" -> Emotion.CURIOUS
            "SPEAKING" -> if (now < until) emotion else Emotion.HAPPY
            else -> if (now < until) emotion else Emotion.CALM
        }
        val accent = when (mode) {
            "LISTENING" -> Color.rgb(51, 191, 197)
            "THINKING" -> Color.rgb(147, 130, 224)
            "SPEAKING" -> Color.rgb(57, 186, 239)
            "ERROR" -> Color.rgb(228, 156, 124)
            else -> Color.rgb(105, 155, 231)
        }

        val scale = min(width / 360f, height / 220f)
        canvas.save()
        canvas.translate((width - 360f * scale) / 2f, (height - 220f * scale) / 2f)
        canvas.scale(scale, scale)
        canvas.translate(0f, (sin(seconds * 1.5) * 2.4).toFloat())

        // Rostro virtual libre y flotante: sin carcasa rectangular ni
        // efecto robótico. Una luz suave acompaña sus expresiones.
        fill(Color.rgb(102, 76, 202), 32)
        canvas.drawOval(39f, 23f, 321f, 203f, brush)
        fill(accent, 22 + (pulse * 18f).toInt())
        canvas.drawOval(57f, 34f, 303f, 194f, brush)

        val blinkMs = now % 5400L
        val blinking = if (blinkMs in 5080L..5310L) {
            val p = (blinkMs - 5080L) / 230f
            1f - abs(2f * p - 1f)
        } else 0f
        val gaze = when (mode) {
            "LISTENING" -> amplitude * 7f
            "THINKING" -> -8f
            else -> (sin(seconds * 0.65) * 5.5).toFloat()
        }
        eye(canvas, 125f, 100f, gaze, blinking, mood, accent)
        eye(canvas, 235f, 100f, gaze,
            if (mood == Emotion.LOVING && mode == "IDLE") 1f else blinking,
            mood, accent)

        fill(Color.rgb(255, 163, 193), 105 + (pulse * 18f).toInt())
        canvas.drawOval(60f, 132f, 100f, 149f, brush)
        canvas.drawOval(260f, 132f, 300f, 149f, brush)

        when {
            mode == "ERROR" -> {
                // Duda suave y amistosa, nunca gesto agresivo.
                stroke(Color.rgb(209, 185, 239), 4f)
                canvas.drawArc(165f, 164f, 195f, 183f, 203f, 134f, false, brush)
            }
            mood == Emotion.SLEEPY -> {
                stroke(Color.rgb(206, 188, 237), 4f)
                canvas.drawLine(170f, 171f, 190f, 171f, brush)
            }
            mood == Emotion.SURPRISED ||
                (mode == "SPEAKING" && sin(seconds * 10) > -0.20) -> {
                fill(Color.rgb(109, 103, 167))
                oval.set(167f, 155f, 193f, 185f)
                canvas.drawOval(oval, brush)
                fill(Color.rgb(255, 172, 202))
                canvas.drawOval(172f, 173f, 188f, 181f, brush)
            }
            else -> {
                stroke(Color.rgb(222, 198, 250), 5f)
                canvas.drawArc(157f, 145f, 203f, 182f, 10f, 160f, false, brush)
            }
        }
        if (mood == Emotion.LOVING) {
            // Unos lentes juguetones aparecen únicamente cuando SKY
            // hace el gesto cariñoso; desaparecen automáticamente.
            stroke(Color.rgb(48, 35, 90), 5.5f)
            canvas.drawRoundRect(79f, 65f, 174f, 143f, 23f, 23f, brush)
            canvas.drawRoundRect(186f, 65f, 281f, 143f, 23f, 23f, brush)
            canvas.drawLine(174f, 83f, 186f, 83f, brush)
            heart(canvas, 127f, 105f, 0.65f)
            heart(canvas, 235f, 105f, 0.65f)
            heart(canvas, 301f, 40f, 0.65f)
            heart(canvas, 55f, 52f, 0.40f)
        }
        if (mood == Emotion.SURPRISED || mode == "SPEAKING") {
            sparkle(canvas, 317f, 43f, 9f + pulse * 3f, Color.rgb(245, 175, 78))
            sparkle(canvas, 43f, 71f, 7f + pulse * 2f, Color.rgb(131, 156, 237))
        }
        if (mode == "THINKING") {
            fill(Color.rgb(139, 139, 216))
            for (i in 0..2) {
                val bob = (sin(seconds * 4.0 + i) * 3f).toFloat()
                canvas.drawCircle(160f + i * 20f, 24f + bob, 3.5f, brush)
            }
        }

        canvas.restore()
        if (isShown) postInvalidateDelayed(66L)
    }
}
