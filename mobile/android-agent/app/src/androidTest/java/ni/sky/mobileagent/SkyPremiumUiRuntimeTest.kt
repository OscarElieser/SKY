package ni.sky.mobileagent

import android.app.AlertDialog
import android.view.View
import android.view.ViewGroup
import android.widget.CheckBox
import android.widget.LinearLayout
import android.widget.TextView
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Smoke tests de la interfaz nativa dentro de Android. No modifica historial real
 * ni envía mensajes externos. Verifica navegación efectiva y controles enlazados.
 */
@RunWith(AndroidJUnit4::class)
class SkyPremiumUiRuntimeTest {
    @Test fun settingsTabsKeepTheirOriginalWorkingControls() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            scenario.onActivity { activity ->
                var consent = false
                var opened = false
                val contents = LinearLayout(activity).apply {
                    orientation = LinearLayout.VERTICAL
                }
                contents.addView(SkyPremiumUi.section(activity,
                    "Motor", "Proveedores conectados", "⚡"))
                val motorButton = TextView(activity).apply {
                    text = "Configuración original"
                }
                contents.addView(motorButton)
                contents.addView(SkyPremiumUi.section(activity,
                    "Privacidad", "Permisos por mensaje", "◈"))
                val consentBox = CheckBox(activity).apply {
                    text = "Datos privados para este mensaje"
                    setOnCheckedChangeListener { _, checked -> consent = checked }
                }
                contents.addView(consentBox)
                contents.addView(SkyPremiumUi.section(activity,
                    "Historial", "Consultas locales", "◷"))
                val historyItem = TextView(activity).apply {
                    text = "Historial sin borrar"
                    setOnClickListener { opened = true }
                }
                contents.addView(historyItem)
                val original = consentBox
                val root = SkyPremiumUi.settingsShell(activity, contents) {}
                activity.setContentView(root)
                val privacyTab = findText(root, "◈ Privacidad")
                assertNotNull("Debe existir pestaña de Privacidad", privacyTab)
                privacyTab!!.performClick()
                assertEquals("No debe recrear el Checkbox ni sus listeners", original,
                    findText(root, "Datos privados para este mensaje"))
                consentBox.isChecked = true
                assertTrue("El permiso original debe seguir conectado", consent)
                val historyTab = findText(root, "◷ Historial")
                assertNotNull(historyTab)
                historyTab!!.performClick()
                val originalHistory = findText(root, "Historial sin borrar")
                assertNotNull(originalHistory)
                originalHistory!!.performClick()
                assertTrue("El historial original debe responder al toque", opened)
            }
        }
    }

    @Test fun historyPremiumOpensWithoutReplacingSQLite() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            scenario.onActivity { activity ->
                val archive = SkyConversationArchive(activity)
                val question = "SKY UI runtime " + System.nanoTime()
                val entry = archive.append(question, "Respuesta local segura", "Groq")
                try {
                    val view = SkyPremiumHistory(activity, archive,
                        onOpenChat = {},
                        onExportEntry = {},
                        onExportAll = {},
                        onHistoryChanged = {}
                    ).show(question)
                    assertTrue("El historial debe mostrarse", view.isShowing)
                    assertNotNull("El buscador debe existir",
                        findText(view.window!!.decorView, "Buscar título, pregunta o respuesta"))
                    assertNotNull("El filtro de favoritos debe existir",
                        findText(view.window!!.decorView, "Favoritos"))
                    assertNotNull("El registro de prueba debe estar disponible",
                        archive.page(question).firstOrNull { it.id == entry.id })
                    view.dismiss()
                } finally {
                    archive.delete(entry.id)
                    archive.close()
                }
            }
        }
    }

    private fun findText(view: View, value: String): TextView? {
        if (view is TextView &&
            (view.text?.toString()?.contains(value) == true ||
             (view.hint?.toString()?.contains(value) == true))) {
            return view
        }
        if (view is ViewGroup) {
            for (index in 0 until view.childCount) {
                findText(view.getChildAt(index), value)?.let { return it }
            }
        }
        return null
    }
}
