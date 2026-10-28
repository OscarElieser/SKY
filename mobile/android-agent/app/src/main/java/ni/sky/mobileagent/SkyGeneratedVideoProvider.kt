package ni.sky.mobileagent

import android.content.ContentProvider
import android.content.ContentValues
import android.database.Cursor
import android.database.MatrixCursor
import android.net.Uri
import android.os.ParcelFileDescriptor
import android.provider.OpenableColumns
import java.io.File

/** Exposes only SKY's last user-generated video to explicitly chosen Android share targets. */
class SkyGeneratedVideoProvider : ContentProvider() {
    companion object {
        const val AUTHORITY = "ni.sky.mobileagent.generated"
        fun uri(): Uri = Uri.parse("content://" + AUTHORITY + "/video")
    }
    override fun onCreate(): Boolean = true
    override fun getType(uri: Uri): String? =
        if (uri.path == "/video") "video/mp4" else null
    private fun file(uri: Uri): File {
        require(uri.path == "/video") { "Unsupported content URI." }
        val c = context ?: throw IllegalStateException("No context")
        return File(c.cacheDir, "sky_creator_last.mp4")
    }
    override fun openFile(uri: Uri, mode: String): ParcelFileDescriptor {
        require(mode == "r") { "Read-only provider." }
        val file = file(uri)
        if (!file.isFile) throw java.io.FileNotFoundException("No generated video.")
        return ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY)
    }
    override fun query(uri: Uri, projection: Array<out String>?, selection: String?,
                       selectionArgs: Array<out String>?, sortOrder: String?): Cursor {
        val f = file(uri)
        return MatrixCursor(arrayOf(OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE)).apply {
            addRow(arrayOf("SKY-Video-Vertical.mp4", f.length()))
        }
    }
    override fun insert(uri: Uri, values: ContentValues?): Uri? = null
    override fun update(uri: Uri, values: ContentValues?, selection: String?,
                        selectionArgs: Array<out String>?): Int = 0
    override fun delete(uri: Uri, selection: String?, selectionArgs: Array<out String>?): Int = 0
}
