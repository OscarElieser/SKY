package ni.sky.mobileagent

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class SkyCoreContractRuntimeTest {
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext

    @Test fun sharedContractIsNativeAndDefaultDeny() {
        assertEquals("platform_permission",
            SkyCoreContract.inspect(context, "open_app", "owner_typed").reason)
        assertTrue(SkyCoreContract.inspect(context, "open_app", "owner_typed",
            platformPermission = true).allowed)
        assertFalse(SkyCoreContract.inspect(context, "open_app", "model_output",
            platformPermission = true).allowed)
        assertFalse(SkyCoreContract.inspect(context, "unknown_command", "owner_typed",
            platformPermission = true).allowed)
        assertFalse(SkyCoreContract.inspect(context, "disable_play_protect", "owner_typed",
            perActionApproved = true, platformPermission = true).allowed)
    }

    @Test fun irreversibleActionsNeedSeparateApproval() {
        val pending = SkyCoreContract.inspect(context, "delete_file", "owner_spoken",
            platformPermission = true)
        assertFalse(pending.allowed)
        assertTrue(pending.requiresConfirmation)
        val withoutUi = SkyCoreContract.inspect(context, "delete_file", "owner_spoken",
            perActionApproved = true, platformPermission = true)
        assertFalse(withoutUi.allowed)
        assertEquals("local_ui_approval", withoutUi.reason)
        val approved = SkyCoreContract.inspect(context, "delete_file", "owner_typed",
            perActionApproved = true, platformPermission = true, localUiApproved = true)
        assertTrue(approved.allowed)
        val untrusted = SkyCoreContract.inspect(context, "delete_file", "remote_server",
            perActionApproved = true, platformPermission = true)
        assertFalse(untrusted.allowed)
    }

    @Test fun receiptDoesNotInflateSuccess() {
        assertEquals("ESTADO_DESCONOCIDO", SkyCoreContract.canonicalReceipt(
            context, "COMPLETADA"))
        assertEquals("ENVIADA_SIN_VERIFICAR", SkyCoreContract.canonicalReceipt(
            context, "ENVIADA_SIN_VERIFICAR"))
    }
}
