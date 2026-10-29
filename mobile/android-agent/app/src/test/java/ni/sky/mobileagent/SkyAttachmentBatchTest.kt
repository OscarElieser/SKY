package ni.sky.mobileagent

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class SkyAttachmentBatchTest {
    @Test fun supportsMultipleMediaTypes() {
        val pdf = SkyAttachmentBatch.supportedType("investigacion.pdf", "application/octet-stream")
        assertEquals(SkyAttachmentBatch.Kind.CLOUD, pdf.first)
        assertEquals("application/pdf", pdf.second)
        assertEquals(SkyAttachmentBatch.Kind.CLOUD,
            SkyAttachmentBatch.supportedType("conferencia.mp4", "video/mp4").first)
        assertEquals(SkyAttachmentBatch.Kind.CLOUD,
            SkyAttachmentBatch.supportedType("tabla.csv", "text/plain").first)
        assertEquals(SkyAttachmentBatch.Kind.OFFICE,
            SkyAttachmentBatch.supportedType("informe.docx", "application/octet-stream").first)
    }

    @Test fun rejectsUnsupportedExecutable() {
        assertEquals(SkyAttachmentBatch.Kind.UNSUPPORTED,
            SkyAttachmentBatch.supportedType("instalador.exe", "application/octet-stream").first)
    }

    @Test fun uses100MbPerFileAndPdfProviderLimit() {
        assertEquals(100L * 1024 * 1024, SkyAttachmentBatch.MAX_PER_FILE)
        assertEquals(50L * 1024 * 1024, SkyAttachmentBatch.PDF_CLOUD_MAX)
        assertEquals(5, SkyAttachmentBatch.MAX_FILES)
    }
}
