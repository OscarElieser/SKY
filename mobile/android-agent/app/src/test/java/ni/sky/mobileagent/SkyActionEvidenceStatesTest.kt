package ni.sky.mobileagent

import org.junit.Assert.assertEquals
import org.junit.Test

class SkyActionEvidenceStatesTest {
    @Test fun authorizationIsNotReportedAsExecutionSuccess() {
        assertEquals("AUTORIZADA", SkyActionEvidence.normalized("AUTHORIZED"))
        assertEquals("AUTORIZADA", SkyActionEvidence.normalized("AUTORIZADA"))
        assertEquals("ENVIADA_SIN_VERIFICAR", SkyActionEvidence.normalized("SENT"))
        assertEquals("VERIFICADA_LOCAL", SkyActionEvidence.normalized("VERIFIED_LOCAL"))
        assertEquals("RECHAZADA", SkyActionEvidence.normalized("REJECTED"))
        assertEquals("ESTADO_DESCONOCIDO", SkyActionEvidence.normalized("ESTADO_DESCONOCIDO"))
    }
}
