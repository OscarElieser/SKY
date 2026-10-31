package ni.sky.mobileagent

import android.graphics.Color
import android.graphics.Paint
import android.graphics.pdf.PdfDocument
import android.net.Uri
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

/** Checks real Android PdfRenderer on actual emulator APIs without network/AI. */
@RunWith(AndroidJUnit4::class)
class SkyAttachmentPreviewInstrumentedTest {
    @Test fun pdfPagesRenderOneAtATimeAndRejectInvalidIndex() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val local = File.createTempFile("sky-preview-", ".pdf", context.cacheDir)
        try {
            val document = PdfDocument()
            try {
                for (n in 1..2) {
                    val info = PdfDocument.PageInfo.Builder(300, 440, n).create()
                    val page = document.startPage(info)
                    page.canvas.drawColor(Color.WHITE)
                    page.canvas.drawText("Documento de prueba · página $n",
                        12f, 48f, Paint().apply {
                            color = Color.BLACK
                            textSize = 14f
                        })
                    document.finishPage(page)
                }
                local.outputStream().use { document.writeTo(it) }
            } finally {
                document.close()
            }
            val item = SkyAttachmentBatch.Item(
                Uri.fromFile(local), local.name, local.length(),
                "application/pdf", SkyAttachmentBatch.Kind.CLOUD
            )
            val first = SkyAttachmentPreview.read(context.contentResolver, item)
            assertEquals(2, first.pageCount)
            assertEquals(0, first.pageIndex)
            assertNotNull(first.bitmap)
            assertTrue(first.bitmap!!.width in 1..960)
            assertTrue(first.bitmap!!.height in 1..1250)

            val second = SkyAttachmentPreview.readPdfPage(context.contentResolver, item, 1)
            assertEquals(2, second.pageCount)
            assertEquals(1, second.pageIndex)
            assertNotNull(second.bitmap)
            assertTrue(second.label.contains("página 2 de 2"))

            try {
                SkyAttachmentPreview.readPdfPage(context.contentResolver, item, 2)
                fail("La página fuera de rango no debe abrirse")
            } catch (_: IllegalArgumentException) {
                // Verified rejection.
            }
            first.bitmap!!.recycle()
            second.bitmap?.recycle()
        } finally {
            local.delete()
        }
    }
}
