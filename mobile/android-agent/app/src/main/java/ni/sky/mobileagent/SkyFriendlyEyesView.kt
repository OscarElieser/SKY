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
import kotlin.math.max
import kotlin.math.sin

/**
 * SKY · Aura Face (Android).
 *
 * Dos ojos y una boca animados, sin rostro ni máscara.
 * Ocupan la altura útil y expresan estados reales del motor
 * de voz: escucha, respuesta, pensamiento y error. No transmite audio.
 */
class SkyFriendlyEyesView(context: Context) : View(context) {

    var mode: String = "IDLE"
        set(value) { field = value; invalidate() }
    var amplitude: Float = 0f
        set(value) { field = value.coerceIn(0f, 1f); invalidate() }

    private val brush = Paint(Paint.ANTI_ALIAS_FLAG)
    private val shape = Path()
    private val bounds = RectF()
    private var emotion = SkyEmotionLexicon.Mood.CALM
    private var expressionChangedAt = 0L
    private var emotionUntil = 0L
    private var touchCount = 0

    init {
        contentDescription = "Ojos y boca animados de SKY. Tocá para cambiar su expresión."
        isClickable = true
        importantForAccessibility = IMPORTANT_FOR_ACCESSIBILITY_YES
    }

    fun nextEmotion(): String {
        val sequence = arrayOf(
            SkyEmotionLexicon.Mood.HAPPY, SkyEmotionLexicon.Mood.CURIOUS, SkyEmotionLexicon.Mood.SURPRISED,
            SkyEmotionLexicon.Mood.LOVING, SkyEmotionLexicon.Mood.EXCITED, SkyEmotionLexicon.Mood.SHY, SkyEmotionLexicon.Mood.SAD,
            SkyEmotionLexicon.Mood.CRYING, SkyEmotionLexicon.Mood.ANGRY, SkyEmotionLexicon.Mood.SLEEPY, SkyEmotionLexicon.Mood.CALM
        )
        emotion = sequence[touchCount++ % sequence.size]
        expressionChangedAt = SystemClock.uptimeMillis()
        emotionUntil = SystemClock.uptimeMillis() + 4500L
        invalidate()
        return SkyEmotionLexicon.message(emotion)
    }

    /** Aplica una emoción visible sin alterar el estado de voz, el chat ni los permisos. */
    fun showExpression(value: String): String {
        emotion = SkyEmotionLexicon.requested(value)
        expressionChangedAt = SystemClock.uptimeMillis()
        emotionUntil = expressionChangedAt + 7500L
        invalidate()
        return SkyEmotionLexicon.message(emotion)
    }

    /** El lenguaje explícito de una respuesta puede activar una expresión temporal. */
    fun reactTo(text: String) {
        SkyEmotionLexicon.dialogue(text)?.let { detected ->
            emotion = detected
            expressionChangedAt = SystemClock.uptimeMillis()
            emotionUntil = expressionChangedAt + 6500L
            invalidate()
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

    /**
     * Ojo anime vectorial: párpados almendrados, pestañas, cejas expresivas,
     * iris turquesa con gradiente, pupila oscura y reflejos especulares.
     * Se recorta el iris al área real del párpado, incluso al parpadear.
     */
    private fun eyes(canvas: Canvas, x: Float, y: Float, look: Float, blink: Float,
                     mood: SkyEmotionLexicon.Mood, iris: Int, speaking: Boolean) {
        val left = x < 180f
        val angry = mood == SkyEmotionLexicon.Mood.ANGRY
        val sad = mood == SkyEmotionLexicon.Mood.SAD || mood == SkyEmotionLexicon.Mood.CRYING
        val sleepy = mood == SkyEmotionLexicon.Mood.SLEEPY
        val squint = mood == SkyEmotionLexicon.Mood.HAPPY || mood == SkyEmotionLexicon.Mood.EXCITED
        val open = when {
            sleepy -> 0.24f
            mood == SkyEmotionLexicon.Mood.SURPRISED -> 1.15f
            angry -> 0.78f
            sad -> 0.77f
            squint -> 0.94f
            mood == SkyEmotionLexicon.Mood.SHY -> 0.83f
            else -> 1f
        }
        val halfHeight = max(2.5f, 61f * open * (1f - blink * 0.98f))
        val leftX = x - 61f
        val rightX = x + 61f

        // Ceja: las puntas interiores cambian de inclinación según el ánimo.
        val outerX = x + if (left) -54f else 54f
        val innerX = x + if (left) 48f else -48f
        val browOuter = y - 112f + if (sad) 8f else 0f
        val browInner = y - 112f + when {
            angry -> 31f
            sad -> -18f
            mood == SkyEmotionLexicon.Mood.SURPRISED -> -14f
            sleepy -> 9f
            else -> 0f
        }
        outline(Color.rgb(216, 233, 251), if (angry) 8f else 6f, 240)
        shape.reset()
        shape.moveTo(outerX, browOuter)
        shape.cubicTo(x, (browOuter + browInner) / 2f - 18f,
            x, (browOuter + browInner) / 2f - 17f, innerX, browInner)
        canvas.drawPath(shape, brush)

        // Párpados: no es una pupila flotando; la forma tiene contorno propio.
        shape.reset()
        shape.moveTo(leftX, y - 1f)
        shape.cubicTo(x - 32f, y - halfHeight * 1.28f,
            x + 32f, y - halfHeight * 1.28f, rightX, y - 2f)
        shape.cubicTo(x + 36f, y + halfHeight * 0.95f,
            x - 36f, y + halfHeight * 0.95f, leftX, y - 1f)
        shape.close()
        canvas.save()
        canvas.clipPath(shape)
        brush.style = Paint.Style.FILL
        brush.shader = LinearGradient(x, y - 67f, x, y + 72f,
            Color.rgb(251, 253, 255), Color.rgb(183, 219, 241), Shader.TileMode.CLAMP)
        canvas.drawPath(shape, brush)
        brush.shader = null

        if (halfHeight > 8f) {
            val pupilX = x + look.coerceIn(-17f, 17f)
            val pupilY = y + when {
                mode == "THINKING" -> -12f
                speaking -> 5f
                else -> 2f
            }
            light(canvas, pupilX, pupilY, 64f, Color.rgb(30, 226, 240), 95)
            brush.shader = RadialGradient(pupilX - 10f, pupilY - 16f, 50f,
                intArrayOf(Color.rgb(123, 251, 250), iris, Color.rgb(19, 66, 162)),
                floatArrayOf(0f, 0.55f, 1f), Shader.TileMode.CLAMP)
            brush.style = Paint.Style.FILL
            canvas.drawCircle(pupilX, pupilY, 48f, brush)
            brush.shader = null
            outline(Color.rgb(20, 80, 148), 3.4f, 204)
            canvas.drawCircle(pupilX, pupilY, 47f, brush)
            // Fibras de iris para generar volumen sin texturas externas.
            for (i in 0..18) {
                val angle = i * Math.PI * 2 / 19
                val xx = kotlin.math.cos(angle).toFloat()
                val yy = sin(angle).toFloat()
                outline(Color.rgb(143, 255, 255), 1.35f, 112)
                canvas.drawLine(pupilX + xx * 30f, pupilY + yy * 30f,
                    pupilX + xx * 43f, pupilY + yy * 43f, brush)
            }
            fill(Color.rgb(14, 36, 91))
            canvas.drawCircle(pupilX, pupilY + 3f, 26f, brush)
            fill(Color.rgb(5, 15, 46))
            canvas.drawCircle(pupilX, pupilY + 4f, 19f, brush)
            fill(Color.WHITE, 250)
            canvas.drawCircle(pupilX - 15f, pupilY - 19f, 13.5f, brush)
            canvas.drawCircle(pupilX + 15f, pupilY + 15f, 5.5f, brush)
            fill(Color.rgb(199, 251, 255), 165)
            canvas.drawCircle(pupilX + 21f, pupilY - 18f, 3.5f, brush)
        }
        canvas.restore()

        // Delineado exterior, línea inferior más suave y pestañas en abanico.
        outline(Color.rgb(9, 21, 58), 8f, 253)
        shape.reset()
        shape.moveTo(leftX, y - 1f)
        shape.cubicTo(x - 32f, y - halfHeight * 1.28f,
            x + 32f, y - halfHeight * 1.28f, rightX, y - 2f)
        canvas.drawPath(shape, brush)
        outline(Color.rgb(115, 200, 226), 3f, 170)
        shape.reset()
        shape.moveTo(leftX + 7f, y + 7f)
        shape.quadTo(x, y + halfHeight * 1.1f, rightX - 7f, y + 7f)
        canvas.drawPath(shape, brush)
        val outer = if (left) leftX else rightX
        val dir = if (left) -1f else 1f
        outline(Color.rgb(9, 21, 58), 5f, 250)
        for (i in 0..2) {
            val lx = outer - dir * i * 14f
            val ly = y - halfHeight * (0.1f + i * 0.32f)
            shape.reset()
            shape.moveTo(lx, ly)
            shape.quadTo(lx + dir * 13f, ly - 16f,
                lx + dir * (21f - i * 2f), ly - (27f - i * 6f))
            canvas.drawPath(shape, brush)
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
            "SLEEPING" -> SkyEmotionLexicon.Mood.SLEEPY
            "LISTENING", "THINKING" -> SkyEmotionLexicon.Mood.CURIOUS
            "ERROR" -> SkyEmotionLexicon.Mood.SAD
            else -> if (now < emotionUntil) emotion else
                if (speaking) SkyEmotionLexicon.Mood.HAPPY else SkyEmotionLexicon.Mood.CALM
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
        val entrance = ((now - expressionChangedAt).coerceAtLeast(0L) / 320f).coerceIn(0f, 1f)
        val bounce = if (entrance < 1f) (1f - entrance) * 5f else 0f
        val irisBlue = Color.rgb(47, 202, 233)
        eyes(canvas, 111f, 286f - bounce, gaze, blink, mood, irisBlue, speaking)
        eyes(canvas, 249f, 286f - bounce, gaze,
            if (mood == SkyEmotionLexicon.Mood.LOVING) 0.28f else blink, mood, irisBlue, speaking)
        // Rubor sutil, incluso en reposo; más visible en alegría y timidez.
        val blushAlpha = when (mood) {
            SkyEmotionLexicon.Mood.SHY -> 135
            SkyEmotionLexicon.Mood.HAPPY, SkyEmotionLexicon.Mood.LOVING -> 98
            else -> 36
        }
        light(canvas, 47f, 364f, 26f, Color.rgb(255, 131, 186), blushAlpha)
        light(canvas, 313f, 364f, 26f, Color.rgb(255, 131, 186), blushAlpha)
        // Naricita mínima que acompaña al rostro anime de referencia.
        outline(Color.rgb(192, 214, 239), 2.8f, 172)
        canvas.drawLine(176f, 392f, 182f, 394f, brush)
        if (mood == SkyEmotionLexicon.Mood.CRYING || mood == SkyEmotionLexicon.Mood.SAD) {
            fill(Color.rgb(112, 218, 250), if (mood == SkyEmotionLexicon.Mood.CRYING) 245 else 180)
            val drop = (now % 1300L) / 1300f
            canvas.drawOval(92f, 325f + drop * 75f, 107f, 350f + drop * 75f, brush)
            if (mood == SkyEmotionLexicon.Mood.CRYING)
                canvas.drawOval(257f, 327f + drop * 70f, 270f, 349f + drop * 70f, brush)
        }
        if (mood == SkyEmotionLexicon.Mood.SHY) {
            light(canvas, 45f, 380f, 30f, Color.rgb(255, 130, 173), 126)
            light(canvas, 315f, 380f, 30f, Color.rgb(255, 130, 173), 126)
        }

        val talkOpen = if (speaking) 5f + ((sin(t * 12.5) + 1) * 11f).toFloat() else 0f
        when {
            mode == "ERROR" -> {
                outline(Color.rgb(255, 203, 220), 6f)
                bounds.set(147f, 462f, 213f, 489f)
                canvas.drawArc(bounds, 194f, 155f, false, brush)
            }
            mood == SkyEmotionLexicon.Mood.SLEEPY -> {
                outline(Color.rgb(229, 211, 250), 6f)
                canvas.drawLine(160f, 474f, 200f, 474f, brush)
            }
            mood == SkyEmotionLexicon.Mood.SAD || mood == SkyEmotionLexicon.Mood.CRYING -> {
                outline(Color.rgb(165, 220, 255), 7f)
                canvas.drawArc(147f, 463f, 213f, 513f, 190f, 160f, false, brush)
            }
            mood == SkyEmotionLexicon.Mood.ANGRY -> {
                outline(Color.rgb(255, 180, 180), 7f)
                canvas.drawLine(153f, 486f, 207f, 486f, brush)
            }
            mood == SkyEmotionLexicon.Mood.SURPRISED || speaking -> {
                fill(Color.rgb(41, 29, 94))
                canvas.drawOval(154f, 453f - talkOpen * 0.34f,
                    206f, 492f + talkOpen * 0.72f, brush)
                fill(Color.rgb(243, 142, 192))
                canvas.drawOval(169f, 481f + talkOpen * 0.2f,
                    191f, 490f + talkOpen * 0.55f, brush)
            }
            mood == SkyEmotionLexicon.Mood.HAPPY || mood == SkyEmotionLexicon.Mood.LOVING || mood == SkyEmotionLexicon.Mood.EXCITED || mood == SkyEmotionLexicon.Mood.SHY -> {
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
        if (mood == SkyEmotionLexicon.Mood.SURPRISED || mood == SkyEmotionLexicon.Mood.EXCITED || speaking) {
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
        if (isShown && windowVisibility == VISIBLE) postInvalidateDelayed(50L)
    }
}
