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

/** Token individual cifrado con Android Keystore. Nunca almacena la clave maestra de SKY. */
class PrivateTokenStore(context: Context) {
    private val prefs = context.getSharedPreferences("sky_mobile_private_v1", Context.MODE_PRIVATE)
    private val alias = "sky_mobile_pairing_aes_v1"
    private fun key(): SecretKey {
        val ks = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        val existing = ks.getKey(alias, null) as? SecretKey
        if (existing != null) return existing
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        generator.init(KeyGenParameterSpec.Builder(alias,
            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256).build())
        return generator.generateKey()
    }
    fun save(server: String, id: String, token: String) {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key())
        prefs.edit().putString("server", server).putString("id", id)
            .putString("iv", Base64.encodeToString(cipher.iv, Base64.NO_WRAP))
            .putString("token", Base64.encodeToString(cipher.doFinal(token.toByteArray(Charsets.UTF_8)), Base64.NO_WRAP))
            .apply()
    }
    fun server(): String = prefs.getString("server", "") ?: ""
    fun deviceId(): String = prefs.getString("id", "") ?: ""
    fun token(): String {
        val iv = prefs.getString("iv", "") ?: ""
        val encrypted = prefs.getString("token", "") ?: ""
        if (iv.isEmpty() || encrypted.isEmpty()) return ""
        return try {
            val c = Cipher.getInstance("AES/GCM/NoPadding")
            c.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, Base64.decode(iv, Base64.NO_WRAP)))
            String(c.doFinal(Base64.decode(encrypted, Base64.NO_WRAP)), Charsets.UTF_8)
        } catch (_: Exception) { "" }
    }
    /** Independent chat credential, encrypted under a fresh AES-GCM IV. */
    fun saveChat(token: String) {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key())
        prefs.edit()
            .putString("chat_iv", Base64.encodeToString(cipher.iv, Base64.NO_WRAP))
            .putString("chat_token", Base64.encodeToString(
                cipher.doFinal(token.toByteArray(Charsets.UTF_8)), Base64.NO_WRAP))
            .apply()
    }
    fun chatToken(): String {
        val iv = prefs.getString("chat_iv", "") ?: ""
        val encrypted = prefs.getString("chat_token", "") ?: ""
        if (iv.isEmpty() || encrypted.isEmpty()) return ""
        return try {
            val c = Cipher.getInstance("AES/GCM/NoPadding")
            c.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, Base64.decode(iv, Base64.NO_WRAP)))
            String(c.doFinal(Base64.decode(encrypted, Base64.NO_WRAP)), Charsets.UTF_8)
        } catch (_: Exception) { "" }
    }
    fun clearChat() {
        prefs.edit().remove("chat_iv").remove("chat_token").apply()
    }
    /** Clave opcional solo para PRUEBAS PERSONALES: nunca en BuildConfig/Git. */
    fun savePersonalCloudKey(value: String) {
        require(SkyPhoneCloud.validPersonalKey(value))
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key())
        prefs.edit()
            .putString("cloud_iv", Base64.encodeToString(cipher.iv, Base64.NO_WRAP))
            .putString("cloud_key", Base64.encodeToString(
                cipher.doFinal(value.toByteArray(Charsets.UTF_8)), Base64.NO_WRAP))
            .putBoolean("cloud_enabled", true)
            .apply()
    }
    fun cloudEnabled(): Boolean =
        prefs.getBoolean("cloud_enabled", false) &&
        !prefs.getString("cloud_key", "").isNullOrBlank()

    fun personalCloudKey(): String {
        if (!cloudEnabled()) return ""
        return try {
            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(Cipher.DECRYPT_MODE, key(),
                GCMParameterSpec(128, Base64.decode(prefs.getString("cloud_iv", ""), Base64.NO_WRAP)))
            String(cipher.doFinal(Base64.decode(
                prefs.getString("cloud_key", ""), Base64.NO_WRAP)), Charsets.UTF_8)
        } catch (_: Exception) { "" }
    }
    fun clearPersonalCloudKey() {
        prefs.edit().remove("cloud_iv").remove("cloud_key").remove("cloud_enabled").apply()
    }
    /** Separate Groq credential; encrypted with Android Keystore and never compiled into APK. */
    fun saveGroqKey(value: String) {
        require(SkyGroqCloud.validKey(value)) { "Clave Groq no válida." }
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key())
        prefs.edit()
            .putString("groq_iv", Base64.encodeToString(cipher.iv, Base64.NO_WRAP))
            .putString("groq_key", Base64.encodeToString(
                cipher.doFinal(value.toByteArray(Charsets.UTF_8)), Base64.NO_WRAP))
            .apply()
    }

    fun groqEnabled(): Boolean = !prefs.getString("groq_key", "").isNullOrBlank() &&
        groqKey().isNotBlank()

    fun groqKey(): String = try {
        val iv = prefs.getString("groq_iv", "").orEmpty()
        val ciphertext = prefs.getString("groq_key", "").orEmpty()
        if (iv.isBlank() || ciphertext.isBlank()) "" else {
            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(Cipher.DECRYPT_MODE, key(),
                GCMParameterSpec(128, Base64.decode(iv, Base64.NO_WRAP)))
            String(cipher.doFinal(Base64.decode(ciphertext, Base64.NO_WRAP)), Charsets.UTF_8)
        }
    } catch (_: Exception) { "" }

    fun clearGroqKey() {
        prefs.edit().remove("groq_key").remove("groq_iv").apply()
    }

    /** Revocar Windows jamás debe borrar la clave independiente del teléfono. */
    fun clear() {
        prefs.edit().remove("server").remove("id").remove("iv").remove("token")
            .remove("chat_iv").remove("chat_token").apply()
    }
}
