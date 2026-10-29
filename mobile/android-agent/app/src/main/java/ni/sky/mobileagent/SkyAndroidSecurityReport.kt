package ni.sky.mobileagent

import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import java.security.MessageDigest
import java.util.Locale

/** Evidencia verificable del APK instalado. No afirma certificación por Google. */
object SkyAndroidSecurityReport {
    @Suppress("DEPRECATION")
    fun certificateSha256(context: Context): String {
        val pm = context.packageManager
        val signatures = if (Build.VERSION.SDK_INT >= 28) {
            pm.getPackageInfo(context.packageName, PackageManager.GET_SIGNING_CERTIFICATES)
                .signingInfo?.apkContentsSigners
        } else {
            pm.getPackageInfo(context.packageName, PackageManager.GET_SIGNATURES).signatures
        }
        return signatures?.firstOrNull()?.toByteArray()?.let { data ->
            MessageDigest.getInstance("SHA-256").digest(data)
                .joinToString(":") { byte ->
                    String.format(Locale.ROOT, "%02X", byte.toInt() and 0xff)
                }
        } ?: "Sin información de firma"
    }

    @Suppress("DEPRECATION")
    fun status(context: Context): String {
        val pm = context.packageManager
        val installed = pm.getPackageInfo(context.packageName, PackageManager.GET_SERVICES)
        val version = installed.versionName ?: "desconocida"
        val accessibility = installed.services?.any {
            it.permission == "android.permission.BIND_ACCESSIBILITY_SERVICE"
        } == true
        val authorized = SkySupervisedControl(context).isAuthorized()
        val signature = runCatching { certificateSha256(context) }
            .getOrElse { "No disponible: no se pudo leer firma local" }
        return buildString {
            append("Versión instalada: ").append(version)
            append("\nTipo: ").append(if (BuildConfig.DEBUG) "DEPURACIÓN" else "RELEASE")
            append("\nControl supervisado: ").append(if (authorized) "AUTORIZADO" else "REVOCADO")
            append("\nAccesibilidad incluida: ").append(if (accessibility) "SÍ" else "NO")
            append("\nRed: HTTPS obligatorio; certificados del sistema")
            append("\nCifrado de claves: Android Keystore AES-GCM")
            append("\n\nHuella SHA-256 de la firma instalada:\n").append(signature)
            append("\n\nCompará esta huella con signer-fingerprint.txt del release oficial.")
            append("\nLa huella no demuestra que Play Protect haya aprobado el APK.")
            append("\nSi Play Protect muestra una alerta, NO desactives esa protección.")
        }
    }
}
