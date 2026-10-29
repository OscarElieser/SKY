package ni.sky.mobileagent

import android.graphics.Bitmap
import android.graphics.Canvas
import android.view.View
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/** Comprueba píxeles reales del personaje en Android, no un mock de sus estados. */
@RunWith(AndroidJUnit4::class)
class SkyAnimeFaceRuntimeTest {
    @Test fun expressionCommandsChangeActualRenderedPixels() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val context = instrumentation.targetContext
        var happy: Bitmap? = null
        var angry: Bitmap? = null
        instrumentation.runOnMainSync {
            val eyes = SkyFriendlyEyesView(context)
            val w = 360
            val h = 590
            eyes.measure(
                View.MeasureSpec.makeMeasureSpec(w, View.MeasureSpec.EXACTLY),
                View.MeasureSpec.makeMeasureSpec(h, View.MeasureSpec.EXACTLY)
            )
            eyes.layout(0, 0, w, h)
            fun snapshot(): Bitmap {
                val bitmap = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
                eyes.draw(Canvas(bitmap))
                return bitmap
            }
            assertTrue(eyes.showExpression("feliz").isNotBlank())
            happy = snapshot()
            assertTrue(eyes.showExpression("enojada").isNotBlank())
            angry = snapshot()
        }
        try {
            assertNotNull(happy)
            assertNotNull(angry)
            assertFalse("Los gestos deben producir dibujos distintos",
                happy!!.sameAs(angry))
            assertTrue("La cara necesita píxeles visibles",
                happy!!.getPixel(110, 290) != 0)
        } finally {
            happy?.recycle()
            angry?.recycle()
        }
    }
}
