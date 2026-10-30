package ni.sky.mobileagent

import android.app.Activity
import android.app.AlertDialog
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.EditText
import android.text.InputFilter
import android.text.InputType
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import java.net.HttpURLConnection
import java.net.URL
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import org.json.JSONObject

/** Instagram mobile link. Never accepts owner or Meta secrets. */
class SkyInstagramMobileLink(private val host: Activity, private val feedback: (String)->Unit) {
    private val base="https://jojzuaeqmjgnqikpnfxk.supabase.co/functions/v1/sky-instagram"
    private val prefs=host.getSharedPreferences("sky_instagram_mobile_v1",Context.MODE_PRIVATE)
    private fun key():SecretKey {
        val store=KeyStore.getInstance("AndroidKeyStore").apply{load(null)}
        (store.getKey("sky_instagram_device_v1",null) as? SecretKey)?.let{return it}
        val gen=KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore")
        gen.init(KeyGenParameterSpec.Builder("sky_instagram_device_v1",
            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
            .setKeySize(256).setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build())
        return gen.generateKey()
    }
    private fun save(token:String) {
        val c=Cipher.getInstance("AES/GCM/NoPadding")
        c.init(Cipher.ENCRYPT_MODE,key())
        prefs.edit().putString("iv",Base64.encodeToString(c.iv,Base64.NO_WRAP))
            .putString("credential",Base64.encodeToString(c.doFinal(token.toByteArray()),Base64.NO_WRAP)).apply()
    }
    private fun token():String {
        return try {
        val iv=prefs.getString("iv",null)?:return ""
        val data=prefs.getString("credential",null)?:return ""
        val c=Cipher.getInstance("AES/GCM/NoPadding")
        c.init(Cipher.DECRYPT_MODE,key(),GCMParameterSpec(128,Base64.decode(iv,Base64.NO_WRAP)))
        String(c.doFinal(Base64.decode(data,Base64.NO_WRAP)),Charsets.UTF_8)
    }catch(_:Exception){""}
    }
    private fun clear(){prefs.edit().remove("iv").remove("credential").apply()}
    private fun request(path:String,verb:String,credential:String?=null,data:JSONObject?=null):JSONObject {
        require(path in setOf("/pair-claim","/mobile-status","/mobile-profile","/mobile-start","/mobile-disconnect"))
        val conn=URL(base+path).openConnection() as HttpURLConnection
        try {
            conn.requestMethod=verb;conn.instanceFollowRedirects=false
            conn.connectTimeout=8000;conn.readTimeout=10000
            conn.setRequestProperty("Accept","application/json")
            credential?.let{conn.setRequestProperty("Authorization","Bearer "+it)}
            data?.let{
                conn.doOutput=true;conn.setRequestProperty("Content-Type","application/json")
                conn.outputStream.use { output->output.write(it.toString().toByteArray()) }
            }
            val status=conn.responseCode
            if(status !in 200..299)error("Servidor Instagram HTTP "+status)
            val body=conn.inputStream.bufferedReader().use{it.readText().take(8192)}
            return JSONObject(body)
        }finally{conn.disconnect()}
    }
    private fun async(work:()->String){
        Thread{
            val msg=try{work()}catch(e:Exception){"Instagram: "+(e.message?:"Error de conexión")}
            host.runOnUiThread{feedback(msg)}
        }.start()
    }
    fun show() {
        val choices=arrayOf("Vincular este teléfono con código temporal",
            "Consultar conexión verificada","Verificar identidad real con Meta",
            "Renovar autorización oficial con Meta","Bandeja de mensajes de Instagram",
            "Desvincular este teléfono")
        // setMessage + setItems oculta las opciones en AlertDialog.
        AlertDialog.Builder(host).setTitle("SKY · Instagram seguro")
            .setItems(choices){_,which->when(which){
                0->pair()
                1->check()
                2->verifyProfile()
                3->renewAuthorization()
                4->openInbox()
                5->AlertDialog.Builder(host).setTitle("Desvincular Instagram")
                    .setMessage("¿Revocar el acceso de este teléfono? No se revoca el permiso global de Meta.")
                    .setPositiveButton("Revocar"){_,_->disconnect()}
                    .setNegativeButton("Cancelar",null).show()
            }}
            .setNeutralButton("Seguridad"){_,_->
                AlertDialog.Builder(host).setTitle("Autorización segura")
                    .setMessage("Meta ya autorizó el servidor. La APK recibe solo una credencial " +
                        "revocable de este dispositivo, nunca la clave maestra ni el token Meta. " +
                        "La identidad exacta del perfil debe verificarse aparte.")
                    .setPositiveButton("Entendido",null).show()
            }
            .setNegativeButton("Cerrar",null).show()
    }
    private fun pair(){
        val input=EditText(host).apply{
            hint="Código temporal de 18 caracteres";setSingleLine(true)
            inputType=InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS
            filters=arrayOf(InputFilter.LengthFilter(18))
        }
        AlertDialog.Builder(host).setTitle("Emparejar Instagram")
            .setMessage("Generá un código temporal desde el servidor SKY mediante una sesión autorizada del propietario. Caduca a los 10 minutos.")
            .setView(input).setPositiveButton("Vincular"){_,_->
                val code=input.text.toString().trim().lowercase()
                if(!Regex("[a-f0-9]{18}").matches(code)){feedback("Código temporal inválido.");return@setPositiveButton}
                async {
                    val result=request("/pair-claim","POST",data=JSONObject().put("code",code))
                    val device=result.getString("device_token")
                    require(device.length==43){"Credencial móvil inválida"}
                    save(device)
                    "SKY Android vinculado al servidor Instagram. Consultá el estado para comprobar permisos."
                }
            }.setNegativeButton("Cancelar",null).show()
    }
    private fun check(){
        val credential=token()
        if(credential.isBlank()){feedback("Este teléfono aún no está vinculado con Instagram.");return}
        async {
            val result=request("/mobile-status","GET",credential)
            val connected=result.optBoolean("authorized",false)
            val scopes=result.optJSONObject("connection")?.optJSONArray("scopes")
            val permissions=(0 until (scopes?.length()?:0)).joinToString(", "){scopes!!.optString(it)}
            if(connected) "Instagram: autorización del servidor confirmada. Permisos: "+permissions+
                ". Identidad de perfil aún pendiente de verificación."
            else "Instagram: el servidor todavía no registra una autorización activa."
        }
    }

    /** Independent live API check; never assumes a public profile means OAuth identity. */
    private fun verifyProfile(){
        val credential=token()
        if(credential.isBlank()){
            feedback("Vinculá primero este teléfono con un código temporal.")
            return
        }
        Thread {
            val message=try {
                val response=request("/mobile-profile","GET",credential)
                val tokenValid=response.optBoolean("token_valid",false)
                val verified=response.optBoolean("profile_verified",false)
                val expires=response.optString("token_expires_at","").ifBlank{"No informada por Meta"}
                if(verified && tokenValid) {
                    val username=response.optString("username","")
                    val accountType=response.optString("account_type","Sin especificar")
                    // Compare against the one locally identified Instagram profile when unambiguous.
                    val prefs=host.getSharedPreferences("sky_public_social_profiles",Context.MODE_PRIVATE)
                    val profiles=org.json.JSONArray(prefs.getString("public_profiles_v1","[]"))
                    val handles=(0 until profiles.length()).mapNotNull { index ->
                        val entry=profiles.optJSONObject(index)
                        if(entry?.optString("platform")=="Instagram")entry.optString("handle").trimStart('@') else null
                    }.filter {it.isNotBlank()}
                    val matches=handles.size==1 && handles[0].equals(username,true)
                    val comparison=when {
                        handles.size!=1 -> "Comprobá que @"+username+" sea tu perfil autorizado."
                        matches -> "Coincide con el perfil local @"+handles[0]+"."
                        else -> "ATENCIÓN: no coincide con el perfil local @"+handles[0]+"."
                    }
                    "Meta verificó la identidad @"+username+". Cuenta: "+accountType+
                        ". "+comparison+" Vigencia del token: "+expires+
                        ". Publicaciones y mensajes siguen deshabilitados hasta sus pruebas."
                } else {
                    val reason=when(response.optString("reason","")) {
                        "missing_facebook_page_permissions" ->
                            "El token usa Facebook Login pero faltan pages_show_list y pages_read_engagement. " +
                            "La vinculación del teléfono sigue activa; hay que actualizar los permisos oficiales en Meta."
                        "token_expired","token_invalid_or_unavailable" ->
                            "El token Meta expiró, fue revocado o no responde. Se requiere renovar la autorización de Meta."
                        "facebook_page_profile_unavailable" ->
                            "Meta no devolvió un perfil profesional asociado a una Página de Facebook."
                        "multiple_authorized_profiles" ->
                            "Meta devolvió varios perfiles y no se puede seleccionar uno automáticamente."
                        "instagram_profile_unavailable" ->
                            "Meta no devolvió el perfil mediante Instagram Login; revisar permisos."
                        "not_connected" -> "La autorización del servidor ya no está disponible."
                        else -> "La identidad todavía no puede verificarse mediante Meta."
                    }
                    "Identidad NO verificada. "+reason+" Token válido: "+
                        (if(tokenValid)"Sí" else "No")+". No se ha publicado nada."
                }
            } catch (_: Exception) {
                "No se pudo completar la consulta oficial con Meta. Revisá la conexión e intentá nuevamente."
            }
            host.runOnUiThread {
                if(!host.isFinishing) AlertDialog.Builder(host)
                    .setTitle("SKY · Identidad oficial de Instagram")
                    .setMessage(message)
                    .setPositiveButton("Entendido",null).show()
            }
        }.start()
    }

    /** Initiate OAuth in the trusted browser using only this phone's revocable credential. */
    private fun renewAuthorization() {
        val credential=token()
        if(credential.isBlank()){
            feedback("Vinculá primero este teléfono con código temporal.")
            return
        }
        AlertDialog.Builder(host)
            .setTitle("Renovar permisos de Instagram")
            .setMessage("SKY abrirá el inicio de sesión oficial de Meta. Revisá el perfil y los permisos solicitados antes de autorizar. Nunca introduzcás contraseñas en SKY: solo en el sitio oficial de Meta. El teléfono conservará su vinculación.")
            .setPositiveButton("Abrir Meta"){_,_->
                Thread {
                    try {
                        val response=request("/mobile-start","POST",credential,JSONObject())
                        val url=Uri.parse(response.getString("authorization_url"))
                        val trusted=url.scheme=="https" &&
                            url.host in setOf("www.facebook.com","business.facebook.com","www.instagram.com") &&
                            (url.path?.endsWith("/dialog/oauth")==true ||
                             url.path?.endsWith("/oauth/authorize")==true) &&
                            !url.getQueryParameter("state").isNullOrBlank()
                        require(trusted) { "URL de autorización no válida" }
                        host.runOnUiThread {
                            if(!host.isFinishing){
                                try {
                                    host.startActivity(Intent(Intent.ACTION_VIEW,url))
                                } catch (_:Exception) {
                                    feedback("No se pudo abrir el navegador oficial de Meta.")
                                }
                            }
                        }
                    } catch (_:Exception) {
                        host.runOnUiThread {
                            if(!host.isFinishing)
                                feedback("Instagram: no se pudo iniciar la renovación segura. Revisá tu conexión.")
                        }
                    }
                }.start()
            }
            .setNegativeButton("Cancelar",null)
            .show()
    }

    /** Read-only owner inbox, protected by the phone's revocable Keystore credential. */
    private fun openInbox() {
        val credential = token()
        if (credential.isBlank()) {
            feedback("Vinculá primero este teléfono con Instagram.")
            return
        }
        SkyInstagramInbox(host, credential).show()
    }

    private fun disconnect(){
        val credential=token()
        if(credential.isBlank()){clear();feedback("Este teléfono ya está desvinculado.");return}
        async {
            request("/mobile-disconnect","POST",credential,JSONObject())
            clear()
            "Credencial Instagram de este teléfono revocada."
        }
    }
}
