package ni.sky.mobileagent

import android.content.ContentResolver
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Color
import android.graphics.pdf.PdfRenderer
import android.media.MediaMetadataRetriever
import java.io.InputStreamReader
import java.util.Locale

/**
 * Local and bounded preview BEFORE consent to upload. Never executes input.
 * A preview is not evidence that the complete remote analysis succeeded.
 */
internal object SkyAttachmentPreview {
    data class Result(
        val label: String,
        val details: String,
        val bitmap: Bitmap? = null,
        val pageCount: Int = 0,
        val pageIndex: Int = 0
    )

    /** Open just one PDF page on a worker; never decode all pages into memory. */
    fun readPdfPage(resolver: ContentResolver, file: SkyAttachmentBatch.Item, index: Int): Result {
        require(file.mime == "application/pdf") { "El adjunto no es un PDF." }
        val descriptor = resolver.openFileDescriptor(file.uri, "r")
            ?: throw IllegalArgumentException("Android no permitió abrir este PDF.")
        return descriptor.use { fd ->
            PdfRenderer(fd).use { pdf ->
                require(pdf.pageCount > 0) { "El PDF no tiene páginas." }
                require(index in 0 until pdf.pageCount) { "La página solicitada no existe." }
                pdf.openPage(index).use { page ->
                    val factor = minOf(960f / page.width, 1250f / page.height, 1f)
                    val bitmap = Bitmap.createBitmap(
                        (page.width * factor).toInt().coerceAtLeast(1),
                        (page.height * factor).toInt().coerceAtLeast(1),
                        Bitmap.Config.ARGB_8888)
                    bitmap.eraseColor(Color.WHITE)
                    page.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                    Result(
                        "PDF · página " + (index + 1) + " de " + pdf.pageCount,
                        file.name + "\n" + file.mime + " · " + file.sizeMb() + " MB" +
                            "\nVista previa local: no verifica ni extrae el texto completo.",
                        bitmap, pdf.pageCount, index
                    )
                }
            }
        }
    }

    fun read(resolver: ContentResolver, file: SkyAttachmentBatch.Item): Result {
        val ext = file.name.substringAfterLast('.', "").lowercase(Locale.ROOT)
        val basic = file.name + "\n" + file.mime + " · " + file.sizeMb() + " MB"
        return when {
            file.mime.startsWith("image/") && ext != "svg" -> {
                val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
                resolver.openInputStream(file.uri)?.use { BitmapFactory.decodeStream(it, null, bounds) }
                require(bounds.outWidth > 0 && bounds.outHeight > 0) { "La imagen no pudo decodificarse." }
                var sample = 1
                while (bounds.outWidth / sample > 1100 || bounds.outHeight / sample > 1100) sample *= 2
                val options = BitmapFactory.Options().apply {
                    inSampleSize = sample
                    inPreferredConfig = Bitmap.Config.RGB_565
                }
                val bitmap = resolver.openInputStream(file.uri)?.use {
                    BitmapFactory.decodeStream(it, null, options)
                } ?: throw IllegalArgumentException("La imagen no tiene una vista previa decodificable.")
                Result("Imagen · vista previa local", basic + "\nDimensiones: " +
                    bounds.outWidth + " × " + bounds.outHeight + " px", bitmap)
            }
            file.mime == "application/pdf" -> readPdfPage(resolver, file, 0)
            file.kind == SkyAttachmentBatch.Kind.OFFICE -> {
                val preview = SkyOfficeStreaming.preview(resolver, file).take(5500)
                Result("Office · texto y celdas recuperados", basic +
                    "\n\n" + preview +
                    "\n\nVista parcial: no contiene necesariamente imágenes, fórmulas ni diseño.")
            }
            file.mime.startsWith("text/") || ext in setOf(
                "txt","md","csv","json","xml","html","htm","py","kt","java","js",
                "ts","dart","css","sql","yaml","yml","log","sh","ps1","ini",
                "cfg","rtf","svg","tex","ipynb") -> {
                val chars = CharArray(5500)
                val amount = resolver.openInputStream(file.uri)?.use { stream ->
                    InputStreamReader(stream, Charsets.UTF_8).use { it.read(chars) }
                } ?: -1
                require(amount >= 0) { "No se pudo leer el texto del archivo." }
                Result("Texto · muestra local", basic + "\n\n" +
                    String(chars, 0, amount) + if (file.size > amount) "\n\n[Muestra parcial]" else "")
            }
            file.mime.startsWith("audio/") || file.mime.startsWith("video/") -> {
                val retriever = MediaMetadataRetriever()
                var thumbnail: Bitmap? = null
                val detail = try {
                    resolver.openFileDescriptor(file.uri, "r")?.use { fd ->
                        retriever.setDataSource(fd.fileDescriptor)
                        val duration = retriever.extractMetadata(
                            MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLongOrNull()
                        if (file.mime.startsWith("video/") &&
                            android.os.Build.VERSION.SDK_INT >= 27) {
                            // Scaled frame, never a full-resolution 4K/8K bitmap.
                            val width = retriever.extractMetadata(
                                MediaMetadataRetriever.METADATA_KEY_VIDEO_WIDTH)?.toIntOrNull() ?: 960
                            val height = retriever.extractMetadata(
                                MediaMetadataRetriever.METADATA_KEY_VIDEO_HEIGHT)?.toIntOrNull() ?: 540
                            val ratio = minOf(960f / width.coerceAtLeast(1),
                                960f / height.coerceAtLeast(1), 1f)
                            thumbnail = runCatching {
                                retriever.getScaledFrameAtTime(0L,
                                    MediaMetadataRetriever.OPTION_CLOSEST_SYNC,
                                    (width * ratio).toInt().coerceAtLeast(1),
                                    (height * ratio).toInt().coerceAtLeast(1))
                            }.getOrNull()
                        }
                        "Duración: " + if (duration != null) (duration / 1000).toString() +
                            " segundos" else "no disponible"
                    } ?: "Metadatos multimedia no disponibles."
                } catch (_: Exception) { "Metadatos multimedia no disponibles." }
                finally { runCatching { retriever.release() } }
                Result(if (file.mime.startsWith("video/")) "Video · fotograma de muestra"
                    else "Audio · información del archivo",
                    basic + "\n" + detail +
                        "\nLa vista previa no transcribe ni reproduce el contenido.",
                    thumbnail)
            }
            else -> Result("Archivo seleccionado", basic +
                "\nEste formato no dispone de una vista previa local completa.")
        }
    }
}
