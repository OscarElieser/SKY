package ni.sky.mobileagent

import android.content.Context
import org.json.JSONObject

/**
 * Shared SKY security contract copied from shared/sky_core_contract_v1.json.
 * Policy inspection only. Does not authorize microphone, apps, files, billing
 * or device control by itself. Android's native permissions remain mandatory.
 */
object SkyCoreContract {
    data class Decision(val allowed: Boolean, val requiresConfirmation: Boolean,
                        val reason: String)

    fun inspect(context: Context, action: String, origin: String,
                perActionApproved: Boolean = false,
                platformPermission: Boolean = false): Decision {
        // Fail closed on missing, malformed or changed contract.
        return try {
            val text = context.assets.open("sky_core_contract_v1.json").bufferedReader()
                .use { it.readText() }
            val data = JSONObject(text)
            if (data.optString("schema") != "sky.core.contract.v1" ||
                data.optString("unknown_action") != "deny" ||
                data.optJSONObject("security")
                    ?.optBoolean("model_output_grants_authorization", true) != false
            ) return Decision(false, false, "unsafe_contract")
            val forbidden = data.getJSONArray("forbidden_actions")
            if ((0 until forbidden.length()).any { forbidden.optString(it) == action })
                return Decision(false, false, "forbidden")
            val definition = data.getJSONObject("actions").optJSONObject(action)
                ?: return Decision(false, false, "unknown_action")
            val needsApproval = definition.optString("approval") == "explicit_per_action"
            val origins = data.getJSONArray("allowed_origins")
            if ((0 until origins.length()).none { origins.optString(it) == origin })
                return Decision(false, needsApproval, "untrusted_origin")
            if (!platformPermission)
                return Decision(false, needsApproval, "platform_permission")
            if (needsApproval && !perActionApproved)
                return Decision(false, true, "per_action_approval")
            Decision(true, needsApproval, "authorized_by_policy_not_executed")
        } catch (_: Exception) {
            Decision(false, false, "contract_unavailable")
        }
    }

    fun canonicalReceipt(context: Context, raw: String): String {
        return try {
            val data = context.assets.open("sky_core_contract_v1.json").bufferedReader()
                .use { JSONObject(it.readText()) }
            val allowed = data.getJSONArray("receipts")
            if ((0 until allowed.length()).any { allowed.optString(it) == raw }) raw
                else "ESTADO_DESCONOCIDO"
        } catch (_: Exception) {
            "ESTADO_DESCONOCIDO"
        }
    }
}
