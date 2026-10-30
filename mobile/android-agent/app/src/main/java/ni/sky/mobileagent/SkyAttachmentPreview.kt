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
    data class Result(val label: String, val details: String, val bitmap: Bitmap? = null)

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
            file.mime == "application/pdf" -> {
                val descriptor = resolver.openFileDescriptor(file.uri, "r")
                    ?: throw IllegalArgumentException("Android no permitió abrir este PDF.")
                descriptor.use { fd ->
                    PdfRenderer(fd).use { pdf ->
                        require(pdf.pageCount > 0) { "El PDF no tiene páginas." }
                        pdf.openPage(0).use { page ->
                            val factor = minOf(960f / page.width, 1250f / page.height, 1f)
                            val bitmap = Bitmap.createBitmap(
                                (page.width * factor).toInt().coerceAtLeast(1),
                                (page.height * factor).toInt().coerceAtLeast(1),
                                Bitmap.Config.ARGB_8888)
                            bitmap.eraseColor(Color.WHITE)
                            page.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                            Result("PDF · primera página", basic +
                                "\nTotal de páginas: " + pdf.pageCount +
                                "\nLa vista previa no extrae ni comprueba todas las páginas.", bitmap)
                        }
                    }
                }
            }
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
                val detail = try {
                    resolver.openFileDescriptor(file.uri, "r")?.use { fd ->
                        retriever.setDataSource(fd.fileDescriptor)
                        val duration = retriever.extractMetadata(
                            MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLongOrNull()
                        "Duración: " + if (duration != null) (duration / 1000).toString() +
                            " segundos" else "no disponible"
                    } ?: "Metadatos multimedia no disponibles."
                } catch (_: Exception) { "Metadatos multimedia no disponibles." }
                finally { runCatching { retriever.release() } }
                Result("Multimedia · metadatos", basic + "\n" + detail +
                    "\nLa transcripción o análisis requiere un motor compatible y autorización.")
            }
            else -> Result("Archivo seleccionado", basic +
                "\nEste formato no dispone de una vista previa local completa.")
        }
    }
}
