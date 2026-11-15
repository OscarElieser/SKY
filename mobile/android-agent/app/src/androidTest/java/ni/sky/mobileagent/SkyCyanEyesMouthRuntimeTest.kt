package ni.sky.mobileagent

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.view.View
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Aceptación real: renderizar ojos y boca en Android sin imagen externa.
 * No altera ni simula funciones de micrófono, teléfono, contactos o chat.
 */
@RunWith(AndroidJUnit4::class)
class SkyCyanEyesMouthRuntimeTest {
    @Test fun onlyEyesAndMouthAreVisibleAndStatesChangePixels() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val frames = mutableListOf<Bitmap>()
        instrumentation.runOnMainSync {
            val view = SkyFriendlyEyesView(instrumentation.targetContext)
            view.measure(
                View.MeasureSpec.makeMeasureSpec(360, View.MeasureSpec.EXACTLY),
                View.MeasureSpec.makeMeasureSpec(590, View.MeasureSpec.EXACTLY)
            )
            view.layout(0, 0, 360, 590)
            fun render(mode: String): Bitmap {
                view.mode = mode
                val bitmap = Bitmap.createBitmap(360, 590, Bitmap.Config.ARGB_8888)
                view.draw(Canvas(bitmap))
                frames.add(bitmap)
                return bitmap
            }
            val idle = render("IDLE")
            assertEquals("Fuera de los ojos y la boca no debe aparecer cabeza ni marco",
                Color.TRANSPARENT, idle.getPixel(180, 100))
            assertTrue("Se deben ver los ojos brillantes",
                Color.alpha(idle.getPixel(111, 286)) > 0)
            assertTrue("Se debe ver boca en el área prevista",
                (138..222).any { x -> (393..448).any { y ->
                    Color.alpha(idle.getPixel(x, y)) > 100
                } })
            assertFalse("Las emociones y la escucha deben cambiar el dibujo",
                idle.sameAs(render("LISTENING")))
            assertFalse("La boca debe cambiar al responder por voz",
                idle.sameAs(render("SPEAKING")))
            assertFalse("Los ojos deben dormirse",
                idle.sameAs(render("SLEEPING")))
            assertFalse("La expresión de error no puede verse igual",
                idle.sameAs(render("ERROR")))
            assertTrue(view.showExpression("feliz").isNotEmpty())
            assertTrue(view.nextEmotion().isNotEmpty())
            view.reactTo("Hola SKY")
        }
        frames.forEach(Bitmap::recycle)
    }
}
