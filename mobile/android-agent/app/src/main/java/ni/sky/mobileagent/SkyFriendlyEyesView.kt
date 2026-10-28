package ni.sky.mobileagent

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.LinearGradient
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RadialGradient
import android.graphics.RectF
import android.graphics.Shader
import android.os.SystemClock
import android.view.View
import java.util.Locale
import kotlin.math.abs
import kotlin.math.min
import kotlin.math.sin

/**
 * SKY · Aura Face (Android).
 *
 * Rostro vectorial vertical, no robótico y sin imágenes externas.
 * Ocupa la altura útil completa y expresa estados reales del motor
 * de voz: escucha, respuesta, pensamiento y error. No transmite audio.
 */
class SkyFriendlyEyesView(context: Context) : View(context) {
    private enum class Emotion { CALM, HAPPY, CURIOUS, SURPRISED, LOVING, SLEEPY }

    var mode: String = "IDLE"
        set(value) { field = value; invalidate() }
    var amplitude: Float = 0f
        set(value) { field = value.coerceIn(0f, 1f); invalidate() }

    private val brush = Paint(Paint.ANTI_ALIAS_FLAG)
    private val shape = Path()
    private val bounds = RectF()
    private var emotion = Emotion.CALM
    private var emotionUntil = 0L
    private var touchCount = 0

    init {
        contentDescription = "Rostro animado de SKY. Tocá para descubrir nuevas expresiones."
        isClickable = true
        importantForAccessibility = IMPORTANT_FOR_ACCESSIBILITY_YES
    }

    fun nextEmotion(): String {
        val sequence = arrayOf(
            Emotion.HAPPY, Emotion.CURIOUS, Emotion.SURPRISED,
            Emotion.LOVING, Emotion.SLEEPY, Emotion.CALM
        )
        emotion = sequence[touchCount++ % sequence.size]
        emotionUntil = SystemClock.uptimeMillis() + 4500L
        invalidate()
        return when (emotion) {
            Emotion.HAPPY -> "¡Qué alegría verte! 😊"
            Emotion.CURIOUS -> "¡Contame más! 🤔"
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
        emotionUntil = SystemClock.uptimeMillis() + 4300L
        invalidate()
    }

    private fun fill(color: Int, alpha: Int = 255) {
        brush.shader = null
        brush.style = Paint.Style.FILL
        brush.color = color
        brush.alpha = alpha.coerceIn(0, 255)
    }

    private fun outline(color: Int, size: Float, alpha: Int = 255) {
        brush.shader = null
        brush.style = Paint.Style.STROKE
        brush.strokeWidth = size
        brush.strokeCap = Paint.Cap.ROUND
        brush.strokeJoin = Paint.Join.ROUND
        brush.color = color
        brush.alpha = alpha
    }

    private fun light(canvas: Canvas, x: Float, y: Float, radius: Float, color: Int, opacity: Int) {
        brush.style = Paint.Style.FILL
        brush.shader = RadialGradient(
            x, y, radius,
            intArrayOf(Color.argb(opacity, Color.red(color), Color.green(color), Color.blue(color)),
                Color.TRANSPARENT),
            null, Shader.TileMode.CLAMP
        )
        canvas.drawCircle(x, y, radius, brush)
        brush.shader = null
    }

    private fun sparkle(canvas: Canvas, x: Float, y: Float, radius: Float, color: Int,
                        opacity: Int = 200) {
        outline(color, 2.2f, opacity)
        canvas.drawLine(x - radius, y, x + radius, y, brush)
        canvas.drawLine(x, y - radius, x, y + radius, brush)
        fill(Color.WHITE, opacity)
        canvas.drawCircle(x, y, 1.7f, brush)
    }

    private fun eyes(canvas: Canvas, x: Float, y: Float, look: Float, blink: Float,
                     mood: Emotion, iris: Int, speaking: Boolean) {
        val open = when (mood) {
            Emotion.SLEEPY -> 0.33f
            Emotion.SURPRISED -> 1.13f
            Emotion.HAPPY -> 0.87f
            else -> 1f
        }
        val halfHeight = 69f * open * (1f - blink * 0.97f)
        val radius = 38f
        fill(Color.rgb(10, 8, 44), 95)
        canvas.drawRoundRect(x - 61f, y - halfHeight + 9f,
            x + 61f, y + halfHeight + 13f, radius, radius, brush)
        brush.shader = LinearGradient(x, y - 70f, x, y + 70f,
            Color.WHITE, Color.rgb(212, 218, 249), Shader.TileMode.CLAMP)
        brush.style = Paint.Style.FILL
        canvas.drawRoundRect(x - 60f, y - halfHeight,
            x + 60f, y + halfHeight, radius, radius, brush)
        brush.shader = null
        if (halfHeight < 17f) {
            outline(Color.rgb(157, 133, 215), 5f)
            canvas.drawLine(x - 40f, y, x + 40f, y, brush)
        } else {
            val pupilY = y + if (mode == "THINKING") -18f else if (speaking) 3f else 0f
            light(canvas, x + look, pupilY + 7f, 45f, iris, 72)
            fill(iris)
            canvas.drawCircle(x + look, pupilY, 39f, brush)
            fill(Color.rgb(38, 33, 86))
            canvas.drawCircle(x + look, pupilY + 4f, 23f, brush)
            fill(Color.rgb(12, 15, 49))
            canvas.drawCircle(x + look, pupilY + 5f, 14f, brush)
            fill(Color.WHITE)
            canvas.drawCircle(x + look - 14f, pupilY - 15f, 12f, brush)
            canvas.drawCircle(x + look + 13f, pupilY + 15f, 5f, brush)
            fill(Color.WHITE, 132)
            canvas.drawCircle(x + look + 18f, pupilY - 17f, 3.5f, brush)
        }
        // Soft brows follow facial state instead of looking robotic.
        shape.reset()
        shape.moveTo(x - 45f, y - 109f)
        shape.quadTo(x, y - 131f - if (mood == Emotion.SURPRISED) 10f else 0f,
            x + 45f, y - 109f)
        outline(Color.rgb(194, 178, 254), 7f, 225)
        canvas.drawPath(shape, brush)
    }

    private fun heart(canvas: Canvas, x: Float, y: Float, radius: Float) {
        canvas.save()
        canvas.translate(x, y)
        canvas.scale(radius / 25f, radius / 25f)
        shape.reset()
        shape.moveTo(0f, 20f)
        shape.cubicTo(-33f, -4f, -20f, -27f, 0f, -12f)
        shape.cubicTo(20f, -27f, 33f, -4f, 0f, 20f)
        shape.close()
        fill(Color.rgb(255, 154, 198))
        canvas.drawPath(shape, brush)
        canvas.restore()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        if (width < 2 || height < 2) return
        val now = SystemClock.uptimeMillis()
        val t = now / 1000.0
        val pulse = ((sin(t * 2.2) + 1.0) / 2.0).toFloat()
        val speaking = mode == "SPEAKING"
        val mood = when (mode) {
            "LISTENING", "THINKING" -> Emotion.CURIOUS
            "ERROR" -> Emotion.CURIOUS
            else -> if (now < emotionUntil) emotion else
                if (speaking) Emotion.HAPPY else Emotion.CALM
        }
        val accent = when (mode) {
            "LISTENING" -> Color.rgb(69, 228, 214)
            "THINKING" -> Color.rgb(183, 155, 255)
            "SPEAKING" -> Color.rgb(113, 210, 255)
            "ERROR" -> Color.rgb(255, 163, 153)
            else -> Color.rgb(154, 142, 250)
        }
        // 360x590 portrait canvas instead of a tiny 360x220 horizontal drawing.
        val scale = min(width / 360f, height / 590f)
        canvas.save()
        canvas.translate((width - 360f * scale) / 2f, (height - 590f * scale) / 2f)
        canvas.scale(scale, scale)

        // Cosmic aura grows softly during listening and talking.
        val aura = 0.93f + pulse * 0.04f + if (mode == "LISTENING") amplitude * 0.05f else 0f
        light(canvas, 180f, 287f, 224f * aura, accent, 63)
        light(canvas, 70f, 194f, 95f, Color.rgb(113, 95, 247), 35)
        light(canvas, 306f, 423f, 108f, Color.rgb(49, 217, 225), 24)
        // Vertical avatar silhouette, soft organic face, not a robot casing.
        canvas.save()
        canvas.translate(0f, (sin(t * 1.25) * 4.5).toFloat())
        shape.reset()
        shape.moveTo(180f, 30f)
        shape.cubicTo(276f, 25f, 350f, 126f, 349f, 275f)
        shape.cubicTo(349f, 453f, 291f, 553f, 180f, 566f)
        shape.cubicTo(70f, 553f, 11f, 453f, 11f, 275f)
        shape.cubicTo(10f, 126f, 84f, 25f, 180f, 30f)
        shape.close()
        fill(Color.rgb(101, 78, 209), 28)
        brush.shader = LinearGradient(30f, 54f, 319f, 552f,
            intArrayOf(Color.rgb(85, 70, 158),
                Color.rgb(62, 48, 131), Color.rgb(45, 42, 106)),
            null, Shader.TileMode.CLAMP)
        canvas.drawPath(shape, brush)
        brush.shader = null
        outline(Color.rgb(167, 153, 253), 2.2f, 110)
        canvas.drawPath(shape, brush)
        light(canvas, 143f, 152f, 122f, Color.rgb(188, 157, 255), 40)
        light(canvas, 240f, 465f, 145f, Color.rgb(80, 180, 231), 22)

        // Expressive pupils track conversation state, blink naturally.
        val blinkMs = now % 4900L
        val blink = if (blinkMs in 4600L..4820L) {
            val p = (blinkMs - 4600L) / 220f
            1f - abs(2f * p - 1f)
        } else 0f
        val gaze = when (mode) {
            "LISTENING" -> amplitude * 11f
            "THINKING" -> -13f
            else -> (sin(t * 0.58) * 9.0).toFloat()
        }
        eyes(canvas, 112f, 290f, gaze, blink, mood, accent, speaking)
        eyes(canvas, 248f, 290f, gaze, if (mood == Emotion.LOVING) 0.3f else blink,
            mood, accent, speaking)

        // Blush + subtle nose make the character warm and approachable.
        fill(Color.rgb(255, 145, 184), 99 + (pulse * 31).toInt())
        canvas.drawOval(23f, 381f, 91f, 414f, brush)
        canvas.drawOval(269f, 381f, 337f, 414f, brush)
        fill(Color.rgb(240, 201, 252), 115)
        canvas.drawOval(170f, 407f, 190f, 421f, brush)

        val talkOpen = if (speaking) 12f + ((sin(t * 11.0) + 1) * 16f).toFloat() else 0f
        when {
            mode == "ERROR" -> {
                outline(Color.rgb(255, 203, 220), 6f)
                bounds.set(147f, 462f, 213f, 489f)
                canvas.drawArc(bounds, 194f, 155f, false, brush)
            }
            mood == Emotion.SLEEPY -> {
                outline(Color.rgb(229, 211, 250), 6f)
                canvas.drawLine(160f, 474f, 200f, 474f, brush)
            }
            mood == Emotion.SURPRISED || speaking -> {
                fill(Color.rgb(41, 29, 94))
                canvas.drawOval(154f, 453f - talkOpen * 0.34f,
                    206f, 492f + talkOpen * 0.72f, brush)
                fill(Color.rgb(243, 142, 192))
                canvas.drawOval(169f, 481f + talkOpen * 0.2f,
                    191f, 490f + talkOpen * 0.55f, brush)
            }
            mood == Emotion.HAPPY || mood == Emotion.LOVING -> {
                outline(Color.rgb(241, 214, 255), 7f)
                canvas.drawArc(138f, 441f, 222f, 503f, 8f, 168f, false, brush)
            }
            else -> {
                outline(Color.rgb(234, 204, 255), 6.5f)
                canvas.drawArc(152f, 450f, 208f, 499f, 20f, 140f, false, brush)
            }
        }
        if (mood == Emotion.LOVING) {
            heart(canvas, 306f, 170f, 18f)
            heart(canvas, 54f, 160f, 12f)
        }
        if (mood == Emotion.SURPRISED || speaking) {
            sparkle(canvas, 320f, 127f, 12f + pulse * 4f, Color.rgb(255, 210, 140))
        }
        if (mode == "THINKING") {
            for (i in 0..2) {
                fill(Color.rgb(207, 189, 255), 125 + i * 32)
                canvas.drawCircle(157f + i * 23f,
                    116f + (sin(t * 3.6 + i * 0.9) * 6.5).toFloat(), 4.8f, brush)
            }
        }
        canvas.restore()
        sparkle(canvas, 25f, 112f, 6.7f, Color.rgb(174, 165, 255), 165)
        sparkle(canvas, 336f, 479f, 7f, Color.rgb(93, 212, 230), 145)
        if (mode == "LISTENING" && amplitude > 0.05f) {
            outline(accent, 3f, (55 + amplitude * 80).toInt())
            canvas.drawArc(0f, 53f, 360f, 570f, 120f, 300f, false, brush)
        }
        canvas.restore()
        if (isShown && windowVisibility == VISIBLE) postInvalidateDelayed(65L)
    }
}
