package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkyScientificMarkupTest {
    @Test fun fractionsSubscriptsAndEquilibriumUseRealMathMl() {
        val html = SkyScientificMarkup.toHtml(
            "La constante:\n\\[\nK_{\\text{eq}} = \\frac{k_{\\text{f}}}{k_{\\text{r}}}\n\\]"
        )
        assertTrue(html.contains("<math"))
        assertTrue(html.contains("<mfrac>"))
        assertTrue(html.contains("<msub>"))
        assertTrue(html.contains("<mtext>eq</mtext>"))
        assertFalse(html.contains("<p>\\["))
    }

    @Test fun reactionArrowAndScienceNotationRenderAsSymbols() {
        val html = SkyScientificMarkup.toHtml(
            "\\[\nA+B\\;\\rightleftharpoons\\;C\n\\]"
        )
        assertTrue(html.contains("⇌"))
        assertTrue(html.contains("display=\"block\""))
    }

    @Test fun markdownHeadingsAndBoldRenderAndAreEscaped() {
        val html = SkyScientificMarkup.toHtml("### 3. Velocidad inicial\n**Problema** <script>alert(1)</script>")
        assertTrue(html.contains("<h3>3. Velocidad inicial</h3>"))
        assertTrue(html.contains("<strong>Problema</strong>"))
        assertFalse(html.contains("<script>"))
        assertTrue(html.contains("&lt;script&gt;"))
    }

    @Test fun inlineMathAndExponentHaveMathMlSemantics() {
        val html = SkyScientificMarkup.toHtml("La energía es \\(E = mc^{2}\\).")
        assertTrue(html.contains("<msup>"))
        assertTrue(html.contains("display=\"inline\""))
        assertFalse(html.contains("\\(E"))
    }

    @Test fun markdownTablesRenderWithEscapedCellsAndHeaders() {
        val html = SkyScientificMarkup.toHtml(
            "| Magnitud | Valor |\n|---|---|\n| Masa | 2 kg |\n| Nota | <img src=x> |"
        )
        assertTrue(html.contains("<table>"))
        assertTrue(html.contains("<th>Magnitud</th>"))
        assertTrue(html.contains("<td>2 kg</td>"))
        assertFalse(html.contains("<img"))
        assertTrue(html.contains("&lt;img"))
    }

    @Test fun multilineMathDoesNotLeakLatexMarkers() {
        val html = SkyScientificMarkup.toHtml(
            "### Ejercicio\n\\[\nv_{\\text{dir}} = k_f[A][B]\n\\]"
        )
        assertTrue(html.contains("<math"))
        assertTrue(html.contains("<msub>"))
        assertTrue(html.contains("<mtext>dir</mtext>"))
        assertFalse(html.contains("<p>\\["))
    }

    @Test fun veryLongEquationDoesNotCrashRenderer() {
        val html = SkyScientificMarkup.mathMl("x".repeat(6000))
        assertTrue(html.startsWith("<code>"))
    }
}
