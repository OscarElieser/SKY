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
 * Dos ojos y una boca animados, sin rostro ni máscara.
 * Ocupan la altura útil y expresan estados reales del motor
 * de voz: escucha, respuesta, pensamiento y error. No transmite audio.
 */
class SkyFriendlyEyesView(context: Context) : View(context) {
    private enum class Emotion { CALM, HAPPY, CURIOUS, SURPRISED, LOVING, SLEEPY, SAD, CRYING, ANGRY, EXCITED, SHY }

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
        contentDescription = "Ojos y boca animados de SKY. Tocá para cambiar su expresión."
        isClickable = true
        importantForAccessibility = IMPORTANT_FOR_ACCESSIBILITY_YES
    }

    fun nextEmotion(): String {
        val sequence = arrayOf(
            Emotion.HAPPY, Emotion.CURIOUS, Emotion.SURPRISED,
            Emotion.LOVING, Emotion.EXCITED, Emotion.SHY, Emotion.SAD,
            Emotion.CRYING, Emotion.ANGRY, Emotion.SLEEPY, Emotion.CALM
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
            Emotion.CALM -> "Aquí estoy para ti. 💙"
            Emotion.SAD -> "Expresión de tristeza. Estoy contigo. 💙"
            Emotion.CRYING -> "Ojitos llorosos de SKY. 💧"
            Emotion.ANGRY -> "SKY pone carita de enojo. 😠"
            Emotion.EXCITED -> "¡Qué emoción! ✨"
            Emotion.SHY -> "Una sonrisa tímida. 🌸"
        }
    }

    fun showExpression(value: String): String {
        val clean = java.text.Normalizer.normalize(
            value.lowercase(Locale.ROOT), java.text.Normalizer.Form.NFD
        ).replace(Regex("""\p{M}+"""), "")
        emotion = when {
            "llora" in clean || "llanto" in clean || "lagrima" in clean -> Emotion.CRYING
            "triste" in clean || "pena" in clean || "melancol" in clean -> Emotion.SAD
            "enoj" in clean || "molest" in clean || "furios" in clean -> Emotion.ANGRY
            "timid" in clean || "vergonz" in clean -> Emotion.SHY
            "sorprend" in clean || "sorpresa" in clean || "asombr" in clean -> Emotion.SURPRISED
            "emocion" in clean || "entusiasm" in clean || "eufor" in clean -> Emotion.EXCITED
            "amor" in clean || "carino" in clean || "quiero" in clean -> Emotion.LOVING
            "feliz" in clean || "alegre" in clean || "sonri" in clean || "risa" in clean -> Emotion.HAPPY
            "sueno" in clean || "dormi" in clean -> Emotion.SLEEPY
            else -> Emotion.CURIOUS
        }
        emotionUntil = SystemClock.uptimeMillis() + 6500L
        invalidate()
        return "SKY muestra una expresión de " + emotion.name.lowercase(Locale.ROOT) + "."
    }

    fun reactTo(text: String) {
        val clean = java.text.Normalizer.normalize(
            text.lowercase(Locale.ROOT), java.text.Normalizer.Form.NFD
        ).replace(Regex("""\p{M}+"""), "")
        when {
            "llora" in clean || "llanto" in clean || "lagrima" in clean ||
                "triste" in clean || "alegre" in clean || "feliz" in clean ||
                "enoj" in clean || "emocion" in clean || "sonri" in clean ||
                "te quiero" in clean || "sorpresa" in clean || "sorprend" in clean ||
                "hola" in clean || "gracias" in clean -> showExpression(clean)
        }
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
            Emotion.HAPPY, Emotion.EXCITED -> 0.87f
            Emotion.SAD, Emotion.CRYING, Emotion.SHY -> 0.73f
            Emotion.ANGRY -> 0.62f
            else -> 1f
        }
        val halfHeight = 69f * open * (1f - blink * 0.97f)
        val radius = 38f
        // Floating, softly rounded eyes: no robotic square frames.
        fill(Color.rgb(23, 18, 67), 105)
        canvas.drawOval(x - 67f, y - halfHeight + 8f,
            x + 67f, y + halfHeight + 12f, brush)
        brush.shader = LinearGradient(x, y - 80f, x, y + 80f,
            Color.WHITE, Color.rgb(212, 220, 251), Shader.TileMode.CLAMP)
        brush.style = Paint.Style.FILL
        canvas.drawOval(x - 65f, y - halfHeight, x + 65f, y + halfHeight, brush)
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
            "SLEEPING" -> Emotion.SLEEPY
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
        // The entire screen is the stage. Only the eyes and mouth are visible;
        // no outline, head, facial frame, nose or cheeks.
        canvas.save()
        canvas.translate(0f, (sin(t * 1.25) * 4.5).toFloat())
        light(canvas, 180f, 310f, 163f, Color.rgb(122, 92, 238), 36)

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
        if (mood == Emotion.CRYING || mood == Emotion.SAD) {
            fill(Color.rgb(112, 218, 250), if (mood == Emotion.CRYING) 245 else 180)
            val drop = (now % 1300L) / 1300f
            canvas.drawOval(92f, 325f + drop * 75f, 107f, 350f + drop * 75f, brush)
            if (mood == Emotion.CRYING)
                canvas.drawOval(257f, 327f + drop * 70f, 270f, 349f + drop * 70f, brush)
        }
        if (mood == Emotion.SHY) {
            light(canvas, 45f, 380f, 30f, Color.rgb(255, 130, 173), 126)
            light(canvas, 315f, 380f, 30f, Color.rgb(255, 130, 173), 126)
        }

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
            mood == Emotion.SAD || mood == Emotion.CRYING -> {
                outline(Color.rgb(165, 220, 255), 7f)
                canvas.drawArc(147f, 463f, 213f, 513f, 190f, 160f, false, brush)
            }
            mood == Emotion.ANGRY -> {
                outline(Color.rgb(255, 180, 180), 7f)
                canvas.drawLine(153f, 486f, 207f, 486f, brush)
            }
            mood == Emotion.SURPRISED || speaking -> {
                fill(Color.rgb(41, 29, 94))
                canvas.drawOval(154f, 453f - talkOpen * 0.34f,
                    206f, 492f + talkOpen * 0.72f, brush)
                fill(Color.rgb(243, 142, 192))
                canvas.drawOval(169f, 481f + talkOpen * 0.2f,
                    191f, 490f + talkOpen * 0.55f, brush)
            }
            mood == Emotion.HAPPY || mood == Emotion.LOVING || mood == Emotion.EXCITED || mood == Emotion.SHY -> {
                outline(Color.rgb(241, 214, 255), 7f)
                canvas.drawArc(138f, 441f, 222f, 503f, 8f, 168f, false, brush)
            }
            else -> {
                // Small warm smile, even at idle.
                outline(Color.rgb(245, 204, 255), 7f)
                shape.reset()
                shape.moveTo(144f, 455f)
                shape.quadTo(180f, 490f, 216f, 455f)
                canvas.drawPath(shape, brush)
            }
        }
        if (mood == Emotion.SURPRISED || mood == Emotion.EXCITED || speaking) {
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
