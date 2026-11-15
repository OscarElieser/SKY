package ni.sky.mobileagent

import android.content.Context
import android.graphics.Canvas
import android.graphics.Camera
import android.graphics.Matrix
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
import kotlin.math.cos

/**
 * SKY · Aura Face (Android).
 *
 * Dos ojos y una boca animados, sin rostro ni máscara.
 * Ocupan la altura útil y expresan estados reales del motor
 * de voz: escucha, respuesta, pensamiento y error. No transmite audio.
 */
class SkyFriendlyEyesView(context: Context) : View(context) {

    var mode: String = "IDLE"
        set(value) {
            if (field != value) expressionChangedAt = SystemClock.uptimeMillis()
            field = value
            invalidate()
        }
    var amplitude: Float = 0f
        set(value) { field = value.coerceIn(0f, 1f); invalidate() }

    private val brush = Paint(Paint.ANTI_ALIAS_FLAG)
    private val shape = Path()
    private val bounds = RectF()
    private var emotion = SkyEmotionLexicon.Mood.CALM
    private var expressionChangedAt = 0L
    private var emotionUntil = 0L
    private var touchCount = 0
    private var motion = "NONE"
    private var motionUntil = 0L

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
        val move = when {
            value.contains("baila", ignoreCase = true) -> "DANCE"
            value.contains("salta", ignoreCase = true) -> "JUMP"
            value.contains("corre", ignoreCase = true) -> "RUN"
            value.contains("gira", ignoreCase = true) -> "SPIN"
            else -> "NONE"
        }
        if (move != "NONE") {
            motion = move
            emotion = SkyEmotionLexicon.Mood.EXCITED
            expressionChangedAt = SystemClock.uptimeMillis()
            motionUntil = expressionChangedAt + 7000L
            emotionUntil = motionUntil
            invalidate()
            return when (move) {
                "DANCE" -> "¡Mirá mis ojos bailando!"
                "JUMP" -> "¡Estoy saltando!"
                "RUN" -> "¡Estoy corriendo!"
                else -> "¡Dando una vuelta!"
            }
        }
        motion = "NONE"
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


    // Solo ojos y boca. Sin imagen externa, cejas, nariz, mejillas, carcasa ni máscara.
    // Se mantienen modo, emociones, gestos, movimientos y las señales de voz existentes.
    private val cyan = Color.rgb(19, 231, 237)
    private val cyanBright = Color.rgb(113, 255, 255)

    private fun fill(color: Int, alpha: Int = 255) {
        brush.shader = null
        brush.style = Paint.Style.FILL
        brush.color = color
        brush.alpha = alpha.coerceIn(0, 255)
    }

    private fun outline(color: Int, width: Float, alpha: Int = 255) {
        brush.shader = null
        brush.style = Paint.Style.STROKE
        brush.strokeWidth = width
        brush.strokeCap = Paint.Cap.ROUND
        brush.strokeJoin = Paint.Join.ROUND
        brush.color = color
        brush.alpha = alpha.coerceIn(0, 255)
    }

    private fun glow(canvas: Canvas, cx: Float, cy: Float,
                     radius: Float, color: Int, alpha: Int) {
        brush.style = Paint.Style.FILL
        brush.alpha = 255
        brush.shader = RadialGradient(cx, cy, radius,
            intArrayOf(Color.argb(alpha.coerceIn(0, 255),
                Color.red(color), Color.green(color), Color.blue(color)),
                Color.TRANSPARENT),
            null, Shader.TileMode.CLAMP)
        canvas.drawCircle(cx, cy, radius, brush)
        brush.shader = null
    }

    private fun drawEye(canvas: Canvas, x: Float, y: Float, radius: Float,
                        gaze: Float, openness: Float, power: Float,
                        mood: SkyEmotionLexicon.Mood, wink: Boolean) {
        val heightFactor = if (wink) 0.11f else openness.coerceIn(0.09f, 1.14f)
        val rY = max(4.4f, radius * heightFactor)
        val color = when {
            mode == "ERROR" -> Color.rgb(255, 151, 160)
            mood == SkyEmotionLexicon.Mood.ANGRY -> Color.rgb(255, 168, 183)
            else -> cyan
        }
        val extra = if (mode == "LISTENING") amplitude * 8f else power * 2.4f
        glow(canvas, x, y, radius * 1.8f + extra, color,
            (64 + power * 35f + amplitude * 35f).toInt())
        if (rY <= radius * 0.18f) {
            outline(color, 10f, 245)
            canvas.drawLine(x - radius * 0.81f, y, x + radius * 0.81f, y, brush)
            return
        }
        // Dos círculos cyan suaves y luminosos, sin iris de estilo humano.
        brush.style = Paint.Style.FILL
        brush.alpha = 255
        brush.shader = RadialGradient(
            x - radius * 0.30f + gaze * 0.32f,
            y - radius * 0.35f, radius * 1.25f,
            intArrayOf(Color.WHITE, cyanBright, color),
            floatArrayOf(0f, 0.32f, 1f), Shader.TileMode.CLAMP
        )
        bounds.set(x - radius, y - rY, x + radius, y + rY)
        canvas.drawOval(bounds, brush)
        brush.shader = null
        // Reflejo muy sutil; el desplazamiento da vida a los ojos.
        fill(Color.WHITE, if (mode == "SLEEPING") 30 else 120)
        canvas.drawOval(x - radius * 0.48f + gaze * 0.25f,
            y - rY * 0.63f, x - radius * 0.23f + gaze * 0.25f,
            y - rY * 0.21f, brush)
    }

    private fun drawMouth(canvas: Canvas, mood: SkyEmotionLexicon.Mood,
                          seconds: Double, speaking: Boolean) {
        val centerX = 180f
        val centerY = 402f
        val width = when (mood) {
            SkyEmotionLexicon.Mood.HAPPY, SkyEmotionLexicon.Mood.EXCITED,
            SkyEmotionLexicon.Mood.LOVING -> 47f
            SkyEmotionLexicon.Mood.SHY -> 29f
            else -> 38f
        }
        val color = if (mode == "ERROR" || mood == SkyEmotionLexicon.Mood.ANGRY)
            Color.rgb(255, 164, 186) else cyan
        val talk = (0.5 + 0.5 * sin(seconds * 12.4)).toFloat()
        val mouthOpen = when {
            speaking -> 8f + talk * 25f + amplitude * 8f
            mood == SkyEmotionLexicon.Mood.SURPRISED -> 24f
            else -> 0f
        }
        glow(canvas, centerX, centerY + 13f, 65f, color,
            if (speaking) 60 + (talk * 45f).toInt() else 36)
        if (mouthOpen > 0f) {
            // Boca abierta/ovalada: el ritmo de TTS es aproximado, no lip-sync fonético.
            fill(color, 48)
            bounds.set(centerX - width * 0.52f,
                centerY - mouthOpen * 0.43f,
                centerX + width * 0.52f,
                centerY + mouthOpen * 0.90f)
            canvas.drawOval(bounds, brush)
            outline(color, 9f)
            canvas.drawOval(bounds, brush)
            return
        }
        outline(color, 10f)
        shape.reset()
        shape.moveTo(centerX - width, centerY)
        when {
            mood == SkyEmotionLexicon.Mood.SLEEPY -> {
                shape.lineTo(centerX + width, centerY)
            }
            mode == "ERROR" || mood == SkyEmotionLexicon.Mood.SAD ||
                mood == SkyEmotionLexicon.Mood.CRYING ||
                mood == SkyEmotionLexicon.Mood.ANGRY -> {
                shape.quadTo(centerX, centerY - 11f, centerX + width, centerY)
            }
            mood == SkyEmotionLexicon.Mood.CURIOUS -> {
                shape.quadTo(centerX, centerY + 13f, centerX + width, centerY)
            }
            else -> {
                val smile = if (mood == SkyEmotionLexicon.Mood.HAPPY ||
                    mood == SkyEmotionLexicon.Mood.EXCITED ||
                    mood == SkyEmotionLexicon.Mood.LOVING) 42f else 31f
                shape.quadTo(centerX, centerY + smile, centerX + width, centerY)
            }
        }
        canvas.drawPath(shape, brush)
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        if (width < 2 || height < 2) return
        val now = SystemClock.uptimeMillis()
        val seconds = now / 1000.0
        val speaking = mode == "SPEAKING"
        val mood = when (mode) {
            "SLEEPING" -> SkyEmotionLexicon.Mood.SLEEPY
            "LISTENING", "THINKING" -> SkyEmotionLexicon.Mood.CURIOUS
            "ERROR" -> SkyEmotionLexicon.Mood.SAD
            else -> if (now < emotionUntil) emotion
                else if (speaking) SkyEmotionLexicon.Mood.HAPPY
                else SkyEmotionLexicon.Mood.CALM
        }

        val scale = min(width / 360f, height / 590f)
        canvas.save()
        canvas.translate((width - 360f * scale) / 2f, (height - 590f * scale) / 2f)
        canvas.scale(scale, scale)

        // Conservar los gestos previamente implementados: bailar, saltar,
        // correr y girar. Se mueve únicamente el conjunto ojos + boca.
        canvas.save()
        val activeMotion = if (now < motionUntil && mode != "SLEEPING") motion else "NONE"
        val elapsed = (now - expressionChangedAt).coerceAtLeast(0L) / 1000.0
        val dx = when (activeMotion) {
            "DANCE" -> (sin(elapsed * 6.0) * 17.0).toFloat()
            "RUN" -> (sin(elapsed * 13.0) * 12.0).toFloat()
            else -> 0f
        }
        val dy = when (activeMotion) {
            "JUMP" -> (-abs(sin(elapsed * 4.5)) * 38.0).toFloat()
            "RUN" -> (sin(elapsed * 15.0) * 8.0).toFloat()
            "DANCE" -> (sin(elapsed * 9.0) * 9.0).toFloat()
            else -> (sin(seconds * 1.2) * 3.0).toFloat()
        }
        canvas.translate(dx, dy)
        if (activeMotion == "SPIN") {
            canvas.rotate((sin(elapsed * 4.2) * 16.0).toFloat(), 180f, 327f)
        }

        // Parpadeo orgánico: cierre rápido de 200 ms cada ~4,6 segundos.
        // Sólo una de las expresiones puede guiñar; no añade permisos/sensores.
        val blinkCycle = now % 4600L
        val blink = if (blinkCycle in 4380L..4580L) {
            val step = (blinkCycle - 4380L) / 200f
            1f - abs(2f * step - 1f)
        } else 0f
        val energy = ((sin(seconds * 2.3) + 1) * 0.5).toFloat()
        val openness = when {
            mode == "SLEEPING" || mood == SkyEmotionLexicon.Mood.SLEEPY -> 0.12f
            mood == SkyEmotionLexicon.Mood.SURPRISED -> 1.14f
            mood == SkyEmotionLexicon.Mood.ANGRY -> 0.64f
            mood == SkyEmotionLexicon.Mood.SAD || mood == SkyEmotionLexicon.Mood.CRYING -> 0.70f
            mood == SkyEmotionLexicon.Mood.SHY -> 0.76f
            mood == SkyEmotionLexicon.Mood.HAPPY -> 0.93f
            else -> 1f
        } * (1f - blink * 0.91f)
        val gaze = when (mode) {
            "LISTENING" -> (amplitude * 12f) - 4f
            "THINKING" -> -9f
            else -> (sin(seconds * 0.58) * 8.0).toFloat()
        }
        val openingBounce = (1f - ((now - expressionChangedAt)
            .coerceAtLeast(0L) / 260f).coerceIn(0f, 1f)) * 6f
        drawEye(canvas, 111f, 286f - openingBounce, 44f, gaze,
            openness, energy, mood, false)
        drawEye(canvas, 249f, 286f - openingBounce, 44f, gaze,
            openness, energy, mood, mood == SkyEmotionLexicon.Mood.LOVING &&
                (now / 1700L) % 4L == 0L)

        drawMouth(canvas, mood, seconds, speaking)
        canvas.restore()
        canvas.restore()
        if (isShown && windowVisibility == VISIBLE) {
            // Mantener ahorro de batería existente al dormirse o salir de pantalla.
            postInvalidateDelayed(if (mode == "SLEEPING") 120L else 33L)
        }
    }
}
