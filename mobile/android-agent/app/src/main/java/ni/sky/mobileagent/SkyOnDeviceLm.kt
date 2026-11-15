package ni.sky.mobileagent

import android.content.Context
import android.net.Uri
import com.google.ai.edge.litertlm.Backend
import com.google.ai.edge.litertlm.Conversation
import com.google.ai.edge.litertlm.ConversationConfig
import com.google.ai.edge.litertlm.Contents
import com.google.ai.edge.litertlm.Engine
import com.google.ai.edge.litertlm.EngineConfig
import java.io.File
import java.io.FileOutputStream
import java.security.MessageDigest
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Primer motor generativo real DENTRO de Android mediante LiteRT-LM CPU.
 * No inicia servidor, no usa HTTP(S) y nunca ejecuta herramientas por salida del LLM.
 *
 * El usuario importa voluntariamente un modelo compatible .litertlm desde
 * Storage Access Framework. No se empaquetan pesos en APK ni se descargan solos.
 * La API de usuario permanece compatible con SKY Windows (que no se modifica).
 */
internal class SkyOnDeviceLm(private val context: Context) {
    private val executor = Executors.newSingleThreadExecutor { task ->
        Thread(task, "sky-ondevice-llm").apply { priority = Thread.MIN_PRIORITY + 1 }
    }
    private val closed = AtomicBoolean(false)
    private val busy = AtomicBoolean(false)
    private val modelFile = File(context.filesDir, MODEL_FILE_NAME)
    private var engine: Engine? = null
    private var conversation: Conversation? = null
    private var loadedPath: String? = null

    data class ModelInfo(val bytes: Long, val sha256: String)
    companion object {
        const val MODEL_FILE_NAME = "sky-private-model.litertlm"
        const val MIN_BYTES = 32L * 1024 * 1024
        const val MAX_BYTES = 3L * 1024 * 1024 * 1024
        const val PROMPT_MAX = 8_000
        const val MIN_FREE_BYTES = 200L * 1024 * 1024

        fun acceptedSize(bytes: Long): Boolean = bytes in MIN_BYTES..MAX_BYTES
        fun acceptedPrompt(text: String): Boolean =
            text.isNotBlank() && text.length <= PROMPT_MAX
        fun sha256(bytes: ByteArray): String = MessageDigest.getInstance("SHA-256")
            .digest(bytes).joinToString("") { "%02x".format(it.toInt() and 0xff) }
    }

    fun hasImportedModel(): Boolean = modelFile.isFile && acceptedSize(modelFile.length())
    fun isBusy(): Boolean = busy.get()

    private fun releaseEngine() {
        conversation?.close()
        conversation = null
        engine?.close()
        engine = null
        loadedPath = null
    }

    /** I/O + SHA-256 ejecutados fuera del hilo principal. */
    fun importModel(source: Uri, callback: (Result<ModelInfo>) -> Unit) {
        if (closed.get()) {
            callback(Result.failure(IllegalStateException("Motor cerrado")))
            return
        }
        if (!busy.compareAndSet(false, true)) {
            callback(Result.failure(IllegalStateException("SKY está procesando otra operación local.")))
            return
        }
        executor.execute {
            val incoming = File(context.filesDir, MODEL_FILE_NAME + ".partial")
            try {
                // Reemplazar un modelo no libera ni destruye uno válido hasta validar
                // el archivo importado y completar la copia con éxito.
                incoming.delete()
                var copied = 0L
                val digest = MessageDigest.getInstance("SHA-256")
                val free = context.filesDir.usableSpace
                require(free >= MIN_BYTES + MIN_FREE_BYTES) {
                    "No hay suficiente espacio libre para importar el modelo."
                }
                context.contentResolver.openInputStream(source).use { input ->
                    requireNotNull(input) { "No se pudo abrir el archivo seleccionado." }
                    FileOutputStream(incoming).use { output ->
                        val bytes = ByteArray(128 * 1024)
                        while (true) {
                            val n = input.read(bytes)
                            if (n < 0) break
                            if (n == 0) continue
                            copied += n
                            require(copied <= MAX_BYTES) {
                                "El modelo supera el máximo de 3 GiB permitido."
                            }
                            digest.update(bytes, 0, n)
                            output.write(bytes, 0, n)
                        }
                        output.fd.sync()
                    }
                }
                require(acceptedSize(copied)) {
                    "El archivo no tiene un tamaño de modelo válido; elegí un .litertlm compatible."
                }
                // No cerrar un engine que está generando: la cola de un solo
                // hilo garantiza que el cambio espera a la respuesta actual.
                releaseEngine()
                val previous = File(context.filesDir, MODEL_FILE_NAME + ".previous")
                previous.delete()
                if (modelFile.exists()) {
                    require(modelFile.renameTo(previous)) { "No pude resguardar el modelo anterior." }
                }
                if (!incoming.renameTo(modelFile)) {
                    if (previous.exists()) previous.renameTo(modelFile)
                    error("No se pudo instalar el modelo en almacenamiento privado.")
                }
                previous.delete()
                val hash = digest.digest().joinToString("") {
                    "%02x".format(it.toInt() and 0xff)
                }
                // La huella permite cotejar con el repositorio oficial del modelo.
                File(context.filesDir, MODEL_FILE_NAME + ".sha256").writeText(hash)
                callback(Result.success(ModelInfo(copied, hash)))
            } catch (error: Exception) {
                callback(Result.failure(error))
            } finally {
                incoming.delete()
                busy.set(false)
            }
        }
    }

    /** Una única conversación persistente en RAM; la app maneja su archivo aparte. */
    fun generate(prompt: String, callback: (Result<String>) -> Unit) {
        if (!acceptedPrompt(prompt)) {
            callback(Result.failure(IllegalArgumentException(
                "Ingresá una consulta de 1 a $PROMPT_MAX caracteres."
            )))
            return
        }
        if (closed.get() || !hasImportedModel()) {
            callback(Result.failure(IllegalStateException(
                "Importá primero un modelo .litertlm desde Ajustes de SKY."
            )))
            return
        }
        if (!busy.compareAndSet(false, true)) {
            callback(Result.failure(IllegalStateException(
                "SKY está atendiendo otro turno local."
            )))
            return
        }
        executor.execute {
            try {
                if (loadedPath != modelFile.absolutePath) {
                    releaseEngine()
                    val candidate = Engine(EngineConfig(
                        modelPath = modelFile.absolutePath,
                        backend = Backend.CPU(),
                        cacheDir = context.cacheDir.absolutePath
                    ))
                    // No cerrar candidate si initialize falla: la API exige
                    // cerrar únicamente motores completamente inicializados.
                    candidate.initialize()
                    val newConversation = try {
                        candidate.createConversation(ConversationConfig(
                            systemInstruction = Contents.of(
                                "Eres SKY, una IA personal en Android. Habla español claro y natural. " +
                                "No afirmes haber ejecutado aplicaciones, enviado mensajes ni " +
                                "consultado internet. Tu salida es texto, no permisos ni acciones. " +
                                "Reconoce incertidumbre y límites de conocimiento."
                            )
                        ))
                    } catch (error: Exception) {
                        candidate.close()
                        throw error
                    }
                    engine = candidate
                    conversation = newConversation
                    loadedPath = modelFile.absolutePath
                }
                val response = requireNotNull(conversation).sendMessage(prompt).toString().trim()
                require(response.isNotBlank()) { "El modelo no generó respuesta." }
                callback(Result.success(response))
            } catch (error: Exception) {
                callback(Result.failure(error))
            } finally {
                busy.set(false)
            }
        }
    }

    fun shutdown() {
        if (!closed.compareAndSet(false, true)) return
        executor.execute { runCatching { releaseEngine() } }
        executor.shutdown()
    }
}
