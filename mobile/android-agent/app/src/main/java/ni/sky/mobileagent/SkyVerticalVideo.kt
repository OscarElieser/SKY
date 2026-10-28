package ni.sky.mobileagent

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.LinearGradient
import android.graphics.Paint
import android.graphics.Shader
import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaFormat
import android.media.MediaMuxer
import android.opengl.EGL14
import android.opengl.EGLExt
import android.opengl.GLES20
import android.opengl.GLUtils
import android.view.Surface
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.concurrent.TimeUnit
import kotlin.math.sin

/**
 * MP4 creator that runs entirely on Android hardware (MediaCodec + OpenGL ES).
 * 10 seconds, vertical 720x1280, H.264, silent. Original animated text slides.
 * The user can add original music/narration using an authorized social editor.
 */
object SkyVerticalVideo {
    private const val WIDTH = 720
    private const val HEIGHT = 1280
    private const val FPS = 15
    private const val DURATION_S = 10
    private const val MIME = "video/avc"
    private const val EGL_RECORDABLE_ANDROID = 0x3142

    private fun slides(text: String): List<String> {
        val pieces = text.lineSequence().map { it.trim().trimStart('-', '*', '#', ' ') }
            .filter { it.length in 12..170 && !it.startsWith("http") }
            .take(30).toList()
        val selected = if (pieces.isEmpty()) listOf(text.take(100)) else pieces
        val result = selected.distinct().take(5).toMutableList()
        while (result.size < 5) result.add(
            listOf("Un detalle que vale la pena conocer",
                "¿Ya lo sabías?", "Guardá esta idea", "Compartí tu experiencia",
                "¿Qué opinás?")[result.size])
        return result
    }

    private fun background(canvas: Canvas, paint: Paint, scene: Int, frame: Int) {
        val colors = arrayOf(
            intArrayOf(0xff0a0c24.toInt(), 0xff312064.toInt()),
            intArrayOf(0xff101437.toInt(), 0xff184d76.toInt()),
            intArrayOf(0xff151039.toInt(), 0xff613478.toInt()),
            intArrayOf(0xff071e34.toInt(), 0xff176868.toInt()),
            intArrayOf(0xff14102f.toInt(), 0xff3c3269.toInt())
        )
        val c = colors[scene % colors.size]
        paint.shader = LinearGradient(0f, 0f, WIDTH.toFloat(), HEIGHT.toFloat(),
            c[0], c[1], Shader.TileMode.CLAMP)
        canvas.drawRect(0f, 0f, WIDTH.toFloat(), HEIGHT.toFloat(), paint)
        paint.shader = null
        val offset = (sin(frame.toDouble() / 12.0) * 28).toFloat()
        paint.color = 0x4475dce0
        canvas.drawCircle(560f + offset, 300f, 195f, paint)
        paint.color = 0x446a57c9
        canvas.drawCircle(90f - offset, 840f, 260f, paint)
        paint.color = 0xaef3d8ff.toInt()
        paint.strokeWidth = 4f
        canvas.drawLine(65f, 1088f, 655f, 1088f, paint)
    }

    private fun lines(canvas: Canvas, paint: Paint, text: String, maxWidth: Float, yStart: Float) {
        val words = text.split(Regex("\\s+"))
        val rows = mutableListOf<String>()
        var line = ""
        words.forEach { word ->
            val candidate = if (line.isEmpty()) word else line + " " + word
            if (paint.measureText(candidate) > maxWidth && line.isNotEmpty()) {
                rows.add(line)
                line = word
            } else line = candidate
        }
        if (line.isNotBlank()) rows.add(line)
        val chosen = rows.take(7)
        val start = yStart - (chosen.size - 1) * 43f
        chosen.forEachIndexed { index, sentence ->
            canvas.drawText(sentence, WIDTH / 2f,
                start + index * 86f, paint)
        }
    }

    private fun frame(canvas: Canvas, slides: List<String>, index: Int) {
        val current = (index * slides.size / (FPS * DURATION_S))
            .coerceIn(0, slides.lastIndex)
        val p = Paint(Paint.ANTI_ALIAS_FLAG)
        background(canvas, p, current, index)
        p.shader = null
        p.textAlign = Paint.Align.CENTER
        p.color = Color.WHITE
        p.typeface = android.graphics.Typeface.create("sans-serif-medium",
            android.graphics.Typeface.BOLD)
        p.textSize = 60f
        p.setShadowLayer(12f, 0f, 5f, Color.BLACK)
        lines(canvas, p, slides[current], 608f, 580f)
        p.clearShadowLayer()
        p.typeface = android.graphics.Typeface.DEFAULT
        p.textSize = 25f
        p.color = 0xffc8c9fc.toInt()
        canvas.drawText("UNA HISTORIA EN 10 SEGUNDOS", 360f, 172f, p)
        p.color = 0xff99f2f0.toInt()
        p.textSize = 29f
        canvas.drawText("¿QUÉ TE PARECE?", 360f, 1035f, p)
        p.color = 0xff6cf0d5.toInt()
        canvas.drawRoundRect(64f, 1135f,
            64f + 592f * (index + 1) / (FPS * DURATION_S), 1145f, 6f, 6f, p)
    }

    private const val VS = "attribute vec4 aPos; attribute vec2 aTex; varying vec2 vTex;" +
        "void main(){gl_Position=aPos;vTex=aTex;}"
    private const val FS = "precision mediump float; varying vec2 vTex; uniform sampler2D tex;" +
        "void main(){gl_FragColor=texture2D(tex,vTex);}"

    private fun shader(type: Int, source: String): Int {
        val id = GLES20.glCreateShader(type)
        GLES20.glShaderSource(id, source)
        GLES20.glCompileShader(id)
        val status = IntArray(1)
        GLES20.glGetShaderiv(id, GLES20.GL_COMPILE_STATUS, status, 0)
        require(status[0] != 0) { "No se pudo compilar el render OpenGL." }
        return id
    }

    private fun program(): Int {
        val id = GLES20.glCreateProgram()
        val vert = shader(GLES20.GL_VERTEX_SHADER, VS)
        val frag = shader(GLES20.GL_FRAGMENT_SHADER, FS)
        GLES20.glAttachShader(id, vert)
        GLES20.glAttachShader(id, frag)
        GLES20.glLinkProgram(id)
        val status = IntArray(1)
        GLES20.glGetProgramiv(id, GLES20.GL_LINK_STATUS, status, 0)
        GLES20.glDeleteShader(vert)
        GLES20.glDeleteShader(frag)
        require(status[0] != 0) { "No se pudo iniciar el render OpenGL." }
        return id
    }

    fun generate(context: Context, script: String): File {
        require(script.trim().length in 12..3500) { "Necesito un guion de al menos 12 caracteres." }
        val file = File(context.cacheDir, "sky_creator_last.mp4")
        val temp = File(context.cacheDir, "sky_creator_pending.mp4")
        temp.delete()
        var codec: MediaCodec? = null
        var muxer: MediaMuxer? = null
        var input: Surface? = null
        var display = EGL14.EGL_NO_DISPLAY
        var eglContext = EGL14.EGL_NO_CONTEXT
        var window = EGL14.EGL_NO_SURFACE
        var muxStarted = false
        var track = -1
        var bitmap: Bitmap? = null
        var texture = 0
        var glProgram = 0

        try {
            val format = MediaFormat.createVideoFormat(MIME, WIDTH, HEIGHT).apply {
                setInteger(MediaFormat.KEY_COLOR_FORMAT,
                    MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface)
                setInteger(MediaFormat.KEY_BIT_RATE, 1_800_000)
                setInteger(MediaFormat.KEY_FRAME_RATE, FPS)
                setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 2)
            }
            val encoder = MediaCodec.createEncoderByType(MIME)
            codec = encoder
            encoder.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
            input = encoder.createInputSurface()
            encoder.start()
            val writer = MediaMuxer(temp.absolutePath,
                MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
            muxer = writer

            display = EGL14.eglGetDisplay(EGL14.EGL_DEFAULT_DISPLAY)
            require(display != EGL14.EGL_NO_DISPLAY) { "No hay EGL en el teléfono." }
            require(EGL14.eglInitialize(display, IntArray(2), 0, IntArray(2), 0)) {
                "No se pudo iniciar EGL."
            }
            val configArray = arrayOfNulls<android.opengl.EGLConfig>(1)
            val count = IntArray(1)
            val attrs = intArrayOf(
                EGL14.EGL_RED_SIZE, 8, EGL14.EGL_GREEN_SIZE, 8,
                EGL14.EGL_BLUE_SIZE, 8, EGL14.EGL_ALPHA_SIZE, 8,
                EGL14.EGL_RENDERABLE_TYPE, EGL14.EGL_OPENGL_ES2_BIT,
                EGL_RECORDABLE_ANDROID, 1, EGL14.EGL_NONE
            )
            require(EGL14.eglChooseConfig(display, attrs, 0, configArray, 0,
                1, count, 0) && count[0] > 0) { "El teléfono no admite la superficie de video." }
            val config = configArray[0] ?: error("Sin configuración EGL")
            eglContext = EGL14.eglCreateContext(display, config, EGL14.EGL_NO_CONTEXT,
                intArrayOf(EGL14.EGL_CONTEXT_CLIENT_VERSION, 2, EGL14.EGL_NONE), 0)
            require(eglContext != EGL14.EGL_NO_CONTEXT) { "No se pudo crear OpenGL ES." }
            window = EGL14.eglCreateWindowSurface(display, config, input,
                intArrayOf(EGL14.EGL_NONE), 0)
            require(window != EGL14.EGL_NO_SURFACE && EGL14.eglMakeCurrent(
                display, window, window, eglContext)) { "Sin superficie de video." }

            glProgram = program()
            GLES20.glUseProgram(glProgram)
            GLES20.glViewport(0, 0, WIDTH, HEIGHT)
            val rect = floatArrayOf(
                -1f,-1f,0f,1f, 1f,-1f,1f,1f, -1f,1f,0f,0f,
                1f,1f,1f,0f)
            val buffer = ByteBuffer.allocateDirect(rect.size * 4).order(
                ByteOrder.nativeOrder()).asFloatBuffer().apply {
                put(rect); position(0)
            }
            val pos = GLES20.glGetAttribLocation(glProgram, "aPos")
            val uv = GLES20.glGetAttribLocation(glProgram, "aTex")
            GLES20.glEnableVertexAttribArray(pos)
            GLES20.glEnableVertexAttribArray(uv)
            buffer.position(0)
            GLES20.glVertexAttribPointer(pos, 2, GLES20.GL_FLOAT,
                false, 16, buffer)
            buffer.position(2)
            GLES20.glVertexAttribPointer(uv, 2, GLES20.GL_FLOAT,
                false, 16, buffer)
            val textures = IntArray(1)
            GLES20.glGenTextures(1, textures, 0)
            texture = textures[0]
            GLES20.glActiveTexture(GLES20.GL_TEXTURE0)
            GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, texture)
            GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D,
                GLES20.GL_TEXTURE_MIN_FILTER, GLES20.GL_LINEAR)
            GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D,
                GLES20.GL_TEXTURE_MAG_FILTER, GLES20.GL_LINEAR)
            GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D,
                GLES20.GL_TEXTURE_WRAP_S, GLES20.GL_CLAMP_TO_EDGE)
            GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D,
                GLES20.GL_TEXTURE_WRAP_T, GLES20.GL_CLAMP_TO_EDGE)
            GLES20.glUniform1i(GLES20.glGetUniformLocation(glProgram, "tex"), 0)
            bitmap = Bitmap.createBitmap(WIDTH, HEIGHT, Bitmap.Config.ARGB_8888)
            val painter = Canvas(bitmap)
            val scenes = slides(script)
            val bufferInfo = MediaCodec.BufferInfo()
            val started = System.nanoTime()

            fun drain(eos: Boolean) {
                while (true) {
                    val out = encoder.dequeueOutputBuffer(bufferInfo, if (eos) 10000 else 0)
                    if (out == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                        require(!muxStarted) { "El encoder cambió formato dos veces." }
                        track = writer.addTrack(encoder.outputFormat)
                        writer.start()
                        muxStarted = true
                    } else if (out >= 0) {
                        if (bufferInfo.size > 0 &&
                            bufferInfo.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG == 0) {
                            require(muxStarted) { "El video todavía no tiene pista." }
                            val bytes = encoder.getOutputBuffer(out) ?: error("Buffer vacío.")
                            bytes.position(bufferInfo.offset)
                            bytes.limit(bufferInfo.offset + bufferInfo.size)
                            writer.writeSampleData(track, bytes, bufferInfo)
                        }
                        val complete = bufferInfo.flags and
                            MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0
                        encoder.releaseOutputBuffer(out, false)
                        if (complete) return
                    } else if (out == MediaCodec.INFO_TRY_AGAIN_LATER) {
                        if (!eos) return
                        require(System.nanoTime() - started < TimeUnit.SECONDS.toNanos(80)) {
                            "El generador de video tardó demasiado."
                        }
                    }
                }
            }

            for (i in 0 until FPS * DURATION_S) {
                frame(painter, scenes, i)
                if (i == 0) GLUtils.texImage2D(GLES20.GL_TEXTURE_2D, 0, bitmap, 0)
                else GLUtils.texSubImage2D(GLES20.GL_TEXTURE_2D, 0, 0, 0, bitmap)
                GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT)
                GLES20.glDrawArrays(GLES20.GL_TRIANGLE_STRIP, 0, 4)
                EGLExt.eglPresentationTimeANDROID(display, window,
                    i * 1_000_000_000L / FPS)
                require(EGL14.eglSwapBuffers(display, window)) {
                    "El codificador no recibió el cuadro del video."
                }
                drain(false)
            }
            encoder.signalEndOfInputStream()
            drain(true)
            require(temp.length() > 10_000L) { "La salida MP4 está incompleta." }
            // Replace only after a complete MP4 has been muxed.
            writer.stop()
            muxStarted = false
            writer.release()
            muxer = null
            file.delete()
            check(temp.renameTo(file)) { "No se pudo guardar el video final." }
            return file
        } catch (error: Exception) {
            temp.delete()
            throw error
        } finally {
            bitmap?.recycle()
            if (texture != 0) GLES20.glDeleteTextures(1, intArrayOf(texture), 0)
            if (glProgram != 0) GLES20.glDeleteProgram(glProgram)
            if (display != EGL14.EGL_NO_DISPLAY) {
                EGL14.eglMakeCurrent(display, EGL14.EGL_NO_SURFACE,
                    EGL14.EGL_NO_SURFACE, EGL14.EGL_NO_CONTEXT)
                if (window != EGL14.EGL_NO_SURFACE) EGL14.eglDestroySurface(display, window)
                if (eglContext != EGL14.EGL_NO_CONTEXT)
                    EGL14.eglDestroyContext(display, eglContext)
                EGL14.eglTerminate(display)
            }
            input?.release()
            runCatching { codec?.stop() }
            codec?.release()
            if (muxStarted) runCatching { muxer?.stop() }
            muxer?.release()
        }
    }
}
