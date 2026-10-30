package ni.sky.mobileagent

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.UUID

@RunWith(AndroidJUnit4::class)
class SkyPrivateFileExecutorRuntimeTest {
    @Test fun createReplaceAndRestoreKeepsOriginal() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val filename = "skytest_" + UUID.randomUUID().toString().replace("-", "") + ".txt"
        val file = File(File(context.filesDir, "sky_safe_documents"), filename)
        val worker = SkyPrivateFileExecutor(context)
        try {
            val first = worker.execute(SkySafeFileConversation.Proposal("crear", filename, "original"))
            assertEquals("original", file.readText())
            assertNull(first.backupId)
            val second = worker.execute(SkySafeFileConversation.Proposal("reemplazar", filename, "nuevo"))
            assertNotNull(second.backupId)
            assertTrue(worker.listBackups().any { it.id == second.backupId && it.filename == filename })
            assertEquals("nuevo", file.readText())
            val restored = worker.restoreBackup(filename, second.backupId!!)
            assertEquals("original", file.readText())
            assertEquals(first.sha256, restored)
        } finally { file.delete() }
    }

    @Test fun refusesPathTraversal() {
        val worker = SkyPrivateFileExecutor(
            InstrumentationRegistry.getInstrumentation().targetContext)
        try {
            worker.execute(SkySafeFileConversation.Proposal("crear", "../escape.txt", "bad"))
            fail("Expected input rejection")
        } catch (_: IllegalArgumentException) {
            // No file may escape the private workspace.
        }
    }
}
