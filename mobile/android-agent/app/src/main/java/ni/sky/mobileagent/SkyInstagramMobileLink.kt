package ni.sky.mobileagent

import android.app.Activity
import android.app.AlertDialog
import android.content.Context
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
    private fun token():String=try {
        val iv=prefs.getString("iv",null)?:return ""
        val data=prefs.getString("credential",null)?:return ""
        val c=Cipher.getInstance("AES/GCM/NoPadding")
        c.init(Cipher.DECRYPT_MODE,key(),GCMParameterSpec(128,Base64.decode(iv,Base64.NO_WRAP)))
        String(c.doFinal(Base64.decode(data,Base64.NO_WRAP)),Charsets.UTF_8)
    }catch(_:Exception){""}
    private fun clear(){prefs.edit().remove("iv").remove("credential").apply()}
    private fun request(path:String,verb:String,credential:String?=null,data:JSONObject?=null):JSONObject {
        require(path in setOf("/pair-claim","/mobile-status","/mobile-disconnect"))
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
            "Consultar conexión verificada","Desvincular este teléfono")
        AlertDialog.Builder(host).setTitle("SKY · Instagram seguro")
            .setMessage("El servidor ya dispone de autorización Meta. " +
                "La APK solo recibirá una credencial de dispositivo, nunca el secreto principal.")
            .setItems(choices){_,which->when(which){
                0->pair()
                1->check()
                2->AlertDialog.Builder(host).setTitle("Desvincular Instagram")
                    .setMessage("¿Revocar el acceso de este teléfono? No se revoca el permiso global de Meta.")
                    .setPositiveButton("Revocar"){_,_->disconnect()}
                    .setNegativeButton("Cancelar",null).show()
            }}.setNegativeButton("Cerrar",null).show()
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
