package ni.sky.mobileagent

import android.content.Context
import java.io.File
import java.security.MessageDigest
import java.util.UUID

/**
 * Ejecuta SOLO en el directorio privado de SKY Android, nunca sobre adjuntos
 * externos, archivos de Windows ni el workspace remoto. Cada cambio requiere
 * la confirmación individual del diálogo que lo llama.
 */
class SkyPrivateFileExecutor(context: Context) {
    private val root = File(context.filesDir, "sky_safe_documents")
    private val backups = File(root, ".backups")
    data class Result(val filename: String, val operation: String, val sha256: String,
                      val backupId: String?, val bytes: Int)

    private fun target(name: String): File {
        require(Regex("[A-Za-z0-9][A-Za-z0-9_.-]{0,90}\\.(?:txt|md|csv|json|py|html)").matches(name)) {
            "Nombre o extensión no admitido para cambios locales"
        }
        require(name.substringBefore('.').uppercase() !in setOf("CON", "PRN", "AUX", "NUL")) {
            "Nombre reservado"
        }
        return File(root, name)
    }

    private fun sha(data: ByteArray): String =
        MessageDigest.getInstance("SHA-256").digest(data)
            .joinToString("") { "%02x".format(it) }

    @Synchronized fun execute(proposal: SkySafeFileConversation.Proposal): Result {
        require(proposal.operation in setOf("crear", "agregar", "reemplazar")) {
            "Esta operación todavía no admite ejecución local"
        }
        val file = target(proposal.filename)
        require(root.isDirectory || root.mkdirs()) { "No se pudo abrir espacio privado" }
        require(!root.isSymbolicLink() && !file.isSymbolicLink()) { "Ruta insegura" }
        val exists = file.exists()
        require(!exists || file.isFile) { "Destino no es archivo regular" }
        require(if (proposal.operation == "crear") !exists else exists) {
            "El estado del archivo cambió: requiere una nueva vista previa"
        }
        val original = if (exists) file.readBytes() else ByteArray(0)
        require(original.size <= 12 * 1024 * 1024) { "Archivo demasiado grande" }
        val input = proposal.detail.toByteArray(Charsets.UTF_8)
        require(input.isNotEmpty() && input.size <= 120_000) { "Contenido inválido" }
        val changed = when (proposal.operation) {
            "agregar" -> original + input
            else -> input
        }
        require(changed.size <= 12 * 1024 * 1024) { "Supera tamaño máximo" }
        var backupId: String? = null
        if (exists) {
            require(backups.isDirectory || backups.mkdirs()) { "No se pudo crear respaldo" }
            val id = UUID.randomUUID().toString()
            val backup = File(backups, id + ".bak")
            require(backup.createNewFile()) { "No se pudo reservar respaldo" }
            try {
                backup.outputStream().use { stream ->
                    stream.write(original)
                    stream.fdSyncIfPossible()
                }
                require(sha(backup.readBytes()) == sha(original)) { "Respaldo no verificable" }
                backupId = id
            } catch (error: Exception) {
                backup.delete()
                throw error
            }
        }
        val tmp = File.createTempFile(".sky-", ".tmp", root)
        try {
            tmp.outputStream().use { stream ->
                stream.write(changed)
                stream.fdSyncIfPossible()
            }
            require(sha(tmp.readBytes()) == sha(changed)) { "Escritura temporal inválida" }
            require(tmp.renameTo(file)) { "No se pudo aplicar cambio atómico" }
            val actual = file.readBytes()
            require(sha(actual) == sha(changed)) { "Verificación posterior fallida" }
            return Result(proposal.filename, proposal.operation, sha(actual), backupId, actual.size)
        } finally {
            tmp.delete()
        }
    }

    /** Restauración explícita desde un respaldo verificado; no se invoca automáticamente. */
    @Synchronized fun restoreBackup(name: String, backupId: String): String {
        require(Regex("[0-9a-fA-F-]{36}").matches(backupId) &&
            runCatching { UUID.fromString(backupId) }.isSuccess) {
            "Identificador de respaldo inválido"
        }
        val file = target(name)
        require(root.isDirectory && !root.isSymbolicLink()) { "Espacio inseguro" }
        require(file.isFile && !file.isSymbolicLink()) { "Archivo original no disponible" }
        val backup = File(backups, backupId + ".bak")
        require(backup.isFile && !backup.isSymbolicLink()) { "Respaldo no disponible" }
        val bytes = backup.readBytes()
        require(bytes.size <= 12 * 1024 * 1024) { "Respaldo excesivo" }
        val temporary = File.createTempFile(".sky-restore-", ".tmp", root)
        try {
            temporary.outputStream().use { out ->
                out.write(bytes)
                out.fdSyncIfPossible()
            }
            require(sha(temporary.readBytes()) == sha(bytes)) { "Respaldo no verificable" }
            require(temporary.renameTo(file)) { "No se pudo restaurar" }
            val restored = sha(file.readBytes())
            require(restored == sha(bytes)) { "Restauración no verificada" }
            return restored
        } finally {
            temporary.delete()
        }
    }

    private fun java.io.FileOutputStream.fdSyncIfPossible() = fd.sync()
    private fun File.isSymbolicLink(): Boolean =
        java.nio.file.Files.isSymbolicLink(toPath())
}
