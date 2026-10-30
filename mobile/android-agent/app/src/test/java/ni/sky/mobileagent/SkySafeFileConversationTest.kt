package ni.sky.mobileagent

import org.junit.Assert.*
import org.junit.Test

class SkySafeFileConversationTest {
    @Test fun understandsNaturalRequestsWithoutExecuting() {
        val cases = listOf(
            "SKY, por favor crea un archivo clase.md con contenido: Nicaragua" to "crear",
            "SKY, necesito que actualices notas.txt con: Versión 2" to "reemplazar",
            "SKY, podrías incorporar al archivo notas.txt: Conclusión" to "agregar",
            "SKY, quiero que prepares un documento informe.docx con contenido: Informe" to "crear",
            "Renombra el archivo notas.txt a final.txt" to "renombrar",
            "Mueve el archivo notas.txt a la papelera" to "papelera"
        )
        for ((utterance, op) in cases) {
            val proposal = SkySafeFileConversation.prepare(utterance)
            assertNotNull(utterance, proposal)
            assertEquals(op, proposal!!.operation)
        }
    }

    @Test fun ignoresUnsafeOrIncompleteOrders() {
        for (utterance in listOf(
            "borra todas mis fotos",
            "ejecuta el terminal",
            "crea un archivo ../secreto.md con contenido: no",
            "crea un documento informe.docx",
            "SKY, cambia los archivos en Windows",
            "Mueve el archivo .env a la papelera"
        )) assertNull(utterance, SkySafeFileConversation.prepare(utterance))
    }
}
