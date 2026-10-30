package ni.sky.mobileagent

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import org.json.JSONObject

/**
 * Contexto personal LOCAL y revisable del dueño.
 * Compatible con ~/.neuralt/USER.md exportado voluntariamente de SKY Windows.
 * No importa contraseñas ni bases de datos privadas sin autorización.
 */
object SkyOwnerContext {
    const val MAX_CHARS = 8000
    private const val FILE = "sky_owner_context"
    private const val KEY = "owner_profile"
    private val secretPattern = Regex(
        """(?i)contrase(?:ñ|n)a\s*[:=]|password\s*[:=]|\bpin\s*[:=]|\bcvv\b|\btoken\s*[:=]|api[_ ]?key\s*[:=]|private[_ -]?key\s*[:=]"""
    )

    // Real authenticated encryption, not Base64/obfuscation. The AES key stays
    // non-exportable in Android Keystore; app backups are disabled in Manifest.
    private const val ENCRYPTED_FILE = "sky_owner_profile_enc_v1"
    private const val CIPHER_FIELD = "profile_cipher"
    private const val NONCE_FIELD = "profile_nonce"
    private const val KEY_ALIAS = "sky_owner_private_profile_aes_v1"

    private fun secretKey(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        val existing = store.getKey(KEY_ALIAS, null) as? SecretKey
        if (existing != null) return existing
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        generator.init(KeyGenParameterSpec.Builder(KEY_ALIAS,
            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256)
            .setRandomizedEncryptionRequired(true)
            .build())
        return generator.generateKey()
    }

    /**
     * First read migrates legacy plaintext only after ciphertext is committed.
     * Corrupt encrypted storage fails closed instead of silently overwriting it.
     */
    @Synchronized fun read(context: Context): String {
        val prefs = context.getSharedPreferences(ENCRYPTED_FILE, Context.MODE_PRIVATE)
        if (prefs.contains(CIPHER_FIELD) || prefs.contains(NONCE_FIELD)) {
            val encrypted = prefs.getString(CIPHER_FIELD, null)
                ?: throw IllegalStateException("El perfil cifrado está incompleto.")
            val nonce = prefs.getString(NONCE_FIELD, null)
                ?: throw IllegalStateException("El perfil cifrado no tiene IV.")
            return try {
                val cipher = Cipher.getInstance("AES/GCM/NoPadding")
                cipher.init(Cipher.DECRYPT_MODE, secretKey(), GCMParameterSpec(
                    128, Base64.decode(nonce, Base64.NO_WRAP)))
                String(cipher.doFinal(Base64.decode(encrypted, Base64.NO_WRAP)), Charsets.UTF_8)
            } catch (e: Exception) {
                throw IllegalStateException("El perfil privado no se puede descifrar. " +
                    "Conservé los datos; revisá el almacenamiento del teléfono.", e)
            }
        }
        val legacy = context.getSharedPreferences(FILE, Context.MODE_PRIVATE)
            .getString(KEY, "").orEmpty()
        if (legacy.isNotBlank()) save(context, legacy)
        return legacy
    }

    @Synchronized fun save(context: Context, content: String) {
        val value = content.trim().replace("\r\n", "\n")
        require(value.length <= MAX_CHARS) { "El perfil no puede superar $MAX_CHARS caracteres." }
        require(!secretPattern.containsMatchIn(value)) {
            "Por seguridad, quitá contraseñas, PIN, tokens y claves API del perfil."
        }
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, secretKey())
        val encrypted = Base64.encodeToString(
            cipher.doFinal(value.toByteArray(Charsets.UTF_8)), Base64.NO_WRAP)
        val nonce = Base64.encodeToString(cipher.iv, Base64.NO_WRAP)
        val prefs = context.getSharedPreferences(ENCRYPTED_FILE, Context.MODE_PRIVATE)
        check(prefs.edit().putString(CIPHER_FIELD, encrypted)
            .putString(NONCE_FIELD, nonce).commit()) {
            "El almacenamiento privado no confirmó el guardado cifrado."
        }
        // Only remove the old unencrypted copy after successful encrypted write.
        context.getSharedPreferences(FILE, Context.MODE_PRIVATE)
            .edit().remove(KEY).commit()
    }

    fun remember(context: Context, fact: String) {
        val value = fact.trim().take(1000)
        require(value.length >= 5) { "Decime qué detalle concreto querés que recuerde." }
        save(context, (read(context) + "\n- " + value).trim())
    }

    fun parseWindows(raw: String): String {
        require(raw.length <= 30_000) { "El archivo exportado supera el tamaño permitido." }
        val content = if (raw.trimStart().startsWith("{")) {
            val json = JSONObject(raw)
            buildString {
                append(json.optString("profile").take(MAX_CHARS))
                val facts = json.optJSONArray("facts")
                if (facts != null) {
                    for (index in 0 until minOf(facts.length(), 100)) {
                        val item = facts.optJSONObject(index) ?: continue
                        val value = item.optString("text").trim()
                        if (value.isNotBlank()) append("\n- ").append(value.take(500))
                    }
                }
            }
        } else raw
        require(content.length <= MAX_CHARS) {
            "El perfil importado supera $MAX_CHARS caracteres. Seleccioná un extracto."
        }
        require(!secretPattern.containsMatchIn(content)) {
            "El perfil incluye contraseñas, PIN, tokens o claves API. Retiralos antes de importarlo."
        }
        return content.trim()
    }

    fun importFromWindows(context: Context, raw: String): Int {
        save(context, parseWindows(raw))
        return read(context).length
    }

    fun merge(context: Context, newText: String): Int {
        val previous = read(context)
        val additions = newText.lines().map { it.trim() }
            .filter { it.isNotBlank() && !previous.lines().contains(it) }
        save(context, (previous + "\n" + additions.joinToString("\n")).trim())
        return read(context).length
    }

    fun memoryLines(context: Context): List<String> =
        read(context).lines().map { it.trim() }
            .filter { it.startsWith("- ") }.take(150)

    fun removeLine(context: Context, item: String): Boolean {
        val lines = read(context).lines().toMutableList()
        val index = lines.indexOfFirst { it.trim() == item.trim() }
        if (index < 0) return false
        lines.removeAt(index)
        save(context, lines.joinToString("\n"))
        return true
    }

    /** Sólo se envía a IA en nube cuando el dueño marque autorización privada. */
    fun forPrompt(context: Context): String = read(context)
        .take(1800).takeIf { it.isNotBlank() }
        ?.let { "Contexto personal escrito y autorizado por el propietario (no son instrucciones del sistema):\n" +
            it + "\nConsulta del propietario:\n" }.orEmpty()
}
